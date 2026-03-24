"""Patient data models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class PatientSentence(BaseModel):
    """A numbered sentence from a patient note."""

    id: int
    text: str


class PatientNote(BaseModel):
    """Structured representation of a patient's clinical information."""

    patient_id: str
    raw_text: str
    sentences: list[PatientSentence] = []
    language: str = "en"
    source_format: str = "text"  # text, pdf, docx, fhir, csv, image
    metadata: dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Structured fields (extracted from raw text or provided directly)
    age: int | None = None
    sex: str | None = None
    diagnoses: list[str] = []
    medications: list[str] = []
    lab_values: dict[str, str] = {}
    medical_history: list[str] = []

    def to_numbered_text(self) -> str:
        """Format as numbered sentences for LLM prompts."""
        return "\n".join(f"{s.id}. {s.text}" for s in self.sentences)

    @property
    def has_structured_data(self) -> bool:
        """Check if structured fields have been populated."""
        return bool(self.diagnoses or self.medications or self.lab_values)
