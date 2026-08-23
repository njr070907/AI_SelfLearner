"""Event history and current-state separation tests."""

from pathlib import Path
from uuid import uuid4

from ai_growth_companion.domain.events import (
    LOCAL_USER_ID,
    ConceptState,
    EventType,
    LearningEvent,
)
from ai_growth_companion.repositories.database import Database, run_migrations
from ai_growth_companion.repositories.learning_store import SQLiteLearningStore


def setup_store(tmp_path: Path) -> tuple[SQLiteLearningStore, str, str]:
    database = Database(f"sqlite:///{(tmp_path / 'events.db').as_posix()}")
    run_migrations(database)
    concept_id = str(uuid4())
    session_id = str(uuid4())
    with database.connect() as connection, connection:
        connection.execute(
            """
            INSERT INTO concepts(id, normalized_name, display_name, domain, created_at)
            VALUES (?, '递归', '递归', 'programming', '2026-08-23T00:00:00Z')
            """,
            (concept_id,),
        )
        connection.execute(
            """
            INSERT INTO learning_sessions(
                id, user_id, concept_id, status, request_id, started_at
            ) VALUES (?, ?, ?, 'created', ?, '2026-08-23T00:00:00Z')
            """,
            (session_id, LOCAL_USER_ID, concept_id, str(uuid4())),
        )
    return SQLiteLearningStore(database), concept_id, session_id


def test_event_history_remains_when_projection_changes(tmp_path: Path) -> None:
    store, concept_id, session_id = setup_store(tmp_path)
    event = LearningEvent(
        id=str(uuid4()),
        user_id=LOCAL_USER_ID,
        session_id=session_id,
        concept_id=concept_id,
        event_type=EventType.ANSWER_SUBMITTED,
        payload={"answer_length": 12},
        request_id=str(uuid4()),
    )
    store.append_event(event)

    first_state = ConceptState(
        user_id=LOCAL_USER_ID,
        concept_id=concept_id,
        mastery_level="fragile",
        understanding_level="novice",
        score=35,
        confidence=0.4,
        evidence_count=1,
        evidence_ids=[event.id],
        latest_event_id=event.id,
        protocol_version="mastery-protocol-v0.1-demo",
    )
    store.save_current_state(first_state)
    store.save_current_state(first_state.model_copy(update={"score": 45}))

    assert store.get_current_state(user_id=LOCAL_USER_ID, concept_id=concept_id).score == 45  # type: ignore[union-attr]
    assert store.list_events(session_id=session_id) == (event,)
