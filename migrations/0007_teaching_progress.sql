-- Purpose: persist conventional lesson progress and interactive activity attempts.
-- Recovery: restore the pre-migration SQLite backup; never edit this file after merge.

CREATE TABLE teaching_lesson_progress (
    lesson_id TEXT NOT NULL REFERENCES teaching_lessons(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_section INTEGER NOT NULL DEFAULT 0 CHECK (current_section >= 0),
    completed_activity_indexes_json TEXT NOT NULL
        CHECK (json_valid(completed_activity_indexes_json)),
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    PRIMARY KEY (lesson_id, user_id)
);

CREATE TABLE teaching_activity_attempts (
    id TEXT PRIMARY KEY,
    lesson_id TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_index INTEGER NOT NULL CHECK (activity_index >= 1),
    selected_answer TEXT NOT NULL,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    request_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    FOREIGN KEY (lesson_id, user_id)
        REFERENCES teaching_lesson_progress(lesson_id, user_id)
        ON DELETE CASCADE
);

CREATE INDEX ix_teaching_progress_user_updated
    ON teaching_lesson_progress(user_id, updated_at DESC);

CREATE INDEX ix_teaching_attempts_lesson_activity
    ON teaching_activity_attempts(lesson_id, user_id, activity_index, created_at DESC);
