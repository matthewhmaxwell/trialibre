"""Pipeline orchestrator: coordinates retrieval -> matching -> ranking.

The central coordinator that wires all pipeline stages together.
Supports both single-patient and batch matching with concurrent processing.
"""

from __future__ import annotations

import asyncio
import logging
import time

from ctm.config import Settings
from ctm.models.matching import MatchingResult, PatientTrialRanking, TrialScore
from ctm.models.patient import PatientNote
from ctm.models.trial import ClinicalTrial
from ctm.pipeline.matching.criterion_matcher import CriterionMatcher
from ctm.pipeline.matching.patient_preprocessor import preprocess_patient
from ctm.pipeline.ranking.combined_ranker import CombinedRanker
from ctm.pipeline.ranking.formula_scorer import FormulaScorer
from ctm.pipeline.ranking.llm_aggregator import LLMAggregator
from ctm.providers.base import LLMProvider
from ctm.sandbox.mock_matcher import SandboxMatcher

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrates the three-stage matching pipeline.

    Stage 1: Retrieval - find candidate trials (BM25 + optional dense)
    Stage 2: Matching - criterion-by-criterion LLM evaluation
    Stage 3: Ranking - score aggregation and strength assignment
    """

    def __init__(self, settings: Settings, llm: LLMProvider | None = None) -> None:
        self._settings = settings
        self._llm = llm

        if settings.sandbox.enabled:
            self._sandbox = SandboxMatcher()
        else:
            self._sandbox = None

        if llm:
            self._matcher = CriterionMatcher(llm, settings.matching)
            self._aggregator = LLMAggregator(llm, settings.ranking)

        self._formula = FormulaScorer(settings.ranking)
        self._ranker = CombinedRanker(settings.ranking)

    async def match_patient(
        self,
        patient: PatientNote,
        trials: list[ClinicalTrial],
        max_trials: int = 50,
        on_progress: callable | None = None,
    ) -> PatientTrialRanking:
        """Run the full matching pipeline for a single patient.

        Args:
            patient: Patient note to match.
            trials: Candidate trials (from retrieval or manual list).
            max_trials: Maximum trials to evaluate.
            on_progress: Optional callback(completed, total) for progress.

        Returns:
            Ranked results with scores and match strengths.
        """
        # Sandbox mode: return precomputed results
        if self._sandbox:
            return await self._sandbox.match_patient(patient, trials, max_trials)

        if not self._llm:
            raise RuntimeError("No LLM provider configured. Set up an AI service or use sandbox mode.")

        # Preprocess patient
        patient = preprocess_patient(patient, self._settings.matching)

        # Limit trials
        candidates = trials[:max_trials]

        # Stage 2: Match (concurrent with semaphore)
        t_match = time.monotonic()
        matching_results = await self._match_concurrently(
            patient, candidates, on_progress
        )
        match_time = (time.monotonic() - t_match) * 1000

        # Stage 3: Rank
        t_rank = time.monotonic()
        scores = await self._rank_results(patient, candidates, matching_results)
        rank_time = (time.monotonic() - t_rank) * 1000

        # Sort
        ranked = self._ranker.rank(scores)

        return PatientTrialRanking(
            patient_id=patient.patient_id,
            scores=ranked,
            total_trials_screened=len(candidates),
            matching_time_ms=match_time,
            ranking_time_ms=rank_time,
        )

    async def _match_concurrently(
        self,
        patient: PatientNote,
        trials: list[ClinicalTrial],
        on_progress: callable | None = None,
    ) -> dict[str, MatchingResult]:
        """Match patient against multiple trials concurrently."""
        semaphore = asyncio.Semaphore(self._settings.matching.concurrency)
        results: dict[str, MatchingResult] = {}
        completed = 0

        async def match_one(trial: ClinicalTrial) -> None:
            nonlocal completed
            async with semaphore:
                try:
                    result = await self._matcher.match(patient, trial)
                    results[trial.nct_id] = result
                except Exception as e:
                    logger.error(f"Matching failed for {trial.nct_id}: {e}")

                completed += 1
                if on_progress:
                    on_progress(completed, len(trials))

        await asyncio.gather(*[match_one(t) for t in trials])
        return results

    async def _rank_results(
        self,
        patient: PatientNote,
        trials: list[ClinicalTrial],
        matching_results: dict[str, MatchingResult],
    ) -> list[TrialScore]:
        """Score and rank all matching results."""
        scores = []

        for trial in trials:
            result = matching_results.get(trial.nct_id)
            if result is None:
                continue

            # Formula score
            formula_score = self._formula.score(result)

            # LLM aggregation
            agg_scores = await self._aggregator.aggregate(patient, trial, result)

            # Combined score
            trial_score = self._ranker.score(
                result, formula_score, agg_scores, trial.brief_title
            )
            scores.append(trial_score)

        return scores
