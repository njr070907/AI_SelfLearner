"""Immutable learning events and recomputable concept state models."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_growth_companion.domain.feedback import ConceptTrend
from ai_growth_companion.schemas.diagnosis import normalize_mastery_level

LOCAL_USER_ID = "00000000-0000-4000-8000-000000000001"


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(UTC)


class EventType(StrEnum):
    """Sprint 0 learning events kept as the recomputation source."""

    SESSION_CREATED = "session_created"
    QUESTION_GENERATED = "question_generated"
    ANSWER_SUBMITTED = "answer_submitted"
    PROVIDER_OBSERVATION_RECORDED = "provider_observation_recorded"
    PROVIDER_FAILED = "provider_failed"
    MASTERY_DECISION_RECORDED = "mastery_decision_recorded"
    LEARNING_ACTION_SELECTED = "learning_action_selected"
    FEEDBACK_SUBMITTED = "feedback_submitted"
    WRONG_ITEM_CREATED = "wrong_item_created"
    WRONG_ITEM_STATUS_UPDATED = "wrong_item_status_updated"
    REVIEW_ITEM_CREATED = "review_item_created"
    RETEST_SUBMITTED = "retest_submitted"
    REVIEW_SCHEDULED = "review_scheduled"


class LearningEvent(BaseModel):
    """An append-only fact from which derived learning state can be rebuilt."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    event_type: EventType
    payload: dict[str, Any]
    session_id: str | None = None
    concept_id: str | None = None
    request_id: str | None = None
    protocol_version: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ConceptState(BaseModel):
    """A disposable projection derived from immutable learning events."""

    model_config = ConfigDict(frozen=True)

    user_id: str = Field(min_length=1)
    concept_id: str = Field(min_length=1)
    mastery_level: str = Field(pattern="^(no_clue|not_evident|fragile|developing|solid)$")
    understanding_level: str = Field(pattern="^(novice|developing|proficient)$")
    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    evidence_count: int = Field(ge=0)
    evidence_ids: list[str]
    latest_event_id: str | None = None
    protocol_version: str = Field(min_length=1)
    trend: ConceptTrend = ConceptTrend.INSUFFICIENT_DATA
    score_delta: int = 0
    wrong_item_count: int = Field(default=0, ge=0)
    open_wrong_item_count: int = Field(default=0, ge=0)
    feedback_count: int = Field(default=0, ge=0)
    feedback_inaccurate_count: int = Field(default=0, ge=0)
    review_attempt_count: int = Field(default=0, ge=0)
    review_success_count: int = Field(default=0, ge=0)
    repeated_misconceptions: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("mastery_level", mode="before")
    @classmethod
    def accept_legacy_mastery_level(cls, value: object) -> object:
        return normalize_mastery_level(value)
