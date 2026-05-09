"""Recorded LLM provider — VCR-style replay of real model calls for CI.

Why this exists: the matching pipeline's correctness is end-to-end. The
criterion parser, the JSON-mode prompts, the aggregator's scoring, and
the ranker's eligibility-veto rule all interlock. Unit tests for each
layer can pass while the full path silently regresses (this is how the
"every criterion came back unknown" parser bug lived for months — the
SandboxMatcher mock skipped the real path entirely). A cassette test
exercises orchestrator → matcher → aggregator → ranker against a
recorded real-model response, so any change that breaks parsing,
prompt format, or strength bucketing fails CI immediately.

Usage:

    # In CI (no network, deterministic):
    provider = RecordedLLMProvider.from_cassette("tests/fixtures/cassettes/foo.json")
    orchestrator = PipelineOrchestrator(settings, provider)
    ranking = await orchestrator.match_patient(patient, [trial])

    # When prompts or models change, re-record:
    real = AnthropicProvider(config)
    provider = RecordedLLMProvider.recording(
        wrapped=real,
        cassette_path="tests/fixtures/cassettes/foo.json",
        metadata={"test_name": "SAMPLE-001 × SAMPLE-NCT-001"},
    )
    # ... run pipeline ...
    provider.save()  # writes cassette to disk

The cassette is order-sensitive on purpose: if the orchestrator's call
order changes, the test fails loudly with a mismatched-prompt diff.
That's the signal we want — we shouldn't be silently making different
LLM calls than what's recorded.
"""

from __future__ import annotations

import difflib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator


class CassetteMismatchError(AssertionError):
    """The orchestrator made a request that doesn't match the recorded one.

    Either the prompts changed (re-record the cassette) or there's a
    real regression. The error message includes a diff between expected
    and actual messages so the cause is obvious.
    """


class CassetteExhaustedError(AssertionError):
    """The orchestrator made more LLM calls than the cassette has."""


class RecordedLLMProvider:
    """LLM provider that replays from disk, optionally recording on the way.

    Implements the `LLMProvider` Protocol structurally: `model_name` (property),
    `complete`, `complete_stream`, `count_tokens`. No `is_available` — that's
    Ollama-specific and not part of the Protocol.
    """

    def __init__(
        self,
        *,
        calls: list[dict[str, Any]] | None = None,
        wrapped: Any | None = None,
        cassette_path: str | Path | None = None,
        metadata: dict[str, Any] | None = None,
        model_name_override: str = "recorded",
    ) -> None:
        self._cassette_path = Path(cassette_path) if cassette_path else None
        self._metadata = metadata or {}
        self._wrapped = wrapped  # if set, we're recording
        self._calls = list(calls or [])
        self._cursor = 0
        self._model_name = model_name_override

    # --- factory constructors ---

    @classmethod
    def from_cassette(cls, path: str | Path) -> "RecordedLLMProvider":
        """Load a cassette from disk for replay."""
        data = json.loads(Path(path).read_text())
        return cls(
            calls=data.get("calls", []),
            metadata=data.get("metadata", {}),
            cassette_path=path,
            model_name_override=data.get("metadata", {}).get("model", "recorded"),
        )

    @classmethod
    def recording(
        cls,
        wrapped: Any,
        cassette_path: str | Path,
        metadata: dict[str, Any] | None = None,
    ) -> "RecordedLLMProvider":
        """Wrap a real provider, forwarding calls and capturing the responses.

        Call `.save()` at the end of the run to write the cassette.
        """
        meta = dict(metadata or {})
        meta.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
        meta.setdefault("provider_class", type(wrapped).__name__)
        meta.setdefault("model", getattr(wrapped, "model_name", "unknown"))
        return cls(
            wrapped=wrapped,
            cassette_path=cassette_path,
            metadata=meta,
            model_name_override=getattr(wrapped, "model_name", "recorded"),
        )

    # --- LLMProvider Protocol surface ---

    @property
    def model_name(self) -> str:
        return self._model_name

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 16384,
        response_format: dict | None = None,
    ) -> str:
        if self._wrapped is not None:
            # Record mode: forward, capture, return.
            response = await self._wrapped.complete(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
            self._calls.append({
                "messages": messages,
                "temperature": temperature,
                "response_format": response_format,
                "response": response,
            })
            return response

        # Replay mode: validate the request matches what was recorded.
        if self._cursor >= len(self._calls):
            raise CassetteExhaustedError(
                f"Pipeline made {self._cursor + 1} LLM calls but cassette "
                f"only has {len(self._calls)}. Either the orchestrator is "
                f"making extra calls, or the cassette is stale and needs "
                f"re-recording."
            )

        recorded = self._calls[self._cursor]
        self._cursor += 1
        self._assert_messages_match(recorded["messages"], messages, self._cursor)
        return recorded["response"]

    async def complete_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 16384,
    ) -> AsyncIterator[str]:
        # The matching pipeline doesn't use streaming. If a future change
        # adopts streaming, we'll need to record token-stream cassettes.
        text = await self.complete(messages=messages, temperature=temperature,
                                   max_tokens=max_tokens)

        async def _gen() -> AsyncIterator[str]:
            yield text

        return _gen()

    def count_tokens(self, text: str) -> int:
        return int(len(text.split()) * 1.3)

    # --- recording I/O ---

    def save(self) -> None:
        """Persist captured calls to disk. Recording mode only."""
        if self._cassette_path is None:
            raise RuntimeError("save() requires cassette_path to be set")
        self._cassette_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"metadata": self._metadata, "calls": self._calls}
        self._cassette_path.write_text(json.dumps(payload, indent=2))

    @property
    def call_count(self) -> int:
        """Number of LLM calls observed (recording) or replayed so far."""
        return self._cursor if self._wrapped is None else len(self._calls)

    @property
    def cassette_size(self) -> int:
        """Number of calls in the loaded cassette."""
        return len(self._calls)

    # --- internals ---

    @staticmethod
    def _assert_messages_match(
        expected: list[dict[str, str]],
        actual: list[dict[str, str]],
        call_index: int,
    ) -> None:
        """Strict equality on message list, with a readable diff on mismatch.

        We compare the full content rather than a hash so the failure
        message tells the engineer *what* changed in the prompt, which
        is the actionable signal (was it a wording tweak? a new field
        in the patient context? a different criterion batch size?).
        """
        if expected == actual:
            return

        def _flatten(msgs: list[dict[str, str]]) -> list[str]:
            out: list[str] = []
            for m in msgs:
                role = m.get("role", "?")
                content = m.get("content", "")
                out.append(f"=== role: {role} ===")
                out.extend(content.splitlines() or [""])
            return out

        diff = "\n".join(difflib.unified_diff(
            _flatten(expected),
            _flatten(actual),
            fromfile=f"cassette[call {call_index}]",
            tofile="actual request",
            lineterm="",
        ))
        raise CassetteMismatchError(
            f"LLM call #{call_index} doesn't match the cassette.\n"
            f"This usually means the pipeline's prompts changed; if the change "
            f"was intentional, re-record the cassette via the recording-mode "
            f"factory in this module.\n\n{diff}"
        )
