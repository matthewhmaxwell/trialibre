"""Referral models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ReferralStatus(str, Enum):
    CREATED = "created"
    SENT = "sent"
    RECEIVED = "received"
    SCREENING = "screening"
    ENROLLED = "enrolled"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"


class ReferralDelivery(str, Enum):
    SECURE_LINK = "secure_link"
    PDF = "pdf"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    FHIR = "fhir"
    PRINT = "print"


class Referral(BaseModel):
    """A patient referral to a trial site."""

    referral_id: str
    patient_id: str
    trial_id: str
    trial_title: str = ""
    site_name: str = ""
    site_contact: str = ""
    status: ReferralStatus = ReferralStatus.CREATED
    delivery_method: ReferralDelivery = ReferralDelivery.PDF
    referring_coordinator: str = ""
    referring_site: str = ""
    match_strength: str = ""
    match_summary: str = ""
    notes: str = ""
    secure_link_url: str | None = None
    secure_link_expires: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status_history: list[dict] = []
