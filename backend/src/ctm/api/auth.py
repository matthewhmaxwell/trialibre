"""API key authentication middleware.

When `api_keys` is configured (via CTM_API__API_KEYS env var or settings.yaml),
all `/api/v1/*` endpoints require a valid API key, except for paths in
`auth_exempt_paths` (health check, docs).

Supply the key via:
- `X-API-Key` request header (preferred)
- `?api_key=...` query parameter (fallback for tools that cannot send headers)
"""

from __future__ import annotations

import hmac
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces API key auth."""

    def __init__(self, app, api_keys: list[str], exempt_paths: list[str]):
        super().__init__(app)
        self._api_keys = [k for k in api_keys if k]  # Filter empty strings
        self._exempt_paths = tuple(exempt_paths)
        self._enabled = bool(self._api_keys)

    async def dispatch(self, request: Request, call_next):
        if not self._enabled:
            return await call_next(request)

        path = request.url.path

        # Exempt paths
        if any(path.startswith(p) for p in self._exempt_paths):
            return await call_next(request)

        # Only protect /api/* routes — static frontend stays public
        if not path.startswith("/api/"):
            return await call_next(request)

        # Extract key from header or query
        provided = request.headers.get("x-api-key") or request.query_params.get("api_key")
        if not provided:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": (
                        "API key required. Send via X-API-Key header or ?api_key= query parameter."
                    )
                },
            )

        # Constant-time comparison against every configured key
        if not any(hmac.compare_digest(provided, key) for key in self._api_keys):
            logger.warning(f"Invalid API key attempt on {path}")
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid API key."},
            )

        return await call_next(request)
