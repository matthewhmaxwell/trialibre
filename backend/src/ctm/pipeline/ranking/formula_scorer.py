"""Deterministic formula-based scoring from criterion labels.

Produces a normalized [0, 1] matching score from criterion-level predictions.
"""

from __future__ import annotations

from ctm.config import RankingConfig
from ctm.models.matching import EligibilityLabel, MatchingResult


class FormulaScorer:
    """Compute a deterministic matching score from criterion labels.

    Score formula:
    - Count inclusion criteria met vs total
    - Penalize for unmet inclusion criteria
    - Penalize for triggered exclusion criteria
    - Normalize to [0, 1]
    """

    def __init__(self, config: RankingConfig) -> None:
        self._config = config

    def score(self, result: MatchingResult) -> float:
        """Compute normalized matching score from criterion results.

        Returns:
            Score in [0.0, 1.0] range.
        """
        eps = 1e-9

        # Inclusion analysis
        inc_met = sum(
            1 for r in result.inclusion_results
            if r.label == EligibilityLabel.INCLUDED
        )
        inc_not = sum(
            1 for r in result.inclusion_results
            if r.label == EligibilityLabel.NOT_INCLUDED
        )
        inc_noinfo = sum(
            1 for r in result.inclusion_results
            if r.label == EligibilityLabel.NOT_ENOUGH_INFO
        )
        inc_na = sum(
            1 for r in result.inclusion_results
            if r.label == EligibilityLabel.NOT_APPLICABLE
        )

        # Exclusion analysis
        exc_triggered = sum(
            1 for r in result.exclusion_results
            if r.label == EligibilityLabel.EXCLUDED
        )

        # Base score: proportion of inclusion criteria met
        denom = inc_met + inc_not + inc_noinfo + eps
        raw = inc_met / denom

        # Penalties
        if inc_not > 0:
            raw -= 1.0
        if exc_triggered > 0:
            raw -= 1.0

        # Normalize from [-2, 1] to [0, 1]
        normalized = (raw + 2.0) / 3.0

        # Clamp
        return max(0.0, min(1.0, normalized))
