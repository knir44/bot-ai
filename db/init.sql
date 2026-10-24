-- Runs once, the first time the postgres volume is created.
-- Elasticsearch stores the *knowledge* (chunks + embeddings).
-- Postgres stores the *conversations*: one row per question-and-answer turn.

CREATE TABLE IF NOT EXISTS sessions (
    id          UUID PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS chat_history (
    id          BIGSERIAL PRIMARY KEY,
    session_id  UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    question    TEXT NOT NULL,    -- what the user asked
    answer      TEXT NOT NULL,    -- what the bot replied
    sources     JSONB,            -- chunks cited in the answer
    trace       JSONB,            -- full retrieval trace (BM25 / vector / RRF / prompt) for the UI
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_history_session_created ON chat_history (session_id, created_at);
