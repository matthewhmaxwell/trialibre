"""Referral management endpoints."""
from __future__ import annotations
from fastapi import APIRouter
router = APIRouter()

@router.post("/referrals")
async def create_referral():
    return {"status": "not_implemented"}

@router.get("/referrals")
async def list_referrals():
    return []

@router.get("/referrals/{referral_id}")
async def get_referral(referral_id: str):
    return {"referral_id": referral_id, "status": "not_found"}

@router.put("/referrals/{referral_id}/status")
async def update_referral_status(referral_id: str):
    return {"referral_id": referral_id, "status": "updated"}
