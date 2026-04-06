"""Tests for the evaluation framework."""

from ctm.evaluation.metrics import evaluate_ranking, aggregate_metrics, _dcg, _ndcg
from ctm.evaluation.ground_truth import GroundTruth, GroundTruthPair
from ctm.models.matching import TrialScore, MatchStrength


def _make_score(trial_id: str, strength: str, combined: float) -> TrialScore:
    return TrialScore(
        trial_id=trial_id,
        trial_title=f"Trial {trial_id}",
        matching_score=combined,
        relevance_score=combined,
        eligibility_score=combined,
        combined_score=combined,
        strength=MatchStrength(strength),
        relevance_explanation="test",
        eligibility_explanation="test",
        confidence=0.8,
        criteria_met=5,
        criteria_not_met=1,
        criteria_excluded=0,
        criteria_unknown=2,
        criteria_total=8,
    )


class TestMetrics:
    def test_dcg_basic(self):
        assert _dcg([3, 2, 0], 3) > 0
        assert _dcg([], 5) == 0.0

    def test_ndcg_perfect(self):
        scores = [3, 2, 1]
        assert _ndcg(scores, scores, 3) == 1.0

    def test_ndcg_worst(self):
        assert _ndcg([0, 0, 0], [3, 2, 1], 3) == 0.0

    def test_evaluate_ranking(self, ground_truth):
        predicted = [
            _make_score("SAMPLE-NCT-001", "strong", 0.92),
            _make_score("SAMPLE-NCT-002", "strong", 0.85),
            _make_score("SAMPLE-NCT-003", "possible", 0.60),
        ]
        result = evaluate_ranking("SAMPLE-001", predicted, ground_truth)
        assert result["precision_at_5"] >= 0
        assert result["strength_accuracy"] >= 0

    def test_aggregate_empty(self):
        m = aggregate_metrics([])
        assert m.total_patients == 0

    def test_aggregate_single(self, ground_truth):
        predicted = [
            _make_score("SAMPLE-NCT-001", "strong", 0.92),
            _make_score("SAMPLE-NCT-002", "strong", 0.85),
        ]
        per_patient = [evaluate_ranking("SAMPLE-001", predicted, ground_truth)]
        m = aggregate_metrics(per_patient)
        assert m.total_patients == 1
        assert m.precision_at_5 >= 0


class TestGroundTruth:
    def test_load(self, ground_truth):
        assert len(ground_truth.pairs) == 24
        assert "SAMPLE-001" in ground_truth.patient_ids
        assert "SAMPLE-NCT-001" in ground_truth.trial_ids

    def test_for_patient(self, ground_truth):
        pairs = ground_truth.for_patient("SAMPLE-001")
        assert len(pairs) == 2
        assert all(p.patient_id == "SAMPLE-001" for p in pairs)

    def test_for_trial(self, ground_truth):
        pairs = ground_truth.for_trial("SAMPLE-NCT-003")
        assert len(pairs) >= 1
