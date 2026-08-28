"""Validated structured teaching content generated from learner materials."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LessonSource(BaseModel):
    """A traceable source excerpt used to build one lesson."""

    model_config = ConfigDict(frozen=True)

    document_id: str = Field(min_length=1, max_length=100)
    filename: str = Field(min_length=1, max_length=255)
    excerpt: str = Field(min_length=1, max_length=2_000)


class LessonEvidence(BaseModel):
    """A short, inspectable piece of source evidence behind generated content."""

    model_config = ConfigDict(frozen=True)

    document_id: str = Field(min_length=1, max_length=100)
    page_number: int | None = Field(default=None, ge=1)
    quote: str = Field(min_length=2, max_length=800)


class TeachingPlanNode(BaseModel):
    """One concept in the lightweight, source-aware teaching route."""

    model_config = ConfigDict(frozen=True)

    node_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    purpose: str = Field(min_length=1, max_length=600)
    prerequisites: list[str] = Field(default_factory=list, max_length=8)
    discovery_prompt: str | None = Field(default=None, max_length=800)
    source_document_ids: list[str] = Field(default_factory=list, max_length=20)


class TeachingDependency(BaseModel):
    """A directed prerequisite edge in a teaching plan."""

    model_config = ConfigDict(frozen=True)

    from_node: str = Field(min_length=1, max_length=80)
    to_node: str = Field(min_length=1, max_length=80)


class TeachingPlan(BaseModel):
    """Validated plan shared by the local role agents before prose generation."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["teaching-plan-v0.1"] = "teaching-plan-v0.1"
    topic: str = Field(min_length=1, max_length=200)
    core_truths: list[str] = Field(default_factory=list, max_length=6)
    nodes: list[TeachingPlanNode] = Field(default_factory=list, max_length=8)
    dependencies: list[TeachingDependency] = Field(default_factory=list, max_length=16)
    visual_intent: Literal["none", "dependency_graph", "process", "comparison", "geometry"] = "none"
    visual_prompt: str | None = Field(default=None, max_length=500)


class LessonSection(BaseModel):
    """One readable teaching section with a concrete learning purpose."""

    model_config = ConfigDict(frozen=True)

    section_type: Literal["concept", "mechanism", "boundary", "example"]
    title: str = Field(min_length=1, max_length=120)
    explanation: str = Field(min_length=1, max_length=4_000)
    key_points: list[str] = Field(min_length=1, max_length=8)
    example: str | None = Field(default=None, max_length=2_000)
    why_it_matters: str | None = Field(default=None, max_length=800)
    discovery_path: str | None = Field(default=None, max_length=1_200)
    prerequisite_ids: list[str] = Field(default_factory=list, max_length=8)
    source_document_ids: list[str] = Field(default_factory=list, max_length=20)
    evidence: list[LessonEvidence] = Field(default_factory=list, max_length=4)


class LessonInteraction(BaseModel):
    """A short objective check embedded in a conventional lesson."""

    model_config = ConfigDict(frozen=True)

    prompt: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(min_length=2, max_length=5)
    correct_answer: str = Field(min_length=1, max_length=500)
    explanation: str = Field(min_length=1, max_length=1_500)
    source_document_ids: list[str] = Field(default_factory=list, max_length=20)
    evidence: list[LessonEvidence] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def correct_answer_is_available(self) -> "LessonInteraction":
        if self.correct_answer not in self.options:
            raise ValueError("correct_answer must be one of options")
        return self


class TeachingLesson(BaseModel):
    """A complete, source-grounded lesson card safe for the UI to render."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["teaching-lesson-v0.1", "teaching-lesson-v0.2"] = "teaching-lesson-v0.2"
    topic: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=2_000)
    learning_objectives: list[str] = Field(min_length=1, max_length=8)
    sections: list[LessonSection] = Field(min_length=3, max_length=8)
    check_questions: list[str] = Field(min_length=1, max_length=5)
    interactive_checks: list[LessonInteraction] = Field(default_factory=list, max_length=8)
    sources: list[LessonSource] = Field(min_length=1, max_length=20)
    teaching_plan: TeachingPlan | None = None
    # Evidence quality is deliberately recorded instead of making every citation issue
    # fatal.  A lesson can be useful before every visual page has been reconciled.
    grounding_status: Literal["verified", "repaired", "partial", "draft"] = "verified"
    grounding_issues: list[str] = Field(default_factory=list, max_length=20)
    # Translation is a derived aid for English/mixed source material.  It never
    # replaces the original evidence stored in the lesson sources.
    translation_status: Literal["not_needed", "pending", "translated", "fallback_original"] = (
        "not_needed"
    )
    translation_model: str | None = Field(default=None, max_length=120)
    translated_unit_count: int = Field(default=0, ge=0)
    translation_failed_unit_count: int = Field(default=0, ge=0)
