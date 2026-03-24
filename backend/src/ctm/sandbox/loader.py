"""Load sandbox sample patients, protocols, and precomputed results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ctm.models.matching import (
    CriterionResult,
    EligibilityLabel,
    MatchingResult,
    MatchStrength,
    PatientTrialRanking,
    TrialScore,
)
from ctm.models.patient import PatientNote, PatientSentence
from ctm.models.trial import ClinicalTrial, EligibilityCriteria


def _sandbox_dir() -> Path:
    """Get the sandbox data directory."""
    # Look relative to the backend package
    candidates = [
        Path(__file__).parent.parent.parent.parent / "sandbox",  # src/ctm/sandbox -> sandbox/
        Path("sandbox"),
        Path("backend/sandbox"),
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("Sandbox data directory not found")


def load_sample_patients() -> list[PatientNote]:
    """Load all sample patient records from the sandbox."""
    patients_dir = _sandbox_dir() / "patients"
    patients = []
    for path in sorted(patients_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        # Build sentences from raw_text
        raw = data.get("raw_text", "")
        import nltk

        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            nltk.download("punkt_tab", quiet=True)

        from nltk.tokenize import sent_tokenize

        sents = sent_tokenize(raw)
        data["sentences"] = [
            {"id": i, "text": s.strip()} for i, s in enumerate(sents) if s.strip()
        ]
        patients.append(PatientNote(**data))
    return patients


def load_sample_protocols() -> list[ClinicalTrial]:
    """Load all sample trial protocols from the sandbox."""
    protocols_dir = _sandbox_dir() / "protocols"
    trials = []
    for path in sorted(protocols_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        # Convert criteria dicts to EligibilityCriteria objects
        if "inclusion_criteria" in data:
            data["inclusion_criteria"] = [
                EligibilityCriteria(**c) if isinstance(c, dict) else c
                for c in data["inclusion_criteria"]
            ]
        if "exclusion_criteria" in data:
            data["exclusion_criteria"] = [
                EligibilityCriteria(**c) if isinstance(c, dict) else c
                for c in data["exclusion_criteria"]
            ]
        trials.append(ClinicalTrial(**data))
    return trials


def load_ground_truth() -> dict[str, dict[str, str]]:
    """Load ground truth match labels.

    Returns: {patient_id: {trial_id: "strong"|"possible"|"unlikely"}}
    """
    gt_path = _sandbox_dir() / "expected_results" / "ground_truth.json"
    if not gt_path.exists():
        return {}
    return json.loads(gt_path.read_text(encoding="utf-8"))


def load_precomputed_matches() -> dict[str, PatientTrialRanking]:
    """Load precomputed match results for sandbox mode (no LLM needed).

    Returns: {patient_id: PatientTrialRanking}
    """
    matches_dir = _sandbox_dir() / "expected_results" / "precomputed_matches"
    if not matches_dir.exists():
        return {}

    results = {}
    for path in sorted(matches_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        patient_id = data.get("patient_id", path.stem)
        results[patient_id] = PatientTrialRanking(**data)
    return results


def load_multilingual_patients() -> list[PatientNote]:
    """Load multilingual variants of sample patients."""
    ml_dir = _sandbox_dir() / "multilingual"
    if not ml_dir.exists():
        return []

    patients = []
    for path in sorted(ml_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        patients.append(PatientNote(**data))
    return patients


def get_sample_patient(patient_id: str) -> PatientNote | None:
    """Get a specific sample patient by ID."""
    for p in load_sample_patients():
        if p.patient_id == patient_id:
            return p
    return None


def get_sample_trial(nct_id: str) -> ClinicalTrial | None:
    """Get a specific sample trial by NCT ID."""
    for t in load_sample_protocols():
        if t.nct_id == nct_id:
            return t
    return None


def get_sandbox_summary() -> dict[str, Any]:
    """Get a summary of available sandbox data."""
    patients = load_sample_patients()
    trials = load_sample_protocols()
    gt = load_ground_truth()
    ml = load_multilingual_patients()

    return {
        "patients_count": len(patients),
        "trials_count": len(trials),
        "ground_truth_pairs": sum(len(v) for v in gt.values()),
        "multilingual_variants": len(ml),
        "conditions_covered": list({d for p in patients for d in p.diagnoses}),
        "languages_available": list({p.language for p in patients + ml}),
    }
