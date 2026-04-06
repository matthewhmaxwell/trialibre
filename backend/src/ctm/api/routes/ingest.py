"""Patient and trial data ingestion endpoints."""
from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request

from ctm.models.trial import ClinicalTrial

logger = logging.getLogger(__name__)

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


@router.post("/ingest/trial")
async def ingest_trial(
    request: Request,
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    title: str | None = Form(None),
    nct_id: str | None = Form(None),
):
    """Upload a single protocol document and extract eligibility criteria.

    Accepts PDF, DOCX, TXT files, or pasted text. Extracts inclusion/exclusion
    criteria using heuristic parsing and stores the trial for matching.
    """
    if not file and not text:
        raise HTTPException(400, "Provide either a file or text")

    trial_id = nct_id or f"UPLOAD-{uuid.uuid4().hex[:8]}"
    trial_title = title or ""
    source_format = "text"
    raw_text = ""

    if file:
        content = await file.read()
        filename = (file.filename or "").lower()
        source_format = filename.rsplit(".", 1)[-1] if "." in filename else "text"

        if filename.endswith(".pdf"):
            from ctm.ingest.pdf_ingestor import PdfIngestor
            raw_text = await PdfIngestor().extract_text(content)
            if not raw_text.strip():
                raise HTTPException(
                    422, "Could not extract text from this PDF. It may be image-based. Try pasting the text instead."
                )

        elif filename.endswith(".docx"):
            from ctm.ingest.docx_ingestor import DocxIngestor
            raw_text = await DocxIngestor().extract_text(content)

        elif filename.endswith((".json", ".jsonl", ".csv")):
            # Structured trial file — use existing parser
            from ctm.ingest.trial_ingestor import ingest_trial_file
            trials = await ingest_trial_file(content)
            if not trials:
                raise HTTPException(422, "No trials found in file")
            # Store all parsed trials
            custom = getattr(request.app.state, "custom_trials", {})
            results = []
            for t in trials:
                t.source_registry = "upload"
                custom[t.nct_id] = t
                results.append({
                    "nct_id": t.nct_id,
                    "brief_title": t.brief_title,
                    "inclusion_count": len(t.inclusion_criteria),
                    "exclusion_count": len(t.exclusion_criteria),
                    "extraction_method": "structured",
                    "source_format": source_format,
                    "warnings": [],
                })
            request.app.state.custom_trials = custom
            return {"trials": results, "count": len(results)}

        else:
            # Plain text file
            raw_text = content.decode("utf-8", errors="replace")

        if not trial_title and file.filename:
            trial_title = file.filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()

    elif text:
        raw_text = text
        source_format = "text"

    if not raw_text.strip():
        raise HTTPException(400, "No text content found")

    # Extract criteria from unstructured text
    from ctm.ingest.criteria_extractor import extract_criteria_from_protocol
    inclusion, exclusion, meta = extract_criteria_from_protocol(raw_text)

    if not trial_title:
        # Try to extract title from first line
        first_line = raw_text.strip().split("\n")[0].strip()
        if len(first_line) < 200:
            trial_title = first_line
        else:
            trial_title = f"Uploaded Protocol {trial_id}"

    # Build ClinicalTrial
    trial = ClinicalTrial(
        nct_id=trial_id,
        brief_title=trial_title,
        raw_inclusion_text="\n".join(c.text for c in inclusion),
        raw_exclusion_text="\n".join(c.text for c in exclusion),
        inclusion_criteria=inclusion,
        exclusion_criteria=exclusion,
        source_registry="upload",
        metadata={
            "extraction": meta,
            "original_text_length": len(raw_text),
        },
    )

    # Store in app state
    custom = getattr(request.app.state, "custom_trials", {})
    custom[trial.nct_id] = trial
    request.app.state.custom_trials = custom

    logger.info(f"Uploaded trial {trial_id}: {len(inclusion)} inc + {len(exclusion)} exc criteria")

    return {
        "nct_id": trial_id,
        "brief_title": trial_title,
        "inclusion_count": len(inclusion),
        "exclusion_count": len(exclusion),
        "extraction_method": meta["method"],
        "confidence": meta["confidence"],
        "source_format": source_format,
        "warnings": meta["warnings"],
    }


@router.post("/ingest/trials")
async def ingest_trials(request: Request, file: UploadFile = File(...)):
    """Upload a structured trial data file (JSON, JSONL, or CSV)."""
    content = await file.read()

    from ctm.ingest.trial_ingestor import ingest_trial_file
    trials = await ingest_trial_file(content)

    if not trials:
        raise HTTPException(422, "No trials found in file")

    custom = getattr(request.app.state, "custom_trials", {})
    for t in trials:
        t.source_registry = "upload"
        custom[t.nct_id] = t
    request.app.state.custom_trials = custom

    return {
        "status": "ingested",
        "count": len(trials),
        "trial_ids": [t.nct_id for t in trials],
    }
