-- Purpose: persist traceable wrong/weak evidence for the review backlog.
-- Previous version: 1
-- Recovery: restore the pre-migration SQLite backup; never edit this file after merge.

CREATE TABLE wrong_items (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL REFERENCES learning_sessions(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL REFERENCES feynman_questions(id) ON DELETE CASCADE,
    explanation_id TEXT NOT NULL REFERENCES user_explanations(id) ON DELETE CASCADE,
    observation_id TEXT NOT NULL UNIQUE REFERENCES provider_observations(id) ON DELETE CASCADE,
    decision_id TEXT NOT NULL UNIQUE REFERENCES mastery_decisions(id) ON DELETE CASCADE,
    source_event_id TEXT NOT NULL REFERENCES learning_events(id) ON DELETE RESTRICT,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    error_type TEXT NOT NULL CHECK (
        error_type IN ('misconception', 'gap', 'insufficient_evidence')
    ),
    error_summary TEXT NOT NULL,
    evidence_json TEXT NOT NULL CHECK (json_valid(evidence_json)),
    correction_text TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'snoozed', 'mastered')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE INDEX ix_wrong_items_user_status_created
    ON wrong_items(user_id, status, created_at DESC);
CREATE INDEX ix_wrong_items_concept_created
    ON wrong_items(concept_id, created_at DESC);
