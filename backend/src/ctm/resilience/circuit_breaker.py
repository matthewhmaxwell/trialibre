"""Circuit breaker for external API calls.

Prevents cascading failures when external services (ClinicalTrials.gov, OpenFDA,
LLM APIs) are down. Opens after N consecutive failures, allows a probe after timeout.
"""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing with one call


class CircuitBreakerError(Exception):
    """Raised when circuit is open and calls are rejected."""

    def __init__(self, service: str, retry_after: float):
        super().__init__(f"Circuit breaker open for {service}. Retry in {retry_after:.0f}s")
        self.service = service
        self.retry_after = retry_after


class CircuitBreaker:
    """Circuit breaker with configurable thresholds.

    Usage:
        breaker = CircuitBreaker("clinicaltrials_gov", failure_threshold=5)

        async with breaker:
            result = await fetch_from_ctgov(...)
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max: int = 1,
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._half_open_count = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                return CircuitState.HALF_OPEN
        return self._state

    async def __aenter__(self):
        async with self._lock:
            current = self.state

            if current == CircuitState.OPEN:
                retry_after = self.recovery_timeout - (
                    time.monotonic() - self._last_failure_time
                )
                raise CircuitBreakerError(self.service_name, max(0, retry_after))

            if current == CircuitState.HALF_OPEN:
                if self._half_open_count >= self.half_open_max:
                    raise CircuitBreakerError(self.service_name, self.recovery_timeout)
                self._half_open_count += 1

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self._lock:
            if exc_type is None:
                # Success
                self._failure_count = 0
                self._half_open_count = 0
                if self._state != CircuitState.CLOSED:
                    logger.info(f"Circuit breaker CLOSED for {self.service_name}")
                self._state = CircuitState.CLOSED
            else:
                # Failure
                self._failure_count += 1
                self._last_failure_time = time.monotonic()

                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit breaker OPEN for {self.service_name} "
                        f"after {self._failure_count} failures"
                    )

        return False  # Don't suppress the exception
