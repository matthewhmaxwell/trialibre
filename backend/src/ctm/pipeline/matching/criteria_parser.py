"""Parse raw eligibility criteria text into structured criterion objects."""

from __future__ import annotations

import re

from ctm.models.trial import EligibilityCriteria


def parse_criteria(raw_text: str, category: str) -> list[EligibilityCriteria]:
    """Parse raw inclusion/exclusion criteria text into structured objects.

    Handles common formats: numbered lists, bullet points, double-newline separated.

    Args:
        raw_text: Raw criteria text from trial protocol.
        category: "inclusion" or "exclusion".

    Returns:
        List of EligibilityCriteria with stable indices.
    """
    if not raw_text or not raw_text.strip():
        return []

    # Split by double newlines first (most common format)
    blocks = re.split(r"\n\s*\n", raw_text.strip())

    criteria = []
    idx = 0

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Skip header lines
        if _is_header(block, category):
            continue

        # Handle multi-line criteria within a block (single newline with numbers/bullets)
        sub_items = _split_numbered_items(block)

        for item in sub_items:
            item = item.strip()
            if len(item) < 5:
                continue
            if _is_header(item, category):
                continue

            # Clean up the criterion text
            item = _clean_criterion(item)
            if item:
                criteria.append(
                    EligibilityCriteria(index=idx, text=item, category=category)
                )
                idx += 1

    return criteria


def _is_header(text: str, category: str) -> bool:
    """Check if a line is a section header."""
    lower = text.lower().strip()
    return any(
        lower.startswith(h)
        for h in [
            "inclusion criteria",
            "exclusion criteria",
            "eligibility criteria",
            "key inclusion",
            "key exclusion",
            "inclusion:",
            "exclusion:",
        ]
    )


def _split_numbered_items(block: str) -> list[str]:
    """Split a block into individual numbered/bulleted items."""
    # Check if block contains numbered items
    lines = block.split("\n")
    if len(lines) <= 1:
        return [block]

    # Pattern: starts with number, letter, bullet, or dash
    item_pattern = re.compile(r"^\s*(?:\d+[\.\)]\s*|[a-z][\.\)]\s*|[-•*]\s*)")

    items = []
    current = []

    for line in lines:
        if item_pattern.match(line) and current:
            items.append(" ".join(current))
            current = [line]
        else:
            current.append(line)

    if current:
        items.append(" ".join(current))

    return items if items else [block]


def _clean_criterion(text: str) -> str:
    """Clean up a criterion string."""
    # Remove leading numbers, bullets, dashes
    text = re.sub(r"^\s*\d+[\.\)]\s*", "", text)
    text = re.sub(r"^\s*[a-z][\.\)]\s*", "", text)
    text = re.sub(r"^\s*[-•*]\s*", "", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text
