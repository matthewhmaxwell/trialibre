"""End-to-end smoke test of the real LLM matching pipeline.

Runs SAMPLE-001 (diabetes patient) against SAMPLE-NCT-001 (Dapagliflozin trial)
through the full PipelineOrchestrator with a real Ollama LLM.

Prints every intermediate result so we can diagnose what works and what doesn't.

Usage:
    python scripts/llm_smoke_test.py [PATIENT_ID] [TRIAL_ID]
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path


def _patient_id() -> str:
    return sys.argv[1] if len(sys.argv) > 1 else "SAMPLE-001"


def _trial_id() -> str:
    return sys.argv[2] if len(sys.argv) > 2 else "SAMPLE-NCT-001"


async def main() -> int:
    from ctm.config import LLMProviderType, load_settings
    from ctm.pipeline.orchestrator import PipelineOrchestrator
    from ctm.providers.registry import create_provider
    from ctm.sandbox.loader import get_sample_patient, get_sample_trial

    pid = _patient_id()
    tid = _trial_id()

    print("=" * 70)
    print(f"  LLM SMOKE TEST  — {pid} × {tid}")
    print("=" * 70)

    # 1. Load settings, force Ollama, disable sandbox
    settings = load_settings()
    settings.llm.provider = LLMProviderType.OLLAMA
    settings.llm.model = "llama3.2:3b"
    settings.llm.base_url = "http://localhost:11434"
    settings.sandbox.enabled = False
    settings.matching.concurrency = 1  # serialize so logs are readable

    # 2. Verify Ollama is reachable + model is loaded
    print("\n[1/5] Verifying Ollama is reachable")
    llm = create_provider(settings.llm)
    if not await llm.is_available():
        print(f"  ✗ Ollama at {settings.llm.base_url} doesn't have model {settings.llm.model}")
        print(f"     Run: ollama pull {settings.llm.model}")
        return 1
    print(f"  ✓ Ollama reachable, model={settings.llm.model}")

    # 3. Load the patient + trial
    print(f"\n[2/5] Loading sample data")
    patient = get_sample_patient(pid)
    trial = get_sample_trial(tid)
    if patient is None:
        print(f"  ✗ Patient {pid} not found in sandbox")
        return 1
    if trial is None:
        print(f"  ✗ Trial {tid} not found in sandbox")
        return 1
    print(f"  ✓ Patient: {patient.patient_id}, age {patient.age}, dx={patient.diagnoses[:1]}")
    print(f"  ✓ Trial:   {trial.nct_id} — {trial.brief_title[:60]}")
    print(f"            {len(trial.inclusion_criteria)} inclusion + "
          f"{len(trial.exclusion_criteria)} exclusion criteria")

    # 4. Run the real pipeline
    print(f"\n[3/5] Running PipelineOrchestrator (real LLM)")
    orchestrator = PipelineOrchestrator(settings, llm)

    t0 = time.monotonic()
    try:
        ranking = await orchestrator.match_patient(
            patient, [trial], max_trials=1
        )
    except Exception as e:
        print(f"  ✗ Pipeline crashed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        await llm.close()
        return 1
    elapsed = time.monotonic() - t0
    print(f"  ✓ Pipeline completed in {elapsed:.1f}s")

    # 5. Print results
    print(f"\n[4/5] Match result")
    if not ranking.scores:
        print("  ✗ No scores returned — pipeline produced empty result")
        await llm.close()
        return 1

    score = ranking.scores[0]
    print(f"  Trial:        {score.trial_id}")
    print(f"  Strength:     {score.strength.value.upper()}")
    print(f"  Combined:     {score.combined_score:.3f}")
    print(f"  Matching:     {score.matching_score:.3f}")
    print(f"  Relevance:    {score.relevance_score:.3f}")
    print(f"  Eligibility:  {score.eligibility_score:+.3f}")
    print(f"  Criteria:     {score.criteria_met} met, {score.criteria_not_met} not met, "
          f"{score.criteria_excluded} excluded, {score.criteria_unknown} unknown "
          f"(of {score.criteria_total} total)")
    print(f"\n  Relevance explanation:\n    {score.relevance_explanation}")
    print(f"\n  Eligibility explanation:\n    {score.eligibility_explanation}")

    # 6. Sanity check vs ground truth
    print(f"\n[5/5] Ground truth comparison")
    gt_path = Path(__file__).parent.parent / "sandbox" / "ground_truth.json"
    if gt_path.exists():
        gt = json.loads(gt_path.read_text())
        match = next(
            (p for p in gt.get("pairs", [])
             if p["patient_id"] == pid and p["trial_id"] == tid),
            None,
        )
        if match:
            expected = match["expected_strength"]
            actual = score.strength.value
            icon = "✓" if expected == actual else "≠"
            print(f"  {icon} Expected: {expected}    Got: {actual}")
            print(f"     Notes: {match.get('notes', '')}")
        else:
            print(f"  (no ground truth entry for {pid} × {tid})")
    else:
        print(f"  (ground truth file not found at {gt_path})")

    print()
    print("=" * 70)
    print("  Smoke test passed — pipeline runs end-to-end with real LLM")
    print("=" * 70)
    await llm.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
