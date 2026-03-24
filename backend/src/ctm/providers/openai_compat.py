"""OpenAI-compatible provider for vLLM, LiteLLM, and other compatible servers."""

from __future__ import annotations

from ctm.config import LLMConfig
from ctm.providers.openai_provider import OpenAIProvider


class OpenAICompatProvider(OpenAIProvider):
    """Provider for any OpenAI-compatible API endpoint.

    Works with vLLM, LiteLLM, text-generation-inference, LocalAI,
    and any server implementing the OpenAI chat completions API.

    Requires base_url to be set in config pointing to the compatible server.
    """

    def __init__(self, config: LLMConfig) -> None:
        if not config.base_url:
            raise ValueError(
                "OpenAI-compatible provider requires base_url to be set. "
                "Example: http://localhost:8080/v1"
            )
        super().__init__(config)

    @property
    def model_name(self) -> str:
        return f"compat:{self._model}"
