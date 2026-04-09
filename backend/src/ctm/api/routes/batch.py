"""Batch screening endpoints."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ctm.models.patient import PatientNote
from ctm.pipeline.orchestrator import PipelineOrchestrator
from ctm.sandbox.loader import load_sample_protocols

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory job store
_jobs: dict[str, dict] = {}

MAX_BATCH_SIZE = 100


class BatchPatient(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=255)
    text: str = Field(..., min_length=10, max_length=500_000)


class BatchRequest(BaseModel):
    patients: list[BatchPatient] = Field(..., min_length=1, max_length=MAX_BATCH_SIZE)
    max_trials: int = Field(default=20, ge=1, le=100)


@router.post("/batch")
async def start_batch(request: Request, body: BatchRequest):
    """Start a batch patient screening job."""
    settings = request.app.state.settings
    llm = getattr(request.app.state, "llm", None)

    if llm is None and not settings.sandbox.enabled:
        settings.sandbox.enabled = True

    job_id = str(uuid.uuid4())[:8]
    job = {
        "job_id": job_id,
        "status": "running",
        "total": len(body.patients),
        "completed": 0,
        "failed": 0,
        "results": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _jobs[job_id] = job

    # Merge sandbox + custom trials
    trials = load_sample_protocols()
    custom = getattr(request.app.state, "custom_trials", {})
    if custom:
        trials = trials + list(custom.values())

    orchestrator = PipelineOrchestrator(settings, llm)

    for bp in body.patients:
        try:
            patient = PatientNote(patient_id=bp.patient_id, raw_text=bp.text)
            ranking = await orchestrator.match_patient(patient, trials, max_trials=body.max_trials)
            job["results"].append({
                "patient_id": bp.patient_id,
                "strong": len(ranking.strong_matches),
                "possible": len(ranking.possible_matches),
                "unlikely": len(ranking.unlikely_matches),
                "top_trial": ranking.scores[0].trial_title if ranking.scores else None,
            })
            job["completed"] += 1
        except (MemoryError, SystemExit, KeyboardInterrupt):
            raise  # Never catch fatal errors
        except Exception as e:
            logger.error(f"Batch processing error for {bp.patient_id}: {type(e).__name__}: {e}")
            job["failed"] += 1
            job["results"].append({"patient_id": bp.patient_id, "error": f"{type(e).__name__}: {e}"})

    job["status"] = "completed" if job["failed"] == 0 else "partial_failure"
    return job


@router.get("/batch/{job_id}")
async def get_batch_status(job_id: str):
    """Get batch job status."""
    if job_id not in _jobs:
        raise HTTPException(404, f"Job {job_id} not found")
    return _jobs[job_id]
