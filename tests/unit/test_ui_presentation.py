"""Presentation mappings keep domain values stable while rendering natural Chinese."""

from datetime import UTC, datetime

import pytest

from ai_growth_companion.application.models import HistoryItem
from ai_growth_companion.domain.feedback import ConceptTrend, FeedbackVerdict
from ai_growth_companion.domain.review import ReviewAttemptStatus, ReviewOutcome
from ai_growth_companion.domain.wrong_items import WrongItemStatus, WrongItemType
from ai_growth_companion.schemas.diagnosis import ActionType, MasteryLevel
from ai_growth_companion.ui.presentation import (
    action_label,
    concept_trend_label,
    error_message,
    feedback_verdict_label,
    filter_history,
    mastery_label,
    review_attempt_status_label,
    review_outcome_label,
    status_label,
    wrong_item_status_label,
    wrong_item_type_label,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (MasteryLevel.SOLID, "理解较稳定"),
        (MasteryLevel.DEVELOPING, "理解正在形成"),
        (MasteryLevel.FRAGILE, "理解还不稳定"),
        (MasteryLevel.NO_CLUE, "完全未掌握"),
    ],
)
def test_mastery_values_have_chinese_presentation_labels(
    value: MasteryLevel,
    expected: str,
) -> None:
    assert mastery_label(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (ActionType.PRACTICE, "进入练习"),
        (ActionType.RE_LEARN, "重新学习"),
        (ActionType.REVIEW, "复习概念"),
        (ActionType.EXAMPLE, "换个例子"),
    ],
)
def test_action_values_have_chinese_button_labels(value: ActionType, expected: str) -> None:
    assert action_label(value) == expected


@pytest.mark.parametrize(
    ("code", "fragment"),
    [
        ("LLM_TIMEOUT", "超时"),
        ("LLM_UNAVAILABLE", "暂时不可用"),
        ("LLM_OUTPUT_INVALID", "结构化协议"),
    ],
)
def test_provider_errors_have_safe_actionable_copy(code: str, fragment: str) -> None:
    message = error_message(code)
    assert fragment in message
    assert "已安全保存" in message


def test_session_status_is_localized_without_changing_the_value() -> None:
    assert status_label("questioned") == "等待你的解释"
    assert status_label("diagnosed") == "诊断完成"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (WrongItemType.MISCONCEPTION, "明确误区"),
        (WrongItemType.GAP, "关键缺口"),
        (WrongItemType.INSUFFICIENT_EVIDENCE, "证据不足"),
    ],
)
def test_wrong_item_types_have_chinese_labels(
    value: WrongItemType,
    expected: str,
) -> None:
    assert wrong_item_type_label(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (WrongItemStatus.OPEN, "待处理"),
        (WrongItemStatus.SNOOZED, "已暂缓"),
        (WrongItemStatus.MASTERED, "已掌握"),
    ],
)
def test_wrong_item_statuses_have_chinese_labels(
    value: WrongItemStatus,
    expected: str,
) -> None:
    assert wrong_item_status_label(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (ReviewOutcome.CORRECT, "本次回答正确"),
        (ReviewOutcome.PARTIAL, "本次回答仍不完整"),
        (ReviewOutcome.INCORRECT, "本次回答需要纠正"),
        (None, "尚未复测"),
    ],
)
def test_review_outcomes_have_chinese_labels(
    value: ReviewOutcome | None,
    expected: str,
) -> None:
    assert review_outcome_label(value) == expected


def test_review_failure_status_has_a_safe_label() -> None:
    assert review_attempt_status_label(ReviewAttemptStatus.FAILED) == "复测失败"


def test_longitudinal_state_and_feedback_choices_have_chinese_labels() -> None:
    assert concept_trend_label(ConceptTrend.IMPROVING) == "理解正在改善"
    assert feedback_verdict_label(FeedbackVerdict.INACCURATE) == "诊断不准确，需要修正"


def history_item(
    *,
    session_id: str,
    concept: str,
    status: str,
    mastery_level: str | None,
) -> HistoryItem:
    return HistoryItem(
        session_id=session_id,
        concept=concept,
        status=status,
        mastery_level=mastery_level,
        confidence=None,
        started_at=datetime(2026, 8, 24, 8, 0, tzinfo=UTC),
    )


def test_search_filters_real_history_by_concept_status_and_mastery() -> None:
    history = (
        history_item(
            session_id="one",
            concept="递归",
            status="diagnosed",
            mastery_level="solid",
        ),
        history_item(
            session_id="two",
            concept="机会成本",
            status="questioned",
            mastery_level=None,
        ),
    )

    assert [item.session_id for item in filter_history(history, "递归")] == ["one"]
    assert [item.session_id for item in filter_history(history, "诊断完成")] == ["one"]
    assert [item.session_id for item in filter_history(history, "理解较稳定")] == ["one"]
    assert [item.session_id for item in filter_history(history, "等待你的解释")] == ["two"]


def test_search_returns_no_results_for_blank_or_unknown_query() -> None:
    history = (
        history_item(
            session_id="one",
            concept="递归",
            status="diagnosed",
            mastery_level="solid",
        ),
    )

    assert filter_history(history, "   ") == ()
    assert filter_history(history, "不存在") == ()
