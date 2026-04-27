"""Tests for `providers.registry` — model-size warnings and creation paths.

The 24-pair Anthropic Sonnet evaluation surfaced that small local Ollama
models (≤8B) hallucinate clinical facts under real criterion-matching
prompts. We now warn loudly at provider creation when an operator pairs
Ollama with a sub-13B model, so they're not surprised at match time.

These tests pin the parser, the threshold, and the fact that hosted
providers never trigger the warning regardless of model name.
"""

from __future__ import annotations

import logging

import pytest

from ctm.config import LLMConfig, LLMProviderType
from ctm.providers.registry import (
    MIN_RECOMMENDED_LOCAL_PARAMS_B,
    _model_size_billions,
    create_provider,
)


@pytest.mark.parametrize(
    "name,expected",
    [
        ("llama3.2:3b", 3.0),
        ("llama3.1:8b", 8.0),
        ("llama3.1:70b", 70.0),
        ("qwen2.5:1.5b", 1.5),
        ("Llama3.1:70B", 70.0),  # case-insensitive
        ("mistral-small", None),
        ("claude-sonnet-4-5-20250929", None),  # cloud model name with no Nb tag
        ("gpt-4o", None),
    ],
)
def test_model_size_parser(name, expected):
    assert _model_size_billions(name) == expected


def _ollama_config(model: str) -> LLMConfig:
    return LLMConfig(
        provider=LLMProviderType.OLLAMA,
        model=model,
        base_url="http://localhost:11434",
    )


def test_warns_on_sub_threshold_local_model(caplog):
    caplog.set_level(logging.WARNING)
    create_provider(_ollama_config("llama3.2:3b"))
    msg = caplog.text
    assert "llama3.2:3b" in msg
    assert "3.0B parameters" in msg
    assert "amlodipine" in msg  # the cited evidence — keeps the lesson in-source
    assert "REAL_LLM_EVAL_FINDINGS.md" in msg


def test_no_warning_on_recommended_local_model(caplog):
    caplog.set_level(logging.WARNING)
    create_provider(_ollama_config("llama3.1:70b"))
    assert "below the" not in caplog.text


def test_threshold_boundary_matches_constant(caplog):
    """A model exactly at the recommended floor should NOT warn."""
    caplog.set_level(logging.WARNING)
    create_provider(_ollama_config(f"custom:{int(MIN_RECOMMENDED_LOCAL_PARAMS_B)}b"))
    assert "below the" not in caplog.text


def test_no_warning_when_model_size_is_unknown(caplog):
    """If we can't parse a size from the name, stay silent rather than
    risk a false-positive warning on a custom-named model."""
    caplog.set_level(logging.WARNING)
    create_provider(_ollama_config("custom-medical-llm"))
    assert "below the" not in caplog.text


def test_hosted_provider_never_warns_about_model_size(caplog):
    """Even if someone names a hosted model with a Nb suffix, we shouldn't
    warn — the size heuristic only applies to local Ollama deployments."""
    caplog.set_level(logging.WARNING)
    cfg = LLMConfig(
        provider=LLMProviderType.ANTHROPIC,
        model="claude-some-3b-variant-that-does-not-exist",
        api_key="sk-ant-test",
    )
    create_provider(cfg)
    assert "below the" not in caplog.text


def test_unknown_provider_raises():
    """Defensive: garbage provider value should fail loudly, not silently."""
    cfg = LLMConfig(provider=LLMProviderType.OLLAMA, model="x")
    cfg.provider = "nonsense"  # bypass enum validation post-init
    with pytest.raises(Exception):
        create_provider(cfg)
