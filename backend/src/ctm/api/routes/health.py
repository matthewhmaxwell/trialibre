"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ctm import __version__
from ctm.models.api import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    llm = getattr(request.app.state, "llm", None)

    return HealthResponse(
        status="ok",
        version=__version__,
        llm_provider=settings.llm.provider.value,
        llm_connected=llm is not None,
        sandbox_mode=settings.sandbox.enabled,
        database_backend=settings.database.backend.value,
    )
