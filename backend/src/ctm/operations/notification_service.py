"""Notification service for match alerts, referral updates, etc."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ctm.models.notification import Notification, NotificationChannel, NotificationType


class NotificationService:
    """Manage user notifications."""

    def __init__(self) -> None:
        self._notifications: list[Notification] = []

    def create(
        self,
        type: NotificationType,
        title: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        action_url: str | None = None,
        metadata: dict | None = None,
    ) -> Notification:
        notif = Notification(
            notification_id=f"notif-{uuid.uuid4().hex[:8]}",
            type=type,
            channel=channel,
            title=title,
            message=message,
            action_url=action_url,
            metadata=metadata or {},
        )
        self._notifications.append(notif)
        return notif

    def get_unread(self) -> list[Notification]:
        return [n for n in self._notifications if not n.read]

    def mark_read(self, notification_id: str) -> bool:
        for n in self._notifications:
            if n.notification_id == notification_id:
                n.read = True
                return True
        return False

    def get_all(self, limit: int = 50) -> list[Notification]:
        return sorted(self._notifications, key=lambda n: n.created_at, reverse=True)[:limit]

    @property
    def unread_count(self) -> int:
        return sum(1 for n in self._notifications if not n.read)
