"""Validated runtime configuration with safe Sprint 0 defaults."""

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and an optional .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = "sqlite:///data/companion.db"
    llm_provider: str = "fake"
    llm_model: str = "fake-mastery-v0.1"
    llm_api_key: SecretStr | None = None
    llm_paid_calls_allowed: bool = False
    llm_timeout_seconds: int = Field(default=30, ge=1, le=120)
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    ollama_quality_model: str = "gpt-oss:20b"
    ollama_balanced_model: str = "qwen3.5:4b"
    ollama_fast_model: str = "qwen3.5:0.8b"
    ollama_timeout_seconds: int = Field(default=300, ge=1, le=600)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_content_enabled: bool = False
    telemetry_enabled: bool = False
    data_retention_days: int = Field(default=30, ge=1, le=3650)

    @model_validator(mode="after")
    def validate_security_boundaries(self) -> Self:
        """Reject configurations that could silently expose content or lack credentials."""
        if self.app_env == "production" and self.log_content_enabled:
            raise ValueError("LOG_CONTENT_ENABLED must be false in production")
        if self.llm_provider.casefold() not in {"fake", "ollama"} and not self.llm_api_key:
            raise ValueError("LLM_API_KEY is required when LLM_PROVIDER is not fake")
        return self

    @property
    def is_fake_mode(self) -> bool:
        """Return whether the deterministic Sprint 0 provider is selected."""
        return self.llm_provider.casefold() == "fake"


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """Load and cache validated settings for the running process."""
    return Settings()
