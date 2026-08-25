-- Purpose: make learner feedback submissions idempotent while retaining correction events.

ALTER TABLE diagnosis_feedback ADD COLUMN request_id TEXT;

CREATE UNIQUE INDEX ux_diagnosis_feedback_request
    ON diagnosis_feedback(request_id)
    WHERE request_id IS NOT NULL;
