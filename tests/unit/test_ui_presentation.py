"""Presentation mappings keep domain values stable while rendering natural Chinese."""

import pytest

from ai_growth_companion.schemas.diagnosis import ActionType, MasteryLevel
from ai_growth_companion.ui.presentation import (
    action_label,
    error_message,
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
