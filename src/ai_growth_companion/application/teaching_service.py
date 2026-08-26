"""Application service for source-grounded lesson generation."""

import json
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.application.knowledge_extraction import extract_knowledge
from ai_growth_companion.application.models import DocumentView
from ai_growth_companion.domain.events import LOCAL_USER_ID
from ai_growth_companion.providers.base import ProviderError, TeachingProvider, TeachingRequest
from ai_growth_companion.repositories.lesson_repository import LessonRecord, SQLiteLessonRepository
from ai_growth_companion.schemas.teaching import TeachingLesson


class TeachingInputError(ValueError):
    """Raised when uploaded knowledge cannot support a lesson."""


class TeachingLessonView(BaseModel):
    """Lesson plus immutable generation metadata exposed to the UI."""

    model_config = ConfigDict(frozen=True)

    lesson_id: str
    lesson: TeachingLesson
    source_documents: tuple[DocumentView, ...]
    provider: str
    model_name: str
    prompt_version: str
    created_at: datetime


class TeachingService:
    """Extract selected materials, generate a validated lesson, and persist it."""

    def __init__(
        self,
        document_library: DocumentLibraryService,
        repository: SQLiteLessonRepository,
        provider: TeachingProvider,
    ) -> None:
        self.document_library = document_library
        self.repository = repository
        self.provider = provider

    def generate_lesson(
        self,
        *,
        topic: str,
        document_ids: tuple[str, ...],
        learning_goal: str | None = None,
        learner_level: str | None = None,
        request_id: str,
    ) -> TeachingLessonView:
        normalized_topic = topic.strip()
        if not normalized_topic:
            raise TeachingInputError("请填写要学习的知识主题")
        if not document_ids:
            raise TeachingInputError("请至少选择一份知识资料")

        source_documents: list[DocumentView] = []
        source_parts: list[str] = []
        source_refs: list[tuple[str, str, str]] = []
        for document_id in document_ids:
            document, content = self.document_library.read(document_id)
            extracted = extract_knowledge(document.filename, content)
            source_documents.append(document)
            source_excerpt = " ".join(extracted.text.split())[:1_800]
            source_refs.append((document.document_id, document.filename, source_excerpt))
            source_parts.append(f"【{document.filename}】\n{extracted.text}")

        response = self.provider.generate_lesson(
            TeachingRequest(
                topic=normalized_topic,
                source_text="\n\n".join(source_parts)[:60_000],
                sources=tuple(source_refs),
                learning_goal=learning_goal.strip() if learning_goal else None,
                learner_level=learner_level,
            ),
            request_id=request_id,
        )
        try:
            lesson = TeachingLesson.model_validate(response.content)
        except Exception as error:
            raise ProviderError(
                "Teaching Provider returned invalid lesson structure",
                code="TEACHING_OUTPUT_SCHEMA_INVALID",
                retryable=False,
            ) from error
        if not lesson.interactive_checks:
            raise ProviderError(
                "Teaching Provider returned no interactive checks",
                code="TEACHING_OUTPUT_SCHEMA_INVALID",
                retryable=False,
            )

        # The selected files are the authoritative source list; the model cannot invent it.
        lesson = TeachingLesson.model_validate(
            {
                **lesson.model_dump(),
                "topic": normalized_topic,
                "sources": [
                    {"document_id": document_id, "filename": filename, "excerpt": excerpt}
                    for document_id, filename, excerpt in source_refs
                ],
            }
        )
        lesson_id = str(uuid4())
        record = self.repository.create(
            lesson_id=lesson_id,
            topic=normalized_topic,
            source_document_ids=tuple(document_ids),
            lesson_json=lesson.model_dump_json(),
            provider=response.metadata.provider,
            model_name=response.metadata.model,
            model_revision=response.metadata.model_revision,
            prompt_version=response.metadata.prompt_version,
            schema_version=response.metadata.schema_version,
            request_id=request_id,
            user_id=LOCAL_USER_ID,
        )
        return self._view(record, source_documents)

    def get_lesson(self, lesson_id: str) -> TeachingLessonView:
        record = self.repository.get(lesson_id)
        documents = self._existing_documents(record.source_document_ids)
        return self._view(record, documents)

    def list_lessons(self, *, limit: int = 20) -> tuple[TeachingLessonView, ...]:
        records = self.repository.list(limit=limit)
        return tuple(
            self._view(record, self._existing_documents(record.source_document_ids))
            for record in records
        )

    def _existing_documents(self, document_ids: tuple[str, ...]) -> tuple[DocumentView, ...]:
        documents: list[DocumentView] = []
        for document_id in document_ids:
            try:
                documents.append(self.document_library.get(document_id))
            except LookupError:
                # A lesson remains readable after its source file is deleted.
                continue
        return tuple(documents)

    @staticmethod
    def _view(
        record: LessonRecord, documents: tuple[DocumentView, ...] | list[DocumentView]
    ) -> TeachingLessonView:
        return TeachingLessonView(
            lesson_id=record.lesson_id,
            lesson=TeachingLesson.model_validate(json.loads(record.lesson_json)),
            source_documents=tuple(documents),
            provider=record.provider,
            model_name=record.model_name,
            prompt_version=record.prompt_version,
            created_at=datetime.fromisoformat(record.created_at.replace("Z", "+00:00")),
        )
