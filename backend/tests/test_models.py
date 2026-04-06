"""Tests for Pydantic model validation."""

import json
from pathlib import Path

from ctm.models.patient import PatientNote
from ctm.models.trial import ClinicalTrial


SANDBOX_DIR = Path(__file__).resolve().parents[1] / "sandbox"


class TestPatientModel:
    def test_load_all_patients(self):
        """All sandbox patients should load without validation errors."""
        patient_dir = SANDBOX_DIR / "patients"
        for path in patient_dir.glob("*.json"):
            data = json.loads(path.read_text())
            patient = PatientNote(**data)
            assert patient.patient_id
            assert patient.raw_text
            assert len(patient.raw_text) > 50

    def test_patient_has_required_fields(self, sample_patient):
        assert sample_patient.patient_id == "SAMPLE-001"
        assert sample_patient.age == 45
        assert sample_patient.sex in ("female", "Female", "F")
        assert len(sample_patient.diagnoses) > 0

    def test_patient_language(self, sample_patient):
        assert sample_patient.language in ("en", "eng", "english", "English")


class TestTrialModel:
    def test_load_all_protocols(self):
        """All sandbox protocols should load without validation errors."""
        proto_dir = SANDBOX_DIR / "protocols"
        for path in proto_dir.glob("*.json"):
            data = json.loads(path.read_text())
            trial = ClinicalTrial(**data)
            assert trial.nct_id
            assert trial.brief_title
            assert len(trial.inclusion_criteria) > 0
            assert len(trial.exclusion_criteria) > 0

    def test_protocol_criteria_count(self, sample_protocols):
        """Each protocol should have realistic criteria counts."""
        for proto in sample_protocols:
            assert len(proto.inclusion_criteria) >= 3, f"{proto.nct_id} has too few inclusion criteria"
            assert len(proto.exclusion_criteria) >= 3, f"{proto.nct_id} has too few exclusion criteria"
