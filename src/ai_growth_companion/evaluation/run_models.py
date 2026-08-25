"""Strict records for reproducible golden-set evaluation runs."""

from datetime import datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, model_validator

from ai_growth_companion.evaluation.golden_set import GoldenScenario
from ai_growth_companion.prompts.registry import PromptVersion
from ai_growth_companion.schemas.diagnosis import (
    LearningAction,
    MasteryDecision,
    ProviderObservation,
    StrictSchema,
)


class EvaluationMode(StrEnum):
    """Whether a run exercised deterministic plumbing or a real Provider."""

    FAKE_PIPELINE = "fake_pipeline"
    REAL_PROVIDER = "real_provider"


class CaseRunStatus(StrEnum):
    """Terminal state for one case attempt."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RunConfiguration(StrictSchema):
    """Safety-relevant settings frozen with the run."""

    mode: EvaluationMode
    requested_cases: int = Field(ge=1, le=20)
    retries_per_case: Literal[0] = 0
    paid_calls_allowed: bool
    prompt_applied_to_provider: bool

    @model_validator(mode="after")
    def real_provider_requires_explicit_paid_permission(self) -> Self:
        if self.mode is EvaluationMode.REAL_PROVIDER and not self.paid_calls_allowed:
            raise ValueError("real Provider runs require explicit paid-call permission")
        if self.mode is EvaluationMode.FAKE_PIPELINE and self.paid_calls_allowed:
            raise ValueError("fake runs must not enable paid calls")
        return self


class ProviderMetadataSnapshot(StrictSchema):
    """Provider metadata detached from supplier SDK types."""

    provider: str
    model: str
    model_revision: str | None
    prompt_version: str
    schema_version: str
    latency_ms: int = Field(ge=0)
    usage: dict[str, int]
    finish_reason: str
    request_id: str


class AutomaticChecks(StrictSchema):
    """Deterministic checks; semantic correctness still requires human review."""

    observation_shape_matches: bool
    evidence_excerpts_valid: bool
    mastery_level_matches: bool
    recommended_action_matches: bool
    confidence_in_expected_range: bool
    passed: bool

    @model_validator(mode="after")
    def passed_must_equal_all_checks(self) -> Self:
        expected = all(
            (
                self.observation_shape_matches,
                self.evidence_excerpts_valid,
                self.mastery_level_matches,
                self.recommended_action_matches,
                self.confidence_in_expected_range,
            )
        )
        if self.passed is not expected:
            raise ValueError("automatic pass flag must equal all deterministic checks")
        return self


class CaseEvaluationResult(StrictSchema):
    """One Provider attempt plus deterministic policy output and checks."""

    case_id: str
    scenario: GoldenScenario
    status: CaseRunStatus
    prompt_applied_to_provider: bool
    provider_metadata: ProviderMetadataSnapshot | None = None
    observation: ProviderObservation | None = None
    decision: MasteryDecision | None = None
    next_action: LearningAction | None = None
    automatic_checks: AutomaticChecks | None = None
    requires_human_semantic_review: bool
    error_code: str | None = None
    failure_details: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def terminal_state_must_be_complete(self) -> Self:
        success_fields = (
            self.provider_metadata,
            self.observation,
            self.decision,
            self.next_action,
            self.automatic_checks,
        )
        if self.status is CaseRunStatus.SUCCEEDED:
            if any(value is None for value in success_fields) or self.error_code is not None:
                raise ValueError("successful case result is incomplete")
            if not self.requires_human_semantic_review:
                raise ValueError("successful AI evaluation requires human semantic review")
        elif any(value is not None for value in success_fields) or self.error_code is None:
            raise ValueError("failed case result contains success fields or lacks an error code")
        return self


class RunSummary(StrictSchema):
    """Non-sensitive aggregate suitable for console output and comparisons."""

    total_cases: int = Field(ge=1, le=20)
    succeeded_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)
    automatic_passed_cases: int = Field(ge=0)
    automatic_failed_cases: int = Field(ge=0)
    human_review_required_cases: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def counts_must_reconcile(self) -> Self:
        if self.succeeded_cases + self.failed_cases != self.total_cases:
            raise ValueError("run success and failure counts do not reconcile")
        if self.automatic_passed_cases + self.automatic_failed_cases != self.succeeded_cases:
            raise ValueError("automatic check counts do not reconcile")
        if self.human_review_required_cases != self.succeeded_cases:
            raise ValueError("every successful case requires human semantic review")
        return self


class GoldenEvaluationRun(StrictSchema):
    """A complete immutable evaluation-run artifact."""

    schema_version: Literal["golden-eval-run-v0.1"]
    run_id: str = Field(min_length=1)
    dataset_id: Literal["high-math-mastery-v0.1"]
    dataset_schema_version: Literal["golden-set-v0.1"]
    prompt_version: PromptVersion
    prompt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    configuration: RunConfiguration
    started_at: datetime
    finished_at: datetime
    cases: list[CaseEvaluationResult] = Field(min_length=1, max_length=20)
    summary: RunSummary

    @model_validator(mode="after")
    def run_must_match_summary(self) -> Self:
        if self.finished_at < self.started_at:
            raise ValueError("run cannot finish before it starts")
        if len(self.cases) != self.summary.total_cases:
            raise ValueError("case count does not match run summary")
        return self
