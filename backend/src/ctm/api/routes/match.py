"""Patient matching endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ctm.models.api import MatchRequest, MatchResponse
from ctm.models.patient import PatientNote, PatientSentence
from ctm.pipeline.orchestrator import PipelineOrchestrator
from ctm.sandbox.loader import load_sample_protocols

router = APIRouter()


@router.post("/match", response_model=MatchResponse)
async def match_patient(request: Request, body: MatchRequest) -> MatchResponse:
    """Match a patient against clinical trials."""
    settings = request.app.state.settings
    llm = getattr(request.app.state, "llm", None)

    # Build patient note
    if not body.patient_text:
        raise HTTPException(400, "Patient text is required")

    patient = PatientNote(
        patient_id=body.patient_id or "anonymous",
        raw_text=body.patient_text,
    )

    # Get trials
    if settings.sandbox.enabled:
        trials = load_sample_protocols()
    else:
        # TODO: Load from trial index or registry search
        trials = load_sample_protocols()  # Fallback to sandbox data

    # Run pipeline
    orchestrator = PipelineOrchestrator(settings, llm)
    ranking = await orchestrator.match_patient(
        patient, trials, max_trials=body.max_trials
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
    )
