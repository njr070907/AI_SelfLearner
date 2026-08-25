"""Validated view models returned to Streamlit and tests."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ai_growth_companion.domain.wrong_items import WrongItemStatus, WrongItemType
from ai_growth_companion.schemas.diagnosis import (
    DiagnosisEnvelope,
    LearningAction,
    MasteryDecision,
    ProviderObservation,
)


class ViewModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class SessionView(ViewModel):
    session_id: str
    concept_id: str
    concept: str
    status: str
    question_id: str
    question_text: str
    coverage_points: tuple[str, ...]
    started_at: datetime
    answer_count: int = 0
    can_submit_follow_up: bool = False


class DiagnosisView(ViewModel):
    session_id: str
    explanation_id: str
    answer_type: Literal["main", "follow_up"]
    sequence_no: int
    concept: str
    question_text: str
    answer_text: str
    status: Literal["succeeded", "failed", "invalid"]
    answer_saved: Literal[True] = True
    retryable: bool
    error_code: str | None = None
    observation: ProviderObservation | None = None
    decision: MasteryDecision | None = None
    next_action: LearningAction | None = None

    @property
    def envelope(self) -> DiagnosisEnvelope | None:
        if self.observation is None or self.decision is None or self.next_action is None:
            return None
        return DiagnosisEnvelope(
            observation=self.observation,
            decision=self.decision,
            next_action=self.next_action,
        )


class HistoryItem(ViewModel):
    session_id: str
    concept: str
    status: str
    mastery_level: str | None
    confidence: float | None
    started_at: datetime


class WrongItemView(ViewModel):
    """A traceable wrong/weak answer ready for review UI consumption."""

    wrong_item_id: str
    concept_id: str
    concept: str
    session_id: str
    explanation_id: str
    question_text: str
    answer_text: str
    error_type: WrongItemType
    error_summary: str
    evidence: ProviderObservation
    correction_text: str
    status: WrongItemStatus
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
