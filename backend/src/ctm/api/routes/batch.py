"""Batch screening endpoints."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ctm.models.patient import PatientNote
from ctm.pipeline.orchestrator import PipelineOrchestrator
from ctm.sandbox.loader import load_sample_protocols

router = APIRouter()

# In-memory job store
_jobs: dict[str, dict] = {}


class BatchPatient(BaseModel):
    patient_id: str
    text: str


class BatchRequest(BaseModel):
    patients: list[BatchPatient]
    max_trials: int = 20


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

    # Run matching for each patient
    trials = load_sample_protocols()
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
        except Exception as e:
            job["failed"] += 1
            job["results"].append({"patient_id": bp.patient_id, "error": str(e)})

    job["status"] = "completed"
    return job


@router.get("/batch/{job_id}")
async def get_batch_status(job_id: str):
    """Get batch job status."""
    if job_id not in _jobs:
        raise HTTPException(404, f"Job {job_id} not found")
    return _jobs[job_id]
