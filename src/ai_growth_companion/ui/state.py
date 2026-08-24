"""Session-scoped appearance and shell state for the Streamlit UI."""

from dataclasses import dataclass
from enum import StrEnum

import streamlit as st


class ThemeMode(StrEnum):
    LIGHT = "light"
    DARK = "dark"


class AccentTheme(StrEnum):
    BLUE = "blue"
    PURPLE = "purple"
    GREEN = "green"
    BLUE_PURPLE = "blue-purple"
    GRAPHITE = "graphite"


THEME_LABELS = {
    ThemeMode.LIGHT: "浅色",
    ThemeMode.DARK: "深色",
}

ACCENT_LABELS = {
    AccentTheme.BLUE: "Blue",
    AccentTheme.PURPLE: "Purple",
    AccentTheme.GREEN: "Green",
    AccentTheme.BLUE_PURPLE: "Blue–Purple",
    AccentTheme.GRAPHITE: "Graphite",
}


@dataclass(frozen=True)
class UiPreferences:
    theme: ThemeMode
    accent: AccentTheme
    sidebar_collapsed: bool


def initialize_ui_state() -> None:
    """Install stable defaults before any themed elements render."""
    st.session_state.setdefault("active_page", "今日")
    st.session_state.setdefault("ui_theme_mode", ThemeMode.LIGHT)
    st.session_state.setdefault("ui_accent_theme", AccentTheme.BLUE_PURPLE)
    st.session_state.setdefault("ui_sidebar_collapsed", False)
    st.session_state.setdefault("ui_search_query", "")


def current_preferences() -> UiPreferences:
    return UiPreferences(
        theme=ThemeMode(st.session_state.ui_theme_mode),
        accent=AccentTheme(st.session_state.ui_accent_theme),
        sidebar_collapsed=bool(st.session_state.ui_sidebar_collapsed),
    )


def toggle_theme() -> None:
    current = ThemeMode(st.session_state.ui_theme_mode)
    st.session_state.ui_theme_mode = (
        ThemeMode.DARK if current is ThemeMode.LIGHT else ThemeMode.LIGHT
    )


def toggle_sidebar() -> None:
    st.session_state.ui_sidebar_collapsed = not bool(st.session_state.ui_sidebar_collapsed)
