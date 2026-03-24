"""Dense (embedding-based) retrieval for clinical trials.

Optional retrieval method. Uses FAISS for fast similarity search.
Requires more memory than BM25 but captures semantic similarity.
"""

from __future__ import annotations

import logging

import numpy as np

from ctm.config import RetrievalConfig
from ctm.embeddings.base import EmbeddingProvider
from ctm.models.trial import ClinicalTrial

logger = logging.getLogger(__name__)


class DenseRetriever:
    """Embedding-based dense retrieval using FAISS."""

    def __init__(self, embedder: EmbeddingProvider, config: RetrievalConfig) -> None:
        self._embedder = embedder
        self._config = config
        self._index = None
        self._trial_ids: list[str] = []

    async def build_index(self, trials: list[ClinicalTrial]) -> None:
        """Build FAISS index from trial embeddings."""
        import faiss

        texts = [self._trial_to_text(t) for t in trials]
        self._trial_ids = [t.nct_id for t in trials]

        logger.info(f"Embedding {len(texts)} trials...")
        embeddings = await self._embedder.embed_texts(texts)

        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)  # Inner product (cosine with normalized vecs)
        faiss.normalize_L2(embeddings)
        self._index.add(embeddings)

        logger.info(f"Dense index built: {len(texts)} trials, {dim} dimensions")

    async def search(self, query: str, top_n: int | None = None) -> list[tuple[str, float]]:
        """Search by query embedding similarity."""
        if self._index is None:
            return []

        n = top_n or self._config.top_n
        query_vec = await self._embedder.embed_query(query)
        query_vec = query_vec.reshape(1, -1).astype(np.float32)

        import faiss
        faiss.normalize_L2(query_vec)

        scores, indices = self._index.search(query_vec, min(n, len(self._trial_ids)))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self._trial_ids):
                results.append((self._trial_ids[idx], float(score)))

        return results

    def _trial_to_text(self, trial: ClinicalTrial) -> str:
        """Convert trial to text for embedding."""
        parts = [trial.brief_title]
        if trial.diseases:
            parts.append(", ".join(trial.diseases))
        if trial.brief_summary:
            parts.append(trial.brief_summary[:500])
        return " ".join(parts)

    @property
    def corpus_size(self) -> int:
        return len(self._trial_ids)
