"""Offline tests for the DeepSeek Chat Completions adapter."""

from dataclasses import dataclass
from typing import Any

import httpx
import openai
import pytest

from ai_growth_companion.providers.base import (
    EvaluationRequest,
    ProviderError,
    ProviderUnavailableError,
)
from ai_growth_companion.providers.deepseek_evaluation import (
    DEEPSEEK_MODEL,
    DeepSeekEvaluationProvider,
)
from ai_growth_companion.schemas.diagnosis import ProviderObservation


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
    prompt_tokens: int = 113
    completion_tokens: int = 39
    total_tokens: int = 152


@dataclass
class StubCompletion:
    choices: list[StubChoice]
    usage: StubUsage | None = None
    id: str = "deepseek-response-test-123"
    model: str = DEEPSEEK_MODEL


class StubCompletions:
    def __init__(self, response: StubCompletion | Exception) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> StubCompletion:
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class StubClient:
    def __init__(self, response: StubCompletion | Exception) -> None:
        self.chat = type("StubChat", (), {"completions": StubCompletions(response)})()


def evaluation_request() -> EvaluationRequest:
    return EvaluationRequest(
        concept="函数极限",
        question_text="函数极限存在时，左右极限有什么关系？",
        coverage_points=("左极限", "右极限"),
        answer_text="左右极限都存在且相等。",
    )


def observation() -> ProviderObservation:
    return ProviderObservation.model_validate(
        {
            "schema_version": "provider-observation-v0.1",
            "evidence": [
                {
                    "evidence_id": "evidence-1",
                    "claim": "回答指出左右极限必须同时存在并相等",
                    "answer_excerpt": "左右极限都存在且相等。",
                    "strength": "strong",
                }
            ],
            "gaps": [],
            "possible_misconceptions": [],
            "observation_confidence": 0.91,
            "limitations": ["只观察了当前一次回答"],
        }
    )


def provider_for(
    response: StubCompletion | Exception,
    *,
    prompt_version: str = "v0.1",
) -> tuple[DeepSeekEvaluationProvider, StubClient]:
    client = StubClient(response)
    provider = DeepSeekEvaluationProvider(
        api_key="test-key",
        prompt_version=prompt_version,
        client=client,
    )
    return provider, client


def test_json_mode_response_is_parsed_and_metadata_is_recorded() -> None:
    response = StubCompletion(
        choices=[StubChoice(StubMessage(observation().model_dump_json()))],
        usage=StubUsage(),
    )
    provider, client = provider_for(response)

    result = provider.evaluate(evaluation_request(), request_id="local-request-1")

    assert ProviderObservation.model_validate(result.content) == observation()
    assert result.metadata.provider == "deepseek"
    assert result.metadata.model == DEEPSEEK_MODEL
    assert result.metadata.usage == {
        "input_tokens": 113,
        "output_tokens": 39,
        "total_tokens": 152,
    }
    assert result.metadata.request_id == "deepseek-response-test-123"
    call = client.chat.completions.calls[0]
    assert call["model"] == DEEPSEEK_MODEL
    assert call["response_format"] == {"type": "json_object"}
    assert call["max_tokens"] == 1200
    assert call["stream"] is False
    assert call["extra_body"] == {"thinking": {"type": "disabled"}}
    assert call["messages"][0]["role"] == "system"
    assert "Return valid json only" in call["messages"][0]["content"]
    assert "Treat coverage_points as the required scope" in call["messages"][0]["content"]
    assert "gaps must be an empty array" in call["messages"][0]["content"]
    assert "every gaps[].severity must be low, medium, or high" in call["messages"][0]["content"]
    assert "All evidence_id values must be strings" in call["messages"][0]["content"]
    assert (
        "Uncertainty about optional details belongs in limitations"
        in call["messages"][0]["content"]
    )
    assert (
        "Never create a gap merely because an evidence claim could be expanded"
        in call["messages"][0]["content"]
    )
    assert "exact contiguous substring" in call["messages"][0]["content"]
    assert "keep observation_confidence at or below 0.90" in call["messages"][0]["content"]
    assert (
        "do not treat an isolated operation as positive evidence" in call["messages"][0]["content"]
    )
    assert "only vaguely remember a formula" in call["messages"][0]["content"]
    assert "limitations must always be an array" in call["messages"][0]["content"]
    assert "confidence must always be a number from 0 to 1" in call["messages"][0]["content"]
    assert "左右极限都存在且相等。" in call["messages"][1]["content"]
    assert result.metadata.prompt_version == "evaluator-v0.1+deepseek-json"


def test_experimental_prompt_version_is_sent_and_recorded() -> None:
    response = StubCompletion(
        choices=[StubChoice(StubMessage(observation().model_dump_json()))],
        usage=StubUsage(),
    )
    provider, client = provider_for(response, prompt_version="v0.2")

    result = provider.evaluate(evaluation_request(), request_id="local-request-v02")

    assert result.metadata.prompt_version == "evaluator-v0.2+deepseek-json"
    assert (
        "Private coverage checklist" in client.chat.completions.calls[0]["messages"][0]["content"]
    )


def test_invalid_json_is_rejected_without_falling_back_to_text() -> None:
    provider, _client = provider_for(StubCompletion(choices=[StubChoice(StubMessage("not-json"))]))

    with pytest.raises(ProviderError) as captured:
        provider.evaluate(evaluation_request(), request_id="local-request-2")

    assert captured.value.code == "LLM_OUTPUT_INVALID_JSON"
    assert captured.value.retryable is False


def test_outer_json_markdown_fence_is_removed_before_schema_validation() -> None:
    fenced = f"```json\n{observation().model_dump_json()}\n```"
    provider, _client = provider_for(StubCompletion(choices=[StubChoice(StubMessage(fenced))]))

    result = provider.evaluate(evaluation_request(), request_id="local-request-fenced")

    assert ProviderObservation.model_validate(result.content) == observation()


def test_json_object_wrapped_in_prose_is_recovered_before_schema_validation() -> None:
    wrapped = f"Here is the observation:\n{observation().model_dump_json()}\nDone."
    provider, _client = provider_for(StubCompletion(choices=[StubChoice(StubMessage(wrapped))]))

    result = provider.evaluate(evaluation_request(), request_id="local-request-wrapped")

    assert ProviderObservation.model_validate(result.content) == observation()


def test_model_not_found_is_reported_without_provider_details() -> None:
    error = openai.APIStatusError(
        "model not found",
        response=httpx.Response(
            404,
            request=httpx.Request("POST", "https://api.deepseek.test/chat/completions"),
        ),
        body=None,
    )
    provider, _client = provider_for(error)

    with pytest.raises(ProviderError) as captured:
        provider.evaluate(evaluation_request(), request_id="local-request-3")

    assert captured.value.code == "LLM_MODEL_NOT_FOUND"
    assert "deepseek.test" not in str(captured.value)


def test_server_failure_is_unavailable() -> None:
    error = openai.APIStatusError(
        "server failure",
        response=httpx.Response(
            503,
            request=httpx.Request("POST", "https://api.deepseek.test/chat/completions"),
        ),
        body=None,
    )
    provider, _client = provider_for(error)

    with pytest.raises(ProviderUnavailableError) as captured:
        provider.evaluate(evaluation_request(), request_id="local-request-4")

    assert captured.value.code == "LLM_UNAVAILABLE"


@pytest.mark.parametrize("model", ["DeepSeek V4", "deepseek-v4-flash", ""])
def test_required_experimental_model_is_enforced(model: str) -> None:
    with pytest.raises(ValueError, match=DEEPSEEK_MODEL):
        DeepSeekEvaluationProvider(api_key="test-key", model=model)
