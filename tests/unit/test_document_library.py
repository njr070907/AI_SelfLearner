"""Unit tests for the local document-library service."""

from pathlib import Path

import pytest

from ai_growth_companion.application.document_library import (
    DocumentLibraryService,
    DocumentValidationError,
)
from ai_growth_companion.repositories.database import Database, run_migrations
from ai_growth_companion.repositories.document_repository import SQLiteDocumentRepository


def service_for(tmp_path: Path) -> DocumentLibraryService:
    database = Database(f"sqlite:///{(tmp_path / 'documents.db').as_posix()}")
    run_migrations(database)
    return DocumentLibraryService(
        SQLiteDocumentRepository(database),
        storage_root=tmp_path / "storage",
    )


def test_document_crud_keeps_metadata_and_file_bytes_in_sync(tmp_path: Path) -> None:
    service = service_for(tmp_path)

    created = service.upload(filename="极限笔记.md", content="# 极限\n\n先看定义。".encode())
    assert created.filename == "极限笔记.md"
    assert created.mime_type == "text/markdown"
    assert created.size_bytes > 0
    assert len(service.list_documents()) == 1

    view, content = service.read(created.document_id)
    assert view == created
    assert content.startswith(b"# ")

    renamed = service.rename(created.document_id, filename="函数极限.md")
    assert renamed.filename == "函数极限.md"
    assert service.read(created.document_id)[0].filename == "函数极限.md"

    replaced = service.replace(
        created.document_id,
        filename="函数极限.txt",
        content=b"definition and examples",
    )
    assert replaced.filename == "函数极限.txt"
    assert replaced.status == "replaced"
    assert service.read(created.document_id)[1] == b"definition and examples"

    service.delete(created.document_id)
    assert service.list_documents() == ()
    assert not list((tmp_path / "storage").iterdir())
    with pytest.raises(LookupError, match="资料不存在"):
        service.get(created.document_id)


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        ("lesson.exe", b"bad", "只支持"),
        ("../lesson.md", b"bad", "目录路径"),
        ("lesson.md", b"", "空文件"),
    ],
)
def test_document_upload_rejects_invalid_files(
    tmp_path: Path,
    filename: str,
    content: bytes,
    message: str,
) -> None:
    service = service_for(tmp_path)

    with pytest.raises(DocumentValidationError, match=message):
        service.upload(filename=filename, content=content)
    assert service.list_documents() == ()
    assert not list((tmp_path / "storage").iterdir())


def test_rename_cannot_change_extension_and_size_limit_is_enforced(tmp_path: Path) -> None:
    service = service_for(tmp_path)
    document = service.upload(filename="lesson.txt", content=b"small")

    with pytest.raises(DocumentValidationError, match="不能改变文件类型"):
        service.rename(document.document_id, filename="lesson.pdf")

    oversized = b"x" * (20 * 1024 * 1024 + 1)
    with pytest.raises(DocumentValidationError, match="20 MB"):
        service.upload(filename="large.txt", content=oversized)
