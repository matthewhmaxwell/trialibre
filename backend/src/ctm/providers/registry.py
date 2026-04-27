"""LLM provider factory and registry."""

from __future__ import annotations

import logging
import re

from ctm.config import LLMConfig, LLMProviderType
from ctm.providers.anthropic_provider import AnthropicProvider
from ctm.providers.base import LLMError, LLMProvider
from ctm.providers.ollama_provider import OllamaProvider
from ctm.providers.openai_compat import OpenAICompatProvider
from ctm.providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

_PROVIDER_MAP: dict[LLMProviderType, type] = {
    LLMProviderType.ANTHROPIC: AnthropicProvider,
    LLMProviderType.OPENAI: OpenAIProvider,
    LLMProviderType.OLLAMA: OllamaProvider,
    LLMProviderType.OPENAI_COMPAT: OpenAICompatProvider,
}

# Below this parameter count we have empirical evidence the model
# hallucinates clinical facts under real prompts (the v6 smoke test
# produced a confident "amlodipine is an SGLT2 inhibitor" claim from
# llama3.2:3b). 13B is the practical floor for clinical use; 70B+
# matches the validated Sonnet-class quality.
MIN_RECOMMENDED_LOCAL_PARAMS_B = 13.0


def _model_size_billions(model_name: str) -> float | None:
    """Best-effort parse of parameter count from common Ollama model tags.

    Examples:
        "llama3.2:3b"     -> 3.0
        "llama3.1:8b"     -> 8.0
        "llama3.1:70b"    -> 70.0
        "qwen2.5:1.5b"    -> 1.5
        "mistral-small"   -> None  (no embedded size)
    """
    m = re.search(r"(\d+(?:\.\d+)?)\s*b\b", model_name.lower())
    return float(m.group(1)) if m else None


def create_provider(config: LLMConfig) -> LLMProvider:
    """Create an LLM provider from configuration.

    Args:
        config: LLM configuration specifying provider type, model, API key, etc.

    Returns:
        An initialized LLMProvider instance.

    Raises:
        LLMError: If the provider type is unknown.
        ValueError: If required configuration is missing.
    """
    provider_cls = _PROVIDER_MAP.get(config.provider)
    if provider_cls is None:
        raise LLMError(
            f"Unknown LLM provider: {config.provider}. "
            f"Available: {', '.join(p.value for p in LLMProviderType)}",
            provider=config.provider.value,
        )

    logger.info(f"Creating LLM provider: {config.provider.value} (model: {config.model})")

    # Loud warning for known-bad local configs. Operators should know
    # before the first match request lands what they've signed up for.
    if config.provider == LLMProviderType.OLLAMA:
        size_b = _model_size_billions(config.model or "")
        if size_b is not None and size_b < MIN_RECOMMENDED_LOCAL_PARAMS_B:
            logger.warning(
                "Ollama model '%s' is %.1fB parameters — below the %sB "
                "floor for clinical matching. Models this small "
                "hallucinate facts under real criterion-matching prompts "
                "(the v6 smoke test produced a confident 'amlodipine is "
                "an SGLT2 inhibitor' claim from llama3.2:3b). Recommend "
                "llama3.1:70b on a GPU, or switch to a hosted provider "
                "for clinical use. See docs/REAL_LLM_EVAL_FINDINGS.md.",
                config.model, size_b, int(MIN_RECOMMENDED_LOCAL_PARAMS_B),
            )

    return provider_cls(config)


def validate_config(config: LLMConfig) -> list[str]:
    """Validate LLM configuration and return any issues.

    Returns:
        List of validation error messages. Empty if valid.
    """
    issues = []

    if config.provider in (LLMProviderType.ANTHROPIC, LLMProviderType.OPENAI):
        if not config.api_key:
            issues.append(
                f"{config.provider.value} requires an access code (API key). "
                "Set it in Settings or via CTM_LLM__API_KEY environment variable."
            )

    if config.provider == LLMProviderType.OPENAI_COMPAT:
        if not config.base_url:
            issues.append(
                "OpenAI-compatible provider requires a base URL. "
                "Set it via CTM_LLM__BASE_URL."
            )

    if not config.model:
        issues.append("No model specified. Set CTM_LLM__MODEL.")

    return issues
