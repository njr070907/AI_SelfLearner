"""Free deterministic provider for repeatable Sprint 0 scenarios."""

from enum import StrEnum

from ai_growth_companion.providers.base import (
    EvaluationRequest,
    ProviderMetadata,
    ProviderResponse,
    ProviderTimeoutError,
    ProviderUnavailableError,
    QuestionRequest,
    TeachingRequest,
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

    def __init__(
        self,
        scenario: FakeScenario = FakeScenario.PARTIAL,
        *,
        prompt_version: str = "v0.1",
    ) -> None:
        self.scenario = scenario
        self.prompt_version = prompt_version

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

    def generate_lesson(self, request: TeachingRequest, *, request_id: str) -> ProviderResponse:
        """Create a deterministic lesson card from uploaded text without network access."""
        excerpt = " ".join(request.source_text.split())[:900]
        source_refs = [
            {"document_id": document_id, "filename": filename, "excerpt": source_excerpt}
            for document_id, filename, source_excerpt in request.sources
        ]
        return ProviderResponse(
            content={
                "schema_version": "teaching-lesson-v0.2",
                "topic": request.topic,
                "title": f"{request.topic}：从材料到理解",
                "summary": (
                    f"这份导学先从材料中提炼 {request.topic} 的核心含义，再解释机制、边界和例子。"
                    f"材料摘要：{excerpt}"
                ),
                "learning_objectives": [
                    f"说清楚 {request.topic} 是什么",
                    f"解释 {request.topic} 为什么成立或如何运作",
                    "指出一个适用边界并举出例子",
                ],
                "sections": [
                    {
                        "section_type": "concept",
                        "title": "先建立概念",
                        "explanation": (
                            f"先用自己的话回答：{request.topic} 解决什么问题？"
                            "材料中最重要的定义或对象是什么？"
                        ),
                        "key_points": ["对象或定义", "要解决的问题", "与相近概念的区别"],
                        "example": f"从材料中找一个能代表 {request.topic} 的最小例子。",
                    },
                    {
                        "section_type": "mechanism",
                        "title": "再理解核心机制",
                        "explanation": (
                            "把过程拆成有顺序的步骤，说明每一步为什么会发生，不要只抄结论或公式。"
                        ),
                        "key_points": ["输入是什么", "中间如何变化", "输出如何产生"],
                        "example": "尝试用一个具体情境走完这条过程。",
                    },
                    {
                        "section_type": "boundary",
                        "title": "最后检查边界",
                        "explanation": (
                            "学习不只包括‘怎么做’，还要知道什么时候不能这样做，"
                            "以及缺少什么条件会失效。"
                        ),
                        "key_points": ["适用条件", "常见误区", "失效或需要补充的情况"],
                        "example": "构造一个看似相同、但条件不满足的反例。",
                    },
                    {
                        "section_type": "example",
                        "title": "用例子复述",
                        "explanation": (
                            "不看原文，用一个新例子复述定义、机制和边界；这一步完成后再做互动小测。"
                        ),
                        "key_points": ["新例子", "关键步骤", "边界提醒"],
                        "example": f"请用一个未出现在材料中的例子说明 {request.topic}。",
                    },
                ],
                "check_questions": [
                    f"如果要向初学者解释 {request.topic}，你会先讲什么？为什么？",
                    f"在什么条件下 {request.topic} 的常见做法会失效？",
                ],
                "interactive_checks": [
                    {
                        "prompt": f"下面哪一种学习方式最适合先掌握 {request.topic}？",
                        "options": [
                            "先理解概念和用途，再看具体例子",
                            "只背诵材料中的最后一句总结",
                            "跳过条件，直接记住一个固定答案",
                        ],
                        "correct_answer": "先理解概念和用途，再看具体例子",
                        "explanation": (
                            "常规学习应先建立概念，再通过例子和边界把知识连接起来；"
                            "只背结论无法判断什么时候适用。"
                        ),
                    },
                    {
                        "prompt": f"学习 {request.topic} 时，遇到一个新例子最应该先检查什么？",
                        "options": [
                            "它是否满足适用条件",
                            "它是否和教材的句子完全一样",
                            "它是否看起来足够复杂",
                        ],
                        "correct_answer": "它是否满足适用条件",
                        "explanation": "先检查条件，才能判断知识能否迁移到新情境。",
                    },
                ],
                "sources": source_refs,
            },
            metadata=self._metadata(
                request_id=request_id,
                prompt_version="fake-teaching-v0.2",
                schema_version="teaching-lesson-v0.2",
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
                prompt_version=f"fake-evaluator-{self.prompt_version}",
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
                "observation_confidence": 0.95,
                "limitations": ["错误概念来自选定的 Fake 场景，而非真实语义判断"],
            }
        if self.scenario is FakeScenario.INSUFFICIENT_EVIDENCE:
            return {
                "schema_version": "provider-observation-v0.1",
                "evidence": [],
                "gaps": [{"description": "当前回答不足以判断核心机制", "severity": "high"}],
                "possible_misconceptions": [],
                "observation_confidence": 0.85,
                "limitations": ["可判断当前未掌握，但无法从回答定位具体误区"],
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
