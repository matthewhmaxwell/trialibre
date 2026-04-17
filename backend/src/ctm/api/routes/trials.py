"""Trial browsing and management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ctm.api.dependencies import get_db_session
from ctm.db.repositories import TrialRepository
from ctm.sandbox.loader import get_sample_trial, load_sample_protocols

router = APIRouter()


@router.get("/trials")
async def list_trials(
    request: Request,
    condition: str | None = None,
    phase: str | None = None,
    offset: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session),
):
    """List available trials (sandbox + persisted) with pagination."""
    if limit > 200:
        limit = 200
    if offset < 0:
        offset = 0

    # Sandbox trials are loaded from disk
    trials = load_sample_protocols()

    # Persisted custom/imported trials from DB
    repo = TrialRepository(session)
    persisted = await repo.list_all()
    if persisted:
        trials = trials + persisted

    if condition:
        trials = [t for t in trials if any(condition.lower() in d.lower() for d in t.diseases)]
    if phase:
        trials = [t for t in trials if t.phase and phase.lower() in t.phase.lower()]

    total = len(trials)
    page = trials[offset : offset + limit]

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
async def get_trial(
    request: Request,
    nct_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get trial details."""
    repo = TrialRepository(session)
    trial = await repo.get(nct_id)
    if trial is not None:
        return trial.model_dump()

    sample = get_sample_trial(nct_id)
    if sample is None:
        raise HTTPException(404, f"Trial {nct_id} not found")
    return sample.model_dump()


@router.delete("/trials/{nct_id}")
async def delete_trial(
    request: Request,
    nct_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete an uploaded trial. Sandbox trials cannot be deleted."""
    repo = TrialRepository(session)
    deleted = await repo.delete(nct_id)
    if deleted:
        return {"status": "deleted", "nct_id": nct_id}

    # If not in DB, check if it's a sandbox trial (which can't be deleted)
    sample = get_sample_trial(nct_id)
    if sample is not None:
        raise HTTPException(403, "Cannot delete sandbox trials")

    raise HTTPException(404, f"Trial {nct_id} not found")
