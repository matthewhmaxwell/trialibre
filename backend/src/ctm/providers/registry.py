"""LLM provider factory and registry."""

from __future__ import annotations

import logging

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
