"""Embedding provider abstraction."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Structural interface for embedding providers."""

    @property
    def model_name(self) -> str:
        """Return the embedding model identifier."""
        ...

    @property
    def dimension(self) -> int:
        """Return the embedding vector dimension."""
        ...

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            numpy array of shape (len(texts), dimension).
        """
        ...

    async def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query text.

        Some models distinguish between document and query embeddings.

        Args:
            query: Query text to embed.

        Returns:
            numpy array of shape (dimension,).
        """
        ...
