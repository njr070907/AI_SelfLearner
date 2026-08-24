"""Command-line safety gates that must fail before any paid call is possible."""

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import SecretStr

from ai_growth_companion.evaluation import cli
from ai_growth_companion.evaluation.cli import main


def test_real_run_requires_explicit_paid_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    with pytest.raises(SystemExit, match="confirm-paid-calls"):
        main(["--provider", "openai", "--model", "gpt-test"])


def test_real_run_requires_api_key_after_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(
        cli,
        "Settings",
        lambda: SimpleNamespace(llm_api_key=None, llm_model="gpt-test"),
    )

    with pytest.raises(SystemExit, match="LLM_API_KEY"):
        main(["--provider", "openai", "--model", "gpt-test", "--confirm-paid-calls"])


def test_paid_confirmation_is_rejected_in_fake_mode() -> None:
    with pytest.raises(SystemExit, match="only valid"):
        main(["--provider", "fake", "--confirm-paid-calls"])


def test_approved_real_run_defaults_to_one_case_and_zero_retry_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class StubOpenAIProvider:
        def __init__(self, **kwargs: Any) -> None:
            captured["provider_kwargs"] = kwargs

    def stub_run(golden_set: Any, **kwargs: Any) -> SimpleNamespace:
        captured["golden_set"] = golden_set
        captured["run_kwargs"] = kwargs
        return SimpleNamespace(
            run_id="openai-evaluator-test",
            summary=SimpleNamespace(
                succeeded_cases=1,
                total_cases=1,
                automatic_passed_cases=1,
                human_review_required_cases=1,
                input_tokens=10,
                output_tokens=5,
                failed_cases=0,
            ),
        )

    def stub_save(run: Any, output: Any) -> None:
        captured["saved"] = (run, output)

    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setattr(cli, "OpenAIEvaluationProvider", StubOpenAIProvider)
    monkeypatch.setattr(cli, "run_golden_evaluation", stub_run)
    monkeypatch.setattr(cli, "save_evaluation_run", stub_save)

    exit_code = main(["--provider", "openai", "--model", "gpt-test", "--confirm-paid-calls"])

    assert exit_code == 0
    assert captured["provider_kwargs"]["model"] == "gpt-test"
    assert captured["run_kwargs"]["max_cases"] == 1
    assert captured["run_kwargs"]["paid_calls_allowed"] is True
    assert captured["run_kwargs"]["mode"].value == "real_provider"
    assert captured["run_kwargs"]["provider_factory"](None) is not None


def test_deepseek_provider_uses_required_model_even_if_env_has_display_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class StubDeepSeekProvider:
        def __init__(self, **kwargs: Any) -> None:
            captured["provider_kwargs"] = kwargs

    def stub_run(_golden_set: Any, **kwargs: Any) -> SimpleNamespace:
        captured["run_kwargs"] = kwargs
        return SimpleNamespace(
            run_id="deepseek-evaluator-test",
            summary=SimpleNamespace(
                succeeded_cases=0,
                total_cases=1,
                automatic_passed_cases=0,
                human_review_required_cases=0,
                input_tokens=0,
                output_tokens=0,
                failed_cases=1,
            ),
        )

    def stub_save(_run: Any, _output: Any) -> None:
        return None

    monkeypatch.setattr(
        cli,
        "Settings",
        lambda: SimpleNamespace(llm_api_key=SecretStr("test-key")),
    )
    monkeypatch.setattr(cli, "DeepSeekEvaluationProvider", StubDeepSeekProvider)
    monkeypatch.setattr(cli, "run_golden_evaluation", stub_run)
    monkeypatch.setattr(cli, "save_evaluation_run", stub_save)

    exit_code = main(["--provider", "deepseek", "--confirm-paid-calls"])

    assert exit_code == 1
    assert captured["provider_kwargs"]["model"] == "deepseek-v4-flash-vision-exp"
    assert captured["run_kwargs"]["max_cases"] == 1
