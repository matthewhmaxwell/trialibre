"""Combined ranker: merge formula + LLM scores, determine match strength."""

from __future__ import annotations

from ctm.config import RankingConfig
from ctm.models.matching import MatchStrength, MatchingResult, TrialScore


class CombinedRanker:
    """Combine formula-based and LLM-based scores into final ranking."""

    def __init__(self, config: RankingConfig) -> None:
        self._config = config

    def score(
        self,
        matching_result: MatchingResult,
        formula_score: float,
        agg_scores: dict,
        trial_title: str = "",
    ) -> TrialScore:
        """Combine scores and determine match strength.

        Args:
            matching_result: Criterion-level results.
            formula_score: Deterministic score from FormulaScorer [0, 1].
            agg_scores: Dict from LLMAggregator with relevance/eligibility scores.
            trial_title: Trial title for the result object.

        Returns:
            TrialScore with combined score and strength label.
        """
        relevance = agg_scores.get("relevance_score", 0.0)
        eligibility = agg_scores.get("eligibility_score", 0.0)

        # Combined score: weighted average of formula and aggregation
        # Normalize eligibility from [-1,1] to [0,1] for combination
        eligibility_normalized = (eligibility + 1.0) / 2.0

        agg_combined = (relevance + eligibility_normalized) / 2.0

        combined = (
            self._config.matching_weight * formula_score
            + self._config.aggregation_weight * agg_combined
        )

        # Clamp to [0, 1]
        combined = max(0.0, min(1.0, combined))

        # Determine strength
        strength = self._determine_strength(combined)

        return TrialScore(
            trial_id=matching_result.trial_id,
            trial_title=trial_title,
            matching_score=formula_score,
            relevance_score=relevance,
            eligibility_score=eligibility,
            combined_score=combined,
            strength=strength,
            relevance_explanation=agg_scores.get("relevance_explanation", ""),
            eligibility_explanation=agg_scores.get("eligibility_explanation", ""),
            criteria_met=matching_result.met_count,
            criteria_not_met=matching_result.not_met_count,
            criteria_excluded=matching_result.excluded_count,
            criteria_unknown=matching_result.unknown_count,
            criteria_total=len(matching_result.all_results),
        )

    def _determine_strength(self, combined_score: float) -> MatchStrength:
        """Map combined score to a semantic match strength."""
        if combined_score >= self._config.strong_match_threshold:
            return MatchStrength.STRONG
        elif combined_score >= self._config.possible_match_threshold:
            return MatchStrength.POSSIBLE
        else:
            return MatchStrength.UNLIKELY

    def rank(self, scores: list[TrialScore]) -> list[TrialScore]:
        """Sort trial scores by combined score descending."""
        return sorted(scores, key=lambda s: s.combined_score, reverse=True)
