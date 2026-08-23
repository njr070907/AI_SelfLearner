"""Rendered Streamlit flow tests using Streamlit's official AppTest harness."""

from pathlib import Path

from pytest import MonkeyPatch
from streamlit.testing.v1 import AppTest

from ai_growth_companion.config import load_settings
from ai_growth_companion.repositories.database import Database, run_migrations

APP_PATH = Path(__file__).resolve().parents[2] / "app.py"


def app_for(tmp_path: Path, monkeypatch: MonkeyPatch, name: str) -> AppTest:
    database_url = f"sqlite:///{(tmp_path / name).as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    load_settings.cache_clear()
    run_migrations(Database(database_url))
    return AppTest.from_file(APP_PATH).run(timeout=10)


def start_session(app: AppTest) -> AppTest:
    app.text_input[0].input("递归")
    return app.button[0].click().run(timeout=10)


def test_user_can_complete_fake_diagnosis_in_rendered_app(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = start_session(app_for(tmp_path, monkeypatch, "ui-success.db"))

    assert not app.exception
    assert len(app.text_area) == 1
    app.text_area[0].input("我用一个合成回答说明递归的机制和边界。")
    app.selectbox[0].select("strong")
    app = app.button[0].click().run(timeout=10)

    assert not app.exception
    assert app.success
    assert len(app.metric) == 2
    assert app.metric[0].value == "solid"


def test_rendered_failure_keeps_answer_and_can_retry(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app = start_session(app_for(tmp_path, monkeypatch, "ui-retry.db"))
    app.text_area[0].input("这个合成回答必须在模拟超时后继续保留。")
    app.selectbox[0].select("provider_timeout")
    app = app.button[0].click().run(timeout=10)

    assert not app.exception
    assert app.error
    assert app.info
    assert "LLM_TIMEOUT" in [item.value for item in app.code]

    app.selectbox[0].select("strong")
    app = app.button[0].click().run(timeout=10)

    assert not app.exception
    assert app.success
    assert app.metric[0].value == "solid"
