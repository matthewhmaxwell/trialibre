"""API request and response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ctm.models.matching import MatchStrength, PatientTrialRanking, TrialScore
from ctm.models.trial import ClinicalTrial


class MatchRequest(BaseModel):
    """Request to match a patient to clinical trials."""

    patient_text: str | None = None
    patient_id: str | None = None
    trial_ids: list[str] | None = None  # Specific trials; None = search all
    max_trials: int = 50
    language: str | None = None  # Auto-detect if None
    include_reasoning: bool = True


class MatchResponse(BaseModel):
    """Response from a match request."""

    patient_id: str
    rankings: list[TrialScore]
    strong_count: int
    possible_count: int
    unlikely_count: int
    total_trials_screened: int
    retrieval_time_ms: float
    matching_time_ms: float
    ranking_time_ms: float
    sandbox_mode: bool = False


class BatchMatchRequest(BaseModel):
    """Request for batch patient screening."""

    patient_ids: list[str] | None = None  # From stored patients
    patient_file: str | None = None  # Path to uploaded file
    max_trials_per_patient: int = 20
    estimated_cost: bool = True  # Return cost estimate before running


class BatchCostEstimate(BaseModel):
    """Estimated cost for a batch run."""

    total_patients: int
    estimated_trials_per_patient: int
    estimated_llm_calls: int
    estimated_cost_usd: float
    estimated_duration_minutes: float


class IngestPatientRequest(BaseModel):
    """Request to ingest patient data."""

    text: str | None = None
    file_path: str | None = None
    language: str | None = None
    patient_id: str | None = None


class IngestPatientResponse(BaseModel):
    """Response from patient ingestion."""

    patient_id: str
    extracted_text: str
    language_detected: str
    source_format: str
    structured_data: dict[str, Any] = {}
    deid_applied: bool = False
    deid_flags: list[str] = []  # Items flagged for human review


class TrialSearchRequest(BaseModel):
    """Request to search trial registries."""

    condition: str | None = None
    intervention: str | None = None
    location: str | None = None
    phase: list[str] | None = None
    status: list[str] | None = None
    registries: list[str] | None = None  # Which registries to search
    page_size: int = 20
    page_token: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = ""
    llm_provider: str = ""
    llm_connected: bool = False
    sandbox_mode: bool = False
    trial_count: int = 0
    database_backend: str = ""


class PrivacyStatusResponse(BaseModel):
    """Current privacy status for the UI indicator."""

    label: str  # "Private", "Secure", "Stored"
    color: str  # "green", "blue", "yellow"
    details: list[str]  # Human-readable detail lines
    deid_active: bool
    processing_location: str
