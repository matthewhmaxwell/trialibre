"""HL7 v2 message ingestor for legacy EHR systems."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Hl7v2Ingestor:
    """Extract patient data from HL7 v2 messages (ADT, ORU, etc.)."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".hl7"]

    @property
    def format_name(self) -> str:
        return "HL7 v2 Message"

    async def extract_text(self, source: str | bytes, **kwargs) -> str:
        message = self._read_message(source)
        segments = message.split("\r")
        if not segments:
            segments = message.split("\n")

        parts = []
        for seg in segments:
            fields = seg.split("|")
            seg_type = fields[0] if fields else ""

            if seg_type == "PID":
                parts.append(self._parse_pid(fields))
            elif seg_type == "DG1":
                parts.append(self._parse_dg1(fields))
            elif seg_type == "OBX":
                parts.append(self._parse_obx(fields))
            elif seg_type == "RXA":
                parts.append(self._parse_rxa(fields))

        return ". ".join(p for p in parts if p)

    async def extract_structured(self, source: str | bytes, **kwargs) -> dict:
        message = self._read_message(source)
        segments = message.split("\r")
        if not segments:
            segments = message.split("\n")

        result: dict = {
            "diagnoses": [],
            "medications": [],
            "lab_values": {},
        }

        for seg in segments:
            fields = seg.split("|")
            seg_type = fields[0] if fields else ""

            if seg_type == "PID" and len(fields) > 7:
                # PID-7: Date of Birth
                # PID-8: Sex
                if len(fields) > 8:
                    result["sex"] = fields[8].strip() or None

            elif seg_type == "DG1" and len(fields) > 3:
                # DG1-3: Diagnosis Code
                diag = fields[3].split("^")
                text = diag[1] if len(diag) > 1 else diag[0]
                if text.strip():
                    result["diagnoses"].append(text.strip())

            elif seg_type == "OBX" and len(fields) > 5:
                # OBX-3: Observation ID, OBX-5: Value
                obs_id = fields[3].split("^")
                name = obs_id[1] if len(obs_id) > 1 else obs_id[0]
                value = fields[5].strip()
                if name and value:
                    result["lab_values"][name.strip()] = value

        return result

    def _read_message(self, source: str | bytes) -> str:
        if isinstance(source, bytes):
            return source.decode("utf-8", errors="replace")
        path = Path(source)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
        return source

    def _parse_pid(self, fields: list[str]) -> str:
        parts = []
        if len(fields) > 5:
            name = fields[5].replace("^", " ").strip()
            if name:
                parts.append(f"Patient: {name}")
        if len(fields) > 8 and fields[8].strip():
            parts.append(f"Sex: {fields[8].strip()}")
        return ". ".join(parts)

    def _parse_dg1(self, fields: list[str]) -> str:
        if len(fields) > 3:
            diag = fields[3].split("^")
            text = diag[1] if len(diag) > 1 else diag[0]
            if text.strip():
                return f"Diagnosis: {text.strip()}"
        return ""

    def _parse_obx(self, fields: list[str]) -> str:
        if len(fields) > 5:
            obs = fields[3].split("^")
            name = obs[1] if len(obs) > 1 else obs[0]
            value = fields[5].strip()
            units = fields[6].strip() if len(fields) > 6 else ""
            if name and value:
                return f"{name.strip()}: {value} {units}".strip()
        return ""

    def _parse_rxa(self, fields: list[str]) -> str:
        if len(fields) > 5:
            med = fields[5].split("^")
            text = med[1] if len(med) > 1 else med[0]
            if text.strip():
                return f"Medication: {text.strip()}"
        return ""
