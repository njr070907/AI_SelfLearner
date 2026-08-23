"""Health checks keep liveness, readiness, and provider dependency separate."""

from pathlib import Path

from ai_growth_companion.application.health import HealthState, check_health
from ai_growth_companion.config import Settings
from ai_growth_companion.repositories.database import Database, run_migrations


def test_migrated_fake_environment_is_ready(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{(tmp_path / 'ready.db').as_posix()}")
    run_migrations(database)

    report = check_health(Settings(_env_file=None), database)

    assert report.liveness.state is HealthState.HEALTHY
    assert report.readiness.state is HealthState.HEALTHY
    assert report.provider_dependency.state is HealthState.HEALTHY
    assert report.is_ready is True


def test_unmigrated_database_is_not_ready_but_process_is_alive(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{(tmp_path / 'behind.db').as_posix()}")

    report = check_health(Settings(_env_file=None), database)

    assert report.liveness.state is HealthState.HEALTHY
    assert report.readiness.state is HealthState.UNHEALTHY
    assert report.database_version == 0
    assert report.is_ready is False


def test_unimplemented_external_provider_does_not_break_liveness(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{(tmp_path / 'external.db').as_posix()}")
    run_migrations(database)
    settings = Settings(
        _env_file=None,
        llm_provider="external",
        llm_api_key="synthetic-only",
    )

    report = check_health(settings, database)

    assert report.liveness.state is HealthState.HEALTHY
    assert report.readiness.state is HealthState.HEALTHY
    assert report.provider_dependency.state is HealthState.DEGRADED
