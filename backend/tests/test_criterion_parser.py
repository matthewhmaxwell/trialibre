"""Tests for `CriterionMatcher._parse_response`.

The criterion-matching prompt asks the LLM to emit results as
`{"0": ["reasoning", [sentence_ids], "label"], ...}`. In practice, smaller
open-weight models (e.g. llama3.2:3b) tend to emit the more conventional
dict shape `{"0": {"reasoning": ..., "sentence_ids": [...], "label": ...}}`
instead, and they often serialize sentence_ids as strings.

This regression test pins both shapes to the parser so a future tightening
of the prompt or a new model can't silently revert us to "all unknown."
"""

from __future__ import annotations

import json

from ctm.config import MatchingConfig
from ctm.models.matching import EligibilityLabel
from ctm.models.trial import EligibilityCriteria
from ctm.pipeline.matching.criterion_matcher import CriterionMatcher


def _matcher() -> CriterionMatcher:
    # The parser path doesn't touch the LLM, so we can pass None as the
    # provider — the test only exercises _parse_response.
    return CriterionMatcher(llm=None, config=MatchingConfig())  # type: ignore[arg-type]


def _criteria() -> list[EligibilityCriteria]:
    return [
        EligibilityCriteria(index=0, text="Age 18-75 years", category="inclusion"),
        EligibilityCriteria(index=1, text="HbA1c 7.5%-10.0%", category="inclusion"),
        EligibilityCriteria(index=2, text="BMI 25-45", category="inclusion"),
    ]


def test_parses_canonical_array_shape():
    """The shape we *ask* for in the prompt: `[reasoning, [ids], label]`."""
    matcher = _matcher()
    response = json.dumps(
        {
            "0": ["Patient is 45.", [1, 6], "included"],
            "1": ["HbA1c is 8.2%.", [16], "included"],
            "2": ["BMI is 31.1.", [8], "included"],
        }
    )

    results = matcher._parse_response(response, _criteria(), category="inclusion")

    assert [r.label for r in results] == [EligibilityLabel.INCLUDED] * 3
    assert results[0].evidence_sentence_ids == [1, 6]
    assert results[1].reasoning.startswith("HbA1c")


def test_parses_dict_shape_emitted_by_small_models():
    """The shape llama3.2:3b actually returns under JSON mode."""
    matcher = _matcher()
    response = json.dumps(
        {
            "0": {
                "reasoning": "Patient is 45, in 18-75 range.",
                "sentence_ids": ["1", "6"],
                "label": "included",
            },
            "1": {
                "reasoning": "HbA1c 8.2% is in 7.5-10.0 range.",
                "sentence_ids": ["16"],
                "label": "included",
            },
            "2": {
                "reasoning": "BMI 31.1 is within 25-45.",
                "sentence_ids": ["8"],
                "label": "included",
            },
        }
    )

    results = matcher._parse_response(response, _criteria(), category="inclusion")

    assert [r.label for r in results] == [EligibilityLabel.INCLUDED] * 3
    # String sentence_ids must be coerced to ints.
    assert results[0].evidence_sentence_ids == [1, 6]
    assert results[1].evidence_sentence_ids == [16]
    assert "BMI" in results[2].reasoning


def test_dict_shape_tolerates_key_aliases():
    """Some prompts/models use 'rationale' or 'eligibility' instead."""
    matcher = _matcher()
    response = json.dumps(
        {
            "0": {
                "rationale": "Age in range.",
                "evidence": [1],
                "eligibility": "included",
            },
            "1": {
                "explanation": "HbA1c too high.",
                "sentences": [16],
                "status": "not included",
            },
            "2": {  # missing fields → degrade safely
                "label": "not enough information",
            },
        }
    )

    results = matcher._parse_response(response, _criteria(), category="inclusion")

    assert results[0].label == EligibilityLabel.INCLUDED
    assert results[1].label == EligibilityLabel.NOT_INCLUDED
    assert results[2].label == EligibilityLabel.NOT_ENOUGH_INFO
    assert results[1].evidence_sentence_ids == [16]


def test_unparseable_json_returns_unknown_for_all():
    """Garbage in → no crash, every criterion marked NOT_ENOUGH_INFO."""
    matcher = _matcher()
    results = matcher._parse_response("this is not json", _criteria(), category="inclusion")

    assert len(results) == 3
    assert all(r.label == EligibilityLabel.NOT_ENOUGH_INFO for r in results)


def test_missing_keys_get_unknown_label():
    """If the model only answers some criteria, the rest get NOT_ENOUGH_INFO."""
    matcher = _matcher()
    response = json.dumps(
        {"0": {"reasoning": "Age fine.", "sentence_ids": [1], "label": "included"}}
    )

    results = matcher._parse_response(response, _criteria(), category="inclusion")

    assert results[0].label == EligibilityLabel.INCLUDED
    assert results[1].label == EligibilityLabel.NOT_ENOUGH_INFO
    assert results[2].label == EligibilityLabel.NOT_ENOUGH_INFO


def test_string_response_with_json_code_fence():
    """Model output wrapped in ```json ... ``` should still parse."""
    matcher = _matcher()
    response = (
        "```json\n"
        + json.dumps(
            {
                "0": ["Age fine.", [1], "included"],
                "1": ["HbA1c high.", [16], "not included"],
                "2": ["BMI fine.", [8], "included"],
            }
        )
        + "\n```"
    )

    results = matcher._parse_response(response, _criteria(), category="inclusion")
    assert [r.label for r in results] == [
        EligibilityLabel.INCLUDED,
        EligibilityLabel.NOT_INCLUDED,
        EligibilityLabel.INCLUDED,
    ]
