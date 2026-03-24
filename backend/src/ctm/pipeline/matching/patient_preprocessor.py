"""Patient note preprocessing for matching.

Handles sentence tokenization, numbering, and token budget management.
"""

from __future__ import annotations

import logging

from ctm.config import MatchingConfig
from ctm.models.patient import PatientNote, PatientSentence

logger = logging.getLogger(__name__)


def preprocess_patient(
    patient: PatientNote,
    config: MatchingConfig,
) -> PatientNote:
    """Preprocess a patient note for matching.

    - Tokenizes into sentences if not already done
    - Numbers sentences for evidence linking
    - Truncates to token budget
    - Optionally appends consent sentence

    Args:
        patient: Raw patient note.
        config: Matching configuration.

    Returns:
        Preprocessed patient note (new object, original unchanged).
    """
    # Tokenize if sentences not yet populated
    if not patient.sentences:
        import nltk

        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            nltk.download("punkt_tab", quiet=True)

        from nltk.tokenize import sent_tokenize

        sents = sent_tokenize(patient.raw_text)
        sentences = [
            PatientSentence(id=i, text=s.strip())
            for i, s in enumerate(sents)
            if s.strip()
        ]
    else:
        sentences = list(patient.sentences)

    # Optionally append consent sentence
    if config.append_consent_sentence:
        sentences.append(
            PatientSentence(id=len(sentences), text=config.consent_sentence)
        )

    # Truncate to token budget
    sentences = _truncate_to_budget(sentences, config.max_patient_tokens)

    return patient.model_copy(update={"sentences": sentences})


def _truncate_to_budget(
    sentences: list[PatientSentence], max_tokens: int
) -> list[PatientSentence]:
    """Keep sentences that fit within the token budget.

    Uses a rough estimate of 1.3 tokens per word.
    """
    result = []
    token_count = 0

    for sent in sentences:
        est_tokens = int(len(sent.text.split()) * 1.3)
        if token_count + est_tokens > max_tokens:
            logger.info(
                f"Truncated patient note at sentence {sent.id} "
                f"(~{token_count} tokens, budget {max_tokens})"
            )
            break
        result.append(sent)
        token_count += est_tokens

    return result
