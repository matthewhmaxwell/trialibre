"""Coordinator dashboard endpoints."""
from __future__ import annotations
from fastapi import APIRouter
router = APIRouter()

@router.get("/dashboard/stats")
async def dashboard_stats():
    return {"recent_matches": 0, "active_referrals": 0, "patients_screened": 0, "trials_matched": 0}
