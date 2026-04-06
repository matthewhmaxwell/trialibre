"""Referral management endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# In-memory store (replaced by DB in production)
_referrals: dict[str, dict] = {}


class ReferralCreate(BaseModel):
    patient_id: str
    trial_id: str
    trial_title: str = ""
    recipient_email: str = ""
    recipient_name: str = ""
    message: str = ""
    include_summary: bool = True
    include_criteria: bool = True


class ReferralStatusUpdate(BaseModel):
    status: str  # sent, accepted, declined, pending


@router.post("/referrals")
async def create_referral(body: ReferralCreate):
    referral_id = str(uuid.uuid4())[:8]
    referral = {
        "referral_id": referral_id,
        "patient_id": body.patient_id,
        "trial_id": body.trial_id,
        "trial_title": body.trial_title,
        "recipient_email": body.recipient_email,
        "recipient_name": body.recipient_name,
        "message": body.message,
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _referrals[referral_id] = referral
    return referral


@router.get("/referrals")
async def list_referrals():
    return list(_referrals.values())


@router.get("/referrals/{referral_id}")
async def get_referral(referral_id: str):
    if referral_id not in _referrals:
        raise HTTPException(404, f"Referral {referral_id} not found")
    return _referrals[referral_id]


@router.put("/referrals/{referral_id}/status")
async def update_referral_status(referral_id: str, body: ReferralStatusUpdate):
    if referral_id not in _referrals:
        raise HTTPException(404, f"Referral {referral_id} not found")
    _referrals[referral_id]["status"] = body.status
    return _referrals[referral_id]
