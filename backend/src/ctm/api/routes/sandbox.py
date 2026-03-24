"""Sandbox mode endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ctm.sandbox.demo_scenarios import get_demo_scenario, get_demo_scenarios
from ctm.sandbox.loader import (
    get_sandbox_summary,
    get_sample_patient,
    get_sample_trial,
    load_sample_patients,
    load_sample_protocols,
)

router = APIRouter()


@router.get("/sandbox/summary")
async def sandbox_summary():
    """Get summary of available sandbox data."""
    return get_sandbox_summary()


@router.get("/sandbox/patients")
async def sandbox_patients():
    """List all sample patients."""
    patients = load_sample_patients()
    return [
        {
            "patient_id": p.patient_id,
            "age": p.age,
            "sex": p.sex,
            "diagnoses": p.diagnoses,
            "language": p.language,
        }
        for p in patients
    ]


@router.get("/sandbox/patients/{patient_id}")
async def sandbox_patient_detail(patient_id: str):
    """Get a specific sample patient."""
    patient = get_sample_patient(patient_id)
    if not patient:
        raise HTTPException(404, f"Sample patient {patient_id} not found")
    return patient.model_dump()


@router.get("/sandbox/protocols")
async def sandbox_protocols():
    """List all sample trial protocols."""
    trials = load_sample_protocols()
    return [
        {
            "nct_id": t.nct_id,
            "brief_title": t.brief_title,
            "diseases": t.diseases,
            "phase": t.phase,
            "status": t.status,
        }
        for t in trials
    ]


@router.get("/sandbox/protocols/{nct_id}")
async def sandbox_protocol_detail(nct_id: str):
    """Get a specific sample trial protocol."""
    trial = get_sample_trial(nct_id)
    if not trial:
        raise HTTPException(404, f"Sample trial {nct_id} not found")
    return trial.model_dump()


@router.get("/sandbox/scenarios")
async def sandbox_scenarios():
    """List available demo scenarios."""
    scenarios = get_demo_scenarios()
    return [
        {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "patient_id": s.patient_id,
            "highlights": s.highlights,
        }
        for s in scenarios
    ]


@router.get("/sandbox/scenarios/{scenario_id}")
async def sandbox_scenario_detail(scenario_id: str):
    """Get a specific demo scenario."""
    scenario = get_demo_scenario(scenario_id)
    if not scenario:
        raise HTTPException(404, f"Scenario {scenario_id} not found")
    return {
        "id": scenario.id,
        "title": scenario.title,
        "description": scenario.description,
        "patient_id": scenario.patient_id,
        "expected_strong_trials": scenario.expected_strong_trials,
        "expected_possible_trials": scenario.expected_possible_trials,
        "expected_unlikely_trials": scenario.expected_unlikely_trials,
        "highlights": scenario.highlights,
    }
