"""Application service for source-grounded lesson generation."""

import json
from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.application.knowledge_extraction import extract_knowledge
from ai_growth_companion.application.models import DocumentView
from ai_growth_companion.domain.events import LOCAL_USER_ID
from ai_growth_companion.providers.base import ProviderError, TeachingProvider, TeachingRequest
from ai_growth_companion.repositories.lesson_progress_repository import (
    LessonProgressRecord,
    SQLiteLessonProgressRepository,
)
from ai_growth_companion.repositories.lesson_repository import LessonRecord, SQLiteLessonRepository
from ai_growth_companion.schemas.teaching import TeachingLesson


class TeachingInputError(ValueError):
    """Raised when uploaded knowledge cannot support a lesson."""


class TeachingActivityAttemptView(BaseModel):
    """Persisted activity result shown without changing mastery state."""

    activity_index: int
    selected_answer: str
    is_correct: bool
    created_at: datetime


class TeachingProgressView(BaseModel):
    """Resumable progress for one conventional lesson."""

    lesson_id: str
    current_section: int
    completed_activity_indexes: tuple[int, ...]
    attempts: tuple[TeachingActivityAttemptView, ...]
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    @property
    def completed_activity_count(self) -> int:
        return len(self.completed_activity_indexes)


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
    progress: TeachingProgressView


class TeachingReportView(BaseModel):
    """Backend-owned course activity report, separate from mastery decisions."""

    lesson_count: int
    completed_lesson_count: int
    total_activity_count: int
    answered_activity_count: int
    correct_activity_count: int
    completion_rate: int
    accuracy: int
    source_document_count: int


class TeachingService:
    """Extract selected materials, generate a validated lesson, and persist it."""

    def __init__(
        self,
        document_library: DocumentLibraryService,
        repository: SQLiteLessonRepository,
        provider: TeachingProvider,
        progress_repository: SQLiteLessonProgressRepository,
    ) -> None:
        self.document_library = document_library
        self.repository = repository
        self.provider = provider
        self.progress_repository = progress_repository

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
        selected_source_ids = {document_id for document_id, _, _ in source_refs}
        try:
            normalized_content = self._normalize_provider_lesson(
                response.content,
                topic=normalized_topic,
                source_refs=source_refs,
            )
            lesson = TeachingLesson.model_validate(normalized_content)
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
        if not self._mentions_topic(lesson, normalized_topic):
            raise ProviderError(
                "Teaching Provider returned content unrelated to the requested topic",
                code="TEACHING_CONTENT_NOT_RELEVANT",
                retryable=False,
            )

        # The selected files are the authoritative source list; the model cannot invent it.
        lesson_payload = lesson.model_dump()
        for section in lesson_payload["sections"]:
            section["source_document_ids"] = self._normalize_source_ids(
                section.get("source_document_ids", []),
                selected_source_ids,
            )
        for interaction in lesson_payload["interactive_checks"]:
            interaction["source_document_ids"] = self._normalize_source_ids(
                interaction.get("source_document_ids", []),
                selected_source_ids,
            )
        lesson = TeachingLesson.model_validate(
            {
                **lesson_payload,
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

    def get_learning_report(self, *, limit: int = 20) -> TeachingReportView:
        """Return a consistent report for the conventional teaching workspace."""
        return self.build_learning_report(self.list_lessons(limit=limit))

    @staticmethod
    def build_learning_report(lessons: Sequence[TeachingLessonView]) -> TeachingReportView:
        """Calculate report metrics from persisted latest attempts, not UI state."""
        latest_attempts: dict[tuple[str, int], TeachingActivityAttemptView] = {}
        total_activity_count = 0
        completed_lesson_count = 0
        source_document_ids: set[str] = set()
        for lesson in lessons:
            total_activity_count += len(lesson.lesson.interactive_checks)
            completed_lesson_count += lesson.progress.completed_at is not None
            source_document_ids.update(source.document_id for source in lesson.lesson.sources)
            for attempt in lesson.progress.attempts:
                key = (lesson.lesson_id, attempt.activity_index)
                previous = latest_attempts.get(key)
                if previous is None or attempt.created_at > previous.created_at:
                    latest_attempts[key] = attempt

        answered_activity_count = len(latest_attempts)
        correct_activity_count = sum(attempt.is_correct for attempt in latest_attempts.values())
        return TeachingReportView(
            lesson_count=len(lessons),
            completed_lesson_count=completed_lesson_count,
            total_activity_count=total_activity_count,
            answered_activity_count=answered_activity_count,
            correct_activity_count=correct_activity_count,
            completion_rate=(
                round(answered_activity_count / total_activity_count * 100)
                if total_activity_count
                else 0
            ),
            accuracy=(
                round(correct_activity_count / answered_activity_count * 100)
                if answered_activity_count
                else 0
            ),
            source_document_count=len(source_document_ids),
        )

    def record_activity_attempt(
        self,
        *,
        lesson_id: str,
        activity_index: int,
        selected_answer: str,
        request_id: str,
    ) -> TeachingProgressView:
        """Persist a teaching interaction and return the fresh progress projection."""
        view = self.get_lesson(lesson_id)
        if activity_index < 1 or activity_index > len(view.lesson.interactive_checks):
            raise ValueError("activity_index is outside the lesson activity range")
        check = view.lesson.interactive_checks[activity_index - 1]
        self.progress_repository.record_activity_attempt(
            lesson_id=lesson_id,
            activity_index=activity_index,
            activity_count=len(view.lesson.interactive_checks),
            selected_answer=selected_answer,
            is_correct=selected_answer == check.correct_answer,
            request_id=request_id,
        )
        return self.get_lesson(lesson_id).progress

    def update_position(self, *, lesson_id: str, current_section: int) -> TeachingProgressView:
        """Save the last visible lesson section for resume."""
        view = self.get_lesson(lesson_id)
        return self._progress_view(
            self.progress_repository.update_position(
                lesson_id=lesson_id,
                current_section=current_section,
                activity_count=len(view.lesson.interactive_checks),
            )
        )

    def complete_lesson(self, lesson_id: str) -> TeachingProgressView:
        """Mark a lesson complete only after all generated checks are answered."""
        view = self.get_lesson(lesson_id)
        return self._progress_view(
            self.progress_repository.complete(
                lesson_id=lesson_id,
                activity_count=len(view.lesson.interactive_checks),
            )
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
    def _normalize_source_ids(
        source_ids: object,
        selected_source_ids: set[str],
    ) -> list[str]:
        """Ensure every generated section/activity has traceable selected sources."""
        if not isinstance(source_ids, list):
            source_ids = []
        normalized = [str(source_id) for source_id in source_ids if str(source_id)]
        if any(source_id not in selected_source_ids for source_id in normalized):
            raise ProviderError(
                "Teaching Provider returned an unknown source reference",
                code="TEACHING_SOURCE_REFERENCE_INVALID",
                retryable=False,
            )
        return normalized or sorted(selected_source_ids)

    @classmethod
    def _normalize_provider_lesson(
        cls,
        content: object,
        *,
        topic: str,
        source_refs: list[tuple[str, str, str]],
    ) -> object:
        """Normalize common model variants before applying the strict lesson schema."""
        if not isinstance(content, dict):
            return content
        payload = dict(content)
        payload["schema_version"] = "teaching-lesson-v0.2"
        payload["topic"] = topic
        payload["sources"] = [
            {"document_id": document_id, "filename": filename, "excerpt": excerpt}
            for document_id, filename, excerpt in source_refs
        ]

        normalized_sections: list[dict[str, object]] = []
        raw_sections = payload.get("sections", [])
        section_types = ("concept", "mechanism", "boundary", "example")
        for index, raw_section in enumerate(raw_sections if isinstance(raw_sections, list) else []):
            if not isinstance(raw_section, dict):
                continue
            section = dict(raw_section)
            if "section_type" not in section and "type" in section:
                section["section_type"] = section.pop("type")
            elif "section_type" not in section and len(raw_sections) == len(section_types):
                # Some JSON responses omit the field while still following the four-section
                # order required by the prompt. Only infer this exact, constrained shape.
                section["section_type"] = section_types[index]
            normalized_sections.append(section)
        payload["sections"] = normalized_sections

        normalized_questions: list[str] = []
        for raw_question in payload.get("check_questions", []):
            if isinstance(raw_question, dict):
                prompt = raw_question.get("prompt") or raw_question.get("question")
                if prompt:
                    normalized_questions.append(str(prompt))
            elif raw_question:
                normalized_questions.append(str(raw_question))
        payload["check_questions"] = normalized_questions

        normalized_checks: list[dict[str, object]] = []
        for raw_check in payload.get("interactive_checks", []):
            if not isinstance(raw_check, dict):
                continue
            check = dict(raw_check)
            options = [str(option).strip() for option in check.get("options", []) if option]
            check["options"] = options
            check["correct_answer"] = cls._normalize_correct_answer(
                check.get("correct_answer"), options
            )
            normalized_checks.append(check)
        payload["interactive_checks"] = normalized_checks
        return payload

    @staticmethod
    def _normalize_correct_answer(answer: object, options: list[str]) -> object:
        """Map answer text, numeric indexes, or A/B/C labels onto option text."""
        if not options:
            return answer
        if isinstance(answer, int) and not isinstance(answer, bool):
            if 1 <= answer <= len(options):
                return options[answer - 1]
            if 0 <= answer < len(options):
                return options[answer]
            return answer
        if not isinstance(answer, str):
            return answer
        normalized = " ".join(answer.split())
        for option in options:
            if normalized == " ".join(option.split()):
                return option
        if normalized.isdigit():
            index = int(normalized)
            if 1 <= index <= len(options):
                return options[index - 1]
            if 0 <= index < len(options):
                return options[index]
        if len(normalized) >= 1 and normalized[0].upper() in "ABCDEFG":
            suffix = normalized[1:].lstrip(".、:：)） ")
            if not suffix:
                index = ord(normalized[0].upper()) - ord("A")
                if 0 <= index < len(options):
                    return options[index]
        return answer

    @staticmethod
    def _mentions_topic(lesson: TeachingLesson, topic: str) -> bool:
        """Reject obviously generic output while leaving semantic review to humans."""
        searchable = " ".join(
            [lesson.title, lesson.summary, *lesson.learning_objectives]
        ).casefold()
        return topic.casefold() in searchable

    def _view(
        self,
        record: LessonRecord,
        documents: tuple[DocumentView, ...] | list[DocumentView],
    ) -> TeachingLessonView:
        lesson = TeachingLesson.model_validate(json.loads(record.lesson_json))
        return TeachingLessonView(
            lesson_id=record.lesson_id,
            lesson=lesson,
            source_documents=tuple(documents),
            provider=record.provider,
            model_name=record.model_name,
            prompt_version=record.prompt_version,
            created_at=datetime.fromisoformat(record.created_at.replace("Z", "+00:00")),
            progress=self._progress_view(
                self.progress_repository.get_or_create(
                    record.lesson_id,
                    activity_count=len(lesson.interactive_checks),
                )
            ),
        )

    @staticmethod
    def _progress_view(record: LessonProgressRecord) -> TeachingProgressView:
        return TeachingProgressView(
            lesson_id=record.lesson_id,
            current_section=record.current_section,
            completed_activity_indexes=record.completed_activity_indexes,
            attempts=tuple(
                TeachingActivityAttemptView(
                    activity_index=attempt.activity_index,
                    selected_answer=attempt.selected_answer,
                    is_correct=attempt.is_correct,
                    created_at=datetime.fromisoformat(attempt.created_at.replace("Z", "+00:00")),
                )
                for attempt in record.attempts
            ),
            started_at=datetime.fromisoformat(record.started_at.replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(record.updated_at.replace("Z", "+00:00")),
            completed_at=(
                datetime.fromisoformat(record.completed_at.replace("Z", "+00:00"))
                if record.completed_at
                else None
            ),
        )
