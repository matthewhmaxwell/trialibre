"""Clinical trial data models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TrialSite(BaseModel):
    """A clinical trial site/location."""

    facility: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    zip_code: str = ""
    latitude: float | None = None
    longitude: float | None = None
    contact_name: str = ""
    contact_phone: str = ""
    contact_email: str = ""


class EligibilityCriteria(BaseModel):
    """A single parsed eligibility criterion."""

    index: int
    text: str
    category: str  # "inclusion" or "exclusion"
    plain_language: str = ""  # LLM-generated plain-language gloss


class ClinicalTrial(BaseModel):
    """Structured representation of a clinical trial."""

    nct_id: str
    brief_title: str
    official_title: str = ""
    diseases: list[str] = []
    interventions: list[str] = []
    brief_summary: str = ""
    detailed_description: str = ""
    phase: str | None = None
    status: str | None = None
    enrollment: int | None = None
    sponsor: str = ""
    start_date: str | None = None
    completion_date: str | None = None

    # Eligibility
    inclusion_criteria: list[EligibilityCriteria] = []
    exclusion_criteria: list[EligibilityCriteria] = []
    raw_inclusion_text: str = ""
    raw_exclusion_text: str = ""
    min_age: str | None = None
    max_age: str | None = None
    sex: str | None = None  # ALL, MALE, FEMALE

    # Sites
    sites: list[TrialSite] = []

    # Source tracking
    source_registry: str = ""  # ctgov, who_ictrp, eu_ctis, isrctn, upload
    source_url: str = ""

    # Additional metadata
    metadata: dict[str, Any] = {}

    @property
    def all_criteria(self) -> list[EligibilityCriteria]:
        """All eligibility criteria (inclusion + exclusion)."""
        return self.inclusion_criteria + self.exclusion_criteria

    @property
    def criteria_count(self) -> int:
        """Total number of eligibility criteria."""
        return len(self.inclusion_criteria) + len(self.exclusion_criteria)
