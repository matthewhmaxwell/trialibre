"""Trial repository — async CRUD for uploaded/imported clinical trials.

Sandbox trials are loaded from disk by `ctm.sandbox.loader` and are NOT
stored here. This repository only handles trials that came from user uploads
or registry imports (CT.gov, etc.).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ctm.db.models import TrialRecord
from ctm.models.trial import ClinicalTrial


class TrialRepository:
    """Async CRUD operations for stored clinical trials."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, nct_id: str) -> ClinicalTrial | None:
        """Get a single trial by NCT ID."""
        result = await self.session.execute(
            select(TrialRecord).where(TrialRecord.nct_id == nct_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return self._record_to_model(record)

    async def list_all(self) -> list[ClinicalTrial]:
        """List all stored trials."""
        result = await self.session.execute(select(TrialRecord))
        return [self._record_to_model(r) for r in result.scalars().all()]

    async def list_paginated(
        self, offset: int = 0, limit: int = 50
    ) -> tuple[list[ClinicalTrial], int]:
        """Paginated list with total count."""
        # Total count
        count_result = await self.session.execute(select(TrialRecord))
        total = len(count_result.scalars().all())
        # Page
        page_result = await self.session.execute(
            select(TrialRecord).offset(offset).limit(limit)
        )
        page = [self._record_to_model(r) for r in page_result.scalars().all()]
        return page, total

    async def upsert(self, trial: ClinicalTrial) -> ClinicalTrial:
        """Insert a trial or update if it already exists."""
        existing = await self.session.execute(
            select(TrialRecord).where(TrialRecord.nct_id == trial.nct_id)
        )
        record = existing.scalar_one_or_none()
        if record is None:
            record = TrialRecord(
                nct_id=trial.nct_id,
                brief_title=trial.brief_title,
                data=trial.model_dump(mode="json"),
                source_registry=trial.source_registry or "upload",
                indexed_at=datetime.now(timezone.utc),
            )
            self.session.add(record)
        else:
            record.brief_title = trial.brief_title
            record.data = trial.model_dump(mode="json")
            record.source_registry = trial.source_registry or record.source_registry
            record.indexed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return trial

    async def delete(self, nct_id: str) -> bool:
        """Delete a trial. Returns True if it existed, False otherwise."""
        result = await self.session.execute(
            delete(TrialRecord).where(TrialRecord.nct_id == nct_id)
        )
        return result.rowcount > 0

    async def exists(self, nct_id: str) -> bool:
        result = await self.session.execute(
            select(TrialRecord.nct_id).where(TrialRecord.nct_id == nct_id)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    def _record_to_model(record: TrialRecord) -> ClinicalTrial:
        """Reconstitute a ClinicalTrial from its stored JSON blob."""
        return ClinicalTrial(**record.data)
