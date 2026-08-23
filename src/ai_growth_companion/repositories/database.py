"""SQLite connection and immutable numbered migration support."""

import argparse
import hashlib
import re
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ai_growth_companion.config import load_settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MIGRATIONS_DIR = PROJECT_ROOT / "migrations"
MIGRATION_PATTERN = re.compile(r"^(?P<version>\d{4})_[a-z0-9_]+\.sql$")


class MigrationError(RuntimeError):
    """Raised when migration files or the database version are unsafe."""


@dataclass(frozen=True)
class Migration:
    """A versioned immutable SQL migration."""

    version: int
    name: str
    path: Path
    checksum: str


@dataclass(frozen=True)
class MigrationReport:
    """Result of bringing a database to the current code version."""

    previous_version: int
    current_version: int
    applied_versions: tuple[int, ...]


def utc_text() -> str:
    """Return a SQLite-friendly UTC timestamp."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sqlite_path_from_url(database_url: str, *, base_dir: Path | None = None) -> Path | str:
    """Resolve the supported sqlite:/// URL form without accepting other databases."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("DATABASE_URL must use the sqlite:/// form in the MVP")

    raw_path = database_url[len(prefix) :]
    if not raw_path:
        raise ValueError("DATABASE_URL must include a database path")
    if "?" in raw_path or "#" in raw_path:
        raise ValueError("DATABASE_URL query parameters and fragments are not supported")
    if raw_path == ":memory:":
        return raw_path

    path = Path(raw_path)
    if not path.is_absolute():
        path = (base_dir or PROJECT_ROOT) / path
    return path.resolve()


class Database:
    """Own SQLite connections and mandatory safety pragmas."""

    def __init__(self, database_url: str, *, base_dir: Path | None = None) -> None:
        self.path = sqlite_path_from_url(database_url, base_dir=base_dir)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open a configured connection and always close it."""
        if isinstance(self.path, Path):
            self.path.parent.mkdir(parents=True, exist_ok=True)
            target = str(self.path)
        else:
            target = self.path

        connection = sqlite3.connect(target, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        if isinstance(self.path, Path):
            connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
        finally:
            connection.close()


def discover_migrations(migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> tuple[Migration, ...]:
    """Load ordered migration metadata and reject gaps or duplicate versions."""
    migrations: list[Migration] = []
    for path in sorted(migrations_dir.glob("*.sql")):
        match = MIGRATION_PATTERN.match(path.name)
        if match is None:
            raise MigrationError(f"Invalid migration filename: {path.name}")
        content = path.read_bytes()
        migrations.append(
            Migration(
                version=int(match.group("version")),
                name=path.name,
                path=path,
                checksum=hashlib.sha256(content).hexdigest(),
            )
        )

    versions = [migration.version for migration in migrations]
    expected = list(range(1, len(migrations) + 1))
    if versions != expected:
        raise MigrationError(f"Migration versions must be continuous: {versions}")
    return tuple(migrations)


def _ensure_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    connection.commit()


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_migrations(
    database: Database,
    migrations: Sequence[Migration] | None = None,
) -> MigrationReport:
    """Apply pending migrations and verify merged migrations were never edited."""
    available = tuple(migrations) if migrations is not None else discover_migrations()
    latest_available = available[-1].version if available else 0

    with database.connect() as connection:
        _ensure_migration_table(connection)
        rows = connection.execute(
            "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
        applied = {int(row["version"]): row for row in rows}
        previous_version = max(applied, default=0)

        if previous_version > latest_available:
            raise MigrationError(
                f"Database version {previous_version} is newer than code version {latest_available}"
            )

        for migration in available:
            existing = applied.get(migration.version)
            if existing is not None and (
                existing["name"] != migration.name or existing["checksum"] != migration.checksum
            ):
                raise MigrationError(f"Applied migration was modified: {migration.name}")

        pending = [migration for migration in available if migration.version not in applied]
        applied_now: list[int] = []
        for migration in pending:
            sql = migration.path.read_text(encoding="utf-8")
            script = "\n".join(
                [
                    "BEGIN IMMEDIATE;",
                    sql,
                    "INSERT INTO schema_migrations (version, name, checksum, applied_at) VALUES (",
                    f"  {migration.version}, {_sql_literal(migration.name)},",
                    f"  {_sql_literal(migration.checksum)}, {_sql_literal(utc_text())}",
                    ");",
                    "COMMIT;",
                ]
            )
            try:
                connection.executescript(script)
            except sqlite3.DatabaseError as error:
                with suppress(sqlite3.DatabaseError):
                    connection.execute("ROLLBACK")
                raise MigrationError(f"Migration failed: {migration.name}") from error
            applied_now.append(migration.version)

    return MigrationReport(
        previous_version=previous_version,
        current_version=latest_available,
        applied_versions=tuple(applied_now),
    )


def migration_status(database: Database) -> tuple[int, int]:
    """Return current and available migration versions without changing business tables."""
    available = discover_migrations()
    latest_available = available[-1].version if available else 0
    with database.connect() as connection:
        _ensure_migration_table(connection)
        row = connection.execute(
            "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
        ).fetchone()
        current = int(row["version"])
    return current, latest_available


def main() -> None:
    """Provide a small migration CLI used locally and in CI."""
    parser = argparse.ArgumentParser(description="AI Growth Companion database migrations")
    parser.add_argument("command", choices=("migrate", "status"))
    args = parser.parse_args()

    settings = load_settings()
    database = Database(settings.database_url)
    if args.command == "migrate":
        report = run_migrations(database)
        print(
            f"database migrated: {report.previous_version} -> {report.current_version}; "
            f"applied={list(report.applied_versions)}"
        )
    else:
        current, available = migration_status(database)
        print(f"database version: current={current}, available={available}")


if __name__ == "__main__":
    main()
