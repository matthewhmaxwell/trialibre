"""Ground truth loader for evaluation.

Ground truth JSON format:
{
  "pairs": [
    {
      "patient_id": "SAMPLE-001",
      "trial_id": "SAMPLE-NCT-001",
      "expected_label": "eligible",       // eligible | excluded | unknown
      "expected_strength": "strong",       // strong | possible | unlikely
      "notes": "Patient meets all inclusion criteria"
    }
  ]
}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GroundTruthPair:
    patient_id: str
    trial_id: str
    expected_label: str  # eligible, excluded, unknown
    expected_strength: str  # strong, possible, unlikely
    notes: str = ""


@dataclass
class GroundTruth:
    pairs: list[GroundTruthPair] = field(default_factory=list)

    def for_patient(self, patient_id: str) -> list[GroundTruthPair]:
        return [p for p in self.pairs if p.patient_id == patient_id]

    def for_trial(self, trial_id: str) -> list[GroundTruthPair]:
        return [p for p in self.pairs if p.trial_id == trial_id]

    @property
    def patient_ids(self) -> set[str]:
        return {p.patient_id for p in self.pairs}

    @property
    def trial_ids(self) -> set[str]:
        return {p.trial_id for p in self.pairs}


def load_ground_truth(path: Path) -> GroundTruth:
    """Load ground truth from JSON file."""
    data = json.loads(path.read_text())
    pairs = [
        GroundTruthPair(
            patient_id=p["patient_id"],
            trial_id=p["trial_id"],
            expected_label=p.get("expected_label", "unknown"),
            expected_strength=p.get("expected_strength", "unknown"),
            notes=p.get("notes", ""),
        )
        for p in data.get("pairs", [])
    ]
    return GroundTruth(pairs=pairs)
