"""DeepSeek Chat Completions adapter for evidence-only evaluation."""

from __future__ import annotations

import json
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

DEEPSEEK_MODEL = "deepseek-v4-flash-vision-exp"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class _UsageLike(Protocol):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class _MessageLike(Protocol):
    content: str | None
    refusal: str | None


class _ChoiceLike(Protocol):
    message: _MessageLike
    finish_reason: str | None


class _ChatCompletionLike(Protocol):
    id: str
    model: str
    choices: list[_ChoiceLike]
    usage: _UsageLike | None


class _ChatCompletionsLike(Protocol):
    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_format: dict[str, str],
        max_tokens: int,
        stream: bool,
        extra_body: dict[str, object],
    ) -> _ChatCompletionLike: ...


class _ChatLike(Protocol):
    completions: _ChatCompletionsLike


class _OpenAIClientLike(Protocol):
    chat: _ChatLike


class DeepSeekEvaluationProvider:
    """Call DeepSeek once and return locally validated candidate JSON."""

    provider_name = "deepseek"
    model_revision: str | None = None

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEEPSEEK_MODEL,
        timeout_seconds: int = 30,
        max_output_tokens: int = 1200,
        prompt_registry: PromptRegistry | None = None,
        client: _OpenAIClientLike | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("DeepSeek API key is required")
        if model != DEEPSEEK_MODEL:
            raise ValueError(f"DeepSeek model must be exactly {DEEPSEEK_MODEL}")
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
                base_url=DEEPSEEK_BASE_URL,
                timeout=float(timeout_seconds),
                max_retries=0,
            ),
        )

    def evaluate(self, request: EvaluationRequest, *, request_id: str) -> ProviderResponse:
        """Call DeepSeek Chat Completions with JSON mode and no automatic retry."""
        rendered = self._prompt_registry.render_evaluation(request)
        system_message = (
            f"{rendered.system_message}\n\n"
            "Return valid json only. Do not use Markdown fences or explanatory text.\n"
            "Treat coverage_points as the required scope: do not invent gaps for "
            "advanced prerequisites or deeper theories that are not listed there. "
            "When every listed point is explicitly and correctly established, leave "
            "gaps empty unless the answer contains a real contradiction or an "
            "explicitly requested part is missing."
        )
        started = perf_counter()
        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": rendered.user_message},
                ],
                response_format={"type": "json_object"},
                max_tokens=self._max_output_tokens,
                stream=False,
                extra_body={"thinking": {"type": "disabled"}},
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
            status_codes = {
                400: "LLM_REQUEST_REJECTED",
                401: "LLM_AUTH_FAILED",
                403: "LLM_FORBIDDEN",
                404: "LLM_MODEL_NOT_FOUND",
            }
            raise ProviderError(
                "The provider rejected the request",
                code=status_codes.get(error.status_code, "LLM_REQUEST_REJECTED"),
                retryable=False,
            ) from error
        except openai.OpenAIError as error:
            raise ProviderError(
                "The provider request failed",
                code="LLM_PROVIDER_ERROR",
                retryable=False,
            ) from error

        latency_ms = round((perf_counter() - started) * 1000)
        if not response.choices:
            raise ProviderError(
                "The provider returned no choices",
                code="LLM_OUTPUT_UNAVAILABLE",
                retryable=False,
            )
        choice = response.choices[0]
        if choice.message.refusal:
            raise ProviderError(
                "The provider refused the evaluation",
                code="LLM_OUTPUT_REFUSED",
                retryable=False,
            )
        if not choice.message.content:
            raise ProviderError(
                "The provider returned empty content",
                code="LLM_OUTPUT_UNAVAILABLE",
                retryable=False,
            )
        if choice.finish_reason == "length":
            raise ProviderError(
                "The provider output was truncated",
                code="LLM_OUTPUT_TRUNCATED",
                retryable=False,
            )
        try:
            content = self._parse_json_object(choice.message.content)
        except json.JSONDecodeError as error:
            raise ProviderError(
                "The provider returned invalid JSON",
                code="LLM_OUTPUT_INVALID",
                retryable=False,
            ) from error

        usage = response.usage
        usage_snapshot = {
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
        }
        returned_model = response.model or self.model_name
        return ProviderResponse(
            content=content,
            metadata=ProviderMetadata(
                provider=self.provider_name,
                model=self.model_name,
                model_revision=(returned_model if returned_model != self.model_name else None),
                prompt_version=f"{rendered.prompt_version}+deepseek-json",
                schema_version="provider-observation-v0.1",
                latency_ms=latency_ms,
                usage=usage_snapshot,
                finish_reason=choice.finish_reason or "unknown",
                request_id=response.id or request_id,
            ),
        )

    @staticmethod
    def _strip_json_fence(content: str) -> str:
        """Remove only an outer Markdown JSON fence; schema validation remains mandatory."""
        stripped = content.strip()
        if not stripped.startswith("```"):
            return stripped
        lines = stripped.splitlines()
        if lines and lines[0].strip().lower() in {"```", "```json"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    @classmethod
    def _parse_json_object(cls, content: str) -> object:
        """Parse JSON directly or recover one object wrapped in harmless prose."""
        stripped = cls._strip_json_fence(content)
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as original_error:
            decoder = json.JSONDecoder()
            for index, character in enumerate(stripped):
                if character != "{":
                    continue
                try:
                    candidate, _end = decoder.raw_decode(stripped[index:])
                except json.JSONDecodeError:
                    continue
                if isinstance(candidate, dict):
                    return candidate
            raise original_error
