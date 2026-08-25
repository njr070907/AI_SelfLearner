"""SQLite persistence for learner feedback and explicit diagnosis corrections."""

import json
import sqlite3
from dataclasses import dataclass
from typing import cast
from uuid import uuid4

from ai_growth_companion.domain.events import LOCAL_USER_ID, EventType
from ai_growth_companion.domain.feedback import FeedbackVerdict
from ai_growth_companion.repositories.database import Database, utc_text


@dataclass(frozen=True)
class FeedbackRecord:
    """Persisted feedback with enough context for a progress view."""

    feedback_id: str
    diagnosis_id: str
    user_id: str
    concept_id: str
    concept: str
    session_id: str
    verdict: FeedbackVerdict
    note: str | None
    request_id: str
    created_at: str


def _payload(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class SQLiteFeedbackRepository:
    """Write feedback and its append-only event atomically."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def submit(
        self,
        *,
        diagnosis_id: str,
        verdict: FeedbackVerdict,
        note: str | None,
        request_id: str,
        user_id: str = LOCAL_USER_ID,
    ) -> FeedbackRecord:
        """Persist one feedback item, replaying an identical idempotent request."""
        with self.database.connect() as connection, connection:
            existing_event = connection.execute(
                """
                SELECT payload_json FROM learning_events
                WHERE request_id = ? AND event_type = ?
                LIMIT 1
                """,
                (request_id, EventType.FEEDBACK_SUBMITTED.value),
            ).fetchone()
            if existing_event is not None:
                payload = json.loads(existing_event["payload_json"])
                if (
                    payload.get("diagnosis_id") != diagnosis_id
                    or payload.get("verdict") != verdict.value
                    or payload.get("note") != note
                ):
                    raise ValueError("同一个幂等键不能用于不同的反馈")
                feedback_id = str(payload["feedback_id"])
                row = self._select_one(connection, feedback_id)
                assert row is not None
                return self._record_from_row(row)

            context = connection.execute(
                """
                SELECT d.id AS diagnosis_id, s.id AS session_id,
                       s.concept_id, c.display_name AS concept
                FROM mastery_decisions d
                JOIN provider_observations o ON o.id = d.observation_id
                JOIN user_explanations e ON e.id = o.explanation_id
                JOIN learning_sessions s ON s.id = e.session_id
                JOIN concepts c ON c.id = s.concept_id
                WHERE d.id = ? AND s.user_id = ?
                """,
                (diagnosis_id, user_id),
            ).fetchone()
            if context is None:
                raise LookupError("诊断不存在或不属于当前用户")

            feedback_id = str(uuid4())
            created_at = utc_text()
            connection.execute(
                """
                INSERT INTO diagnosis_feedback(
                    id, decision_id, user_id, verdict, note, created_at, request_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback_id,
                    diagnosis_id,
                    user_id,
                    verdict.value,
                    note,
                    created_at,
                    request_id,
                ),
            )
            self._insert_event(
                connection,
                user_id=user_id,
                session_id=context["session_id"],
                concept_id=context["concept_id"],
                request_id=request_id,
                payload={
                    "feedback_id": feedback_id,
                    "diagnosis_id": diagnosis_id,
                    "verdict": verdict.value,
                    "note": note,
                },
            )
            row = self._select_one(connection, feedback_id)
            assert row is not None
            return self._record_from_row(row)

    def get(self, feedback_id: str) -> FeedbackRecord:
        with self.database.connect() as connection:
            row = self._select_one(connection, feedback_id)
        if row is None:
            raise LookupError("反馈不存在")
        return self._record_from_row(row)

    @staticmethod
    def _select_one(
        connection: sqlite3.Connection,
        feedback_id: str,
    ) -> sqlite3.Row | None:
        return cast(
            sqlite3.Row | None,
            connection.execute(
                """
                SELECT f.id, f.decision_id, f.user_id, s.concept_id,
                       c.display_name AS concept, s.id AS session_id,
                       f.verdict, f.note, f.request_id, f.created_at
                FROM diagnosis_feedback f
                JOIN mastery_decisions d ON d.id = f.decision_id
                JOIN provider_observations o ON o.id = d.observation_id
                JOIN user_explanations e ON e.id = o.explanation_id
                JOIN learning_sessions s ON s.id = e.session_id
                JOIN concepts c ON c.id = s.concept_id
                WHERE f.id = ?
                """,
                (feedback_id,),
            ).fetchone(),
        )

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> FeedbackRecord:
        return FeedbackRecord(
            feedback_id=row["id"],
            diagnosis_id=row["decision_id"],
            user_id=row["user_id"],
            concept_id=row["concept_id"],
            concept=row["concept"],
            session_id=row["session_id"],
            verdict=FeedbackVerdict(row["verdict"]),
            note=row["note"],
            request_id=row["request_id"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _insert_event(
        connection: sqlite3.Connection,
        *,
        user_id: str,
        session_id: str,
        concept_id: str,
        request_id: str,
        payload: dict[str, object],
    ) -> None:
        connection.execute(
            """
            INSERT INTO learning_events(
                id, user_id, session_id, concept_id, event_type, payload_json,
                request_id, protocol_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                user_id,
                session_id,
                concept_id,
                EventType.FEEDBACK_SUBMITTED.value,
                _payload(payload),
                request_id,
                "feedback-v0.1",
                utc_text(),
            ),
        )
