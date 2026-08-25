-- Purpose: add deterministic due dates and retest history for the review queue.
-- Previous version: 2
-- Recovery: restore the pre-migration SQLite backup; never edit this file after merge.

CREATE TABLE review_items (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    wrong_item_id TEXT NOT NULL UNIQUE REFERENCES wrong_items(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('active', 'mastered')),
    due_at TEXT NOT NULL,
    interval_days INTEGER NOT NULL CHECK (interval_days > 0),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    last_result TEXT CHECK (last_result IS NULL OR last_result IN ('correct', 'partial', 'incorrect')),
    last_attempt_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE review_attempts (
    id TEXT PRIMARY KEY,
    review_item_id TEXT NOT NULL REFERENCES review_items(id) ON DELETE CASCADE,
    request_id TEXT NOT NULL UNIQUE,
    answer_text TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('succeeded', 'failed', 'invalid')),
    result TEXT CHECK (result IS NULL OR result IN ('correct', 'partial', 'incorrect')),
    observation_json TEXT CHECK (observation_json IS NULL OR json_valid(observation_json)),
    decision_json TEXT CHECK (decision_json IS NULL OR json_valid(decision_json)),
    action_json TEXT CHECK (action_json IS NULL OR json_valid(action_json)),
    error_code TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX ix_review_items_user_due
    ON review_items(user_id, status, due_at);
CREATE INDEX ix_review_attempts_item_created
    ON review_attempts(review_item_id, created_at DESC);

INSERT INTO review_items(
    id, user_id, concept_id, wrong_item_id, status, due_at, interval_days,
    attempt_count, last_result, last_attempt_id, created_at, updated_at
)
SELECT
    lower(hex(randomblob(16))), user_id, concept_id, id, 'active', created_at, 1,
    0, NULL, NULL, created_at, updated_at
FROM wrong_items;
