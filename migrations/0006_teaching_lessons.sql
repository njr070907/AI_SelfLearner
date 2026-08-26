-- Purpose: persist structured teaching content generated from uploaded knowledge.
-- Recovery: restore the pre-migration SQLite backup; never edit this file after merge.

CREATE TABLE teaching_lessons (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    source_document_ids_json TEXT NOT NULL CHECK (json_valid(source_document_ids_json)),
    lesson_json TEXT NOT NULL CHECK (json_valid(lesson_json)),
    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_revision TEXT,
    prompt_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    request_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE INDEX ix_teaching_lessons_user_created
    ON teaching_lessons(user_id, created_at DESC);
