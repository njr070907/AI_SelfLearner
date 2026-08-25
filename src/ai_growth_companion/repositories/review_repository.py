"""SQLite persistence for due review items and deterministic retest scheduling."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast
from uuid import uuid4

from ai_growth_companion.domain.events import LOCAL_USER_ID, EventType
from ai_growth_companion.domain.review import (
    ReviewAttemptStatus,
    ReviewItemStatus,
    ReviewOutcome,
    ReviewScheduler,
)
from ai_growth_companion.repositories.database import Database, utc_text
from ai_growth_companion.repositories.wrong_item_repository import WrongItemRecord
from ai_growth_companion.schemas.diagnosis import (
    LearningAction,
    MasteryDecision,
    ProviderObservation,
)


@dataclass(frozen=True)
class ReviewItemRecord:
    """Raw schedule data used to build the page contract."""

    review_item_id: str
    user_id: str
    concept_id: str
    concept: str
    wrong_item_id: str
    status: ReviewItemStatus
    due_at: str
    interval_days: int
    attempt_count: int
    last_result: ReviewOutcome | None
    last_attempt_id: str | None
    created_at: str
    updated_at: str
    question_text: str


@dataclass(frozen=True)
class ReviewAttemptRecord:
    """A submitted retest, including failures that did not change scheduling."""

    attempt_id: str
    review_item_id: str
    request_id: str
    answer_text: str
    status: ReviewAttemptStatus
    result: ReviewOutcome | None
    observation_json: str | None
    decision_json: str | None
    action_json: str | None
    error_code: str | None
    created_at: str


def _event_payload(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _next_due(now: str, interval_days: int) -> str:
    parsed = datetime.fromisoformat(now.replace("Z", "+00:00"))
    return (parsed + timedelta(days=interval_days)).isoformat().replace("+00:00", "Z")


class SQLiteReviewRepository:
    """Persist review schedules and retest attempts with request idempotency."""

    def __init__(self, database: Database, *, scheduler: ReviewScheduler | None = None) -> None:
        self.database = database
        self.scheduler = scheduler or ReviewScheduler()

    def ensure_for_wrong_item(self, item: WrongItemRecord) -> ReviewItemRecord:
        """Create an immediately due schedule for a new wrong item, once."""
        with self.database.connect() as connection, connection:
            existing = self._select_one_by_wrong_item(connection, item.wrong_item_id)
            if existing is not None:
                return self._record_from_row(existing)

            review_item_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO review_items(
                    id, user_id, concept_id, wrong_item_id, status, due_at,
                    interval_days, attempt_count, last_result, last_attempt_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'active', ?, ?, 0, NULL, NULL, ?, ?)
                """,
                (
                    review_item_id,
                    item.user_id,
                    item.concept_id,
                    item.wrong_item_id,
                    item.created_at,
                    self.scheduler.intervals[0],
                    item.created_at,
                    item.updated_at,
                ),
            )
            self._insert_event(
                connection,
                event_type=EventType.REVIEW_ITEM_CREATED,
                session_id=item.session_id,
                concept_id=item.concept_id,
                request_id=None,
                payload={"review_item_id": review_item_id, "wrong_item_id": item.wrong_item_id},
            )
            row = self._select_one(connection, review_item_id)
        return self._record_from_row(row)

    def list_due(
        self,
        *,
        user_id: str = LOCAL_USER_ID,
        now: str | None = None,
        limit: int = 50,
    ) -> tuple[ReviewItemRecord, ...]:
        """Return active items whose due time has arrived, oldest first."""
        now_text = now or utc_text()
        bounded_limit = max(1, min(limit, 100))
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT r.*, c.display_name AS concept, w.question_text
                FROM review_items r
                JOIN concepts c ON c.id = r.concept_id
                JOIN wrong_items w ON w.id = r.wrong_item_id
                WHERE r.user_id = ? AND r.status = 'active' AND r.due_at <= ?
                ORDER BY r.due_at ASC, r.created_at ASC
                LIMIT ?
                """,
                (user_id, now_text, bounded_limit),
            ).fetchall()
        return tuple(self._record_from_row(row) for row in rows)

    def get(self, review_item_id: str) -> ReviewItemRecord:
        with self.database.connect() as connection:
            row = self._select_one(connection, review_item_id)
        return self._record_from_row(row)

    def get_attempt_by_request(
        self,
        request_id: str,
    ) -> tuple[ReviewItemRecord, ReviewAttemptRecord] | None:
        """Load an idempotent retest before any provider call is attempted."""
        with self.database.connect() as connection:
            attempt_row = self._select_attempt_by_request(connection, request_id)
            if attempt_row is None:
                return None
            item_row = self._select_one(connection, attempt_row["review_item_id"])
        return self._record_from_row(item_row), self._attempt_from_row(attempt_row)

    def mark_mastered_for_wrong_item(self, wrong_item_id: str) -> None:
        """Remove a mastered wrong item from the active review queue."""
        with self.database.connect() as connection, connection:
            connection.execute(
                """
                UPDATE review_items
                SET status = 'mastered', updated_at = ?
                WHERE wrong_item_id = ?
                """,
                (utc_text(), wrong_item_id),
            )

    def record_failure(
        self,
        *,
        review_item_id: str,
        answer_text: str,
        request_id: str,
        status: ReviewAttemptStatus,
        error_code: str,
    ) -> tuple[ReviewItemRecord, ReviewAttemptRecord]:
        """Record an unusable provider attempt while leaving due scheduling intact."""
        with self.database.connect() as connection, connection:
            item_row = self._select_one(connection, review_item_id)
            item = self._record_from_row(item_row)
            existing = self._select_attempt_by_request(connection, request_id)
            if existing is not None:
                self._ensure_same_request(existing, review_item_id, answer_text)
                return item, self._attempt_from_row(existing)

            attempt_id = str(uuid4())
            now = utc_text()
            connection.execute(
                """
                INSERT INTO review_attempts(
                    id, review_item_id, request_id, answer_text, status, result,
                    observation_json, decision_json, action_json, error_code, created_at
                ) VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, ?, ?)
                """,
                (
                    attempt_id,
                    review_item_id,
                    request_id,
                    answer_text,
                    status.value,
                    error_code,
                    now,
                ),
            )
            self._insert_event(
                connection,
                event_type=EventType.RETEST_SUBMITTED,
                session_id=None,
                concept_id=item.concept_id,
                request_id=request_id,
                payload={
                    "review_item_id": review_item_id,
                    "attempt_id": attempt_id,
                    "status": status.value,
                    "error_code": error_code,
                },
            )
            attempt_row = self._select_attempt(connection, attempt_id)
        return item, self._attempt_from_row(attempt_row)

    def record_success(
        self,
        *,
        review_item_id: str,
        answer_text: str,
        request_id: str,
        result: ReviewOutcome,
        observation: ProviderObservation,
        decision: MasteryDecision,
        action: LearningAction,
    ) -> tuple[ReviewItemRecord, ReviewAttemptRecord]:
        """Save a usable retest and advance its next due time deterministically."""
        with self.database.connect() as connection, connection:
            item_row = self._select_one(connection, review_item_id)
            item = self._record_from_row(item_row)
            existing = self._select_attempt_by_request(connection, request_id)
            if existing is not None:
                self._ensure_same_request(existing, review_item_id, answer_text)
                return item, self._attempt_from_row(existing)

            now = utc_text()
            next_interval = self.scheduler.next_interval(item.interval_days, result)
            next_due = _next_due(now, next_interval)
            attempt_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO review_attempts(
                    id, review_item_id, request_id, answer_text, status, result,
                    observation_json, decision_json, action_json, error_code, created_at
                ) VALUES (?, ?, ?, ?, 'succeeded', ?, ?, ?, ?, NULL, ?)
                """,
                (
                    attempt_id,
                    review_item_id,
                    request_id,
                    answer_text,
                    result.value,
                    observation.model_dump_json(),
                    decision.model_dump_json(),
                    action.model_dump_json(),
                    now,
                ),
            )
            connection.execute(
                """
                UPDATE review_items
                SET due_at = ?, interval_days = ?, attempt_count = attempt_count + 1,
                    last_result = ?, last_attempt_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    next_due,
                    next_interval,
                    result.value,
                    attempt_id,
                    now,
                    review_item_id,
                ),
            )
            self._insert_event(
                connection,
                event_type=EventType.RETEST_SUBMITTED,
                session_id=None,
                concept_id=item.concept_id,
                request_id=request_id,
                protocol_version=decision.protocol_version,
                payload={
                    "review_item_id": review_item_id,
                    "attempt_id": attempt_id,
                    "status": ReviewAttemptStatus.SUCCEEDED.value,
                    "result": result.value,
                },
            )
            self._insert_event(
                connection,
                event_type=EventType.REVIEW_SCHEDULED,
                session_id=None,
                concept_id=item.concept_id,
                request_id=request_id,
                payload={
                    "review_item_id": review_item_id,
                    "interval_days": next_interval,
                    "due_at": next_due,
                    "result": result.value,
                },
            )
            updated_row = self._select_one(connection, review_item_id)
            attempt_row = self._select_attempt(connection, attempt_id)
        return self._record_from_row(updated_row), self._attempt_from_row(attempt_row)

    @staticmethod
    def _ensure_same_request(
        row: sqlite3.Row,
        review_item_id: str,
        answer_text: str,
    ) -> None:
        if row["review_item_id"] != review_item_id or row["answer_text"] != answer_text:
            raise ValueError("同一个幂等键不能用于不同的复测提交")

    @staticmethod
    def _select_one_by_wrong_item(
        connection: sqlite3.Connection,
        wrong_item_id: str,
    ) -> sqlite3.Row | None:
        row = connection.execute(
            "SELECT * FROM review_items WHERE wrong_item_id = ?",
            (wrong_item_id,),
        ).fetchone()
        return cast(sqlite3.Row | None, row)

    @staticmethod
    def _select_one(
        connection: sqlite3.Connection,
        review_item_id: str,
    ) -> sqlite3.Row | None:
        row = connection.execute(
            """
            SELECT r.*, c.display_name AS concept, w.question_text
            FROM review_items r
            JOIN concepts c ON c.id = r.concept_id
            JOIN wrong_items w ON w.id = r.wrong_item_id
            WHERE r.id = ?
            """,
            (review_item_id,),
        ).fetchone()
        return cast(sqlite3.Row | None, row)

    @staticmethod
    def _select_attempt_by_request(
        connection: sqlite3.Connection,
        request_id: str,
    ) -> sqlite3.Row | None:
        row = connection.execute(
            "SELECT * FROM review_attempts WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        return cast(sqlite3.Row | None, row)

    @staticmethod
    def _select_attempt(
        connection: sqlite3.Connection,
        attempt_id: str,
    ) -> sqlite3.Row | None:
        row = connection.execute(
            "SELECT * FROM review_attempts WHERE id = ?",
            (attempt_id,),
        ).fetchone()
        return cast(sqlite3.Row | None, row)

    @staticmethod
    def _record_from_row(row: sqlite3.Row | None) -> ReviewItemRecord:
        if row is None:
            raise LookupError("复习项目不存在")
        return ReviewItemRecord(
            review_item_id=row["id"],
            user_id=row["user_id"],
            concept_id=row["concept_id"],
            concept=row["concept"],
            wrong_item_id=row["wrong_item_id"],
            status=ReviewItemStatus(row["status"]),
            due_at=row["due_at"],
            interval_days=int(row["interval_days"]),
            attempt_count=int(row["attempt_count"]),
            last_result=(None if row["last_result"] is None else ReviewOutcome(row["last_result"])),
            last_attempt_id=row["last_attempt_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            question_text=row["question_text"],
        )

    @staticmethod
    def _attempt_from_row(row: sqlite3.Row | None) -> ReviewAttemptRecord:
        if row is None:
            raise LookupError("复测记录不存在")
        return ReviewAttemptRecord(
            attempt_id=row["id"],
            review_item_id=row["review_item_id"],
            request_id=row["request_id"],
            answer_text=row["answer_text"],
            status=ReviewAttemptStatus(row["status"]),
            result=None if row["result"] is None else ReviewOutcome(row["result"]),
            observation_json=row["observation_json"],
            decision_json=row["decision_json"],
            action_json=row["action_json"],
            error_code=row["error_code"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _insert_event(
        connection: sqlite3.Connection,
        *,
        event_type: EventType,
        session_id: str | None,
        concept_id: str,
        request_id: str | None,
        protocol_version: str | None = None,
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
