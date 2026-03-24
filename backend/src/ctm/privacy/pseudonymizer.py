"""Consistent pseudonym generation for de-identified data.

Replaces PHI with consistent fake values so that the same real name
always maps to the same pseudonym within a session. This preserves
readability of the clinical note while protecting privacy.
"""

from __future__ import annotations

import hashlib
from typing import Any

# Pseudonym pools
_FIRST_NAMES = [
    "Alex", "Jordan", "Morgan", "Casey", "Riley",
    "Taylor", "Quinn", "Avery", "Dakota", "Reese",
    "Sage", "Rowan", "Blake", "Parker", "Drew",
]

_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones",
    "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Anderson", "Thomas", "Wilson", "Moore", "Taylor",
]

_CITIES = [
    "Springfield", "Riverside", "Fairview", "Greenville", "Madison",
    "Franklin", "Clinton", "Georgetown", "Burlington", "Ashland",
]


class Pseudonymizer:
    """Generate consistent pseudonyms for PHI replacement.

    The same input always produces the same pseudonym within a session,
    maintaining internal consistency (e.g., if "Dr. Smith" appears
    multiple times, it's always replaced with the same fake name).
    """

    def __init__(self, seed: str = "trialibre") -> None:
        self._seed = seed
        self._mapping: dict[str, str] = {}

    def pseudonymize(self, value: str, entity_type: str) -> str:
        """Generate a consistent pseudonym for a PHI value.

        Args:
            value: The original PHI value.
            entity_type: The type of entity (PERSON, LOCATION, etc.)

        Returns:
            A consistent fake replacement value.
        """
        cache_key = f"{entity_type}:{value}"
        if cache_key in self._mapping:
            return self._mapping[cache_key]

        idx = self._hash_to_index(value)

        if entity_type == "PERSON":
            pseudo = f"{_FIRST_NAMES[idx % len(_FIRST_NAMES)]} {_LAST_NAMES[idx % len(_LAST_NAMES)]}"
        elif entity_type == "LOCATION":
            pseudo = _CITIES[idx % len(_CITIES)]
        elif entity_type == "DATE_TIME":
            pseudo = "[DATE REDACTED]"
        elif entity_type == "PHONE_NUMBER":
            pseudo = f"(555) {idx % 900 + 100:03d}-{idx % 9000 + 1000:04d}"
        elif entity_type == "EMAIL_ADDRESS":
            name = _FIRST_NAMES[idx % len(_FIRST_NAMES)].lower()
            pseudo = f"{name}@example.com"
        elif entity_type in ("US_SSN", "MEDICAL_RECORD_NUMBER", "HEALTH_PLAN_ID"):
            pseudo = f"[{entity_type} REDACTED]"
        else:
            pseudo = f"[{entity_type} REDACTED]"

        self._mapping[cache_key] = pseudo
        return pseudo

    def get_mapping(self) -> dict[str, str]:
        """Get the current pseudonym mapping (for re-identification)."""
        return dict(self._mapping)

    def _hash_to_index(self, value: str) -> int:
        """Hash a value to a stable integer index."""
        h = hashlib.sha256(f"{self._seed}:{value}".encode()).hexdigest()
        return int(h[:8], 16)
