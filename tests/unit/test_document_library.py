"""Unit tests for the local document-library service."""

import io
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

import ai_growth_companion.application.document_library as document_library_module
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


def test_rename_cannot_change_extension_and_oversized_text_is_split_safely(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = service_for(tmp_path)
    document = service.upload(filename="lesson.txt", content=b"small")

    with pytest.raises(DocumentValidationError, match="不能改变文件类型"):
        service.rename(document.document_id, filename="lesson.pdf")

    monkeypatch.setattr(document_library_module, "MAX_DOCUMENT_BYTES", 900)
    monkeypatch.setattr(document_library_module, "AUTO_SPLIT_TARGET_BYTES", 700)
    oversized = ("第一段内容。\n\n第二段内容。\n" * 120).encode("utf-8")
    documents = service.upload_documents(filename="large.txt", content=oversized)
    payloads = [service.read(document.document_id)[1] for document in documents]

    assert len(documents) > 1
    assert all(document.size_bytes <= 900 for document in documents)
    assert b"".join(payloads) == oversized
    assert all(payload.endswith(b"\n\n") for payload in payloads[:-1])


def test_oversized_pdf_is_split_at_page_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = service_for(tmp_path)
    monkeypatch.setattr(document_library_module, "MAX_DOCUMENT_BYTES", 900)
    monkeypatch.setattr(document_library_module, "AUTO_SPLIT_TARGET_BYTES", 700)

    writer = PdfWriter()
    for _ in range(20):
        writer.add_blank_page(width=612, height=792)
    stream = io.BytesIO()
    writer.write(stream)

    documents = service.upload_documents(filename="book.pdf", content=stream.getvalue())

    assert len(documents) > 1
    assert all(document.size_bytes <= 900 for document in documents)
    page_counts = [
        len(PdfReader(io.BytesIO(service.read(document.document_id)[1])).pages)
        for document in documents
    ]
    assert sum(page_counts) == 20
    assert all("_pages_" in document.filename for document in documents)


def test_oversized_replacement_keeps_original_entry_and_adds_chunks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = service_for(tmp_path)
    original = service.upload(filename="old.txt", content=b"old")
    monkeypatch.setattr(document_library_module, "MAX_DOCUMENT_BYTES", 900)
    monkeypatch.setattr(document_library_module, "AUTO_SPLIT_TARGET_BYTES", 700)
    oversized = ("新的段落内容。\n\n" * 120).encode("utf-8")

    documents = service.replace_documents(
        original.document_id,
        filename="new.txt",
        content=oversized,
    )

    assert len(documents) > 1
    assert documents[0].document_id == original.document_id
    assert documents[0].status == "replaced"
    assert b"".join(service.read(document.document_id)[1] for document in documents) == oversized
