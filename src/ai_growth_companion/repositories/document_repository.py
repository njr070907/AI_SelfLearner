"""SQLite persistence for the local document library."""

import sqlite3
from dataclasses import dataclass
from typing import cast

from ai_growth_companion.domain.events import LOCAL_USER_ID
from ai_growth_companion.repositories.database import Database, utc_text


@dataclass(frozen=True)
class DocumentRecord:
    """Document metadata kept in SQLite; file bytes remain on disk."""

    document_id: str
    user_id: str
    filename: str
    storage_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    status: str
    created_at: str
    updated_at: str


class SQLiteDocumentRepository:
    """Persist document metadata with user-scoped CRUD operations."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def create(
        self,
        *,
        document_id: str,
        user_id: str,
        filename: str,
        storage_name: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
    ) -> DocumentRecord:
        now = utc_text()
        with self.database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO documents(
                    id, user_id, filename, storage_name, mime_type,
                    size_bytes, sha256, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ready', ?, ?)
                """,
                (
                    document_id,
                    user_id,
                    filename,
                    storage_name,
                    mime_type,
                    size_bytes,
                    sha256,
                    now,
                    now,
                ),
            )
            row = self._select_one(connection, document_id, user_id)
        assert row is not None
        return self._record_from_row(row)

    def list(
        self,
        *,
        user_id: str = LOCAL_USER_ID,
        limit: int = 100,
    ) -> tuple[DocumentRecord, ...]:
        bounded_limit = max(1, min(limit, 500))
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, user_id, filename, storage_name, mime_type,
                       size_bytes, sha256, status, created_at, updated_at
                FROM documents
                WHERE user_id = ?
                ORDER BY updated_at DESC, filename COLLATE NOCASE ASC
                LIMIT ?
                """,
                (user_id, bounded_limit),
            ).fetchall()
        return tuple(self._record_from_row(row) for row in rows)

    def get(self, document_id: str, *, user_id: str = LOCAL_USER_ID) -> DocumentRecord:
        with self.database.connect() as connection:
            row = self._select_one(connection, document_id, user_id)
        if row is None:
            raise LookupError("资料不存在")
        return self._record_from_row(row)

    def rename(
        self,
        document_id: str,
        *,
        filename: str,
        user_id: str = LOCAL_USER_ID,
    ) -> DocumentRecord:
        with self.database.connect() as connection, connection:
            if self._select_one(connection, document_id, user_id) is None:
                raise LookupError("资料不存在")
            connection.execute(
                """
                UPDATE documents
                SET filename = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (filename, utc_text(), document_id, user_id),
            )
            row = self._select_one(connection, document_id, user_id)
        assert row is not None
        return self._record_from_row(row)

    def replace(
        self,
        document_id: str,
        *,
        filename: str,
        storage_name: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        user_id: str = LOCAL_USER_ID,
    ) -> DocumentRecord:
        with self.database.connect() as connection, connection:
            if self._select_one(connection, document_id, user_id) is None:
                raise LookupError("资料不存在")
            connection.execute(
                """
                UPDATE documents
                SET filename = ?, storage_name = ?, mime_type = ?,
                    size_bytes = ?, sha256 = ?, status = 'replaced', updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (
                    filename,
                    storage_name,
                    mime_type,
                    size_bytes,
                    sha256,
                    utc_text(),
                    document_id,
                    user_id,
                ),
            )
            row = self._select_one(connection, document_id, user_id)
        assert row is not None
        return self._record_from_row(row)

    def delete(self, document_id: str, *, user_id: str = LOCAL_USER_ID) -> DocumentRecord:
        with self.database.connect() as connection, connection:
            row = self._select_one(connection, document_id, user_id)
            if row is None:
                raise LookupError("资料不存在")
            connection.execute(
                "DELETE FROM documents WHERE id = ? AND user_id = ?",
                (document_id, user_id),
            )
        return self._record_from_row(row)

    @staticmethod
    def _select_one(
        connection: sqlite3.Connection,
        document_id: str,
        user_id: str,
    ) -> sqlite3.Row | None:
        return cast(
            sqlite3.Row | None,
            connection.execute(
                """
                SELECT id, user_id, filename, storage_name, mime_type,
                       size_bytes, sha256, status, created_at, updated_at
                FROM documents
                WHERE id = ? AND user_id = ?
                """,
                (document_id, user_id),
            ).fetchone(),
        )

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> DocumentRecord:
        return DocumentRecord(
            document_id=str(row["id"]),
            user_id=str(row["user_id"]),
            filename=str(row["filename"]),
            storage_name=str(row["storage_name"]),
            mime_type=str(row["mime_type"]),
            size_bytes=int(row["size_bytes"]),
            sha256=str(row["sha256"]),
            status=str(row["status"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
