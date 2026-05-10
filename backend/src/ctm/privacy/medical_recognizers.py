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

    # SSN backup recognizer.
    #
    # Presidio ships a US_SSN recognizer but it failed to flag the canonical
    # `123-45-6789` example in the test_privacy_wireup PHI sample (caught by
    # commit-pending regression test). The likely cause: the built-in scoring
    # discounts SSN-shaped numbers when surrounding context is weak, and our
    # clinical notes don't always have a "SSN:" prefix. We add a high-score
    # catch-all keyed on either the explicit prefix OR the strict
    # ###-##-#### shape, so anything that LOOKS like an SSN is treated as
    # one. False positives here (a 9-digit identifier that happens to match)
    # cost us a redacted token; false negatives leak PHI.
    ssn_backup = PatternRecognizer(
        supported_entity="US_SSN",
        patterns=[
            Pattern(
                name="ssn_with_prefix",
                regex=r"\b(?:SSN|Social\s*Security|SS\s*#)\s*[:#]?\s*\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
                score=0.95,
            ),
            Pattern(
                name="ssn_dashed_strict",
                regex=r"\b\d{3}-\d{2}-\d{4}\b",
                score=0.7,
            ),
        ],
        supported_language="en",
    )
    recognizers.append(ssn_backup)

    # US street address recognizer.
    #
    # Presidio's spaCy-backed LOCATION recognizer catches city / state names
    # (e.g. "Asheville", "NC") but does not catch the street line ("1428
    # Maplewood Drive"). Street addresses are HIPAA Safe Harbor identifier
    # #2 and need to go. Pattern: <number> <Word(s)> <street-suffix>, with
    # the suffix list covering the common abbreviations and full forms.
    street_recognizer = PatternRecognizer(
        supported_entity="LOCATION",
        patterns=[
            Pattern(
                name="us_street_address",
                regex=(
                    r"\b\d{1,6}\s+(?:[A-Z][a-zA-Z]+\s+){1,4}"
                    r"(?:St(?:reet)?|Ave(?:nue)?|Rd|Road|Blvd|Boulevard|"
                    r"Ln|Lane|Dr|Drive|Ct|Court|Pl|Place|Way|Pkwy|Parkway|"
                    r"Cir|Circle|Ter|Terrace|Hwy|Highway)\b\.?"
                ),
                score=0.85,
            ),
            # 5- or 9-digit ZIP — HIPAA Safe Harbor identifier #2.
            Pattern(
                name="us_zip",
                regex=r"\b\d{5}(?:-\d{4})?\b",
                score=0.4,  # low score so a year like 12345 is unlikely to false-positive
            ),
        ],
        supported_language="en",
    )
    recognizers.append(street_recognizer)

    return recognizers
