"""Tests for generated, source-traceable teaching lessons."""

from pathlib import Path

import pytest

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.application.teaching_service import TeachingInputError, TeachingService
from ai_growth_companion.providers.fake import FakeLLMProvider
from ai_growth_companion.repositories.database import Database, run_migrations
from ai_growth_companion.repositories.document_repository import SQLiteDocumentRepository
from ai_growth_companion.repositories.lesson_repository import SQLiteLessonRepository


def service_for(tmp_path: Path) -> tuple[TeachingService, DocumentLibraryService]:
    database = Database(f"sqlite:///{(tmp_path / 'teaching.db').as_posix()}")
    run_migrations(database)
    documents = DocumentLibraryService(
        SQLiteDocumentRepository(database), storage_root=tmp_path / "documents"
    )
    return TeachingService(
        documents, SQLiteLessonRepository(database), FakeLLMProvider()
    ), documents


def test_uploaded_material_becomes_a_persisted_lesson(tmp_path: Path) -> None:
    teaching, documents = service_for(tmp_path)
    document = documents.upload(
        filename="limits.md",
        content="# 函数极限\n\n极限描述函数在某点附近的变化趋势。".encode(),
    )

    view = teaching.generate_lesson(
        topic="函数极限",
        document_ids=(document.document_id,),
        learning_goal="能解释定义和适用边界",
        learner_level="beginner",
        request_id="teaching-test-1",
    )

    assert view.lesson.title == "函数极限：从材料到理解"
    assert {section.section_type for section in view.lesson.sections} == {
        "concept",
        "mechanism",
        "boundary",
        "example",
    }
    assert view.lesson.sources[0].document_id == document.document_id
    assert teaching.get_lesson(view.lesson_id).lesson == view.lesson
    assert len(teaching.list_lessons()) == 1

    documents.delete(document.document_id)
    assert teaching.get_lesson(view.lesson_id).lesson == view.lesson
    assert teaching.get_lesson(view.lesson_id).source_documents == ()


def test_teaching_requires_a_topic_and_a_source(tmp_path: Path) -> None:
    teaching, _documents = service_for(tmp_path)

    with pytest.raises(TeachingInputError, match="主题"):
        teaching.generate_lesson(topic=" ", document_ids=(), request_id="teaching-test-2")

    with pytest.raises(TeachingInputError, match="至少选择"):
        teaching.generate_lesson(topic="函数极限", document_ids=(), request_id="teaching-test-3")
