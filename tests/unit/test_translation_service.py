"""Tests for the optional local English-to-Chinese source translation path."""

from pathlib import Path
from threading import Event
from time import monotonic, sleep

import pytest

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.application.teaching_service import TeachingService
from ai_growth_companion.application.translation_service import (
    TranslationService,
    build_bilingual_context,
    detect_source_language,
)
from ai_growth_companion.providers.base import (
    ProviderError,
    ProviderMetadata,
    ProviderResponse,
    TeachingSourceUnit,
    TranslationRequest,
)
from ai_growth_companion.providers.fake import FakeLLMProvider
from ai_growth_companion.providers.ollama import OllamaTranslationProvider
from ai_growth_companion.repositories.database import Database, run_migrations
from ai_growth_companion.repositories.document_repository import SQLiteDocumentRepository
from ai_growth_companion.repositories.lesson_progress_repository import (
    SQLiteLessonProgressRepository,
)
from ai_growth_companion.repositories.lesson_repository import SQLiteLessonRepository


class StubTranslationProvider:
    provider_name = "ollama"
    model_name = "qwen3.5:0.8b"
    model_revision = "stub-1"

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.requests: list[TranslationRequest] = []

    def translate(self, request: TranslationRequest, *, request_id: str) -> ProviderResponse:
        del request_id
        self.requests.append(request)
        if self.fail:
            raise ProviderError("translation unavailable", code="LLM_UNAVAILABLE", retryable=True)
        return ProviderResponse(
            content={"translated_text": "函数极限描述函数在某点附近的变化趋势。"},
            metadata=ProviderMetadata(
                provider=self.provider_name,
                model=self.model_name,
                model_revision=self.model_revision,
                prompt_version="translation-test-v0.1",
                schema_version="translation-v0.1",
                latency_ms=1,
                usage={},
                finish_reason="stop",
                request_id="translation-test-1",
            ),
        )


def test_language_detection_distinguishes_english_and_chinese() -> None:
    assert detect_source_language("Function limits describe change near a point.") == "en"
    assert detect_source_language("函数极限描述函数在某点附近的变化趋势。") == "zh"
    assert detect_source_language("函数 limits describe 变化") == "mixed"


def test_translation_keeps_original_evidence_and_adds_bilingual_context() -> None:
    provider = StubTranslationProvider()
    service = TranslationService(provider)
    original = TeachingSourceUnit(
        document_id="doc-1",
        filename="limits.md",
        page_number=None,
        text="Function limits describe change near a point.",
    )

    result = service.translate_units((original,), request_id="translate-1")

    assert result.status == "translated"
    assert result.model_name == "qwen3.5:0.8b"
    assert result.translated_unit_count == 1
    assert result.units[0].text == original.text
    assert result.units[0].translated_text == "函数极限描述函数在某点附近的变化趋势。"
    context = build_bilingual_context(result.units)
    assert "[中文译文]" in context
    assert "[英文原文（证据引用必须从这里逐字复制）]" in context
    assert original.text in context


def test_translation_failure_falls_back_without_blocking() -> None:
    provider = StubTranslationProvider(fail=True)
    result = TranslationService(provider).translate_units(
        (
            TeachingSourceUnit(
                document_id="doc-1",
                filename="limits.md",
                page_number=None,
                text="Function limits describe change near a point.",
            ),
        ),
        request_id="translate-fallback-1",
    )

    assert result.status == "fallback_original"
    assert result.units[0].translated_text is None
    assert result.failed_unit_count == 1


@pytest.mark.parametrize("content", ["", "中文内容\ufffd", "Function limits remain untranslated."])
def test_invalid_translation_content_falls_back(content: str) -> None:
    class InvalidProvider(StubTranslationProvider):
        def translate(self, request: TranslationRequest, *, request_id: str) -> ProviderResponse:
            del request, request_id
            return ProviderResponse(
                content={"translated_text": content},
                metadata=ProviderMetadata(
                    provider="ollama",
                    model="qwen3.5:0.8b",
                    model_revision=None,
                    prompt_version="test",
                    schema_version="translation-v0.1",
                    latency_ms=1,
                    usage={},
                    finish_reason="stop",
                    request_id="test",
                ),
            )

    result = TranslationService(InvalidProvider()).translate_units(
        (
            TeachingSourceUnit(
                document_id="doc-1",
                filename="limits.md",
                page_number=None,
                text="Function limits describe change near a point.",
            ),
        ),
        request_id="translate-invalid-1",
    )
    assert result.status == "fallback_original"


def test_teaching_service_uses_translation_before_generation(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{(tmp_path / 'translation.db').as_posix()}")
    run_migrations(database)
    documents = DocumentLibraryService(
        SQLiteDocumentRepository(database), storage_root=tmp_path / "documents"
    )
    translator = StubTranslationProvider()
    teaching = TeachingService(
        documents,
        SQLiteLessonRepository(database),
        FakeLLMProvider(),
        SQLiteLessonProgressRepository(database),
        translation_provider=translator,
    )
    document = documents.upload(
        filename="limits.md",
        content=b"# Function limits\n\nFunction limits describe change near a point.",
    )

    assert teaching.schedule_translation(document.document_id, request_id="upload-translation-1")
    deadline = monotonic() + 2
    while monotonic() < deadline and not list(
        teaching.translation_service.cache_root.glob("*.json")
    ):
        sleep(0.01)
    assert list(teaching.translation_service.cache_root.glob("*.json"))

    lesson = teaching.generate_lesson(
        topic="函数极限",
        document_ids=(document.document_id,),
        request_id="teaching-translation-1",
    )

    assert translator.requests
    assert lesson.lesson.translation_status == "translated"
    assert lesson.lesson.translated_unit_count == 1
    assert lesson.lesson.sections[0].evidence[0].quote.startswith("# Function limits")


def test_upload_translation_is_queued_without_waiting_for_provider(tmp_path: Path) -> None:
    started = Event()
    release = Event()

    class SlowTranslationProvider(StubTranslationProvider):
        def translate(self, request: TranslationRequest, *, request_id: str) -> ProviderResponse:
            started.set()
            release.wait(timeout=2)
            return super().translate(request, request_id=request_id)

    provider = SlowTranslationProvider()
    service = TranslationService(provider, cache_root=tmp_path)
    unit = TeachingSourceUnit(
        document_id="doc-upload",
        filename="notes.md",
        page_number=None,
        text="Function limits describe change near a point.",
    )
    queued_at = monotonic()
    assert service.schedule_units(
        (unit,),
        source_sha256="a" * 64,
        request_id="upload-background-1",
    )
    assert monotonic() - queued_at < 0.5
    assert started.wait(timeout=1)

    pending = service.prepare_units(
        (unit,),
        source_hashes={"doc-upload": "a" * 64},
        request_id="lesson-while-translating",
    )
    assert pending.status == "pending"
    assert pending.units[0].translated_text is None

    release.set()
    deadline = monotonic() + 2
    while monotonic() < deadline and not list(tmp_path.glob("*.json")):
        sleep(0.01)
    assert list(tmp_path.glob("*.json"))


def test_ollama_translation_provider_returns_structured_translation() -> None:
    from dataclasses import dataclass
    from typing import Any

    @dataclass
    class Message:
        content: str | None
        refusal: str | None = None

    @dataclass
    class Choice:
        message: Message
        finish_reason: str | None = "stop"

    @dataclass
    class Usage:
        prompt_tokens: int = 4
        completion_tokens: int = 5
        total_tokens: int = 9

    class Completions:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def create(self, **kwargs: Any) -> Any:
            self.calls.append(kwargs)
            return type(
                "Completion",
                (),
                {
                    "choices": [Choice(Message('{"translated_text":"中文译文"}'))],
                    "id": "translation-response-1",
                    "model": "qwen3.5:0.8b",
                    "usage": Usage(),
                },
            )()

    completions = Completions()
    client = type("Client", (), {"chat": type("Chat", (), {"completions": completions})()})()
    provider = OllamaTranslationProvider(model="qwen3.5:0.8b", client=client)

    result = provider.translate(
        TranslationRequest(text="Function limits describe change."),
        request_id="translation-provider-1",
    )

    assert result.content == {"translated_text": "中文译文"}
    assert result.metadata.schema_version == "translation-v0.1"
    assert completions.calls[0]["model"] == "qwen3.5:0.8b"
