"""Anthropic Claude LLM provider."""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

import anthropic

from ctm.config import LLMConfig
from ctm.providers.base import AuthenticationError, LLMError, RateLimitError

logger = logging.getLogger(__name__)


class AnthropicProvider:
    """Anthropic Claude provider with retry and rate limit handling."""

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._model = config.model
        self._max_retries = config.max_retries
        self._client = anthropic.AsyncAnthropic(
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=0,  # We handle retries ourselves
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
        system_msg = ""
        user_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                user_msgs.append({"role": m["role"], "content": m["content"]})

        for attempt in range(self._max_retries):
            try:
                response = await self._client.messages.create(
                    model=self._model,
                    system=system_msg,
                    messages=user_msgs,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.content[0].text

            except anthropic.AuthenticationError as e:
                raise AuthenticationError(
                    f"Anthropic authentication failed: {e}", provider="anthropic"
                ) from e

            except anthropic.RateLimitError as e:
                wait = min(2**attempt, 60)
                logger.warning(
                    f"Anthropic rate limited (attempt {attempt + 1}/{self._max_retries}), "
                    f"waiting {wait}s"
                )
                if attempt == self._max_retries - 1:
                    raise RateLimitError(
                        f"Rate limit exceeded after {self._max_retries} retries",
                        provider="anthropic",
                        retry_after=wait,
                    ) from e
                await asyncio.sleep(wait)

            except anthropic.APIError as e:
                if attempt == self._max_retries - 1:
                    raise LLMError(
                        f"Anthropic API error after {self._max_retries} retries: {e}",
                        provider="anthropic",
                        retryable=False,
                    ) from e
                wait = min(2**attempt, 30)
                logger.warning(
                    f"Anthropic API error (attempt {attempt + 1}): {e}, retrying in {wait}s"
                )
                await asyncio.sleep(wait)

        raise LLMError("Unexpected: exhausted retries", provider="anthropic")

    async def complete_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 16384,
    ) -> AsyncIterator[str]:
        system_msg = ""
        user_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                user_msgs.append({"role": m["role"], "content": m["content"]})

        async with self._client.messages.stream(
            model=self._model,
            system=system_msg,
            messages=user_msgs,
            temperature=temperature,
            max_tokens=max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def count_tokens(self, text: str) -> int:
        # Rough estimate: ~1.3 tokens per word for English
        return int(len(text.split()) * 1.3)
