"""Privacy engine: config-driven de-identification and data handling.

De-ID behavior is determined by the privacy configuration:
- LOCAL LLM (Ollama): De-ID OFF (data never leaves device)
- CLOUD LLM (Anthropic/OpenAI): De-ID ON automatically
- User can override in settings
"""

from __future__ import annotations

import logging
from typing import Any

from ctm.config import Settings
from ctm.models.patient import PatientNote

logger = logging.getLogger(__name__)


class PrivacyEngine:
    """Manages de-identification based on configuration.

    Sits between patient ingestion and the LLM pipeline.
    When active, strips PHI before sending to cloud APIs,
    and provides re-identification for local display.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._deid = None
        self._pseudonymizer = None
        self._reidentifier = None

    @property
    def is_active(self) -> bool:
        """Whether de-identification is currently active."""
        return self._settings.should_deid

    async def process_patient(
        self, patient: PatientNote
    ) -> tuple[PatientNote, dict[str, Any]]:
        """Process a patient note through the privacy engine.

        If de-ID is active, strips PHI and returns a de-identified copy.
        If de-ID is inactive, returns the original unchanged.

        Args:
            patient: Original patient note.

        Returns:
            Tuple of (processed patient note, privacy metadata).
            Privacy metadata includes: deid_applied, entities_found, flags.
        """
        metadata: dict[str, Any] = {
            "deid_applied": False,
            "entities_found": [],
            "flags": [],
            "processing_location": "local" if not self._settings.is_cloud_llm else "cloud",
        }

        if not self.is_active:
            logger.debug("De-ID inactive (local processing). Passing through.")
            return patient, metadata

        # Lazy-load Presidio components
        if self._deid is None:
            await self._initialize_deid()

        # De-identify the raw text
        from ctm.privacy.presidio_deid import PresidioDeid

        assert self._deid is not None
        deid_result = await self._deid.deidentify(patient.raw_text, patient.language)

        # Create de-identified copy
        deid_patient = patient.model_copy(
            update={"raw_text": deid_result.anonymized_text}
        )

        # Update sentences with de-identified text
        if patient.sentences:
            from nltk.tokenize import sent_tokenize

            deid_sents = sent_tokenize(deid_result.anonymized_text)
            deid_patient.sentences = [
                type(patient.sentences[0])(id=i, text=s.strip())
                for i, s in enumerate(deid_sents)
                if s.strip()
            ]

        metadata.update({
            "deid_applied": True,
            "entities_found": [
                {"type": e.entity_type, "score": e.score}
                for e in deid_result.entities
            ],
            "flags": deid_result.validation_flags,
        })

        if deid_result.validation_flags:
            logger.warning(
                f"De-ID validation flags for patient {patient.patient_id}: "
                f"{deid_result.validation_flags}"
            )

        return deid_patient, metadata

    async def _initialize_deid(self) -> None:
        """Lazy-initialize de-identification components."""
        from ctm.privacy.presidio_deid import PresidioDeid

        self._deid = PresidioDeid()
        await self._deid.initialize()
        logger.info("Privacy engine initialized with Presidio de-identification")

    def get_status(self) -> dict[str, Any]:
        """Get current privacy status for the UI indicator."""
        if not self._settings.is_cloud_llm:
            return {
                "label": "Private",
                "color": "green",
                "details": [
                    "All processing happens on your device",
                    "No patient data is sent externally",
                ],
                "deid_active": False,
                "processing_location": "local",
            }

        if self.is_active:
            return {
                "label": "Secure",
                "color": "blue",
                "details": [
                    "Patient names and IDs are removed before processing",
                    "Data is sent securely to your AI service, then deleted",
                ],
                "deid_active": True,
                "processing_location": "cloud",
            }

        return {
            "label": "Stored",
            "color": "yellow",
            "details": [
                "Data is sent to your AI service for processing",
                "De-identification is currently disabled",
            ],
            "deid_active": False,
            "processing_location": "cloud",
        }
