"""Curated demo scenarios for training and sales demos.

Each scenario walks through a complete workflow with sample data,
demonstrating specific features of Trialibre.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DemoScenario:
    """A curated demo walkthrough."""

    id: str
    title: str
    description: str
    patient_id: str
    expected_strong_trials: list[str]
    expected_possible_trials: list[str]
    expected_unlikely_trials: list[str]
    highlights: list[str]  # Feature highlights to demonstrate


# Predefined demo scenarios
DEMO_SCENARIOS = [
    DemoScenario(
        id="diabetes-screening",
        title="Diabetes Patient Screening",
        description="Screen a Type 2 diabetes patient against available trials. "
        "Demonstrates strong and possible matches with detailed criterion analysis.",
        patient_id="SAMPLE-001",
        expected_strong_trials=["SAMPLE-NCT-001", "SAMPLE-NCT-002"],
        expected_possible_trials=[],
        expected_unlikely_trials=[],
        highlights=[
            "Criterion-by-criterion matching with plain-language explanations",
            "Match strength indicators (Strong/Possible/Unlikely)",
            "One-page print summary generation",
            "Referral creation with WhatsApp sharing",
        ],
    ),
    DemoScenario(
        id="oncology-matching",
        title="Lung Cancer Trial Matching",
        description="Match a Stage IIIB NSCLC patient to immunotherapy and targeted therapy trials. "
        "Shows how biomarker status (PD-L1, EGFR) affects eligibility.",
        patient_id="SAMPLE-002",
        expected_strong_trials=["SAMPLE-NCT-003"],
        expected_possible_trials=[],
        expected_unlikely_trials=["SAMPLE-NCT-004"],
        highlights=[
            "Biomarker-driven matching (PD-L1, EGFR)",
            "Strong vs Unlikely match comparison",
            "Drug interaction checking",
            "Geographic site matching",
        ],
    ),
    DemoScenario(
        id="ledc-hiv",
        title="HIV Treatment in Sub-Saharan Africa",
        description="Match a treatment-naive HIV patient in Kenya to available trials. "
        "Demonstrates LEDC context with geographic and accessibility considerations.",
        patient_id="SAMPLE-005",
        expected_strong_trials=["SAMPLE-NCT-009"],
        expected_possible_trials=[],
        expected_unlikely_trials=["SAMPLE-NCT-010"],
        highlights=[
            "LEDC-context matching",
            "Geographic distance to trial sites",
            "Treatment-naive vs experienced criteria",
            "Multilingual patient note support (Swahili variant available)",
        ],
    ),
    DemoScenario(
        id="pediatric-asthma",
        title="Pediatric Asthma Trial Search",
        description="Find trials for a child with moderate persistent asthma. "
        "Shows age-based eligibility filtering and exacerbation history matching.",
        patient_id="SAMPLE-007",
        expected_strong_trials=["SAMPLE-NCT-013"],
        expected_possible_trials=[],
        expected_unlikely_trials=["SAMPLE-NCT-014"],
        highlights=[
            "Pediatric age-based filtering",
            "Exacerbation frequency matching",
            "Age exclusion demonstration (trial requires 12+, patient is 8)",
        ],
    ),
    DemoScenario(
        id="batch-screening",
        title="Batch Patient Screening",
        description="Screen multiple patients simultaneously against all available trials. "
        "Demonstrates batch processing with progress tracking and cost estimation.",
        patient_id="ALL",  # Uses all sample patients
        expected_strong_trials=[],
        expected_possible_trials=[],
        expected_unlikely_trials=[],
        highlights=[
            "Batch upload and processing",
            "Cost estimation before running",
            "Progress tracking with live updates",
            "Exportable results (CSV/PDF)",
            "Enrollment funnel visualization",
        ],
    ),
]


def get_demo_scenarios() -> list[DemoScenario]:
    """Get all available demo scenarios."""
    return DEMO_SCENARIOS


def get_demo_scenario(scenario_id: str) -> DemoScenario | None:
    """Get a specific demo scenario by ID."""
    for s in DEMO_SCENARIOS:
        if s.id == scenario_id:
            return s
    return None
