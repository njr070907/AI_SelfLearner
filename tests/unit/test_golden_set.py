"""Contract and provenance tests for the Sprint 1 high-math golden set."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_growth_companion.evaluation.golden_set import (
    GoldenScenario,
    GoldenSet,
    ReviewStatus,
    load_golden_set,
)

GOLDEN_SET_PATH = Path("evals/golden/high_math_v0.1.json")


def load_payload() -> dict[str, object]:
    """Return a mutable copy of the canonical JSON payload."""
    return json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))


def test_canonical_golden_set_has_complete_scenario_matrix() -> None:
    golden_set = load_golden_set(GOLDEN_SET_PATH)

    assert len(golden_set.cases) == 20
    concept_ids = {case.concept_id for case in golden_set.cases}
    assert len(concept_ids) == 5

    for concept_id in concept_ids:
        scenarios = {case.scenario for case in golden_set.cases if case.concept_id == concept_id}
        assert scenarios == set(GoldenScenario)


def test_canonical_golden_set_is_human_approved() -> None:
    golden_set = load_golden_set(GOLDEN_SET_PATH)

    assert golden_set.status == "approved"
    assert all(case.human_review.status is ReviewStatus.APPROVED for case in golden_set.cases)


def test_approved_dataset_rejects_an_unreviewed_case() -> None:
    payload = load_payload()
    cases = payload["cases"]
    assert isinstance(cases, list)
    first_case = cases[0]
    assert isinstance(first_case, dict)
    first_case["human_review"] = {
        "status": "pending",
        "reviewer": None,
        "reviewed_at": None,
        "notes": [],
    }

    with pytest.raises(ValidationError, match="requires every case to be human-approved"):
        GoldenSet.model_validate(payload)


def test_canonical_golden_set_does_not_include_source_pdfs() -> None:
    golden_set = load_golden_set(GOLDEN_SET_PATH)

    assert golden_set.source_policy.raw_pdfs_in_repository is False
    assert all(source.included_in_repository is False for source in golden_set.sources)


def test_duplicate_case_id_is_rejected() -> None:
    payload = load_payload()
    cases = payload["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[1], dict)
    assert isinstance(cases[5], dict)
    cases[5]["case_id"] = cases[1]["case_id"]

    with pytest.raises(ValidationError, match="case IDs must be unique"):
        GoldenSet.model_validate(payload)


def test_unknown_source_reference_is_rejected() -> None:
    payload = load_payload()
    cases = payload["cases"]
    assert isinstance(cases, list)
    first_case = cases[0]
    assert isinstance(first_case, dict)
    source_refs = first_case["source_refs"]
    assert isinstance(source_refs, list)
    assert isinstance(source_refs[0], dict)
    source_refs[0]["document_id"] = "missing-source"

    with pytest.raises(ValidationError, match="unknown source document"):
        GoldenSet.model_validate(payload)


def test_non_strong_case_cannot_allow_solid_mastery() -> None:
    payload = load_payload()
    cases = payload["cases"]
    assert isinstance(cases, list)
    partial_case = deepcopy(cases[1])
    assert isinstance(partial_case, dict)
    rubric = partial_case["rubric"]
    assert isinstance(rubric, dict)
    rubric["acceptable_mastery_levels"] = ["solid"]
    rubric["forbidden_mastery_levels"] = ["no_clue"]
    cases[1] = partial_case

    with pytest.raises(ValidationError, match="non-strong case must forbid solid mastery"):
        GoldenSet.model_validate(payload)


def test_case_id_suffix_must_match_scenario() -> None:
    payload = load_payload()
    cases = payload["cases"]
    assert isinstance(cases, list)
    first_case = cases[0]
    assert isinstance(first_case, dict)
    first_case["scenario"] = "partial"

    with pytest.raises(ValidationError, match="case ID suffix must match scenario"):
        GoldenSet.model_validate(payload)
