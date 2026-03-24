"""Check patient medications against trial exclusions for drug interactions."""

from __future__ import annotations

import logging

from ctm.models.patient import PatientNote
from ctm.models.trial import ClinicalTrial
from ctm.safety.drug_db import DrugDatabase

logger = logging.getLogger(__name__)


class InteractionChecker:
    """Check for drug interactions between patient meds and trial interventions."""

    def __init__(self) -> None:
        self._db = DrugDatabase()

    async def check(
        self, patient: PatientNote, trial: ClinicalTrial
    ) -> list[dict]:
        """Check for interactions between patient meds and trial drugs.

        Returns:
            List of flagged interactions with severity and description.
        """
        if not patient.medications or not trial.interventions:
            return []

        # Combine patient meds + trial interventions
        all_drugs = list(patient.medications) + list(trial.interventions)
        interactions = await self._db.get_interactions(all_drugs)

        # Filter to only interactions involving both patient meds AND trial drugs
        flags = []
        patient_meds_lower = {m.lower() for m in patient.medications}
        trial_drugs_lower = {d.lower() for d in trial.interventions}

        for interaction in interactions:
            drug_names = [d.lower() for d in interaction.get("drugs", [])]
            has_patient = any(d in patient_meds_lower for d in drug_names)
            has_trial = any(d in trial_drugs_lower for d in drug_names)

            if has_patient and has_trial:
                flags.append(interaction)

        return flags

    async def close(self) -> None:
        await self._db.close()
