"""SQLite storage for append-only learning events and derived concept state."""

import json

from ai_growth_companion.domain.events import ConceptState, LearningEvent
from ai_growth_companion.repositories.database import Database


def _datetime_text(value: object) -> str:
    return str(value).replace("+00:00", "Z")


class SQLiteLearningStore:
    """Persist immutable evidence events separately from recomputable state."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def append_event(self, event: LearningEvent) -> None:
        """Append one fact; duplicate IDs or idempotency keys fail visibly."""
        with self.database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO learning_events (
                    id, user_id, session_id, concept_id, event_type, payload_json,
                    request_id, protocol_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.user_id,
                    event.session_id,
                    event.concept_id,
                    event.event_type.value,
                    json.dumps(event.payload, ensure_ascii=False, sort_keys=True),
                    event.request_id,
                    event.protocol_version,
                    _datetime_text(event.created_at.isoformat()),
                ),
            )

    def list_events(self, *, session_id: str) -> tuple[LearningEvent, ...]:
        """Return a session timeline in insertion time order."""
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, user_id, session_id, concept_id, event_type, payload_json,
                       request_id, protocol_version, created_at
                FROM learning_events
                WHERE session_id = ?
                ORDER BY created_at, rowid
                """,
                (session_id,),
            ).fetchall()

        return tuple(
            LearningEvent(
                id=row["id"],
                user_id=row["user_id"],
                session_id=row["session_id"],
                concept_id=row["concept_id"],
                event_type=row["event_type"],
                payload=json.loads(row["payload_json"]),
                request_id=row["request_id"],
                protocol_version=row["protocol_version"],
                created_at=row["created_at"],
            )
            for row in rows
        )

    def save_current_state(self, state: ConceptState) -> None:
        """Replace only the derived projection; source events remain unchanged."""
        state_json = state.model_dump_json()
        with self.database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO concept_states (
                    user_id, concept_id, mastery_level, understanding_level, score,
                    confidence, evidence_count, latest_event_id, state_json,
                    protocol_version, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, concept_id) DO UPDATE SET
                    mastery_level = excluded.mastery_level,
                    understanding_level = excluded.understanding_level,
                    score = excluded.score,
                    confidence = excluded.confidence,
                    evidence_count = excluded.evidence_count,
                    latest_event_id = excluded.latest_event_id,
                    state_json = excluded.state_json,
                    protocol_version = excluded.protocol_version,
                    updated_at = excluded.updated_at
                """,
                (
                    state.user_id,
                    state.concept_id,
                    state.mastery_level,
                    state.understanding_level,
                    state.score,
                    state.confidence,
                    state.evidence_count,
                    state.latest_event_id,
                    state_json,
                    state.protocol_version,
                    _datetime_text(state.updated_at.isoformat()),
                ),
            )

    def get_current_state(self, *, user_id: str, concept_id: str) -> ConceptState | None:
        """Load the current projection, if one has been computed."""
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM concept_states WHERE user_id = ? AND concept_id = ?",
                (user_id, concept_id),
            ).fetchone()
        return None if row is None else ConceptState.model_validate_json(row["state_json"])
