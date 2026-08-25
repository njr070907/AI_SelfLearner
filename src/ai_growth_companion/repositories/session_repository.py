"""SQLite repository for the complete deterministic Sprint 0 learning loop."""

import json
import sqlite3
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from ai_growth_companion.application.models import HistoryItem
from ai_growth_companion.domain.events import LOCAL_USER_ID, ConceptState, EventType, utc_now
from ai_growth_companion.domain.feedback import ConceptTrend
from ai_growth_companion.domain.session import InvalidSessionState, SessionStatus
from ai_growth_companion.providers.base import ProviderMetadata
from ai_growth_companion.repositories.database import Database, utc_text
from ai_growth_companion.schemas.diagnosis import (
    LearningAction,
    MasteryDecision,
    ProviderObservation,
    QuestionDraft,
)


@dataclass(frozen=True)
class SessionRecord:
    id: str
    concept_id: str
    concept: str
    status: str
    started_at: str


@dataclass(frozen=True)
class QuestionRecord:
    id: str
    session_id: str
    question_text: str
    coverage_points: tuple[str, ...]


@dataclass(frozen=True)
class ExplanationRecord:
    id: str
    session_id: str
    question_id: str
    answer_text: str
    request_id: str
    answer_type: Literal["main", "follow_up"]
    sequence_no: int


@dataclass(frozen=True)
class StoredOutcome:
    status: Literal["succeeded", "failed", "invalid"]
    error_code: str | None
    observation: ProviderObservation | None
    decision: MasteryDecision | None
    action: LearningAction | None
    diagnosis_id: str | None = None


def _event_payload(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _insert_event(
    connection: sqlite3.Connection,
    *,
    user_id: str,
    event_type: EventType,
    payload: dict[str, object],
    session_id: str | None = None,
    concept_id: str | None = None,
    request_id: str | None = None,
    protocol_version: str | None = None,
    event_id: str | None = None,
) -> str:
    persisted_id = event_id or str(uuid4())
    connection.execute(
        """
        INSERT INTO learning_events(
            id, user_id, session_id, concept_id, event_type, payload_json,
            request_id, protocol_version, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            persisted_id,
            user_id,
            session_id,
            concept_id,
            event_type.value,
            _event_payload(payload),
            request_id,
            protocol_version,
            utc_text(),
        ),
    )
    return persisted_id


class SQLiteSessionRepository:
    """Persist facts atomically while keeping external calls outside transactions."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def create_session(
        self,
        *,
        concept: str,
        learning_goal: str | None,
        learner_level: str | None,
        request_id: str,
    ) -> SessionRecord:
        """Create one idempotent local-user session and its first event."""
        with self.database.connect() as connection, connection:
            existing = connection.execute(
                """
                SELECT s.id, s.concept_id, c.display_name AS concept, s.status, s.started_at
                FROM learning_sessions s
                JOIN concepts c ON c.id = s.concept_id
                WHERE s.request_id = ?
                """,
                (request_id,),
            ).fetchone()
            if existing is not None:
                return SessionRecord(**dict(existing))

            normalized_name = concept.casefold()
            concept_id = str(uuid4())
            now = utc_text()
            connection.execute(
                """
                INSERT INTO concepts(id, normalized_name, display_name, domain, created_at)
                VALUES (?, ?, ?, '', ?)
                ON CONFLICT(normalized_name, domain) DO NOTHING
                """,
                (concept_id, normalized_name, concept, now),
            )
            concept_row = connection.execute(
                "SELECT id, display_name FROM concepts WHERE normalized_name = ? AND domain = ''",
                (normalized_name,),
            ).fetchone()
            concept_id = str(concept_row["id"])
            session_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO learning_sessions(
                    id, user_id, concept_id, status, learning_goal, learner_level,
                    request_id, started_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    LOCAL_USER_ID,
                    concept_id,
                    SessionStatus.CREATED.value,
                    learning_goal,
                    learner_level,
                    request_id,
                    now,
                ),
            )
            _insert_event(
                connection,
                user_id=LOCAL_USER_ID,
                session_id=session_id,
                concept_id=concept_id,
                event_type=EventType.SESSION_CREATED,
                payload={"concept": concept},
                request_id=request_id,
            )
            return SessionRecord(
                id=session_id,
                concept_id=concept_id,
                concept=str(concept_row["display_name"]),
                status=SessionStatus.CREATED.value,
                started_at=now,
            )

    def save_question(
        self,
        *,
        session: SessionRecord,
        draft: QuestionDraft,
        metadata: ProviderMetadata,
    ) -> QuestionRecord:
        """Persist one validated question and advance the session."""
        with self.database.connect() as connection, connection:
            existing = connection.execute(
                "SELECT id, session_id, question_text, coverage_points_json "
                "FROM feynman_questions WHERE session_id = ?",
                (session.id,),
            ).fetchone()
            if existing is not None:
                return QuestionRecord(
                    id=existing["id"],
                    session_id=existing["session_id"],
                    question_text=existing["question_text"],
                    coverage_points=tuple(json.loads(existing["coverage_points_json"])),
                )

            current = connection.execute(
                "SELECT status FROM learning_sessions WHERE id = ?", (session.id,)
            ).fetchone()
            if current is None or current["status"] not in {
                SessionStatus.CREATED.value,
                SessionStatus.QUESTION_FAILED.value,
            }:
                raise InvalidSessionState("当前会话不能生成问题")

            question_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO feynman_questions(
                    id, session_id, question_text, coverage_points_json, difficulty,
                    question_type, prompt_version, provider, model_name,
                    model_revision, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    question_id,
                    session.id,
                    draft.question_text,
                    json.dumps(draft.coverage_points, ensure_ascii=False),
                    draft.difficulty,
                    draft.question_type,
                    metadata.prompt_version,
                    metadata.provider,
                    metadata.model,
                    metadata.model_revision,
                    utc_text(),
                ),
            )
            connection.execute(
                "UPDATE learning_sessions SET status = ?, error_code = NULL WHERE id = ?",
                (SessionStatus.QUESTIONED.value, session.id),
            )
            _insert_event(
                connection,
                user_id=LOCAL_USER_ID,
                session_id=session.id,
                concept_id=session.concept_id,
                event_type=EventType.QUESTION_GENERATED,
                payload={"question_id": question_id, "schema_version": draft.schema_version},
                request_id=metadata.request_id,
            )
            return QuestionRecord(
                id=question_id,
                session_id=session.id,
                question_text=draft.question_text,
                coverage_points=tuple(draft.coverage_points),
            )

    def get_session_with_question(self, session_id: str) -> tuple[SessionRecord, QuestionRecord]:
        """Load the current session and its single Sprint 0 question."""
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT s.id, s.concept_id, c.display_name AS concept, s.status, s.started_at,
                       q.id AS question_id, q.question_text, q.coverage_points_json
                FROM learning_sessions s
                JOIN concepts c ON c.id = s.concept_id
                JOIN feynman_questions q ON q.session_id = s.id
                WHERE s.id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            raise LookupError("学习会话不存在或尚未生成问题")
        return (
            SessionRecord(
                id=row["id"],
                concept_id=row["concept_id"],
                concept=row["concept"],
                status=row["status"],
                started_at=row["started_at"],
            ),
            QuestionRecord(
                id=row["question_id"],
                session_id=row["id"],
                question_text=row["question_text"],
                coverage_points=tuple(json.loads(row["coverage_points_json"])),
            ),
        )

    def save_answer(
        self,
        *,
        session: SessionRecord,
        question: QuestionRecord,
        answer_text: str,
        request_id: str,
        answer_type: Literal["main", "follow_up"] = "main",
    ) -> tuple[ExplanationRecord, bool]:
        """Persist one answer before any provider call and make it idempotent."""
        with self.database.connect() as connection, connection:
            existing = connection.execute(
                """
                SELECT id, session_id, question_id, answer_text, request_id,
                       answer_type, sequence_no
                FROM user_explanations WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
            if existing is not None:
                if (
                    existing["session_id"] != session.id
                    or existing["question_id"] != question.id
                    or existing["answer_text"] != answer_text
                    or existing["answer_type"] != answer_type
                ):
                    raise InvalidSessionState("同一个幂等键不能用于不同的回答提交")
                return ExplanationRecord(**dict(existing)), False

            current = connection.execute(
                "SELECT status FROM learning_sessions WHERE id = ?", (session.id,)
            ).fetchone()
            allowed_statuses = (
                {SessionStatus.QUESTIONED.value}
                if answer_type == "main"
                else {SessionStatus.DIAGNOSED.value}
            )
            if current is None or current["status"] not in allowed_statuses:
                if answer_type == "follow_up":
                    raise InvalidSessionState("只有完成一次成功诊断后才能提交追问回答")
                raise InvalidSessionState("当前会话不能提交新回答")

            next_sequence = connection.execute(
                "SELECT COALESCE(MAX(sequence_no), 0) + 1 AS sequence_no "
                "FROM user_explanations WHERE session_id = ?",
                (session.id,),
            ).fetchone()["sequence_no"]
            if answer_type == "main" and next_sequence != 1:
                raise InvalidSessionState("当前会话已经有主回答")

            explanation_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO user_explanations(
                    id, session_id, question_id, answer_text, answer_type,
                    sequence_no, request_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    explanation_id,
                    session.id,
                    question.id,
                    answer_text,
                    answer_type,
                    next_sequence,
                    request_id,
                    utc_text(),
                ),
            )
            connection.execute(
                "UPDATE learning_sessions SET status = ?, error_code = NULL WHERE id = ?",
                (SessionStatus.ANSWERED.value, session.id),
            )
            _insert_event(
                connection,
                user_id=LOCAL_USER_ID,
                session_id=session.id,
                concept_id=session.concept_id,
                event_type=EventType.ANSWER_SUBMITTED,
                payload={
                    "explanation_id": explanation_id,
                    "answer_length": len(answer_text),
                    "answer_type": answer_type,
                    "sequence_no": next_sequence,
                },
                request_id=request_id,
            )
            return (
                ExplanationRecord(
                    id=explanation_id,
                    session_id=session.id,
                    question_id=question.id,
                    answer_text=answer_text,
                    request_id=request_id,
                    answer_type=answer_type,
                    sequence_no=next_sequence,
                ),
                True,
            )

    def get_explanation(self, explanation_id: str) -> ExplanationRecord:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT id, session_id, question_id, answer_text, request_id,
                       answer_type, sequence_no
                FROM user_explanations WHERE id = ?
                """,
                (explanation_id,),
            ).fetchone()
        if row is None:
            raise LookupError("学习回答不存在")
        return ExplanationRecord(**dict(row))

    def get_main_explanation(self, session_id: str) -> ExplanationRecord | None:
        """Load the main submitted answer so history can be reopened after a restart."""
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT id, session_id, question_id, answer_text, request_id,
                       answer_type, sequence_no
                FROM user_explanations
                WHERE session_id = ? AND answer_type = 'main'
                ORDER BY sequence_no
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        return None if row is None else ExplanationRecord(**dict(row))

    def get_latest_explanation(self, session_id: str) -> ExplanationRecord | None:
        """Load the latest answer in a teaching session, including a follow-up."""
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT id, session_id, question_id, answer_text, request_id,
                       answer_type, sequence_no
                FROM user_explanations
                WHERE session_id = ?
                ORDER BY sequence_no DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        return None if row is None else ExplanationRecord(**dict(row))

    def answer_count(self, session_id: str) -> int:
        """Return the number of submitted answers in a teaching session."""
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS answer_count FROM user_explanations WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return int(row["answer_count"])

    def next_attempt_no(self, explanation_id: str) -> int:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(attempt_no), 0) + 1 AS attempt_no "
                "FROM provider_observations WHERE explanation_id = ?",
                (explanation_id,),
            ).fetchone()
        return int(row["attempt_no"])

    def record_failure(
        self,
        *,
        session: SessionRecord,
        explanation: ExplanationRecord,
        attempt_no: int,
        request_id: str,
        provider: str,
        model: str,
        model_revision: str | None,
        status: str,
        error_code: str,
    ) -> None:
        """Record failure metadata while deliberately retaining the answer."""
        with self.database.connect() as connection, connection:
            observation_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO provider_observations(
                    id, explanation_id, status, attempt_no, provider, model_name,
                    model_revision, prompt_version, schema_version, request_id,
                    error_code, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    explanation.id,
                    status,
                    attempt_no,
                    provider,
                    model,
                    model_revision,
                    "fake-evaluator-v0.1",
                    "provider-observation-v0.1",
                    request_id,
                    error_code,
                    utc_text(),
                ),
            )
            connection.execute(
                "UPDATE learning_sessions SET status = ?, error_code = ? WHERE id = ?",
                (SessionStatus.DIAGNOSIS_FAILED.value, error_code, session.id),
            )
            _insert_event(
                connection,
                user_id=LOCAL_USER_ID,
                session_id=session.id,
                concept_id=session.concept_id,
                event_type=EventType.PROVIDER_FAILED,
                payload={
                    "observation_id": observation_id,
                    "status": status,
                    "error_code": error_code,
                    "attempt_no": attempt_no,
                },
                request_id=request_id,
            )

    def record_success(
        self,
        *,
        session: SessionRecord,
        explanation: ExplanationRecord,
        attempt_no: int,
        observation_id: str,
        decision_id: str,
        action_id: str,
        observation: ProviderObservation,
        decision: MasteryDecision,
        action: LearningAction,
        metadata: ProviderMetadata,
    ) -> str:
        """Atomically save validated observation, decision, action, events, and projection."""
        with self.database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO provider_observations(
                    id, explanation_id, status, attempt_no, result_json, provider,
                    model_name, model_revision, prompt_version, schema_version,
                    request_id, latency_ms, usage_json, finish_reason, created_at
                ) VALUES (?, ?, 'succeeded', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    explanation.id,
                    attempt_no,
                    observation.model_dump_json(),
                    metadata.provider,
                    metadata.model,
                    metadata.model_revision,
                    metadata.prompt_version,
                    metadata.schema_version,
                    metadata.request_id,
                    metadata.latency_ms,
                    json.dumps(metadata.usage, sort_keys=True),
                    metadata.finish_reason,
                    utc_text(),
                ),
            )
            connection.execute(
                """
                INSERT INTO mastery_decisions(
                    id, observation_id, mastery_level, understanding_level, score,
                    confidence, evidence_ids_json, reason, protocol_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    observation_id,
                    decision.mastery_level.value,
                    decision.understanding_level.value,
                    decision.score,
                    decision.confidence,
                    json.dumps(decision.evidence_ids),
                    decision.reason,
                    decision.protocol_version,
                    utc_text(),
                ),
            )
            connection.execute(
                """
                INSERT INTO learning_actions(
                    id, decision_id, action_type, instruction, reason,
                    evidence_ids_json, policy_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action_id,
                    decision_id,
                    action.action_type.value,
                    action.instruction,
                    action.reason,
                    json.dumps(action.evidence_ids),
                    action.policy_version,
                    utc_text(),
                ),
            )
            _insert_event(
                connection,
                user_id=LOCAL_USER_ID,
                session_id=session.id,
                concept_id=session.concept_id,
                event_type=EventType.PROVIDER_OBSERVATION_RECORDED,
                payload={
                    "observation_id": observation_id,
                    "schema_version": observation.schema_version,
                },
                request_id=metadata.request_id,
            )
            decision_event_id = _insert_event(
                connection,
                user_id=LOCAL_USER_ID,
                session_id=session.id,
                concept_id=session.concept_id,
                event_type=EventType.MASTERY_DECISION_RECORDED,
                payload={"decision_id": decision_id, "score": decision.score},
                request_id=metadata.request_id,
                protocol_version=decision.protocol_version,
            )
            _insert_event(
                connection,
                user_id=LOCAL_USER_ID,
                session_id=session.id,
                concept_id=session.concept_id,
                event_type=EventType.LEARNING_ACTION_SELECTED,
                payload={"action_id": action_id, "action_type": action.action_type.value},
                request_id=metadata.request_id,
                protocol_version=action.policy_version,
            )
            connection.execute(
                "UPDATE learning_sessions SET status = ?, completed_at = ?, error_code = NULL "
                "WHERE id = ?",
                (SessionStatus.DIAGNOSED.value, utc_text(), session.id),
            )
            self._rebuild_state_in_transaction(
                connection,
                user_id=LOCAL_USER_ID,
                concept_id=session.concept_id,
                latest_event_id=decision_event_id,
            )
            return decision_event_id

    def _rebuild_state_in_transaction(
        self,
        connection: sqlite3.Connection,
        *,
        user_id: str,
        concept_id: str,
        latest_event_id: str | None = None,
    ) -> ConceptState | None:
        rows = connection.execute(
            """
            SELECT d.id, d.mastery_level, d.understanding_level, d.score,
                   d.confidence, d.protocol_version, d.created_at
            FROM mastery_decisions d
            JOIN provider_observations o ON o.id = d.observation_id
            JOIN user_explanations e ON e.id = o.explanation_id
            JOIN learning_sessions s ON s.id = e.session_id
            WHERE s.user_id = ? AND s.concept_id = ?
            ORDER BY d.created_at, d.rowid
            """,
            (user_id, concept_id),
        ).fetchall()
        if not rows:
            connection.execute(
                "DELETE FROM concept_states WHERE user_id = ? AND concept_id = ?",
                (user_id, concept_id),
            )
            return None

        latest = rows[-1]
        evidence_ids = [str(row["id"]) for row in rows]
        scores = [int(row["score"]) for row in rows]
        score_delta = scores[-1] - scores[-2] if len(scores) > 1 else 0
        if len(scores) < 2:
            trend = ConceptTrend.INSUFFICIENT_DATA
        elif score_delta >= 10:
            trend = ConceptTrend.IMPROVING
        elif score_delta <= -10:
            trend = ConceptTrend.DECLINING
        else:
            trend = ConceptTrend.STABLE
        feedback_stats = connection.execute(
            """
            SELECT COUNT(*) AS feedback_count,
                   SUM(CASE WHEN f.verdict = 'inaccurate' THEN 1 ELSE 0 END)
                       AS feedback_inaccurate_count
            FROM diagnosis_feedback f
            JOIN mastery_decisions d ON d.id = f.decision_id
            JOIN provider_observations o ON o.id = d.observation_id
            JOIN user_explanations e ON e.id = o.explanation_id
            JOIN learning_sessions s ON s.id = e.session_id
            WHERE s.user_id = ? AND s.concept_id = ?
            """,
            (user_id, concept_id),
        ).fetchone()
        wrong_stats = connection.execute(
            """
            SELECT COUNT(*) AS wrong_item_count,
                   SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END)
                       AS open_wrong_item_count
            FROM wrong_items
            WHERE user_id = ? AND concept_id = ?
            """,
            (user_id, concept_id),
        ).fetchone()
        review_stats = connection.execute(
            """
            SELECT COUNT(*) AS review_attempt_count,
                   SUM(CASE WHEN a.status = 'succeeded' AND a.result = 'correct'
                            THEN 1 ELSE 0 END) AS review_success_count
            FROM review_attempts a
            JOIN review_items r ON r.id = a.review_item_id
            WHERE r.user_id = ? AND r.concept_id = ?
            """,
            (user_id, concept_id),
        ).fetchone()
        repeated_rows = connection.execute(
            """
            SELECT error_summary, COUNT(*) AS occurrences
            FROM wrong_items
            WHERE user_id = ? AND concept_id = ? AND error_type = 'misconception'
            GROUP BY error_summary
            HAVING COUNT(*) >= 2
            ORDER BY occurrences DESC, error_summary
            LIMIT 5
            """,
            (user_id, concept_id),
        ).fetchall()
        if latest_event_id is None:
            event_row = connection.execute(
                """
                SELECT id FROM learning_events
                WHERE user_id = ? AND concept_id = ? AND event_type = ?
                ORDER BY created_at DESC, rowid DESC
                LIMIT 1
                """,
                (user_id, concept_id, EventType.MASTERY_DECISION_RECORDED.value),
            ).fetchone()
            latest_event_id = None if event_row is None else str(event_row["id"])
        state = ConceptState(
            user_id=user_id,
            concept_id=concept_id,
            mastery_level=latest["mastery_level"],
            understanding_level=latest["understanding_level"],
            score=latest["score"],
            confidence=latest["confidence"],
            evidence_count=len(rows),
            evidence_ids=evidence_ids,
            latest_event_id=latest_event_id,
            protocol_version=latest["protocol_version"],
            trend=trend,
            score_delta=score_delta,
            wrong_item_count=int(wrong_stats["wrong_item_count"] or 0),
            open_wrong_item_count=int(wrong_stats["open_wrong_item_count"] or 0),
            feedback_count=int(feedback_stats["feedback_count"] or 0),
            feedback_inaccurate_count=int(feedback_stats["feedback_inaccurate_count"] or 0),
            review_attempt_count=int(review_stats["review_attempt_count"] or 0),
            review_success_count=int(review_stats["review_success_count"] or 0),
            repeated_misconceptions=[str(row["error_summary"]) for row in repeated_rows],
            updated_at=utc_now(),
        )
        connection.execute(
            """
            INSERT INTO concept_states(
                user_id, concept_id, mastery_level, understanding_level, score,
                confidence, evidence_count, latest_event_id, state_json,
                protocol_version, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, concept_id) DO UPDATE SET
                mastery_level = excluded.mastery_level,
                understanding_level = excluded.understanding_level,
                score = excluded.score,
                confidence = excluded.confidence,
                evidence_count = excluded.evidence_count,
                latest_event_id = excluded.latest_event_id,
                state_json = excluded.state_json,
                protocol_version = excluded.protocol_version,
                updated_at = excluded.updated_at
            """,
            (
                state.user_id,
                state.concept_id,
                state.mastery_level,
                state.understanding_level,
                state.score,
                state.confidence,
                state.evidence_count,
                state.latest_event_id,
                state.model_dump_json(),
                state.protocol_version,
                state.updated_at.isoformat().replace("+00:00", "Z"),
            ),
        )
        return state

    def rebuild_current_state(self, *, user_id: str, concept_id: str) -> ConceptState | None:
        """Recreate a disposable projection solely from persisted decisions."""
        with self.database.connect() as connection, connection:
            return self._rebuild_state_in_transaction(
                connection,
                user_id=user_id,
                concept_id=concept_id,
            )

    def load_outcome(self, explanation_id: str) -> StoredOutcome | None:
        """Load the newest attempt without exposing provider raw content."""
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT o.status, o.error_code, o.result_json,
                       d.id AS diagnosis_id, d.mastery_level, d.understanding_level, d.score,
                       d.confidence, d.evidence_ids_json, d.reason,
                       d.protocol_version, a.action_type, a.instruction,
                       a.reason AS action_reason, a.evidence_ids_json AS action_evidence_ids,
                       a.policy_version
                FROM provider_observations o
                LEFT JOIN mastery_decisions d ON d.observation_id = o.id
                LEFT JOIN learning_actions a ON a.decision_id = d.id
                WHERE o.explanation_id = ?
                ORDER BY o.attempt_no DESC
                LIMIT 1
                """,
                (explanation_id,),
            ).fetchone()
        if row is None:
            return None
        if row["status"] != "succeeded":
            return StoredOutcome(
                status=row["status"],
                error_code=row["error_code"],
                observation=None,
                decision=None,
                action=None,
                diagnosis_id=row["diagnosis_id"],
            )
        return StoredOutcome(
            status="succeeded",
            error_code=None,
            observation=ProviderObservation.model_validate_json(row["result_json"]),
            decision=MasteryDecision(
                mastery_level=row["mastery_level"],
                understanding_level=row["understanding_level"],
                score=row["score"],
                confidence=row["confidence"],
                evidence_ids=json.loads(row["evidence_ids_json"]),
                reason=row["reason"],
                protocol_version=row["protocol_version"],
            ),
            action=LearningAction(
                action_type=row["action_type"],
                instruction=row["instruction"],
                reason=row["action_reason"],
                evidence_ids=json.loads(row["action_evidence_ids"]),
                policy_version=row["policy_version"],
            ),
            diagnosis_id=row["diagnosis_id"],
        )

    def list_current_states(
        self,
        *,
        user_id: str = LOCAL_USER_ID,
        limit: int = 100,
    ) -> tuple[ConceptState, ...]:
        """Return derived states for concepts that have at least one diagnosis."""
        bounded_limit = max(1, min(limit, 100))
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT state_json FROM concept_states
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (user_id, bounded_limit),
            ).fetchall()
        return tuple(ConceptState.model_validate_json(row["state_json"]) for row in rows)

    def list_history(self, *, limit: int = 20) -> tuple[HistoryItem, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT s.id AS session_id, c.display_name AS concept, s.status,
                       d.mastery_level, d.confidence, s.started_at
                FROM learning_sessions s
                JOIN concepts c ON c.id = s.concept_id
                LEFT JOIN user_explanations e ON e.session_id = s.id AND e.sequence_no = 1
                LEFT JOIN provider_observations o ON o.id = (
                    SELECT o2.id FROM provider_observations o2
                    WHERE o2.explanation_id = e.id
                    ORDER BY o2.attempt_no DESC LIMIT 1
                )
                LEFT JOIN mastery_decisions d ON d.observation_id = o.id
                ORDER BY s.started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return tuple(
            HistoryItem(
                session_id=row["session_id"],
                concept=row["concept"],
                status=row["status"],
                mastery_level=row["mastery_level"],
                confidence=row["confidence"],
                started_at=row["started_at"],
            )
            for row in rows
        )
