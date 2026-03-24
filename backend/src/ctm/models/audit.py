"""Audit trail models."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    MATCH_STARTED = "match_started"
    MATCH_COMPLETED = "match_completed"
    BATCH_STARTED = "batch_started"
    BATCH_COMPLETED = "batch_completed"
    REFERRAL_CREATED = "referral_created"
    REFERRAL_STATUS_CHANGED = "referral_status_changed"
    PATIENT_INGESTED = "patient_ingested"
    TRIAL_IMPORTED = "trial_imported"
    SETTINGS_CHANGED = "settings_changed"
    PRIVACY_CHANGED = "privacy_changed"
    REPORT_GENERATED = "report_generated"
    DEID_APPLIED = "deid_applied"
    DEID_VALIDATION_FLAG = "deid_validation_flag"


class AuditEntry(BaseModel):
    """A single audit log entry with cryptographic chaining."""

    entry_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action: AuditAction
    user: str = "system"
    details: dict = {}
    prompt_version: str | None = None
    model_used: str | None = None
    previous_hash: str = ""
    entry_hash: str = ""

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this entry for chain integrity."""
        payload = json.dumps(
            {
                "entry_id": self.entry_id,
                "timestamp": self.timestamp.isoformat(),
                "action": self.action.value,
                "user": self.user,
                "details": self.details,
                "prompt_version": self.prompt_version,
                "model_used": self.model_used,
                "previous_hash": self.previous_hash,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def seal(self) -> None:
        """Compute and set the entry hash."""
        self.entry_hash = self.compute_hash()

    def verify(self) -> bool:
        """Verify the entry hash matches the content."""
        return self.entry_hash == self.compute_hash()
