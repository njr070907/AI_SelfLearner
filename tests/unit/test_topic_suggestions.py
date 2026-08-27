"""Tests for background AI topic extraction and learner-facing choices."""

from pathlib import Path
from time import monotonic, sleep

from ai_growth_companion.application.topic_suggestions import (
    TopicSuggestionService,
    source_signature,
)
from ai_growth_companion.providers.base import (
    ProviderMetadata,
    ProviderResponse,
    TopicSuggestionRequest,
)


class StubTopicProvider:
    provider_name = "ollama"
    model_name = "qwen3.5:4b"
    model_revision = "stub-1"

    def __init__(self, *, invalid: bool = False) -> None:
        self.invalid = invalid
        self.requests: list[TopicSuggestionRequest] = []

    def suggest_topics(
        self,
        request: TopicSuggestionRequest,
        *,
        request_id: str,
    ) -> ProviderResponse:
        del request_id
        self.requests.append(request)
        topics = (
            {
                "title": "函数极限的定义",
                "summary": "理解函数在某点附近趋近的含义。",
                "key_concepts": ["极限", "趋近"],
                "confidence": "high",
            },
            {
                "title": "极限的基本计算方法",
                "summary": "整理代入、等价无穷小和运算法则。",
                "key_concepts": ["代入", "无穷小"],
                "confidence": "medium",
            },
        )
        return ProviderResponse(
            content={"topics": [] if self.invalid else topics},
            metadata=ProviderMetadata(
                provider=self.provider_name,
                model=self.model_name,
                model_revision=self.model_revision,
                prompt_version="topic-test-v0.1",
                schema_version="topic-suggestion-v0.1",
                latency_ms=1,
                usage={},
                finish_reason="stop",
                request_id="topic-test-1",
            ),
        )


def test_topic_suggestions_are_cached_after_background_generation(tmp_path: Path) -> None:
    provider = StubTopicProvider()
    service = TopicSuggestionService(provider, cache_root=tmp_path)
    labels = (("doc-1", "limits.md"),)
    signature = source_signature((("doc-1", "limits.md", "a" * 64),))

    pending = service.get_or_schedule(
        source_text="# 函数极限\n\nFunction limits describe change.",
        source_labels=labels,
        source_signature=signature,
        request_id="topics-1",
    )
    assert pending.status == "pending"
    assert pending.suggestions
    assert pending.suggestions[0].title.startswith("函数极限")
    deadline = monotonic() + 2
    while monotonic() < deadline and not list(tmp_path.glob("*.json")):
        sleep(0.01)
    assert list(tmp_path.glob("*.json"))

    ready = service.get_or_schedule(
        source_text="# 函数极限\n\nFunction limits describe change.",
        source_labels=labels,
        source_signature=signature,
        request_id="topics-2",
    )
    assert ready.status == "ready"
    assert ready.model_name == "qwen3.5:4b"
    assert ready.suggestions[0].title == "函数极限的定义"
    assert ready.suggestions[0].source_document_ids == ("doc-1",)
    assert len(provider.requests) == 1


def test_topic_suggestions_cap_source_ids_for_large_libraries(tmp_path: Path) -> None:
    service = TopicSuggestionService(None, cache_root=tmp_path)
    labels = tuple((f"doc-{index}", f"part-{index}.md") for index in range(22))
    signature = source_signature(
        tuple((document_id, filename, "d" * 64) for document_id, filename in labels)
    )

    pending = service.get_or_schedule(
        source_text="# 函数极限\n\nFunction limits describe change.",
        source_labels=labels,
        source_signature=signature,
        request_id="topics-large-library-1",
    )

    assert pending.suggestions
    assert len(pending.suggestions[0].source_document_ids) == 20


def test_topic_provider_failure_returns_a_selectable_fallback(tmp_path: Path) -> None:
    provider = StubTopicProvider(invalid=True)
    service = TopicSuggestionService(provider, cache_root=tmp_path)
    signature = source_signature((("doc-1", "limits.md", "b" * 64),))

    assert service.schedule(
        source_text="# 函数极限\n\nFunction limits describe change.",
        source_labels=(("doc-1", "limits.md"),),
        source_signature=signature,
        request_id="topics-fallback-1",
    )
    deadline = monotonic() + 2
    while monotonic() < deadline and not list(tmp_path.glob("*.json")):
        sleep(0.01)
    result = service.get_or_schedule(
        source_text="# 函数极限\n\nFunction limits describe change.",
        source_labels=(("doc-1", "limits.md"),),
        source_signature=signature,
        request_id="topics-fallback-2",
    )
    assert result.status == "fallback"
    assert result.suggestions
    assert "AI 主题分析暂时不可用" in result.suggestions[0].summary


def test_english_provider_labels_remain_readable_in_chinese_ui(tmp_path: Path) -> None:
    provider = StubTopicProvider()

    def english_topics(
        request: TopicSuggestionRequest,
        *,
        request_id: str,
    ) -> ProviderResponse:
        del request, request_id
        return ProviderResponse(
            content={
                "topics": [
                    {
                        "title": "Calculus Limits",
                        "summary": "How a function approaches a value.",
                        "key_concepts": ["limit"],
                    }
                ]
            },
            metadata=ProviderMetadata(
                provider=provider.provider_name,
                model=provider.model_name,
                model_revision=provider.model_revision,
                prompt_version="topic-test-english-v0.1",
                schema_version="topic-suggestion-v0.1",
                latency_ms=1,
                usage={},
                finish_reason="stop",
                request_id="topic-test-english-1",
            ),
        )

    provider.suggest_topics = english_topics  # type: ignore[method-assign]
    service = TopicSuggestionService(provider, cache_root=tmp_path)
    signature = source_signature((("doc-1", "calculus.md", "c" * 64),))
    assert service.schedule(
        source_text="# Calculus Limits\n\nA function approaches a value.",
        source_labels=(("doc-1", "calculus.md"),),
        source_signature=signature,
        request_id="topics-english-1",
    )
    deadline = monotonic() + 2
    while monotonic() < deadline and not list(tmp_path.glob("*.json")):
        sleep(0.01)
    result = service.get_or_schedule(
        source_text="# Calculus Limits\n\nA function approaches a value.",
        source_labels=(("doc-1", "calculus.md"),),
        source_signature=signature,
        request_id="topics-english-2",
    )
    assert result.status == "ready"
    assert result.suggestions[0].title.startswith("资料主题：")
    assert result.suggestions[0].summary.startswith("根据资料整理：")
