"""LLM-based relevance and eligibility aggregation.

Uses the LLM to produce holistic relevance (R) and eligibility (E) scores
from criterion-level predictions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from jinja2 import Template

from ctm.config import RankingConfig
from ctm.models.matching import MatchingResult
from ctm.models.patient import PatientNote
from ctm.models.trial import ClinicalTrial
from ctm.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class LLMAggregator:
    """Aggregate criterion-level results into trial-level scores via LLM."""

    def __init__(self, llm: LLMProvider, config: RankingConfig) -> None:
        self._llm = llm
        self._config = config
        self._template = self._load_template()

    def _load_template(self) -> Template:
        # 1. Packaged location (works after pip install)
        package_path = Path(__file__).parent.parent.parent / "prompts" / "aggregation.jinja2"
        if package_path.exists():
            return Template(package_path.read_text())
        # 2. Dev fallback
        dev_path = Path(__file__).parent.parent.parent.parent.parent / "config" / "prompts" / "aggregation.jinja2"
        if dev_path.exists():
            return Template(dev_path.read_text())
        raise FileNotFoundError(
            f"Aggregation prompt template not found. Tried: {package_path}, {dev_path}."
        )

    async def aggregate(
        self,
        patient: PatientNote,
        trial: ClinicalTrial,
        matching_result: MatchingResult,
    ) -> dict:
        """Produce relevance and eligibility scores.

        Args:
            patient: Patient note.
            trial: Clinical trial.
            matching_result: Criterion-level matching results.

        Returns:
            Dict with relevance_score_R, eligibility_score_E, and explanations.
        """
        system_prompt = self._template.render()

        # Build criterion summary
        criterion_summary = self._build_criterion_summary(matching_result)

        user_prompt = (
            f"Patient Note:\n{patient.to_numbered_text()}\n\n"
            f"Trial: {trial.brief_title}\n"
            f"Conditions: {', '.join(trial.diseases)}\n"
            f"Summary: {trial.brief_summary[:300]}\n\n"
            f"Criterion-Level Results:\n{criterion_summary}\n\n"
            f"JSON output:"
        )

        try:
            response = await self._llm.complete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            text = response.strip().strip("`")
            if text.startswith("json"):
                text = text[4:].strip()

            data = json.loads(text)

            r_score = float(data.get("relevance_score_R", 0))
            e_score = float(data.get("eligibility_score_E", 0))

            # Normalize: R from [0,100] to [0,1], E from [-R,R] to [-1,1]
            r_normalized = max(0.0, min(1.0, r_score / 100.0))
            e_normalized = max(-1.0, min(1.0, e_score / max(r_score, 1.0)))

            return {
                "relevance_score": r_normalized,
                "eligibility_score": e_normalized,
                "relevance_explanation": data.get("relevance_explanation", ""),
                "eligibility_explanation": data.get("eligibility_explanation", ""),
            }

        except Exception as e:
            logger.error(f"LLM aggregation failed: {e}")
            return {
                "relevance_score": 0.0,
                "eligibility_score": 0.0,
                "relevance_explanation": f"Aggregation failed: {e}",
                "eligibility_explanation": "",
            }

    def _build_criterion_summary(self, result: MatchingResult) -> str:
        """Build a text summary of criterion results for the aggregation prompt."""
        lines = []

        if result.inclusion_results:
            lines.append("Inclusion Criteria:")
            for r in result.inclusion_results:
                lines.append(f"  {r.criterion_index}. {r.criterion_text}")
                lines.append(f"     Result: {r.label.value}")
                lines.append(f"     Reasoning: {r.reasoning[:150]}")

        if result.exclusion_results:
            lines.append("\nExclusion Criteria:")
            for r in result.exclusion_results:
                lines.append(f"  {r.criterion_index}. {r.criterion_text}")
                lines.append(f"     Result: {r.label.value}")
                lines.append(f"     Reasoning: {r.reasoning[:150]}")

        return "\n".join(lines)
