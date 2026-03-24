"""Patient and trial data ingestion endpoints."""
from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
router = APIRouter()

@router.post("/ingest/patient")
async def ingest_patient(text: str | None = Form(None), file: UploadFile | None = File(None)):
    """Ingest patient data from text or file upload."""
    if not text and not file:
        raise HTTPException(400, "Provide either text or a file")
    source = text or ""
    if file:
        source = (await file.read()).decode("utf-8", errors="replace")
    return {"status": "ingested", "text_length": len(source), "source_format": "text" if text else file.content_type}

@router.post("/ingest/trials")
async def ingest_trials(file: UploadFile = File(...)):
    """Upload trial data file."""
    content = await file.read()
    return {"status": "ingested", "filename": file.filename, "size": len(content)}
