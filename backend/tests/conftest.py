"""Shared test fixtures."""

import json
from pathlib import Path

import pytest

from ctm.config import load_settings
from ctm.models.patient import PatientNote
from ctm.models.trial import ClinicalTrial


SANDBOX_DIR = Path(__file__).resolve().parents[1] / "sandbox"


@pytest.fixture
def settings():
    """Load default settings with sandbox enabled."""
    s = load_settings()
    s.sandbox.enabled = True
    return s


@pytest.fixture
def sample_patient() -> PatientNote:
    """Load the diabetes sample patient."""
    path = SANDBOX_DIR / "patients" / "diabetes_45f.json"
    data = json.loads(path.read_text())
    return PatientNote(**data)


@pytest.fixture
def sample_patients() -> list[PatientNote]:
    """Load all sample patients."""
    patients = []
    patient_dir = SANDBOX_DIR / "patients"
    for p in sorted(patient_dir.glob("*.json")):
        data = json.loads(p.read_text())
        patients.append(PatientNote(**data))
    return patients


@pytest.fixture
def sample_protocols() -> list[ClinicalTrial]:
    """Load all sample trial protocols."""
    protocols = []
    proto_dir = SANDBOX_DIR / "protocols"
    for p in sorted(proto_dir.glob("*.json")):
        data = json.loads(p.read_text())
        protocols.append(ClinicalTrial(**data))
    return protocols


@pytest.fixture
def ground_truth():
    """Load ground truth for evaluation."""
    from ctm.evaluation.ground_truth import load_ground_truth
    return load_ground_truth(SANDBOX_DIR / "ground_truth.json")
