"""Batch screening endpoints."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
router = APIRouter()

@router.post("/batch")
async def start_batch(request: Request):
    """Start a batch patient screening job."""
    return {"status": "not_implemented", "message": "Batch processing endpoint. Configure via full setup."}

@router.get("/batch/{job_id}")
async def get_batch_status(job_id: str):
    """Get batch job status."""
    raise HTTPException(404, f"Job {job_id} not found")
