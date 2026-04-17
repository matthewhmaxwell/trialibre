"""SQLAlchemy ORM models for persistent storage."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ctm.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PatientRecord(Base):
    """Stored patient record (only when local storage is enabled)."""

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    structured_data: Mapped[dict] = mapped_column(JSON, default=dict)
    language: Mapped[str] = mapped_column(String(10), default="en")
    source_format: Mapped[str] = mapped_column(String(50), default="text")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class TrialRecord(Base):
    """Stored clinical trial."""

    __tablename__ = "trials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nct_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    brief_title: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)  # Full trial JSON
    source_registry: Mapped[str] = mapped_column(String(50), default="")
    indexed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class MatchRecord(Base):
    """Stored match result (when logging is enabled)."""

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(255), index=True)
    trial_id: Mapped[str] = mapped_column(String(20), index=True)
    combined_score: Mapped[float] = mapped_column(Float, default=0.0)
    strength: Mapped[str] = mapped_column(String(20), default="unlikely")
    result_data: Mapped[dict] = mapped_column(JSON, default=dict)
    prompt_version: Mapped[str] = mapped_column(String(50), default="")
    model_used: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ReferralRecord(Base):
    """Stored referral."""

    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referral_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    patient_id: Mapped[str] = mapped_column(String(255), index=True)
    trial_id: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), default="created")
    delivery_method: Mapped[str] = mapped_column(String(20), default="pdf")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class AuditRecord(Base):
    """Immutable audit log entry with cryptographic chaining."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    action: Mapped[str] = mapped_column(String(50))
    user: Mapped[str] = mapped_column(String(255), default="system")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    previous_hash: Mapped[str] = mapped_column(String(64), default="")
    entry_hash: Mapped[str] = mapped_column(String(64), default="")


class FeedbackRecord(Base):
    """Coordinator feedback on match results."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feedback_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    patient_id: Mapped[str] = mapped_column(String(255), index=True)
    trial_id: Mapped[str] = mapped_column(String(20), index=True)
    feedback_type: Mapped[str] = mapped_column(String(30))
    coordinator: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    outcome: Mapped[str | None] = mapped_column(String(30), nullable=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class NotificationRecord(Base):
    """User notification."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    notification_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(Text, default="")
    message: Mapped[str] = mapped_column(Text, default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    action_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class BatchJobRecord(Base):
    """Stored batch processing job (matching or trial sync)."""

    __tablename__ = "batch_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    job_type: Mapped[str] = mapped_column(String(30), default="match", index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    total: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    results: Mapped[list] = mapped_column(JSON, default=list)
    job_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
