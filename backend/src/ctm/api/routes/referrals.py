"""Referral management endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ctm.api.dependencies import get_db_session
from ctm.db.repositories import ReferralRepository

router = APIRouter()


class ReferralCreate(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=255)
    trial_id: str = Field(..., min_length=1, max_length=64)
    trial_title: str = Field(default="", max_length=500)
    recipient_email: EmailStr | None = None
    recipient_name: str = Field(default="", max_length=255)
    message: str = Field(default="", max_length=5000)
    include_summary: bool = True
    include_criteria: bool = True


class ReferralStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(created|sent|accepted|declined|pending)$")


@router.post("/referrals")
async def create_referral(
    body: ReferralCreate,
    session: AsyncSession = Depends(get_db_session),
):
    repo = ReferralRepository(session)
    referral_id = str(uuid.uuid4())[:8]
    data = {
        "trial_title": body.trial_title,
        "recipient_email": body.recipient_email,
        "recipient_name": body.recipient_name,
        "message": body.message,
        "include_summary": body.include_summary,
        "include_criteria": body.include_criteria,
        "delivery_method": "pdf",
    }
    return await repo.create(
        referral_id=referral_id,
        patient_id=body.patient_id,
        trial_id=body.trial_id,
        data=data,
    )


@router.get("/referrals")
async def list_referrals(session: AsyncSession = Depends(get_db_session)):
    repo = ReferralRepository(session)
    return await repo.list_all()


@router.get("/referrals/{referral_id}")
async def get_referral(
    referral_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    repo = ReferralRepository(session)
    referral = await repo.get(referral_id)
    if referral is None:
        raise HTTPException(404, f"Referral {referral_id} not found")
    return referral


@router.put("/referrals/{referral_id}/status")
async def update_referral_status(
    referral_id: str,
    body: ReferralStatusUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    repo = ReferralRepository(session)
    updated = await repo.update_status(referral_id, body.status)
    if updated is None:
        raise HTTPException(404, f"Referral {referral_id} not found")
    return updated
