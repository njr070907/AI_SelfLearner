-- Purpose: establish the Sprint 0 evidence-first data model.
-- Previous version: 0
-- Recovery: restore the pre-migration SQLite backup; never edit this file after merge.

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    locale TEXT NOT NULL DEFAULT 'zh-CN',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE concepts (
    id TEXT PRIMARY KEY,
    normalized_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    domain TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE (normalized_name, domain)
);

CREATE TABLE learning_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (
        status IN (
            'created', 'questioned', 'answered', 'diagnosed',
            'question_failed', 'diagnosis_failed'
        )
    ),
    learning_goal TEXT,
    learner_level TEXT,
    request_id TEXT NOT NULL UNIQUE,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    error_code TEXT
);

CREATE TABLE feynman_questions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE REFERENCES learning_sessions(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    coverage_points_json TEXT NOT NULL CHECK (json_valid(coverage_points_json)),
    difficulty TEXT NOT NULL,
    question_type TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_revision TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE user_explanations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES learning_sessions(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL REFERENCES feynman_questions(id) ON DELETE CASCADE,
    answer_text TEXT NOT NULL,
    answer_type TEXT NOT NULL CHECK (answer_type IN ('main', 'follow_up')),
    sequence_no INTEGER NOT NULL CHECK (sequence_no >= 1),
    request_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    UNIQUE (session_id, sequence_no)
);

CREATE TABLE provider_observations (
    id TEXT PRIMARY KEY,
    explanation_id TEXT NOT NULL REFERENCES user_explanations(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('succeeded', 'failed', 'invalid')),
    attempt_no INTEGER NOT NULL CHECK (attempt_no >= 1),
    result_json TEXT CHECK (result_json IS NULL OR json_valid(result_json)),
    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_revision TEXT,
    prompt_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    request_id TEXT NOT NULL UNIQUE,
    latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    usage_json TEXT CHECK (usage_json IS NULL OR json_valid(usage_json)),
    finish_reason TEXT,
    error_code TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (explanation_id, attempt_no)
);

CREATE TABLE mastery_decisions (
    id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL UNIQUE REFERENCES provider_observations(id) ON DELETE CASCADE,
    mastery_level TEXT NOT NULL CHECK (
        mastery_level IN ('not_evident', 'fragile', 'developing', 'solid')
    ),
    understanding_level TEXT NOT NULL CHECK (
        understanding_level IN ('novice', 'developing', 'proficient')
    ),
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    evidence_ids_json TEXT NOT NULL CHECK (json_valid(evidence_ids_json)),
    reason TEXT NOT NULL,
    protocol_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE learning_actions (
    id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL UNIQUE REFERENCES mastery_decisions(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL CHECK (
        action_type IN ('review', 'example', 'practice', 're_explain')
    ),
    instruction TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL CHECK (json_valid(evidence_ids_json)),
    policy_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE diagnosis_feedback (
    id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL REFERENCES mastery_decisions(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    verdict TEXT NOT NULL CHECK (verdict IN ('accurate', 'partial', 'inaccurate')),
    note TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE learning_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT REFERENCES learning_sessions(id) ON DELETE CASCADE,
    concept_id TEXT REFERENCES concepts(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (length(event_type) > 0),
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
    request_id TEXT,
    protocol_version TEXT,
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX ux_learning_events_request_type
    ON learning_events(request_id, event_type)
    WHERE request_id IS NOT NULL;

CREATE TABLE concept_states (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    mastery_level TEXT NOT NULL CHECK (
        mastery_level IN ('not_evident', 'fragile', 'developing', 'solid')
    ),
    understanding_level TEXT NOT NULL CHECK (
        understanding_level IN ('novice', 'developing', 'proficient')
    ),
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    evidence_count INTEGER NOT NULL CHECK (evidence_count >= 0),
    latest_event_id TEXT REFERENCES learning_events(id) ON DELETE SET NULL,
    state_json TEXT NOT NULL CHECK (json_valid(state_json)),
    protocol_version TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, concept_id)
);

CREATE TABLE idempotency_records (
    request_id TEXT PRIMARY KEY,
    operation TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    response_json TEXT CHECK (response_json IS NULL OR json_valid(response_json)),
    created_at TEXT NOT NULL
);

CREATE INDEX ix_sessions_user_started
    ON learning_sessions(user_id, started_at DESC);
CREATE INDEX ix_sessions_concept_started
    ON learning_sessions(concept_id, started_at DESC);
CREATE INDEX ix_events_session_created
    ON learning_events(session_id, created_at);
CREATE INDEX ix_events_user_type_created
    ON learning_events(user_id, event_type, created_at DESC);
CREATE INDEX ix_observations_explanation_created
    ON provider_observations(explanation_id, created_at DESC);

INSERT INTO users (id, display_name, locale, created_at, updated_at)
VALUES (
    '00000000-0000-4000-8000-000000000001',
    'default',
    'zh-CN',
    '2026-08-23T00:00:00Z',
    '2026-08-23T00:00:00Z'
);

