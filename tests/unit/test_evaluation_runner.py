"""Deterministic batch-runner, safety-gate, and result-contract tests."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_growth_companion.evaluation.golden_set import GoldenCase, load_golden_set
from ai_growth_companion.evaluation.run_models import EvaluationMode
from ai_growth_companion.evaluation.runner import run_golden_evaluation, save_evaluation_run
from ai_growth_companion.providers.fake import FakeLLMProvider, FakeScenario

GOLDEN_SET_PATH = Path("evals/golden/high_math_v0.1.json")


def matching_fake_provider(case: GoldenCase) -> FakeLLMProvider:
    return FakeLLMProvider(FakeScenario(case.scenario.value))


def test_fake_pipeline_matches_all_approved_automatic_expectations() -> None:
    golden_set = load_golden_set(GOLDEN_SET_PATH)

    run = run_golden_evaluation(
        golden_set,
        provider_factory=matching_fake_provider,
        mode=EvaluationMode.FAKE_PIPELINE,
        run_id="test-fake-run",
    )

    assert run.summary.total_cases == 20
    assert run.summary.succeeded_cases == 20
    assert run.summary.automatic_passed_cases == 20
    assert run.summary.human_review_required_cases == 20
    assert run.summary.input_tokens == 0
    assert run.summary.estimated_cost_usd is None
    assert run.configuration.paid_calls_allowed is False
    assert run.configuration.prompt_applied_to_provider is False
    assert all(result.automatic_checks and result.automatic_checks.passed for result in run.cases)
    partial_results = [result for result in run.cases if result.scenario.value == "partial"]
    assert all(
        result.decision and result.decision.mastery_level == "fragile" for result in partial_results
    )
    assert all(
        result.decision
        and result.decision.protocol_version == "mastery-protocol-v0.2-golden-baseline"
        for result in run.cases
    )


def test_provider_failure_is_retained_without_stopping_the_batch() -> None:
    golden_set = load_golden_set(GOLDEN_SET_PATH)

    run = run_golden_evaluation(
        golden_set,
        provider_factory=lambda _case: FakeLLMProvider(FakeScenario.PROVIDER_FAILURE),
        mode=EvaluationMode.FAKE_PIPELINE,
        max_cases=1,
        run_id="test-failure-run",
    )

    assert run.summary.failed_cases == 1
    assert run.summary.succeeded_cases == 0
    assert run.cases[0].error_code == "LLM_UNAVAILABLE"
    assert run.cases[0].requires_human_semantic_review is False


def test_real_provider_mode_requires_explicit_paid_call_permission() -> None:
    golden_set = load_golden_set(GOLDEN_SET_PATH)

    with pytest.raises(ValidationError, match="explicit paid-call permission"):
        run_golden_evaluation(
            golden_set,
            provider_factory=matching_fake_provider,
            mode=EvaluationMode.REAL_PROVIDER,
            max_cases=1,
            paid_calls_allowed=False,
        )


def test_run_artifact_is_saved_as_valid_json(tmp_path: Path) -> None:
    golden_set = load_golden_set(GOLDEN_SET_PATH)
    run = run_golden_evaluation(
        golden_set,
        provider_factory=matching_fake_provider,
        mode=EvaluationMode.FAKE_PIPELINE,
        max_cases=1,
        run_id="test-save-run",
    )
    output_path = tmp_path / "run.json"

    save_evaluation_run(run, output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "test-save-run"
    assert payload["summary"]["total_cases"] == 1
