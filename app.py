"""Streamlit entry point for AI Growth Companion."""

from ai_growth_companion.config import load_settings
from ai_growth_companion.ui.scaffold import render_scaffold


def main() -> None:
    """Render the current Sprint 0 application shell."""
    settings = load_settings()
    render_scaffold(settings)


if __name__ == "__main__":
    main()
