"""Record an LLM-pipeline cassette by running the real pipeline once.

Used to (re)generate the cassettes that drive `tests/test_pipeline_cassette.py`.
The cassette captures every LLM request/response pair the orchestrator
makes for a (patient, trial) pair, so CI can replay the full pipeline
without network access.

Defaults to Anthropic + the validated Sonnet model. Costs ~$0.10 per
(patient, trial) pair to record.

Usage:

    # Auth: ANTHROPIC_API_KEY must be set in env.
    python scripts/record_cassette.py \\
        --patient SAMPLE-001 --trial SAMPLE-NCT-001 \\
        --output tests/fixtures/cassettes/sample001_nct001.json
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--patient", default="SAMPLE-001",
                   help="Sandbox patient ID (default: SAMPLE-001)")
    p.add_argument("--trial", default="SAMPLE-NCT-001",
                   help="Sandbox trial ID (default: SAMPLE-NCT-001)")
    p.add_argument("--provider", default="anthropic",
                   choices=["anthropic", "openai", "ollama"])
    p.add_argument("--model", default=None,
                   help="Model override (default: provider-appropriate)")
    p.add_argument("--output", required=True,
                   help="Where to save the cassette JSON")
    return p.parse_args()


async def main() -> int:
    args = parse_args()

    from ctm.config import LLMProviderType, load_settings
    from ctm.pipeline.orchestrator import PipelineOrchestrator
    from ctm.providers.registry import create_provider
    from ctm.sandbox.loader import get_sample_patient, get_sample_trial

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
    from fixtures.recorded_provider import RecordedLLMProvider  # noqa: E402

    settings = load_settings()
    settings.llm.provider = LLMProviderType(args.provider)
    if args.model:
        settings.llm.model = args.model
    settings.sandbox.enabled = False
    settings.matching.concurrency = 1  # serial, so the cassette has a stable order

    real_provider = create_provider(settings.llm)
    print(f"[setup] {args.provider} provider, model={settings.llm.model}")
    print(f"[setup] recording {args.patient} × {args.trial}")

    output_path = Path(args.output)
    recorder = RecordedLLMProvider.recording(
        wrapped=real_provider,
        cassette_path=output_path,
        metadata={
            "test_name": f"{args.patient} × {args.trial}",
            "patient_id": args.patient,
            "trial_id": args.trial,
        },
    )

    patient = get_sample_patient(args.patient)
    trial = get_sample_trial(args.trial)
    if patient is None or trial is None:
        print(f"[fatal] missing sandbox data for {args.patient} or {args.trial}")
        return 1

    orchestrator = PipelineOrchestrator(settings, recorder)
    ranking = await orchestrator.match_patient(patient, [trial], max_trials=1)

    if not ranking.scores:
        print("[fatal] pipeline returned no scores; cassette would be useless")
        return 1

    score = ranking.scores[0]
    print(f"[result] strength={score.strength.value}  combined={score.combined_score:.3f}")
    print(f"[result] criteria: {score.criteria_met} met / {score.criteria_not_met} not / "
          f"{score.criteria_excluded} excl / {score.criteria_unknown} unknown")
    print(f"[result] {recorder.call_count} LLM calls captured")

    recorder.save()
    print(f"[saved] {output_path} ({output_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
