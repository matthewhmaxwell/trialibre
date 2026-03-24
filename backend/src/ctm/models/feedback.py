"""Coordinator feedback models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class FeedbackType(str, Enum):
    MATCH_CORRECT = "match_correct"
    MATCH_INCORRECT = "match_incorrect"
    CRITERION_OVERRIDE = "criterion_override"
    ENROLLMENT_OUTCOME = "enrollment_outcome"


class EnrollmentOutcome(str, Enum):
    ENROLLED = "enrolled"
    SCREEN_FAILURE = "screen_failure"
    PATIENT_DECLINED = "patient_declined"
    LOST_TO_FOLLOWUP = "lost_to_followup"
    OTHER = "other"


class CoordinatorFeedback(BaseModel):
    """Feedback from a coordinator on a match result."""

    feedback_id: str
    patient_id: str
    trial_id: str
    type: FeedbackType
    coordinator: str = ""
    notes: str = ""
    outcome: EnrollmentOutcome | None = None
    criterion_index: int | None = None
    corrected_label: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
