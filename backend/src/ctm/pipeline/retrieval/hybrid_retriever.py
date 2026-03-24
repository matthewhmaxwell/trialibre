"""Hybrid retrieval with reciprocal rank fusion.

Combines BM25 (sparse) and dense (embedding) retrieval results.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from ctm.config import RetrievalConfig
from ctm.models.trial import ClinicalTrial
from ctm.pipeline.retrieval.bm25_retriever import BM25Retriever
from ctm.pipeline.retrieval.dense_retriever import DenseRetriever

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid search combining BM25 + dense retrieval via RRF."""

    def __init__(
        self,
        bm25: BM25Retriever,
        dense: DenseRetriever | None,
        config: RetrievalConfig,
    ) -> None:
        self._bm25 = bm25
        self._dense = dense
        self._config = config

    async def retrieve(
        self,
        queries: list[str],
        top_n: int | None = None,
    ) -> list[str]:
        """Retrieve trial IDs using hybrid search.

        Args:
            queries: List of search queries (ranked by priority).
            top_n: Max results to return.

        Returns:
            List of NCT IDs sorted by fused score.
        """
        n = top_n or self._config.top_n
        k = self._config.fusion_k
        scores: dict[str, float] = defaultdict(float)

        # BM25 search
        if self._config.enable_bm25:
            for priority, query in enumerate(queries):
                priority_weight = 1.0 / (priority + 1)
                bm25_results = self._bm25.search(query, top_n=n)
                for rank, (nct_id, _) in enumerate(bm25_results):
                    scores[nct_id] += priority_weight / (rank + k)

        # Dense search
        if self._config.enable_dense and self._dense is not None:
            for priority, query in enumerate(queries):
                priority_weight = 1.0 / (priority + 1)
                dense_results = await self._dense.search(query, top_n=n)
                for rank, (nct_id, _) in enumerate(dense_results):
                    scores[nct_id] += priority_weight / (rank + k)

        # Sort by fused score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [nct_id for nct_id, _ in ranked[:n]]
