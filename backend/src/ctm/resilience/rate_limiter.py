"""Token bucket rate limiter for LLM API calls."""

from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """Token bucket rate limiter.

    Controls the rate of API calls to prevent hitting provider rate limits.

    Usage:
        limiter = RateLimiter(requests_per_minute=60)
        await limiter.acquire()
        # ... make API call ...
    """

    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self._tokens = float(requests_per_minute)
        self._max_tokens = float(requests_per_minute)
        self._rate = requests_per_minute / 60.0  # tokens per second
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a token is available, then consume one."""
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

            # Wait for a token to become available
            wait_time = (1.0 - self._tokens) / self._rate
            await asyncio.sleep(min(wait_time, 1.0))

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._max_tokens, self._tokens + elapsed * self._rate)
        self._last_refill = now

    @property
    def available_tokens(self) -> float:
        """Current number of available tokens (approximate)."""
        return self._tokens
