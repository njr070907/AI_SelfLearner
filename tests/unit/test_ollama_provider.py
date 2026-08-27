"""Offline contract tests for the local Ollama adapters."""

from dataclasses import dataclass
from typing import Any

from ai_growth_companion.providers.base import (
    EvaluationRequest,
    QuestionRequest,
    TeachingRequest,
    TopicSuggestionRequest,
)
from ai_growth_companion.providers.ollama import (
    OLLAMA_BALANCED_MODEL,
    OLLAMA_QUALITY_MODEL,
    OllamaEvaluationProvider,
    OllamaQuestionProvider,
    OllamaTeachingProvider,
    OllamaTopicSuggestionProvider,
)
from ai_growth_companion.schemas.diagnosis import ProviderObservation, QuestionDraft
from ai_growth_companion.schemas.teaching import (
    LessonInteraction,
    LessonSection,
    LessonSource,
    TeachingLesson,
)


@dataclass
class StubMessage:
    content: str | None
    refusal: str | None = None


@dataclass
class StubChoice:
    message: StubMessage
    finish_reason: str | None = "stop"


@dataclass
class StubUsage:
    prompt_tokens: int = 11
    completion_tokens: int = 7
    total_tokens: int = 18


@dataclass
class StubCompletion:
    choices: list[StubChoice]
    id: str = "ollama-response-1"
    model: str = OLLAMA_QUALITY_MODEL
    usage: StubUsage | None = None


class StubCompletions:
    def __init__(self, response: StubCompletion) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> StubCompletion:
        self.calls.append(kwargs)
        return self.response


class StubClient:
    def __init__(self, response: StubCompletion) -> None:
        self.chat = type("StubChat", (), {"completions": StubCompletions(response)})()


def observation_payload() -> ProviderObservation:
    return ProviderObservation.model_validate(
        {
            "schema_version": "provider-observation-v0.1",
            "evidence": [
                {
                    "evidence_id": "e1",
                    "claim": "回答覆盖核心机制",
                    "answer_excerpt": "左右极限都存在且相等。",
                    "strength": "strong",
                }
            ],
            "gaps": [],
            "possible_misconceptions": [],
            "observation_confidence": 0.9,
            "limitations": [],
        }
    )


def lesson_payload() -> TeachingLesson:
    return TeachingLesson(
        topic="函数极限",
        title="函数极限导学",
        summary="先理解变化趋势。",
        learning_objectives=["说清楚定义"],
        sections=[
            LessonSection(
                section_type="concept",
                title="概念",
                explanation="描述变化趋势。",
                key_points=["定义"],
            ),
            LessonSection(
                section_type="mechanism",
                title="机制",
                explanation="按步骤理解。",
                key_points=["步骤"],
            ),
            LessonSection(
                section_type="boundary",
                title="边界",
                explanation="检查条件。",
                key_points=["条件"],
            ),
        ],
        check_questions=["什么时候失效？"],
        interactive_checks=[
            LessonInteraction(
                prompt="哪一个选项正确？",
                options=["A", "B"],
                correct_answer="A",
                explanation="A 符合资料。",
            )
        ],
        sources=[LessonSource(document_id="doc-1", filename="a.md", excerpt="定义")],
    )


def test_ollama_evaluation_uses_local_openai_compatible_endpoint() -> None:
    client = StubClient(
        StubCompletion(choices=[StubChoice(StubMessage(observation_payload().model_dump_json()))])
    )
    provider = OllamaEvaluationProvider(client=client)

    result = provider.evaluate(
        EvaluationRequest(
            concept="函数极限",
            question_text="左右极限有什么关系？",
            coverage_points=("左极限", "右极限"),
            answer_text="左右极限都存在且相等。",
        ),
        request_id="ollama-eval-1",
    )

    assert ProviderObservation.model_validate(result.content) == observation_payload()
    assert result.metadata.provider == "ollama"
    assert result.metadata.model == OLLAMA_QUALITY_MODEL
    assert result.metadata.prompt_version == "evaluator-v0.1+ollama-grounded-json"
    call = client.chat.completions.calls[0]
    assert call["model"] == OLLAMA_QUALITY_MODEL
    assert call["response_format"] == {"type": "json_object"}
    assert call["extra_body"] == {"reasoning_effort": "low"}


def test_ollama_question_provider_uses_balanced_model() -> None:
    draft = QuestionDraft(
        concept="导数",
        question_text="请解释导数的含义、机制和适用边界。",
        coverage_points=["含义", "机制", "边界"],
        difficulty="introductory",
        question_type="mechanism",
    )
    client = StubClient(
        StubCompletion(
            choices=[StubChoice(StubMessage(draft.model_dump_json()))],
            model=OLLAMA_BALANCED_MODEL,
        )
    )
    provider = OllamaQuestionProvider(model=OLLAMA_BALANCED_MODEL, client=client)

    result = provider.generate_question(QuestionRequest(concept="导数"), request_id="question-1")

    assert QuestionDraft.model_validate(result.content) == draft
    assert result.metadata.model == OLLAMA_BALANCED_MODEL
    assert result.metadata.prompt_version == "ollama-question-v0.1"


def test_ollama_teaching_provider_is_text_only_and_source_grounded() -> None:
    client = StubClient(
        StubCompletion(choices=[StubChoice(StubMessage(lesson_payload().model_dump_json()))])
    )
    provider = OllamaTeachingProvider(client=client)

    result = provider.generate_lesson(
        TeachingRequest(
            topic="函数极限",
            source_text="定义描述变化趋势。",
            sources=(("doc-1", "a.md", "定义"),),
        ),
        request_id="teaching-1",
    )

    assert TeachingLesson.model_validate(result.content) == lesson_payload()
    assert provider.supports_vision is False
    assert result.metadata.model == OLLAMA_QUALITY_MODEL
    assert result.metadata.prompt_version == "teaching-v0.4+ollama-grounded-json"


def test_ollama_topic_provider_returns_structured_chinese_choices() -> None:
    response = StubCompletion(
        choices=[
            StubChoice(
                StubMessage(
                    '{"topics":[{"title":"函数极限的定义",'
                    '"summary":"理解函数在某点附近趋近的含义。",'
                    '"key_concepts":["极限"],"confidence":"high"}]}'
                )
            )
        ],
        model=OLLAMA_BALANCED_MODEL,
    )
    client = StubClient(response)
    provider = OllamaTopicSuggestionProvider(
        model=OLLAMA_BALANCED_MODEL,
        client=client,
    )

    result = provider.suggest_topics(
        TopicSuggestionRequest(
            source_text="Function limits describe change near a point.",
            source_labels=(("doc-1", "limits.md"),),
        ),
        request_id="topic-provider-1",
    )

    assert result.content["topics"][0]["title"] == "函数极限的定义"
    assert result.metadata.schema_version == "topic-suggestion-v0.1"
    assert client.chat.completions.calls[0]["model"] == OLLAMA_BALANCED_MODEL
