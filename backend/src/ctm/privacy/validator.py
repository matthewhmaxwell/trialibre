"""De-identification validator.

Flags text that may still contain PHI after de-identification,
for optional human review before sending to cloud APIs.
"""

from __future__ import annotations

import re


class DeidValidator:
    """Validate de-identified text for potential PHI leakage.

    Runs heuristic checks to catch PHI that Presidio may have missed.
    Flags items for human review rather than blocking.
    """

    # Patterns that suggest remaining PHI
    _SUSPICIOUS_PATTERNS = [
        # Potential names (capitalized words not in common medical vocab)
        (r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+[A-Z][a-z]+", "Possible name with title"),
        # Phone-like patterns
        (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "Possible phone number"),
        # Email-like patterns
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Possible email"),
        # SSN-like patterns
        (r"\b\d{3}-\d{2}-\d{4}\b", "Possible SSN"),
        # Date patterns that might contain birth dates
        (r"\b(?:DOB|Date of Birth|Born)\s*[:#]?\s*\d", "Possible date of birth"),
        # Address-like patterns
        (r"\b\d+\s+(?:[A-Z][a-z]+\s+){1,3}(?:St|Ave|Blvd|Dr|Ln|Rd|Way|Ct)\b", "Possible address"),
    ]

    def validate(self, text: str) -> list[str]:
        """Check de-identified text for potential remaining PHI.

        Args:
            text: De-identified text to validate.

        Returns:
            List of warning strings for items that may need human review.
            Empty list means no suspicious patterns found.
        """
        flags = []

        for pattern, description in self._SUSPICIOUS_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                flags.append(
                    f"{description} detected ({len(matches)} occurrence(s)). "
                    "Review recommended before external processing."
                )

        return flags
