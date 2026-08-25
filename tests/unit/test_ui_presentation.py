"""Presentation mappings keep domain values stable while rendering natural Chinese."""

from datetime import UTC, datetime

import pytest

from ai_growth_companion.application.models import HistoryItem
from ai_growth_companion.schemas.diagnosis import ActionType, MasteryLevel
from ai_growth_companion.ui.presentation import (
    action_label,
    error_message,
    filter_history,
    mastery_label,
    status_label,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (MasteryLevel.SOLID, "理解较稳定"),
        (MasteryLevel.DEVELOPING, "理解正在形成"),
        (MasteryLevel.FRAGILE, "理解还不稳定"),
        (MasteryLevel.NOT_EVIDENT, "暂无足够掌握证据"),
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
        (ActionType.RE_EXPLAIN, "再解释一次"),
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
