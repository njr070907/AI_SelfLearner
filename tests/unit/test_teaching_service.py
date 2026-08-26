"""Tests for generated, source-traceable teaching lessons."""

from pathlib import Path

import pytest

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.application.teaching_service import TeachingInputError, TeachingService
from ai_growth_companion.providers.fake import FakeLLMProvider
from ai_growth_companion.repositories.database import Database, run_migrations
from ai_growth_companion.repositories.document_repository import SQLiteDocumentRepository
from ai_growth_companion.repositories.lesson_progress_repository import (
    SQLiteLessonProgressRepository,
)
from ai_growth_companion.repositories.lesson_repository import SQLiteLessonRepository


def service_for(tmp_path: Path) -> tuple[TeachingService, DocumentLibraryService]:
    database = Database(f"sqlite:///{(tmp_path / 'teaching.db').as_posix()}")
    run_migrations(database)
    documents = DocumentLibraryService(
        SQLiteDocumentRepository(database), storage_root=tmp_path / "documents"
    )
    return TeachingService(
        documents,
        SQLiteLessonRepository(database),
        FakeLLMProvider(),
        SQLiteLessonProgressRepository(database),
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
    assert len(view.lesson.interactive_checks) == 2
    assert (
        view.lesson.interactive_checks[0].correct_answer
        in view.lesson.interactive_checks[0].options
    )
    assert view.lesson.sources[0].document_id == document.document_id
    assert view.lesson.sections[0].source_document_ids == [document.document_id]
    assert view.lesson.interactive_checks[0].source_document_ids == [document.document_id]
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


def test_lesson_activity_progress_is_persisted_and_idempotent(tmp_path: Path) -> None:
    teaching, documents = service_for(tmp_path)
    document = documents.upload(
        filename="limits.md",
        content="# 函数极限\n\n极限描述函数在某点附近的变化趋势。".encode(),
    )
    lesson = teaching.generate_lesson(
        topic="函数极限",
        document_ids=(document.document_id,),
        request_id="teaching-progress-1",
    )

    initial = teaching.get_lesson(lesson.lesson_id).progress
    assert initial.completed_activity_indexes == ()
    assert initial.completed_at is None

    first = lesson.lesson.interactive_checks[0]
    updated = teaching.record_activity_attempt(
        lesson_id=lesson.lesson_id,
        activity_index=1,
        selected_answer=first.correct_answer,
        request_id="teaching-progress-answer-1",
    )
    assert updated.completed_activity_indexes == (1,)
    assert updated.attempts[0].selected_answer == first.correct_answer

    replayed = teaching.record_activity_attempt(
        lesson_id=lesson.lesson_id,
        activity_index=1,
        selected_answer=first.correct_answer,
        request_id="teaching-progress-answer-1",
    )
    assert replayed == updated

    with pytest.raises(ValueError, match="幂等键"):
        teaching.record_activity_attempt(
            lesson_id=lesson.lesson_id,
            activity_index=1,
            selected_answer="另一个答案",
            request_id="teaching-progress-answer-1",
        )

    second = lesson.lesson.interactive_checks[1]
    teaching.record_activity_attempt(
        lesson_id=lesson.lesson_id,
        activity_index=2,
        selected_answer=second.options[-1],
        request_id="teaching-progress-answer-2",
    )
    completed = teaching.complete_lesson(lesson.lesson_id)
    assert completed.completed_at is not None
    assert completed.completed_activity_indexes == (1, 2)
    assert teaching.get_lesson(lesson.lesson_id).progress == completed
