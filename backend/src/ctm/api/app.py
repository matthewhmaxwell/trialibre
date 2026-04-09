"""FastAPI application factory.

Creates the Trialibre API server that:
- Serves the React frontend (static files)
- Provides all API endpoints
- Auto-selects an available port
- Manages lifecycle of LLM providers, database, etc.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ctm import __version__
from ctm.config import Settings, load_settings
from ctm.db.base import Database
from ctm.providers.registry import create_provider, validate_config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    settings: Settings = app.state.settings

    # Initialize database
    db = Database(settings.database)
    await db.connect()
    app.state.db = db

    # Initialize LLM provider (if configured)
    issues = validate_config(settings.llm)
    if not issues:
        try:
            app.state.llm = create_provider(settings.llm)
            logger.info(f"LLM provider ready: {settings.llm.provider.value}")
        except Exception as e:
            logger.warning(f"LLM provider failed to initialize: {e}")
            app.state.llm = None
    else:
        logger.info(f"LLM not configured: {'; '.join(issues)}")
        app.state.llm = None

    # Enable sandbox if no LLM configured
    if app.state.llm is None and not settings.sandbox.enabled:
        settings.sandbox.enabled = True
        logger.info("No AI service configured. Sandbox mode activated.")

    # In-memory storage for uploaded custom trials (with lock for concurrency safety)
    import threading
    app.state.custom_trials: dict = {}
    app.state.custom_trials_lock = threading.Lock()

    yield

    # Shutdown
    await db.disconnect()
    if hasattr(app.state, "llm") and app.state.llm and hasattr(app.state.llm, "close"):
        await app.state.llm.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = load_settings()

    app = FastAPI(
        title="Trialibre",
        description="Clinical trial patient matching and enrollment management",
        version=__version__,
        lifespan=lifespan,
    )

    app.state.settings = settings

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    from ctm.api.routes import audit, batch, dashboard, health, ingest, match, privacy, referrals, sandbox, settings as settings_routes, trials

    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(match.router, prefix="/api/v1", tags=["Match"])
    app.include_router(batch.router, prefix="/api/v1", tags=["Batch"])
    app.include_router(trials.router, prefix="/api/v1", tags=["Trials"])
    app.include_router(ingest.router, prefix="/api/v1", tags=["Ingest"])
    app.include_router(referrals.router, prefix="/api/v1", tags=["Referrals"])
    app.include_router(privacy.router, prefix="/api/v1", tags=["Privacy"])
    app.include_router(sandbox.router, prefix="/api/v1", tags=["Sandbox"])
    app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])
    app.include_router(audit.router, prefix="/api/v1", tags=["Audit"])
    app.include_router(settings_routes.router, prefix="/api/v1", tags=["Settings"])

    # Serve frontend static files (if built)
    if settings.api.serve_frontend:
        frontend_path = Path(settings.api.frontend_build_path)
        if frontend_path.exists():
            app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
            logger.info(f"Serving frontend from {frontend_path}")

    return app
