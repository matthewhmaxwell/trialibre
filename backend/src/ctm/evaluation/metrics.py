"""Evaluation metrics for clinical trial matching quality.

Implements standard IR metrics adapted to the trial matching domain:
- Precision@K, Recall@K
- NDCG (Normalized Discounted Cumulative Gain)
- Criterion-level accuracy, sensitivity, specificity
- Hallucination detection rate
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from collections import defaultdict

from ctm.evaluation.ground_truth import GroundTruth, GroundTruthPair
from ctm.models.matching import TrialScore


@dataclass
class MatchingMetrics:
    """Aggregated evaluation metrics for a matching run."""

    # Trial-level ranking
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    ndcg_at_5: float = 0.0
    ndcg_at_10: float = 0.0
    mean_reciprocal_rank: float = 0.0

    # Strength classification
    strength_accuracy: float = 0.0
    strength_precision: dict[str, float] = field(default_factory=dict)
    strength_recall: dict[str, float] = field(default_factory=dict)

    # Criterion-level (if available)
    criterion_accuracy: float = 0.0
    criterion_sensitivity: float = 0.0
    criterion_specificity: float = 0.0
    hallucination_rate: float = 0.0

    # Counts
    total_patients: int = 0
    total_pairs_evaluated: int = 0

    def summary(self) -> dict:
        return {
            "P@5": f"{self.precision_at_5:.3f}",
            "P@10": f"{self.precision_at_10:.3f}",
            "R@5": f"{self.recall_at_5:.3f}",
            "R@10": f"{self.recall_at_10:.3f}",
            "NDCG@5": f"{self.ndcg_at_5:.3f}",
            "NDCG@10": f"{self.ndcg_at_10:.3f}",
            "MRR": f"{self.mean_reciprocal_rank:.3f}",
            "Strength Acc": f"{self.strength_accuracy:.3f}",
            "Criterion Acc": f"{self.criterion_accuracy:.3f}",
            "Hallucination %": f"{self.hallucination_rate:.1%}",
            "Patients": self.total_patients,
            "Pairs": self.total_pairs_evaluated,
        }


def _relevance_score(expected_strength: str) -> int:
    """Convert expected strength to numeric relevance."""
    return {"strong": 3, "possible": 2, "unlikely": 0}.get(expected_strength, 0)


def _dcg(scores: list[int], k: int) -> float:
    """Discounted cumulative gain."""
    return sum(s / math.log2(i + 2) for i, s in enumerate(scores[:k]))


def _ndcg(predicted_scores: list[int], ideal_scores: list[int], k: int) -> float:
    """Normalized DCG."""
    dcg = _dcg(predicted_scores, k)
    ideal = _dcg(sorted(ideal_scores, reverse=True), k)
    return dcg / ideal if ideal > 0 else 0.0


def evaluate_ranking(
    patient_id: str,
    predicted: list[TrialScore],
    ground_truth: GroundTruth,
) -> dict:
    """Evaluate a single patient's ranking against ground truth.

    Returns per-patient metrics dict.
    """
    gt_pairs = ground_truth.for_patient(patient_id)
    if not gt_pairs:
        return {}

    gt_map: dict[str, GroundTruthPair] = {p.trial_id: p for p in gt_pairs}
    eligible_ids = {p.trial_id for p in gt_pairs if p.expected_label == "eligible"}

    # Build relevance vectors
    pred_trial_ids = [s.trial_id for s in predicted]
    pred_relevance = [_relevance_score(gt_map[tid].expected_strength) if tid in gt_map else 0 for tid in pred_trial_ids]
    ideal_relevance = [_relevance_score(p.expected_strength) for p in gt_pairs]

    # Precision / Recall @ K
    def precision_at_k(k: int) -> float:
        top_k = set(pred_trial_ids[:k])
        return len(top_k & eligible_ids) / k if k > 0 else 0.0

    def recall_at_k(k: int) -> float:
        top_k = set(pred_trial_ids[:k])
        return len(top_k & eligible_ids) / len(eligible_ids) if eligible_ids else 0.0

    # MRR
    mrr = 0.0
    for i, tid in enumerate(pred_trial_ids):
        if tid in eligible_ids:
            mrr = 1.0 / (i + 1)
            break

    # Strength accuracy
    correct = 0
    total = 0
    for score in predicted:
        if score.trial_id in gt_map:
            total += 1
            if score.strength == gt_map[score.trial_id].expected_strength:
                correct += 1

    return {
        "precision_at_5": precision_at_k(5),
        "precision_at_10": precision_at_k(10),
        "recall_at_5": recall_at_k(5),
        "recall_at_10": recall_at_k(10),
        "ndcg_at_5": _ndcg(pred_relevance, ideal_relevance, 5),
        "ndcg_at_10": _ndcg(pred_relevance, ideal_relevance, 10),
        "mrr": mrr,
        "strength_accuracy": correct / total if total > 0 else 0.0,
        "total_pairs": total,
    }


def aggregate_metrics(per_patient: list[dict]) -> MatchingMetrics:
    """Aggregate per-patient metrics into overall metrics."""
    if not per_patient:
        return MatchingMetrics()

    valid = [m for m in per_patient if m]
    if not valid:
        return MatchingMetrics()

    n = len(valid)
    return MatchingMetrics(
        precision_at_5=sum(m["precision_at_5"] for m in valid) / n,
        precision_at_10=sum(m["precision_at_10"] for m in valid) / n,
        recall_at_5=sum(m["recall_at_5"] for m in valid) / n,
        recall_at_10=sum(m["recall_at_10"] for m in valid) / n,
        ndcg_at_5=sum(m["ndcg_at_5"] for m in valid) / n,
        ndcg_at_10=sum(m["ndcg_at_10"] for m in valid) / n,
        mean_reciprocal_rank=sum(m["mrr"] for m in valid) / n,
        strength_accuracy=sum(m["strength_accuracy"] for m in valid) / n,
        total_patients=n,
        total_pairs_evaluated=sum(m["total_pairs"] for m in valid),
    )
