"""Format auto-detection for patient data files."""

from __future__ import annotations

import mimetypes
from pathlib import Path

# Format detection mapping
_EXTENSION_MAP = {
    ".txt": "text",
    ".text": "text",
    ".pdf": "pdf",
    ".doc": "docx",
    ".docx": "docx",
    ".csv": "csv",
    ".tsv": "csv",
    ".xlsx": "csv",
    ".xls": "csv",
    ".json": "json",
    ".xml": "xml",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".tiff": "image",
    ".tif": "image",
    ".bmp": "image",
    ".hl7": "hl7v2",
}

# Magic bytes for format detection
_MAGIC_BYTES = {
    b"%PDF": "pdf",
    b"PK\x03\x04": "docx",  # ZIP-based (DOCX, XLSX)
    b"\xff\xd8\xff": "image",  # JPEG
    b"\x89PNG": "image",  # PNG
    b"MSH|": "hl7v2",  # HL7 v2 message
}


def detect_format(source: str | bytes | Path) -> str:
    """Auto-detect the format of a file or data.

    Args:
        source: File path or raw bytes.

    Returns:
        Format identifier: 'text', 'pdf', 'docx', 'csv', 'json', 'xml',
        'image', 'hl7v2', 'fhir'.
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.exists():
            # Check extension first
            ext = path.suffix.lower()
            if ext in _EXTENSION_MAP:
                detected = _EXTENSION_MAP[ext]
                # Special case: JSON could be FHIR
                if detected == "json":
                    return _check_fhir_json(path)
                return detected

            # Fall back to magic bytes
            with open(path, "rb") as f:
                header = f.read(16)
            return _detect_from_bytes(header)

        # It's a string but not a file path - treat as text
        if isinstance(source, str):
            return _detect_from_content(source)

    if isinstance(source, bytes):
        return _detect_from_bytes(source[:16])

    return "text"


def _detect_from_bytes(header: bytes) -> str:
    """Detect format from file header bytes."""
    for magic, fmt in _MAGIC_BYTES.items():
        if header.startswith(magic):
            return fmt
    return "text"


def _detect_from_content(text: str) -> str:
    """Detect format from text content."""
    stripped = text.strip()

    # FHIR JSON
    if stripped.startswith("{") and '"resourceType"' in stripped[:200]:
        return "fhir"

    # HL7 v2
    if stripped.startswith("MSH|"):
        return "hl7v2"

    # XML (possibly FHIR)
    if stripped.startswith("<?xml") or stripped.startswith("<"):
        if "fhir" in stripped[:500].lower() or "Bundle" in stripped[:500]:
            return "fhir"
        return "xml"

    # JSON
    if stripped.startswith("{") or stripped.startswith("["):
        return "json"

    return "text"


def _check_fhir_json(path: Path) -> str:
    """Check if a JSON file is FHIR."""
    try:
        with open(path, "r") as f:
            content = f.read(500)
        if '"resourceType"' in content:
            return "fhir"
    except Exception:
        pass
    return "json"
