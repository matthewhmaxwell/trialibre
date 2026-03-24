"""LLM provider abstraction using Python Protocols.

Any object implementing these methods can serve as a provider.
No inheritance required - structural typing (duck typing with type safety).
"""

from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Structural interface for all LLM providers."""

    @property
    def model_name(self) -> str:
        """Return the model identifier being used."""
        ...

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 16384,
        response_format: dict | None = None,
    ) -> str:
        """Send messages and return the completion text.

        Args:
            messages: List of {"role": "system"|"user"|"assistant", "content": "..."}
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens in response
            response_format: Optional format hint (e.g., {"type": "json_object"})

        Returns:
            The completion text string.

        Raises:
            LLMError: On API errors after retries exhausted.
        """
        ...

    async def complete_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 16384,
    ) -> AsyncIterator[str]:
        """Stream completion tokens.

        Yields individual tokens/chunks as they arrive.
        """
        ...

    def count_tokens(self, text: str) -> int:
        """Estimate token count for the given text.

        Uses a rough heuristic (words * 1.3) if no tokenizer is available.
        """
        ...


class LLMError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(self, message: str, provider: str = "", retryable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class RateLimitError(LLMError):
    """Rate limit exceeded."""

    def __init__(self, message: str, provider: str = "", retry_after: float | None = None):
        super().__init__(message, provider=provider, retryable=True)
        self.retry_after = retry_after


class AuthenticationError(LLMError):
    """Authentication/authorization failed."""

    def __init__(self, message: str, provider: str = ""):
        super().__init__(message, provider=provider, retryable=False)


class ModelNotFoundError(LLMError):
    """Requested model not available."""

    def __init__(self, message: str, provider: str = ""):
        super().__init__(message, provider=provider, retryable=False)
