"""Batch screening endpoints."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ctm.api.dependencies import get_db_session
from ctm.db.repositories import BatchJobRepository, TrialRepository
from ctm.models.patient import PatientNote
from ctm.pipeline.orchestrator import PipelineOrchestrator
from ctm.sandbox.loader import load_sample_protocols

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_BATCH_SIZE = 100


class BatchPatient(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=255)
    text: str = Field(..., min_length=10, max_length=500_000)


class BatchRequest(BaseModel):
    patients: list[BatchPatient] = Field(..., min_length=1, max_length=MAX_BATCH_SIZE)
    max_trials: int = Field(default=20, ge=1, le=100)


@router.post("/batch")
async def start_batch(
    request: Request,
    body: BatchRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Start a batch patient screening job (synchronous in this implementation)."""
    settings = request.app.state.settings
    llm = getattr(request.app.state, "llm", None)

    if llm is None and not settings.sandbox.enabled:
        settings.sandbox.enabled = True

    job_id = str(uuid.uuid4())[:8]
    jobs = BatchJobRepository(session)
    await jobs.create(job_id=job_id, total=len(body.patients))

    # Build trial corpus
    trials = load_sample_protocols()
    trial_repo = TrialRepository(session)
    persisted = await trial_repo.list_all()
    if persisted:
        trials = trials + persisted

    orchestrator = PipelineOrchestrator(settings, llm)

    completed = 0
    failed = 0
    results: list[dict] = []

    for bp in body.patients:
        try:
            patient = PatientNote(patient_id=bp.patient_id, raw_text=bp.text)
            ranking = await orchestrator.match_patient(
                patient, trials, max_trials=body.max_trials
            )
            results.append({
                "patient_id": bp.patient_id,
                "strong": len(ranking.strong_matches),
                "possible": len(ranking.possible_matches),
                "unlikely": len(ranking.unlikely_matches),
                "top_trial": ranking.scores[0].trial_title if ranking.scores else None,
            })
            completed += 1
        except (MemoryError, SystemExit, KeyboardInterrupt):
            raise
        except Exception as e:
            logger.error(
                f"Batch processing error for {bp.patient_id}: {type(e).__name__}: {e}"
            )
            failed += 1
            results.append({
                "patient_id": bp.patient_id,
                "error": f"{type(e).__name__}: {e}",
            })

    final_status = "completed" if failed == 0 else "partial_failure"
    return await jobs.update(
        job_id,
        status=final_status,
        completed=completed,
        failed=failed,
        results=results,
    )


@router.get("/batch/{job_id}")
async def get_batch_status(
    job_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get batch job status."""
    jobs = BatchJobRepository(session)
    job = await jobs.get(job_id)
    if job is None:
        raise HTTPException(404, f"Job {job_id} not found")
    return job
