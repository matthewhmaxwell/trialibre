"""Notification models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    MATCH_FOUND = "match_found"
    BATCH_COMPLETE = "batch_complete"
    REFERRAL_STATUS = "referral_status"
    NEW_TRIAL = "new_trial"
    CRITERIA_CHANGED = "criteria_changed"
    SYSTEM = "system"


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"


class Notification(BaseModel):
    """A user notification."""

    notification_id: str
    type: NotificationType
    channel: NotificationChannel = NotificationChannel.IN_APP
    title: str
    message: str
    read: bool = False
    action_url: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = {}
