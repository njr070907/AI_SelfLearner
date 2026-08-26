"""Rendered Streamlit flow tests using Streamlit's official AppTest harness."""

from pathlib import Path

import pytest
from pytest import MonkeyPatch
from streamlit.testing.v1 import AppTest

from ai_growth_companion.application.demo_workspace import seed_fake_workspace
from ai_growth_companion.config import load_settings
from ai_growth_companion.domain.review import ReviewAttemptStatus, ReviewOutcome
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


def app_for_real_provider(tmp_path: Path, monkeypatch: MonkeyPatch, name: str) -> AppTest:
    database_url = f"sqlite:///{(tmp_path / name).as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("LLM_MODEL", "deepseek-v4-flash-vision-exp")
    monkeypatch.setenv("LLM_API_KEY", "synthetic-key")
    monkeypatch.setenv("LLM_PAID_CALLS_ALLOWED", "true")
    load_settings.cache_clear()
    run_migrations(Database(database_url))
    return AppTest.from_file(APP_PATH).run(timeout=10)


def app_for_seeded(tmp_path: Path, monkeypatch: MonkeyPatch, name: str) -> AppTest:
    database_url = f"sqlite:///{(tmp_path / name).as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("LLM_PAID_CALLS_ALLOWED", "false")
    load_settings.cache_clear()
    seed_fake_workspace(database_url, seed_name=name)
    return AppTest.from_file(APP_PATH).run(timeout=10)


def rendered_markdown(app: AppTest) -> str:
    return "\n".join(item.value for item in app.markdown)


def button_with_label(app: AppTest, label: str):  # type: ignore[no-untyped-def]
    return next(item for item in app.button if item.label == label)


def input_with_label(app: AppTest, label: str):  # type: ignore[no-untyped-def]
    return next(item for item in app.text_input if item.label == label)


def text_area_with_label(app: AppTest, label: str):  # type: ignore[no-untyped-def]
    return next(item for item in app.text_area if item.label == label)


def select_with_label(app: AppTest, label: str):  # type: ignore[no-untyped-def]
    return next(item for item in app.selectbox if item.label == label)


def open_learn(app: AppTest) -> AppTest:
    return (
        next(item for item in app.sidebar.button if item.key == "nav_learn").click().run(timeout=10)
    )


def open_mistakes(app: AppTest) -> AppTest:
    return (
        next(item for item in app.sidebar.button if item.key == "nav_mistakes")
        .click()
        .run(timeout=10)
    )


def open_review(app: AppTest) -> AppTest:
    return (
        next(item for item in app.sidebar.button if item.key == "nav_review")
        .click()
        .run(timeout=10)
    )


def open_documents(app: AppTest) -> AppTest:
    return (
        next(item for item in app.sidebar.button if item.key == "nav_documents")
        .click()
        .run(timeout=10)
    )


def submit_review_scenario(
    app: AppTest,
    scenario: str,
    *,
    answer: str = "我重新说明了核心机制、适用边界和一个具体例子。",
) -> AppTest:
    text_area_with_label(app, "你的复测回答").input(answer)
    select_with_label(app, "复测场景").select(scenario)
    return button_with_label(app, "提交复测").click().run(timeout=10)


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
    assert "你已经讲清楚的证据" in page
    assert "缺少的关键点" in page
    assert "可能的误区" in page
    assert "当前掌握判断" in page
    assert "下一步" in page
    assert not app.error


@pytest.mark.parametrize(
    ("scenario", "mastery_copy", "action_copy"),
    [
        ("partial", "理解还不稳定", "重新学习"),
        ("misconception", "理解还不稳定", "复习概念"),
        ("insufficient_evidence", "完全未掌握", "重新学习"),
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
    assert "已保存的原始回答" in rendered_markdown(app)
    assert "我用一个合成回答说明递归的机制、边界和例子。" in rendered_markdown(app)
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


def test_same_session_supports_follow_up_and_resume(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = submit_scenario(
        start_session(app_for(tmp_path, monkeypatch, "ui-follow-up.db")),
        "partial",
    )
    session_id = app.session_state["current_session_id"]

    app = button_with_label(app, "重新学习").click().run(timeout=10)
    text_area_with_label(app, "你的后续解释").input(
        "这次我补充递归的终止条件、调用机制和适用边界。"
    )
    select_with_label(app, "后续诊断场景").select("strong")
    app = button_with_label(app, "提交后续解释").click().run(timeout=10)

    assert not app.exception
    assert app.session_state["current_session_id"] == session_id
    diagnosis = app.session_state["last_diagnosis"]
    assert diagnosis.session_id == session_id
    assert diagnosis.answer_type == "follow_up"
    assert diagnosis.sequence_no == 2
    assert "理解较稳定" in rendered_markdown(app)

    app = (
        next(item for item in app.sidebar.button if item.key == "nav_today").click().run(timeout=10)
    )
    app = button_with_label(app, "继续本次会话").click().run(timeout=10)

    assert not app.exception
    assert app.session_state["current_session_id"] == session_id
    assert "理解较稳定" in rendered_markdown(app)
    assert any("第 2 次回答" in item.value for item in app.caption)


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


def test_responsive_theme_styles_survive_the_learning_result(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = submit_scenario(
        start_session(app_for(tmp_path, monkeypatch, "ui-responsive.db")),
        "misconception",
    )
    app = button_with_label(app, "浅色").click().run(timeout=10)
    collapse = next(item for item in app.sidebar.button if item.key == "sidebar_toggle")
    app = collapse.click().run(timeout=10)

    page = rendered_markdown(app)
    assert not app.exception
    assert app.session_state["ui_theme_mode"] is ThemeMode.DARK
    assert app.session_state["ui_sidebar_collapsed"] is True
    assert "@media (max-width: 760px)" in page
    assert ".diagnosis-grid { grid-template-columns: 1fr; }" in page
    assert "可能的误区" in page


def test_real_provider_mode_hides_fake_controls_and_reports_deepseek(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = app_for_real_provider(tmp_path, monkeypatch, "ui-real-provider.db")

    app = open_learn(app)
    assert not any(item.label == "诊断场景" for item in app.selectbox)
    assert "deepseek-v4-flash-vision-exp" not in rendered_markdown(app)

    app = (
        next(item for item in app.sidebar.button if item.key == "nav_system")
        .click()
        .run(timeout=10)
    )
    page = rendered_markdown(app)
    assert "DeepSeek Provider" in page
    assert "当前仅使用 Fake Provider" not in page


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


def test_mistake_notebook_has_a_clear_empty_state(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = open_mistakes(app_for(tmp_path, monkeypatch, "ui-wrong-empty.db"))

    assert not app.exception
    assert "目前没有需要整理的错题" in rendered_markdown(app)
    assert "学习" in [item.label for item in app.sidebar.button]
    assert "错题" in [item.label for item in app.sidebar.button]
    assert "复习" in [item.label for item in app.sidebar.button]
    assert "进度" in [item.label for item in app.sidebar.button]


def test_document_library_has_upload_empty_state_and_navigation(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = open_documents(app_for(tmp_path, monkeypatch, "ui-documents-empty.db"))

    assert not app.exception
    assert "资料库" in rendered_markdown(app)
    assert any("资料库还是空的" in item.value for item in app.info)
    assert "上传资料" in [item.label for item in app.button]
    assert "资料库" in [item.label for item in app.sidebar.button]


def test_document_library_can_upload_and_list_a_text_file(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = open_documents(app_for(tmp_path, monkeypatch, "ui-documents-upload.db"))
    uploader = next(item for item in app.file_uploader if item.label == "选择要上传的资料")
    app = uploader.upload("limits.md", b"# Limits\n", "text/markdown").run(timeout=10)
    app = button_with_label(app, "上传资料").click().run(timeout=10)

    assert not app.exception
    assert "limits.md" in rendered_markdown(app)
    assert any("已上传 1 个文件" in item.value for item in app.success)
    assert any(item.label == "下载" for item in app.download_button)


def test_seeded_mistakes_show_all_types_and_support_filtering_and_sorting(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = open_mistakes(app_for_seeded(tmp_path, monkeypatch, "ui-wrong-list.db"))
    page = rendered_markdown(app)

    assert not app.exception
    assert "明确误区" in page
    assert "关键缺口" in page
    assert "证据不足" in page
    assert "待处理" in page

    select_with_label(app, "错题类型").select("misconception")
    app = app.run(timeout=10)
    filtered = rendered_markdown(app)
    assert "洛必达法则" in filtered
    assert "泰勒公式" not in filtered
    assert "函数极限" not in filtered

    select_with_label(app, "错题类型").select(None)
    select_with_label(app, "排序方式").select("concept")
    app = app.run(timeout=10)
    sorted_page = rendered_markdown(app)
    assert app.session_state["wrong_sort_order"] == "concept"
    assert sorted_page.index("函数极限") < sorted_page.index("洛必达法则")


def test_mistake_detail_preserves_source_answer_and_diagnosis_evidence(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = open_mistakes(app_for_seeded(tmp_path, monkeypatch, "ui-wrong-detail.db"))
    app = button_with_label(app, "查看详情").click().run(timeout=10)
    page = rendered_markdown(app)

    assert not app.exception
    assert "当时的题目与回答" in page
    assert "原题" in page
    assert "你的原回答" in page
    assert "已经讲清楚的证据" in page
    assert "缺少的关键点" in page
    assert "可能的误区" in page
    assert "正确思路" in page
    assert button_with_label(app, "安排复习")
    assert button_with_label(app, "标记已掌握")
    assert button_with_label(app, "围绕此知识点重新作答")


def test_mistake_can_enter_review_and_mark_mastered(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = open_mistakes(app_for_seeded(tmp_path, monkeypatch, "ui-wrong-actions.db"))
    app = button_with_label(app, "查看详情").click().run(timeout=10)
    wrong_item_id = app.session_state["selected_wrong_item_id"]

    review_app = button_with_label(app, "安排复习").click().run(timeout=10)
    assert not review_app.exception
    assert review_app.session_state["active_page"] == "复习"
    assert review_app.session_state["review_source_wrong_item_id"] == wrong_item_id
    assert review_app.session_state["current_review_item_id"]
    assert "当前复习题" in rendered_markdown(review_app)

    app = open_mistakes(review_app)
    app = button_with_label(app, "标记已掌握").click().run(timeout=10)
    assert not app.exception
    assert "已标记为掌握" in app.success[0].value
    assert "已掌握" in rendered_markdown(app)
    assert button_with_label(app, "恢复待处理")


def test_mistake_can_start_a_fresh_explanation_for_the_same_concept(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = open_mistakes(app_for_seeded(tmp_path, monkeypatch, "ui-wrong-reanswer.db"))
    app = button_with_label(app, "查看详情").click().run(timeout=10)
    concept = next(
        candidate
        for candidate in ("函数极限", "洛必达法则", "泰勒公式")
        if candidate in rendered_markdown(app)
    )
    app = button_with_label(app, "围绕此知识点重新作答").click().run(timeout=10)

    assert not app.exception
    assert app.session_state["active_page"] == "学习"
    assert app.session_state["current_session_id"]
    assert "学习主题" in rendered_markdown(app)
    assert "费曼问题" in rendered_markdown(app)
    assert concept in rendered_markdown(app)


def test_missing_mistake_detail_shows_recoverable_error(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = open_mistakes(app_for_seeded(tmp_path, monkeypatch, "ui-wrong-error.db"))
    app.session_state["selected_wrong_item_id"] = "missing-wrong-item"
    app = app.run(timeout=10)

    assert not app.exception
    assert app.error
    assert "不存在或已经无法读取" in app.error[0].value
    assert button_with_label(app, "回到错题列表")


def test_mistake_page_keeps_theme_and_narrow_layout_contract(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = open_mistakes(app_for_seeded(tmp_path, monkeypatch, "ui-wrong-responsive.db"))
    app = button_with_label(app, "查看详情").click().run(timeout=10)
    app = button_with_label(app, "浅色").click().run(timeout=10)
    page = rendered_markdown(app)

    assert not app.exception
    assert app.session_state["ui_theme_mode"] is ThemeMode.DARK
    assert "@media (max-width: 760px)" in page
    assert ".source-answer-grid, .mistake-evidence-grid, .mistake-correction" in page
    assert '.st-key-view-mistakes [data-testid="stHorizontalBlock"]' in page
    assert "你的原回答" in page


def test_review_queue_has_empty_state_and_clear_core_navigation(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = open_review(app_for(tmp_path, monkeypatch, "ui-review-empty.db"))

    assert not app.exception
    assert "今天没有到期的复习任务" in rendered_markdown(app)
    assert button_with_label(app, "去学习新主题")


def test_seeded_review_queue_shows_due_count_current_item_and_progress(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = open_review(app_for_seeded(tmp_path, monkeypatch, "ui-review-queue.db"))
    page = rendered_markdown(app)

    assert not app.exception
    assert "今日到期" in page
    assert "本轮已完成" in page
    assert "本轮任务总数" in page
    assert "当前复习题" in page
    assert "今日复习队列" in page
    assert text_area_with_label(app, "你的复测回答")
    assert button_with_label(app, "提交复测")
    postpone = button_with_label(app, "延后复习")
    assert postpone.disabled is True
    assert "当前契约尚不支持手动延后" in app.caption[-1].value
    queue_actions = [item for item in app.button if item.label in {"当前题", "开始这题"}]
    assert len(queue_actions) == 3


@pytest.mark.parametrize(
    ("scenario", "outcome", "copy"),
    [
        ("strong", ReviewOutcome.CORRECT, "本次回答正确"),
        ("partial", ReviewOutcome.PARTIAL, "本次回答仍不完整"),
        ("misconception", ReviewOutcome.INCORRECT, "本次回答需要纠正"),
    ],
)
def test_retest_outcomes_render_backend_feedback_and_reschedule(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    scenario: str,
    outcome: ReviewOutcome,
    copy: str,
) -> None:
    app = open_review(app_for_seeded(tmp_path, monkeypatch, f"ui-review-{scenario}.db"))
    review_item_id = app.session_state["current_review_item_id"]
    app = submit_review_scenario(app, scenario)
    result = app.session_state["review_result"]
    page = rendered_markdown(app)

    assert not app.exception
    assert result.status is ReviewAttemptStatus.SUCCEEDED
    assert result.result is outcome
    assert result.review_item.review_item_id == review_item_id
    assert copy in page
    assert "已经讲清楚" in page
    assert "仍需补充" in page
    assert "可能的误区" in page
    assert "后端已重新安排下次复习" in app.success[0].value
    assert button_with_label(app, "下一题")


def test_successful_retest_advances_queue_and_persists_after_restart(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = open_review(app_for_seeded(tmp_path, monkeypatch, "ui-review-persist.db"))
    first_id = app.session_state["current_review_item_id"]
    app = submit_review_scenario(app, "strong")

    assert app.session_state["review_result"].review_item.interval_days == 3
    app = button_with_label(app, "下一题").click().run(timeout=10)
    assert not app.exception
    assert app.session_state["current_review_item_id"] != first_id
    assert len([item for item in app.button if item.label in {"当前题", "开始这题"}]) == 2

    restarted = AppTest.from_file(APP_PATH).run(timeout=10)
    restarted = open_review(restarted)
    assert not restarted.exception
    assert len([item for item in restarted.button if item.label in {"当前题", "开始这题"}]) == 2
    assert first_id != restarted.session_state["current_review_item_id"]


def test_failed_retest_keeps_answer_and_can_retry_without_duplicate_review(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    answer = "这段复测回答必须在失败以后仍然完整保留。"
    app = open_review(app_for_seeded(tmp_path, monkeypatch, "ui-review-retry.db"))
    review_item_id = app.session_state["current_review_item_id"]
    app = submit_review_scenario(app, "provider_timeout", answer=answer)

    assert not app.exception
    assert app.session_state["review_result"].status is ReviewAttemptStatus.FAILED
    assert app.session_state[f"review_saved_answer_{review_item_id}"] == answer
    assert answer in rendered_markdown(app)
    assert "已经保存" in app.info[0].value
    assert button_with_label(app, "使用已保存回答重试复测")

    select_with_label(app, "重试复测场景").select("strong")
    app = button_with_label(app, "使用已保存回答重试复测").click().run(timeout=10)
    assert not app.exception
    assert app.session_state["review_result"].status is ReviewAttemptStatus.SUCCEEDED
    assert app.session_state["review_result"].review_item.attempt_count == 1
    assert "后端已重新安排下次复习" in app.success[0].value

    app = button_with_label(app, "下一题").click().run(timeout=10)
    assert len([item for item in app.button if item.label in {"当前题", "开始这题"}]) == 2


def test_review_item_can_be_marked_mastered_and_removed_from_queue(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = open_review(app_for_seeded(tmp_path, monkeypatch, "ui-review-mastered.db"))
    app = button_with_label(app, "标记已掌握").click().run(timeout=10)

    assert not app.exception
    assert "已标记为掌握" in app.success[0].value
    assert len([item for item in app.button if item.label in {"当前题", "开始这题"}]) == 2


def test_review_page_keeps_dark_theme_and_narrow_layout_contract(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = open_review(app_for_seeded(tmp_path, monkeypatch, "ui-review-responsive.db"))
    app = button_with_label(app, "浅色").click().run(timeout=10)
    page = rendered_markdown(app)

    assert not app.exception
    assert app.session_state["ui_theme_mode"] is ThemeMode.DARK
    assert ".review-result-grid { grid-template-columns: 1fr; }" in page
    assert '.st-key-view-review [data-testid="stHorizontalBlock"]' in page
    assert '[data-testid="stExpandSidebarButton"] {' in page
    assert "当前复习题" in page


def test_seeded_today_page_exposes_the_four_core_workspaces(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = app_for_seeded(tmp_path, monkeypatch, "ui-today-workspaces.db")
    page = rendered_markdown(app)

    assert not app.exception
    assert "学习记录" in page
    assert "待处理错题" in page
    assert "今日到期复习" in page
    assert "长期状态主题" in page
    assert button_with_label(app, "继续学习")
    assert button_with_label(app, "查看错题")
    assert button_with_label(app, "开始复习")
    assert button_with_label(app, "查看进度")


def test_user_correction_is_saved_and_reflected_in_progress(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = submit_scenario(
        start_session(app_for(tmp_path, monkeypatch, "ui-feedback-progress.db")),
        "partial",
    )
    select_with_label(app, "你的判断").select("inaccurate")
    text_area_with_label(app, "补充说明或修正").input("诊断遗漏了我对递归终止条件的说明。")
    app = button_with_label(app, "提交诊断反馈").click().run(timeout=10)

    assert not app.exception
    assert "反馈已保存" in app.success[0].value
    assert "我用一个合成回答说明递归的机制、边界和例子。" in rendered_markdown(app)

    app = (
        next(item for item in app.sidebar.button if item.key == "nav_progress")
        .click()
        .run(timeout=10)
    )
    page = rendered_markdown(app)
    assert "长期状态" in page
    assert "修正反馈 / 全部反馈" in page
    assert "1 / 1" in page
    assert "递归" in page


def test_seeded_progress_shows_backend_trends_and_longitudinal_counts(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = app_for_seeded(tmp_path, monkeypatch, "ui-progress-state.db")
    app = (
        next(item for item in app.sidebar.button if item.key == "nav_progress")
        .click()
        .run(timeout=10)
    )
    page = rendered_markdown(app)

    assert not app.exception
    assert "长期状态" in page
    assert "函数极限" in page
    assert "洛必达法则" in page
    assert "泰勒公式" in page
    assert "理解正在改善" in page
    assert "待处理 / 全部错题" in page
    assert "复测正确 / 全部复测" in page
    assert "修正反馈 / 全部反馈" in page


def test_complete_fake_ui_loop_connects_learning_mistake_review_and_progress(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = submit_scenario(
        start_session(app_for(tmp_path, monkeypatch, "ui-complete-loop.db")),
        "partial",
    )
    assert "理解还不稳定" in rendered_markdown(app)

    app = open_mistakes(app)
    assert "递归" in rendered_markdown(app)
    app = button_with_label(app, "查看详情").click().run(timeout=10)
    source_answer = "我用一个合成回答说明递归的机制、边界和例子。"
    assert source_answer in rendered_markdown(app)

    app = button_with_label(app, "安排复习").click().run(timeout=10)
    assert app.session_state["active_page"] == "复习"
    assert "递归" in rendered_markdown(app)
    app = submit_review_scenario(app, "strong")
    assert app.session_state["review_result"].result is ReviewOutcome.CORRECT
    assert "后端已重新安排下次复习" in app.success[0].value

    app = button_with_label(app, "标记这个错题为已掌握").click().run(timeout=10)
    assert "今天没有到期的复习任务" in rendered_markdown(app)
    app = app.run(timeout=10)
    assert "今天没有到期的复习任务" in rendered_markdown(app)

    app = open_mistakes(app)
    assert "已掌握" in rendered_markdown(app)
    assert source_answer in rendered_markdown(app)

    app = (
        next(item for item in app.sidebar.button if item.key == "nav_progress")
        .click()
        .run(timeout=10)
    )
    page = rendered_markdown(app)
    assert "递归" in page
    assert "1 / 1" in page
    assert "复测正确 / 全部复测" in page
