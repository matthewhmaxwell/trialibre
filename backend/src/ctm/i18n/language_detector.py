"""Language detection for patient notes."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """Detect the language of a text.

    Returns:
        ISO 639-1 language code (e.g., 'en', 'fr', 'sw').
    """
    if not text or len(text.strip()) < 20:
        return "en"

    try:
        from langdetect import detect
        lang = detect(text)
        return lang
    except Exception as e:
        logger.debug(f"Language detection failed: {e}")
        return "en"


def is_supported_language(lang: str) -> bool:
    """Check if a language is supported for UI and prompts."""
    return lang in {"en", "fr", "es", "pt", "ar", "hi", "sw"}
