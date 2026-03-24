"""Plain text ingestor."""

from __future__ import annotations

from pathlib import Path


class TextIngestor:
    """Ingest plain text patient notes."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".txt", ".text"]

    @property
    def format_name(self) -> str:
        return "Plain Text"

    async def extract_text(self, source: str | bytes, **kwargs) -> str:
        if isinstance(source, bytes):
            return source.decode("utf-8", errors="replace")
        path = Path(source)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
        # source is the text itself
        return source

    async def extract_structured(self, source: str | bytes, **kwargs) -> dict:
        return {}
