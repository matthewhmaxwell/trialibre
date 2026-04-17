"""Referral repository — async CRUD for patient-trial referrals."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ctm.db.models import ReferralRecord


class ReferralRepository:
    """Async CRUD operations for stored referrals."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, referral_id: str) -> dict | None:
        result = await self.session.execute(
            select(ReferralRecord).where(ReferralRecord.referral_id == referral_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return self._record_to_dict(record)

    async def list_all(self) -> list[dict]:
        result = await self.session.execute(
            select(ReferralRecord).order_by(ReferralRecord.created_at.desc())
        )
        return [self._record_to_dict(r) for r in result.scalars().all()]

    async def create(
        self,
        referral_id: str,
        patient_id: str,
        trial_id: str,
        data: dict,
    ) -> dict:
        record = ReferralRecord(
            referral_id=referral_id,
            patient_id=patient_id,
            trial_id=trial_id,
            status="created",
            delivery_method=data.get("delivery_method", "pdf"),
            data=data,
        )
        self.session.add(record)
        await self.session.flush()
        return self._record_to_dict(record)

    async def update_status(self, referral_id: str, status: str) -> dict | None:
        result = await self.session.execute(
            select(ReferralRecord).where(ReferralRecord.referral_id == referral_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        record.status = status
        record.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return self._record_to_dict(record)

    async def delete(self, referral_id: str) -> bool:
        result = await self.session.execute(
            delete(ReferralRecord).where(ReferralRecord.referral_id == referral_id)
        )
        return result.rowcount > 0

    @staticmethod
    def _record_to_dict(record: ReferralRecord) -> dict:
        return {
            "referral_id": record.referral_id,
            "patient_id": record.patient_id,
            "trial_id": record.trial_id,
            "status": record.status,
            "delivery_method": record.delivery_method,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            **(record.data or {}),
        }
