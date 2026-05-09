"""Smoke tests for the printable match summary.

The print summary is the most consequential output of the system: it
gets attached to referrals and printed for charts. The AI-disclaimer
in the body is therefore non-negotiable — a clinician reading a
printed sheet has no other surface to learn that this is
decision-support output. This test pins the disclaimer's presence so
a future template refactor can't silently drop it.
"""

from __future__ import annotations

from ctm.models.matching import MatchStrength, TrialScore
from ctm.models.patient import PatientNote
from ctm.models.trial import ClinicalTrial
from ctm.reports.print_summary import generate_print_summary


def _patient() -> PatientNote:
    return PatientNote(
        patient_id="P-001",
        raw_text="45F with T2DM, HbA1c 8.2%, on metformin.",
        age=45,
        sex="Female",
        diagnoses=["Type 2 diabetes"],
    )


def _trial() -> ClinicalTrial:
    return ClinicalTrial(
        nct_id="NCT-001",
        brief_title="SGLT2 study",
        diseases=["Type 2 Diabetes"],
    )


def _score() -> TrialScore:
    return TrialScore(
        trial_id="NCT-001",
        trial_title="SGLT2 study",
        combined_score=0.8,
        strength=MatchStrength.STRONG,
        relevance_explanation="Trial is relevant to T2DM.",
        criteria_met=5,
        criteria_total=10,
    )


def test_summary_includes_ai_disclaimer():
    """If the disclaimer disappears, this fails — and someone has to
    explicitly defend the change in code review."""
    out = generate_print_summary(_patient(), _trial(), _score())
    lower = out.lower()
    assert "ai-generated" in lower
    assert "verify before clinical use" in lower
    # And the longer body explaining what "decision support" means:
    assert "decision support" in lower or "shortlist" in lower


def test_summary_runs_without_optional_data():
    """Make sure removing or adding the disclaimer didn't break the
    template's basic rendering when most fields are sparse."""
    minimal_score = TrialScore(
        trial_id="NCT-002",
        strength=MatchStrength.UNLIKELY,
    )
    out = generate_print_summary(_patient(), _trial(), minimal_score)
    # No exception, non-empty output, and the disclaimer is still there.
    assert "TRIALIBRE MATCH SUMMARY" in out
    assert "ai-generated" in out.lower()
