"""Persistence for conventional lesson progress and activity attempts."""

import json
import sqlite3
from dataclasses import dataclass
from typing import cast
from uuid import uuid4

from ai_growth_companion.domain.events import LOCAL_USER_ID
from ai_growth_companion.repositories.database import Database, utc_text


@dataclass(frozen=True)
class LessonActivityAttemptRecord:
    """One submitted interactive activity answer."""

    attempt_id: str
    lesson_id: str
    user_id: str
    activity_index: int
    selected_answer: str
    is_correct: bool
    request_id: str
    created_at: str


@dataclass(frozen=True)
class LessonProgressRecord:
    """Progress projection for one lesson and local user."""

    lesson_id: str
    user_id: str
    current_section: int
    completed_activity_indexes: tuple[int, ...]
    attempts: tuple[LessonActivityAttemptRecord, ...]
    started_at: str
    updated_at: str
    completed_at: str | None


class SQLiteLessonProgressRepository:
    """Persist resumable lesson state without treating quiz results as mastery."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def get_or_create(
        self,
        lesson_id: str,
        *,
        activity_count: int,
        user_id: str = LOCAL_USER_ID,
    ) -> LessonProgressRecord:
        """Return progress, creating an empty projection on first lesson open."""
        if activity_count < 0:
            raise ValueError("activity_count cannot be negative")
        with self.database.connect() as connection, connection:
            row = self._select_progress(connection, lesson_id, user_id)
            if row is None:
                now = utc_text()
                connection.execute(
                    """
                    INSERT INTO teaching_lesson_progress(
                        lesson_id, user_id, current_section,
                        completed_activity_indexes_json, started_at, updated_at, completed_at
                    ) VALUES (?, ?, 0, ?, ?, ?, NULL)
                    """,
                    (lesson_id, user_id, "[]", now, now),
                )
                row = self._select_progress(connection, lesson_id, user_id)
            assert row is not None
            attempts = self._select_attempts(connection, lesson_id, user_id)
        return self._record_from_rows(row, attempts)

    def record_activity_attempt(
        self,
        *,
        lesson_id: str,
        activity_index: int,
        activity_count: int,
        selected_answer: str,
        is_correct: bool,
        request_id: str,
        user_id: str = LOCAL_USER_ID,
    ) -> tuple[LessonProgressRecord, LessonActivityAttemptRecord]:
        """Save an answer and update completion without assigning a mastery level."""
        if activity_index < 1 or activity_index > activity_count:
            raise ValueError("activity_index is outside the lesson activity range")
        normalized_answer = selected_answer.strip()
        if not normalized_answer:
            raise ValueError("selected_answer cannot be empty")

        with self.database.connect() as connection, connection:
            progress_row = self._select_progress(connection, lesson_id, user_id)
            if progress_row is None:
                now = utc_text()
                connection.execute(
                    """
                    INSERT INTO teaching_lesson_progress(
                        lesson_id, user_id, current_section,
                        completed_activity_indexes_json, started_at, updated_at, completed_at
                    ) VALUES (?, ?, 0, ?, ?, ?, NULL)
                    """,
                    (lesson_id, user_id, "[]", now, now),
                )
                progress_row = self._select_progress(connection, lesson_id, user_id)
            assert progress_row is not None

            existing = self._select_attempt_by_request(connection, request_id)
            if existing is not None:
                if (
                    existing["lesson_id"] != lesson_id
                    or int(existing["activity_index"]) != activity_index
                    or existing["selected_answer"] != normalized_answer
                ):
                    raise ValueError("同一个幂等键不能用于不同的互动答案")
                attempt = self._attempt_from_row(existing)
                attempts = self._select_attempts(connection, lesson_id, user_id)
                return self._record_from_rows(progress_row, attempts), attempt

            attempt_id = str(uuid4())
            now = utc_text()
            connection.execute(
                """
                INSERT INTO teaching_activity_attempts(
                    id, lesson_id, user_id, activity_index, selected_answer,
                    is_correct, request_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    lesson_id,
                    user_id,
                    activity_index,
                    normalized_answer,
                    int(is_correct),
                    request_id,
                    now,
                ),
            )
            completed = set(json.loads(str(progress_row["completed_activity_indexes_json"])))
            completed.add(activity_index)
            connection.execute(
                """
                UPDATE teaching_lesson_progress
                SET completed_activity_indexes_json = ?, updated_at = ?
                WHERE lesson_id = ? AND user_id = ?
                """,
                (json.dumps(sorted(completed)), now, lesson_id, user_id),
            )
            attempt_row = self._select_attempt(connection, attempt_id)
            updated_progress = self._select_progress(connection, lesson_id, user_id)
            attempts = self._select_attempts(connection, lesson_id, user_id)
        assert attempt_row is not None and updated_progress is not None
        return self._record_from_rows(updated_progress, attempts), self._attempt_from_row(
            attempt_row
        )

    def update_position(
        self,
        *,
        lesson_id: str,
        current_section: int,
        activity_count: int,
        user_id: str = LOCAL_USER_ID,
    ) -> LessonProgressRecord:
        """Save the learner's last visible section for resume."""
        if current_section < 0:
            raise ValueError("current_section cannot be negative")
        self.get_or_create(lesson_id, activity_count=activity_count, user_id=user_id)
        with self.database.connect() as connection, connection:
            connection.execute(
                """
                UPDATE teaching_lesson_progress
                SET current_section = ?, updated_at = ?
                WHERE lesson_id = ? AND user_id = ?
                """,
                (current_section, utc_text(), lesson_id, user_id),
            )
            row = self._select_progress(connection, lesson_id, user_id)
            attempts = self._select_attempts(connection, lesson_id, user_id)
        assert row is not None
        return self._record_from_rows(row, attempts)

    def complete(
        self,
        *,
        lesson_id: str,
        activity_count: int,
        user_id: str = LOCAL_USER_ID,
    ) -> LessonProgressRecord:
        """Mark a lesson complete only after all required activities are answered."""
        progress = self.get_or_create(
            lesson_id,
            activity_count=activity_count,
            user_id=user_id,
        )
        if not set(range(1, activity_count + 1)).issubset(set(progress.completed_activity_indexes)):
            raise ValueError("完成课程前需要先完成全部互动练习")
        with self.database.connect() as connection, connection:
            now = utc_text()
            connection.execute(
                """
                UPDATE teaching_lesson_progress
                SET updated_at = ?, completed_at = COALESCE(completed_at, ?)
                WHERE lesson_id = ? AND user_id = ?
                """,
                (now, now, lesson_id, user_id),
            )
            row = self._select_progress(connection, lesson_id, user_id)
            attempts = self._select_attempts(connection, lesson_id, user_id)
        assert row is not None
        return self._record_from_rows(row, attempts)

    @staticmethod
    def _select_progress(
        connection: sqlite3.Connection,
        lesson_id: str,
        user_id: str,
    ) -> sqlite3.Row | None:
        return cast(
            sqlite3.Row | None,
            connection.execute(
                """
                SELECT lesson_id, user_id, current_section,
                       completed_activity_indexes_json, started_at, updated_at, completed_at
                FROM teaching_lesson_progress
                WHERE lesson_id = ? AND user_id = ?
                """,
                (lesson_id, user_id),
            ).fetchone(),
        )

    @staticmethod
    def _select_attempts(
        connection: sqlite3.Connection,
        lesson_id: str,
        user_id: str,
    ) -> tuple[sqlite3.Row, ...]:
        return tuple(
            connection.execute(
                """
                SELECT id, lesson_id, user_id, activity_index, selected_answer,
                       is_correct, request_id, created_at
                FROM teaching_activity_attempts
                WHERE lesson_id = ? AND user_id = ?
                ORDER BY activity_index ASC, created_at DESC
                """,
                (lesson_id, user_id),
            ).fetchall()
        )

    @staticmethod
    def _select_attempt_by_request(
        connection: sqlite3.Connection,
        request_id: str,
    ) -> sqlite3.Row | None:
        return cast(
            sqlite3.Row | None,
            connection.execute(
                "SELECT * FROM teaching_activity_attempts WHERE request_id = ?",
                (request_id,),
            ).fetchone(),
        )

    @staticmethod
    def _select_attempt(
        connection: sqlite3.Connection,
        attempt_id: str,
    ) -> sqlite3.Row | None:
        return cast(
            sqlite3.Row | None,
            connection.execute(
                "SELECT * FROM teaching_activity_attempts WHERE id = ?",
                (attempt_id,),
            ).fetchone(),
        )

    @staticmethod
    def _attempt_from_row(row: sqlite3.Row) -> LessonActivityAttemptRecord:
        return LessonActivityAttemptRecord(
            attempt_id=str(row["id"]),
            lesson_id=str(row["lesson_id"]),
            user_id=str(row["user_id"]),
            activity_index=int(row["activity_index"]),
            selected_answer=str(row["selected_answer"]),
            is_correct=bool(row["is_correct"]),
            request_id=str(row["request_id"]),
            created_at=str(row["created_at"]),
        )

    @classmethod
    def _record_from_rows(
        cls,
        row: sqlite3.Row,
        attempts: tuple[sqlite3.Row, ...],
    ) -> LessonProgressRecord:
        return LessonProgressRecord(
            lesson_id=str(row["lesson_id"]),
            user_id=str(row["user_id"]),
            current_section=int(row["current_section"]),
            completed_activity_indexes=tuple(
                int(value) for value in json.loads(str(row["completed_activity_indexes_json"]))
            ),
            attempts=tuple(cls._attempt_from_row(item) for item in attempts),
            started_at=str(row["started_at"]),
            updated_at=str(row["updated_at"]),
            completed_at=(str(row["completed_at"]) if row["completed_at"] else None),
        )
