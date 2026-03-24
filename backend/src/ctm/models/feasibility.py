"""Site feasibility models."""

from __future__ import annotations

from pydantic import BaseModel


class FeasibilityEstimate(BaseModel):
    """Estimated patient pool for a trial at a site."""

    trial_id: str
    trial_title: str = ""
    total_patients_screened: int = 0
    estimated_eligible: int = 0
    strong_matches: int = 0
    possible_matches: int = 0
    unlikely_matches: int = 0
    top_exclusion_reasons: list[str] = []
    top_missing_criteria: list[str] = []


class FeasibilityReport(BaseModel):
    """Complete feasibility report for a site."""

    site_name: str = ""
    condition: str = ""
    estimates: list[FeasibilityEstimate] = []
    total_patients_in_database: int = 0
    total_trials_analyzed: int = 0
