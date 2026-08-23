"""Strict contracts for human-reviewed Mastery Protocol golden sets."""

import json
from collections import Counter
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator

from ai_growth_companion.schemas.diagnosis import (
    ActionType,
    MasteryLevel,
    StrictSchema,
)


class GoldenScenario(StrEnum):
    """The four answer qualities every selected concept must cover."""

    STRONG = "strong"
    PARTIAL = "partial"
    MISCONCEPTION = "misconception"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ReviewStatus(StrEnum):
    """Human review state kept separately from machine validation."""

    PENDING = "pending"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"


class SourcePolicy(StrictSchema):
    """Repository rules for copyrighted reference material."""

    raw_pdfs_in_repository: Literal[False] = False
    derived_cases_are_original: Literal[True] = True
    source_text_is_not_reproduced: Literal[True] = True


class SourceDocument(StrictSchema):
    """A local reference identified without exposing an absolute local path."""

    document_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=200)
    page_count: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    included_in_repository: Literal[False] = False


class SourceReference(StrictSchema):
    """Page-level provenance for one original evaluation case."""

    document_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    pages: list[int] = Field(min_length=1)
    topics: list[str] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def pages_must_be_unique_and_positive(self) -> Self:
        if any(page <= 0 for page in self.pages):
            raise ValueError("source pages must be positive")
        if len(self.pages) != len(set(self.pages)):
            raise ValueError("source pages must be unique")
        return self


class ConfidenceRange(StrictSchema):
    """Acceptable confidence interval for a provider observation."""

    minimum: float = Field(ge=0, le=1)
    maximum: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def minimum_must_not_exceed_maximum(self) -> Self:
        if self.minimum > self.maximum:
            raise ValueError("confidence minimum must not exceed maximum")
        return self


class EvaluationRubric(StrictSchema):
    """Human-readable expectations used to score model observations and decisions."""

    required_evidence: list[str] = Field(max_length=6)
    required_gaps: list[str] = Field(max_length=6)
    required_misconceptions: list[str] = Field(max_length=4)
    required_limitations: list[str] = Field(max_length=4)
    forbidden_claims: list[str] = Field(min_length=1, max_length=6)
    acceptable_mastery_levels: list[MasteryLevel] = Field(min_length=1, max_length=3)
    forbidden_mastery_levels: list[MasteryLevel] = Field(min_length=1, max_length=3)
    recommended_actions: list[ActionType] = Field(min_length=1, max_length=3)
    confidence: ConfidenceRange
    evaluator_note: str = Field(min_length=1, max_length=800)

    @model_validator(mode="after")
    def mastery_level_sets_must_be_disjoint(self) -> Self:
        acceptable = set(self.acceptable_mastery_levels)
        forbidden = set(self.forbidden_mastery_levels)
        if acceptable & forbidden:
            raise ValueError("acceptable and forbidden mastery levels must be disjoint")
        return self


class HumanReview(StrictSchema):
    """Review metadata; pending cases cannot masquerade as approved ground truth."""

    status: ReviewStatus
    reviewer: str | None = Field(default=None, min_length=1, max_length=100)
    reviewed_at: datetime | None = None
    notes: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def review_identity_must_match_status(self) -> Self:
        if self.status is ReviewStatus.PENDING:
            if self.reviewer is not None or self.reviewed_at is not None:
                raise ValueError("pending review cannot have reviewer or reviewed_at")
        elif self.reviewer is None or self.reviewed_at is None:
            raise ValueError("completed review requires reviewer and reviewed_at")
        return self


class GoldenCase(StrictSchema):
    """One original question-answer example with an explicit scoring rubric."""

    case_id: str = Field(pattern=r"^hm-[a-z0-9-]+-(strong|partial|misconception|insufficient)$")
    concept_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    concept: str = Field(min_length=1, max_length=100)
    scenario: GoldenScenario
    question_text: str = Field(min_length=20, max_length=1000)
    learner_answer: str = Field(min_length=2, max_length=2000)
    coverage_points: list[str] = Field(min_length=2, max_length=6)
    rubric: EvaluationRubric
    source_refs: list[SourceReference] = Field(min_length=1, max_length=4)
    human_review: HumanReview

    @model_validator(mode="after")
    def scenario_must_have_safe_rubric(self) -> Self:
        acceptable = set(self.rubric.acceptable_mastery_levels)
        forbidden = set(self.rubric.forbidden_mastery_levels)
        scenario_suffix = self.scenario.value.replace("_evidence", "")

        if not self.case_id.endswith(f"-{scenario_suffix}"):
            raise ValueError("case ID suffix must match scenario")

        if self.scenario is GoldenScenario.STRONG:
            if MasteryLevel.SOLID not in acceptable:
                raise ValueError("strong case must allow solid mastery")
            if not self.rubric.required_evidence:
                raise ValueError("strong case requires evidence expectations")
        else:
            if MasteryLevel.SOLID not in forbidden:
                raise ValueError("non-strong case must forbid solid mastery")

        if self.scenario is GoldenScenario.PARTIAL and not self.rubric.required_gaps:
            raise ValueError("partial case requires gap expectations")
        if (
            self.scenario is GoldenScenario.MISCONCEPTION
            and not self.rubric.required_misconceptions
        ):
            raise ValueError("misconception case requires misconception expectations")
        if self.scenario is GoldenScenario.INSUFFICIENT_EVIDENCE:
            if self.rubric.required_evidence:
                raise ValueError("insufficient-evidence case cannot require positive evidence")
            if not self.rubric.required_limitations:
                raise ValueError("insufficient-evidence case requires limitations")
        return self


class GoldenSet(StrictSchema):
    """The complete versioned Sprint 1 high-math evaluation dataset."""

    schema_version: Literal["golden-set-v0.1"]
    dataset_id: Literal["high-math-mastery-v0.1"]
    language: Literal["zh-CN"]
    status: Literal["draft_human_review", "approved"]
    mastery_protocol_version: str = Field(min_length=1)
    purpose: str = Field(min_length=1, max_length=500)
    source_policy: SourcePolicy
    sources: list[SourceDocument] = Field(min_length=1)
    cases: list[GoldenCase] = Field(min_length=20, max_length=20)

    @model_validator(mode="after")
    def dataset_must_be_complete_and_traceable(self) -> Self:
        source_map = {source.document_id: source for source in self.sources}
        if len(source_map) != len(self.sources):
            raise ValueError("source document IDs must be unique")

        case_ids = {case.case_id for case in self.cases}
        if len(case_ids) != len(self.cases):
            raise ValueError("case IDs must be unique")

        concept_counts = Counter(case.concept_id for case in self.cases)
        if len(concept_counts) != 5 or set(concept_counts.values()) != {4}:
            raise ValueError("dataset must contain five concepts with four cases each")

        expected_scenarios = set(GoldenScenario)
        for concept_id in concept_counts:
            actual = {case.scenario for case in self.cases if case.concept_id == concept_id}
            if actual != expected_scenarios:
                raise ValueError(f"concept {concept_id} must cover all four scenarios")

        for case in self.cases:
            for reference in case.source_refs:
                source = source_map.get(reference.document_id)
                if source is None:
                    raise ValueError(f"unknown source document: {reference.document_id}")
                if max(reference.pages) > source.page_count:
                    raise ValueError(f"source page exceeds page count: {reference.document_id}")

        all_approved = all(case.human_review.status is ReviewStatus.APPROVED for case in self.cases)
        if self.status == "approved" and not all_approved:
            raise ValueError("approved dataset requires every case to be human-approved")
        return self


def load_golden_set(path: Path) -> GoldenSet:
    """Load and strictly validate a UTF-8 JSON golden set."""
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return GoldenSet.model_validate(payload)
