"""Validated view models returned to Streamlit and tests."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ai_growth_companion.domain.events import ConceptState
from ai_growth_companion.domain.feedback import FeedbackVerdict
from ai_growth_companion.domain.review import ReviewAttemptStatus, ReviewItemStatus, ReviewOutcome
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
    diagnosis_id: str | None = None
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


class ReviewQueueItemView(ViewModel):
    """A due review item that a page can render without storage access."""

    review_item_id: str
    wrong_item_id: str
    concept_id: str
    concept: str
    question_text: str
    due_at: datetime
    interval_days: int
    attempt_count: int
    last_result: ReviewOutcome | None
    status: ReviewItemStatus
    is_due: bool


class ReviewResultView(ViewModel):
    """The retest result plus the next deterministic scheduling decision."""

    review_item: ReviewQueueItemView
    attempt_id: str
    status: ReviewAttemptStatus
    result: ReviewOutcome | None
    retryable: bool
    error_code: str | None = None
    observation: ProviderObservation | None = None
    decision: MasteryDecision | None = None
    next_action: LearningAction | None = None


class FeedbackView(ViewModel):
    """A learner correction that can be shown without exposing storage rows."""

    feedback_id: str
    diagnosis_id: str
    concept_id: str
    concept: str
    verdict: FeedbackVerdict
    note: str | None
    created_at: datetime


class DocumentView(ViewModel):
    """Safe document metadata exposed to the UI without a filesystem path."""

    document_id: str
    filename: str
    extension: str
    mime_type: str
    size_bytes: int
    sha256: str
    status: str
    created_at: datetime
    updated_at: datetime


class WorkspaceSnapshot(ViewModel):
    """One read model for the home, progress, wrong-item, and review pages."""

    history: tuple[HistoryItem, ...]
    concept_states: tuple[ConceptState, ...]
    wrong_items: tuple[WrongItemView, ...]
    review_queue: tuple[ReviewQueueItemView, ...]
