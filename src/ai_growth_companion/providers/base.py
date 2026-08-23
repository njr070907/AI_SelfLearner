"""Provider-neutral request, response, and failure contracts."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class QuestionRequest:
    """Minimum context needed to generate one diagnostic question."""

    concept: str
    learning_goal: str | None = None
    learner_level: str | None = None


@dataclass(frozen=True)
class EvaluationRequest:
    """Minimum untrusted learner content sent for observation."""

    concept: str
    question_text: str
    coverage_points: tuple[str, ...]
    answer_text: str


@dataclass(frozen=True)
class ProviderMetadata:
    """Version and cost metadata saved with every provider attempt."""

    provider: str
    model: str
    model_revision: str | None
    prompt_version: str
    schema_version: str
    latency_ms: int
    usage: dict[str, int]
    finish_reason: str
    request_id: str


@dataclass(frozen=True)
class ProviderResponse:
    """Raw structured candidate that the application must validate."""

    content: Any
    metadata: ProviderMetadata


class ProviderError(RuntimeError):
    """Safe provider failure without response or user content leakage."""

    def __init__(self, message: str, *, code: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ProviderTimeoutError(ProviderError):
    """A retryable timeout."""

    def __init__(self) -> None:
        super().__init__("The provider timed out", code="LLM_TIMEOUT", retryable=True)


class ProviderUnavailableError(ProviderError):
    """A retryable provider availability failure."""

    def __init__(self) -> None:
        super().__init__("The provider is unavailable", code="LLM_UNAVAILABLE", retryable=True)


class EvaluationProvider(Protocol):
    """Provider behavior required by the evidence-extraction evaluation pipeline."""

    provider_name: str
    model_name: str
    model_revision: str | None

    def evaluate(self, request: EvaluationRequest, *, request_id: str) -> ProviderResponse:
        """Generate a raw structured observation candidate."""
        ...


class LLMProvider(EvaluationProvider, Protocol):
    """Full provider behavior visible to interactive application services."""

    def generate_question(self, request: QuestionRequest, *, request_id: str) -> ProviderResponse:
        """Generate a raw structured question candidate."""
        ...
