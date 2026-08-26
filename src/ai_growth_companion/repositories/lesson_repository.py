"""SQLite persistence for generated, source-traceable teaching lessons."""

import json
import sqlite3
from dataclasses import dataclass
from typing import cast

from ai_growth_companion.domain.events import LOCAL_USER_ID
from ai_growth_companion.repositories.database import Database, utc_text


@dataclass(frozen=True)
class LessonRecord:
    lesson_id: str
    user_id: str
    topic: str
    source_document_ids: tuple[str, ...]
    lesson_json: str
    provider: str
    model_name: str
    model_revision: str | None
    prompt_version: str
    schema_version: str
    request_id: str
    created_at: str


class SQLiteLessonRepository:
    """Persist generated lessons without storing a second copy of source bytes."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def create(
        self,
        *,
        lesson_id: str,
        topic: str,
        source_document_ids: tuple[str, ...],
        lesson_json: str,
        provider: str,
        model_name: str,
        model_revision: str | None,
        prompt_version: str,
        schema_version: str,
        request_id: str,
        user_id: str = LOCAL_USER_ID,
    ) -> LessonRecord:
        now = utc_text()
        with self.database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO teaching_lessons(
                    id, user_id, topic, source_document_ids_json, lesson_json,
                    provider, model_name, model_revision, prompt_version,
                    schema_version, request_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lesson_id,
                    user_id,
                    topic,
                    json.dumps(source_document_ids, ensure_ascii=False),
                    lesson_json,
                    provider,
                    model_name,
                    model_revision,
                    prompt_version,
                    schema_version,
                    request_id,
                    now,
                ),
            )
            row = self._select_one(connection, lesson_id, user_id)
        assert row is not None
        return self._record_from_row(row)

    def list(
        self,
        *,
        user_id: str = LOCAL_USER_ID,
        limit: int = 50,
    ) -> tuple[LessonRecord, ...]:
        bounded_limit = max(1, min(limit, 200))
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, user_id, topic, source_document_ids_json, lesson_json,
                       provider, model_name, model_revision, prompt_version,
                       schema_version, request_id, created_at
                FROM teaching_lessons
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, bounded_limit),
            ).fetchall()
        return tuple(self._record_from_row(row) for row in rows)

    def get(self, lesson_id: str, *, user_id: str = LOCAL_USER_ID) -> LessonRecord:
        with self.database.connect() as connection:
            row = self._select_one(connection, lesson_id, user_id)
        if row is None:
            raise LookupError("教学内容不存在")
        return self._record_from_row(row)

    @staticmethod
    def _select_one(
        connection: sqlite3.Connection,
        lesson_id: str,
        user_id: str,
    ) -> sqlite3.Row | None:
        return cast(
            sqlite3.Row | None,
            connection.execute(
                """
                SELECT id, user_id, topic, source_document_ids_json, lesson_json,
                       provider, model_name, model_revision, prompt_version,
                       schema_version, request_id, created_at
                FROM teaching_lessons
                WHERE id = ? AND user_id = ?
                """,
                (lesson_id, user_id),
            ).fetchone(),
        )

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> LessonRecord:
        return LessonRecord(
            lesson_id=str(row["id"]),
            user_id=str(row["user_id"]),
            topic=str(row["topic"]),
            source_document_ids=tuple(json.loads(str(row["source_document_ids_json"]))),
            lesson_json=str(row["lesson_json"]),
            provider=str(row["provider"]),
            model_name=str(row["model_name"]),
            model_revision=(str(row["model_revision"]) if row["model_revision"] else None),
            prompt_version=str(row["prompt_version"]),
            schema_version=str(row["schema_version"]),
            request_id=str(row["request_id"]),
            created_at=str(row["created_at"]),
        )
