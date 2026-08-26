"""Validated structured teaching content generated from learner materials."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LessonSource(BaseModel):
    """A traceable source excerpt used to build one lesson."""

    model_config = ConfigDict(frozen=True)

    document_id: str = Field(min_length=1, max_length=100)
    filename: str = Field(min_length=1, max_length=255)
    excerpt: str = Field(min_length=1, max_length=2_000)


class LessonSection(BaseModel):
    """One readable teaching section with a concrete learning purpose."""

    model_config = ConfigDict(frozen=True)

    section_type: Literal["concept", "mechanism", "boundary", "example"]
    title: str = Field(min_length=1, max_length=120)
    explanation: str = Field(min_length=1, max_length=4_000)
    key_points: list[str] = Field(min_length=1, max_length=8)
    example: str | None = Field(default=None, max_length=2_000)


class LessonInteraction(BaseModel):
    """A short objective check embedded in a conventional lesson."""

    model_config = ConfigDict(frozen=True)

    prompt: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(min_length=2, max_length=5)
    correct_answer: str = Field(min_length=1, max_length=500)
    explanation: str = Field(min_length=1, max_length=1_500)

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
