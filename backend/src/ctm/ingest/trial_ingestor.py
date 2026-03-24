"""Trial protocol file ingestor.

Parses uploaded trial files (JSON, CSV, XML) into ClinicalTrial objects.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path

from ctm.models.trial import ClinicalTrial, EligibilityCriteria

logger = logging.getLogger(__name__)


async def ingest_trial_file(source: str | bytes) -> list[ClinicalTrial]:
    """Ingest a trial file and return parsed trials.

    Supports: JSONL, JSON array, CSV.

    Args:
        source: File path or raw content.

    Returns:
        List of ClinicalTrial objects.
    """
    if isinstance(source, bytes):
        content = source.decode("utf-8", errors="replace")
    else:
        path = Path(source)
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
        else:
            content = source

    stripped = content.strip()

    # Try JSONL (one JSON object per line)
    if stripped.startswith("{"):
        trials = []
        for line in stripped.split("\n"):
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    trials.append(_parse_trial_dict(data))
                except json.JSONDecodeError:
                    continue
        if trials:
            return trials

    # Try JSON array
    if stripped.startswith("["):
        data_list = json.loads(stripped)
        return [_parse_trial_dict(d) for d in data_list]

    # Try CSV
    reader = csv.DictReader(io.StringIO(content))
    trials = []
    for row in reader:
        trials.append(_parse_trial_csv_row(row))
    return trials


def _parse_trial_dict(data: dict) -> ClinicalTrial:
    """Parse a trial from a JSON dict."""
    # Parse eligibility criteria if provided as raw text
    inclusion = data.get("inclusion_criteria", [])
    exclusion = data.get("exclusion_criteria", [])

    if isinstance(inclusion, str):
        inclusion = _parse_criteria_text(inclusion, "inclusion")
    elif isinstance(inclusion, list) and inclusion and isinstance(inclusion[0], dict):
        inclusion = [EligibilityCriteria(**c) for c in inclusion]

    if isinstance(exclusion, str):
        exclusion = _parse_criteria_text(exclusion, "exclusion")
    elif isinstance(exclusion, list) and exclusion and isinstance(exclusion[0], dict):
        exclusion = [EligibilityCriteria(**c) for c in exclusion]

    return ClinicalTrial(
        nct_id=data.get("nct_id", data.get("_id", "")),
        brief_title=data.get("brief_title", data.get("title", "")),
        official_title=data.get("official_title", ""),
        diseases=_ensure_list(data.get("diseases", data.get("diseases_list", []))),
        interventions=_ensure_list(data.get("interventions", data.get("drugs_list", []))),
        brief_summary=data.get("brief_summary", ""),
        phase=data.get("phase"),
        status=data.get("status"),
        enrollment=_parse_int(data.get("enrollment")),
        sponsor=data.get("sponsor", ""),
        inclusion_criteria=inclusion if isinstance(inclusion, list) else [],
        exclusion_criteria=exclusion if isinstance(exclusion, list) else [],
        raw_inclusion_text=data.get("raw_inclusion_text", data.get("inclusion_criteria", "")),
        raw_exclusion_text=data.get("raw_exclusion_text", data.get("exclusion_criteria", "")),
        source_registry=data.get("source_registry", "upload"),
        metadata=data.get("metadata", {}),
    )


def _parse_trial_csv_row(row: dict) -> ClinicalTrial:
    """Parse a trial from a CSV row."""
    return ClinicalTrial(
        nct_id=row.get("nct_id", row.get("NCT Number", "")),
        brief_title=row.get("brief_title", row.get("Title", "")),
        diseases=_split_csv_field(row.get("conditions", row.get("Conditions", ""))),
        interventions=_split_csv_field(row.get("interventions", row.get("Interventions", ""))),
        brief_summary=row.get("brief_summary", row.get("Description", "")),
        phase=row.get("phase", row.get("Phases", None)),
        status=row.get("status", row.get("Status", None)),
        enrollment=_parse_int(row.get("enrollment", row.get("Enrollment", None))),
        sponsor=row.get("sponsor", row.get("Sponsor", "")),
        source_registry="upload",
    )


def _parse_criteria_text(text: str, category: str) -> list[EligibilityCriteria]:
    """Parse criteria from raw text into structured objects."""
    if not text or not text.strip():
        return []

    lines = text.strip().split("\n\n")
    criteria = []
    idx = 0
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue
        if line.lower().startswith(("inclusion", "exclusion")):
            continue
        # Strip leading numbers/bullets
        import re

        line = re.sub(r"^\d+[\.\)]\s*", "", line)
        line = re.sub(r"^[-•]\s*", "", line)
        if line.strip():
            criteria.append(
                EligibilityCriteria(index=idx, text=line.strip(), category=category)
            )
            idx += 1
    return criteria


def _ensure_list(value) -> list[str]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def _split_csv_field(value: str) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split("|") if v.strip()]


def _parse_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None
