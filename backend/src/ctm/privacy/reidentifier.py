"""Re-identification for local display only.

Maps pseudonyms back to original values so the coordinator can see
real patient information in the UI. This mapping NEVER leaves the device.
"""

from __future__ import annotations


class Reidentifier:
    """Reverse pseudonym mapping for local display.

    Stores the mapping from pseudonym -> original value.
    Used only for displaying results to the local user.
    The mapping is session-scoped and never persisted or transmitted.
    """

    def __init__(self) -> None:
        self._reverse_map: dict[str, str] = {}

    def store_mapping(self, pseudonym_mapping: dict[str, str]) -> None:
        """Store a forward mapping (original -> pseudonym) as reverse.

        Args:
            pseudonym_mapping: {cache_key: pseudonym} from Pseudonymizer.
        """
        for key, pseudonym in pseudonym_mapping.items():
            # key format is "ENTITY_TYPE:original_value"
            _, _, original = key.partition(":")
            self._reverse_map[pseudonym] = original

    def reidentify(self, text: str) -> str:
        """Replace pseudonyms with original values in text.

        Args:
            text: Text containing pseudonyms.

        Returns:
            Text with pseudonyms replaced by originals.
        """
        result = text
        # Sort by length descending to avoid partial replacements
        for pseudonym, original in sorted(
            self._reverse_map.items(), key=lambda x: len(x[0]), reverse=True
        ):
            result = result.replace(pseudonym, original)
        return result

    def clear(self) -> None:
        """Clear all mappings (e.g., when session ends)."""
        self._reverse_map.clear()
