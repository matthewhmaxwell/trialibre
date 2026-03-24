"""LLM-based I/O translation.

Translates patient input to English for matching, and results back
to the user's language. All LLM prompts stay in English internally.
"""

from __future__ import annotations

import logging

from ctm.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class Translator:
    """Translate text between languages using the configured LLM."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def to_english(self, text: str, source_lang: str) -> str:
        """Translate patient text to English for matching.

        If already English, returns unchanged.
        """
        if source_lang == "en":
            return text

        try:
            response = await self._llm.complete(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a medical translator. Translate the following clinical text "
                            "to English. Preserve all medical terminology, lab values, and "
                            "clinical details exactly. Output only the translation."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0.0,
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Translation to English failed: {e}")
            return text  # Return original on failure

    async def from_english(self, text: str, target_lang: str) -> str:
        """Translate English results to the user's language.

        If target is English, returns unchanged.
        """
        if target_lang == "en":
            return text

        lang_names = {
            "fr": "French", "es": "Spanish", "pt": "Portuguese",
            "ar": "Arabic", "hi": "Hindi", "sw": "Swahili",
        }
        lang_name = lang_names.get(target_lang, target_lang)

        try:
            response = await self._llm.complete(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"Translate the following clinical text to {lang_name}. "
                            "Preserve medical terminology where appropriate. "
                            "Output only the translation."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0.0,
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Translation to {target_lang} failed: {e}")
            return text
