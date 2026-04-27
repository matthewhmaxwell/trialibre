"""Diagnostic: invoke the criterion matcher LLM call exactly once and dump
the raw response. The smoke test surfaced that all criteria came back as
NOT_ENOUGH_INFO; this script shows the actual JSON shape the model returned
so we can fix the parser.

Output: prints the system prompt, user prompt, raw response, and tries
json.loads on it.
"""

from __future__ import annotations

import asyncio
import json
import sys


async def main() -> int:
    from ctm.config import LLMProviderType, MatchingConfig, load_settings
    from ctm.pipeline.matching.criterion_matcher import CriterionMatcher
    from ctm.providers.registry import create_provider
    from ctm.sandbox.loader import get_sample_patient, get_sample_trial

    settings = load_settings()
    settings.llm.provider = LLMProviderType.OLLAMA
    settings.llm.model = "llama3.2:3b"
    settings.llm.base_url = "http://localhost:11434"

    llm = create_provider(settings.llm)
    cfg = MatchingConfig(max_criteria_per_prompt=5, max_patient_tokens=1500)
    matcher = CriterionMatcher(llm, cfg)

    patient = get_sample_patient("SAMPLE-001")
    trial = get_sample_trial("SAMPLE-NCT-001")
    if patient is None or trial is None:
        print("missing sandbox data")
        return 1

    # Preprocess to get numbered sentences
    from ctm.pipeline.matching.patient_preprocessor import preprocess_patient
    patient = preprocess_patient(patient, cfg)

    # Take just the first 5 inclusion criteria
    batch = trial.inclusion_criteria[:5]
    patient_text = patient.to_numbered_text()
    trial_context = matcher._build_trial_context(trial)

    system_prompt = matcher._inclusion_template.render()
    criteria_text = "\n".join(f"{c.index}. {c.text}" for c in batch)
    user_prompt = (
        f"Patient Note:\n{patient_text}\n\n"
        f"Clinical Trial:\n{trial_context}\n\n"
        f"Inclusion Criteria:\n{criteria_text}\n\n"
        f"JSON output:"
    )

    print("=" * 70)
    print("SYSTEM PROMPT:")
    print("-" * 70)
    print(system_prompt)
    print()
    print("=" * 70)
    print("USER PROMPT:")
    print("-" * 70)
    print(user_prompt[:2000])
    print(f"... (total {len(user_prompt)} chars)" if len(user_prompt) > 2000 else "")
    print()
    print("=" * 70)
    print("Calling LLM (this will take ~10-15 min)...")
    import time
    t0 = time.monotonic()
    try:
        raw = await llm.complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        print(f"LLM call failed: {type(e).__name__}: {e}")
        await llm.close()
        return 1
    elapsed = time.monotonic() - t0
    print(f"LLM call took {elapsed:.1f}s")
    print()
    print("=" * 70)
    print("RAW RESPONSE:")
    print("-" * 70)
    print(repr(raw))
    print()
    print("RAW (pretty):")
    print(raw)
    print()

    print("=" * 70)
    print("PARSING ATTEMPT:")
    print("-" * 70)
    text = raw.strip().strip("`")
    if text.startswith("json"):
        text = text[4:].strip()
    try:
        data = json.loads(text)
        print(f"json.loads OK. type = {type(data).__name__}")
        print(f"top-level keys: {list(data.keys()) if isinstance(data, dict) else 'NOT A DICT'}")
        print()
        print("Pretty:")
        print(json.dumps(data, indent=2)[:3000])
        print()
        print("Looking up keys '0' through '4':")
        for i in range(5):
            entry = data.get(str(i))
            print(f"  data['{i}']: type={type(entry).__name__}  value={repr(entry)[:200]}")
    except json.JSONDecodeError as e:
        print(f"json.loads FAILED: {e}")
        print(f"first 500 chars of cleaned text: {text[:500]}")

    await llm.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
