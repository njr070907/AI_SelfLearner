"""Deterministic Fake Provider scenario tests."""

import pytest
from pydantic import ValidationError

from ai_growth_companion.providers.base import (
    EvaluationRequest,
    ProviderTimeoutError,
    ProviderUnavailableError,
    QuestionRequest,
)
from ai_growth_companion.providers.fake import FakeLLMProvider, FakeScenario
from ai_growth_companion.schemas.diagnosis import (
    ProviderObservation,
    QuestionDraft,
    validate_answer_excerpts,
)

ANSWER = "我用一个合成回答说明核心机制和边界。"


def evaluation_request() -> EvaluationRequest:
    return EvaluationRequest(
        concept="递归",
        question_text="请解释递归如何终止。",
        coverage_points=("基本情况", "规模缩小"),
        answer_text=ANSWER,
    )


@pytest.mark.parametrize(
    "scenario",
    [
        FakeScenario.STRONG,
        FakeScenario.PARTIAL,
        FakeScenario.MISCONCEPTION,
        FakeScenario.INSUFFICIENT_EVIDENCE,
    ],
)
def test_success_scenarios_return_valid_observations(scenario: FakeScenario) -> None:
    provider = FakeLLMProvider(scenario)

    first = provider.evaluate(evaluation_request(), request_id="request-1")
    second = provider.evaluate(evaluation_request(), request_id="request-1")
    observation = ProviderObservation.model_validate(first.content)

    assert first == second
    validate_answer_excerpts(observation, ANSWER)
    assert first.metadata.provider == "fake"
    assert first.metadata.usage == {"input_tokens": 0, "output_tokens": 0}


def test_question_is_structured_and_deterministic() -> None:
    provider = FakeLLMProvider()

    response = provider.generate_question(
        QuestionRequest(concept="机会成本"), request_id="question-request"
    )
    question = QuestionDraft.model_validate(response.content)

    assert question.concept == "机会成本"
    assert len(question.coverage_points) == 3
    assert response.metadata.schema_version == "question-v0.1"


def test_timeout_is_explicit_and_retryable() -> None:
    provider = FakeLLMProvider(FakeScenario.PROVIDER_TIMEOUT)

    with pytest.raises(ProviderTimeoutError) as captured:
        provider.evaluate(evaluation_request(), request_id="timeout-request")

    assert captured.value.code == "LLM_TIMEOUT"
    assert captured.value.retryable is True


def test_provider_failure_is_explicit_and_retryable() -> None:
    provider = FakeLLMProvider(FakeScenario.PROVIDER_FAILURE)

    with pytest.raises(ProviderUnavailableError) as captured:
        provider.evaluate(evaluation_request(), request_id="failure-request")

    assert captured.value.code == "LLM_UNAVAILABLE"
    assert captured.value.retryable is True


def test_invalid_schema_scenario_is_rejected() -> None:
    provider = FakeLLMProvider(FakeScenario.INVALID_SCHEMA)
    response = provider.evaluate(evaluation_request(), request_id="invalid-request")

    with pytest.raises(ValidationError):
        ProviderObservation.model_validate(response.content)


def test_insufficient_evidence_can_be_a_high_confidence_observation() -> None:
    provider = FakeLLMProvider(FakeScenario.INSUFFICIENT_EVIDENCE)
    response = provider.evaluate(evaluation_request(), request_id="insufficient-request")
    observation = ProviderObservation.model_validate(response.content)

    assert observation.observation_confidence == 0.85
    assert observation.evidence == []
    assert observation.possible_misconceptions == []
