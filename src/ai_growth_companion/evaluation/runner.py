"""Batch runner for deterministic and future real-Provider golden-set evaluations."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from ai_growth_companion.domain.mastery import DemoLearningPolicy, DemoMasteryEngine
from ai_growth_companion.evaluation.golden_set import (
    GoldenCase,
    GoldenScenario,
    GoldenSet,
)
from ai_growth_companion.evaluation.run_models import (
    AutomaticChecks,
    CaseEvaluationResult,
    CaseRunStatus,
    EvaluationMode,
    GoldenEvaluationRun,
    ProviderMetadataSnapshot,
    RunConfiguration,
    RunSummary,
)
from ai_growth_companion.prompts.registry import PromptRegistry
from ai_growth_companion.providers.base import (
    EvaluationProvider,
    EvaluationRequest,
    ProviderError,
)
from ai_growth_companion.schemas.diagnosis import (
    ProviderObservation,
    validate_answer_excerpts,
)

ProviderFactory = Callable[[GoldenCase], EvaluationProvider]


def run_golden_evaluation(
    golden_set: GoldenSet,
    *,
    provider_factory: ProviderFactory,
    mode: EvaluationMode,
    max_cases: int = 20,
    paid_calls_allowed: bool = False,
    prompt_registry: PromptRegistry | None = None,
    run_id: str | None = None,
) -> GoldenEvaluationRun:
    """Run a bounded, zero-retry batch and retain every structured attempt."""
    configuration = RunConfiguration(
        mode=mode,
        requested_cases=max_cases,
        paid_calls_allowed=paid_calls_allowed,
        prompt_applied_to_provider=mode is EvaluationMode.REAL_PROVIDER,
    )
    registry = prompt_registry or PromptRegistry()
    prompt_bundle = registry.load_evaluation()
    selected_cases = golden_set.cases[: configuration.requested_cases]
    actual_run_id = run_id or f"golden-{uuid4()}"
    started_at = datetime.now(UTC)
    results = [
        _run_case(
            case,
            provider_factory=provider_factory,
            configuration=configuration,
            run_id=actual_run_id,
            prompt_registry=registry,
        )
        for case in selected_cases
    ]
    finished_at = datetime.now(UTC)
    summary = _summarize(results)
    return GoldenEvaluationRun(
        schema_version="golden-eval-run-v0.1",
        run_id=actual_run_id,
        dataset_id=golden_set.dataset_id,
        dataset_schema_version=golden_set.schema_version,
        prompt_version=prompt_bundle.manifest.version,
        prompt_sha256=prompt_bundle.sha256,
        configuration=configuration,
        started_at=started_at,
        finished_at=finished_at,
        cases=results,
        summary=summary,
    )


def _run_case(
    case: GoldenCase,
    *,
    provider_factory: ProviderFactory,
    configuration: RunConfiguration,
    run_id: str,
    prompt_registry: PromptRegistry,
) -> CaseEvaluationResult:
    request = EvaluationRequest(
        concept=case.concept,
        question_text=case.question_text,
        coverage_points=tuple(case.coverage_points),
        answer_text=case.learner_answer,
    )
    prompt_registry.render_evaluation(request)
    provider = provider_factory(case)
    request_id = f"{run_id}:{case.case_id}"
    try:
        response = provider.evaluate(request, request_id=request_id)
    except ProviderError as error:
        return _failed_result(case, configuration, error.code)

    try:
        observation = ProviderObservation.model_validate(response.content)
    except ValidationError:
        return _failed_result(case, configuration, "LLM_OUTPUT_SCHEMA_INVALID")

    try:
        validate_answer_excerpts(observation, request.answer_text)
    except ValueError:
        return _failed_result(case, configuration, "LLM_OUTPUT_EVIDENCE_INVALID")

    decision = DemoMasteryEngine().decide(
        observation,
        observation_id=f"{request_id}:observation",
    )
    action = DemoLearningPolicy().choose(observation, decision)
    checks = _automatic_checks(case, observation, decision.mastery_level, action.action_type)
    metadata = ProviderMetadataSnapshot(
        provider=response.metadata.provider,
        model=response.metadata.model,
        model_revision=response.metadata.model_revision,
        prompt_version=response.metadata.prompt_version,
        schema_version=response.metadata.schema_version,
        latency_ms=response.metadata.latency_ms,
        usage=response.metadata.usage,
        finish_reason=response.metadata.finish_reason,
        request_id=response.metadata.request_id,
    )
    return CaseEvaluationResult(
        case_id=case.case_id,
        scenario=case.scenario,
        status=CaseRunStatus.SUCCEEDED,
        prompt_applied_to_provider=configuration.prompt_applied_to_provider,
        provider_metadata=metadata,
        observation=observation,
        decision=decision,
        next_action=action,
        automatic_checks=checks,
        requires_human_semantic_review=True,
    )


def _failed_result(
    case: GoldenCase,
    configuration: RunConfiguration,
    error_code: str,
) -> CaseEvaluationResult:
    return CaseEvaluationResult(
        case_id=case.case_id,
        scenario=case.scenario,
        status=CaseRunStatus.FAILED,
        prompt_applied_to_provider=configuration.prompt_applied_to_provider,
        requires_human_semantic_review=False,
        error_code=error_code,
    )


def _automatic_checks(
    case: GoldenCase,
    observation: ProviderObservation,
    mastery_level: object,
    action_type: object,
) -> AutomaticChecks:
    shape_matches = _observation_shape_matches(case.scenario, observation)
    mastery_matches = (
        mastery_level in case.rubric.acceptable_mastery_levels
        and mastery_level not in case.rubric.forbidden_mastery_levels
    )
    action_matches = action_type in case.rubric.recommended_actions
    confidence_matches = (
        case.rubric.confidence.minimum
        <= observation.observation_confidence
        <= case.rubric.confidence.maximum
    )
    values = (shape_matches, True, mastery_matches, action_matches, confidence_matches)
    return AutomaticChecks(
        observation_shape_matches=shape_matches,
        evidence_excerpts_valid=True,
        mastery_level_matches=mastery_matches,
        recommended_action_matches=action_matches,
        confidence_in_expected_range=confidence_matches,
        passed=all(values),
    )


def _observation_shape_matches(
    scenario: GoldenScenario,
    observation: ProviderObservation,
) -> bool:
    if scenario is GoldenScenario.STRONG:
        return (
            bool(observation.evidence)
            and not observation.gaps
            and not (observation.possible_misconceptions)
        )
    if scenario is GoldenScenario.PARTIAL:
        return (
            bool(observation.evidence)
            and bool(observation.gaps)
            and not observation.possible_misconceptions
        )
    if scenario is GoldenScenario.MISCONCEPTION:
        return bool(observation.possible_misconceptions)
    return not observation.evidence and bool(observation.gaps) and bool(observation.limitations)


def _summarize(results: list[CaseEvaluationResult]) -> RunSummary:
    succeeded = [result for result in results if result.status is CaseRunStatus.SUCCEEDED]
    failed = [result for result in results if result.status is CaseRunStatus.FAILED]
    automatic_passed = [
        result
        for result in succeeded
        if result.automatic_checks is not None and result.automatic_checks.passed
    ]
    input_tokens = sum(
        (result.provider_metadata.usage.get("input_tokens", 0))
        for result in succeeded
        if result.provider_metadata is not None
    )
    output_tokens = sum(
        (result.provider_metadata.usage.get("output_tokens", 0))
        for result in succeeded
        if result.provider_metadata is not None
    )
    return RunSummary(
        total_cases=len(results),
        succeeded_cases=len(succeeded),
        failed_cases=len(failed),
        automatic_passed_cases=len(automatic_passed),
        automatic_failed_cases=len(succeeded) - len(automatic_passed),
        human_review_required_cases=len(succeeded),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=None,
    )


def save_evaluation_run(run: GoldenEvaluationRun, output_path: Path) -> None:
    """Atomically write a local run artifact under an ignored output directory."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(run.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
