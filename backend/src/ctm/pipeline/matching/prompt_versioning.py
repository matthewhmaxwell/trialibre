"""Prompt version tracking for audit trail integrity.

Each prompt change gets a version. The audit trail records which
prompt version was used for each match, ensuring reproducibility.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def get_prompt_version() -> str:
    """Get the current prompt version based on template content hashes.

    Returns a version string that changes whenever any prompt template is modified.
    """
    prompts_dir = Path(__file__).parent.parent.parent.parent / "config" / "prompts"
    if not prompts_dir.exists():
        return "unknown"

    hasher = hashlib.sha256()
    for path in sorted(prompts_dir.glob("*.jinja2")):
        hasher.update(path.read_bytes())

    short_hash = hasher.hexdigest()[:8]
    return f"v1.0.0-{short_hash}"


def get_prompt_metadata() -> dict:
    """Get metadata about current prompt templates."""
    prompts_dir = Path(__file__).parent.parent.parent.parent / "config" / "prompts"
    if not prompts_dir.exists():
        return {"version": "unknown", "templates": []}

    templates = []
    for path in sorted(prompts_dir.glob("*.jinja2")):
        content = path.read_bytes()
        templates.append({
            "name": path.name,
            "hash": hashlib.sha256(content).hexdigest()[:8],
            "size": len(content),
        })

    return {
        "version": get_prompt_version(),
        "templates": templates,
    }
