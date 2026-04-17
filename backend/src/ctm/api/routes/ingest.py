"""Patient and trial data ingestion endpoints."""
from __future__ import annotations

import asyncio
import re
import uuid
import logging

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ctm.api.dependencies import get_db_session
from ctm.db.repositories import BatchJobRepository, TrialRepository
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
        raise HTTPException(
            413, f"File too large. Maximum size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
        )
    return content


@router.post("/ingest/patient")
async def ingest_patient(
    text: str | None = Form(None), file: UploadFile | None = File(None)
):
    """Ingest patient data from text or file upload."""
    if not text and not file:
        raise HTTPException(400, "Provide either text or a file")
    source = text or ""
    if file:
        content = await _read_upload(file)
        source = content.decode("utf-8", errors="replace")
    return {
        "status": "ingested",
        "text_length": len(source),
        "source_format": "text" if text else file.content_type,
    }


@router.post("/ingest/trial")
async def ingest_trial(
    request: Request,
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    title: str | None = Form(None),
    nct_id: str | None = Form(None),
    session: AsyncSession = Depends(get_db_session),
):
    """Upload a single protocol document and extract eligibility criteria."""
    if not file and not text:
        raise HTTPException(400, "Provide either a file or text")

    repo = TrialRepository(session)
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
                    422,
                    "Could not extract text from this PDF. It may be image-based. "
                    "Try pasting the text instead.",
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
                await repo.upsert(t)
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
            trial_title = (
                file.filename.rsplit(".", 1)[0]
                .replace("_", " ")
                .replace("-", " ")
                .title()
            )

    elif text:
        if len(text) > MAX_TEXT_LENGTH:
            raise HTTPException(
                413, f"Text too long. Maximum is {MAX_TEXT_LENGTH:,} characters."
            )
        raw_text = text
        source_format = "text"

    if not raw_text.strip():
        raise HTTPException(400, "No text content found")

    from ctm.ingest.criteria_extractor import extract_criteria_from_protocol
    inclusion, exclusion, meta = extract_criteria_from_protocol(raw_text)

    if not trial_title:
        first_line = raw_text.strip().split("\n")[0].strip()
        trial_title = first_line if len(first_line) < 200 else f"Uploaded Protocol {trial_id}"

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

    await repo.upsert(trial)
    logger.info(
        f"Uploaded trial {trial_id}: {len(inclusion)} inc + {len(exclusion)} exc criteria"
    )

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
async def ingest_trials(
    request: Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
):
    """Upload a structured trial data file (JSON, JSONL, or CSV)."""
    content = await _read_upload(file)

    from ctm.ingest.trial_ingestor import ingest_trial_file
    trials = await ingest_trial_file(content)

    if not trials:
        raise HTTPException(422, "No trials found in file")

    repo = TrialRepository(session)
    for t in trials:
        t.source_registry = "upload"
        await repo.upsert(t)

    return {
        "status": "ingested",
        "count": len(trials),
        "trial_ids": [t.nct_id for t in trials],
    }


async def _ctgov_curl_fallback(nct_id: str, client) -> ClinicalTrial | None:
    """Fallback: fetch from CT.gov via curl subprocess when httpx has SSL issues."""
    import asyncio
    import json as _json

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
async def import_from_ctgov(
    request: Request,
    nct_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Import a trial from ClinicalTrials.gov by NCT ID."""
    from ctm.data.registries.ctgov_client import CTGovClient

    nct_id = nct_id.strip().upper()
    if not nct_id.startswith("NCT"):
        nct_id = f"NCT{nct_id}"
    if not NCT_ID_PATTERN.match(nct_id):
        raise HTTPException(
            400,
            "Invalid NCT ID format. Expected NCT followed by 8 digits (e.g. NCT04560881).",
        )

    repo = TrialRepository(session)
    existing = await repo.get(nct_id)
    if existing is not None:
        return {
            "nct_id": existing.nct_id,
            "brief_title": existing.brief_title,
            "inclusion_count": len(existing.inclusion_criteria),
            "exclusion_count": len(existing.exclusion_criteria),
            "source": existing.source_registry,
            "already_loaded": True,
        }

    client = CTGovClient()
    trial = None
    try:
        trial = await client.get_trial(nct_id)
    except Exception as e:
        logger.warning(f"httpx failed for {nct_id}: {type(e).__name__}: {e}")
        try:
            trial = await _ctgov_curl_fallback(nct_id, client)
        except Exception as e2:
            raise HTTPException(502, f"Failed to reach ClinicalTrials.gov: {e2}")
    finally:
        await client.close()

    if trial is None:
        raise HTTPException(404, f"Trial {nct_id} not found on ClinicalTrials.gov")

    await repo.upsert(trial)

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


# ─────────────────────────────────────────────────────────────────
# Bulk ClinicalTrials.gov sync
# ─────────────────────────────────────────────────────────────────


class CTGovSyncRequest(BaseModel):
    """Parameters for a bulk CT.gov sync job."""

    condition: str | None = None
    intervention: str | None = None
    location: str | None = None
    status: list[str] | None = None
    phase: list[str] | None = None
    max_trials: int = Field(default=500, ge=1, le=10_000)
    page_size: int = Field(default=100, ge=10, le=1000)


@router.post("/ingest/ctgov-sync")
async def start_ctgov_sync(
    request: Request,
    body: CTGovSyncRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Start a background job that bulk-imports trials from ClinicalTrials.gov.

    Returns immediately with a job_id. Poll `/api/v1/ingest/ctgov/sync/{job_id}`
    for progress.

    The sync paginates through CT.gov results matching the search criteria
    and upserts each trial into the local database. Existing trials with
    the same NCT ID are updated.
    """
    if not any([body.condition, body.intervention, body.location, body.phase, body.status]):
        raise HTTPException(
            400,
            "Provide at least one filter (condition, intervention, location, phase, or status)."
        )

    job_id = str(uuid.uuid4())[:8]
    jobs = BatchJobRepository(session)
    await jobs.create(
        job_id=job_id,
        total=0,  # filled in by background task once first page arrives
        job_type="ctgov_sync",
        job_metadata=body.model_dump(),
    )
    # Commit the job record before launching the background task
    await session.commit()

    db = request.app.state.db
    asyncio.create_task(_run_ctgov_sync(db, job_id, body))

    return {
        "job_id": job_id,
        "status": "running",
        "message": "Sync started. Poll /api/v1/ingest/ctgov-sync/{job_id} for progress.",
    }


@router.get("/ingest/ctgov-sync/{job_id}")
async def get_ctgov_sync_status(
    job_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get the status of a running or completed CT.gov sync job."""
    jobs = BatchJobRepository(session)
    job = await jobs.get(job_id)
    if job is None:
        raise HTTPException(404, f"Sync job {job_id} not found")
    if job["job_type"] != "ctgov_sync":
        raise HTTPException(400, f"Job {job_id} is not a CT.gov sync job (it's a {job['job_type']} job)")
    return job


async def _run_ctgov_sync(db, job_id: str, body: CTGovSyncRequest) -> None:
    """Background task: paginate CT.gov, upsert each trial, update job state.

    Uses fresh DB sessions per page to avoid holding a connection for the
    duration of the sync. Failures on individual trials are recorded but
    don't stop the sync.
    """
    from ctm.data.registries.ctgov_client import CTGovClient

    client = CTGovClient()
    page_token: str | None = None
    completed = 0
    failed = 0
    failure_log: list[dict] = []
    total_announced: int | None = None

    try:
        while True:
            try:
                page = await client.search(
                    condition=body.condition,
                    intervention=body.intervention,
                    location=body.location,
                    status=body.status,
                    phase=body.phase,
                    page_size=body.page_size,
                    page_token=page_token,
                )
            except Exception as e:
                logger.error(f"CT.gov search failed during sync {job_id}: {e}")
                async with db.session() as s:
                    await BatchJobRepository(s).update(
                        job_id,
                        status="failed",
                        results=failure_log + [{"error": f"Search failed: {e}"}],
                    )
                return

            # On the first page, record the total (capped at max_trials)
            if total_announced is None:
                api_total = page.get("total", 0) or 0
                total_announced = min(api_total, body.max_trials)
                async with db.session() as s:
                    await BatchJobRepository(s).update(job_id, total=total_announced)

            # Upsert each trial in this page (within a single session)
            async with db.session() as s:
                trial_repo = TrialRepository(s)
                for trial in page["trials"]:
                    if completed + failed >= body.max_trials:
                        break
                    try:
                        await trial_repo.upsert(trial)
                        completed += 1
                    except Exception as e:
                        failed += 1
                        failure_log.append({
                            "nct_id": getattr(trial, "nct_id", "?"),
                            "error": f"{type(e).__name__}: {e}",
                        })

            # Persist progress after each page
            async with db.session() as s:
                await BatchJobRepository(s).update(
                    job_id,
                    completed=completed,
                    failed=failed,
                    results=failure_log,
                )

            page_token = page.get("next_page_token")
            if not page_token or completed + failed >= body.max_trials:
                break

        # Mark complete
        final_status = "completed" if failed == 0 else "partial_failure"
        async with db.session() as s:
            await BatchJobRepository(s).update(job_id, status=final_status)

    except (MemoryError, SystemExit, KeyboardInterrupt):
        raise
    except Exception as e:
        logger.exception(f"CT.gov sync {job_id} crashed")
        try:
            async with db.session() as s:
                await BatchJobRepository(s).update(
                    job_id,
                    status="failed",
                    results=failure_log + [{"error": f"{type(e).__name__}: {e}"}],
                )
        except Exception:
            logger.exception(f"Could not record final failure state for sync {job_id}")
    finally:
        await client.close()
