-- Purpose: add the local document library used by the self-study workspace.
-- Files stay on disk; SQLite stores metadata and the generated storage name.

CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    storage_name TEXT NOT NULL UNIQUE,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes > 0),
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    status TEXT NOT NULL DEFAULT 'ready' CHECK (status IN ('ready', 'replaced')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX ix_documents_user_updated
    ON documents(user_id, updated_at DESC);
