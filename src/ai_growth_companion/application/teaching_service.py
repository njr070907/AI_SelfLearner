"""Application service for source-grounded lesson generation."""

import json
import re
import unicodedata
from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from ai_growth_companion.application.document_library import (
    DocumentLibraryService,
    DocumentValidationError,
)
from ai_growth_companion.application.knowledge_extraction import KnowledgeUnit, extract_knowledge
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
from ai_growth_companion.domain.events import LOCAL_USER_ID
from ai_growth_companion.providers.base import (
    ProviderError,
    TeachingPageImage,
    TeachingProvider,
    TeachingRequest,
    TeachingSourceUnit,
)
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

    MAX_SOURCE_CONTEXT_CHARS = 60_000
    MAX_UNITS_PER_DOCUMENT = 12

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
        self.source_selector = TopicSourceSelector(document_library)

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
        source_parts: list[str] = []
        source_refs: list[tuple[str, str, str]] = []
        source_units: list[TeachingSourceUnit] = []
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
                    page_label = (
                        f"第 {unit.page_number} 页" if unit.page_number is not None else "文本内容"
                    )
                    source_parts.append(f"【{document.filename} · {page_label}】\n{unit.text}")
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

        source_text = "\n\n".join(source_parts)[: self.MAX_SOURCE_CONTEXT_CHARS]
        teaching_request = TeachingRequest(
            topic=normalized_topic,
            source_text=source_text,
            sources=tuple(source_refs),
            learning_goal=learning_goal.strip() if learning_goal else None,
            learner_level=learner_level,
            source_units=tuple(source_units),
            visual_pages=tuple(visual_pages),
        )
        response = self.provider.generate_lesson(teaching_request, request_id=request_id)
        selected_source_ids = {document_id for document_id, _, _ in source_refs}
        try:
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
            interaction["evidence"] = self._normalize_evidence(
                interaction.get("evidence", interaction.get("source_evidence", []))
            )
        for section in lesson_payload["sections"]:
            section["evidence"] = self._normalize_evidence(
                section.get("evidence", section.get("source_evidence", []))
            )
        lesson_payload = self._repair_missing_evidence(
            teaching_request,
            lesson_payload,
            request_id=request_id,
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
        self._validate_source_grounding(
            lesson,
            selected_source_ids=selected_source_ids,
            source_text=source_text,
            source_units=source_units,
            visual_pages=visual_pages,
        )
        self._validate_lesson_quality(lesson)
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

    def _repair_missing_evidence(
        self,
        request: TeachingRequest,
        lesson_payload: dict[str, object],
        *,
        request_id: str,
    ) -> dict[str, object]:
        """Run one bounded evidence-only repair for Providers that explicitly support it."""
        if not self._has_missing_evidence(lesson_payload):
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
        except ProviderError:
            # The original output is still validated below and will fail closed if needed.
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
                if not existing and index < len(candidates) and isinstance(candidates[index], dict):
                    item["evidence"] = self._normalize_evidence(
                        candidates[index].get("evidence", [])
                    )
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
        except ProviderError:
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
    def _has_missing_evidence(lesson_payload: dict[str, object]) -> bool:
        for key in ("sections", "interactive_checks"):
            items = lesson_payload.get(key)
            if not isinstance(items, list):
                return True
            if any(
                not isinstance(item, dict)
                or not isinstance(item.get("evidence"), list)
                or not item["evidence"]
                for item in items
            ):
                return True
        return False

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
        """Normalize small naming differences without weakening source validation."""
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
    ) -> None:
        """Require every generated teaching unit to carry inspectable source evidence."""
        allowed_pages = {(page.document_id, page.page_number) for page in visual_pages}
        allowed_text_pages = {
            (unit.document_id, unit.page_number)
            for unit in source_units
            if unit.page_number is not None
        }
        evidence_groups = [
            *(section.evidence for section in lesson.sections),
            *(check.evidence for check in lesson.interactive_checks),
        ]
        for evidence_group in evidence_groups:
            if not evidence_group:
                raise ProviderError(
                    "教学内容缺少章节级资料证据，不能确认内容来自原文",
                    code="TEACHING_SOURCE_EVIDENCE_MISSING",
                    retryable=False,
                )
            for evidence in evidence_group:
                if evidence.document_id not in selected_source_ids:
                    raise ProviderError(
                        "教学内容引用了未选择的资料",
                        code="TEACHING_SOURCE_EVIDENCE_INVALID",
                        retryable=False,
                    )
                quote = " ".join(evidence.quote.split())
                if len(re.sub(r"\s+", "", quote)) < 4:
                    raise ProviderError(
                        "教学资料证据过短，无法人工核对",
                        code="TEACHING_SOURCE_EVIDENCE_INVALID",
                        retryable=False,
                    )
                if visual_pages:
                    if (
                        evidence.page_number is None
                        or (
                            evidence.document_id,
                            evidence.page_number,
                        )
                        not in allowed_pages
                    ):
                        raise ProviderError(
                            "视觉教学证据缺少有效页码",
                            code="TEACHING_SOURCE_EVIDENCE_INVALID",
                            retryable=False,
                        )
                elif (
                    evidence.page_number is not None
                    and (
                        evidence.document_id,
                        evidence.page_number,
                    )
                    not in allowed_text_pages
                ):
                    raise ProviderError(
                        "教学资料证据页码无法在已读取页面中核对",
                        code="TEACHING_SOURCE_EVIDENCE_INVALID",
                        retryable=False,
                    )
                elif source_text and not cls._quote_supported(quote, source_text):
                    raise ProviderError(
                        "教学内容包含无法在原文中核对的引文",
                        code="TEACHING_SOURCE_EVIDENCE_UNSUPPORTED",
                        retryable=False,
                    )

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
