"""HL7 FHIR R4 JSON/XML ingestor.

Extracts patient data from FHIR resources (Patient, Condition,
MedicationStatement, Observation, etc.).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FhirIngestor:
    """Extract patient data from FHIR R4 resources."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".json"]  # FHIR JSON

    @property
    def format_name(self) -> str:
        return "HL7 FHIR R4"

    async def extract_text(self, source: str | bytes, **kwargs) -> str:
        data = self._parse(source)
        structured = await self.extract_structured(source)

        parts = []
        if structured.get("age"):
            parts.append(f"Age: {structured['age']}")
        if structured.get("sex"):
            parts.append(f"Sex: {structured['sex']}")
        if structured.get("diagnoses"):
            parts.append(f"Diagnoses: {', '.join(structured['diagnoses'])}")
        if structured.get("medications"):
            parts.append(f"Medications: {', '.join(structured['medications'])}")
        if structured.get("lab_values"):
            labs = [f"{k}: {v}" for k, v in structured["lab_values"].items()]
            parts.append(f"Lab Values: {', '.join(labs)}")
        if structured.get("medical_history"):
            parts.append(f"History: {', '.join(structured['medical_history'])}")

        return ". ".join(parts) if parts else json.dumps(data, indent=2)

    async def extract_structured(self, source: str | bytes, **kwargs) -> dict:
        data = self._parse(source)
        resource_type = data.get("resourceType", "")

        if resource_type == "Bundle":
            return self._extract_from_bundle(data)
        elif resource_type == "Patient":
            return self._extract_from_patient(data)
        else:
            return {}

    def _parse(self, source: str | bytes) -> dict:
        if isinstance(source, bytes):
            try:
                return json.loads(source.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                raise ValueError(f"Invalid FHIR JSON (bytes): {e}")
        # Try as JSON string first, then as file path
        if isinstance(source, str) and source.lstrip().startswith(("{", "[")):
            try:
                return json.loads(source)
            except json.JSONDecodeError:
                pass
        try:
            path = Path(source)
            if len(str(path)) < 1024 and path.exists() and path.is_file():
                return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            pass
        try:
            return json.loads(source)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse as FHIR JSON: {e}")

    def _extract_from_bundle(self, bundle: dict) -> dict:
        result: dict = {
            "diagnoses": [],
            "medications": [],
            "lab_values": {},
            "medical_history": [],
        }

        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            rt = resource.get("resourceType", "")

            if rt == "Patient":
                patient_data = self._extract_from_patient(resource)
                result.update({k: v for k, v in patient_data.items() if v})

            elif rt == "Condition":
                code = resource.get("code", {})
                text = code.get("text", "")
                if not text:
                    codings = code.get("coding", [])
                    text = codings[0].get("display", "") if codings else ""
                if text:
                    result["diagnoses"].append(text)

            elif rt in ("MedicationStatement", "MedicationRequest"):
                med = resource.get("medicationCodeableConcept", {})
                text = med.get("text", "")
                if not text:
                    codings = med.get("coding", [])
                    text = codings[0].get("display", "") if codings else ""
                if text:
                    result["medications"].append(text)

            elif rt == "Observation":
                code = resource.get("code", {})
                name = code.get("text", "")
                if not name:
                    codings = code.get("coding", [])
                    name = codings[0].get("display", "") if codings else ""
                value = resource.get("valueQuantity", {})
                if name and value:
                    val_str = f"{value.get('value', '')} {value.get('unit', '')}".strip()
                    result["lab_values"][name] = val_str

        return result

    def _extract_from_patient(self, patient: dict) -> dict:
        result: dict = {}

        # Age from birthDate
        birth_date = patient.get("birthDate")
        if birth_date:
            from datetime import date

            try:
                bd = date.fromisoformat(birth_date)
                today = date.today()
                result["age"] = today.year - bd.year - (
                    (today.month, today.day) < (bd.month, bd.day)
                )
            except (ValueError, TypeError):
                pass

        # Sex
        result["sex"] = patient.get("gender", "").capitalize()

        return result
