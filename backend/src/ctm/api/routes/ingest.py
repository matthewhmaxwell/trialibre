"""Patient and trial data ingestion endpoints."""
from __future__ import annotations

import re
import uuid
import logging

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request

from ctm.models.trial import ClinicalTrial

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_TEXT_LENGTH = 1_000_000  # 1M characters
NCT_ID_PATTERN = re.compile(r"^NCT\d{8}$")


async def _read_upload(file: UploadFile) -> bytes:
    """Read an uploaded file with size limit enforcement."""
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File too large. Maximum size is {MAX_UPLOAD_BYTES // (1024*1024)} MB.")
    return content


def _get_custom_trials(request: Request) -> dict:
    return getattr(request.app.state, "custom_trials", {})


def _store_trial(request: Request, trial: ClinicalTrial) -> None:
    """Thread-safe trial storage using the app-level lock."""
    lock = getattr(request.app.state, "custom_trials_lock", None)
    custom = _get_custom_trials(request)
    if lock:
        with lock:
            custom[trial.nct_id] = trial
            request.app.state.custom_trials = custom
    else:
        custom[trial.nct_id] = trial
        request.app.state.custom_trials = custom


@router.post("/ingest/patient")
async def ingest_patient(text: str | None = Form(None), file: UploadFile | None = File(None)):
    """Ingest patient data from text or file upload."""
    if not text and not file:
        raise HTTPException(400, "Provide either text or a file")
    source = text or ""
    if file:
        content = await _read_upload(file)
        source = content.decode("utf-8", errors="replace")
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
        content = await _read_upload(file)
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
            from ctm.ingest.trial_ingestor import ingest_trial_file
            trials = await ingest_trial_file(content)
            if not trials:
                raise HTTPException(422, "No trials found in file")
            results = []
            for t in trials:
                t.source_registry = "upload"
                _store_trial(request, t)
                results.append({
                    "nct_id": t.nct_id,
                    "brief_title": t.brief_title,
                    "inclusion_count": len(t.inclusion_criteria),
                    "exclusion_count": len(t.exclusion_criteria),
                    "extraction_method": "structured",
                    "source_format": source_format,
                    "warnings": [],
                })
            return {"trials": results, "count": len(results)}

        else:
            raw_text = content.decode("utf-8", errors="replace")

        if not trial_title and file.filename:
            trial_title = file.filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()

    elif text:
        if len(text) > MAX_TEXT_LENGTH:
            raise HTTPException(413, f"Text too long. Maximum is {MAX_TEXT_LENGTH:,} characters.")
        raw_text = text
        source_format = "text"

    if not raw_text.strip():
        raise HTTPException(400, "No text content found")

    from ctm.ingest.criteria_extractor import extract_criteria_from_protocol
    inclusion, exclusion, meta = extract_criteria_from_protocol(raw_text)

    if not trial_title:
        first_line = raw_text.strip().split("\n")[0].strip()
        if len(first_line) < 200:
            trial_title = first_line
        else:
            trial_title = f"Uploaded Protocol {trial_id}"

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

    _store_trial(request, trial)
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
    content = await _read_upload(file)

    from ctm.ingest.trial_ingestor import ingest_trial_file
    trials = await ingest_trial_file(content)

    if not trials:
        raise HTTPException(422, "No trials found in file")

    for t in trials:
        t.source_registry = "upload"
        _store_trial(request, t)

    return {
        "status": "ingested",
        "count": len(trials),
        "trial_ids": [t.nct_id for t in trials],
    }


async def _ctgov_curl_fallback(nct_id: str, client: "CTGovClient") -> "ClinicalTrial | None":
    """Fallback: fetch from CT.gov via curl subprocess when httpx has SSL issues."""
    import asyncio
    import json as _json

    # nct_id is already validated by caller — safe for subprocess
    proc = await asyncio.create_subprocess_exec(
        "curl", "-s", "--max-time", "30",
        f"https://clinicaltrials.gov/api/v2/studies/{nct_id}",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode != 0 or not stdout:
        return None
    try:
        data = _json.loads(stdout.decode())
    except (ValueError, UnicodeDecodeError):
        return None
    if "protocolSection" not in data:
        return None
    return client._parse_study(data)


@router.post("/ingest/ctgov/{nct_id}")
async def import_from_ctgov(request: Request, nct_id: str):
    """Import a trial from ClinicalTrials.gov by NCT ID."""
    from ctm.data.registries.ctgov_client import CTGovClient

    # Strict NCT ID validation
    nct_id = nct_id.strip().upper()
    if not nct_id.startswith("NCT"):
        nct_id = f"NCT{nct_id}"
    if not NCT_ID_PATTERN.match(nct_id):
        raise HTTPException(400, "Invalid NCT ID format. Expected NCT followed by 8 digits (e.g. NCT04560881).")

    # Check if already loaded
    custom = _get_custom_trials(request)
    if nct_id in custom:
        t = custom[nct_id]
        return {
            "nct_id": t.nct_id,
            "brief_title": t.brief_title,
            "inclusion_count": len(t.inclusion_criteria),
            "exclusion_count": len(t.exclusion_criteria),
            "source": t.source_registry,
            "already_loaded": True,
        }

    client = CTGovClient()
    trial = None
    try:
        trial = await client.get_trial(nct_id)
    except (Exception,) as e:
        logger.warning(f"httpx failed for {nct_id}: {type(e).__name__}: {e}")
        try:
            trial = await _ctgov_curl_fallback(nct_id, client)
        except Exception as e2:
            raise HTTPException(502, f"Failed to reach ClinicalTrials.gov: {e2}")
    finally:
        await client.close()

    if trial is None:
        raise HTTPException(404, f"Trial {nct_id} not found on ClinicalTrials.gov")

    _store_trial(request, trial)

    return {
        "nct_id": trial.nct_id,
        "brief_title": trial.brief_title,
        "inclusion_count": len(trial.inclusion_criteria),
        "exclusion_count": len(trial.exclusion_criteria),
        "diseases": trial.diseases,
        "phase": trial.phase,
        "sponsor": trial.sponsor,
        "sites_count": len(trial.sites),
        "source": "ctgov",
        "already_loaded": False,
    }
