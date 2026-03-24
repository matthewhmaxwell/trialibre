"""Mock matcher that returns precomputed results for sandbox mode.

No LLM calls are made. Results are loaded from the precomputed matches directory.
This allows the full UI to be functional without any API key configuration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ctm.models.matching import (
    CriterionResult,
    EligibilityLabel,
    MatchingResult,
    MatchStrength,
    PatientTrialRanking,
    TrialScore,
)
from ctm.models.patient import PatientNote
from ctm.models.trial import ClinicalTrial
from ctm.sandbox.loader import load_ground_truth, load_precomputed_matches


class SandboxMatcher:
    """Returns precomputed match results without calling any LLM.

    Used when sandbox mode is active (no API key configured).
    """

    def __init__(self) -> None:
        self._ground_truth = load_ground_truth()
        self._precomputed = load_precomputed_matches()

    async def match_patient(
        self,
        patient: PatientNote,
        trials: list[ClinicalTrial],
        max_trials: int = 50,
    ) -> PatientTrialRanking:
        """Return precomputed results for a sandbox patient.

        If precomputed results exist for this patient, returns them.
        Otherwise, generates synthetic results based on ground truth labels.
        """
        # Check for full precomputed results
        if patient.patient_id in self._precomputed:
            return self._precomputed[patient.patient_id]

        # Generate results from ground truth labels
        patient_gt = self._ground_truth.get(patient.patient_id, {})
        scores = []

        for trial in trials[:max_trials]:
            expected = patient_gt.get(trial.nct_id, "unlikely")
            strength = MatchStrength(expected) if expected in MatchStrength.__members__.values() else MatchStrength.UNLIKELY

            # Generate realistic-looking scores based on strength
            if strength == MatchStrength.STRONG:
                combined = 0.85
                matching = 0.9
                relevance = 0.85
                eligibility = 0.8
            elif strength == MatchStrength.POSSIBLE:
                combined = 0.55
                matching = 0.6
                relevance = 0.7
                eligibility = 0.3
            else:
                combined = 0.2
                matching = 0.3
                relevance = 0.4
                eligibility = -0.3

            inc_count = len(trial.inclusion_criteria)
            exc_count = len(trial.exclusion_criteria)

            if strength == MatchStrength.STRONG:
                met = int(inc_count * 0.85)
                not_met = 0
                excluded = 0
                unknown = inc_count - met
            elif strength == MatchStrength.POSSIBLE:
                met = int(inc_count * 0.6)
                not_met = 0
                excluded = 0
                unknown = inc_count - met
            else:
                met = int(inc_count * 0.3)
                not_met = max(1, int(inc_count * 0.2))
                excluded = max(1, int(exc_count * 0.3))
                unknown = inc_count - met - not_met

            scores.append(
                TrialScore(
                    trial_id=trial.nct_id,
                    trial_title=trial.brief_title,
                    matching_score=matching,
                    relevance_score=relevance,
                    eligibility_score=eligibility,
                    combined_score=combined,
                    strength=strength,
                    relevance_explanation=f"Patient condition aligns with trial focus on {', '.join(trial.diseases[:2])}.",
                    eligibility_explanation=_generate_explanation(strength, trial),
                    criteria_met=met,
                    criteria_not_met=not_met,
                    criteria_excluded=excluded,
                    criteria_unknown=unknown,
                    criteria_total=inc_count + exc_count,
                )
            )

        # Sort by combined score descending
        scores.sort(key=lambda s: s.combined_score, reverse=True)

        return PatientTrialRanking(
            patient_id=patient.patient_id,
            scores=scores,
            total_trials_screened=len(trials),
            retrieval_time_ms=120.0,  # Simulated
            matching_time_ms=850.0,
            ranking_time_ms=45.0,
            metadata={"sandbox": True},
        )

    async def get_criterion_details(
        self,
        patient: PatientNote,
        trial: ClinicalTrial,
    ) -> MatchingResult:
        """Generate detailed criterion-level results for sandbox display."""
        patient_gt = self._ground_truth.get(patient.patient_id, {})
        expected = patient_gt.get(trial.nct_id, "unlikely")

        inclusion_results = []
        for crit in trial.inclusion_criteria:
            label = _assign_criterion_label(expected, crit, "inclusion", patient)
            inclusion_results.append(
                CriterionResult(
                    criterion_index=crit.index,
                    criterion_text=crit.text,
                    category="inclusion",
                    reasoning=f"Based on patient record analysis for: {crit.text}",
                    plain_reasoning=_generate_plain_reasoning(label, crit.text, patient),
                    evidence_sentence_ids=[0, 1] if patient.sentences else [],
                    label=label,
                    confidence=0.9 if label != EligibilityLabel.NOT_ENOUGH_INFO else 0.5,
                )
            )

        exclusion_results = []
        for crit in trial.exclusion_criteria:
            label = _assign_criterion_label(expected, crit, "exclusion", patient)
            exclusion_results.append(
                CriterionResult(
                    criterion_index=crit.index,
                    criterion_text=crit.text,
                    category="exclusion",
                    reasoning=f"Based on patient record analysis for: {crit.text}",
                    plain_reasoning=_generate_plain_reasoning(label, crit.text, patient),
                    evidence_sentence_ids=[],
                    label=label,
                    confidence=0.9 if label != EligibilityLabel.NOT_ENOUGH_INFO else 0.5,
                )
            )

        return MatchingResult(
            patient_id=patient.patient_id,
            trial_id=trial.nct_id,
            inclusion_results=inclusion_results,
            exclusion_results=exclusion_results,
            prompt_version="sandbox-v1",
            model_used="sandbox-mock",
        )


def _assign_criterion_label(
    expected_strength: str,
    criterion,
    category: str,
    patient: PatientNote,
) -> EligibilityLabel:
    """Assign a plausible criterion label based on expected match strength."""
    import random

    random.seed(hash(f"{patient.patient_id}:{criterion.text}"))

    if expected_strength == "strong":
        if category == "inclusion":
            return random.choices(
                [EligibilityLabel.INCLUDED, EligibilityLabel.NOT_ENOUGH_INFO],
                weights=[85, 15],
            )[0]
        else:
            return random.choices(
                [EligibilityLabel.NOT_EXCLUDED, EligibilityLabel.NOT_APPLICABLE],
                weights=[70, 30],
            )[0]
    elif expected_strength == "possible":
        if category == "inclusion":
            return random.choices(
                [EligibilityLabel.INCLUDED, EligibilityLabel.NOT_ENOUGH_INFO],
                weights=[55, 45],
            )[0]
        else:
            return random.choices(
                [EligibilityLabel.NOT_EXCLUDED, EligibilityLabel.NOT_ENOUGH_INFO],
                weights=[70, 30],
            )[0]
    else:  # unlikely
        if category == "inclusion":
            return random.choices(
                [EligibilityLabel.INCLUDED, EligibilityLabel.NOT_INCLUDED, EligibilityLabel.NOT_ENOUGH_INFO],
                weights=[30, 40, 30],
            )[0]
        else:
            return random.choices(
                [EligibilityLabel.EXCLUDED, EligibilityLabel.NOT_EXCLUDED, EligibilityLabel.NOT_APPLICABLE],
                weights=[40, 30, 30],
            )[0]


def _generate_explanation(strength: MatchStrength, trial: ClinicalTrial) -> str:
    """Generate a brief explanation for the match strength."""
    if strength == MatchStrength.STRONG:
        return "Patient appears to meet most eligibility criteria for this trial."
    elif strength == MatchStrength.POSSIBLE:
        return "Some eligibility criteria could not be verified with the available patient information."
    else:
        return "Patient may not meet one or more key eligibility criteria for this trial."


def _generate_plain_reasoning(
    label: EligibilityLabel, criterion_text: str, patient: PatientNote
) -> str:
    """Generate plain-language reasoning for a criterion result."""
    if label == EligibilityLabel.INCLUDED:
        return f"Patient record supports meeting this requirement."
    elif label == EligibilityLabel.NOT_INCLUDED:
        return f"Patient record suggests this requirement is not met."
    elif label == EligibilityLabel.EXCLUDED:
        return f"Patient may have a condition that prevents participation."
    elif label == EligibilityLabel.NOT_EXCLUDED:
        return f"No evidence in patient record that this exclusion applies."
    elif label == EligibilityLabel.NOT_APPLICABLE:
        return f"This criterion does not apply to this patient."
    else:
        return f"Patient record does not mention information related to this. This may need to be confirmed."
