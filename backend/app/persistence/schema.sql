-- Proficiency ledger + session audit trail (Design.md §4).
-- LangGraph's AsyncPostgresSaver manages its own checkpoint tables separately
-- via .setup(); these are the durable, cross-session coaching records.

CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    goal        TEXT,
    background  TEXT,
    target_role TEXT
);

-- One row per user × competency. Growth = current_level - baseline_level.
CREATE TABLE IF NOT EXISTS proficiency_ledger (
    user_id        TEXT NOT NULL REFERENCES users(id),
    competency_id  TEXT NOT NULL,
    baseline_level INT,
    current_level  INT,
    target_level   INT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, competency_id)
);

CREATE TABLE IF NOT EXISTS session (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    thread_id  TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at   TIMESTAMPTZ,
    summary    TEXT
);

-- Audit trail of every scoring decision (the observability / credibility story).
CREATE TABLE IF NOT EXISTS assessment_event (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id    TEXT REFERENCES session(id),
    user_id       TEXT NOT NULL,
    competency_id TEXT NOT NULL,
    level         INT NOT NULL,
    evidence      TEXT,
    confidence    REAL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Opaque bearer tokens → user. Data access is scoped to the token's user so a
-- user_id in a URL is never trusted (closes the IDOR).
CREATE TABLE IF NOT EXISTS auth_token (
    token      TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ledger_user ON proficiency_ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_event_user  ON assessment_event(user_id);
CREATE INDEX IF NOT EXISTS idx_token_user  ON auth_token(user_id);
