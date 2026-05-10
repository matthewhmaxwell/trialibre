"""Feedback repository — async CRUD for clinician feedback on matches.

Persisted feedback is the loop closer for shipping: every "right" /
"wrong" / "unsure" verdict from a real user is a data point we can
later mine to recalibrate prompts, thresholds, or the eligibility
veto, without having to ask the user to re-evaluate. The
`FeedbackRecord` schema has been on the books for a while; this
repository is what finally makes it reachable.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ctm.db.models import FeedbackRecord


# The verdicts the UI surfaces. Kept tight so aggregation stays simple.
ALLOWED_FEEDBACK_TYPES = ("correct", "incorrect", "unsure")


class FeedbackRepository:
    """Async CRUD operations for clinician feedback on match results."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        feedback_id: str,
        patient_id: str,
        trial_id: str,
        feedback_type: str,
        notes: str = "",
        coordinator: str = "",
        outcome: str | None = None,
        data: dict | None = None,
    ) -> dict:
        if feedback_type not in ALLOWED_FEEDBACK_TYPES:
            raise ValueError(
                f"feedback_type must be one of {ALLOWED_FEEDBACK_TYPES}, "
                f"got {feedback_type!r}"
            )
        record = FeedbackRecord(
            feedback_id=feedback_id,
            patient_id=patient_id,
            trial_id=trial_id,
            feedback_type=feedback_type,
            coordinator=coordinator,
            notes=notes,
            outcome=outcome,
            data=data or {},
        )
        self.session.add(record)
        await self.session.flush()
        return self._record_to_dict(record)

    async def list_for_trial(self, trial_id: str) -> list[dict]:
        result = await self.session.execute(
            select(FeedbackRecord)
            .where(FeedbackRecord.trial_id == trial_id)
            .order_by(FeedbackRecord.created_at.desc())
        )
        return [self._record_to_dict(r) for r in result.scalars().all()]

    async def list_all(self, limit: int = 500) -> list[dict]:
        result = await self.session.execute(
            select(FeedbackRecord)
            .order_by(FeedbackRecord.created_at.desc())
            .limit(limit)
        )
        return [self._record_to_dict(r) for r in result.scalars().all()]

    async def aggregate(self) -> dict:
        """Counts per verdict across all feedback. Cheap to compute,
        useful for the dashboard 'how often are we right?' card."""
        rows = await self.list_all(limit=10_000)
        counts: dict[str, int] = {t: 0 for t in ALLOWED_FEEDBACK_TYPES}
        for r in rows:
            t = r.get("feedback_type")
            if t in counts:
                counts[t] += 1
        total = sum(counts.values())
        return {
            "total": total,
            "counts": counts,
            "agreement_rate": (counts["correct"] / total) if total else None,
        }

    @staticmethod
    def _record_to_dict(record: FeedbackRecord) -> dict:
        return {
            "feedback_id": record.feedback_id,
            "patient_id": record.patient_id,
            "trial_id": record.trial_id,
            "feedback_type": record.feedback_type,
            "coordinator": record.coordinator,
            "notes": record.notes,
            "outcome": record.outcome,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            **(record.data or {}),
        }
