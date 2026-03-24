# Trialibre Sandbox Data

This directory contains synthetic sample data for testing, demos, and user onboarding.

**All patient records are fully synthetic.** No real patient data is included.

## Structure

```
sandbox/
├── patients/           # 12 synthetic patient records (JSON)
├── protocols/          # 24 synthetic trial protocols (JSON)
├── expected_results/
│   ├── ground_truth.json           # Patient-trial match labels
│   └── precomputed_matches/        # Pre-computed results for sandbox mode
├── multilingual/       # Non-English patient record variants
└── README.md
```

## Sample Patients

| ID | File | Condition | Age/Sex | Context |
|----|------|-----------|---------|---------|
| SAMPLE-001 | diabetes_45f.json | Type 2 Diabetes | 45F | US |
| SAMPLE-002 | nsclc_62m.json | NSCLC Stage IIIB | 62M | US |
| SAMPLE-003 | breast_cancer_38f.json | HER2+ Breast Cancer | 38F | US |
| SAMPLE-004 | alzheimers_74m.json | Early Alzheimer's | 74M | US |
| SAMPLE-005 | hiv_29m.json | HIV (treatment-naive) | 29M | Kenya |
| SAMPLE-006 | ckd_55f.json | CKD Stage 3b | 55F | US |
| SAMPLE-007 | pediatric_asthma_8m.json | Moderate Asthma | 8M | US |
| SAMPLE-008 | depression_41f.json | Treatment-Resistant MDD | 41F | US |
| SAMPLE-009 | sickle_cell_22f.json | Sickle Cell Disease | 22F | Nigeria |
| SAMPLE-010 | rheumatoid_arthritis_50m.json | Rheumatoid Arthritis | 50M | US |
| SAMPLE-011 | malaria_5f.json | Severe Malaria | 5F | Tanzania |
| SAMPLE-012 | tb_mdr_35m.json | MDR-TB | 35M | India |

## Sample Protocols

Each condition has 2 trial protocols designed to produce different match outcomes:
- One trial is a **strong match** for the corresponding patient
- One trial is **unlikely** or **possible** (demonstrates why patients don't qualify)

## Ground Truth

`expected_results/ground_truth.json` contains the expected match strength for each patient-protocol pair. Used for:
- Sandbox mode (returns precomputed results without LLM calls)
- Golden set testing (regression tests for matching accuracy)
- Demo scenarios (predictable walkthrough results)

## Usage

### Sandbox Mode (no API key)
When a user skips the setup wizard or has no API key configured, Trialibre loads sandbox data automatically. The full UI works with precomputed results.

### Testing
```bash
pytest tests/golden/  # Runs golden set tests against sandbox data
```

### Demo
Demo scenarios are defined in `src/ctm/sandbox/demo_scenarios.py`.
