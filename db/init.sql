-- Runs once, the first time the postgres volume is created.
-- Elasticsearch stores the *knowledge* (chunks + embeddings).
-- Postgres stores the *conversations* (who asked what, and what we answered).

CREATE TABLE IF NOT EXISTS sessions (
    id          UUID PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS messages (
    id          BIGSERIAL PRIMARY KEY,
    session_id  UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    sources     JSONB,            -- chunks cited for an assistant answer
    trace       JSONB,            -- full retrieval trace (BM25 / vector / RRF / prompt) for the UI
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_session_created ON messages (session_id, created_at);
