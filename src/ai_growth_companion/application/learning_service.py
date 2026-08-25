"""End-to-end deterministic Sprint 0 learning use cases."""

from collections.abc import Callable
from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import ValidationError

from ai_growth_companion.application.models import DiagnosisView, HistoryItem, SessionView
from ai_growth_companion.domain.mastery import DemoLearningPolicy, DemoMasteryEngine
from ai_growth_companion.domain.session import (
    InvalidSessionState,
    normalize_concept,
    validate_answer,
)
from ai_growth_companion.providers.base import (
    EvaluationRequest,
    LLMProvider,
    ProviderError,
    QuestionRequest,
)
from ai_growth_companion.providers.fake import FakeLLMProvider, FakeScenario
from ai_growth_companion.repositories.session_repository import (
    ExplanationRecord,
    QuestionRecord,
    SessionRecord,
    SQLiteSessionRepository,
    StoredOutcome,
)
from ai_growth_companion.schemas.diagnosis import (
    ProviderObservation,
    QuestionDraft,
    validate_answer_excerpts,
)

ProviderFactory = Callable[[FakeScenario], LLMProvider]


def default_fake_provider_factory(scenario: FakeScenario) -> LLMProvider:
    return FakeLLMProvider(scenario)


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class LearningService:
    """Orchestrate persistence, provider observation, mastery decision, and policy."""

    def __init__(
        self,
        repository: SQLiteSessionRepository,
        *,
        provider_factory: ProviderFactory = default_fake_provider_factory,
        mastery_engine: DemoMasteryEngine | None = None,
        learning_policy: DemoLearningPolicy | None = None,
    ) -> None:
        self.repository = repository
        self.provider_factory = provider_factory
        self.mastery_engine = mastery_engine or DemoMasteryEngine()
        self.learning_policy = learning_policy or DemoLearningPolicy()

    def start_session(
        self,
        *,
        concept: str,
        request_id: str,
        learning_goal: str | None = None,
        learner_level: str | None = None,
    ) -> SessionView:
        """Create a session and persist one validated Fake question."""
        normalized = normalize_concept(concept)
        session = self.repository.create_session(
            concept=normalized,
            learning_goal=learning_goal,
            learner_level=learner_level,
            request_id=request_id,
        )
        try:
            session, question = self.repository.get_session_with_question(session.id)
        except LookupError:
            provider = self.provider_factory(FakeScenario.PARTIAL)
            response = provider.generate_question(
                QuestionRequest(
                    concept=normalized,
                    learning_goal=learning_goal,
                    learner_level=learner_level,
                ),
                request_id=request_id,
            )
            draft = QuestionDraft.model_validate(response.content)
            question = self.repository.save_question(
                session=session,
                draft=draft,
                metadata=response.metadata,
            )
            session, _ = self.repository.get_session_with_question(session.id)

        return self._session_view(session, question)

    def get_session(self, session_id: str) -> SessionView:
        session, question = self.repository.get_session_with_question(session_id)
        return self._session_view(session, question)

    def submit_answer(
        self,
        *,
        session_id: str,
        answer_text: str,
        scenario: FakeScenario,
        request_id: str,
    ) -> DiagnosisView:
        """Save the main explanation first, then evaluate it outside a transaction."""
        return self._submit_explanation(
            session_id=session_id,
            answer_text=answer_text,
            answer_type="main",
            scenario=scenario,
            request_id=request_id,
        )

    def submit_follow_up(
        self,
        *,
        session_id: str,
        answer_text: str,
        scenario: FakeScenario,
        request_id: str,
    ) -> DiagnosisView:
        """Submit a same-session answer to the selected next action."""
        return self._submit_explanation(
            session_id=session_id,
            answer_text=answer_text,
            answer_type="follow_up",
            scenario=scenario,
            request_id=request_id,
        )

    def _submit_explanation(
        self,
        *,
        session_id: str,
        answer_text: str,
        answer_type: Literal["main", "follow_up"],
        scenario: FakeScenario,
        request_id: str,
    ) -> DiagnosisView:
        """Persist one teaching turn before evaluating it with the provider."""
        answer = validate_answer(answer_text)
        session, question = self.repository.get_session_with_question(session_id)
        explanation, created = self.repository.save_answer(
            session=session,
            question=question,
            answer_text=answer,
            answer_type=answer_type,
            request_id=request_id,
        )
        if not created:
            existing = self.repository.load_outcome(explanation.id)
            if existing is not None:
                return self._view(session.concept, question.question_text, explanation, existing)

        return self._evaluate_saved_answer(
            session_id=session_id,
            explanation=explanation,
            scenario=scenario,
            request_id=request_id,
        )

    def retry(
        self,
        *,
        explanation_id: str,
        scenario: FakeScenario,
        request_id: str,
    ) -> DiagnosisView:
        """Retry the same saved answer as a new provider attempt."""
        explanation = self.repository.get_explanation(explanation_id)
        current = self.repository.load_outcome(explanation.id)
        if current is None or current.status not in {"failed", "invalid"}:
            raise InvalidSessionState("只有失败或格式无效的诊断可以重试")
        return self._evaluate_saved_answer(
            session_id=explanation.session_id,
            explanation=explanation,
            scenario=scenario,
            request_id=request_id,
        )

    def _evaluate_saved_answer(
        self,
        *,
        session_id: str,
        explanation: ExplanationRecord,
        scenario: FakeScenario,
        request_id: str,
    ) -> DiagnosisView:
        session, question = self.repository.get_session_with_question(session_id)
        attempt_no = self.repository.next_attempt_no(explanation.id)
        provider = self.provider_factory(scenario)
        try:
            response = provider.evaluate(
                EvaluationRequest(
                    concept=session.concept,
                    question_text=question.question_text,
                    coverage_points=question.coverage_points,
                    answer_text=explanation.answer_text,
                ),
                request_id=request_id,
            )
        except ProviderError as error:
            self.repository.record_failure(
                session=session,
                explanation=explanation,
                attempt_no=attempt_no,
                request_id=request_id,
                provider=provider.provider_name,
                model=provider.model_name,
                model_revision=provider.model_revision,
                status="failed",
                error_code=error.code,
            )
            return self._view(
                session.concept,
                question.question_text,
                explanation,
                StoredOutcome(
                    status="failed",
                    error_code=error.code,
                    observation=None,
                    decision=None,
                    action=None,
                ),
            )

        try:
            observation = ProviderObservation.model_validate(response.content)
            validate_answer_excerpts(observation, explanation.answer_text)
        except (ValidationError, ValueError):
            self.repository.record_failure(
                session=session,
                explanation=explanation,
                attempt_no=attempt_no,
                request_id=request_id,
                provider=response.metadata.provider,
                model=response.metadata.model,
                model_revision=response.metadata.model_revision,
                status="invalid",
                error_code="LLM_OUTPUT_INVALID",
            )
            return self._view(
                session.concept,
                question.question_text,
                explanation,
                StoredOutcome(
                    status="invalid",
                    error_code="LLM_OUTPUT_INVALID",
                    observation=None,
                    decision=None,
                    action=None,
                ),
            )

        observation_id = str(uuid4())
        decision = self.mastery_engine.decide(observation, observation_id=observation_id)
        action = self.learning_policy.choose(observation, decision)
        self.repository.record_success(
            session=session,
            explanation=explanation,
            attempt_no=attempt_no,
            observation_id=observation_id,
            decision_id=str(uuid4()),
            action_id=str(uuid4()),
            observation=observation,
            decision=decision,
            action=action,
            metadata=response.metadata,
        )
        return DiagnosisView(
            session_id=session.id,
            explanation_id=explanation.id,
            answer_type=explanation.answer_type,
            sequence_no=explanation.sequence_no,
            concept=session.concept,
            question_text=question.question_text,
            answer_text=explanation.answer_text,
            status="succeeded",
            retryable=False,
            observation=observation,
            decision=decision,
            next_action=action,
        )

    def get_session_diagnosis(self, session_id: str) -> DiagnosisView | None:
        session, question = self.repository.get_session_with_question(session_id)
        explanation = self.repository.get_latest_explanation(session_id)
        if explanation is None:
            return None
        outcome = self.repository.load_outcome(explanation.id)
        if outcome is None:
            return None
        return self._view(session.concept, question.question_text, explanation, outcome)

    def list_history(self) -> tuple[HistoryItem, ...]:
        return self.repository.list_history()

    def _session_view(self, session: SessionRecord, question: QuestionRecord) -> SessionView:
        """Build the stable page contract without leaking repository records."""
        return SessionView(
            session_id=session.id,
            concept_id=session.concept_id,
            concept=session.concept,
            status=session.status,
            question_id=question.id,
            question_text=question.question_text,
            coverage_points=question.coverage_points,
            started_at=_parse_datetime(session.started_at),
            answer_count=self.repository.answer_count(session.id),
            can_submit_follow_up=session.status == "diagnosed",
        )

    @staticmethod
    def _view(
        concept: str,
        question_text: str,
        explanation: ExplanationRecord,
        outcome: StoredOutcome,
    ) -> DiagnosisView:
        return DiagnosisView(
            session_id=explanation.session_id,
            explanation_id=explanation.id,
            answer_type=explanation.answer_type,
            sequence_no=explanation.sequence_no,
            concept=concept,
            question_text=question_text,
            answer_text=explanation.answer_text,
            status=outcome.status,
            retryable=outcome.status in {"failed", "invalid"},
            error_code=outcome.error_code,
            observation=outcome.observation,
            decision=outcome.decision,
            next_action=outcome.action,
        )
