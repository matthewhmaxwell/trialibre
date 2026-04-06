"""Settings management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class SettingsUpdate(BaseModel):
    llm_provider: str | None = None
    llm_model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    language: str | None = None
    sandbox_mode: bool | None = None
    privacy_level: str | None = None
    deid_mode: str | None = None


@router.get("/settings")
async def get_settings(request: Request):
    s = request.app.state.settings
    return {
        "llm_provider": s.llm.provider.value,
        "llm_model": s.llm.model,
        "api_key": "",  # Never return the actual key
        "base_url": getattr(s.llm, "base_url", ""),
        "language": s.language,
        "sandbox_mode": s.sandbox.enabled,
        "privacy_level": s.privacy.level.value,
        "deid_mode": s.privacy.deid_mode.value,
    }


@router.put("/settings")
async def update_settings(request: Request, body: SettingsUpdate):
    """Update settings. Changes are applied in-memory (not persisted to disk)."""
    s = request.app.state.settings

    if body.llm_provider is not None:
        from ctm.config import LLMProviderType
        try:
            s.llm.provider = LLMProviderType(body.llm_provider)
        except ValueError:
            s.llm.provider = body.llm_provider
    if body.llm_model is not None:
        s.llm.model = body.llm_model
    if body.api_key is not None and body.api_key:
        s.llm.api_key = body.api_key
    if body.base_url is not None:
        s.llm.base_url = body.base_url
    if body.language is not None:
        s.language = body.language
    if body.sandbox_mode is not None:
        s.sandbox.enabled = body.sandbox_mode

    return {"status": "saved"}
