"""Application service for source-grounded lesson generation."""

import io
import json
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from pypdf import PdfReader

from ai_growth_companion.application.document_library import (
    DocumentLibraryService,
    DocumentValidationError,
)
from ai_growth_companion.application.knowledge_extraction import (
    KnowledgeUnit,
    decode_text_content,
    extract_knowledge,
)
from ai_growth_companion.application.local_role_agents import LocalRoleAgentLayer
from ai_growth_companion.application.models import DocumentView
from ai_growth_companion.application.pdf_visual import (
    MAX_VISION_PAGES,
    render_pdf_pages,
    select_pdf_pages,
)
from ai_growth_companion.application.source_selector import (
    TopicSourceSelection,
    TopicSourceSelector,
)
from ai_growth_companion.application.topic_suggestions import (
    TopicSuggestionResult,
    TopicSuggestionService,
    source_signature,
)
from ai_growth_companion.application.translation_service import (
    TranslationService,
    build_bilingual_context,
)
from ai_growth_companion.domain.events import LOCAL_USER_ID
from ai_growth_companion.providers.base import (
    ProviderError,
    TeachingPageImage,
    TeachingPlanRequest,
    TeachingProvider,
    TeachingRequest,
    TeachingSourceUnit,
    TopicSuggestionProvider,
    TranslationProvider,
)
from ai_growth_companion.repositories.lesson_progress_repository import (
    LessonProgressRecord,
    SQLiteLessonProgressRepository,
)
from ai_growth_companion.repositories.lesson_repository import LessonRecord, SQLiteLessonRepository
from ai_growth_companion.schemas.teaching import TeachingLesson, TeachingPlan

_TOPIC_SAMPLE_CACHE: dict[tuple[str, str], str] = {}


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
    verified_lesson_count: int = 0
    partial_lesson_count: int = 0
    draft_lesson_count: int = 0


@dataclass(frozen=True)
class GroundingResolution:
    """Best-effort source reconciliation result kept with a saved lesson."""

    payload: dict[str, object]
    status: str
    issues: tuple[str, ...]


class TeachingService:
    """Extract selected materials, generate a validated lesson, and persist it."""

    MAX_SOURCE_CONTEXT_CHARS = 60_000
    MAX_UNITS_PER_DOCUMENT = 12
    MAX_TOPIC_SAMPLE_CHARS = 6_000
    MAX_TOPIC_CONTEXT_CHARS = 50_000
    MAX_TOPIC_DOCUMENT_SAMPLES = 8

    def __init__(
        self,
        document_library: DocumentLibraryService,
        repository: SQLiteLessonRepository,
        provider: TeachingProvider,
        progress_repository: SQLiteLessonProgressRepository,
        translation_provider: TranslationProvider | None = None,
        topic_provider: TopicSuggestionProvider | None = None,
        role_agents: LocalRoleAgentLayer | None = None,
    ) -> None:
        self.document_library = document_library
        self.repository = repository
        self.provider = provider
        self.progress_repository = progress_repository
        self.source_selector = TopicSourceSelector(document_library)
        self.translation_service = TranslationService(
            translation_provider,
            cache_root=document_library.storage_root.parent / "translations",
        )
        self.topic_service = TopicSuggestionService(
            topic_provider,
            cache_root=document_library.storage_root.parent / "topic_suggestions",
        )
        self.role_agents = role_agents or LocalRoleAgentLayer()

    def schedule_translation(self, document_id: str, *, request_id: str | None = None) -> bool:
        """Start upload-time translation in the background when the source is English."""
        if self.translation_service.provider is None:
            translation_queued = False
        else:
            document, content = self.document_library.read(document_id)
            try:
                extracted = extract_knowledge(document.filename, content)
            except DocumentValidationError:
                # Scanned/garbled PDFs are handled by the explicit visual path instead.
                extracted = None
            if extracted is None:
                translation_queued = False
            else:
                source_units = tuple(
                    TeachingSourceUnit(
                        document_id=document.document_id,
                        filename=document.filename,
                        page_number=unit.page_number,
                        text=unit.text,
                        quality=unit.quality,
                    )
                    for unit in extracted.units
                )
                translation_queued = self.translation_service.schedule_units(
                    source_units,
                    source_sha256=document.sha256,
                    request_id=request_id or f"upload:{document.document_id}",
                )
        # Topic extraction is independent of the translation cache. This means a
        # user can choose a topic while the optional translation worker is still
        # running; the final lesson still enforces Chinese output.
        self.get_topic_suggestions((document_id,), request_id=request_id)
        return translation_queued

    def get_topic_suggestions(
        self,
        document_ids: tuple[str, ...],
        *,
        request_id: str | None = None,
    ) -> TopicSuggestionResult:
        """Return cached AI topics or queue analysis for the selected materials."""
        if not document_ids:
            return TopicSuggestionResult(suggestions=(), status="unavailable")
        labels: list[tuple[str, str]] = []
        signatures: list[tuple[str, str, str]] = []
        sampled_parts: list[str] = []
        filename_parts: list[str] = []
        sample_indexes = self._topic_sample_indexes(len(document_ids))
        for index, document_id in enumerate(document_ids):
            try:
                document, content = self.document_library.read(document_id)
            except (DocumentValidationError, LookupError):
                continue
            labels.append((document.document_id, document.filename))
            signatures.append((document.document_id, document.filename, document.sha256))
            # Topic choices are an index operation, not lesson generation.  Read
            # only a small representative sample so opening the teaching page does
            # not walk every page in a large PDF.  The full, page-aware extraction
            # remains in generate_lesson where it is needed for source evidence.
            cache_key = (document.document_id, document.sha256)
            sample = _TOPIC_SAMPLE_CACHE.get(cache_key, "")
            if index in sample_indexes and cache_key not in _TOPIC_SAMPLE_CACHE:
                sample = self._topic_sample(document.filename, content)
                _TOPIC_SAMPLE_CACHE[cache_key] = sample
            if sample:
                sampled_parts.append(f"【资料：{document.filename}】\n{sample}")
            else:
                filename_parts.append(f"【资料标题：{document.filename}】")
        if not labels:
            return TopicSuggestionResult(suggestions=(), status="unavailable")
        text = "\n\n".join(sampled_parts + filename_parts)[: self.MAX_TOPIC_CONTEXT_CHARS]
        return self.topic_service.get_or_schedule(
            source_text=text,
            source_labels=tuple(labels),
            source_signature=source_signature(tuple(signatures)),
            request_id=request_id or "topics:background",
        )

    @classmethod
    def _topic_sample_indexes(cls, document_count: int) -> set[int]:
        """Choose evenly spaced chunks so a large library stays responsive."""
        if document_count <= cls.MAX_TOPIC_DOCUMENT_SAMPLES:
            return set(range(document_count))
        last_index = document_count - 1
        return {
            round(index * last_index / (cls.MAX_TOPIC_DOCUMENT_SAMPLES - 1))
            for index in range(cls.MAX_TOPIC_DOCUMENT_SAMPLES)
        }

    @classmethod
    def _topic_sample(cls, filename: str, content: bytes) -> str:
        """Extract a bounded representative sample for fast topic analysis.

        This intentionally does not perform full page extraction or translation.
        Topic analysis runs in the background and only needs enough context to
        propose learner-facing choices; lesson generation later performs the
        authoritative extraction and keeps page-level evidence.
        """
        extension = Path(filename).suffix.casefold()
        if extension in {".md", ".markdown", ".txt"}:
            try:
                text = decode_text_content(content)
            except DocumentValidationError:
                return ""
            return cls._bounded_topic_text(text, cls.MAX_TOPIC_SAMPLE_CHARS)
        if extension != ".pdf":
            return ""
        try:
            reader = PdfReader(io.BytesIO(content))
            page_count = len(reader.pages)
            if page_count == 0:
                return ""
            # The first page usually contains the chapter/section heading.  One
            # page per uploaded chunk keeps this index operation fast even for a
            # multi-hundred-page textbook; the lesson path still reads every page
            # when it needs authoritative evidence.
            indexes = (0,) if page_count > 8 else tuple(range(page_count))
            text = "\n\n".join(reader.pages[index].extract_text() or "" for index in indexes)
        except Exception:
            return ""
        return cls._bounded_topic_text(text, cls.MAX_TOPIC_SAMPLE_CHARS)

    @staticmethod
    def _bounded_topic_text(text: str, limit: int = 6_000) -> str:
        normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
        if len(normalized) <= limit:
            return normalized
        # Keep both the beginning (usually headings/definitions) and the ending
        # (often summary/chapters) rather than blindly truncating at the front.
        head = int(limit * 0.7)
        tail = limit - head
        return f"{normalized[:head]}\n…\n{normalized[-tail:]}"

    def recommend_sources(
        self,
        *,
        topic: str,
        document_ids: tuple[str, ...] | None = None,
        limit: int = 3,
    ) -> TopicSourceSelection:
        """Recommend relevant chunks while keeping manual selection available."""
        return self.source_selector.recommend(
            topic=topic,
            document_ids=document_ids,
            limit=limit,
        )

    def generate_lesson(
        self,
        *,
        topic: str,
        document_ids: tuple[str, ...],
        learning_goal: str | None = None,
        learner_level: str | None = None,
        request_id: str,
        use_vision: bool = False,
    ) -> TeachingLessonView:
        normalized_topic = topic.strip()
        if not normalized_topic:
            raise TeachingInputError("请填写要学习的知识主题")
        if not document_ids:
            raise TeachingInputError("请至少选择一份知识资料")
        if use_vision and not self.provider.supports_vision:
            raise TeachingInputError("当前 Provider 不支持视觉读取，请切换到 DeepSeek 教学模式")

        source_documents: list[DocumentView] = []
        source_refs: list[tuple[str, str, str]] = []
        source_units: list[TeachingSourceUnit] = []
        source_hashes: dict[str, str] = {}
        visual_pages: list[TeachingPageImage] = []
        for document_id in document_ids:
            document, content = self.document_library.read(document_id)
            extracted = None
            try:
                extracted = extract_knowledge(document.filename, content)
            except DocumentValidationError:
                if not use_vision or document.extension != ".pdf":
                    raise
            source_documents.append(document)
            source_hashes[document.document_id] = document.sha256
            source_excerpt = (
                " ".join(extracted.text.split())[:1_800]
                if extracted is not None
                else "原始 PDF 页面将通过视觉输入读取。"
            )
            source_refs.append((document.document_id, document.filename, source_excerpt))
            if extracted is not None:
                selected_units = self._select_source_units(
                    normalized_topic,
                    extracted.units,
                    limit=self.MAX_UNITS_PER_DOCUMENT,
                )
                if not selected_units:
                    selected_units = (KnowledgeUnit(None, extracted.text[:12_000], "clear"),)
                for unit in selected_units:
                    source_unit = TeachingSourceUnit(
                        document_id=document.document_id,
                        filename=document.filename,
                        page_number=unit.page_number,
                        text=unit.text,
                        quality=unit.quality,
                    )
                    source_units.append(source_unit)
            if use_vision and document.extension == ".pdf":
                remaining = MAX_VISION_PAGES - len(visual_pages)
                if remaining > 0:
                    page_numbers = select_pdf_pages(
                        content,
                        topic=normalized_topic,
                        max_pages=remaining,
                    )
                    visual_pages.extend(
                        render_pdf_pages(
                            content,
                            document_id=document.document_id,
                            filename=document.filename,
                            page_numbers=page_numbers,
                        )
                    )

        if use_vision and not visual_pages:
            raise TeachingInputError("视觉读取模式至少需要选择一份 PDF 资料")

        translation_result = self.translation_service.prepare_units(
            tuple(source_units),
            source_hashes=source_hashes,
            request_id=f"{request_id}:translation",
        )
        source_units = list(translation_result.units)
        source_text = build_bilingual_context(tuple(source_units))[: self.MAX_SOURCE_CONTEXT_CHARS]
        teaching_plan = self.role_agents.plan_lesson(
            TeachingPlanRequest(
                topic=normalized_topic,
                source_text=source_text,
                source_units=tuple(source_units),
                source_document_ids=tuple(document_id for document_id, _, _ in source_refs),
                learning_goal=learning_goal.strip() if learning_goal else None,
                learner_level=learner_level,
                output_language="zh-CN",
            ),
            request_id=f"{request_id}:planner",
        )
        teaching_request = TeachingRequest(
            topic=normalized_topic,
            source_text=source_text,
            sources=tuple(source_refs),
            learning_goal=learning_goal.strip() if learning_goal else None,
            learner_level=learner_level,
            output_language="zh-CN",
            source_units=tuple(source_units),
            visual_pages=tuple(visual_pages),
            teaching_plan=teaching_plan,
        )
        selected_source_ids = {document_id for document_id, _, _ in source_refs}
        response = None
        fallback_reason: str | None = None
        try:
            response = self.provider.generate_lesson(teaching_request, request_id=request_id)
        except ProviderError as error:
            # A provider outage should not erase the learner's requested study session.  Keep
            # the failure code in the saved lesson and build a transparent local draft instead.
            fallback_reason = f"模型生成未完成（{error.code}），已保存资料导读草稿"
        except Exception:
            # Provider adapters should normally translate failures into ProviderError, but an
            # unexpected adapter/runtime exception must not strand the learner without a course.
            fallback_reason = "模型生成出现未预期错误，已保存资料导读草稿"

        lesson_payload: dict[str, object]
        if response is None:
            lesson_payload = self._build_fallback_lesson(
                normalized_topic,
                source_refs=source_refs,
                source_text=source_text,
                source_units=source_units,
                reason=fallback_reason or "模型没有返回内容，已保存资料导读草稿",
            )
        else:
            normalized_content = self._normalize_provider_lesson(
                response.content,
                topic=normalized_topic,
                source_refs=source_refs,
            )
            if isinstance(normalized_content, dict):
                normalized_content = self._complete_incomplete_lesson(
                    teaching_request,
                    normalized_content,
                    request_id=request_id,
                    source_refs=source_refs,
                )
            lesson_payload = (
                dict(normalized_content) if isinstance(normalized_content, dict) else {}
            )
            lesson_payload = self._normalize_lesson_payload(
                lesson_payload,
                topic=normalized_topic,
                source_refs=source_refs,
                selected_source_ids=selected_source_ids,
            )

            # Invalid structure or obvious topic drift is converted into a usable, clearly
            # labelled extractive draft rather than blocking the whole generation flow.
            try:
                candidate = TeachingLesson.model_validate(lesson_payload)
                if not candidate.interactive_checks:
                    raise ValueError("no interactive checks")
                if not self._has_chinese_prose(candidate):
                    repaired_language = self._repair_lesson_language(
                        teaching_request,
                        lesson_payload,
                        request_id=request_id,
                        source_refs=source_refs,
                    )
                    if repaired_language is not None:
                        lesson_payload = self._normalize_lesson_payload(
                            repaired_language,
                            topic=normalized_topic,
                            source_refs=source_refs,
                            selected_source_ids=selected_source_ids,
                        )
                        candidate = TeachingLesson.model_validate(lesson_payload)
                    if not self._has_chinese_prose(candidate):
                        raise ValueError("lesson prose is not Chinese")
                if not self._mentions_topic(candidate, normalized_topic):
                    raise ValueError("content unrelated to requested topic")
            except Exception:
                fallback_reason = "模型返回内容不完整或跑题，已保存资料导读草稿"
                lesson_payload = self._build_fallback_lesson(
                    normalized_topic,
                    source_refs=source_refs,
                    source_text=source_text,
                    source_units=source_units,
                    reason=fallback_reason,
                )

        lesson_payload = self._normalize_lesson_payload(
            lesson_payload,
            topic=normalized_topic,
            source_refs=source_refs,
            selected_source_ids=selected_source_ids,
        )
        lesson_payload = self._attach_teaching_plan(lesson_payload, teaching_plan)
        lesson_payload = self._repair_missing_evidence(
            teaching_request,
            lesson_payload,
            request_id=request_id,
        )
        resolution = self._reconcile_source_grounding(
            lesson_payload,
            topic=normalized_topic,
            source_refs=source_refs,
            source_text=source_text,
            source_units=source_units,
            visual_pages=visual_pages,
            selected_source_ids=selected_source_ids,
            draft=bool(fallback_reason),
        )
        lesson_payload = resolution.payload
        lesson_payload.update(
            {
                "topic": normalized_topic,
                "sources": [
                    {"document_id": document_id, "filename": filename, "excerpt": excerpt}
                    for document_id, filename, excerpt in source_refs
                ],
                "grounding_status": resolution.status,
                "grounding_issues": list(resolution.issues),
                "translation_status": translation_result.status,
                "translation_model": translation_result.model_name,
                "translated_unit_count": translation_result.translated_unit_count,
                "translation_failed_unit_count": translation_result.failed_unit_count,
            }
        )
        lesson = TeachingLesson.model_validate(lesson_payload)
        try:
            self._validate_lesson_quality(lesson)
        except ProviderError:
            # Keep the same no-blocking contract for short/garbled model output.  The fallback
            # is deterministic and passes the conventional lesson shape checks.
            lesson_payload = self._build_fallback_lesson(
                normalized_topic,
                source_refs=source_refs,
                source_text=source_text,
                source_units=source_units,
                reason="模型内容质量不足，已保存资料导读草稿",
            )
            lesson_payload = self._attach_teaching_plan(lesson_payload, teaching_plan)
            resolution = self._reconcile_source_grounding(
                lesson_payload,
                topic=normalized_topic,
                source_refs=source_refs,
                source_text=source_text,
                source_units=source_units,
                visual_pages=visual_pages,
                selected_source_ids=selected_source_ids,
                draft=True,
            )
            lesson_payload = resolution.payload
            lesson_payload.update(
                {
                    "topic": normalized_topic,
                    "sources": [
                        {"document_id": document_id, "filename": filename, "excerpt": excerpt}
                        for document_id, filename, excerpt in source_refs
                    ],
                    "grounding_status": "draft",
                    "grounding_issues": list(
                        dict.fromkeys(
                            (*resolution.issues, "模型内容质量不足，已切换为资料导读草稿")
                        )
                    ),
                    "translation_status": translation_result.status,
                    "translation_model": translation_result.model_name,
                    "translated_unit_count": translation_result.translated_unit_count,
                    "translation_failed_unit_count": translation_result.failed_unit_count,
                }
            )
            lesson = TeachingLesson.model_validate(lesson_payload)

        lesson_id = str(uuid4())
        metadata = response.metadata if response is not None else None
        record = self.repository.create(
            lesson_id=lesson_id,
            topic=normalized_topic,
            source_document_ids=tuple(document_ids),
            lesson_json=lesson.model_dump_json(),
            provider=metadata.provider if metadata is not None else self.provider.provider_name,
            model_name=metadata.model if metadata is not None else self.provider.model_name,
            model_revision=(metadata.model_revision if metadata is not None else None),
            prompt_version=(
                metadata.prompt_version if metadata is not None else "teaching-fallback-v0.1"
            ),
            schema_version=(
                metadata.schema_version if metadata is not None else "teaching-lesson-v0.2"
            ),
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
        verified_lesson_count = 0
        partial_lesson_count = 0
        draft_lesson_count = 0
        for lesson in lessons:
            total_activity_count += len(lesson.lesson.interactive_checks)
            completed_lesson_count += lesson.progress.completed_at is not None
            source_document_ids.update(source.document_id for source in lesson.lesson.sources)
            if lesson.lesson.grounding_status == "verified":
                verified_lesson_count += 1
            elif lesson.lesson.grounding_status == "draft":
                draft_lesson_count += 1
            else:
                partial_lesson_count += 1
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
            verified_lesson_count=verified_lesson_count,
            partial_lesson_count=partial_lesson_count,
            draft_lesson_count=draft_lesson_count,
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

    @classmethod
    def _select_source_units(
        cls,
        topic: str,
        units: tuple[KnowledgeUnit, ...],
        *,
        limit: int,
    ) -> tuple[KnowledgeUnit, ...]:
        """Select topic-relevant pages while keeping neighboring context for definitions."""
        readable = [unit for unit in units if unit.text.strip()]
        if not readable:
            return ()
        terms = cls._topic_terms(topic)
        scores = [
            sum(unit.text.casefold().count(term.casefold()) for term in terms) for unit in readable
        ]
        ranked_indexes = [
            index
            for index, score in sorted(enumerate(scores), key=lambda item: (-item[1], item[0]))[
                : max(1, limit // 2)
            ]
            if score > 0
        ]
        if ranked_indexes:
            selected_indexes: set[int] = set()
            for index in ranked_indexes:
                selected_indexes.update(range(max(0, index - 1), min(len(readable), index + 2)))
            candidates = [readable[index] for index in sorted(selected_indexes)]
        else:
            candidates = readable[:limit]

        selected: list[KnowledgeUnit] = []
        total_chars = 0
        for unit in candidates:
            if len(selected) >= limit:
                break
            remaining = 18_000 - total_chars
            if remaining <= 0:
                break
            text = unit.text[:remaining]
            selected.append(KnowledgeUnit(unit.page_number, text, unit.quality))
            total_chars += len(text)
        return tuple(selected)

    @staticmethod
    def _topic_terms(topic: str) -> tuple[str, ...]:
        normalized = topic.casefold().strip()
        aliases: dict[str, tuple[str, ...]] = {
            "极限": ("limit", "limits"),
            "函数极限": ("limit", "limits", "function", "functions"),
            "导数": ("derivative", "derivatives"),
            "切线": ("tangent", "tangent line", "secant"),
            "割线": ("secant", "secant line", "tangent"),
            "瞬时变化率": ("instantaneous", "rate of change", "derivative"),
            "积分": ("integral", "integrals"),
            "线性代数": ("linear algebra", "matrix", "vector"),
        }
        chunks = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", normalized)
        cjk_bigrams = [
            chunk[index : index + 2]
            for chunk in chunks
            if re.fullmatch(r"[\u4e00-\u9fff]+", chunk)
            for index in range(len(chunk) - 1)
        ]
        return tuple(
            dict.fromkeys((normalized, *chunks, *cjk_bigrams, *aliases.get(normalized, ())))
        )

    @classmethod
    def _normalize_lesson_payload(
        cls,
        payload: dict[str, object],
        *,
        topic: str,
        source_refs: list[tuple[str, str, str]],
        selected_source_ids: set[str],
    ) -> dict[str, object]:
        """Normalize model fields before Pydantic validation can reject recoverable variants."""
        normalized = dict(payload)
        normalized["schema_version"] = "teaching-lesson-v0.2"
        normalized["topic"] = topic
        normalized["sources"] = [
            {"document_id": document_id, "filename": filename, "excerpt": excerpt}
            for document_id, filename, excerpt in source_refs
        ]
        sections: list[dict[str, object]] = []
        raw_sections = normalized.get("sections", [])
        for raw_section in raw_sections if isinstance(raw_sections, list) else []:
            if not isinstance(raw_section, dict):
                continue
            section = dict(raw_section)
            section["source_document_ids"] = cls._normalize_source_ids(
                section.get("source_document_ids", []), selected_source_ids
            )
            section["evidence"] = cls._normalize_evidence(
                section.get("evidence", section.get("source_evidence", []))
            )
            sections.append(section)
        normalized["sections"] = sections

        checks: list[dict[str, object]] = []
        raw_checks = normalized.get("interactive_checks", [])
        for raw_check in raw_checks if isinstance(raw_checks, list) else []:
            if not isinstance(raw_check, dict):
                continue
            check = dict(raw_check)
            check["source_document_ids"] = cls._normalize_source_ids(
                check.get("source_document_ids", []), selected_source_ids
            )
            raw_options = check.get("options", [])
            options = (
                [str(option).strip() for option in raw_options if option]
                if isinstance(raw_options, list)
                else []
            )
            check["options"] = options
            check["correct_answer"] = cls._normalize_correct_answer(
                check.get("correct_answer"), options
            )
            check["evidence"] = cls._normalize_evidence(
                check.get("evidence", check.get("source_evidence", []))
            )
            checks.append(check)
        normalized["interactive_checks"] = checks
        return normalized

    @staticmethod
    def _attach_teaching_plan(
        payload: dict[str, object], teaching_plan: TeachingPlan
    ) -> dict[str, object]:
        """Persist the validated route regardless of which prose path was used."""
        normalized = dict(payload)
        normalized["teaching_plan"] = teaching_plan.model_dump(mode="json")
        node_by_id = {node.node_id: node for node in teaching_plan.nodes}
        sections = normalized.get("sections")
        if isinstance(sections, list):
            enriched_sections: list[object] = []
            for section in sections:
                if not isinstance(section, dict):
                    enriched_sections.append(section)
                    continue
                enriched = dict(section)
                section_type = str(enriched.get("section_type", ""))
                node = node_by_id.get(section_type)
                if node is not None:
                    enriched.setdefault("why_it_matters", node.purpose)
                    enriched.setdefault("discovery_path", node.discovery_prompt)
                    enriched.setdefault("prerequisite_ids", node.prerequisites)
                enriched_sections.append(enriched)
            normalized["sections"] = enriched_sections
        return normalized

    @classmethod
    def _build_fallback_lesson(
        cls,
        topic: str,
        *,
        source_refs: list[tuple[str, str, str]],
        source_text: str,
        source_units: list[TeachingSourceUnit],
        reason: str,
    ) -> dict[str, object]:
        """Build a usable, honest extractive lesson when a model result is unusable."""
        source_ids = [document_id for document_id, _, _ in source_refs]
        unit = next((item for item in source_units if item.text.strip()), None)
        fact = " ".join((unit.text if unit else source_text).split())[:500]
        if not fact:
            fact = "当前资料暂未提取出可复制文字，先建立学习框架，再逐步补充原文证据。"
        evidence: list[dict[str, object]] = []
        if unit and len("".join(unit.text.split())) >= 4:
            evidence.append(
                {
                    "document_id": unit.document_id,
                    "page_number": unit.page_number,
                    "quote": " ".join(unit.text.split())[:800],
                }
            )
        summary = (
            f"这是一份围绕“{topic}”的资料导读草稿。系统先把已读取的原文整理成学习顺序，"
            f"再由你通过例子和小测确认理解。当前状态：{reason}。资料摘录：{fact[:220]}"
        )
        section_specs = (
            (
                "concept",
                "先认识核心概念",
                "先从资料摘录出发，用自己的话说明核心概念是什么、解决什么问题。",
            ),
            (
                "mechanism",
                "再梳理运作过程",
                "把资料中的定义、步骤或变化过程按顺序整理出来，说明每一步为什么发生。",
            ),
            (
                "boundary",
                "检查适用条件",
                "学习一个结论时，同时检查它依赖的条件、容易混淆的情况，以及什么时候不能直接使用。",
            ),
            (
                "example",
                "用新例子验证",
                "最后用一个资料之外但结构相近的新例子复述概念、过程和边界，检查是否真的理解。",
            ),
        )
        sections = []
        for section_type, title, guidance in section_specs:
            sections.append(
                {
                    "section_type": section_type,
                    "title": title,
                    "explanation": f"{guidance}\n\n资料中的可用摘录是：{fact}",
                    "key_points": ["资料中的关键表述", "需要解释的原因", "需要自己验证的地方"],
                    "example": f"请围绕“{topic}”写一个具体例子，并说明它如何对应资料摘录。",
                    "source_document_ids": source_ids,
                    "evidence": [dict(item) for item in evidence],
                }
            )
        check_evidence = [dict(item) for item in evidence]
        return {
            "schema_version": "teaching-lesson-v0.2",
            "topic": topic,
            "title": f"{topic}：资料导读草稿",
            "summary": summary,
            "learning_objectives": [
                f"用自己的话说明 {topic} 的核心含义",
                f"根据资料解释 {topic} 的运作过程和适用条件",
                f"用一个新例子检验是否真正理解 {topic}",
            ],
            "sections": sections,
            "check_questions": [
                f"如果向别人解释 {topic}，你会先讲资料中的哪一个关键点？为什么？",
                f"面对一个新例子时，如何检查 {topic} 的适用条件？",
            ],
            "interactive_checks": [
                {
                    "prompt": f"学习 {topic} 时，第一步更应该做什么？",
                    "options": ["先理解概念和条件，再看例子", "只背最后一句结论"],
                    "correct_answer": "先理解概念和条件，再看例子",
                    "explanation": "先理解概念和条件，才能判断知识能否迁移到新例子。",
                    "source_document_ids": source_ids,
                    "evidence": check_evidence,
                },
                {
                    "prompt": f"如何确认自己真的理解了 {topic}？",
                    "options": ["用自己的话解释并完成新例子", "只重复资料原句"],
                    "correct_answer": "用自己的话解释并完成新例子",
                    "explanation": "解释和迁移到新例子可以暴露只记住句子却没有理解的问题。",
                    "source_document_ids": source_ids,
                    "evidence": [dict(item) for item in check_evidence],
                },
            ],
            "sources": [
                {"document_id": document_id, "filename": filename, "excerpt": excerpt}
                for document_id, filename, excerpt in source_refs
            ],
            "grounding_status": "draft",
            "grounding_issues": [reason],
        }

    @classmethod
    def _reconcile_source_grounding(
        cls,
        payload: dict[str, object],
        *,
        topic: str,
        source_refs: list[tuple[str, str, str]],
        source_text: str,
        source_units: list[TeachingSourceUnit],
        visual_pages: list[TeachingPageImage],
        selected_source_ids: set[str],
        draft: bool,
    ) -> GroundingResolution:
        """Repair recoverable evidence errors and record unresolved ones instead of rejecting."""
        del topic
        normalized = dict(payload)
        existing_issues = normalized.get("grounding_issues", [])
        issues: list[str] = (
            [str(issue) for issue in existing_issues if issue]
            if isinstance(existing_issues, list)
            else []
        )
        repaired = False
        allowed_pages = {(page.document_id, page.page_number) for page in visual_pages}
        allowed_text_pages = {
            (unit.document_id, unit.page_number)
            for unit in source_units
            if unit.page_number is not None
        }
        filenames = {document_id: filename for document_id, filename, _ in source_refs}
        ordered_source_ids = sorted(selected_source_ids)

        for key in ("sections", "interactive_checks"):
            items = normalized.get(key)
            if not isinstance(items, list):
                continue
            updated_items: list[object] = []
            for item in items:
                if not isinstance(item, dict):
                    updated_items.append(item)
                    issues.append(f"{key} 中存在无法解析的条目")
                    continue
                current = dict(item)
                raw_evidence = cls._normalize_evidence(current.get("evidence", []))
                if not raw_evidence:
                    fallback = cls._fallback_evidence(source_units, visual_pages)
                    if fallback is not None:
                        raw_evidence = [fallback]
                        repaired = True
                    else:
                        issues.append(f"{key} 有条目暂时没有可核对的原文证据")

                resolved: list[dict[str, object]] = []
                for evidence in raw_evidence:
                    quote = str(evidence.get("quote", "")).strip()
                    matched_unit = cls._find_unit_for_quote(quote, source_units)
                    document_id = str(evidence.get("document_id", "")).strip()
                    if document_id not in selected_source_ids:
                        if matched_unit is not None:
                            document_id = matched_unit.document_id
                            repaired = True
                        elif len(ordered_source_ids) == 1:
                            document_id = ordered_source_ids[0]
                            repaired = True
                        else:
                            document_id = (
                                ordered_source_ids[0] if ordered_source_ids else document_id
                            )
                            issues.append("证据来源无法唯一对应到选中的资料")
                    if not document_id:
                        issues.append("证据缺少资料来源")
                        continue

                    if len("".join(quote.split())) < 4 and matched_unit is not None:
                        quote = " ".join(matched_unit.text.split())[:800]
                        repaired = True
                    if len("".join(quote.split())) < 4:
                        issues.append("证据原文过短，已保留课程但暂不展示该条证据")
                        continue
                    if (
                        not visual_pages
                        and source_text
                        and matched_unit is None
                        and not cls._quote_supported(quote, source_text)
                    ):
                        issues.append("部分教学引文暂时无法在原文中核对")

                    raw_page = cls._parse_page_number(evidence.get("page_number"))
                    filename = filenames.get(document_id, "")
                    page_number = cls._resolve_evidence_page(
                        document_id=document_id,
                        filename=filename,
                        raw_page=raw_page,
                        matched_unit=matched_unit,
                        allowed_pages=allowed_pages,
                        allowed_text_pages=allowed_text_pages,
                        visual_pages=visual_pages,
                    )
                    if raw_page != page_number:
                        repaired = True
                    if visual_pages and page_number is None:
                        issues.append("视觉证据页码无法唯一核对，已保存课程并标记为部分核验")
                    elif not visual_pages and raw_page is not None and page_number is None:
                        issues.append("文字证据页码无法核对，已保存课程并标记为部分核验")
                    resolved.append(
                        {
                            "document_id": document_id,
                            "page_number": page_number,
                            "quote": quote[:800],
                        }
                    )
                current["evidence"] = resolved
                updated_items.append(current)
            normalized[key] = updated_items

        unique_issues = tuple(dict.fromkeys(issues))
        status = (
            "draft"
            if draft
            else "partial"
            if unique_issues
            else "repaired"
            if repaired
            else "verified"
        )
        return GroundingResolution(normalized, status, unique_issues)

    @staticmethod
    def _fallback_evidence(
        source_units: list[TeachingSourceUnit], visual_pages: list[TeachingPageImage]
    ) -> dict[str, object] | None:
        for unit in source_units:
            quote = " ".join(unit.text.split())[:800]
            if len("".join(quote.split())) >= 4:
                page_number = unit.page_number
                if visual_pages and (unit.document_id, page_number) not in {
                    (page.document_id, page.page_number) for page in visual_pages
                }:
                    page_number = None
                return {
                    "document_id": unit.document_id,
                    "page_number": page_number,
                    "quote": quote,
                }
        return None

    @classmethod
    def _find_unit_for_quote(
        cls, quote: str, source_units: list[TeachingSourceUnit]
    ) -> TeachingSourceUnit | None:
        if len("".join(quote.split())) < 4:
            return None
        for unit in source_units:
            if cls._quote_supported(quote, unit.text):
                return unit
        quote_key = cls._quote_key(quote)
        if len(quote_key) < 12:
            return None
        for unit in source_units:
            unit_key = cls._quote_key(unit.text)
            if quote_key[: min(40, len(quote_key))] in unit_key:
                return unit
        return None

    @staticmethod
    def _parse_page_number(value: object) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value if value > 0 else None
        if isinstance(value, float) and value.is_integer() and value > 0:
            return int(value)
        if isinstance(value, str):
            match = re.search(r"(?<!\d)(\d{1,5})(?!\d)", value)
            if match:
                page = int(match.group(1))
                return page if page > 0 else None
        return None

    @staticmethod
    def _document_page_range(filename: str) -> tuple[int, int] | None:
        match = re.search(r"_pages_(\d+)-(\d+)(?:\.[^.]+)?$", filename, flags=re.IGNORECASE)
        if match is None:
            return None
        start, end = int(match.group(1)), int(match.group(2))
        return (start, end) if start <= end else None

    @classmethod
    def _resolve_evidence_page(
        cls,
        *,
        document_id: str,
        filename: str,
        raw_page: int | None,
        matched_unit: TeachingSourceUnit | None,
        allowed_pages: set[tuple[str, int]],
        allowed_text_pages: set[tuple[str, int]],
        visual_pages: list[TeachingPageImage],
    ) -> int | None:
        allowed = allowed_pages if visual_pages else allowed_text_pages
        if (
            matched_unit is not None
            and matched_unit.page_number is not None
            and (document_id, matched_unit.page_number) in allowed
        ):
            return matched_unit.page_number

        candidates: list[int] = []
        if raw_page is not None:
            candidates.append(raw_page)
            candidates.extend((raw_page + 1, raw_page - 1))
            page_range = cls._document_page_range(filename)
            if page_range is not None:
                start, end = page_range
                if start <= raw_page <= end:
                    candidates.append(raw_page - start + 1)
        for candidate in dict.fromkeys(candidates):
            if candidate > 0 and (document_id, candidate) in allowed:
                return candidate

        if visual_pages:
            document_pages = [
                page.page_number for page in visual_pages if page.document_id == document_id
            ]
            if len(document_pages) == 1:
                return document_pages[0]
        return None

    def _repair_missing_evidence(
        self,
        request: TeachingRequest,
        lesson_payload: dict[str, object],
        *,
        request_id: str,
    ) -> dict[str, object]:
        """Run one bounded evidence-only repair for Providers that explicitly support it."""
        if not self._has_missing_evidence(lesson_payload, request=request):
            return lesson_payload
        repair = getattr(self.provider, "repair_lesson_evidence", None)
        if not callable(repair):
            return lesson_payload
        try:
            response = repair(
                request,
                lesson_payload,
                request_id=f"{request_id}:evidence-repair",
            )
        except Exception:
            # Keep the original content and let deterministic reconciliation mark any gap.
            return lesson_payload
        repaired = response.content
        if not isinstance(repaired, dict):
            return lesson_payload

        merged = dict(lesson_payload)
        for key in ("sections", "interactive_checks"):
            originals = merged.get(key)
            candidates = repaired.get(key)
            if not isinstance(originals, list) or not isinstance(candidates, list):
                continue
            updated: list[object] = []
            for index, original in enumerate(originals):
                if not isinstance(original, dict):
                    updated.append(original)
                    continue
                item = dict(original)
                existing = self._normalize_evidence(item.get("evidence", []))
                if index < len(candidates) and isinstance(candidates[index], dict):
                    candidate_evidence = self._normalize_evidence(
                        candidates[index].get("evidence", [])
                    )
                else:
                    candidate_evidence = []
                needs_repair = not existing or self._evidence_needs_repair(existing, request)
                if needs_repair and candidate_evidence:
                    item["evidence"] = self._normalize_evidence(candidate_evidence)
                updated.append(item)
            merged[key] = updated
        return merged

    def _complete_incomplete_lesson(
        self,
        request: TeachingRequest,
        lesson_payload: dict[str, object],
        *,
        request_id: str,
        source_refs: list[tuple[str, str, str]],
    ) -> dict[str, object]:
        """Complete an abbreviated real-Provider response with one bounded follow-up call."""
        if not self._has_incomplete_structure(lesson_payload):
            return lesson_payload
        complete = getattr(self.provider, "complete_lesson", None)
        if not callable(complete):
            return lesson_payload
        try:
            response = complete(
                request,
                lesson_payload,
                request_id=f"{request_id}:lesson-completion",
            )
        except Exception:
            return lesson_payload
        candidate = response.content
        if not isinstance(candidate, dict):
            return lesson_payload
        normalized_candidate = self._normalize_provider_lesson(
            candidate,
            topic=request.topic,
            source_refs=source_refs,
        )
        if not isinstance(normalized_candidate, dict):
            return lesson_payload

        merged = dict(lesson_payload)
        for key in ("sections", "interactive_checks"):
            value = normalized_candidate.get(key)
            if isinstance(value, list) and len(value) >= (4 if key == "sections" else 2):
                merged[key] = value
        for key in ("summary", "learning_objectives", "check_questions"):
            current = merged.get(key)
            candidate_value = normalized_candidate.get(key)
            if key == "summary" and isinstance(current, str) and len(current.strip()) >= 30:
                continue
            if key != "summary" and isinstance(current, list) and len(current) >= 2:
                continue
            if candidate_value:
                merged[key] = candidate_value
        return merged

    def _repair_lesson_language(
        self,
        request: TeachingRequest,
        lesson_payload: dict[str, object],
        *,
        request_id: str,
        source_refs: list[tuple[str, str, str]],
    ) -> dict[str, object] | None:
        """Ask a capable Provider for one bounded Chinese-output repair."""
        complete = getattr(self.provider, "complete_lesson", None)
        if not callable(complete):
            return None
        try:
            response = complete(
                request,
                lesson_payload,
                request_id=f"{request_id}:language-repair",
            )
        except Exception:
            return None
        candidate = response.content
        if not isinstance(candidate, dict):
            return None
        normalized = self._normalize_provider_lesson(
            candidate,
            topic=request.topic,
            source_refs=source_refs,
        )
        return normalized if isinstance(normalized, dict) else None

    @staticmethod
    def _has_incomplete_structure(lesson_payload: dict[str, object]) -> bool:
        sections = lesson_payload.get("sections")
        checks = lesson_payload.get("interactive_checks")
        if not isinstance(sections, list) or len(sections) < 4:
            return True
        if not isinstance(checks, list) or len(checks) < 2:
            return True
        if (
            not isinstance(lesson_payload.get("summary"), str)
            or len(str(lesson_payload["summary"]).strip()) < 30
        ):
            return True
        for key in ("learning_objectives", "check_questions"):
            value = lesson_payload.get(key)
            if not isinstance(value, list) or len(value) < 2:
                return True
        section_keys = {"section_type", "title", "explanation", "key_points"}
        if any(
            not isinstance(section, dict) or not section_keys.issubset(section)
            for section in sections
        ):
            return True
        check_keys = {"prompt", "options", "correct_answer", "explanation"}
        return any(
            not isinstance(check, dict) or not check_keys.issubset(check) for check in checks
        )

    @staticmethod
    def _has_missing_evidence(
        lesson_payload: dict[str, object], *, request: TeachingRequest | None = None
    ) -> bool:
        for key in ("sections", "interactive_checks"):
            items = lesson_payload.get(key)
            if not isinstance(items, list):
                return True
            if any(
                not isinstance(item, dict)
                or not isinstance(item.get("evidence"), list)
                or not item["evidence"]
                or (
                    request is not None
                    and request.visual_pages
                    and any(
                        not isinstance(evidence, dict)
                        or TeachingService._parse_page_number(evidence.get("page_number")) is None
                        for evidence in item["evidence"]
                    )
                )
                for item in items
            ):
                return True
        return False

    @classmethod
    def _evidence_needs_repair(
        cls, evidence: list[dict[str, object]], request: TeachingRequest
    ) -> bool:
        """Return whether visual evidence has a missing page that a Provider can repair."""
        if not request.visual_pages:
            return False
        allowed = {(page.document_id, page.page_number) for page in request.visual_pages}
        return any(
            cls._parse_page_number(item.get("page_number")) is None
            or (str(item.get("document_id", "")), cls._parse_page_number(item.get("page_number")))
            not in allowed
            for item in evidence
        )

    @staticmethod
    def _normalize_source_ids(
        source_ids: object,
        selected_source_ids: set[str],
    ) -> list[str]:
        """Keep source IDs inside the user's selection without blocking recovery."""
        if not isinstance(source_ids, list):
            source_ids = []
        normalized = [str(source_id) for source_id in source_ids if str(source_id)]
        selected = [source_id for source_id in normalized if source_id in selected_source_ids]
        return selected or sorted(selected_source_ids)

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
            if "evidence" not in section and "source_evidence" in section:
                section["evidence"] = section.pop("source_evidence")
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
            if "evidence" not in check and "source_evidence" in check:
                check["evidence"] = check.pop("source_evidence")
            normalized_checks.append(check)
        payload["interactive_checks"] = normalized_checks
        return payload

    @staticmethod
    def _normalize_evidence(raw: object) -> list[dict[str, object]]:
        """Normalize common Provider evidence variants before best-effort reconciliation."""
        if not isinstance(raw, list):
            return []
        normalized: list[dict[str, object]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            evidence = dict(item)
            if "document_id" not in evidence and "source_document_id" in evidence:
                evidence["document_id"] = evidence.pop("source_document_id")
            if "page_number" not in evidence and "page" in evidence:
                evidence["page_number"] = evidence.pop("page")
            if "quote" not in evidence and "text" in evidence:
                evidence["quote"] = evidence.pop("text")
            if "page_number" in evidence:
                evidence["page_number"] = TeachingService._parse_page_number(
                    evidence.get("page_number")
                )
            if "document_id" in evidence:
                evidence["document_id"] = str(evidence.get("document_id", "")).strip()[:100]
            if "quote" in evidence:
                evidence["quote"] = str(evidence.get("quote", "")).strip()[:800]
            normalized.append(evidence)
        return normalized

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
        """Reject generic output while accepting common Chinese/English topic variants."""
        searchable = " ".join(
            [lesson.title, lesson.summary, *lesson.learning_objectives]
        ).casefold()
        compact_searchable = re.sub(r"\s+", "", searchable)
        normalized_topic = topic.strip().casefold()
        if normalized_topic in searchable or normalized_topic in compact_searchable:
            return True

        aliases: dict[str, tuple[str, ...]] = {
            "极限": ("limit", "limits"),
            "导数": ("derivative", "derivatives"),
            "积分": ("integral", "integrals"),
            "向量": ("vector", "vectors"),
            "矩阵": ("matrix", "matrices"),
            "函数": ("function", "functions"),
        }
        terms: list[str] = list(aliases.get(normalized_topic, ()))
        for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", normalized_topic):
            terms.append(chunk)
            terms.extend(chunk[index : index + 2] for index in range(len(chunk) - 1))
        terms.extend(re.findall(r"[a-z0-9]+", normalized_topic))
        return any(
            term and re.sub(r"\s+", "", term) in compact_searchable for term in dict.fromkeys(terms)
        )

    @classmethod
    def _validate_source_grounding(
        cls,
        lesson: TeachingLesson,
        *,
        selected_source_ids: set[str],
        source_text: str,
        source_units: list[TeachingSourceUnit],
        visual_pages: list[TeachingPageImage],
    ) -> tuple[str, ...]:
        """Report source-grounding problems without making a usable lesson impossible to save."""
        allowed_pages = {(page.document_id, page.page_number) for page in visual_pages}
        allowed_text_pages = {
            (unit.document_id, unit.page_number)
            for unit in source_units
            if unit.page_number is not None
        }
        issues: list[str] = []
        evidence_groups = [
            *(section.evidence for section in lesson.sections),
            *(check.evidence for check in lesson.interactive_checks),
        ]
        for evidence_group in evidence_groups:
            if not evidence_group:
                issues.append("部分章节暂时没有可核对的原文证据")
                continue
            for evidence in evidence_group:
                if evidence.document_id not in selected_source_ids:
                    issues.append("部分证据来源不在本次选择范围内")
                    continue
                quote = " ".join(evidence.quote.split())
                if len(re.sub(r"\s+", "", quote)) < 4:
                    issues.append("部分证据原文过短，暂不能人工核对")
                    continue
                if visual_pages:
                    if (
                        evidence.page_number is None
                        or (
                            evidence.document_id,
                            evidence.page_number,
                        )
                        not in allowed_pages
                    ):
                        issues.append("视觉证据页码无法唯一核对")
                elif (
                    evidence.page_number is not None
                    and (
                        evidence.document_id,
                        evidence.page_number,
                    )
                    not in allowed_text_pages
                ):
                    issues.append("文字证据页码无法在已读取页面中核对")
                elif source_text and not cls._quote_supported(quote, source_text):
                    issues.append("部分教学引文暂时无法在原文中核对")
        return tuple(dict.fromkeys(issues))

    @staticmethod
    def _quote_supported(quote: str, source_text: str) -> bool:
        compact_quote = TeachingService._quote_key(quote)
        compact_source = TeachingService._quote_key(source_text)
        return bool(compact_quote) and compact_quote in compact_source

    @staticmethod
    def _quote_key(text: str) -> str:
        """Normalize PDF line breaks and common math punctuation for safe quote matching."""
        normalized = unicodedata.normalize("NFKC", text).casefold()
        normalized = re.sub(r"\s+", "", normalized)
        return re.sub(r"[^\w\u4e00-\u9fff=+\-*/^().,:;%<>\[\]{}]", "", normalized)

    @staticmethod
    def _validate_lesson_quality(lesson: TeachingLesson) -> None:
        """Reject structurally valid but visibly incomplete or garbled lessons."""
        expected_types = ("concept", "mechanism", "boundary", "example")
        actual_types = tuple(section.section_type for section in lesson.sections)
        if actual_types != expected_types:
            raise ProviderError(
                "教学内容缺少完整的概念、机制、边界和例子章节",
                code="TEACHING_CONTENT_QUALITY_INVALID",
                retryable=False,
            )
        if len(lesson.summary.strip()) < 30 or len(lesson.learning_objectives) < 2:
            raise ProviderError(
                "教学内容摘要或学习目标过短",
                code="TEACHING_CONTENT_QUALITY_INVALID",
                retryable=False,
            )
        for section in lesson.sections:
            if len(section.explanation.strip()) < 40 or len(section.key_points) < 2:
                raise ProviderError(
                    "教学章节内容过短，未形成可阅读的讲解",
                    code="TEACHING_CONTENT_QUALITY_INVALID",
                    retryable=False,
                )
            if not section.example or len(section.example.strip()) < 10:
                raise ProviderError(
                    "教学章节缺少可用例子或练习",
                    code="TEACHING_CONTENT_QUALITY_INVALID",
                    retryable=False,
                )
            if "\ufffd" in section.explanation or "\ufffd" in section.example:
                raise ProviderError(
                    "教学章节包含乱码",
                    code="TEACHING_CONTENT_QUALITY_INVALID",
                    retryable=False,
                )
        if not 2 <= len(lesson.interactive_checks) <= 4:
            raise ProviderError(
                "互动小测数量必须为 2–4 道",
                code="TEACHING_CONTENT_QUALITY_INVALID",
                retryable=False,
            )
        if "\ufffd" in lesson.summary or "\ufffd" in lesson.title:
            raise ProviderError(
                "教学标题或摘要包含乱码",
                code="TEACHING_CONTENT_QUALITY_INVALID",
                retryable=False,
            )
        if not TeachingService._has_chinese_prose(lesson):
            raise ProviderError(
                "教学内容没有形成中文讲解",
                code="TEACHING_OUTPUT_LANGUAGE_INVALID",
                retryable=False,
            )

    @staticmethod
    def _has_chinese_prose(lesson: TeachingLesson) -> bool:
        """Require a meaningful amount of Chinese in learner-facing prose."""
        prose_parts = [lesson.title, lesson.summary, *lesson.learning_objectives]
        prose_parts.extend(lesson.check_questions)
        for section in lesson.sections:
            prose_parts.extend((section.title, section.explanation, section.example or ""))
            prose_parts.extend(section.key_points)
        for check in lesson.interactive_checks:
            prose_parts.extend((check.prompt, check.explanation, *check.options))
        prose = " ".join(prose_parts)
        chinese = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", prose))
        latin = len(re.findall(r"[A-Za-z]{2,}", prose))
        if chinese < 12:
            return False
        return chinese >= latin * 0.15 or latin == 0

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
