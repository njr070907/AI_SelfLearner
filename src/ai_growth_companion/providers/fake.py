"""Free deterministic provider for repeatable Sprint 0 scenarios."""

from enum import StrEnum

from ai_growth_companion.providers.base import (
    EvaluationRequest,
    ProviderMetadata,
    ProviderResponse,
    ProviderTimeoutError,
    ProviderUnavailableError,
    QuestionRequest,
)


class FakeScenario(StrEnum):
    """Supported deterministic paths, including failures."""

    STRONG = "strong"
    PARTIAL = "partial"
    MISCONCEPTION = "misconception"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_FAILURE = "provider_failure"
    INVALID_SCHEMA = "invalid_schema"


class FakeLLMProvider:
    """Return predictable fixtures without calling a network or paid model."""

    provider_name: str = "fake"
    model_name: str = "fake-mastery-v0.1"
    model_revision: str | None = "deterministic-1"

    def __init__(self, scenario: FakeScenario = FakeScenario.PARTIAL) -> None:
        self.scenario = scenario

    def _metadata(
        self,
        *,
        request_id: str,
        prompt_version: str,
        schema_version: str,
    ) -> ProviderMetadata:
        return ProviderMetadata(
            provider=self.provider_name,
            model=self.model_name,
            model_revision=self.model_revision,
            prompt_version=prompt_version,
            schema_version=schema_version,
            latency_ms=5,
            usage={"input_tokens": 0, "output_tokens": 0},
            finish_reason="stop",
            request_id=request_id,
        )

    def generate_question(self, request: QuestionRequest, *, request_id: str) -> ProviderResponse:
        """Return one generic mechanism question for the selected concept."""
        return ProviderResponse(
            content={
                "schema_version": "question-v0.1",
                "concept": request.concept,
                "question_text": (
                    f"请不用背诵定义，用自己的话解释“{request.concept}”为什么成立、"
                    "它如何运作，以及在什么情况下可能不适用。"
                ),
                "coverage_points": ["核心含义", "运作机制", "适用边界"],
                "difficulty": "introductory",
                "question_type": "mechanism",
            },
            metadata=self._metadata(
                request_id=request_id,
                prompt_version="fake-question-v0.1",
                schema_version="question-v0.1",
            ),
        )

    def evaluate(self, request: EvaluationRequest, *, request_id: str) -> ProviderResponse:
        """Return the configured success, uncertainty, or failure scenario."""
        if self.scenario is FakeScenario.PROVIDER_TIMEOUT:
            raise ProviderTimeoutError
        if self.scenario is FakeScenario.PROVIDER_FAILURE:
            raise ProviderUnavailableError

        excerpt = self._excerpt(request.answer_text)
        content = self._content_for(excerpt)
        return ProviderResponse(
            content=content,
            metadata=self._metadata(
                request_id=request_id,
                prompt_version="fake-evaluator-v0.1",
                schema_version="provider-observation-v0.1",
            ),
        )

    @staticmethod
    def _excerpt(answer: str) -> str:
        stripped = answer.strip()
        return stripped[:120] if stripped else "无有效回答"

    def _content_for(self, excerpt: str) -> dict[str, object]:
        if self.scenario is FakeScenario.STRONG:
            return {
                "schema_version": "provider-observation-v0.1",
                "evidence": [
                    {
                        "evidence_id": "fake-evidence-strong-1",
                        "claim": "回答覆盖了核心机制和适用边界",
                        "answer_excerpt": excerpt,
                        "strength": "strong",
                    }
                ],
                "gaps": [],
                "possible_misconceptions": [],
                "observation_confidence": 0.9,
                "limitations": ["Fake 场景仅用于验证产品管道"],
            }
        if self.scenario is FakeScenario.MISCONCEPTION:
            return {
                "schema_version": "provider-observation-v0.1",
                "evidence": [],
                "gaps": [],
                "possible_misconceptions": [
                    {
                        "description": "回答中包含一个用于测试的明确错误概念",
                        "confidence": 0.9,
                        "answer_excerpt": excerpt,
                    }
                ],
                "observation_confidence": 0.85,
                "limitations": ["错误概念来自选定的 Fake 场景，而非真实语义判断"],
            }
        if self.scenario is FakeScenario.INSUFFICIENT_EVIDENCE:
            return {
                "schema_version": "provider-observation-v0.1",
                "evidence": [],
                "gaps": [{"description": "当前回答不足以判断核心机制", "severity": "high"}],
                "possible_misconceptions": [],
                "observation_confidence": 0.2,
                "limitations": ["需要更多解释或一个高信息量追问"],
            }
        if self.scenario is FakeScenario.INVALID_SCHEMA:
            return {
                "schema_version": "provider-observation-v0.1",
                "observation_confidence": 1.5,
                "unexpected": "this payload must be rejected",
            }
        return {
            "schema_version": "provider-observation-v0.1",
            "evidence": [
                {
                    "evidence_id": "fake-evidence-partial-1",
                    "claim": "回答表达了部分相关理解",
                    "answer_excerpt": excerpt,
                    "strength": "medium",
                }
            ],
            "gaps": [{"description": "尚未完整解释运作机制", "severity": "medium"}],
            "possible_misconceptions": [],
            "observation_confidence": 0.65,
            "limitations": ["Fake 场景不评价回答的真实知识正确性"],
        }
