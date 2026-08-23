"""Secret scan rules detect high-confidence tokens without storing a real secret."""

from ai_growth_companion.observability.secrets import find_secrets


def test_synthetic_openai_shaped_key_is_detected() -> None:
    synthetic = "sk-" + ("A" * 32)

    findings = find_secrets(f"value={synthetic}")

    assert findings[0].rule == "openai-key"


def test_normal_documentation_text_is_not_reported() -> None:
    assert find_secrets("LLM_API_KEY=\nDo not commit API keys.") == ()
