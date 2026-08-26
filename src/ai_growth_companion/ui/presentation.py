"""Chinese-first presentation mappings for the Streamlit product layer."""

from collections.abc import Iterable
from datetime import datetime
from enum import Enum

from ai_growth_companion.application.models import HistoryItem
from ai_growth_companion.providers.fake import FakeScenario

MASTERY_LABELS = {
    "solid": "理解较稳定",
    "developing": "理解正在形成",
    "fragile": "理解还不稳定",
    "no_clue": "完全未掌握",
    "not_evident": "完全未掌握",
}

ACTION_LABELS = {
    "practice": "进入练习",
    "re_learn": "重新学习",
    "re_explain": "重新学习",
    "review": "复习概念",
    "example": "换个例子",
}

ACTION_HEADINGS = {
    "practice": "下一步：用一道练习检验迁移",
    "re_learn": "下一步：重新学习核心概念",
    "re_explain": "下一步：重新学习核心概念",
    "review": "下一步：先复习关键概念",
    "example": "下一步：换一个例子建立联系",
}

STATUS_LABELS = {
    "created": "正在准备问题",
    "questioned": "等待你的解释",
    "answered": "等待诊断",
    "diagnosed": "诊断完成",
    "question_failed": "问题生成失败",
    "diagnosis_failed": "诊断待重试",
    "succeeded": "诊断完成",
    "failed": "诊断失败",
    "invalid": "诊断格式无效",
}

WRONG_ITEM_TYPE_LABELS = {
    "misconception": "明确误区",
    "gap": "关键缺口",
    "insufficient_evidence": "证据不足",
}

WRONG_ITEM_STATUS_LABELS = {
    "open": "待处理",
    "snoozed": "已暂缓",
    "mastered": "已掌握",
}

REVIEW_OUTCOME_LABELS = {
    "correct": "本次回答正确",
    "partial": "本次回答仍不完整",
    "incorrect": "本次回答需要纠正",
}

REVIEW_ATTEMPT_STATUS_LABELS = {
    "succeeded": "复测完成",
    "failed": "复测失败",
    "invalid": "结果格式无效",
}

CONCEPT_TREND_LABELS = {
    "insufficient_data": "证据还不足以判断趋势",
    "improving": "理解正在改善",
    "stable": "理解变化较稳定",
    "declining": "近期证据有所回落",
}

FEEDBACK_VERDICT_LABELS = {
    "accurate": "诊断准确",
    "partial": "部分准确",
    "inaccurate": "诊断不准确，需要修正",
}

SEVERITY_LABELS = {
    "low": "轻微",
    "medium": "重要",
    "high": "关键",
}

ERROR_MESSAGES = {
    "LLM_TIMEOUT": "诊断响应超时，本次解释已安全保存。",
    "LLM_UNAVAILABLE": "诊断服务暂时不可用，本次解释已安全保存。",
    "LLM_OUTPUT_INVALID": "诊断结果不符合结构化协议，本次解释已安全保存。",
    "LLM_OUTPUT_INVALID_JSON": "诊断结果不是可解析的结构化数据。",
    "LLM_OUTPUT_SCHEMA_INVALID": "诊断字段不符合当前协议。",
    "LLM_OUTPUT_EVIDENCE_INVALID": "诊断引用的证据不在本次解释中。",
}

SCENARIO_LABELS: dict[FakeScenario, str] = {
    FakeScenario.STRONG: "理解较完整（strong）",
    FakeScenario.PARTIAL: "部分理解（partial）",
    FakeScenario.MISCONCEPTION: "存在误区（misconception）",
    FakeScenario.INSUFFICIENT_EVIDENCE: "证据不足（insufficient evidence）",
    FakeScenario.PROVIDER_TIMEOUT: "模拟响应超时（timeout）",
    FakeScenario.PROVIDER_FAILURE: "模拟服务失败（failure）",
    FakeScenario.INVALID_SCHEMA: "模拟格式无效（invalid schema）",
}


def _value(value: str | Enum | None) -> str | None:
    if isinstance(value, Enum):
        return str(value.value)
    return value


def mastery_label(value: str | Enum | None) -> str:
    """Return a natural Chinese label without changing the stored enum value."""
    normalized = _value(value)
    if normalized is None:
        return "尚未形成诊断"
    return MASTERY_LABELS.get(normalized, normalized)


def action_label(value: str | Enum | None) -> str:
    """Return a concise Chinese CTA for a policy action."""
    normalized = _value(value)
    if normalized is None:
        return "等待下一步"
    return ACTION_LABELS.get(normalized, normalized)


def action_heading(value: str | Enum | None) -> str:
    normalized = _value(value)
    if normalized is None:
        return "下一步：等待诊断"
    return ACTION_HEADINGS.get(normalized, f"下一步：{action_label(normalized)}")


def status_label(value: str | Enum | None) -> str:
    normalized = _value(value)
    if normalized is None:
        return "未知状态"
    return STATUS_LABELS.get(normalized, normalized)


def severity_label(value: str | Enum) -> str:
    normalized = _value(value)
    assert normalized is not None
    return SEVERITY_LABELS.get(normalized, normalized)


def wrong_item_type_label(value: str | Enum) -> str:
    """Localize a backend-provided wrong-item classification."""
    normalized = _value(value)
    assert normalized is not None
    return WRONG_ITEM_TYPE_LABELS.get(normalized, normalized)


def wrong_item_status_label(value: str | Enum) -> str:
    """Localize a user-controlled wrong-item lifecycle status."""
    normalized = _value(value)
    assert normalized is not None
    return WRONG_ITEM_STATUS_LABELS.get(normalized, normalized)


def review_outcome_label(value: str | Enum | None) -> str:
    """Localize the scheduling outcome returned by the review service."""
    normalized = _value(value)
    if normalized is None:
        return "尚未复测"
    return REVIEW_OUTCOME_LABELS.get(normalized, normalized)


def review_attempt_status_label(value: str | Enum) -> str:
    """Localize a retest attempt status without inferring success."""
    normalized = _value(value)
    assert normalized is not None
    return REVIEW_ATTEMPT_STATUS_LABELS.get(normalized, normalized)


def concept_trend_label(value: str | Enum) -> str:
    """Localize the backend projection's longitudinal trend."""
    normalized = _value(value)
    assert normalized is not None
    return CONCEPT_TREND_LABELS.get(normalized, normalized)


def feedback_verdict_label(value: str | Enum) -> str:
    """Localize a learner feedback choice."""
    normalized = _value(value)
    assert normalized is not None
    return FEEDBACK_VERDICT_LABELS.get(normalized, normalized)


def error_message(error_code: str | None) -> str:
    return ERROR_MESSAGES.get(error_code or "", "诊断暂时失败，本次解释已安全保存。")


def local_datetime(value: datetime) -> str:
    return value.astimezone().strftime("%Y年%m月%d日 %H:%M")


def filter_history(items: Iterable[HistoryItem], query: str) -> tuple[HistoryItem, ...]:
    """Safely filter existing history without searching private answer content."""
    normalized = query.strip().casefold()
    if not normalized:
        return ()

    matches = []
    for item in items:
        searchable = " ".join(
            (
                item.concept,
                status_label(item.status),
                mastery_label(item.mastery_level),
                local_datetime(item.started_at),
            )
        ).casefold()
        if normalized in searchable:
            matches.append(item)
    return tuple(matches)
