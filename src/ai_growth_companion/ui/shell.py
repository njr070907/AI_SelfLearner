"""Persistent navigation, appearance controls, and local history search."""

from collections.abc import Callable, Sequence
from html import escape

import streamlit as st

from ai_growth_companion.application.models import HistoryItem
from ai_growth_companion.ui.presentation import (
    filter_history,
    local_datetime,
    mastery_label,
    status_label,
)
from ai_growth_companion.ui.state import (
    ACCENT_LABELS,
    AccentTheme,
    ThemeMode,
    UiPreferences,
    toggle_sidebar,
    toggle_theme,
)

NAVIGATION = (
    ("今日", "home", "nav_today"),
    ("学习", "school", "nav_learn"),
    ("进度", "timeline", "nav_progress"),
    ("系统", "settings", "nav_system"),
)


def render_sidebar(
    *,
    preferences: UiPreferences,
    active_page: str,
    navigate: Callable[[str], None],
) -> None:
    """Render a capsule-style sidebar with a stable icon-only mode."""
    with st.sidebar:
        if preferences.sidebar_collapsed:
            st.markdown(
                '<span class="sidebar-collapse-marker" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div class="brand"><span class="brand-mark">S</span>'
            '<span class="brand-copy">AI SelfLearner</span></div>',
            unsafe_allow_html=True,
        )
        st.button(
            "展开边栏" if preferences.sidebar_collapsed else "收起边栏",
            key="sidebar_toggle",
            type="tertiary",
            icon=(
                ":material/left_panel_open:"
                if preferences.sidebar_collapsed
                else ":material/left_panel_close:"
            ),
            help="展开边栏" if preferences.sidebar_collapsed else "收起边栏",
            on_click=toggle_sidebar,
            use_container_width=True,
        )
        st.markdown('<div class="nav-section-label">导航</div>', unsafe_allow_html=True)
        with st.container(key="nav_list"):
            st.markdown(
                '<div class="nav-slider" aria-hidden="true"></div>',
                unsafe_allow_html=True,
            )
            for page, icon, key in NAVIGATION:
                st.button(
                    page,
                    key=key,
                    type="primary" if page == active_page else "tertiary",
                    icon=f":material/{icon}:",
                    on_click=navigate,
                    args=(page,),
                    use_container_width=True,
                )
        st.markdown(
            '<div class="sidebar-status"><span class="status-dot"></span>'
            '<span class="sidebar-status-copy">Fake Provider 已就绪<br>'
            "本地模式 · 零 API 费用</span></div>",
            unsafe_allow_html=True,
        )


def render_top_toolbar(*, active_page: str, preferences: UiPreferences) -> str:
    """Render stable glass chrome and return the current search query."""
    with st.container(key="app_toolbar"):
        title, search, theme, accent = st.columns(
            [1.05, 2.6, 0.72, 1.05],
            vertical_alignment="center",
            gap="small",
        )
        title.markdown(
            f'<div class="toolbar-location"><span class="toolbar-dot"></span>'
            f"{escape(active_page)}</div>",
            unsafe_allow_html=True,
        )
        search_query = search.text_input(
            "搜索学习历史",
            key="ui_search_query",
            type="search",
            placeholder="搜索主题、掌握判断或状态",
            icon=":material/search:",
            label_visibility="collapsed",
        )
        theme.button(
            "浅色" if preferences.theme is ThemeMode.LIGHT else "深色",
            key="theme_toggle",
            type="tertiary",
            icon=(
                ":material/light_mode:"
                if preferences.theme is ThemeMode.LIGHT
                else ":material/dark_mode:"
            ),
            help="切换为深色模式" if preferences.theme is ThemeMode.LIGHT else "切换为浅色模式",
            on_click=toggle_theme,
            use_container_width=True,
        )
        accent.selectbox(
            "强调色",
            options=list(AccentTheme),
            key="ui_accent_theme",
            format_func=ACCENT_LABELS.__getitem__,
            label_visibility="collapsed",
            help="选择界面的 Accent Theme",
        )
    return search_query or ""


def render_search_results(
    *,
    history: Sequence[HistoryItem],
    query: str,
    open_result: Callable[[str, str], None],
) -> None:
    """Render bounded results from real local history data."""
    normalized = query.strip()
    if not normalized:
        return

    matches = filter_history(history, normalized)
    with st.container(key="search_results"):
        st.markdown(
            f'<div class="search-results-title">搜索结果 <span>{len(matches)} 条</span></div>',
            unsafe_allow_html=True,
        )
        if not matches:
            st.caption("没有匹配的学习主题、掌握判断或记录状态。")
            return

        for item in matches[:6]:
            details, action = st.columns([4.3, 0.7], vertical_alignment="center")
            details.markdown(
                '<div class="search-result-row">'
                f"<strong>{escape(item.concept)}</strong>"
                f"<span>{escape(mastery_label(item.mastery_level))} · "
                f"{escape(status_label(item.status))} · "
                f"{escape(local_datetime(item.started_at))}</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            action.button(
                "打开",
                key=f"search_result_{item.session_id}",
                type="tertiary",
                icon=":material/arrow_forward:",
                help=f"在进度中查看{item.concept}",
                on_click=open_result,
                args=(item.session_id, item.concept),
                use_container_width=True,
            )
