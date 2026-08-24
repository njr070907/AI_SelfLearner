"""Guardrails for the shared UI design baseline."""

from ai_growth_companion.ui.theme import APP_CSS


def test_theme_supports_ambient_light_and_dark_modes() -> None:
    assert "radial-gradient" in APP_CSS
    assert "--ambient-blue" in APP_CSS
    assert "--ambient-violet" in APP_CSS
    assert "@media (prefers-color-scheme: dark)" in APP_CSS


def test_glass_is_scoped_to_navigation_chrome() -> None:
    glass_rules = [
        line.strip()
        for line in APP_CSS.splitlines()
        if "backdrop-filter:" in line and "none" not in line
    ]

    assert len(glass_rules) == 4
    assert '[data-testid="stSidebar"]' in APP_CSS
    assert '[data-testid="stHeader"]' in APP_CSS
    assert ".diagnosis-panel {" in APP_CSS
    assert "background: var(--surface-solid);" in APP_CSS


def test_theme_has_responsive_and_accessibility_contracts() -> None:
    assert "@media (max-width: 980px)" in APP_CSS
    assert "@media (max-width: 760px)" in APP_CSS
    assert "min-height: 48px" in APP_CSS
    assert "@media (prefers-reduced-motion: reduce)" in APP_CSS
    assert "focus-visible" in APP_CSS
    assert "transition-all" not in APP_CSS
