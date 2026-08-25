"""Guardrails for the shared appearance and material system."""

import pytest

from ai_growth_companion.ui.state import AccentTheme, ThemeMode, UiPreferences
from ai_growth_companion.ui.theme import APP_CSS, design_system_css, token_css


def preferences(
    theme: ThemeMode = ThemeMode.LIGHT,
    accent: AccentTheme = AccentTheme.BLUE_PURPLE,
) -> UiPreferences:
    return UiPreferences(theme=theme, accent=accent, sidebar_collapsed=False)


def test_light_and_dark_modes_emit_complete_distinct_surface_tokens() -> None:
    light = token_css(preferences(ThemeMode.LIGHT))
    dark = token_css(preferences(ThemeMode.DARK))

    for token in (
        "--canvas",
        "--surface-solid",
        "--surface-elevated",
        "--glass",
        "--ink",
        "--ink-muted",
        "--line",
        "--shadow-floating",
    ):
        assert token in light
        assert token in dark
    assert "#f3f6fb" in light
    assert "#10151d" in dark
    assert light != dark


@pytest.mark.parametrize("accent", list(AccentTheme))
def test_each_accent_controls_action_focus_glow_and_ambient(accent: AccentTheme) -> None:
    css = token_css(preferences(accent=accent))

    for token in (
        "--accent",
        "--accent-secondary",
        "--accent-soft",
        "--focus-ring",
        "--glow-hover",
        "--glow-pressed",
        "--ambient-primary",
        "--ambient-secondary",
        "--glass-accent",
    ):
        assert token in css


def test_glass_is_scoped_to_persistent_or_temporary_chrome() -> None:
    assert '[data-testid="stSidebar"] {' in APP_CSS
    assert ".st-key-app_toolbar {" in APP_CSS
    assert ".st-key-search_results {" in APP_CSS
    assert ".diagnosis-panel" in APP_CSS
    assert "background: var(--surface-solid);" in APP_CSS


def test_theme_has_collapse_responsive_and_accessibility_contracts() -> None:
    css = design_system_css(preferences())

    assert "sidebar-collapse-marker" in css
    assert "@media (max-width: 980px)" in css
    assert "@media (max-width: 760px)" in css
    assert "min-height: 48px" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "@media (prefers-reduced-transparency: reduce)" in css
    assert "focus-visible" in css
    assert 'button[kind^="primary"]' in css
    assert "transition-all" not in css
    assert "animation: fade" not in css


def test_motion_system_has_tokens_view_transitions_and_pointer_glow() -> None:
    css = design_system_css(preferences())

    for token in (
        "--motion-fast",
        "--motion-normal",
        "--motion-page",
        "--motion-expand",
        "--motion-press",
        "--ease-standard",
        "--ease-emphasized",
    ):
        assert token in css
    assert "@keyframes view-enter-soft {" in css
    assert '[class*="st-key-view-"]' in css
    assert "--glow-x" in css
    assert ".st-key-app_toolbar:hover::after" in css
    assert css.count("@media (hover: hover) and (pointer: fine)") >= 2


def test_motion_language_covers_stagger_expand_and_glow_contracts() -> None:
    css = design_system_css(preferences())

    assert "@keyframes view-rise" in css
    assert '[class*="st-key-view-"] > :nth-child(2)' in css
    assert "animation-delay: 160ms" in css
    assert "@keyframes view-pop" in css
    assert '[data-testid="stSelectboxVirtualDropdown"]' in css
    assert "::details-content" in css
    assert "interpolate-size: allow-keywords" in css
    assert "animation-delay: .01ms" in css
    assert 'button[kind="primary"]:not(:disabled):hover::after' in css
    assert "transition-all" not in css
    assert "animation: fade" not in css
    assert "@keyframes view-enter " not in css


def test_toolbar_styles_current_react_aria_select_without_streamlit_defaults() -> None:
    assert '.react-aria-ComboBox [role="group"]' in APP_CSS
    assert '.react-aria-ComboBox input[role="combobox"]' in APP_CSS
    assert '.react-aria-ComboBox [role="group"]:focus-within' in APP_CSS
    assert '[data-testid="stTextInputRootElement"]:focus-within' in APP_CSS
