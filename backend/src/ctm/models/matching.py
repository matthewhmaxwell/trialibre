"""Matching result data models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EligibilityLabel(str, Enum):
    """Criterion-level eligibility labels."""

    INCLUDED = "included"
    NOT_INCLUDED = "not included"
    EXCLUDED = "excluded"
    NOT_EXCLUDED = "not excluded"
    NOT_APPLICABLE = "not applicable"
    NOT_ENOUGH_INFO = "not enough information"


class MatchStrength(str, Enum):
    """User-facing match strength (semantic, not numeric)."""

    STRONG = "strong"
    POSSIBLE = "possible"
    UNLIKELY = "unlikely"


class CriterionResult(BaseModel):
    """Result of evaluating a single eligibility criterion against a patient."""

    criterion_index: int
    criterion_text: str
    category: str  # "inclusion" or "exclusion"
    reasoning: str  # LLM reasoning
    plain_reasoning: str = ""  # Plain-language explanation for UI
    evidence_sentence_ids: list[int] = []
    label: EligibilityLabel
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class MatchingResult(BaseModel):
    """Complete matching result for a patient-trial pair."""

    patient_id: str
    trial_id: str
    inclusion_results: list[CriterionResult] = []
    exclusion_results: list[CriterionResult] = []
    prompt_version: str = ""  # For audit trail
    model_used: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def all_results(self) -> list[CriterionResult]:
        return self.inclusion_results + self.exclusion_results

    @property
    def met_count(self) -> int:
        """Number of inclusion criteria met."""
        return sum(
            1 for r in self.inclusion_results if r.label == EligibilityLabel.INCLUDED
        )

    @property
    def not_met_count(self) -> int:
        """Number of inclusion criteria not met."""
        return sum(
            1 for r in self.inclusion_results if r.label == EligibilityLabel.NOT_INCLUDED
        )

    @property
    def excluded_count(self) -> int:
        """Number of exclusion criteria triggered."""
        return sum(
            1 for r in self.exclusion_results if r.label == EligibilityLabel.EXCLUDED
        )

    @property
    def unknown_count(self) -> int:
        """Number of criteria with insufficient information."""
        return sum(
            1 for r in self.all_results if r.label == EligibilityLabel.NOT_ENOUGH_INFO
        )


class TrialScore(BaseModel):
    """Scored and ranked trial for a patient."""

    trial_id: str
    trial_title: str = ""
    matching_score: float = Field(ge=0.0, le=1.0, default=0.0)
    relevance_score: float = Field(ge=0.0, le=1.0, default=0.0)
    eligibility_score: float = Field(ge=-1.0, le=1.0, default=0.0)
    combined_score: float = Field(ge=0.0, le=1.0, default=0.0)
    strength: MatchStrength = MatchStrength.UNLIKELY
    relevance_explanation: str = ""
    eligibility_explanation: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)

    # Criterion summary for UI
    criteria_met: int = 0
    criteria_not_met: int = 0
    criteria_excluded: int = 0
    criteria_unknown: int = 0
    criteria_total: int = 0

    # Geographic info
    nearest_site_distance_km: float | None = None
    nearest_site_name: str = ""

    # Drug safety flags
    drug_interaction_flags: list[str] = []


class PatientTrialRanking(BaseModel):
    """Complete ranked results for a patient."""

    patient_id: str
    scores: list[TrialScore] = []  # Sorted descending by combined_score
    total_trials_screened: int = 0
    retrieval_time_ms: float = 0.0
    matching_time_ms: float = 0.0
    ranking_time_ms: float = 0.0
    metadata: dict[str, Any] = {}

    @property
    def strong_matches(self) -> list[TrialScore]:
        return [s for s in self.scores if s.strength == MatchStrength.STRONG]

    @property
    def possible_matches(self) -> list[TrialScore]:
        return [s for s in self.scores if s.strength == MatchStrength.POSSIBLE]

    @property
    def unlikely_matches(self) -> list[TrialScore]:
        return [s for s in self.scores if s.strength == MatchStrength.UNLIKELY]
