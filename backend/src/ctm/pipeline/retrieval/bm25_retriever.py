"""BM25 sparse retrieval for clinical trials.

Primary retrieval method. Works offline, memory-efficient.
Uses configurable field weights for title, conditions, and full text.
"""

from __future__ import annotations

import logging

import nltk
from rank_bm25 import BM25Okapi

from ctm.config import RetrievalConfig
from ctm.models.trial import ClinicalTrial

logger = logging.getLogger(__name__)


class BM25Retriever:
    """BM25-based sparse retrieval over clinical trial corpus."""

    def __init__(self, config: RetrievalConfig) -> None:
        self._config = config
        self._index: BM25Okapi | None = None
        self._trial_ids: list[str] = []
        self._trials_map: dict[str, ClinicalTrial] = {}

    def build_index(self, trials: list[ClinicalTrial]) -> None:
        """Build BM25 index from trials with weighted fields."""
        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            nltk.download("punkt_tab", quiet=True)

        corpus = []
        self._trial_ids = []
        self._trials_map = {}

        for trial in trials:
            tokens = self._tokenize_trial(trial)
            corpus.append(tokens)
            self._trial_ids.append(trial.nct_id)
            self._trials_map[trial.nct_id] = trial

        if corpus:
            self._index = BM25Okapi(corpus)
            logger.info(f"BM25 index built with {len(corpus)} trials")
        else:
            logger.warning("No trials to index")

    def search(self, query: str, top_n: int | None = None) -> list[tuple[str, float]]:
        """Search the index and return ranked trial IDs with scores.

        Args:
            query: Search query text.
            top_n: Number of results. Defaults to config.top_n.

        Returns:
            List of (nct_id, score) tuples, sorted by score descending.
        """
        if self._index is None:
            return []

        n = top_n or self._config.top_n
        tokens = nltk.word_tokenize(query.lower())
        scores = self._index.get_scores(tokens)

        # Get top N indices
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:n]

        return [
            (self._trial_ids[idx], float(score))
            for idx, score in ranked
            if score > 0
        ]

    def search_multi(self, queries: list[str], top_n: int = 2000) -> dict[str, float]:
        """Search with multiple queries, accumulating scores.

        Earlier queries (higher priority) are weighted more.

        Returns:
            {nct_id: accumulated_score}
        """
        accumulated: dict[str, float] = {}

        for priority, query in enumerate(queries):
            weight = 1.0 / (priority + 1)  # Priority decay
            results = self.search(query, top_n=top_n)

            for nct_id, score in results:
                accumulated[nct_id] = accumulated.get(nct_id, 0.0) + score * weight

        return accumulated

    def get_trial(self, nct_id: str) -> ClinicalTrial | None:
        """Get a trial by NCT ID from the indexed corpus."""
        return self._trials_map.get(nct_id)

    def _tokenize_trial(self, trial: ClinicalTrial) -> list[str]:
        """Tokenize a trial with weighted fields."""
        tokens: list[str] = []

        # Title (highest weight)
        title_weight = int(self._config.bm25_title_weight)
        title_tokens = nltk.word_tokenize(trial.brief_title.lower())
        tokens.extend(title_tokens * title_weight)

        # Conditions (medium weight)
        cond_weight = int(self._config.bm25_condition_weight)
        for disease in trial.diseases:
            cond_tokens = nltk.word_tokenize(disease.lower())
            tokens.extend(cond_tokens * cond_weight)

        # Full text (base weight)
        text_weight = int(self._config.bm25_text_weight)
        full_text = f"{trial.brief_summary} {trial.raw_inclusion_text} {trial.raw_exclusion_text}"
        text_tokens = nltk.word_tokenize(full_text.lower())
        tokens.extend(text_tokens * text_weight)

        return tokens

    @property
    def corpus_size(self) -> int:
        return len(self._trial_ids)
