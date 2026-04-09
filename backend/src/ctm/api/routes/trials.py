"""Trial browsing and management endpoints."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from ctm.sandbox.loader import load_sample_protocols, get_sample_trial
router = APIRouter()


@router.get("/trials")
async def list_trials(
    request: Request,
    condition: str | None = None,
    phase: str | None = None,
    offset: int = 0,
    limit: int = 50,
):
    """List available trials (sandbox + uploaded) with pagination."""
    if limit > 200:
        limit = 200
    if offset < 0:
        offset = 0

    trials = load_sample_protocols()

    # Merge in custom uploaded trials
    custom = getattr(request.app.state, "custom_trials", {})
    if custom:
        trials = trials + list(custom.values())

    if condition:
        trials = [t for t in trials if any(condition.lower() in d.lower() for d in t.diseases)]
    if phase:
        trials = [t for t in trials if t.phase and phase.lower() in t.phase.lower()]

    total = len(trials)
    page = trials[offset:offset + limit]

    return {
        "trials": [
            {
                "nct_id": t.nct_id,
                "brief_title": t.brief_title,
                "diseases": t.diseases,
                "phase": t.phase,
                "status": t.status,
                "source": t.source_registry or "sandbox",
                "inclusion_count": len(t.inclusion_criteria),
                "exclusion_count": len(t.exclusion_criteria),
            }
            for t in page
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/trials/{nct_id}")
async def get_trial(request: Request, nct_id: str):
    """Get trial details."""
    # Check custom trials first
    custom = getattr(request.app.state, "custom_trials", {})
    if nct_id in custom:
        return custom[nct_id].model_dump()

    trial = get_sample_trial(nct_id)
    if not trial:
        raise HTTPException(404, f"Trial {nct_id} not found")
    return trial.model_dump()


@router.delete("/trials/{nct_id}")
async def delete_trial(request: Request, nct_id: str):
    """Delete an uploaded trial. Only uploaded trials can be deleted."""
    custom = getattr(request.app.state, "custom_trials", {})
    if nct_id not in custom:
        # Check if it's a sandbox trial
        trial = get_sample_trial(nct_id)
        if trial:
            raise HTTPException(403, "Cannot delete sandbox trials")
        raise HTTPException(404, f"Trial {nct_id} not found")

    del custom[nct_id]
    request.app.state.custom_trials = custom
    return {"status": "deleted", "nct_id": nct_id}
