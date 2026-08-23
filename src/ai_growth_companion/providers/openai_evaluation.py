"""OpenAI Responses API adapter for evidence-only learner-answer evaluation."""

from __future__ import annotations

from time import perf_counter
from typing import Protocol, cast

import openai
from openai import OpenAI

from ai_growth_companion.prompts.registry import PromptRegistry
from ai_growth_companion.providers.base import (
    EvaluationRequest,
    ProviderError,
    ProviderMetadata,
    ProviderResponse,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from ai_growth_companion.schemas.diagnosis import ProviderObservation


class _UsageLike(Protocol):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class _ParsedResponseLike(Protocol):
    id: str
    model: str
    status: str | None
    output_parsed: ProviderObservation | None
    usage: _UsageLike | None


class _ResponsesLike(Protocol):
    def parse(
        self,
        *,
        model: str,
        instructions: str,
        input: str,
        text_format: type[ProviderObservation],
        max_output_tokens: int,
        store: bool,
    ) -> _ParsedResponseLike: ...


class _OpenAIClientLike(Protocol):
    responses: _ResponsesLike


class OpenAIEvaluationProvider:
    """Extract a strict observation while leaving mastery decisions to local code."""

    provider_name = "openai"
    model_revision: str | None = None

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int = 30,
        max_output_tokens: int = 1200,
        prompt_registry: PromptRegistry | None = None,
        client: _OpenAIClientLike | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("OpenAI API key is required")
        if not model.strip() or model.lower().startswith("fake"):
            raise ValueError("A non-Fake OpenAI model name is required")
        if not 1 <= timeout_seconds <= 120:
            raise ValueError("timeout_seconds must be between 1 and 120")
        if not 100 <= max_output_tokens <= 5000:
            raise ValueError("max_output_tokens must be between 100 and 5000")

        self.model_name = model
        self._max_output_tokens = max_output_tokens
        self._prompt_registry = prompt_registry or PromptRegistry()
        self._client = client or cast(
            _OpenAIClientLike,
            OpenAI(
                api_key=api_key,
                timeout=float(timeout_seconds),
                max_retries=0,
            ),
        )

    def evaluate(self, request: EvaluationRequest, *, request_id: str) -> ProviderResponse:
        """Call OpenAI once, returning only validated structured evidence and safe metadata."""
        rendered = self._prompt_registry.render_evaluation(request)
        started = perf_counter()
        try:
            response = self._client.responses.parse(
                model=self.model_name,
                instructions=rendered.system_message,
                input=rendered.user_message,
                text_format=ProviderObservation,
                max_output_tokens=self._max_output_tokens,
                store=False,
            )
        except openai.APITimeoutError as error:
            raise ProviderTimeoutError from error
        except openai.RateLimitError as error:
            raise ProviderError(
                "The provider rate limit was reached",
                code="LLM_RATE_LIMIT",
                retryable=True,
            ) from error
        except openai.APIConnectionError as error:
            raise ProviderUnavailableError from error
        except openai.APIStatusError as error:
            if error.status_code >= 500:
                raise ProviderUnavailableError from error
            raise ProviderError(
                "The provider rejected the request",
                code="LLM_REQUEST_REJECTED",
                retryable=False,
            ) from error
        except openai.OpenAIError as error:
            raise ProviderError(
                "The provider request failed",
                code="LLM_PROVIDER_ERROR",
                retryable=False,
            ) from error

        latency_ms = round((perf_counter() - started) * 1000)
        if response.status != "completed" or response.output_parsed is None:
            raise ProviderError(
                "The provider did not return a complete structured observation",
                code="LLM_OUTPUT_UNAVAILABLE",
                retryable=False,
            )

        usage = response.usage
        usage_snapshot = {
            "input_tokens": usage.input_tokens if usage else 0,
            "output_tokens": usage.output_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
        }
        returned_model = response.model or self.model_name
        return ProviderResponse(
            content=response.output_parsed,
            metadata=ProviderMetadata(
                provider=self.provider_name,
                model=self.model_name,
                model_revision=(returned_model if returned_model != self.model_name else None),
                prompt_version=rendered.prompt_version,
                schema_version="provider-observation-v0.1",
                latency_ms=latency_ms,
                usage=usage_snapshot,
                finish_reason=response.status,
                request_id=response.id or request_id,
            ),
        )
