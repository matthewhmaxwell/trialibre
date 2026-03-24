"""Retry utility with exponential backoff and jitter."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    **kwargs,
) -> T:
    """Execute an async function with exponential backoff retry.

    Args:
        func: Async function to call.
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay in seconds.
        jitter: Add random jitter to delay.
        retryable_exceptions: Exception types that trigger retry.

    Returns:
        The function's return value.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e
            if attempt == max_retries:
                break

            delay = min(base_delay * (2**attempt), max_delay)
            if jitter:
                delay *= 0.5 + random.random()

            logger.warning(
                f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}. "
                f"Waiting {delay:.1f}s"
            )
            await asyncio.sleep(delay)

    raise last_exception  # type: ignore[misc]
