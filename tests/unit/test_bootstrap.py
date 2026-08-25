"""Offline tests for application Provider composition."""

from pathlib import Path

import pytest

from ai_growth_companion.application.bootstrap import build_learning_service
from ai_growth_companion.config import Settings
from ai_growth_companion.providers.deepseek_evaluation import DEEPSEEK_MODEL
from ai_growth_companion.providers.fake import FakeScenario
from ai_growth_companion.repositories.database import Database, run_migrations


def test_bootstrap_defaults_to_fake_without_network(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{(tmp_path / 'bootstrap.db').as_posix()}")
    run_migrations(database)

    service = build_learning_service(database, Settings(_env_file=None))
    session = service.start_session(concept="递归", request_id="bootstrap-fake")

    assert session.concept == "递归"


def test_bootstrap_rejects_real_mode_without_explicit_paid_permission(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{(tmp_path / 'bootstrap-deepseek.db').as_posix()}")
    run_migrations(database)
    settings = Settings(
        _env_file=None,
        llm_provider="deepseek",
        llm_model=DEEPSEEK_MODEL,
        llm_api_key="synthetic-key",
    )

    with pytest.raises(ValueError, match="explicit paid-call permission"):
        build_learning_service(database, settings)


def test_bootstrap_constructs_deepseek_mode_only_with_fixed_model_and_permission(
    tmp_path: Path,
) -> None:
    database = Database(f"sqlite:///{(tmp_path / 'bootstrap-deepseek-ok.db').as_posix()}")
    run_migrations(database)
    settings = Settings(
        _env_file=None,
        llm_provider="deepseek",
        llm_model=DEEPSEEK_MODEL,
        llm_api_key="synthetic-key",
        llm_paid_calls_allowed=True,
    )

    service = build_learning_service(database, settings)

    assert service.provider_factory(FakeScenario.PARTIAL).provider_name == "deepseek"
