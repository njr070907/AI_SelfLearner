"""Seed a repeatable local Fake workspace for frontend development."""

import argparse
from os import environ

from ai_growth_companion.application.demo_workspace import seed_fake_workspace


def main() -> int:
    """Seed demo data without network access, paid calls, or destructive resets."""
    parser = argparse.ArgumentParser(
        description="Create repeatable Fake learning data for local UI development."
    )
    parser.add_argument(
        "--database",
        default=environ.get("DATABASE_URL", "sqlite:///data/companion.db"),
        help="SQLite URL; defaults to DATABASE_URL from the local environment.",
    )
    parser.add_argument(
        "--seed-name",
        default="frontend-demo",
        help="Stable name used to make repeated runs idempotent.",
    )
    args = parser.parse_args()

    summary = seed_fake_workspace(args.database, seed_name=args.seed_name)
    print(f"Seeded Fake workspace: {args.seed_name}")
    print(f"History: {summary.history_count}")
    print(f"Concept states: {summary.concept_state_count}")
    print(f"Wrong items: {summary.wrong_item_count}")
    print(f"Due review items: {summary.review_queue_count}")
    print("Network calls: 0; paid calls: 0; existing data was not deleted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
