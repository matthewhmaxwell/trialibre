"""Sentence-transformers embedding provider.

Default provider: runs on CPU, no GPU required.
Uses a medical domain model for better clinical text matching.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np

from ctm.config import EmbeddingConfig

logger = logging.getLogger(__name__)


class SentenceTransformerEmbedding:
    """Embedding provider using sentence-transformers library.

    Default model is a PubMedBERT variant fine-tuned for medical NLI,
    which provides better clinical text similarity than general models.
    Falls back to all-MiniLM-L6-v2 if the medical model fails to load.
    """

    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._model_name = config.model
        self._device = self._resolve_device(config.device)
        self._model = None
        self._dim: int | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._dim is None:
            self._ensure_loaded()
        return self._dim  # type: ignore

    def _resolve_device(self, device: str) -> str:
        if device != "auto":
            return device
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return

        from sentence_transformers import SentenceTransformer

        try:
            logger.info(f"Loading embedding model: {self._model_name} on {self._device}")
            self._model = SentenceTransformer(self._model_name, device=self._device)
        except Exception as e:
            logger.warning(
                f"Failed to load {self._model_name}: {e}. "
                "Falling back to all-MiniLM-L6-v2"
            )
            self._model_name = "all-MiniLM-L6-v2"
            self._model = SentenceTransformer(self._model_name, device=self._device)

        # Determine dimension from a test embedding
        test = self._model.encode(["test"], convert_to_numpy=True)
        self._dim = test.shape[1]
        logger.info(f"Embedding model loaded: {self._model_name} (dim={self._dim})")

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        self._ensure_loaded()
        assert self._model is not None

        embeddings = self._model.encode(
            texts,
            batch_size=self._config.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings

    async def embed_query(self, query: str) -> np.ndarray:
        result = await self.embed_texts([query])
        return result[0]
