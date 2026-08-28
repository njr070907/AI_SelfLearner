"""Offline safety tests for interactive Provider selection."""

import pytest

from ai_growth_companion.application.provider_factory import build_provider_factory
from ai_growth_companion.config import Settings
from ai_growth_companion.providers.base import QuestionRequest
from ai_growth_companion.providers.deepseek_evaluation import DEEPSEEK_MODEL
from ai_growth_companion.providers.fake import FakeScenario
from ai_growth_companion.providers.ollama import (
    OLLAMA_BALANCED_MODEL,
    OLLAMA_QUALITY_MODEL,
)


def test_fake_factory_is_free_and_deterministic() -> None:
    factory = build_provider_factory(Settings(_env_file=None))
    provider = factory(FakeScenario.STRONG)

    question = provider.generate_question(
        QuestionRequest(concept="极限"),
        request_id="factory-question",
    )

    assert provider.provider_name == "fake"
    assert question.metadata.provider == "fake"


def test_fake_mode_rejects_paid_permission() -> None:
    with pytest.raises(ValueError, match="cannot enable paid"):
        build_provider_factory(Settings(_env_file=None), paid_calls_allowed=True)


def test_deepseek_mode_requires_explicit_paid_permission() -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="deepseek",
        llm_model=DEEPSEEK_MODEL,
        llm_api_key="test-key",
    )

    with pytest.raises(ValueError, match="explicit paid-call permission"):
        build_provider_factory(settings)


def test_deepseek_factory_uses_fixed_model_and_local_question_without_network() -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="deepseek",
        llm_model=DEEPSEEK_MODEL,
        llm_api_key="test-key",
    )
    factory = build_provider_factory(settings, paid_calls_allowed=True)
    provider = factory(FakeScenario.PARTIAL)

    question = provider.generate_question(
        QuestionRequest(concept="导数"),
        request_id="deepseek-question",
    )

    assert provider.provider_name == "deepseek"
    assert provider.model_name == DEEPSEEK_MODEL
    assert question.metadata.provider == "fake"


def test_deepseek_factory_rejects_unapproved_model() -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="deepseek",
        llm_model="DeepSeek V4",
        llm_api_key="test-key",
    )

    with pytest.raises(ValueError, match="must be exactly"):
        build_provider_factory(settings, paid_calls_allowed=True)


def test_ollama_factory_routes_evaluation_to_quality_and_questions_to_balanced_model() -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="ollama",
        llm_model=OLLAMA_QUALITY_MODEL,
    )

    provider = build_provider_factory(settings)(FakeScenario.PARTIAL)

    assert provider.provider_name == "ollama"
    assert provider.model_name == OLLAMA_QUALITY_MODEL
    assert provider.question_model_name == OLLAMA_BALANCED_MODEL
