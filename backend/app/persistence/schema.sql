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

-- ── Practice loop (development coach) ───────────────────────────
-- Generated reps (cache) + their quality telemetry, keyed by rep id.
CREATE TABLE IF NOT EXISTS practice_rep (
    rep_id         TEXT PRIMARY KEY,
    competency_id  TEXT NOT NULL,
    rep_type       TEXT NOT NULL,
    level          INT NOT NULL,
    data           JSONB NOT NULL,
    attempts       INT NOT NULL DEFAULT 0,
    passes         INT NOT NULL DEFAULT 0,
    flags          INT NOT NULL DEFAULT 0,
    hint_exhausted INT NOT NULL DEFAULT 0,
    demoted        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rep_key ON practice_rep(competency_id, rep_type, level);

-- Who flagged which rep — one flag per user, so a single account can't demote it.
CREATE TABLE IF NOT EXISTS rep_flag (
    rep_id     TEXT NOT NULL,
    user_id    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (rep_id, user_id)
);

-- One row per graded practice attempt — the evidence trail.
CREATE TABLE IF NOT EXISTS rep_attempt (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id       TEXT NOT NULL,
    competency_id TEXT NOT NULL,
    rep_id        TEXT,
    type          TEXT,
    target_level  INT,
    level_awarded INT,
    passed        BOOLEAN,
    confidence    REAL,
    hints_used    INT NOT NULL DEFAULT 0,
    attempt_no    INT NOT NULL DEFAULT 1,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_attempt_user ON rep_attempt(user_id, competency_id);

-- Per user × competency mastery state.
CREATE TABLE IF NOT EXISTS mastery (
    user_id                TEXT NOT NULL,
    competency_id          TEXT NOT NULL,
    level                  INT NOT NULL DEFAULT 0,
    confidence             REAL NOT NULL DEFAULT 0,
    reps_cleared_at_target INT NOT NULL DEFAULT 0,
    status                 TEXT NOT NULL DEFAULT 'unseen',
    -- ISO strings (not TIMESTAMPTZ) so values round-trip identically to the
    -- in-memory repo, which the practice scheduler compares as strings.
    last_practiced_at      TEXT,
    next_rep_due_at        TEXT,
    PRIMARY KEY (user_id, competency_id)
);

CREATE INDEX IF NOT EXISTS idx_ledger_user ON proficiency_ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_event_user  ON assessment_event(user_id);
CREATE INDEX IF NOT EXISTS idx_token_user  ON auth_token(user_id);
