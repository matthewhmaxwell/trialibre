"""Extract inclusion/exclusion criteria from unstructured protocol text.

Takes raw text from a PDF, DOCX, or pasted protocol document and finds
the eligibility criteria sections. Works without an LLM — pure regex/heuristic.
"""

from __future__ import annotations

import re
import logging

from ctm.models.trial import EligibilityCriteria
from ctm.pipeline.matching.criteria_parser import parse_criteria

logger = logging.getLogger(__name__)

# Section header patterns (case-insensitive)
_INCLUSION_HEADERS = re.compile(
    r"(?:key\s+)?inclusion\s+criteria|"
    r"eligibility\s+criteria\s*[-:—]\s*inclusion|"
    r"subjects?\s+must\s+meet\s+(?:all\s+)?(?:of\s+)?the\s+following|"
    r"inclusion\s*:",
    re.IGNORECASE,
)

_EXCLUSION_HEADERS = re.compile(
    r"(?:key\s+)?exclusion\s+criteria|"
    r"eligibility\s+criteria\s*[-:—]\s*exclusion|"
    r"subjects?\s+(?:will\s+be|are)\s+excluded\s+if|"
    r"exclusion\s*:",
    re.IGNORECASE,
)

# Section boundaries — headers that mark the END of criteria sections
_STOP_HEADERS = re.compile(
    r"^\s*(?:"
    r"study\s+design|study\s+procedures|study\s+endpoints|"
    r"statistical\s+analysis|statistical\s+methods|"
    r"primary\s+(?:end\s*point|outcome)|secondary\s+(?:end\s*point|outcome)|"
    r"schedule\s+of\s+(?:events|assessments|activities)|"
    r"investigational\s+product|study\s+drug|study\s+treatment|"
    r"safety\s+(?:assessments|monitoring)|adverse\s+events|"
    r"data\s+management|data\s+collection|"
    r"ethical\s+considerations|informed\s+consent|"
    r"references|appendix|abbreviations|glossary|"
    r"administrative|regulatory|"
    r"randomization|stratification|blinding|"
    r"sample\s+size|power\s+calculation|"
    r"discontinuation|withdrawal"
    r")\s*(?:[:.]|\s*$)",
    re.IGNORECASE | re.MULTILINE,
)


def extract_criteria_from_protocol(
    text: str,
) -> tuple[list[EligibilityCriteria], list[EligibilityCriteria], dict]:
    """Extract inclusion and exclusion criteria from protocol text.

    Args:
        text: Raw text from a protocol document (PDF, DOCX, or pasted).

    Returns:
        Tuple of (inclusion_criteria, exclusion_criteria, metadata).
        metadata includes: method, sections_found, confidence, warnings.
    """
    warnings: list[str] = []
    sections_found: list[str] = []

    if not text or not text.strip():
        return [], [], {"method": "heuristic", "sections_found": [], "confidence": "none", "warnings": ["Empty text"]}

    # Find section boundaries
    inc_start, inc_end = _find_section(text, _INCLUSION_HEADERS, _EXCLUSION_HEADERS)
    exc_start, exc_end = _find_section(text, _EXCLUSION_HEADERS, _STOP_HEADERS)

    # If exclusion comes before inclusion in the document, adjust
    if inc_start is not None and exc_start is not None and exc_start < inc_start:
        # Swap: exclusion found first, inclusion after
        exc_end_alt = inc_start
        inc_end_alt = _find_next_stop(text, inc_start)
        exc_text = text[exc_start:exc_end_alt].strip()
        inc_text = text[inc_start:inc_end_alt].strip()
    else:
        inc_text = text[inc_start:inc_end].strip() if inc_start is not None else ""
        exc_text = text[exc_start:exc_end].strip() if exc_start is not None else ""

    if inc_start is not None:
        sections_found.append("inclusion")
    if exc_start is not None:
        sections_found.append("exclusion")

    # Parse structured criteria from section text
    inclusion = parse_criteria(inc_text, "inclusion") if inc_text else []
    exclusion = parse_criteria(exc_text, "exclusion") if exc_text else []

    # Fallback: if no sections found, try keyword classification
    if not inclusion and not exclusion:
        logger.warning("No criteria sections found via headers. Trying keyword fallback.")
        warnings.append("Could not find standard criteria section headers. Used keyword-based extraction.")
        inclusion, exclusion = _keyword_fallback(text)
        if inclusion or exclusion:
            sections_found.append("keyword_fallback")

    # Determine confidence
    if len(sections_found) == 2 and "keyword_fallback" not in sections_found:
        confidence = "high"
    elif len(sections_found) >= 1:
        confidence = "medium"
        if not inclusion:
            warnings.append("No inclusion criteria found")
        if not exclusion:
            warnings.append("No exclusion criteria found")
    else:
        confidence = "low"
        warnings.append("Could not extract structured criteria from this document")

    logger.info(
        f"Extracted {len(inclusion)} inclusion + {len(exclusion)} exclusion criteria "
        f"(confidence={confidence}, sections={sections_found})"
    )

    return inclusion, exclusion, {
        "method": "heuristic",
        "sections_found": sections_found,
        "confidence": confidence,
        "warnings": warnings,
    }


def _find_section(
    text: str, header_pattern: re.Pattern, end_pattern: re.Pattern
) -> tuple[int | None, int | None]:
    """Find the start and end positions of a criteria section."""
    match = header_pattern.search(text)
    if match is None:
        return None, None

    # Start after the header line
    start = match.end()
    # Skip to next line
    newline = text.find("\n", start)
    if newline != -1:
        start = newline + 1

    # Find end: next section header or stop header
    end_match = end_pattern.search(text, start)
    if end_match:
        end = end_match.start()
    else:
        end = len(text)

    return start, end


def _find_next_stop(text: str, start: int) -> int:
    """Find the next stop header after a position."""
    match = _STOP_HEADERS.search(text, start)
    if match:
        return match.start()
    # Also check for another criteria section
    for pattern in [_INCLUSION_HEADERS, _EXCLUSION_HEADERS]:
        m = pattern.search(text, start + 50)  # Skip past current header
        if m:
            return m.start()
    return len(text)


def _keyword_fallback(
    text: str,
) -> tuple[list[EligibilityCriteria], list[EligibilityCriteria]]:
    """Last-resort keyword-based criteria classification."""
    inclusion_keywords = re.compile(
        r"must\s+(?:have|be|meet)|required|eligible|aged?\s+\d|"
        r"diagnosis\s+of|confirmed|documented|willing\s+to",
        re.IGNORECASE,
    )
    exclusion_keywords = re.compile(
        r"excluded|not\s+eligible|prohibited|contraindicated|"
        r"history\s+of.*(?:within|in\s+the\s+past)|"
        r"unable\s+to|unwilling|pregnant|nursing",
        re.IGNORECASE,
    )

    lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 15]

    inclusion = []
    exclusion = []
    inc_idx = 0
    exc_idx = 0

    for line in lines:
        line_clean = re.sub(r"^\s*\d+[\.\)]\s*", "", line).strip()
        if not line_clean or len(line_clean) < 10:
            continue

        inc_score = len(inclusion_keywords.findall(line))
        exc_score = len(exclusion_keywords.findall(line))

        if exc_score > inc_score:
            exclusion.append(EligibilityCriteria(index=exc_idx, text=line_clean, category="exclusion"))
            exc_idx += 1
        elif inc_score > 0:
            inclusion.append(EligibilityCriteria(index=inc_idx, text=line_clean, category="inclusion"))
            inc_idx += 1

    return inclusion[:20], exclusion[:15]  # Cap to reasonable counts
