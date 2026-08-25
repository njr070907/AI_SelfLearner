"""Contract tests for the repeatable frontend demo workspace seed."""

from pathlib import Path

from ai_growth_companion.application.demo_workspace import seed_fake_workspace


def test_fake_workspace_seed_is_rich_and_idempotent(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'demo.db').as_posix()}"

    first = seed_fake_workspace(database_url, seed_name="ui-contract")
    second = seed_fake_workspace(database_url, seed_name="ui-contract")

    assert first == second
    assert first.history_count == 4
    assert first.concept_state_count == 3
    assert first.wrong_item_count == 3
    assert first.review_queue_count == 3
