"""Streamlit composition root for AI Growth Companion."""

import streamlit as st

from ai_growth_companion.application.bootstrap import build_document_library, build_learning_service
from ai_growth_companion.application.health import check_health
from ai_growth_companion.config import load_settings
from ai_growth_companion.repositories.database import Database
from ai_growth_companion.ui.application import render_application


def main() -> None:
    """Validate runtime dependencies, then render the fake learning loop."""
    st.set_page_config(
        page_title="AI SelfLearner",
        page_icon="S",
        layout="wide",
        initial_sidebar_state="auto",
    )
    settings = load_settings()
    database = Database(settings.database_url)

    health_report = check_health(settings, database)
    if not health_report.is_ready:
        st.error(health_report.readiness.detail)
        st.info("请先运行 README 中的数据库迁移命令。")
        st.stop()

    try:
        service = build_learning_service(database, settings)
    except ValueError as error:
        st.error(f"Provider 配置不可用：{error}")
        st.info(
            "默认使用 Fake Provider。若要启用真实模式，请固定模型并显式设置 "
            "LLM_PAID_CALLS_ALLOWED=true。"
        )
        st.stop()
    document_library = build_document_library(database)
    render_application(
        service,
        document_library=document_library,
        settings=settings,
        health_report=health_report,
    )


if __name__ == "__main__":
    main()
