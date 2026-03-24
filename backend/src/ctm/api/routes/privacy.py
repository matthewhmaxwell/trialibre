"""Privacy settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ctm.models.api import PrivacyStatusResponse
from ctm.privacy.engine import PrivacyEngine

router = APIRouter()


@router.get("/privacy/status", response_model=PrivacyStatusResponse)
async def privacy_status(request: Request) -> PrivacyStatusResponse:
    """Get current privacy status for the UI indicator."""
    settings = request.app.state.settings
    engine = PrivacyEngine(settings)
    status = engine.get_status()
    return PrivacyStatusResponse(**status)
