"""Patient matching endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ctm.api.dependencies import get_db_session
from ctm.db.repositories import TrialRepository
from ctm.models.api import MatchRequest, MatchResponse
from ctm.models.patient import PatientNote
from ctm.pipeline.orchestrator import PipelineOrchestrator
from ctm.sandbox.loader import load_sample_protocols

router = APIRouter()


@router.post("/match", response_model=MatchResponse)
async def match_patient(
    request: Request,
    body: MatchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> MatchResponse:
    """Match a patient against clinical trials."""
    settings = request.app.state.settings
    llm = getattr(request.app.state, "llm", None)

    # Auto-enable sandbox if no LLM is configured
    if llm is None and not settings.sandbox.enabled:
        settings.sandbox.enabled = True

    if not body.patient_text:
        raise HTTPException(400, "Patient text is required")

    patient = PatientNote(
        patient_id=body.patient_id or "anonymous",
        raw_text=body.patient_text,
    )

    # Build trial corpus: sandbox + persisted custom trials
    trials = load_sample_protocols()
    repo = TrialRepository(session)
    persisted = await repo.list_all()
    if persisted:
        trials = trials + persisted

    # Filter to specific trial IDs if requested
    if body.trial_ids:
        id_set = set(body.trial_ids)
        trials = [t for t in trials if t.nct_id in id_set]
        if not trials:
            raise HTTPException(404, "None of the specified trial IDs were found")

    orchestrator = PipelineOrchestrator(settings, llm)
    ranking = await orchestrator.match_patient(
        patient, trials, max_trials=body.max_trials
    )

    # Build user-visible warnings
    warnings: list[str] = []
    if settings.sandbox.enabled:
        warnings.append(
            "These results were generated in sandbox mode from pre-computed sample "
            "data, not by calling a live AI model. Configure an AI provider for "
            "real matching."
        )
    if body.trial_ids and len(ranking.scores) < len(body.trial_ids):
        missing = len(body.trial_ids) - len(ranking.scores)
        warnings.append(
            f"{missing} of {len(body.trial_ids)} requested trials were not found "
            "and were skipped."
        )

    return MatchResponse(
        patient_id=ranking.patient_id,
        rankings=ranking.scores,
        strong_count=len(ranking.strong_matches),
        possible_count=len(ranking.possible_matches),
        unlikely_count=len(ranking.unlikely_matches),
        total_trials_screened=ranking.total_trials_screened,
        retrieval_time_ms=ranking.retrieval_time_ms,
        matching_time_ms=ranking.matching_time_ms,
        ranking_time_ms=ranking.ranking_time_ms,
        sandbox_mode=settings.sandbox.enabled,
        warnings=warnings,
    )
