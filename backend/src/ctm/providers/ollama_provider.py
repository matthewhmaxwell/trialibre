"""Ollama local LLM provider."""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

import httpx

from ctm.config import LLMConfig
from ctm.providers.base import LLMError, ModelNotFoundError

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://localhost:11434"


class OllamaProvider:
    """Ollama local model provider.

    Communicates with a locally running Ollama server via HTTP API.
    No patient data leaves the device.
    """

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._model = config.model or "llama3.1:8b"
        self._base_url = config.base_url or DEFAULT_OLLAMA_URL
        self._max_retries = config.max_retries
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(config.timeout, connect=10.0),
        )

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 16384,
        response_format: dict | None = None,
    ) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if response_format and response_format.get("type") == "json_object":
            payload["format"] = "json"

        for attempt in range(self._max_retries):
            try:
                response = await self._client.post("/api/chat", json=payload)

                if response.status_code == 404:
                    raise ModelNotFoundError(
                        f"Model '{self._model}' not found in Ollama. "
                        f"Try: ollama pull {self._model}",
                        provider="ollama",
                    )

                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")

            except httpx.ConnectError as e:
                raise LLMError(
                    f"Cannot connect to Ollama at {self._base_url}. "
                    "Is Ollama running? Start it with: ollama serve",
                    provider="ollama",
                    retryable=False,
                ) from e

            except (ModelNotFoundError, LLMError):
                raise

            except (httpx.HTTPError, Exception) as e:
                # httpx exceptions often have empty str(); fall back to type name
                err_msg = str(e) or repr(e) or type(e).__name__
                if attempt == self._max_retries - 1:
                    raise LLMError(
                        f"Ollama error after {self._max_retries} retries: {err_msg}",
                        provider="ollama",
                    ) from e
                wait = min(2**attempt, 15)
                logger.warning(f"Ollama error (attempt {attempt + 1}): {err_msg}")
                await asyncio.sleep(wait)

        raise LLMError("Unexpected: exhausted retries", provider="ollama")

    async def complete_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 16384,
    ) -> AsyncIterator[str]:
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with self._client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    import json

                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content

    def count_tokens(self, text: str) -> int:
        return int(len(text.split()) * 1.3)

    async def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            response = await self._client.get("/api/tags")
            if response.status_code != 200:
                return False
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return any(self._model in m for m in models)
        except (httpx.HTTPError, Exception):
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
