"""Batch job repository — async CRUD for batch matching jobs."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ctm.db.models import BatchJobRecord


class BatchJobRepository:
    """Async CRUD operations for batch jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, job_id: str) -> dict | None:
        result = await self.session.execute(
            select(BatchJobRecord).where(BatchJobRecord.job_id == job_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return self._record_to_dict(record)

    async def create(self, job_id: str, total: int) -> dict:
        record = BatchJobRecord(
            job_id=job_id,
            status="running",
            total=total,
            completed=0,
            failed=0,
            results=[],
        )
        self.session.add(record)
        await self.session.flush()
        return self._record_to_dict(record)

    async def update(
        self,
        job_id: str,
        *,
        status: str | None = None,
        completed: int | None = None,
        failed: int | None = None,
        results: list | None = None,
    ) -> dict | None:
        result = await self.session.execute(
            select(BatchJobRecord).where(BatchJobRecord.job_id == job_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        if status is not None:
            record.status = status
        if completed is not None:
            record.completed = completed
        if failed is not None:
            record.failed = failed
        if results is not None:
            record.results = results
        record.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return self._record_to_dict(record)

    @staticmethod
    def _record_to_dict(record: BatchJobRecord) -> dict:
        return {
            "job_id": record.job_id,
            "status": record.status,
            "total": record.total,
            "completed": record.completed,
            "failed": record.failed,
            "results": record.results or [],
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }
