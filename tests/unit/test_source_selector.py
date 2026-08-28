"""Tests for deterministic topic-to-document recommendations."""

from pathlib import Path

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.application.source_selector import TopicSourceSelector
from ai_growth_companion.repositories.database import Database, run_migrations
from ai_growth_companion.repositories.document_repository import SQLiteDocumentRepository


def selector_for(tmp_path: Path) -> tuple[TopicSourceSelector, DocumentLibraryService]:
    database = Database(f"sqlite:///{(tmp_path / 'selector.db').as_posix()}")
    run_migrations(database)
    documents = DocumentLibraryService(
        SQLiteDocumentRepository(database), storage_root=tmp_path / "documents"
    )
    return TopicSourceSelector(documents), documents


def test_recommends_one_high_confidence_chunk_for_topic(tmp_path: Path) -> None:
    selector, documents = selector_for(tmp_path)
    limits = documents.upload(
        filename="Calculus_part_02_pages_0151-0300.pdf.txt",
        content=(
            b"Prelude to Limits\n\nThe limit of a function describes the value approached "
            b"as x gets close to a point. One-sided limits can differ."
        ),
    )
    documents.upload(
        filename="linear-algebra.txt",
        content=b"Vectors and matrices are introduced here.",
    )

    result = selector.recommend(topic="limits")

    assert result.confidence == "high"
    assert result.requires_manual_selection is False
    assert result.requires_confirmation is False
    assert result.selected_document_ids == (limits.document_id,)
    assert result.matches[0].page_range == "第 151-300 页"
    assert "limits" in result.matches[0].matched_terms


def test_chinese_topic_uses_small_explicit_alias_set(tmp_path: Path) -> None:
    selector, documents = selector_for(tmp_path)
    eigen = documents.upload(
        filename="linear-algebra-part-03.txt",
        content=b"Eigenvalues and eigenvectors describe important matrix behavior.",
    )
    documents.upload(
        filename="calculus.txt",
        content=b"Limits and derivatives are discussed in this chapter.",
    )

    result = selector.recommend(topic="特征值")

    assert result.selected_document_ids == (eigen.document_id,)
    assert result.confidence == "high"
    assert result.requires_confirmation is False
    assert "eigenvalue" in result.matches[0].matched_terms


def test_recommendation_supports_common_legacy_text_encoding(tmp_path: Path) -> None:
    selector, documents = selector_for(tmp_path)
    limits = documents.upload(
        filename="legacy-limits.txt",
        content="函数极限描述函数在某点附近的变化趋势".encode("gb18030"),
    )

    result = selector.recommend(topic="函数极限")

    assert result.selected_document_ids == (limits.document_id,)
    assert result.confidence == "high"


def test_recommendation_can_be_restricted_to_manual_source_scope(tmp_path: Path) -> None:
    selector, documents = selector_for(tmp_path)
    limits = documents.upload(filename="limits.txt", content=b"The limit of a function exists.")
    vectors = documents.upload(filename="vectors.txt", content=b"Vectors and matrices.")

    result = selector.recommend(topic="vectors", document_ids=(limits.document_id,))

    assert result.matches == ()
    assert result.selected_document_ids == ()
    assert result.confidence == "low"
    assert result.requires_manual_selection is True
    assert vectors.document_id not in result.selected_document_ids


def test_teaching_service_exposes_recommendation_contract(tmp_path: Path) -> None:
    from ai_growth_companion.application.teaching_service import TeachingService
    from ai_growth_companion.providers.fake import FakeLLMProvider
    from ai_growth_companion.repositories.lesson_progress_repository import (
        SQLiteLessonProgressRepository,
    )
    from ai_growth_companion.repositories.lesson_repository import SQLiteLessonRepository

    database = Database(f"sqlite:///{(tmp_path / 'teaching.db').as_posix()}")
    run_migrations(database)
    documents = DocumentLibraryService(
        SQLiteDocumentRepository(database), storage_root=tmp_path / "documents"
    )
    document = documents.upload(
        filename="limits.md", content=b"# Limits\n\nThe limit approaches a value."
    )
    teaching = TeachingService(
        documents,
        SQLiteLessonRepository(database),
        FakeLLMProvider(),
        SQLiteLessonProgressRepository(database),
    )

    result = teaching.recommend_sources(topic="limits")

    assert result.selected_document_ids == (document.document_id,)
