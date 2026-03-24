"""Cryptographically chained audit logger.

Each entry includes a SHA-256 hash of the previous entry,
creating a tamper-evident chain for 21 CFR Part 11 compliance.
"""

from __future__ import annotations

import logging
import uuid

from ctm.config import AuditConfig
from ctm.models.audit import AuditAction, AuditEntry

logger = logging.getLogger(__name__)


class AuditLogger:
    """Immutable, cryptographically chained audit logger."""

    def __init__(self, config: AuditConfig) -> None:
        self._config = config
        self._entries: list[AuditEntry] = []
        self._last_hash: str = "0" * 64  # Genesis hash

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def log(
        self,
        action: AuditAction,
        details: dict | None = None,
        user: str = "system",
        prompt_version: str | None = None,
        model_used: str | None = None,
    ) -> AuditEntry | None:
        """Log an audit entry with cryptographic chaining.

        Returns:
            The created AuditEntry, or None if auditing is disabled.
        """
        if not self._config.enabled:
            return None

        entry = AuditEntry(
            entry_id=f"audit-{uuid.uuid4().hex[:12]}",
            action=action,
            user=user,
            details=details or {},
            previous_hash=self._last_hash,
        )

        if self._config.log_prompts:
            entry.prompt_version = prompt_version
            entry.model_used = model_used

        if self._config.crypto_chain:
            entry.seal()
            self._last_hash = entry.entry_hash

        self._entries.append(entry)
        return entry

    def verify_chain(self) -> tuple[bool, int]:
        """Verify the integrity of the entire audit chain.

        Returns:
            Tuple of (is_valid, first_invalid_index).
            If valid, first_invalid_index is -1.
        """
        if not self._entries:
            return True, -1

        expected_prev = "0" * 64  # Genesis

        for i, entry in enumerate(self._entries):
            if entry.previous_hash != expected_prev:
                return False, i

            if not entry.verify():
                return False, i

            expected_prev = entry.entry_hash

        return True, -1

    def get_entries(
        self,
        action: AuditAction | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Get audit entries, optionally filtered by action."""
        entries = self._entries
        if action:
            entries = [e for e in entries if e.action == action]
        return entries[-limit:]

    @property
    def entry_count(self) -> int:
        return len(self._entries)
