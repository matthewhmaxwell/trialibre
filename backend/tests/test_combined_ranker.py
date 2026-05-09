"""Tests for `CombinedRanker` strength bucketing.

Pins the eligibility-veto rule that emerged from the 24-pair Anthropic
Sonnet evaluation: a confident negative eligibility signal should produce
UNLIKELY regardless of relevance, mirroring the clinical reality that a
hard contraindication (age out of range, prior excluded therapy, etc.)
ends the analysis.
"""

from __future__ import annotations

from ctm.config import RankingConfig
from ctm.models.matching import (
    CriterionResult,
    EligibilityLabel,
    MatchingResult,
    MatchStrength,
)
from ctm.pipeline.ranking.combined_ranker import CombinedRanker


def _ranker(**overrides) -> CombinedRanker:
    cfg = RankingConfig(**overrides)
    return CombinedRanker(cfg)


def _result() -> MatchingResult:
    # Empty result; ranker only reads counts via the score() method's args,
    # not from this object directly for strength determination.
    return MatchingResult(patient_id="P", trial_id="T")


def test_high_relevance_high_eligibility_returns_strong():
    ranker = _ranker()
    score = ranker.score(
        _result(),
        formula_score=0.8,
        agg_scores={"relevance_score": 0.9, "eligibility_score": 0.8},
    )
    assert score.strength == MatchStrength.STRONG


def test_low_relevance_low_eligibility_returns_unlikely():
    ranker = _ranker()
    score = ranker.score(
        _result(),
        formula_score=0.1,
        agg_scores={"relevance_score": 0.2, "eligibility_score": -0.3},
    )
    assert score.strength == MatchStrength.UNLIKELY


def test_definite_exclusion_vetoes_high_relevance_into_unlikely():
    """The bug the Anthropic eval surfaced: an 8-year-old in a 12-65 trial
    had relevance=0.95 and eligibility=-1.00 (model said 'definitively
    ineligible due to age'), but the combined score landed at 0.47 —
    above the POSSIBLE threshold. Clinically, this should be UNLIKELY
    regardless of how relevant the trial is."""
    ranker = _ranker()
    score = ranker.score(
        _result(),
        formula_score=0.5,
        agg_scores={"relevance_score": 0.95, "eligibility_score": -1.0},
    )
    assert score.strength == MatchStrength.UNLIKELY
    # Sanity: the unclamped combined is in the POSSIBLE band, so the veto
    # — not arithmetic — is what's producing UNLIKELY.
    assert 0.4 <= score.combined_score < 0.7


def test_borderline_eligibility_does_not_trigger_veto():
    """eligibility=-0.71 means 'leans ineligible but not maxed out' (e.g.
    'patient may not meet a criterion that wasn't explicitly recorded').
    Default threshold is -0.85, so a -0.71 should NOT clamp."""
    ranker = _ranker()
    score = ranker.score(
        _result(),
        formula_score=0.5,
        agg_scores={"relevance_score": 0.95, "eligibility_score": -0.71},
    )
    # combined ≈ 0.5*0.5 + 0.5*((0.95 + 0.145)/2) ≈ 0.524
    # → POSSIBLE band, no veto
    assert score.strength == MatchStrength.POSSIBLE


def test_veto_threshold_is_configurable():
    """Allow operators to tighten or loosen the veto without code change."""
    # Disable veto entirely:
    ranker = _ranker(hard_exclusion_threshold=-1.5)
    score = ranker.score(
        _result(),
        formula_score=0.5,
        agg_scores={"relevance_score": 0.95, "eligibility_score": -1.0},
    )
    # Veto disabled → falls back to threshold-based bucketing.
    assert score.strength == MatchStrength.POSSIBLE


def test_eligibility_score_passed_through_untouched():
    """The veto changes strength only — the raw score must still surface
    so callers can render the underlying clinical signal."""
    ranker = _ranker()
    score = ranker.score(
        _result(),
        formula_score=0.5,
        agg_scores={"relevance_score": 0.95, "eligibility_score": -1.0},
    )
    assert score.eligibility_score == -1.0
    assert score.relevance_score == 0.95


def test_per_criterion_results_propagate_to_trial_score():
    """README promises 'criterion-level explainability' — that requires
    the per-criterion lists to actually reach TrialScore so the UI can
    render them. Pin it: the ranker must pass these through, not drop
    them after computing counts."""
    inclusion = [
        CriterionResult(
            criterion_index=0,
            criterion_text="Age 18-65",
            category="inclusion",
            reasoning="Patient is 45.",
            evidence_sentence_ids=[1, 6],
            label=EligibilityLabel.INCLUDED,
        ),
        CriterionResult(
            criterion_index=1,
            criterion_text="HbA1c >= 7.5%",
            category="inclusion",
            reasoning="HbA1c is 8.2%.",
            evidence_sentence_ids=[16],
            label=EligibilityLabel.INCLUDED,
        ),
    ]
    exclusion = [
        CriterionResult(
            criterion_index=0,
            criterion_text="Active malignancy",
            category="exclusion",
            reasoning="No malignancy in note.",
            evidence_sentence_ids=[],
            label=EligibilityLabel.NOT_ENOUGH_INFO,
        ),
    ]
    mr = MatchingResult(
        patient_id="P", trial_id="T",
        inclusion_results=inclusion, exclusion_results=exclusion,
    )

    ranker = _ranker()
    score = ranker.score(
        mr,
        formula_score=0.7,
        agg_scores={"relevance_score": 0.9, "eligibility_score": 0.8},
    )

    # Counts are still the summary path the card header uses.
    assert score.criteria_met == 2
    assert score.criteria_total == 3
    # And the full lists must come through for the expanded view.
    assert len(score.inclusion_results) == 2
    assert len(score.exclusion_results) == 1
    assert score.inclusion_results[0].criterion_text == "Age 18-65"
    assert score.inclusion_results[0].evidence_sentence_ids == [1, 6]
    assert score.exclusion_results[0].label == EligibilityLabel.NOT_ENOUGH_INFO
