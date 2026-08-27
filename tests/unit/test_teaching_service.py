"""Tests for generated, source-traceable teaching lessons."""

from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.application.teaching_service import TeachingInputError, TeachingService
from ai_growth_companion.providers.base import (
    ProviderError,
    ProviderResponse,
    TeachingRequest,
)
from ai_growth_companion.providers.fake import FakeLLMProvider
from ai_growth_companion.repositories.database import Database, run_migrations
from ai_growth_companion.repositories.document_repository import SQLiteDocumentRepository
from ai_growth_companion.repositories.lesson_progress_repository import (
    SQLiteLessonProgressRepository,
)
from ai_growth_companion.repositories.lesson_repository import SQLiteLessonRepository


def service_for(
    tmp_path: Path,
    provider: FakeLLMProvider | None = None,
) -> tuple[TeachingService, DocumentLibraryService]:
    database = Database(f"sqlite:///{(tmp_path / 'teaching.db').as_posix()}")
    run_migrations(database)
    documents = DocumentLibraryService(
        SQLiteDocumentRepository(database), storage_root=tmp_path / "documents"
    )
    return TeachingService(
        documents,
        SQLiteLessonRepository(database),
        provider or FakeLLMProvider(),
        SQLiteLessonProgressRepository(database),
    ), documents


class UnrelatedTeachingProvider(FakeLLMProvider):
    """Return valid structure with a deliberately unrelated teaching summary."""

    def generate_lesson(self, request: TeachingRequest, *, request_id: str) -> ProviderResponse:
        response = super().generate_lesson(request, request_id=request_id)
        payload = dict(response.content)
        payload["title"] = "完全无关的课程"
        payload["summary"] = "这是一份没有提到用户主题的通用摘要。"
        payload["learning_objectives"] = ["完成一个通用学习目标"]
        return ProviderResponse(content=payload, metadata=response.metadata)


class UngroundedTeachingProvider(FakeLLMProvider):
    """Return a structurally valid lesson without chapter-level source proof."""

    def generate_lesson(self, request: TeachingRequest, *, request_id: str) -> ProviderResponse:
        response = super().generate_lesson(request, request_id=request_id)
        payload = dict(response.content)
        payload["sections"] = [
            {key: value for key, value in section.items() if key != "evidence"}
            for section in payload["sections"]
        ]
        payload["interactive_checks"] = [
            {key: value for key, value in check.items() if key != "evidence"}
            for check in payload["interactive_checks"]
        ]
        return ProviderResponse(content=payload, metadata=response.metadata)


class AlternateTeachingProvider(FakeLLMProvider):
    """Emit common DeepSeek field variants to exercise service normalization."""

    def generate_lesson(self, request: TeachingRequest, *, request_id: str) -> ProviderResponse:
        response = super().generate_lesson(request, request_id=request_id)
        payload = dict(response.content)
        payload["schema_version"] = "1.0"
        payload["sources"] = [request.sources[0][0]]
        alternate_sections = []
        for section in payload["sections"]:
            alternate = dict(section)
            alternate["type"] = alternate.pop("section_type")
            alternate_sections.append(alternate)
        payload["sections"] = alternate_sections
        payload["check_questions"] = [
            {"prompt": question, "options": ["A", "B"]} for question in payload["check_questions"]
        ]
        payload["interactive_checks"][0]["correct_answer"] = 1
        return ProviderResponse(content=payload, metadata=response.metadata)


class PositionalSectionTeachingProvider(FakeLLMProvider):
    """Emit four ordered sections without a section type to exercise the narrow fallback."""

    def generate_lesson(self, request: TeachingRequest, *, request_id: str) -> ProviderResponse:
        response = super().generate_lesson(request, request_id=request_id)
        payload = dict(response.content)
        payload["sections"] = [
            {key: value for key, value in section.items() if key not in {"section_type", "type"}}
            for section in payload["sections"]
        ]
        return ProviderResponse(content=payload, metadata=response.metadata)


class CapturingTeachingProvider(FakeLLMProvider):
    """Keep the request so the visual teaching path can be checked offline."""

    supports_vision = True

    def __init__(self) -> None:
        super().__init__()
        self.last_request: TeachingRequest | None = None

    def generate_lesson(self, request: TeachingRequest, *, request_id: str) -> ProviderResponse:
        self.last_request = request
        return super().generate_lesson(request, request_id=request_id)


class RepairingTeachingProvider(UngroundedTeachingProvider):
    """Simulate a real Provider that can fill only omitted evidence fields."""

    def repair_lesson_evidence(
        self,
        request: TeachingRequest,
        lesson_content: dict[str, object],
        *,
        request_id: str,
    ) -> ProviderResponse:
        del lesson_content
        evidence = {
            "document_id": request.sources[0][0],
            "quote": "极限描述函数在某点附近的变化趋势。",
        }
        return ProviderResponse(
            content={
                "sections": [{"evidence": [evidence]} for _ in range(4)],
                "interactive_checks": [{"evidence": [evidence]} for _ in range(2)],
            },
            metadata=self._metadata(
                request_id=request_id,
                prompt_version="test-evidence-repair",
                schema_version="teaching-lesson-v0.2",
            ),
        )


class CompletingTeachingProvider(FakeLLMProvider):
    """Simulate a model that first returns a short draft, then completes it."""

    def generate_lesson(self, request: TeachingRequest, *, request_id: str) -> ProviderResponse:
        response = super().generate_lesson(request, request_id=request_id)
        payload = dict(response.content)
        payload.pop("sections", None)
        payload.pop("interactive_checks", None)
        return ProviderResponse(content=payload, metadata=response.metadata)

    def complete_lesson(
        self,
        request: TeachingRequest,
        lesson_content: dict[str, object],
        *,
        request_id: str,
    ) -> ProviderResponse:
        del lesson_content
        response = super().generate_lesson(request, request_id=request_id)
        return ProviderResponse(content=response.content, metadata=response.metadata)


class PageAwareTeachingProvider(FakeLLMProvider):
    """Return genuine page numbers from text-extractable PDF source units."""

    def generate_lesson(self, request: TeachingRequest, *, request_id: str) -> ProviderResponse:
        response = super().generate_lesson(request, request_id=request_id)
        payload = dict(response.content)
        page_number = next(
            (unit.page_number for unit in request.source_units if unit.page_number is not None),
            None,
        )
        if page_number is not None:
            for key in ("sections", "interactive_checks"):
                for item in payload[key]:
                    for evidence in item["evidence"]:
                        evidence["page_number"] = page_number
        return ProviderResponse(content=payload, metadata=response.metadata)


def blank_pdf() -> bytes:
    stream = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=320, height=240)
    writer.write(stream)
    return stream.getvalue()


def _minimal_text_pdf(text: str) -> bytes:
    """Create a tiny text-extractable PDF without requiring a font package."""
    stream = f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n").encode(
            "ascii"
        )
    )
    return bytes(pdf)


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
    source_fact = "极限描述函数在某点附近的变化趋势。"
    assert source_fact in view.lesson.summary
    assert source_fact in view.lesson.sections[0].explanation
    assert source_fact in view.lesson.sections[2].explanation
    assert source_fact in view.lesson.interactive_checks[0].explanation
    assert source_fact in view.lesson.sections[0].evidence[0].quote
    assert source_fact in view.lesson.interactive_checks[0].evidence[0].quote
    assert teaching.get_lesson(view.lesson_id).lesson == view.lesson
    assert len(teaching.list_lessons()) == 1

    documents.delete(document.document_id)
    assert teaching.get_lesson(view.lesson_id).lesson == view.lesson
    assert teaching.get_lesson(view.lesson_id).source_documents == ()


def test_visual_teaching_can_use_image_only_pdf_without_text_extraction(
    tmp_path: Path,
) -> None:
    provider = CapturingTeachingProvider()
    teaching, documents = service_for(tmp_path, provider=provider)
    document = documents.upload(filename="扫描教材.pdf", content=blank_pdf())

    view = teaching.generate_lesson(
        topic="函数极限",
        document_ids=(document.document_id,),
        request_id="teaching-vision-service-1",
        use_vision=True,
    )

    assert provider.last_request is not None
    assert len(provider.last_request.visual_pages) == 1
    assert provider.last_request.visual_pages[0].page_number == 1
    assert view.lesson.sources[0].excerpt == "原始 PDF 页面将通过视觉输入读取。"
    assert view.lesson.sections[0].evidence[0].page_number == 1
    assert provider.last_request.source_units == ()


def test_missing_evidence_can_be_repaired_without_rewriting_lesson(tmp_path: Path) -> None:
    teaching, documents = service_for(tmp_path, provider=RepairingTeachingProvider())
    document = documents.upload(
        filename="topic.md", content="# 函数极限\n\n极限描述函数在某点附近的变化趋势。".encode()
    )

    lesson = teaching.generate_lesson(
        topic="函数极限",
        document_ids=(document.document_id,),
        request_id="teaching-repair-1",
    )

    assert lesson.lesson.sections[0].evidence[0].quote.startswith("极限描述函数")
    assert lesson.lesson.interactive_checks[0].evidence[0].document_id == document.document_id


def test_abbreviated_real_provider_output_can_be_completed(tmp_path: Path) -> None:
    teaching, documents = service_for(tmp_path, provider=CompletingTeachingProvider())
    document = documents.upload(
        filename="topic.md", content="# 函数极限\n\n极限描述函数在某点附近的变化趋势。".encode()
    )

    lesson = teaching.generate_lesson(
        topic="函数极限",
        document_ids=(document.document_id,),
        request_id="teaching-completion-1",
    )

    assert len(lesson.lesson.sections) == 4
    assert len(lesson.lesson.interactive_checks) == 2


def test_text_pdf_page_evidence_is_accepted(tmp_path: Path) -> None:
    teaching, documents = service_for(tmp_path, provider=PageAwareTeachingProvider())
    document = documents.upload(
        filename="topic.pdf", content=_minimal_text_pdf("function limits describe change")
    )

    lesson = teaching.generate_lesson(
        topic="函数极限",
        document_ids=(document.document_id,),
        request_id="teaching-page-evidence-1",
    )

    assert lesson.lesson.sections[0].evidence[0].page_number == 1


def test_teaching_requires_a_topic_and_a_source(tmp_path: Path) -> None:
    teaching, _documents = service_for(tmp_path)

    with pytest.raises(TeachingInputError, match="主题"):
        teaching.generate_lesson(topic=" ", document_ids=(), request_id="teaching-test-2")

    with pytest.raises(TeachingInputError, match="至少选择"):
        teaching.generate_lesson(topic="函数极限", document_ids=(), request_id="teaching-test-3")


def test_teaching_rejects_obviously_unrelated_provider_content(tmp_path: Path) -> None:
    _default_teaching, documents = service_for(tmp_path)
    database = Database(f"sqlite:///{(tmp_path / 'unrelated.db').as_posix()}")
    run_migrations(database)
    teaching = TeachingService(
        documents,
        SQLiteLessonRepository(database),
        UnrelatedTeachingProvider(),
        SQLiteLessonProgressRepository(database),
    )
    document = documents.upload(
        filename="topic.md", content="# 函数极限\n\n极限描述变化趋势。".encode()
    )

    with pytest.raises(ProviderError, match="unrelated|not relevant|不相关") as captured:
        teaching.generate_lesson(
            topic="函数极限",
            document_ids=(document.document_id,),
            request_id="teaching-unrelated-1",
        )
    assert captured.value.code == "TEACHING_CONTENT_NOT_RELEVANT"


def test_teaching_rejects_structured_content_without_source_evidence(tmp_path: Path) -> None:
    teaching, documents = service_for(tmp_path, provider=UngroundedTeachingProvider())
    document = documents.upload(
        filename="topic.md", content="# 函数极限\n\n极限描述变化趋势。".encode()
    )

    with pytest.raises(ProviderError, match="资料证据|source evidence") as captured:
        teaching.generate_lesson(
            topic="函数极限",
            document_ids=(document.document_id,),
            request_id="teaching-ungrounded-1",
        )
    assert captured.value.code == "TEACHING_SOURCE_EVIDENCE_MISSING"


def test_teaching_normalizes_common_provider_field_variants(tmp_path: Path) -> None:
    teaching, documents = service_for(tmp_path, provider=AlternateTeachingProvider())
    document = documents.upload(
        filename="topic.md", content="# 函数极限\n\n极限描述变化趋势。".encode()
    )

    lesson = teaching.generate_lesson(
        topic="函数极限",
        document_ids=(document.document_id,),
        request_id="teaching-normalize-1",
    )

    assert lesson.lesson.schema_version == "teaching-lesson-v0.2"
    assert [section.section_type for section in lesson.lesson.sections] == [
        "concept",
        "mechanism",
        "boundary",
        "example",
    ]
    assert all(isinstance(question, str) for question in lesson.lesson.check_questions)
    assert (
        lesson.lesson.interactive_checks[0].correct_answer
        == (lesson.lesson.interactive_checks[0].options[0])
    )
    assert lesson.lesson.sources[0].document_id == document.document_id


def test_teaching_normalizes_ordered_sections_without_type(tmp_path: Path) -> None:
    teaching, documents = service_for(tmp_path, provider=PositionalSectionTeachingProvider())
    document = documents.upload(
        filename="topic.md", content="# 函数极限\n\n极限描述变化趋势。".encode()
    )

    lesson = teaching.generate_lesson(
        topic="函数极限",
        document_ids=(document.document_id,),
        request_id="teaching-normalize-positional-1",
    )

    assert [section.section_type for section in lesson.lesson.sections] == [
        "concept",
        "mechanism",
        "boundary",
        "example",
    ]


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

    report = teaching.get_learning_report()
    assert report.lesson_count == 1
    assert report.completed_lesson_count == 1
    assert report.total_activity_count == 2
    assert report.answered_activity_count == 2
    assert report.correct_activity_count == 1
    assert report.completion_rate == 100
    assert report.accuracy == 50
    assert report.source_document_count == 1
