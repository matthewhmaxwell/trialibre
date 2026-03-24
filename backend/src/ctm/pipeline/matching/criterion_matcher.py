"""Core LLM-based criterion matching engine.

Evaluates patient eligibility against trial criteria using batched LLM calls.
Each call evaluates multiple criteria at once (not one API call per criterion).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from jinja2 import Template

from ctm.config import MatchingConfig
from ctm.models.matching import CriterionResult, EligibilityLabel, MatchingResult
from ctm.models.patient import PatientNote
from ctm.models.trial import ClinicalTrial, EligibilityCriteria
from ctm.providers.base import LLMProvider

logger = logging.getLogger(__name__)

# Prompt version for audit trail
PROMPT_VERSION = "v1.0.0"


class CriterionMatcher:
    """Evaluates patient eligibility against trial criteria via LLM.

    Batches criteria per prompt to minimize API calls.
    A typical trial with 20 criteria uses 2 API calls (inclusion + exclusion),
    not 20 individual calls.
    """

    def __init__(self, llm: LLMProvider, config: MatchingConfig) -> None:
        self._llm = llm
        self._config = config
        self._inclusion_template = self._load_template("inclusion_matching.jinja2")
        self._exclusion_template = self._load_template("exclusion_matching.jinja2")

    def _load_template(self, name: str) -> Template:
        """Load a Jinja2 prompt template."""
        prompts_dir = Path(__file__).parent.parent.parent.parent / "config" / "prompts"
        template_path = prompts_dir / name
        if template_path.exists():
            return Template(template_path.read_text())
        # Fallback: use a basic template
        logger.warning(f"Prompt template not found: {template_path}")
        return Template("Evaluate the patient against these criteria. Output JSON.")

    async def match(
        self, patient: PatientNote, trial: ClinicalTrial
    ) -> MatchingResult:
        """Match a patient against a trial's eligibility criteria.

        Makes two LLM calls: one for inclusion, one for exclusion criteria.
        Criteria are batched within each call.

        Args:
            patient: Preprocessed patient note with numbered sentences.
            trial: Clinical trial with parsed criteria.

        Returns:
            MatchingResult with criterion-level assessments.
        """
        patient_text = patient.to_numbered_text()

        # Build trial context
        trial_context = self._build_trial_context(trial)

        # Evaluate inclusion criteria
        inclusion_results = await self._evaluate_criteria(
            patient_text,
            trial_context,
            trial.inclusion_criteria,
            "inclusion",
        )

        # Evaluate exclusion criteria
        exclusion_results = await self._evaluate_criteria(
            patient_text,
            trial_context,
            trial.exclusion_criteria,
            "exclusion",
        )

        return MatchingResult(
            patient_id=patient.patient_id,
            trial_id=trial.nct_id,
            inclusion_results=inclusion_results,
            exclusion_results=exclusion_results,
            prompt_version=PROMPT_VERSION,
            model_used=self._llm.model_name,
        )

    async def _evaluate_criteria(
        self,
        patient_text: str,
        trial_context: str,
        criteria: list[EligibilityCriteria],
        category: str,
    ) -> list[CriterionResult]:
        """Evaluate a set of criteria (inclusion or exclusion) via LLM."""
        if not criteria:
            return []

        # Batch criteria if there are too many for one prompt
        batches = self._batch_criteria(criteria)
        all_results = []

        for batch in batches:
            results = await self._evaluate_batch(
                patient_text, trial_context, batch, category
            )
            all_results.extend(results)

        return all_results

    async def _evaluate_batch(
        self,
        patient_text: str,
        trial_context: str,
        criteria: list[EligibilityCriteria],
        category: str,
    ) -> list[CriterionResult]:
        """Evaluate one batch of criteria via a single LLM call."""
        # Select template
        template = (
            self._inclusion_template
            if category == "inclusion"
            else self._exclusion_template
        )

        system_prompt = template.render()

        # Build criteria list for the prompt
        criteria_text = "\n".join(
            f"{c.index}. {c.text}" for c in criteria
        )

        user_prompt = (
            f"Patient Note:\n{patient_text}\n\n"
            f"Clinical Trial:\n{trial_context}\n\n"
            f"{'Inclusion' if category == 'inclusion' else 'Exclusion'} Criteria:\n"
            f"{criteria_text}\n\n"
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

            parsed = self._parse_response(response, criteria, category)
            return parsed

        except Exception as e:
            logger.error(f"Criterion matching failed for {category}: {e}")
            # Return "not enough information" for all criteria on failure
            return [
                CriterionResult(
                    criterion_index=c.index,
                    criterion_text=c.text,
                    category=category,
                    reasoning=f"Evaluation failed: {e}",
                    evidence_sentence_ids=[],
                    label=EligibilityLabel.NOT_ENOUGH_INFO,
                    confidence=0.0,
                )
                for c in criteria
            ]

    def _parse_response(
        self,
        response: str,
        criteria: list[EligibilityCriteria],
        category: str,
    ) -> list[CriterionResult]:
        """Parse the LLM JSON response into CriterionResult objects."""
        # Clean response
        text = response.strip().strip("`")
        if text.startswith("json"):
            text = text[4:].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse criterion response as JSON: {text[:200]}")
            return [
                CriterionResult(
                    criterion_index=c.index,
                    criterion_text=c.text,
                    category=category,
                    reasoning="Response parsing failed",
                    evidence_sentence_ids=[],
                    label=EligibilityLabel.NOT_ENOUGH_INFO,
                    confidence=0.0,
                )
                for c in criteria
            ]

        results = []
        for criterion in criteria:
            key = str(criterion.index)
            entry = data.get(key, [])

            if isinstance(entry, list) and len(entry) >= 3:
                reasoning = str(entry[0])
                sentence_ids = entry[1] if isinstance(entry[1], list) else []
                label_str = str(entry[2]).lower().strip()
            else:
                reasoning = str(entry) if entry else "No reasoning provided"
                sentence_ids = []
                label_str = "not enough information"

            # Map label string to enum
            label = self._parse_label(label_str, category)

            results.append(
                CriterionResult(
                    criterion_index=criterion.index,
                    criterion_text=criterion.text,
                    category=category,
                    reasoning=reasoning,
                    evidence_sentence_ids=[int(s) for s in sentence_ids if isinstance(s, (int, float))],
                    label=label,
                    confidence=0.9 if label != EligibilityLabel.NOT_ENOUGH_INFO else 0.5,
                )
            )

        return results

    def _parse_label(self, label_str: str, category: str) -> EligibilityLabel:
        """Parse a label string to EligibilityLabel enum."""
        label_map = {
            "included": EligibilityLabel.INCLUDED,
            "not included": EligibilityLabel.NOT_INCLUDED,
            "excluded": EligibilityLabel.EXCLUDED,
            "not excluded": EligibilityLabel.NOT_EXCLUDED,
            "not applicable": EligibilityLabel.NOT_APPLICABLE,
            "not enough information": EligibilityLabel.NOT_ENOUGH_INFO,
        }
        return label_map.get(label_str, EligibilityLabel.NOT_ENOUGH_INFO)

    def _batch_criteria(
        self, criteria: list[EligibilityCriteria]
    ) -> list[list[EligibilityCriteria]]:
        """Split criteria into batches that fit within token limits."""
        max_per_batch = self._config.max_criteria_per_prompt
        batches = []
        for i in range(0, len(criteria), max_per_batch):
            batches.append(criteria[i : i + max_per_batch])
        return batches

    def _build_trial_context(self, trial: ClinicalTrial) -> str:
        """Build trial context string for the prompt."""
        parts = [f"Title: {trial.brief_title}"]
        if trial.diseases:
            parts.append(f"Target Conditions: {', '.join(trial.diseases)}")
        if trial.interventions:
            parts.append(f"Interventions: {', '.join(trial.interventions)}")
        if trial.brief_summary:
            parts.append(f"Summary: {trial.brief_summary[:500]}")
        return "\n".join(parts)
