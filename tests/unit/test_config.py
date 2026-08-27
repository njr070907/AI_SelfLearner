"""Configuration boundary tests."""

import pytest
from pydantic import ValidationError

from ai_growth_companion.config import Settings


def test_default_configuration_uses_fake_provider_without_key() -> None:
    settings = Settings(_env_file=None)

    assert settings.is_fake_mode is True
    assert settings.llm_api_key is None
    assert settings.llm_paid_calls_allowed is False
    assert settings.log_content_enabled is False


def test_external_provider_requires_api_key() -> None:
    with pytest.raises(ValidationError, match="LLM_API_KEY is required"):
        Settings(_env_file=None, llm_provider="external", llm_api_key=None)


def test_ollama_provider_does_not_require_an_api_key() -> None:
    settings = Settings(_env_file=None, llm_provider="ollama", llm_model="gpt-oss:20b")

    assert settings.llm_api_key is None
    assert settings.ollama_quality_model == "gpt-oss:20b"
    assert settings.ollama_balanced_model == "qwen3.5:4b"
    assert settings.ollama_fast_model == "qwen3.5:0.8b"


def test_production_rejects_content_logging() -> None:
    with pytest.raises(ValidationError, match="LOG_CONTENT_ENABLED must be false"):
        Settings(_env_file=None, app_env="production", log_content_enabled=True)


def test_api_key_is_redacted_in_settings_representation() -> None:
    secret = "synthetic-test-secret"
    settings = Settings(_env_file=None, llm_provider="external", llm_api_key=secret)

    assert secret not in repr(settings)
