"""Settings management endpoints."""
from __future__ import annotations
from fastapi import APIRouter, Request
router = APIRouter()

@router.get("/settings")
async def get_settings(request: Request):
    s = request.app.state.settings
    return {
        "llm_provider": s.llm.provider.value,
        "llm_model": s.llm.model,
        "language": s.language,
        "sandbox_mode": s.sandbox.enabled,
        "privacy_level": s.privacy.level.value,
        "deid_mode": s.privacy.deid_mode.value,
    }
