"""Referral service for patient-trial referrals."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone

from ctm.models.matching import TrialScore
from ctm.models.patient import PatientNote
from ctm.models.referral import Referral, ReferralDelivery, ReferralStatus
from ctm.models.trial import ClinicalTrial

logger = logging.getLogger(__name__)


class ReferralService:
    """Create and manage patient-to-trial referrals."""

    def __init__(self) -> None:
        self._referrals: dict[str, Referral] = {}

    def create_referral(
        self,
        patient: PatientNote,
        trial: ClinicalTrial,
        score: TrialScore,
        coordinator: str = "",
        delivery: ReferralDelivery = ReferralDelivery.PDF,
        site_index: int = 0,
        notes: str = "",
    ) -> Referral:
        """Create a new referral."""
        ref_id = f"REF-{uuid.uuid4().hex[:8].upper()}"

        site = trial.sites[site_index] if trial.sites and site_index < len(trial.sites) else None

        # Generate secure link
        token = hashlib.sha256(f"{ref_id}:{datetime.now().isoformat()}".encode()).hexdigest()[:32]
        secure_url = f"/referral/{ref_id}?token={token}"

        referral = Referral(
            referral_id=ref_id,
            patient_id=patient.patient_id,
            trial_id=trial.nct_id,
            trial_title=trial.brief_title,
            site_name=site.facility if site else "",
            site_contact=site.contact_email if site else "",
            status=ReferralStatus.CREATED,
            delivery_method=delivery,
            referring_coordinator=coordinator,
            match_strength=score.strength.value,
            match_summary=self._build_summary(score),
            notes=notes,
            secure_link_url=secure_url,
            secure_link_expires=datetime.now(timezone.utc) + timedelta(days=7),
            status_history=[{
                "status": "created",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "by": coordinator or "system",
            }],
        )

        self._referrals[ref_id] = referral
        return referral

    def update_status(
        self, referral_id: str, new_status: ReferralStatus, updated_by: str = ""
    ) -> Referral | None:
        """Update referral status."""
        referral = self._referrals.get(referral_id)
        if not referral:
            return None

        referral.status = new_status
        referral.updated_at = datetime.now(timezone.utc)
        referral.status_history.append({
            "status": new_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "by": updated_by or "system",
        })

        return referral

    def get_referral(self, referral_id: str) -> Referral | None:
        return self._referrals.get(referral_id)

    def list_referrals(
        self, patient_id: str | None = None, trial_id: str | None = None
    ) -> list[Referral]:
        """List referrals, optionally filtered."""
        refs = list(self._referrals.values())
        if patient_id:
            refs = [r for r in refs if r.patient_id == patient_id]
        if trial_id:
            refs = [r for r in refs if r.trial_id == trial_id]
        return sorted(refs, key=lambda r: r.created_at, reverse=True)

    def _build_summary(self, score: TrialScore) -> str:
        return (
            f"{score.strength.value.title()} Match. "
            f"{score.criteria_met} of {score.criteria_total} criteria met, "
            f"{score.criteria_unknown} could not be verified."
        )
