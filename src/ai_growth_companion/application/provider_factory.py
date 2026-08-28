"""Safe provider selection for the interactive learning service."""

from collections.abc import Callable

from ai_growth_companion.config import Settings
from ai_growth_companion.providers.base import (
    EvaluationRequest,
    LLMProvider,
    ProviderResponse,
    QuestionRequest,
)
from ai_growth_companion.providers.deepseek_evaluation import (
    DEEPSEEK_MODEL,
    DeepSeekEvaluationProvider,
)
from ai_growth_companion.providers.fake import FakeLLMProvider, FakeScenario
from ai_growth_companion.providers.ollama import (
    OllamaEvaluationProvider,
    OllamaInteractiveProvider,
    OllamaQuestionProvider,
)

ApplicationProviderFactory = Callable[[FakeScenario], LLMProvider]


class DeepSeekInteractiveProvider:
    """Use DeepSeek for evidence while keeping question generation deterministic."""

    provider_name = "deepseek"
    model_revision: str | None = None

    def __init__(self, evaluator: DeepSeekEvaluationProvider) -> None:
        self._evaluator = evaluator
        self.model_name = evaluator.model_name

    def generate_question(
        self,
        request: QuestionRequest,
        *,
        request_id: str,
    ) -> ProviderResponse:
        """Generate a local question until a separately versioned question provider exists."""
        return FakeLLMProvider(FakeScenario.PARTIAL).generate_question(
            request,
            request_id=request_id,
        )

    def evaluate(
        self,
        request: EvaluationRequest,
        *,
        request_id: str,
    ) -> ProviderResponse:
        """Delegate only evidence extraction to the fixed DeepSeek model."""
        return self._evaluator.evaluate(request, request_id=request_id)


def build_provider_factory(
    settings: Settings,
    *,
    paid_calls_allowed: bool = False,
    prompt_version: str = "v0.1",
    max_output_tokens: int = 1200,
) -> ApplicationProviderFactory:
    """Build a service factory with explicit, testable paid-call boundaries."""
    provider = settings.llm_provider.casefold()
    if provider == "fake":
        if paid_calls_allowed:
            raise ValueError("Fake mode cannot enable paid Provider calls")
        return lambda scenario: FakeLLMProvider(scenario)

    if provider == "ollama":
        quality_model = (
            settings.ollama_quality_model
            if settings.llm_model.casefold().startswith("fake")
            else settings.llm_model
        )
        ollama_evaluator = OllamaEvaluationProvider(
            model=quality_model,
            base_url=settings.ollama_base_url,
            timeout_seconds=settings.ollama_timeout_seconds,
            max_output_tokens=max_output_tokens,
            prompt_version=prompt_version,
        )
        questioner = OllamaQuestionProvider(
            model=settings.ollama_balanced_model,
            base_url=settings.ollama_base_url,
            timeout_seconds=settings.ollama_timeout_seconds,
            max_output_tokens=800,
        )
        interactive = OllamaInteractiveProvider(ollama_evaluator, questioner)
        return lambda _scenario: interactive

    if provider != "deepseek":
        raise ValueError("Interactive MVP supports only fake, ollama, or deepseek Provider mode")
    if not paid_calls_allowed:
        raise ValueError("DeepSeek mode requires explicit paid-call permission")
    if settings.llm_api_key is None:
        raise ValueError("DeepSeek mode requires LLM_API_KEY")
    if settings.llm_model != DEEPSEEK_MODEL:
        raise ValueError(f"DeepSeek model must be exactly {DEEPSEEK_MODEL}")

    deepseek_evaluator = DeepSeekEvaluationProvider(
        api_key=settings.llm_api_key.get_secret_value(),
        model=DEEPSEEK_MODEL,
        timeout_seconds=settings.llm_timeout_seconds,
        max_output_tokens=max_output_tokens,
        prompt_version=prompt_version,
    )
    return lambda _scenario: DeepSeekInteractiveProvider(deepseek_evaluator)
