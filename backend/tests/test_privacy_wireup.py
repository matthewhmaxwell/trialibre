"""Regression test for the de-ID wireup.

The README's headline privacy promise is: "Built-in de-identification
(via Presidio) strips PHI before sending to any cloud LLM." Until this
test landed, that path was claimed-but-unwired — `PrivacyEngine` lived
in `ctm.privacy.engine` with passing unit tests, but the `/match`
endpoint never called it. A real patient note submitted to a
cloud-LLM-configured deployment would have leaked names, dates, MRNs,
phone numbers etc. verbatim to Anthropic / OpenAI.

What this test pins:
1. `PrivacyEngine.process_patient` actually removes the PHI types
   Presidio claims to handle (PERSON, DATE_TIME, PHONE_NUMBER, EMAIL,
   SSN, address, MRN).
2. The /match endpoint INVOKES the engine before passing the patient
   to the orchestrator. Verified by capturing every message handed
   to the LLM provider via `RecordedLLMProvider` and asserting none
   of the original PHI strings appear in any captured prompt.
3. The `DeIdSummary` in the response truthfully reports what was
   stripped, so the UI can show the user what happened.

Skipped when Presidio isn't installed (Presidio is in pyproject deps,
but the spaCy model download is heavy and we don't want to make this
a hard CI block).
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Presidio's spaCy model loads on first use; if it's not present the
# test should skip rather than fail the suite.
pytest.importorskip("presidio_analyzer")
try:
    import spacy  # noqa: F401
    spacy.load("en_core_web_lg")
except Exception:
    pytest.skip("Presidio spaCy model not installed; skipping de-ID e2e test",
                allow_module_level=True)


# Realistic clinical-note-shaped text containing every PHI category the
# README implies we strip. Each value is unique so we can grep for it
# specifically in the captured LLM messages.
PHI_NOTE = """\
Patient: Jeremiah Donaldson-Whitcombe (MRN: 88374521)
DOB: 03/14/1962, age 64. Phone: 555-242-9981.
Address: 1428 Maplewood Drive, Asheville, NC 28801
Email: jdonaldson1962@example.com. SSN: 123-45-6789.

HPI: 64M with poorly controlled type 2 diabetes mellitus diagnosed in
2014. HbA1c 8.7% on metformin 1000mg BID. BMI 32.4. BP 148/92.

Plan: add empagliflozin 10mg daily, recheck HbA1c in 3 months.
Follow up at Mission Hospital with Dr. Karen Martinez on 06/12/2026.
"""

# The literal PHI strings we expect Presidio to have removed before any
# of these reach the LLM. Each one is checked individually so a failure
# message tells you WHICH PHI category leaked.
PHI_LITERALS = [
    "Jeremiah",
    "Donaldson-Whitcombe",
    "88374521",
    "03/14/1962",
    "555-242-9981",
    "1428 Maplewood",
    "jdonaldson1962@example.com",
    "123-45-6789",
    "Karen Martinez",
    "06/12/2026",
]


def _settings_for_cloud_llm():
    """Settings configured so `should_deid` returns True (cloud provider
    + auto de-ID mode). This is the production-shaped condition under
    which the privacy gate has to fire."""
    from ctm.config import LLMProviderType, Settings
    s = Settings()
    s.llm.provider = LLMProviderType.ANTHROPIC
    s.llm.model = "claude-sonnet-4-5-20250929"
    s.llm.api_key = "sk-ant-test"  # bypass the missing-key check
    s.sandbox.enabled = False
    return s


def test_privacy_engine_strips_all_phi_categories():
    """Engine-level: feed the realistic note in, assert each PHI literal
    is gone from the output. This proves Presidio + our medical
    recognizers are doing what the README claims."""
    from ctm.models.patient import PatientNote
    from ctm.privacy.engine import PrivacyEngine

    settings = _settings_for_cloud_llm()
    engine = PrivacyEngine(settings)
    assert engine.is_active, "engine should be active for cloud provider"

    patient = PatientNote(patient_id="P-001", raw_text=PHI_NOTE, language="en")
    deid_patient, metadata = asyncio.run(engine.process_patient(patient))

    assert metadata["deid_applied"] is True
    assert metadata["entities_found"], "Presidio found no PHI entities at all"

    leaked = [s for s in PHI_LITERALS if s in deid_patient.raw_text]
    assert not leaked, (
        f"De-ID claimed to strip PHI but {len(leaked)} literal PHI strings "
        f"survived in the output: {leaked}.\n"
        f"This is the production-blocking failure mode: a clinician's "
        f"patient note would be sent verbatim to the cloud LLM.\n\n"
        f"De-ID output (first 500 chars):\n{deid_patient.raw_text[:500]}"
    )

    # The clinical signal — the actual matching content — must survive,
    # otherwise the de-ID destroys the patient's eligibility data.
    must_survive = ["diabetes", "metformin", "HbA1c", "BMI", "empagliflozin"]
    missing = [s for s in must_survive if s.lower() not in deid_patient.raw_text.lower()]
    assert not missing, (
        f"De-ID stripped clinical content too: {missing}. "
        f"Matching would fail for this patient."
    )


def test_match_endpoint_de_identifies_before_calling_llm():
    """End-to-end: call the route handler with PHI-laden text, capture
    the messages handed to the LLM via RecordedLLMProvider, assert no
    PHI literal appears in any captured message.

    This is the test that would have caught the original wireup gap:
    even if `PrivacyEngine.process_patient` is correct in isolation,
    if the route handler doesn't call it, PHI flows straight through.
    """
    from ctm.api.routes.match import match_patient
    from ctm.models.api import MatchRequest
    from ctm.models.matching import MatchStrength
    from tests.fixtures.recorded_provider import RecordedLLMProvider

    settings = _settings_for_cloud_llm()

    # Pre-canned LLM responses so the orchestrator runs without network.
    # Content shape doesn't matter — we're testing what gets SENT, not
    # what comes back. Three calls: inclusion-batch, exclusion-batch,
    # aggregator (matches the orchestrator's call structure).
    canned = '{"0": {"reasoning": "ok", "sentence_ids": [], "label": "not enough information"}}'
    canned_agg = (
        '{"relevance_explanation": "n/a", "relevance_score_R": 50, '
        '"eligibility_explanation": "n/a", "eligibility_score_E": 0}'
    )

    # The recorder appends every (messages, response) tuple to the cassette
    # in memory. We'll inspect those after the call.
    captured: list[dict] = []

    class CapturingProvider:
        """Minimal LLMProvider that records every prompt it sees."""

        @property
        def model_name(self) -> str:
            return "capture"

        async def complete(self, messages, temperature=0.0, max_tokens=16384,
                           response_format=None):
            captured.append({
                "messages": [dict(m) for m in messages],
                "temperature": temperature,
            })
            # Aggregator prompt is shorter and uses the aggregation system
            # message; criterion prompts are longer with inclusion/exclusion.
            sys_content = next(
                (m["content"] for m in messages if m["role"] == "system"), ""
            )
            if "aggregate" in sys_content.lower() or "Based on the patient" in sys_content:
                return canned_agg
            return canned

        async def complete_stream(self, messages, temperature=0.0, max_tokens=16384):
            yield await self.complete(messages, temperature, max_tokens)

        def count_tokens(self, text: str) -> int:
            return int(len(text.split()) * 1.3)

    provider = CapturingProvider()

    # FastAPI route handler is just an async function — we can call it
    # directly with stubbed Request and DB session, no full app boot.
    request = MagicMock()
    request.app.state.settings = settings
    request.app.state.llm = provider
    session = MagicMock()
    # The handler reads persisted trials via repo.list_all(); make it return
    # an empty list (sandbox protocols are loaded from disk separately).
    repo_mock = MagicMock()

    async def _list_all():
        return []

    repo_mock.list_all = _list_all

    body = MatchRequest(patient_id="P-001", patient_text=PHI_NOTE, max_trials=2)

    # Patch TrialRepository so it returns our empty mock; the route
    # already loads sandbox protocols from disk for the trial corpus.
    import ctm.api.routes.match as match_module
    original_repo_cls = match_module.TrialRepository
    match_module.TrialRepository = lambda _session: repo_mock
    try:
        response = asyncio.run(match_patient(request, body, session))
    finally:
        match_module.TrialRepository = original_repo_cls

    # The route ran successfully and reported that de-ID was applied.
    assert response.deid.applied is True, (
        "DeIdSummary says de-ID did NOT run — the privacy gate is unwired. "
        f"deid metadata: {response.deid}"
    )
    assert response.deid.processing_location == "cloud"
    assert response.deid.entities_removed, "no PHI entities were reported as removed"

    # The hot assertion: no PHI literal should appear in any LLM message.
    assert captured, "no LLM calls were captured; orchestrator may have skipped to sandbox"
    leaked: dict[str, list[int]] = {}
    for i, call in enumerate(captured):
        joined = "\n".join(m.get("content", "") for m in call["messages"])
        for phi in PHI_LITERALS:
            if phi in joined:
                leaked.setdefault(phi, []).append(i)

    assert not leaked, (
        f"PHI leaked into {sum(len(v) for v in leaked.values())} LLM call(s). "
        f"This is the production-blocking failure: the cloud LLM received "
        f"unredacted patient identifiers.\n\nLeaked literals → call indices:\n"
        + "\n".join(f"  {p!r} → calls {idxs}" for p, idxs in leaked.items())
    )


def test_local_llm_skips_de_identification():
    """The privacy contract: cloud LLM → de-ID applied, local LLM → not.
    A clinician running Ollama locally shouldn't pay the de-ID latency
    or risk Presidio scrubbing a real medical term that looked like a
    name."""
    from ctm.config import LLMProviderType, Settings
    from ctm.models.patient import PatientNote
    from ctm.privacy.engine import PrivacyEngine

    settings = Settings()
    settings.llm.provider = LLMProviderType.OLLAMA
    settings.llm.model = "llama3.1:70b"
    settings.sandbox.enabled = False

    engine = PrivacyEngine(settings)
    assert engine.is_active is False

    patient = PatientNote(patient_id="P-001", raw_text=PHI_NOTE, language="en")
    out, metadata = asyncio.run(engine.process_patient(patient))

    # Pass-through: original text unchanged, no entities reported.
    assert out.raw_text == PHI_NOTE
    assert metadata["deid_applied"] is False
    assert metadata["processing_location"] == "local"
