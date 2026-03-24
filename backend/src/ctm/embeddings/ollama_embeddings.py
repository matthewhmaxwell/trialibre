"""Ollama embedding provider using the Ollama embed API."""

from __future__ import annotations

import logging

import httpx
import numpy as np

from ctm.config import EmbeddingConfig

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://localhost:11434"


class OllamaEmbedding:
    """Embedding provider using Ollama's embed endpoint.

    Keeps everything local - no data leaves the device.
    Default model: nomic-embed-text (768 dimensions, good for medical text).
    """

    def __init__(self, config: EmbeddingConfig) -> None:
        self._model_name = config.model or "nomic-embed-text"
        self._base_url = DEFAULT_OLLAMA_URL
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
        self._dim: int | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._dim is None:
            raise RuntimeError("Dimension unknown. Call embed_texts first.")
        return self._dim

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        response = await self._client.post(
            "/api/embed",
            json={"model": self._model_name, "input": texts},
        )
        response.raise_for_status()
        data = response.json()
        embeddings = np.array(data["embeddings"], dtype=np.float32)
        self._dim = embeddings.shape[1]
        return embeddings

    async def embed_query(self, query: str) -> np.ndarray:
        result = await self.embed_texts([query])
        return result[0]

    async def close(self) -> None:
        await self._client.aclose()
