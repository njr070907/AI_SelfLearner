"""SQLite persistence for traceable wrong and insufficient-evidence items."""

import json
import sqlite3
from dataclasses import dataclass
from typing import cast
from uuid import uuid4

from ai_growth_companion.domain.events import LOCAL_USER_ID, EventType
from ai_growth_companion.domain.wrong_items import WrongItemStatus, WrongItemType
from ai_growth_companion.repositories.database import Database, utc_text
from ai_growth_companion.schemas.diagnosis import (
    LearningAction,
    MasteryDecision,
    ProviderObservation,
)


@dataclass(frozen=True)
class WrongItemRecord:
    """Raw persisted wrong-item data; application models hide storage details."""

    wrong_item_id: str
    user_id: str
    concept_id: str
    concept: str
    session_id: str
    question_id: str
    explanation_id: str
    observation_id: str
    decision_id: str
    source_event_id: str
    question_text: str
    answer_text: str
    error_type: WrongItemType
    error_summary: str
    evidence_json: str
    correction_text: str
    status: WrongItemStatus
    created_at: str
    updated_at: str
    resolved_at: str | None


def _event_payload(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def classify_observation(observation: ProviderObservation) -> WrongItemType | None:
    """Return one review category, or None when the answer is currently solid."""
    if observation.possible_misconceptions:
        return WrongItemType.MISCONCEPTION
    if not observation.evidence:
        return WrongItemType.INSUFFICIENT_EVIDENCE
    if observation.gaps:
        return WrongItemType.GAP
    return None


def summarize_observation(observation: ProviderObservation, item_type: WrongItemType) -> str:
    """Create a short deterministic summary without asking the model for new prose."""
    if item_type is WrongItemType.MISCONCEPTION:
        return "；".join(item.description for item in observation.possible_misconceptions)
    if item_type is WrongItemType.GAP:
        return "；".join(item.description for item in observation.gaps)
    return "当前回答没有提供足够的可验证证据，暂时不能确认已经理解。"


class SQLiteWrongItemRepository:
    """Persist wrong items and their user-controlled lifecycle events."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def create_from_success(
        self,
        *,
        user_id: str,
        concept_id: str,
        concept: str,
        session_id: str,
        question_id: str,
        question_text: str,
        explanation_id: str,
        answer_text: str,
        observation_id: str,
        decision_id: str,
        source_event_id: str,
        observation: ProviderObservation,
        decision: MasteryDecision,
        action: LearningAction,
    ) -> WrongItemRecord | None:
        """Create one item only when a successful observation needs later work."""
        item_type = classify_observation(observation)
        if item_type is None:
            return None

        now = utc_text()
        wrong_item_id = str(uuid4())
        with self.database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO wrong_items(
                    id, user_id, concept_id, session_id, question_id, explanation_id,
                    observation_id, decision_id, source_event_id, question_text, answer_text,
                    error_type, error_summary, evidence_json, correction_text, status,
                    created_at, updated_at, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, NULL)
                """,
                (
                    wrong_item_id,
                    user_id,
                    concept_id,
                    session_id,
                    question_id,
                    explanation_id,
                    observation_id,
                    decision_id,
                    source_event_id,
                    question_text,
                    answer_text,
                    item_type.value,
                    summarize_observation(observation, item_type),
                    observation.model_dump_json(),
                    action.instruction,
                    now,
                    now,
                ),
            )
            self._insert_event(
                connection,
                event_type=EventType.WRONG_ITEM_CREATED,
                session_id=session_id,
                concept_id=concept_id,
                request_id=None,
                protocol_version=decision.protocol_version,
                payload={
                    "wrong_item_id": wrong_item_id,
                    "error_type": item_type.value,
                    "observation_id": observation_id,
                },
            )
            row = self._select_one(connection, wrong_item_id)
        return self._record_from_row(row)

    def get(self, wrong_item_id: str) -> WrongItemRecord:
        with self.database.connect() as connection:
            row = self._select_one(connection, wrong_item_id)
        if row is None:
            raise LookupError("错题不存在")
        return self._record_from_row(row)

    def list(
        self,
        *,
        user_id: str = LOCAL_USER_ID,
        status: WrongItemStatus | None = None,
        limit: int = 50,
    ) -> tuple[WrongItemRecord, ...]:
        """Return newest items, with open work naturally shown first."""
        bounded_limit = max(1, min(limit, 100))
        clauses = ["w.user_id = ?"]
        parameters: list[object] = [user_id]
        if status is not None:
            clauses.append("w.status = ?")
            parameters.append(status.value)
        parameters.append(bounded_limit)
        with self.database.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT w.*, c.display_name AS concept
                FROM wrong_items w
                JOIN concepts c ON c.id = w.concept_id
                WHERE {" AND ".join(clauses)}
                ORDER BY CASE w.status WHEN 'open' THEN 0 WHEN 'snoozed' THEN 1 ELSE 2 END,
                         w.created_at DESC
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return tuple(self._record_from_row(row) for row in rows)

    def update_status(
        self,
        *,
        wrong_item_id: str,
        status: WrongItemStatus,
        request_id: str,
    ) -> WrongItemRecord:
        """Update status and append a user-visible lifecycle event idempotently."""
        now = utc_text()
        with self.database.connect() as connection, connection:
            row = self._select_one(connection, wrong_item_id)
            if row is None:
                raise LookupError("错题不存在")
            existing_event = connection.execute(
                """
                SELECT payload_json FROM learning_events
                WHERE request_id = ? AND event_type = ?
                LIMIT 1
                """,
                (request_id, EventType.WRONG_ITEM_STATUS_UPDATED.value),
            ).fetchone()
            if existing_event is not None:
                payload = json.loads(existing_event["payload_json"])
                if (
                    payload.get("wrong_item_id") != wrong_item_id
                    or payload.get("status") != status.value
                ):
                    raise ValueError("同一个幂等键不能用于不同的错题状态变更")
                latest = self._select_one(connection, wrong_item_id)
                assert latest is not None
                return self._record_from_row(latest)

            resolved_at = now if status is WrongItemStatus.MASTERED else None
            connection.execute(
                """
                UPDATE wrong_items
                SET status = ?, updated_at = ?, resolved_at = ?
                WHERE id = ?
                """,
                (status.value, now, resolved_at, wrong_item_id),
            )
            self._insert_event(
                connection,
                event_type=EventType.WRONG_ITEM_STATUS_UPDATED,
                session_id=row["session_id"],
                concept_id=row["concept_id"],
                request_id=request_id,
                protocol_version=None,
                payload={"wrong_item_id": wrong_item_id, "status": status.value},
            )
            updated = self._select_one(connection, wrong_item_id)
        assert updated is not None
        return self._record_from_row(updated)

    @staticmethod
    def _select_one(
        connection: sqlite3.Connection,
        wrong_item_id: str,
    ) -> sqlite3.Row | None:
        row = connection.execute(
            """
            SELECT w.*, c.display_name AS concept
            FROM wrong_items w
            JOIN concepts c ON c.id = w.concept_id
            WHERE w.id = ?
            """,
            (wrong_item_id,),
        ).fetchone()
        return cast(sqlite3.Row | None, row)

    @staticmethod
    def _record_from_row(row: sqlite3.Row | None) -> WrongItemRecord:
        if row is None:
            raise LookupError("错题不存在")
        return WrongItemRecord(
            wrong_item_id=row["id"],
            user_id=row["user_id"],
            concept_id=row["concept_id"],
            concept=row["concept"],
            session_id=row["session_id"],
            question_id=row["question_id"],
            explanation_id=row["explanation_id"],
            observation_id=row["observation_id"],
            decision_id=row["decision_id"],
            source_event_id=row["source_event_id"],
            question_text=row["question_text"],
            answer_text=row["answer_text"],
            error_type=WrongItemType(row["error_type"]),
            error_summary=row["error_summary"],
            evidence_json=row["evidence_json"],
            correction_text=row["correction_text"],
            status=WrongItemStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            resolved_at=row["resolved_at"],
        )

    @staticmethod
    def _insert_event(
        connection: sqlite3.Connection,
        *,
        event_type: EventType,
        session_id: str,
        concept_id: str,
        request_id: str | None,
        protocol_version: str | None,
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
                LOCAL_USER_ID,
                session_id,
                concept_id,
                event_type.value,
                _event_payload(payload),
                request_id,
                protocol_version,
                utc_text(),
            ),
        )
