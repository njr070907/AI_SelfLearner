"""Create a local user export without network calls or external uploads."""

import argparse
from os import environ
from pathlib import Path

from ai_growth_companion.application.bootstrap import build_document_library
from ai_growth_companion.application.export_service import UserExportService
from ai_growth_companion.repositories.database import Database, run_migrations


def main() -> int:
    """Write a self-describing ZIP export to a local, ignored directory."""
    parser = argparse.ArgumentParser(description="Export local AI SelfLearner data.")
    parser.add_argument(
        "--database",
        default=environ.get("DATABASE_URL", "sqlite:///data/companion.db"),
        help="SQLite URL; defaults to DATABASE_URL from the local environment.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output ZIP path; defaults to exports/<generated filename>.",
    )
    args = parser.parse_args()

    database = Database(args.database)
    run_migrations(database)
    documents = build_document_library(database)
    artifact = UserExportService(database, documents).export()
    output = args.output or Path("exports") / artifact.filename
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(artifact.content)
    print(f"Export written: {output}")
    print(f"SHA-256: {artifact.sha256}")
    print(f"Documents: {artifact.included_document_count} included")
    if artifact.missing_document_count:
        print(f"Warning: {artifact.missing_document_count} document files were missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
