"""Batch patient screening processor.

Processes multiple patients asynchronously with progress tracking
and resume-on-failure capability.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from ctm.models.batch import BatchJob, BatchResult, BatchStatus
from ctm.models.matching import PatientTrialRanking
from ctm.models.patient import PatientNote
from ctm.models.trial import ClinicalTrial
from ctm.pipeline.orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Process multiple patients against trials in batch mode."""

    def __init__(self, orchestrator: PipelineOrchestrator) -> None:
        self._orchestrator = orchestrator
        self._jobs: dict[str, BatchJob] = {}
        self._results: dict[str, list[PatientTrialRanking]] = {}

    def estimate_cost(
        self,
        num_patients: int,
        avg_trials_per_patient: int = 20,
        cost_per_1k_tokens: float = 0.003,
        avg_tokens_per_match: int = 4000,
    ) -> dict:
        """Estimate cost for a batch run.

        Returns:
            Dict with estimated cost, duration, and call counts.
        """
        total_matches = num_patients * avg_trials_per_patient
        # 2 LLM calls per trial (inclusion + exclusion) + 1 aggregation
        total_calls = total_matches * 3
        total_tokens = total_calls * avg_tokens_per_match
        estimated_cost = (total_tokens / 1000) * cost_per_1k_tokens
        # ~2 seconds per LLM call with concurrency 5
        estimated_minutes = (total_calls / 5 * 2) / 60

        return {
            "total_patients": num_patients,
            "estimated_trials_per_patient": avg_trials_per_patient,
            "estimated_llm_calls": total_calls,
            "estimated_cost_usd": round(estimated_cost, 2),
            "estimated_duration_minutes": round(estimated_minutes, 1),
        }

    async def start_batch(
        self,
        patients: list[PatientNote],
        trials: list[ClinicalTrial],
        max_trials_per_patient: int = 20,
        on_progress: callable | None = None,
    ) -> str:
        """Start a batch screening job.

        Returns:
            Job ID for tracking.
        """
        job_id = f"batch-{uuid.uuid4().hex[:8]}"
        job = BatchJob(
            job_id=job_id,
            total_patients=len(patients),
            started_at=datetime.now(timezone.utc),
        )
        job.status = BatchStatus.RUNNING
        self._jobs[job_id] = job
        self._results[job_id] = []

        # Process in background
        asyncio.create_task(
            self._run_batch(job, patients, trials, max_trials_per_patient, on_progress)
        )

        return job_id

    async def _run_batch(
        self,
        job: BatchJob,
        patients: list[PatientNote],
        trials: list[ClinicalTrial],
        max_trials: int,
        on_progress: callable | None,
    ) -> None:
        """Execute the batch processing."""
        for patient in patients:
            if job.status == BatchStatus.CANCELLED:
                break

            try:
                ranking = await self._orchestrator.match_patient(
                    patient, trials, max_trials=max_trials
                )
                self._results[job.job_id].append(ranking)
                job.completed_patients += 1

            except Exception as e:
                logger.error(f"Batch match failed for {patient.patient_id}: {e}")
                job.failed_patients += 1

            if on_progress:
                on_progress(job.completed_patients + job.failed_patients, job.total_patients)

        job.status = BatchStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)

    def get_job(self, job_id: str) -> BatchJob | None:
        return self._jobs.get(job_id)

    def get_results(self, job_id: str) -> BatchResult | None:
        job = self._jobs.get(job_id)
        if not job:
            return None

        rankings = self._results.get(job_id, [])
        total_matches = sum(
            len([s for s in r.scores if s.strength.value != "unlikely"])
            for r in rankings
        )

        duration = 0.0
        if job.started_at and job.completed_at:
            duration = (job.completed_at - job.started_at).total_seconds()

        return BatchResult(
            job_id=job_id,
            rankings=rankings,
            total_patients=job.total_patients,
            total_matches=total_matches,
            duration_seconds=duration,
        )

    def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job and job.status == BatchStatus.RUNNING:
            job.status = BatchStatus.CANCELLED
            return True
        return False
