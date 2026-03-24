"""Batch processing models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from ctm.models.matching import PatientTrialRanking


class BatchStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchJob(BaseModel):
    """A batch patient screening job."""

    job_id: str
    status: BatchStatus = BatchStatus.QUEUED
    total_patients: int = 0
    completed_patients: int = 0
    failed_patients: int = 0
    estimated_cost_usd: float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

    @property
    def progress_pct(self) -> float:
        if self.total_patients == 0:
            return 0.0
        return (self.completed_patients / self.total_patients) * 100


class BatchResult(BaseModel):
    """Results of a completed batch job."""

    job_id: str
    rankings: list[PatientTrialRanking] = []
    total_patients: int = 0
    total_matches: int = 0
    duration_seconds: float = 0.0
    actual_cost_usd: float | None = None
