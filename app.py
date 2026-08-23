"""Streamlit composition root for AI Growth Companion."""

import streamlit as st

from ai_growth_companion.application.learning_service import LearningService
from ai_growth_companion.config import load_settings
from ai_growth_companion.repositories.database import Database, MigrationError, migration_status
from ai_growth_companion.repositories.session_repository import SQLiteSessionRepository
from ai_growth_companion.ui.application import render_application


def main() -> None:
    """Validate runtime dependencies, then render the fake learning loop."""
    st.set_page_config(page_title="AI Growth Companion", page_icon="🌱", layout="centered")
    settings = load_settings()
    database = Database(settings.database_url)

    try:
        current_version, available_version = migration_status(database)
    except (MigrationError, OSError, ValueError) as error:
        st.error(f"数据库状态检查失败：{error}")
        st.stop()

    if current_version != available_version:
        st.error(
            f"数据库版本未就绪（当前 {current_version}，需要 {available_version}）。"
            "请先运行 README 中的数据库迁移命令。"
        )
        st.stop()

    if not settings.is_fake_mode:
        st.error("Sprint 0 只实现 Fake Provider。请将 LLM_PROVIDER 设置为 fake。")
        st.stop()

    repository = SQLiteSessionRepository(database)
    service = LearningService(repository)
    render_application(
        service,
        settings=settings,
        database_version=current_version,
    )


if __name__ == "__main__":
    main()
