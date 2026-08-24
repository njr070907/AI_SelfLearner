"""Rendered Streamlit flow tests using Streamlit's official AppTest harness."""

from pathlib import Path

import pytest
from pytest import MonkeyPatch
from streamlit.testing.v1 import AppTest

from ai_growth_companion.config import load_settings
from ai_growth_companion.repositories.database import Database, run_migrations
from ai_growth_companion.ui.state import AccentTheme, ThemeMode

APP_PATH = Path(__file__).resolve().parents[2] / "app.py"


def app_for(tmp_path: Path, monkeypatch: MonkeyPatch, name: str) -> AppTest:
    database_url = f"sqlite:///{(tmp_path / name).as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    load_settings.cache_clear()
    run_migrations(Database(database_url))
    return AppTest.from_file(APP_PATH).run(timeout=10)


def rendered_markdown(app: AppTest) -> str:
    return "\n".join(item.value for item in app.markdown)


def button_with_label(app: AppTest, label: str):  # type: ignore[no-untyped-def]
    return next(item for item in app.button if item.label == label)


def input_with_label(app: AppTest, label: str):  # type: ignore[no-untyped-def]
    return next(item for item in app.text_input if item.label == label)


def select_with_label(app: AppTest, label: str):  # type: ignore[no-untyped-def]
    return next(item for item in app.selectbox if item.label == label)


def open_learn(app: AppTest) -> AppTest:
    return (
        next(item for item in app.sidebar.button if item.key == "nav_learn").click().run(timeout=10)
    )


def start_session(app: AppTest) -> AppTest:
    app = open_learn(app)
    input_with_label(app, "学习主题").input("递归")
    return button_with_label(app, "生成费曼问题").click().run(timeout=10)


def submit_scenario(app: AppTest, scenario: str) -> AppTest:
    app.text_area[0].input("我用一个合成回答说明递归的机制、边界和例子。")
    select_with_label(app, "诊断场景").select(scenario)
    return button_with_label(app, "提交解释并查看诊断").click().run(timeout=10)


def test_first_visit_has_a_clear_empty_state(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = app_for(tmp_path, monkeypatch, "ui-empty.db")

    assert not app.exception
    assert "还没有学习记录" in rendered_markdown(app)
    assert button_with_label(app, "开始第一次学习")


def test_user_can_complete_fake_diagnosis_in_rendered_app(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = submit_scenario(
        start_session(app_for(tmp_path, monkeypatch, "ui-success.db")),
        "strong",
    )

    assert not app.exception
    page = rendered_markdown(app)
    assert "理解较稳定" in page
    assert "你已经讲清楚的部分" in page
    assert "还缺少的关键点" in page
    assert "下一步" in page
    assert not app.error


@pytest.mark.parametrize(
    ("scenario", "mastery_copy", "action_copy"),
    [
        ("partial", "理解还不稳定", "再解释一次"),
        ("misconception", "理解还不稳定", "复习概念"),
        ("insufficient_evidence", "暂无足够掌握证据", "再解释一次"),
    ],
)
def test_success_scenarios_render_the_expected_diagnosis_and_action(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    scenario: str,
    mastery_copy: str,
    action_copy: str,
) -> None:
    app = submit_scenario(
        start_session(app_for(tmp_path, monkeypatch, f"ui-{scenario}.db")),
        scenario,
    )

    assert not app.exception
    page = rendered_markdown(app)
    assert mastery_copy in page
    assert action_copy in page or any(action_copy in button.label for button in app.button)


@pytest.mark.parametrize(
    ("scenario", "error_fragment"),
    [
        ("provider_timeout", "超时"),
        ("provider_failure", "暂时不可用"),
        ("invalid_schema", "结构化协议"),
    ],
)
def test_rendered_provider_errors_keep_the_answer_and_offer_retry(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    scenario: str,
    error_fragment: str,
) -> None:
    app = submit_scenario(
        start_session(app_for(tmp_path, monkeypatch, f"ui-{scenario}.db")),
        scenario,
    )

    assert not app.exception
    assert app.error
    assert error_fragment in app.error[0].value
    assert app.info
    assert button_with_label(app, "使用已保存的解释重试")


def test_failed_diagnosis_can_retry_with_saved_answer(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = submit_scenario(
        start_session(app_for(tmp_path, monkeypatch, "ui-retry.db")),
        "provider_timeout",
    )
    select_with_label(app, "重试时使用的 Fake 场景").select("strong")
    app = button_with_label(app, "使用已保存的解释重试").click().run(timeout=10)

    assert not app.exception
    assert "理解较稳定" in rendered_markdown(app)
    assert not app.error


def test_theme_accent_and_sidebar_controls_update_ui_state(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = app_for(tmp_path, monkeypatch, "ui-appearance.db")

    select_with_label(app, "强调色").select(AccentTheme.GREEN)
    app = app.run(timeout=10)
    assert app.session_state["ui_accent_theme"] is AccentTheme.GREEN

    app = button_with_label(app, "浅色").click().run(timeout=10)
    assert app.session_state["ui_theme_mode"] is ThemeMode.DARK

    collapse = next(item for item in app.sidebar.button if item.key == "sidebar_toggle")
    app = collapse.click().run(timeout=10)
    assert app.session_state["ui_sidebar_collapsed"] is True


def test_search_filters_real_history_and_opens_progress(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = submit_scenario(
        start_session(app_for(tmp_path, monkeypatch, "ui-search.db")),
        "strong",
    )

    input_with_label(app, "搜索学习历史").input("递归")
    app = app.run(timeout=10)
    assert "搜索结果" in rendered_markdown(app)
    assert "递归" in rendered_markdown(app)

    app = button_with_label(app, "打开").click().run(timeout=10)
    assert app.session_state["active_page"] == "进度"
    assert "看见理解如何变化" in rendered_markdown(app)
