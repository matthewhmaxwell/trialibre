"""PDF document ingestor."""

from __future__ import annotations

import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PdfIngestor:
    """Extract text from PDF documents (discharge summaries, lab reports, etc.)."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    @property
    def format_name(self) -> str:
        return "PDF Document"

    async def extract_text(self, source: str | bytes, **kwargs) -> str:
        from pypdf import PdfReader

        if isinstance(source, bytes):
            reader = PdfReader(io.BytesIO(source))
        else:
            reader = PdfReader(source)

        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())

        full_text = "\n\n".join(pages)

        if not full_text.strip():
            logger.warning("PDF appears to be image-based (no extractable text). Try OCR.")

        return full_text

    async def extract_structured(self, source: str | bytes, **kwargs) -> dict:
        return {}
