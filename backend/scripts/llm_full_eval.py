"""Full evaluation of the real LLM matching pipeline against sandbox ground truth.

Runs every (sandbox patient × sandbox trial) pair through the actual
PipelineOrchestrator + Ollama, captures results, and compares against the
hand-annotated ground truth in sandbox/ground_truth.json.

This is the definitive test that the LLM pipeline produces clinically
plausible output, replacing the circular SandboxMatcher-based metrics.

Output: a JSON results file at sandbox/llm_eval_results.json with one entry
per patient-trial pair, plus an aggregate summary printed at the end.

Usage:
    python scripts/llm_full_eval.py [--patients N] [--trials N] [--model NAME]

Resumes from prior incomplete runs if the results file exists.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--patients", type=int, default=None,
                   help="Cap number of patients (default: all 12)")
    p.add_argument("--trials", type=int, default=None,
                   help="Cap trials per patient (default: all 24)")
    p.add_argument("--model", default="llama3.2:3b",
                   help="Ollama model name (default: llama3.2:3b)")
    p.add_argument("--base-url", default="http://localhost:11434",
                   help="Ollama base URL")
    p.add_argument("--output", default="sandbox/llm_eval_results.json",
                   help="Where to save per-pair results (incremental)")
    p.add_argument("--resume", action="store_true",
                   help="Skip pairs already in the output file")
    return p.parse_args()


async def main() -> int:
    args = parse_args()

    from ctm.config import LLMProviderType, load_settings
    from ctm.pipeline.orchestrator import PipelineOrchestrator
    from ctm.providers.registry import create_provider
    from ctm.sandbox.loader import load_sample_patients, load_sample_protocols

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing results if resuming
    existing: dict[str, dict] = {}
    if args.resume and output_path.exists():
        try:
            existing = {
                f"{r['patient_id']}::{r['trial_id']}": r
                for r in json.loads(output_path.read_text()).get("pairs", [])
            }
            print(f"[resume] {len(existing)} pairs already done, will skip")
        except Exception as e:
            print(f"[resume] couldn't read existing results: {e}; starting fresh")

    # Configure for Ollama, no sandbox
    settings = load_settings()
    settings.llm.provider = LLMProviderType.OLLAMA
    settings.llm.model = args.model
    settings.llm.base_url = args.base_url
    settings.sandbox.enabled = False
    settings.matching.concurrency = 1

    llm = create_provider(settings.llm)
    if not await llm.is_available():
        print(f"[fatal] Ollama at {args.base_url} doesn't have model {args.model}")
        return 1
    print(f"[setup] Ollama ready, model={args.model}")

    # Load sandbox data
    patients = sorted(load_sample_patients(), key=lambda p: p.patient_id)
    protocols = sorted(load_sample_protocols(), key=lambda t: t.nct_id)
    if args.patients:
        patients = patients[: args.patients]
    if args.trials:
        protocols = protocols[: args.trials]

    # Ground truth
    gt_path = Path(__file__).parent.parent / "sandbox" / "ground_truth.json"
    gt_pairs = json.loads(gt_path.read_text()).get("pairs", []) if gt_path.exists() else []
    gt_lookup = {(p["patient_id"], p["trial_id"]): p for p in gt_pairs}

    total_pairs = len(patients) * len(protocols)
    print(f"[setup] {len(patients)} patients × {len(protocols)} trials = {total_pairs} pairs")

    orchestrator = PipelineOrchestrator(settings, llm)

    results: list[dict] = list(existing.values())
    done = len(existing)
    started_at = time.monotonic()

    for pi, patient in enumerate(patients):
        for ti, trial in enumerate(protocols):
            key = f"{patient.patient_id}::{trial.nct_id}"
            if key in existing:
                continue

            t0 = time.monotonic()
            try:
                ranking = await orchestrator.match_patient(
                    patient, [trial], max_trials=1
                )
            except Exception as e:
                elapsed = time.monotonic() - t0
                done += 1
                print(f"[{done}/{total_pairs}] {patient.patient_id} × {trial.nct_id}  "
                      f"ERROR after {elapsed:.0f}s: {type(e).__name__}: {e}")
                results.append({
                    "patient_id": patient.patient_id,
                    "trial_id": trial.nct_id,
                    "error": f"{type(e).__name__}: {e}",
                    "elapsed_s": round(elapsed, 1),
                })
                _save(output_path, results, args.model)
                continue

            elapsed = time.monotonic() - t0
            done += 1

            if not ranking.scores:
                print(f"[{done}/{total_pairs}] {patient.patient_id} × {trial.nct_id}  "
                      f"EMPTY result after {elapsed:.0f}s")
                results.append({
                    "patient_id": patient.patient_id,
                    "trial_id": trial.nct_id,
                    "error": "empty result",
                    "elapsed_s": round(elapsed, 1),
                })
                _save(output_path, results, args.model)
                continue

            score = ranking.scores[0]
            gt = gt_lookup.get((patient.patient_id, trial.nct_id))
            expected = gt.get("expected_strength") if gt else None
            correct = (expected == score.strength.value) if expected else None

            entry = {
                "patient_id": patient.patient_id,
                "trial_id": trial.nct_id,
                "expected_strength": expected,
                "actual_strength": score.strength.value,
                "correct": correct,
                "combined_score": round(score.combined_score, 3),
                "matching_score": round(score.matching_score, 3),
                "relevance_score": round(score.relevance_score, 3),
                "eligibility_score": round(score.eligibility_score, 3),
                "criteria_met": score.criteria_met,
                "criteria_not_met": score.criteria_not_met,
                "criteria_excluded": score.criteria_excluded,
                "criteria_unknown": score.criteria_unknown,
                "criteria_total": score.criteria_total,
                "relevance_explanation": score.relevance_explanation[:300],
                "eligibility_explanation": score.eligibility_explanation[:300],
                "elapsed_s": round(elapsed, 1),
            }
            results.append(entry)

            mark = "✓" if correct else ("✗" if correct is False else "?")
            avg_s = (time.monotonic() - started_at) / max(done - len(existing), 1)
            remaining = (total_pairs - done) * avg_s / 60
            print(f"[{done}/{total_pairs}] {patient.patient_id} × {trial.nct_id}  "
                  f"{score.strength.value:9s} (exp={expected or '?':9s}) {mark}  "
                  f"score={score.combined_score:.2f} elapsed={elapsed:.0f}s  "
                  f"~{remaining:.0f}m remaining")

            # Save every result so we never lose progress
            _save(output_path, results, args.model)

    # Aggregate
    print("\n" + "=" * 70)
    print("  AGGREGATE")
    print("=" * 70)

    scored = [r for r in results if r.get("correct") is not None]
    if scored:
        correct_n = sum(1 for r in scored if r["correct"])
        print(f"  Strength accuracy:  {correct_n}/{len(scored)} = {100*correct_n/len(scored):.1f}%")

        # Per-strength breakdown
        from collections import Counter
        by_expected = Counter(r["expected_strength"] for r in scored)
        for exp_s in ("strong", "possible", "unlikely"):
            subset = [r for r in scored if r["expected_strength"] == exp_s]
            if subset:
                got = Counter(r["actual_strength"] for r in subset)
                print(f"    expected={exp_s:9s} (n={len(subset)}): {dict(got)}")

    errors = [r for r in results if r.get("error")]
    if errors:
        print(f"  Errors: {len(errors)}/{len(results)}")
        for r in errors[:5]:
            print(f"    {r['patient_id']} × {r['trial_id']}: {r.get('error', '')[:80]}")

    durations = [r.get("elapsed_s", 0) for r in results if "elapsed_s" in r]
    if durations:
        durations.sort()
        median = durations[len(durations) // 2]
        print(f"  Latency:  median={median:.1f}s  min={min(durations):.1f}s  max={max(durations):.1f}s")

    print(f"\n  Results saved to: {output_path}")
    await llm.close()
    return 0


def _save(path: Path, results: list[dict], model: str) -> None:
    payload = {
        "model": model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pair_count": len(results),
        "pairs": results,
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
