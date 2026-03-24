"""Base ingestor protocol and format detection."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Ingestor(Protocol):
    """Structural interface for format-specific ingestors."""

    @property
    def supported_extensions(self) -> list[str]:
        """File extensions this ingestor handles (e.g., ['.pdf', '.PDF'])."""
        ...

    @property
    def format_name(self) -> str:
        """Human-readable format name (e.g., 'PDF Document')."""
        ...

    async def extract_text(self, source: str | bytes, **kwargs) -> str:
        """Extract text content from the source.

        Args:
            source: File path (str) or raw bytes.

        Returns:
            Extracted plain text.
        """
        ...

    async def extract_structured(self, source: str | bytes, **kwargs) -> dict:
        """Extract structured data if possible.

        Returns:
            Dict with keys like 'diagnoses', 'medications', 'lab_values'.
            Empty dict if structured extraction not supported.
        """
        ...
