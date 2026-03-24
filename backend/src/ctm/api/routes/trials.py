"""Trial browsing and management endpoints."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from ctm.sandbox.loader import load_sample_protocols, get_sample_trial
router = APIRouter()

@router.get("/trials")
async def list_trials(request: Request, condition: str | None = None, phase: str | None = None):
    """List available trials."""
    trials = load_sample_protocols()
    if condition:
        trials = [t for t in trials if any(condition.lower() in d.lower() for d in t.diseases)]
    if phase:
        trials = [t for t in trials if t.phase and phase.lower() in t.phase.lower()]
    return [{"nct_id": t.nct_id, "brief_title": t.brief_title, "diseases": t.diseases, "phase": t.phase, "status": t.status} for t in trials]

@router.get("/trials/{nct_id}")
async def get_trial(nct_id: str):
    """Get trial details."""
    trial = get_sample_trial(nct_id)
    if not trial:
        raise HTTPException(404, f"Trial {nct_id} not found")
    return trial.model_dump()
