"""Offline tests for the paid OpenAI adapter; no network calls are made here."""

from dataclasses import dataclass
from typing import Any

import httpx
import openai
import pytest

from ai_growth_companion.providers.base import (
    EvaluationRequest,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from ai_growth_companion.providers.openai_evaluation import OpenAIEvaluationProvider
from ai_growth_companion.schemas.diagnosis import ProviderObservation


@dataclass
class StubUsage:
    input_tokens: int = 101
    output_tokens: int = 47
    total_tokens: int = 148


@dataclass
class StubResponse:
    output_parsed: ProviderObservation | None
    status: str | None = "completed"
    id: str = "response-test-123"
    model: str = "gpt-test-2026-08-01"
    usage: StubUsage | None = None


class StubResponses:
    def __init__(self, response: StubResponse | Exception) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> StubResponse:
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class StubClient:
    def __init__(self, response: StubResponse | Exception) -> None:
        self.responses = StubResponses(response)


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


def provider_for(response: StubResponse | Exception) -> tuple[OpenAIEvaluationProvider, StubClient]:
    client = StubClient(response)
    provider = OpenAIEvaluationProvider(
        api_key="test-key",
        model="gpt-test",
        max_output_tokens=700,
        client=client,
    )
    return provider, client


def test_structured_observation_and_safe_metadata_are_returned() -> None:
    provider, client = provider_for(StubResponse(output_parsed=observation(), usage=StubUsage()))

    result = provider.evaluate(evaluation_request(), request_id="local-request-1")

    assert result.content == observation()
    assert result.metadata.provider == "openai"
    assert result.metadata.model == "gpt-test"
    assert result.metadata.model_revision == "gpt-test-2026-08-01"
    assert result.metadata.request_id == "response-test-123"
    assert result.metadata.usage == {
        "input_tokens": 101,
        "output_tokens": 47,
        "total_tokens": 148,
    }
    call = client.responses.calls[0]
    assert call["text_format"] is ProviderObservation
    assert call["max_output_tokens"] == 700
    assert call["store"] is False
    assert "左右极限都存在且相等。" not in call["instructions"]
    assert "左右极限都存在且相等。" in call["input"]


@pytest.mark.parametrize(
    ("sdk_error", "expected_error", "expected_code"),
    [
        (
            openai.APITimeoutError(httpx.Request("POST", "https://api.openai.test/v1")),
            ProviderTimeoutError,
            "LLM_TIMEOUT",
        ),
        (
            openai.APIConnectionError(request=httpx.Request("POST", "https://api.openai.test/v1")),
            ProviderUnavailableError,
            "LLM_UNAVAILABLE",
        ),
        (
            openai.RateLimitError(
                "rate limited",
                response=httpx.Response(
                    429,
                    request=httpx.Request("POST", "https://api.openai.test/v1"),
                ),
                body=None,
            ),
            ProviderError,
            "LLM_RATE_LIMIT",
        ),
        (
            openai.APIStatusError(
                "bad request",
                response=httpx.Response(
                    400,
                    request=httpx.Request("POST", "https://api.openai.test/v1"),
                ),
                body=None,
            ),
            ProviderError,
            "LLM_REQUEST_REJECTED",
        ),
    ],
)
def test_sdk_failures_are_mapped_without_leaking_details(
    sdk_error: Exception,
    expected_error: type[ProviderError],
    expected_code: str,
) -> None:
    provider, _client = provider_for(sdk_error)

    with pytest.raises(expected_error) as captured:
        provider.evaluate(evaluation_request(), request_id="local-request-2")

    assert captured.value.code == expected_code
    assert "openai.test" not in str(captured.value)


@pytest.mark.parametrize(
    "response",
    [
        StubResponse(output_parsed=None),
        StubResponse(output_parsed=observation(), status="incomplete"),
    ],
)
def test_missing_or_incomplete_structured_output_is_rejected(response: StubResponse) -> None:
    provider, _client = provider_for(response)

    with pytest.raises(ProviderError) as captured:
        provider.evaluate(evaluation_request(), request_id="local-request-3")

    assert captured.value.code == "LLM_OUTPUT_UNAVAILABLE"
    assert captured.value.retryable is False


@pytest.mark.parametrize("model", ["", "  ", "fake-mastery-v0.1"])
def test_real_provider_rejects_missing_or_fake_model(model: str) -> None:
    with pytest.raises(ValueError, match="non-Fake"):
        OpenAIEvaluationProvider(api_key="test-key", model=model)
