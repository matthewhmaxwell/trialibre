"""End-to-end pipeline test against a recorded Sonnet cassette.

This is the regression test the project was missing for months. The
criterion parser bug (commit ebd5df5) lived undiscovered because every
existing test stubbed the LLM via SandboxMatcher and skipped the real
matcher → aggregator → ranker path. A cassette test replays a real
Sonnet response through that path with no network access, so any
change that breaks parsing, prompt format, or strength bucketing
fails CI immediately.

Cassette source: SAMPLE-001 (Type 2 diabetes) × SAMPLE-NCT-001
(Dapagliflozin Phase 3) recorded against claude-sonnet-4-5-20250929.
3 LLM calls: inclusion-batch, exclusion-batch, aggregator.

Re-record with `python scripts/record_cassette.py` if prompts change
(Anthropic costs about $0.10).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ctm.config import LLMProviderType, MatchingConfig, load_settings
from ctm.models.matching import EligibilityLabel, MatchStrength
from ctm.pipeline.orchestrator import PipelineOrchestrator
from ctm.sandbox.loader import get_sample_patient, get_sample_trial
from tests.fixtures.recorded_provider import (
    CassetteExhaustedError,
    CassetteMismatchError,
    RecordedLLMProvider,
)

CASSETTE_DIR = Path(__file__).parent / "fixtures" / "cassettes"
SONNET_CASSETTE = CASSETTE_DIR / "sample001_nct001_sonnet.json"


def _settings_for_replay():
    """Settings that match the recording exactly. The cassette is keyed
    on prompt content, so any setting that changes prompt shape (token
    truncation, batch size) must match what was recorded."""
    s = load_settings()
    s.llm.provider = LLMProviderType.ANTHROPIC
    s.llm.model = "claude-sonnet-4-5-20250929"
    s.sandbox.enabled = False
    s.matching = MatchingConfig()  # all defaults — same as the recorder
    s.matching.concurrency = 1
    return s


@pytest.fixture
def cassette() -> RecordedLLMProvider:
    if not SONNET_CASSETTE.exists():
        pytest.skip(
            f"cassette missing: {SONNET_CASSETTE}. Re-record with "
            f"`python scripts/record_cassette.py --output {SONNET_CASSETTE}`."
        )
    return RecordedLLMProvider.from_cassette(SONNET_CASSETTE)


def test_full_pipeline_against_recorded_sonnet(cassette: RecordedLLMProvider):
    """Drive the orchestrator end-to-end with the cassette and assert on
    the final TrialScore. The cassette captured a real Sonnet response
    for SAMPLE-001 × SAMPLE-NCT-001."""

    async def run():
        settings = _settings_for_replay()
        patient = get_sample_patient("SAMPLE-001")
        trial = get_sample_trial("SAMPLE-NCT-001")
        assert patient is not None and trial is not None, \
            "sandbox data missing — install must include sandbox/ fixtures"

        orchestrator = PipelineOrchestrator(settings, cassette)
        ranking = await orchestrator.match_patient(patient, [trial], max_trials=1)
        return ranking

    ranking = asyncio.run(run())

    # Pipeline ran end-to-end and produced a score.
    assert ranking.scores, "orchestrator returned no scores"
    score = ranking.scores[0]
    assert score.trial_id == "SAMPLE-NCT-001"

    # Strength bucketing reaches one of the three buckets — not the default.
    # The exact bucket from this cassette was POSSIBLE; we pin that so a
    # ranker logic regression (e.g. another eligibility-veto bug) is caught.
    assert score.strength == MatchStrength.POSSIBLE
    assert 0.6 < score.combined_score < 0.75

    # The relevance / eligibility scores from the aggregator round-tripped
    # through the parser without being silently zeroed (the original bug
    # signature: every score = 0.0 because the dict-shaped LLM output
    # didn't match the array-shaped parser).
    assert score.relevance_score > 0.5
    assert score.eligibility_score != 0.0

    # Per-criterion explainability data made it through to TrialScore (the
    # "criterion-level explainability" promise from the README; previously
    # CombinedRanker dropped these lists after computing counts).
    assert len(score.inclusion_results) == 10
    assert len(score.exclusion_results) == 10
    assert score.criteria_total == 20

    # The cassette captured a meaningful number of "met" criteria — not
    # zero (the parser-bug failure mode) and not all (the all-correct
    # over-confidence failure mode).
    assert score.criteria_met >= 5

    # Some criteria came back with evidence sentence IDs — the field that
    # the new TrialCard UI renders as monospace chips. If the parser
    # regresses on string-vs-int sentence IDs, this drops to 0.
    total_evidence = sum(
        len(r.evidence_sentence_ids) for r in score.inclusion_results
    )
    assert total_evidence > 0, "no evidence_sentence_ids survived parsing"

    # At least one criterion has populated reasoning (the parser would
    # zero this out if it hit the "no reasoning provided" fallback).
    assert any(r.reasoning and r.reasoning != "No reasoning provided"
               for r in score.inclusion_results)

    # Aggregator explanation is non-empty (caught the case where the
    # aggregator silently fails and we ship empty strings).
    assert score.relevance_explanation
    assert score.eligibility_explanation


def test_cassette_replays_exact_call_count(cassette: RecordedLLMProvider):
    """Sanity check that the cassette has the expected number of LLM calls.
    If the orchestrator's call structure changes (e.g. a new step is added
    that makes a 4th LLM call), this fails loudly so we know to re-record."""
    assert cassette.cassette_size == 3, (
        f"expected 3 LLM calls (inclusion + exclusion + aggregator), got "
        f"{cassette.cassette_size}. Either the cassette is stale or the "
        f"orchestrator changed its call structure."
    )


def test_replay_fails_loudly_when_pipeline_makes_extra_call():
    """If a future change makes the orchestrator call the LLM more times
    than the cassette has, replay should raise CassetteExhaustedError, not
    silently fall back to empty responses."""
    provider = RecordedLLMProvider(calls=[
        {"messages": [{"role": "user", "content": "hi"}], "response": "ok"},
    ])

    async def run():
        await provider.complete([{"role": "user", "content": "hi"}])
        # Second call should fail — only 1 in cassette.
        await provider.complete([{"role": "user", "content": "again"}])

    with pytest.raises(CassetteExhaustedError):
        asyncio.run(run())


def test_replay_fails_with_diff_when_request_drifts():
    """If the orchestrator's prompt changes vs what the cassette recorded,
    replay should fail with a unified diff so the cause is obvious."""
    provider = RecordedLLMProvider(calls=[
        {
            "messages": [{"role": "user", "content": "the original prompt"}],
            "response": "ok",
        },
    ])

    async def run():
        await provider.complete([{"role": "user", "content": "the changed prompt"}])

    with pytest.raises(CassetteMismatchError) as exc:
        asyncio.run(run())
    msg = str(exc.value)
    assert "the original prompt" in msg
    assert "the changed prompt" in msg
    assert "re-record" in msg.lower()
