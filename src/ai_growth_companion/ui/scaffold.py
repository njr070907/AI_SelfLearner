"""Minimal Sprint 0 page used before the fake learning loop is connected."""

import streamlit as st

from ai_growth_companion.config import Settings


def render_scaffold(settings: Settings) -> None:
    """Render a truthful status page without claiming real diagnosis capability."""
    st.set_page_config(page_title="AI Growth Companion", page_icon="🌱", layout="centered")

    st.title("AI Growth Companion")
    st.caption("用自己的话解释知识，检查自己是否真正理解。")

    st.info(
        "当前是 Sprint 0 工程底座。诊断使用可预测的 Fake Provider，还不能代表真实的学习掌握判断。"
    )

    st.subheader("当前运行状态")
    left, right = st.columns(2)
    left.metric("运行环境", settings.app_env)
    right.metric("AI 模式", "Fake（演示）" if settings.is_fake_mode else settings.llm_provider)

    st.write("下一步将接通数据库、结构化观察和完整的假诊断闭环。")
    st.caption("不会在页面或日志中显示 API Key。")
