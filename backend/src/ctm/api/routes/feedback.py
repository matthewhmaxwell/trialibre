"""Feedback endpoint — coordinator verdicts on match results.

POST /feedback : record a {correct,incorrect,unsure} verdict on a
                 (patient_id, trial_id) pair, with an optional note.
                 The model + prompt version + score at the time of the
                 verdict are captured in the `data` blob so a future
                 audit can re-evaluate the same pair against a newer
                 model and measure drift.

GET /feedback   : list recent feedback (default 100, max 500).
GET /feedback/aggregate : per-verdict counts and overall agreement rate.

This closes the loop the README has been promising: "every match shows
which criteria were met, not met, or couldn't be verified" — followed,
now, by "and you can tell us when we got it wrong."
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ctm.api.dependencies import get_db_session
from ctm.db.repositories.feedback import ALLOWED_FEEDBACK_TYPES, FeedbackRepository

router = APIRouter()


class FeedbackCreate(BaseModel):
    """Body for POST /feedback."""

    patient_id: str
    trial_id: str
    feedback_type: str = Field(
        description=f"One of: {ALLOWED_FEEDBACK_TYPES}",
    )
    notes: str = ""
    coordinator: str = ""
    outcome: str | None = None
    # Free-form data the UI can attach for later analysis: combined
    # score, strength, model name, etc. Stored as JSON.
    data: dict = Field(default_factory=dict)


@router.post("/feedback", status_code=201)
async def submit_feedback(
    body: FeedbackCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Record a coordinator verdict on a match result."""
    if body.feedback_type not in ALLOWED_FEEDBACK_TYPES:
        raise HTTPException(
            422,
            f"feedback_type must be one of {ALLOWED_FEEDBACK_TYPES}",
        )
    repo = FeedbackRepository(session)
    feedback_id = f"fb-{uuid.uuid4().hex[:12]}"
    record = await repo.create(
        feedback_id=feedback_id,
        patient_id=body.patient_id,
        trial_id=body.trial_id,
        feedback_type=body.feedback_type,
        notes=body.notes,
        coordinator=body.coordinator,
        outcome=body.outcome,
        data=body.data,
    )
    await session.commit()
    return record


@router.get("/feedback")
async def list_feedback(
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    """List recent feedback entries, newest first."""
    repo = FeedbackRepository(session)
    return await repo.list_all(limit=limit)


@router.get("/feedback/aggregate")
async def aggregate_feedback(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Per-verdict counts and overall agreement rate."""
    repo = FeedbackRepository(session)
    return await repo.aggregate()
