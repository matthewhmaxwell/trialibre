"""LLM-based keyword generation for trial retrieval."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from jinja2 import Template

from ctm.config import RetrievalConfig
from ctm.models.patient import PatientNote
from ctm.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class KeywordGenerator:
    """Generate search keywords from patient notes using an LLM."""

    def __init__(self, llm: LLMProvider, config: RetrievalConfig) -> None:
        self._llm = llm
        self._config = config
        self._template = self._load_template()

    def _load_template(self) -> Template:
        path = Path(__file__).parent.parent.parent.parent / "config" / "prompts" / "keyword_generation.jinja2"
        if path.exists():
            return Template(path.read_text())
        return Template("Generate search keywords for this patient. Output JSON with summary and conditions list.")

    async def generate(self, patient: PatientNote) -> dict:
        """Generate keywords from a patient note.

        Returns:
            {"summary": "...", "conditions": ["condition1", ...]}
        """
        system_prompt = self._template.render(max_keywords=self._config.max_keywords)

        try:
            response = await self._llm.complete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Patient description:\n{patient.raw_text[:6000]}\n\nJSON output:"},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            text = response.strip().strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
            data = json.loads(text)

            conditions = data.get("conditions", [])[:self._config.max_keywords]
            return {"summary": data.get("summary", ""), "conditions": conditions}

        except Exception as e:
            logger.error(f"Keyword generation failed: {e}")
            # Fallback: use diagnoses from structured data
            if patient.diagnoses:
                return {"summary": "", "conditions": patient.diagnoses}
            return {"summary": "", "conditions": []}
