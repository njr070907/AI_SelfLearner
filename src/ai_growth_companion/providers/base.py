"""Provider-neutral request, response, and failure contracts."""

from dataclasses import dataclass
from typing import Any, Protocol

from ai_growth_companion.schemas.teaching import TeachingPlan


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
class TeachingRequest:
    """Untrusted uploaded knowledge and context used to draft one lesson."""

    topic: str
    source_text: str
    sources: tuple[tuple[str, str, str], ...]
    learning_goal: str | None = None
    learner_level: str | None = None
    output_language: str = "zh-CN"
    source_units: tuple["TeachingSourceUnit", ...] = ()
    visual_pages: tuple["TeachingPageImage", ...] = ()
    teaching_plan: TeachingPlan | None = None


@dataclass(frozen=True)
class TeachingPlanRequest:
    """Bounded source context supplied to the local planner role."""

    topic: str
    source_text: str
    source_units: tuple["TeachingSourceUnit", ...] = ()
    source_document_ids: tuple[str, ...] = ()
    learning_goal: str | None = None
    learner_level: str | None = None
    output_language: str = "zh-CN"


@dataclass(frozen=True)
class TeachingSourceUnit:
    """A bounded, page-aware source block supplied to a teaching Provider."""

    document_id: str
    filename: str
    page_number: int | None
    text: str
    quality: str = "clear"
    # Optional derived text used to help a Chinese-language lesson model understand
    # an English source. ``text`` always remains the canonical original used for
    # evidence quotes and page-level verification.
    translated_text: str | None = None


@dataclass(frozen=True)
class TeachingPageImage:
    """One local PDF page rendered for an explicitly requested vision call."""

    document_id: str
    filename: str
    page_number: int
    media_type: str
    content: bytes


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


@dataclass(frozen=True)
class TranslationRequest:
    """A bounded source fragment to translate without changing its meaning."""

    text: str
    source_language: str = "en"
    target_language: str = "zh-CN"


@dataclass(frozen=True)
class TopicSuggestionRequest:
    """Source material used to propose learner-selectable study topics."""

    source_text: str
    source_labels: tuple[tuple[str, str], ...] = ()
    max_topics: int = 8
    output_language: str = "zh-CN"


class TranslationProvider(Protocol):
    """Provider contract for optional, best-effort source translation."""

    provider_name: str
    model_name: str
    model_revision: str | None

    def translate(self, request: TranslationRequest, *, request_id: str) -> ProviderResponse:
        """Return a translated fragment while preserving the original separately."""
        ...


class TopicSuggestionProvider(Protocol):
    """Provider contract for deriving topic choices from uploaded material."""

    provider_name: str
    model_name: str
    model_revision: str | None

    def suggest_topics(
        self,
        request: TopicSuggestionRequest,
        *,
        request_id: str,
    ) -> ProviderResponse:
        """Return structured, Chinese learner-facing topic candidates."""
        ...


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


class TeachingProvider(Protocol):
    """Provider behavior required to turn uploaded knowledge into a lesson."""

    provider_name: str
    model_name: str
    model_revision: str | None
    supports_vision: bool

    def generate_lesson(self, request: TeachingRequest, *, request_id: str) -> ProviderResponse:
        """Generate a raw structured lesson candidate."""
        ...


class TeachingPlanProvider(Protocol):
    """Optional role provider that designs a dependency-aware teaching route."""

    provider_name: str
    model_name: str
    model_revision: str | None

    def generate_plan(
        self,
        request: TeachingPlanRequest,
        *,
        request_id: str,
    ) -> ProviderResponse:
        """Return a raw plan candidate; the application validates or replaces it."""
        ...


class TeachingEvidenceRepairProvider(Protocol):
    """Optional bounded repair capability for real structured-output Providers."""

    def repair_lesson_evidence(
        self,
        request: TeachingRequest,
        lesson_content: dict[str, object],
        *,
        request_id: str,
    ) -> ProviderResponse:
        """Fill only missing source evidence without rewriting lesson prose."""
        ...


class TeachingCompletionProvider(Protocol):
    """Optional bounded completion capability for incomplete lesson JSON."""

    def complete_lesson(
        self,
        request: TeachingRequest,
        lesson_content: dict[str, object],
        *,
        request_id: str,
    ) -> ProviderResponse:
        """Complete missing lesson fields while retaining the original source boundary."""
        ...
