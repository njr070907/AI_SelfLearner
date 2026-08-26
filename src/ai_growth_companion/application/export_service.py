"""User-scoped local data export with a self-describing ZIP artifact."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.domain.events import LOCAL_USER_ID
from ai_growth_companion.repositories.database import Database, migration_status, utc_text

EXPORT_FORMAT = "ai-growth-companion-user-export"
EXPORT_VERSION = "0.1"
_SAFE_FILENAME = re.compile(r"[^\w.\-\u4e00-\u9fff ]", re.UNICODE)


@dataclass(frozen=True)
class ExportArtifact:
    """A complete user export ready for a local download or backup."""

    filename: str
    content: bytes
    sha256: str
    table_counts: dict[str, int]
    included_document_count: int
    missing_document_count: int


class UserExportService:
    """Export only the local user's records and owned document bytes."""

    def __init__(self, database: Database, document_library: DocumentLibraryService) -> None:
        self.database = database
        self.document_library = document_library

    def export(self, *, user_id: str = LOCAL_USER_ID) -> ExportArtifact:
        """Build a versioned ZIP containing user data, metadata and source files."""
        current_version, available_version = migration_status(self.database)
        if current_version != available_version:
            raise RuntimeError(
                "数据库迁移未完成，不能导出："
                f"current={current_version}, available={available_version}"
            )

        with self.database.connect() as connection:
            tables = self._read_user_tables(connection, user_id=user_id)

        document_rows = tables.get("documents", [])
        document_entries: list[dict[str, Any]] = []
        document_payloads: list[tuple[str, bytes]] = []
        for row in document_rows:
            document_id = str(row["id"])
            filename = str(row["filename"])
            archive_name = f"documents/{document_id}_{self._safe_filename(filename)}"
            try:
                _, content = self.document_library.read(document_id)
            except LookupError:
                document_entries.append(
                    {
                        "document_id": document_id,
                        "filename": filename,
                        "archive_path": None,
                        "status": "missing",
                    }
                )
                continue
            document_entries.append(
                {
                    "document_id": document_id,
                    "filename": filename,
                    "archive_path": archive_name,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "size_bytes": len(content),
                    "status": "included",
                }
            )
            document_payloads.append((archive_name, content))

        generated_at = utc_text()
        manifest: dict[str, Any] = {
            "format": EXPORT_FORMAT,
            "version": EXPORT_VERSION,
            "generated_at": generated_at,
            "user_id": user_id,
            "database": {
                "schema_version": current_version,
                "available_schema_version": available_version,
            },
            "tables": {name: len(rows) for name, rows in tables.items()},
            "documents": document_entries,
            "warnings": (
                ["部分资料文件在导出时不存在，因此仅导出了其元数据。"]
                if any(entry["status"] == "missing" for entry in document_entries)
                else []
            ),
        }

        archive = BytesIO()
        with zipfile.ZipFile(archive, mode="w") as output:
            output.writestr(
                "manifest.json",
                self._json_bytes(manifest),
                compress_type=zipfile.ZIP_DEFLATED,
            )
            for table_name, rows in tables.items():
                output.writestr(
                    f"data/{table_name}.json",
                    self._json_bytes(rows),
                    compress_type=zipfile.ZIP_DEFLATED,
                )
            for archive_name, content in document_payloads:
                # PDFs and other source files are already compressed in most cases;
                # storing bytes avoids needless CPU work and preserves them exactly.
                output.writestr(archive_name, content, compress_type=zipfile.ZIP_STORED)

        content = archive.getvalue()
        timestamp = generated_at.replace(":", "").replace("-", "").replace("T", "-").rstrip("Z")
        return ExportArtifact(
            filename=f"ai-growth-companion-export-{timestamp}.zip",
            content=content,
            sha256=hashlib.sha256(content).hexdigest(),
            table_counts={name: len(rows) for name, rows in tables.items()},
            included_document_count=sum(
                entry["status"] == "included" for entry in document_entries
            ),
            missing_document_count=sum(entry["status"] == "missing" for entry in document_entries),
        )

    @classmethod
    def _read_user_tables(
        cls,
        connection: sqlite3.Connection,
        *,
        user_id: str,
    ) -> dict[str, list[dict[str, Any]]]:
        queries = {
            "users": (
                "SELECT id, display_name, locale, created_at, updated_at FROM users WHERE id = ?",
                (user_id,),
            ),
            "concepts": (
                """
                SELECT DISTINCT c.id, c.normalized_name, c.display_name, c.domain,
                                c.created_at
                FROM concepts c
                WHERE EXISTS (
                    SELECT 1 FROM learning_sessions s
                    WHERE s.user_id = ? AND s.concept_id = c.id
                )
                   OR EXISTS (
                    SELECT 1 FROM concept_states cs
                    WHERE cs.user_id = ? AND cs.concept_id = c.id
                )
                   OR EXISTS (
                    SELECT 1 FROM learning_events e
                    WHERE e.user_id = ? AND e.concept_id = c.id
                )
                   OR EXISTS (
                    SELECT 1 FROM wrong_items w
                    WHERE w.user_id = ? AND w.concept_id = c.id
                )
                   OR EXISTS (
                    SELECT 1 FROM review_items r
                    WHERE r.user_id = ? AND r.concept_id = c.id
                )
                ORDER BY c.id
                """,
                (user_id,) * 5,
            ),
            "learning_sessions": (
                "SELECT * FROM learning_sessions WHERE user_id = ? ORDER BY started_at, id",
                (user_id,),
            ),
            "feynman_questions": (
                """
                SELECT q.* FROM feynman_questions q
                JOIN learning_sessions s ON s.id = q.session_id
                WHERE s.user_id = ? ORDER BY q.created_at, q.id
                """,
                (user_id,),
            ),
            "user_explanations": (
                """
                SELECT e.* FROM user_explanations e
                JOIN learning_sessions s ON s.id = e.session_id
                WHERE s.user_id = ? ORDER BY e.created_at, e.id
                """,
                (user_id,),
            ),
            "provider_observations": (
                """
                SELECT o.* FROM provider_observations o
                JOIN user_explanations e ON e.id = o.explanation_id
                JOIN learning_sessions s ON s.id = e.session_id
                WHERE s.user_id = ? ORDER BY o.created_at, o.id
                """,
                (user_id,),
            ),
            "mastery_decisions": (
                """
                SELECT d.* FROM mastery_decisions d
                JOIN provider_observations o ON o.id = d.observation_id
                JOIN user_explanations e ON e.id = o.explanation_id
                JOIN learning_sessions s ON s.id = e.session_id
                WHERE s.user_id = ? ORDER BY d.created_at, d.id
                """,
                (user_id,),
            ),
            "learning_actions": (
                """
                SELECT a.* FROM learning_actions a
                JOIN mastery_decisions d ON d.id = a.decision_id
                JOIN provider_observations o ON o.id = d.observation_id
                JOIN user_explanations e ON e.id = o.explanation_id
                JOIN learning_sessions s ON s.id = e.session_id
                WHERE s.user_id = ? ORDER BY a.created_at, a.id
                """,
                (user_id,),
            ),
            "diagnosis_feedback": (
                "SELECT * FROM diagnosis_feedback WHERE user_id = ? ORDER BY created_at, id",
                (user_id,),
            ),
            "learning_events": (
                "SELECT * FROM learning_events WHERE user_id = ? ORDER BY created_at, id",
                (user_id,),
            ),
            "concept_states": (
                "SELECT * FROM concept_states WHERE user_id = ? ORDER BY concept_id",
                (user_id,),
            ),
            "wrong_items": (
                "SELECT * FROM wrong_items WHERE user_id = ? ORDER BY created_at, id",
                (user_id,),
            ),
            "review_items": (
                "SELECT * FROM review_items WHERE user_id = ? ORDER BY due_at, id",
                (user_id,),
            ),
            "review_attempts": (
                """
                SELECT a.* FROM review_attempts a
                JOIN review_items r ON r.id = a.review_item_id
                WHERE r.user_id = ? ORDER BY a.created_at, a.id
                """,
                (user_id,),
            ),
            "documents": (
                "SELECT * FROM documents WHERE user_id = ? ORDER BY updated_at, id",
                (user_id,),
            ),
            "teaching_lessons": (
                "SELECT * FROM teaching_lessons WHERE user_id = ? ORDER BY created_at, id",
                (user_id,),
            ),
            "teaching_lesson_progress": (
                """
                SELECT * FROM teaching_lesson_progress
                WHERE user_id = ? ORDER BY updated_at, lesson_id
                """,
                (user_id,),
            ),
            "teaching_activity_attempts": (
                """
                SELECT * FROM teaching_activity_attempts
                WHERE user_id = ? ORDER BY created_at, id
                """,
                (user_id,),
            ),
        }
        return {
            table_name: [dict(row) for row in connection.execute(query, params).fetchall()]
            for table_name, (query, params) in queries.items()
        }

    @staticmethod
    def _json_bytes(value: object) -> bytes:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")

    @staticmethod
    def _safe_filename(filename: str) -> str:
        safe = _SAFE_FILENAME.sub("_", Path(filename).name).strip(" .")
        return (safe or "document")[:180]
