"""LLM-based patient note structuring.

Takes raw extracted text from any format and normalizes it into
a structured PatientNote with demographics, diagnoses, medications, etc.
"""

from __future__ import annotations

import json
import logging
import uuid

from ctm.models.patient import PatientNote, PatientSentence
from ctm.providers.base import LLMProvider

logger = logging.getLogger(__name__)

STRUCTURING_PROMPT = """You are a clinical data extraction assistant. Given a patient record (which may be messy, OCR'd, or in any format), extract the following structured information.

Output ONLY a JSON object with these fields:
{
  "age": <integer or null>,
  "sex": "<Male/Female/Other or null>",
  "diagnoses": ["list of diagnoses"],
  "medications": ["list of medications with doses if available"],
  "lab_values": {"test_name": "value with units"},
  "medical_history": ["list of relevant medical history items"]
}

If a field cannot be determined from the text, use null for scalars or empty lists/objects.
Do not invent information that is not in the text."""


async def structure_patient_note(
    raw_text: str,
    llm: LLMProvider,
    language: str = "en",
    patient_id: str | None = None,
    source_format: str = "text",
) -> PatientNote:
    """Convert raw text into a structured PatientNote.

    Uses the LLM to extract demographics, diagnoses, medications, and labs
    from unstructured clinical text.

    Args:
        raw_text: Raw patient note text (from any ingestor).
        llm: LLM provider for extraction.
        language: Detected language of the text.
        patient_id: Optional patient identifier.
        source_format: Original file format.

    Returns:
        Structured PatientNote.
    """
    pid = patient_id or f"P-{uuid.uuid4().hex[:8]}"

    # Build sentences
    import nltk

    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)

    from nltk.tokenize import sent_tokenize

    sents = sent_tokenize(raw_text)
    sentences = [
        PatientSentence(id=i, text=s.strip())
        for i, s in enumerate(sents)
        if s.strip()
    ]

    # Extract structured data via LLM
    structured = {}
    try:
        response = await llm.complete(
            messages=[
                {"role": "system", "content": STRUCTURING_PROMPT},
                {"role": "user", "content": f"Patient record:\n\n{raw_text[:8000]}"},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        # Parse JSON response
        text = response.strip().strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()
        structured = json.loads(text)

    except Exception as e:
        logger.warning(f"LLM structuring failed: {e}. Using raw text only.")

    return PatientNote(
        patient_id=pid,
        raw_text=raw_text,
        sentences=sentences,
        language=language,
        source_format=source_format,
        age=structured.get("age"),
        sex=structured.get("sex"),
        diagnoses=structured.get("diagnoses", []),
        medications=structured.get("medications", []),
        lab_values=structured.get("lab_values", {}),
        medical_history=structured.get("medical_history", []),
    )
