"""Privacy configuration models for the setup wizard and runtime."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ProcessingLocation(str, Enum):
    LOCAL = "local"  # Ollama, data stays on device
    CLOUD = "cloud"  # Anthropic/OpenAI, data sent externally
    HYBRID = "hybrid"  # Retrieval local, LLM cloud


class DataRetention(str, Enum):
    DELETE_IMMEDIATELY = "delete_immediately"
    RETAIN_DAYS = "retain_days"
    RETAIN_INDEFINITELY = "retain_indefinitely"


class PrivacySettings(BaseModel):
    """User-facing privacy settings (from setup wizard)."""

    processing_location: ProcessingLocation = ProcessingLocation.CLOUD
    delete_after_match: bool = True
    retain_match_logs: bool = False
    allow_local_storage: bool = False
    data_retention: DataRetention = DataRetention.DELETE_IMMEDIATELY
    retention_days: int | None = None

    # De-identification
    deid_enabled: bool = True  # True when cloud processing
    deid_strip_names: bool = True
    deid_strip_dates: bool = True
    deid_strip_locations: bool = True
    deid_strip_ids: bool = True
    deid_human_review: bool = False  # Flag uncertain de-ID for review

    @property
    def privacy_status_label(self) -> str:
        """Human-readable privacy status for the UI indicator."""
        if self.delete_after_match and not self.retain_match_logs:
            return "Private"
        if self.retain_match_logs and not self.allow_local_storage:
            return "Secure"
        return "Stored"

    @property
    def privacy_status_color(self) -> str:
        """Color for the privacy shield indicator."""
        if self.delete_after_match and not self.retain_match_logs:
            return "green"
        if self.retain_match_logs and not self.allow_local_storage:
            return "blue"
        return "yellow"
