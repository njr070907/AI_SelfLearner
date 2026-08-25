"""SQLite migration integration tests."""

import sqlite3
from pathlib import Path

import pytest

from ai_growth_companion.repositories.database import (
    Database,
    MigrationError,
    discover_migrations,
    migration_status,
    run_migrations,
)


def database_for(tmp_path: Path) -> Database:
    return Database(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")


def test_empty_database_migrates_to_latest_and_is_repeatable(tmp_path: Path) -> None:
    database = database_for(tmp_path)

    first = run_migrations(database)
    second = run_migrations(database)

    assert first.previous_version == 0
    assert first.current_version == len(discover_migrations())
    assert first.applied_versions == tuple(range(1, first.current_version + 1))
    assert second.previous_version == first.current_version
    assert second.applied_versions == ()
    assert migration_status(database) == (first.current_version, first.current_version)


def test_initial_migration_creates_event_and_projection_tables(tmp_path: Path) -> None:
    database = database_for(tmp_path)
    run_migrations(database)

    with database.connect() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        foreign_keys_enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]

    assert {"learning_events", "concept_states", "provider_observations", "wrong_items"} <= tables
    assert foreign_keys_enabled == 1


def test_database_newer_than_code_is_rejected(tmp_path: Path) -> None:
    database = database_for(tmp_path)
    run_migrations(database)

    with database.connect() as connection, connection:
        connection.execute(
            "INSERT INTO schema_migrations(version, name, checksum, applied_at) "
            "VALUES (9999, '9999_future.sql', 'synthetic', '2026-08-23T00:00:00Z')"
        )

    with pytest.raises(MigrationError, match="newer than code"):
        run_migrations(database)


def test_applied_migration_checksum_change_is_rejected(tmp_path: Path) -> None:
    database = database_for(tmp_path)
    migrations = discover_migrations()
    run_migrations(database, migrations)

    with database.connect() as connection, connection:
        connection.execute("UPDATE schema_migrations SET checksum = 'changed' WHERE version = 1")

    with pytest.raises(MigrationError, match="Applied migration was modified"):
        run_migrations(database, migrations)


def test_invalid_foreign_key_is_rejected(tmp_path: Path) -> None:
    database = database_for(tmp_path)
    run_migrations(database)

    with database.connect() as connection, pytest.raises(sqlite3.IntegrityError), connection:
        connection.execute(
            """
            INSERT INTO learning_events (
                id, user_id, event_type, payload_json, created_at
            ) VALUES ('event-1', 'missing-user', 'answer_submitted', '{}', '2026-08-23T00:00:00Z')
            """
        )
