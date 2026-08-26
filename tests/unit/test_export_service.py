"""Tests for user-scoped, source-preserving data exports."""

import json
import zipfile
from io import BytesIO
from pathlib import Path

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.application.export_service import UserExportService
from ai_growth_companion.repositories.database import Database, run_migrations
from ai_growth_companion.repositories.document_repository import SQLiteDocumentRepository


def service_for(tmp_path: Path) -> tuple[Database, DocumentLibraryService]:
    database = Database(f"sqlite:///{(tmp_path / 'export.db').as_posix()}")
    run_migrations(database)
    return database, DocumentLibraryService(
        SQLiteDocumentRepository(database),
        storage_root=tmp_path / "documents",
    )


def test_export_contains_user_tables_manifest_and_original_document_bytes(tmp_path: Path) -> None:
    database, documents = service_for(tmp_path)
    source = "# 函数极限\n\n这是一份可以导出的本地资料。".encode()
    document = documents.upload(filename="limits.md", content=source)

    artifact = UserExportService(database, documents).export()

    assert artifact.filename.startswith("ai-growth-companion-export-")
    assert len(artifact.sha256) == 64
    assert artifact.table_counts["users"] == 1
    assert artifact.table_counts["documents"] == 1
    assert artifact.included_document_count == 1
    assert artifact.missing_document_count == 0

    with zipfile.ZipFile(BytesIO(artifact.content)) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        exported_document = json.loads(archive.read("data/documents.json"))[0]

        assert manifest["format"] == "ai-growth-companion-user-export"
        assert manifest["database"]["schema_version"] == 7
        assert exported_document["id"] == document.document_id
        assert exported_document["sha256"] == document.sha256
        archive_path = manifest["documents"][0]["archive_path"]
        assert archive_path in names
        assert archive.read(archive_path) == source


def test_export_records_missing_document_without_failing_or_inventing_bytes(
    tmp_path: Path,
) -> None:
    database, documents = service_for(tmp_path)
    document = documents.upload(filename="missing.txt", content=b"will be removed")
    (tmp_path / "documents" / f"{document.document_id}.txt").unlink()

    artifact = UserExportService(database, documents).export()

    assert artifact.included_document_count == 0
    assert artifact.missing_document_count == 1
    with zipfile.ZipFile(BytesIO(artifact.content)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["documents"][0]["status"] == "missing"
        assert manifest["documents"][0]["archive_path"] is None
        assert not any(name.startswith("documents/") for name in archive.namelist())
