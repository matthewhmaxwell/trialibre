"""OpenAI and Azure OpenAI LLM provider."""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

import openai

from ctm.config import LLMConfig
from ctm.providers.base import AuthenticationError, LLMError, RateLimitError

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """OpenAI / Azure OpenAI provider with retry and rate limit handling."""

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._model = config.model
        self._max_retries = config.max_retries

        kwargs: dict = {"api_key": config.api_key, "timeout": config.timeout}
        if config.base_url:
            kwargs["base_url"] = config.base_url

        self._client = openai.AsyncOpenAI(**kwargs)

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
        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        for attempt in range(self._max_retries):
            try:
                response = await self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                return content or ""

            except openai.AuthenticationError as e:
                raise AuthenticationError(
                    f"OpenAI authentication failed: {e}", provider="openai"
                ) from e

            except openai.RateLimitError as e:
                wait = min(2**attempt, 60)
                logger.warning(
                    f"OpenAI rate limited (attempt {attempt + 1}/{self._max_retries}), "
                    f"waiting {wait}s"
                )
                if attempt == self._max_retries - 1:
                    raise RateLimitError(
                        f"Rate limit exceeded after {self._max_retries} retries",
                        provider="openai",
                        retry_after=wait,
                    ) from e
                await asyncio.sleep(wait)

            except openai.APIError as e:
                if attempt == self._max_retries - 1:
                    raise LLMError(
                        f"OpenAI API error after {self._max_retries} retries: {e}",
                        provider="openai",
                        retryable=False,
                    ) from e
                wait = min(2**attempt, 30)
                logger.warning(f"OpenAI API error (attempt {attempt + 1}): {e}")
                await asyncio.sleep(wait)

        raise LLMError("Unexpected: exhausted retries", provider="openai")

    async def complete_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 16384,
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def count_tokens(self, text: str) -> int:
        return int(len(text.split()) * 1.3)
