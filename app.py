"""Streamlit composition root for AI Growth Companion."""

import streamlit as st

from ai_growth_companion.application.health import check_health
from ai_growth_companion.application.learning_service import LearningService
from ai_growth_companion.config import load_settings
from ai_growth_companion.repositories.database import Database
from ai_growth_companion.repositories.session_repository import SQLiteSessionRepository
from ai_growth_companion.ui.application import render_application


def main() -> None:
    """Validate runtime dependencies, then render the fake learning loop."""
    st.set_page_config(page_title="AI Growth Companion", page_icon="🌱", layout="centered")
    settings = load_settings()
    database = Database(settings.database_url)

    health_report = check_health(settings, database)
    if not health_report.is_ready:
        st.error(health_report.readiness.detail)
        st.info("请先运行 README 中的数据库迁移命令。")
        st.stop()

    if not settings.is_fake_mode:
        st.error("Sprint 0 只实现 Fake Provider。请将 LLM_PROVIDER 设置为 fake。")
        st.stop()

    repository = SQLiteSessionRepository(database)
    service = LearningService(repository)
    render_application(
        service,
        settings=settings,
        health_report=health_report,
    )


if __name__ == "__main__":
    main()
