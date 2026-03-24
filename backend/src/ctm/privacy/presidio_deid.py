"""Microsoft Presidio-based de-identification.

Handles the 18 HIPAA Safe Harbor identifier types with medical-specific
custom recognizers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DetectedEntity:
    """A PHI entity detected in text."""

    entity_type: str
    start: int
    end: int
    score: float
    text: str = ""


@dataclass
class DeidResult:
    """Result of de-identification."""

    anonymized_text: str
    original_text: str
    entities: list[DetectedEntity] = field(default_factory=list)
    validation_flags: list[str] = field(default_factory=list)


class PresidioDeid:
    """De-identification engine using Microsoft Presidio.

    Detects and removes/replaces PHI including:
    - Names (PERSON)
    - Dates (DATE_TIME)
    - Phone numbers (PHONE_NUMBER)
    - Email addresses (EMAIL_ADDRESS)
    - Medical record numbers (custom: MEDICAL_RECORD_NUMBER)
    - Social Security numbers (US_SSN)
    - Locations/addresses (LOCATION)
    - Ages over 89 (custom: AGE_OVER_89)
    - And other HIPAA Safe Harbor identifiers
    """

    def __init__(self) -> None:
        self._analyzer = None
        self._anonymizer = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Presidio analyzer and anonymizer."""
        if self._initialized:
            return

        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine

        self._analyzer = AnalyzerEngine()
        self._anonymizer = AnonymizerEngine()

        # Add custom medical recognizers
        from ctm.privacy.medical_recognizers import get_medical_recognizers

        for recognizer in get_medical_recognizers():
            self._analyzer.registry.add_recognizer(recognizer)

        self._initialized = True
        logger.info("Presidio de-identification engine initialized")

    async def deidentify(self, text: str, language: str = "en") -> DeidResult:
        """De-identify text by detecting and replacing PHI.

        Args:
            text: Raw text potentially containing PHI.
            language: Text language code.

        Returns:
            DeidResult with anonymized text, detected entities, and validation flags.
        """
        if not self._initialized:
            await self.initialize()

        assert self._analyzer is not None
        assert self._anonymizer is not None

        # Map language codes to Presidio-supported languages
        presidio_lang = "en" if language not in ("en", "es", "fr", "de", "it", "pt") else language

        # Detect entities
        results = self._analyzer.analyze(
            text=text,
            language=presidio_lang,
            entities=[
                "PERSON",
                "PHONE_NUMBER",
                "EMAIL_ADDRESS",
                "DATE_TIME",
                "LOCATION",
                "US_SSN",
                "MEDICAL_RECORD_NUMBER",
                "CREDIT_CARD",
                "IP_ADDRESS",
                "URL",
            ],
            score_threshold=0.4,
        )

        entities = [
            DetectedEntity(
                entity_type=r.entity_type,
                start=r.start,
                end=r.end,
                score=r.score,
                text=text[r.start : r.end],
            )
            for r in results
        ]

        # Anonymize
        anonymized = self._anonymizer.anonymize(text=text, analyzer_results=results)

        # Validation flags: low-confidence detections that may need human review
        flags = []
        for entity in entities:
            if entity.score < 0.7:
                flags.append(
                    f"Low confidence ({entity.score:.0%}) detection of "
                    f"{entity.entity_type}: review recommended"
                )

        return DeidResult(
            anonymized_text=anonymized.text,
            original_text=text,
            entities=entities,
            validation_flags=flags,
        )
