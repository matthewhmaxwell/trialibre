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

        # Portuguese/Spanish disambiguation for short texts.
        # langdetect often confuses PT and ES on short medical text.
        if lang in ("es", "pt") and len(text) < 200:
            lang = _disambiguate_pt_es(text, lang)

        return lang
    except Exception as e:
        logger.debug(f"Language detection failed: {e}")
        return "en"


# Words that appear in Portuguese clinical text but not Spanish
_PT_MARKERS = {
    "anos", "não", "além", "também", "então", "são", "está",
    "diagnóstico", "medicações", "medicação", "paciente",
    "vezes", "ao", "dia", "desde", "há", "duas", "três",
    "apresenta", "queixa", "exames", "jejum", "glicemia",
}
_ES_MARKERS = {
    "años", "además", "también", "entonces", "están",
    "diagnóstico", "medicamentos", "medicación", "paciente",
    "veces", "al", "día", "desde", "hace", "dos", "tres",
    "presenta", "queja", "exámenes", "ayunas", "glucemia",
}


def _disambiguate_pt_es(text: str, detected: str) -> str:
    """Use word-level heuristics to distinguish PT from ES on short text."""
    words = set(text.lower().split())
    pt_score = len(words & _PT_MARKERS)
    es_score = len(words & _ES_MARKERS)
    if pt_score > es_score:
        return "pt"
    if es_score > pt_score:
        return "es"
    return detected


def is_supported_language(lang: str) -> bool:
    """Check if a language is supported for UI and prompts."""
    return lang in {"en", "fr", "es", "pt", "ar", "hi", "sw"}
