"""CSV/Excel tabular data ingestor."""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Common column name mappings to structured fields
_COLUMN_MAP = {
    "age": "age",
    "patient_age": "age",
    "sex": "sex",
    "gender": "sex",
    "patient_sex": "sex",
    "diagnosis": "diagnoses",
    "diagnoses": "diagnoses",
    "condition": "diagnoses",
    "primary_diagnosis": "diagnoses",
    "medication": "medications",
    "medications": "medications",
    "drugs": "medications",
    "current_medications": "medications",
}


class CsvIngestor:
    """Extract patient data from CSV/Excel files."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".csv", ".tsv", ".xlsx", ".xls"]

    @property
    def format_name(self) -> str:
        return "Spreadsheet (CSV/Excel)"

    async def extract_text(self, source: str | bytes, **kwargs) -> str:
        rows = await self._read_rows(source)
        if not rows:
            return ""

        # Convert rows to narrative text
        parts = []
        for row in rows:
            line_parts = []
            for key, value in row.items():
                if value and str(value).strip():
                    line_parts.append(f"{key}: {value}")
            if line_parts:
                parts.append(". ".join(line_parts))

        return "\n\n".join(parts)

    async def extract_structured(self, source: str | bytes, **kwargs) -> dict:
        rows = await self._read_rows(source)
        if not rows:
            return {}

        # Use first row for single-patient files
        row = rows[0]
        structured: dict = {}

        for col_name, value in row.items():
            normalized = col_name.lower().strip().replace(" ", "_")
            if normalized in _COLUMN_MAP:
                field = _COLUMN_MAP[normalized]
                if field in ("diagnoses", "medications"):
                    # Split comma-separated values
                    items = [v.strip() for v in str(value).split(",") if v.strip()]
                    structured[field] = items
                elif field == "age":
                    try:
                        structured[field] = int(float(str(value)))
                    except (ValueError, TypeError):
                        pass
                else:
                    structured[field] = str(value).strip()

        return structured

    async def _read_rows(self, source: str | bytes) -> list[dict]:
        path = Path(source) if isinstance(source, str) else None

        if path and path.suffix.lower() in (".xlsx", ".xls"):
            return await self._read_excel(path)

        # CSV/TSV
        if isinstance(source, bytes):
            text = source.decode("utf-8", errors="replace")
        elif path and path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
        else:
            text = source if isinstance(source, str) else ""

        dialect = csv.Sniffer().sniff(text[:2048]) if text else csv.excel
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        return list(reader)

    async def _read_excel(self, path: Path) -> list[dict]:
        import openpyxl

        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            return []

        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            return []

        headers = [str(h or f"col_{i}").strip() for i, h in enumerate(rows[0])]
        result = []
        for row in rows[1:]:
            result.append(dict(zip(headers, [str(v) if v is not None else "" for v in row])))

        wb.close()
        return result
