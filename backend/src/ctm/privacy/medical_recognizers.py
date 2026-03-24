"""Custom Presidio recognizers for medical-specific PHI patterns."""

from __future__ import annotations


def get_medical_recognizers() -> list:
    """Get custom medical PHI recognizers for Presidio.

    These supplement Presidio's built-in recognizers with patterns
    specific to clinical/medical records.
    """
    from presidio_analyzer import PatternRecognizer, Pattern

    recognizers = []

    # Medical Record Number (MRN) patterns
    # Common formats: MRN-123456, MRN: 123456, MRN#123456
    mrn_recognizer = PatternRecognizer(
        supported_entity="MEDICAL_RECORD_NUMBER",
        patterns=[
            Pattern(
                name="mrn_prefix",
                regex=r"\b(?:MRN|mrn|M\.R\.N\.|Med\.?\s*Rec\.?\s*(?:No\.?|#)?)\s*[:#]?\s*\d{4,10}\b",
                score=0.85,
            ),
            Pattern(
                name="patient_id_prefix",
                regex=r"\b(?:Patient\s*(?:ID|Id|id|#)|PID|Pt\s*#)\s*[:#]?\s*\d{4,10}\b",
                score=0.8,
            ),
            Pattern(
                name="accession_number",
                regex=r"\b(?:Accession\s*(?:No\.?|#|Number)?)\s*[:#]?\s*[A-Z]?\d{6,12}\b",
                score=0.75,
            ),
        ],
        supported_language="en",
    )
    recognizers.append(mrn_recognizer)

    # Health plan ID numbers
    health_plan_recognizer = PatternRecognizer(
        supported_entity="HEALTH_PLAN_ID",
        patterns=[
            Pattern(
                name="insurance_id",
                regex=r"\b(?:Insurance|Policy|Member|Subscriber)\s*(?:ID|Id|#|No\.?)\s*[:#]?\s*[A-Z0-9]{6,15}\b",
                score=0.7,
            ),
        ],
        supported_language="en",
    )
    recognizers.append(health_plan_recognizer)

    return recognizers
