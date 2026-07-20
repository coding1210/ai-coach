"""Postgres-backed Repository (local Postgres now, Supabase later — same SQL).

Uses an async psycopg connection pool. The evaluation report is stashed as JSON
in `session.summary`; `get_latest_report` returns the most recently finished
session's report for a user.
"""

from __future__ import annotations

import json
from pathlib import Path

from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import AsyncConnectionPool

from app.models import AssessmentEvent, LedgerEntry
from app.persistence.repository import Repository

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class PostgresRepository(Repository):
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @classmethod
    async def create(cls, database_url: str) -> "PostgresRepository":
        pool = AsyncConnectionPool(database_url, open=False, kwargs={"row_factory": dict_row})
        await pool.open()
        repo = cls(pool)
        await repo._setup()
        return repo

    async def _setup(self) -> None:
        ddl = _SCHEMA_PATH.read_text(encoding="utf-8")
        async with self._pool.connection() as conn:
            await conn.execute(ddl)

    async def close(self) -> None:
        await self._pool.close()

    async def upsert_user(self, user_id, goal, background, target_role) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, goal, background, target_role)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                  SET goal = EXCLUDED.goal,
                      background = EXCLUDED.background,
                      target_role = EXCLUDED.target_role
                """,
                (user_id, goal, background, target_role),
            )

    async def start_session(self, session_id, user_id, thread_id) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO session (id, user_id, thread_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (session_id, user_id, thread_id),
            )

    async def finish_session(self, session_id, report) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                UPDATE session
                   SET ended_at = now(),
                       summary = %s
                 WHERE id = %s
                """,
                (json.dumps(report) if report is not None else None, session_id),
            )

    async def record_assessments(self, session_id, user_id, events: list[AssessmentEvent]) -> None:
        if not events:
            return
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(
                    """
                    INSERT INTO assessment_event
                        (session_id, user_id, competency_id, level, evidence, confidence)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (session_id, user_id, e.competency_id, e.level, e.evidence, e.confidence)
                        for e in events
                    ],
                )

    async def upsert_ledger_entry(
        self, user_id, competency_id, *, current_level, target_level
    ) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO proficiency_ledger
                    (user_id, competency_id, baseline_level, current_level, target_level, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (user_id, competency_id) DO UPDATE
                  SET current_level = EXCLUDED.current_level,
                      target_level  = EXCLUDED.target_level,
                      updated_at    = now()
                """,
                (user_id, competency_id, current_level, current_level, target_level),
            )

    async def get_progress(self, user_id) -> list[LedgerEntry]:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT competency_id, baseline_level, current_level, target_level, updated_at
                  FROM proficiency_ledger
                 WHERE user_id = %s
                 ORDER BY competency_id
                """,
                (user_id,),
            )
            rows = await cur.fetchall()
        return [LedgerEntry.model_validate(r) for r in rows]

    async def get_latest_report(self, user_id) -> dict | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT summary
                  FROM session
                 WHERE user_id = %s AND summary IS NOT NULL
                 ORDER BY COALESCE(ended_at, started_at) DESC
                 LIMIT 1
                """,
                (user_id,),
            )
            row = await cur.fetchone()
        if not row or not row["summary"]:
            return None
        summary = row["summary"]
        return summary if isinstance(summary, dict) else json.loads(summary)

    async def store_token(self, token, user_id) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                "INSERT INTO auth_token (token, user_id) VALUES (%s, %s) "
                "ON CONFLICT (token) DO NOTHING",
                (token, user_id),
            )

    async def user_for_token(self, token) -> str | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT user_id FROM auth_token WHERE token = %s", (token,)
            )
            row = await cur.fetchone()
        return row["user_id"] if row else None

    # ── practice reps + telemetry (durable; overrides the base aux store) ──
    _FLAG_DEMOTE_AT = 2

    async def save_rep(self, rep_id, competency_id, rep_type, level, data) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO practice_rep (rep_id, competency_id, rep_type, level, data)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (rep_id) DO UPDATE SET data = EXCLUDED.data
                """,
                (rep_id, competency_id, rep_type, level, Json(data)),
            )

    async def get_rep(self, rep_id) -> dict | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute("SELECT data FROM practice_rep WHERE rep_id = %s", (rep_id,))
            row = await cur.fetchone()
        return row["data"] if row else None

    async def get_cached_rep(self, competency_id, rep_type, level) -> dict | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT data FROM practice_rep
                 WHERE competency_id = %s AND rep_type = %s AND level = %s AND NOT demoted
                 ORDER BY created_at DESC LIMIT 1
                """,
                (competency_id, rep_type, level),
            )
            row = await cur.fetchone()
        return row["data"] if row else None

    async def record_rep_outcome(self, rep_id, passed, hint_exhausted=False) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                UPDATE practice_rep
                   SET attempts = attempts + 1,
                       passes = passes + %s,
                       hint_exhausted = hint_exhausted + %s
                 WHERE rep_id = %s
                """,
                (1 if passed else 0, 1 if hint_exhausted else 0, rep_id),
            )

    async def flag_rep(self, rep_id) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                "UPDATE practice_rep SET flags = flags + 1, "
                "demoted = (flags + 1 >= %s) WHERE rep_id = %s",
                (self._FLAG_DEMOTE_AT, rep_id),
            )

    async def get_rep_stats(self) -> list[dict]:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT rep_id, attempts, passes, flags, hint_exhausted, demoted FROM practice_rep"
            )
            return list(await cur.fetchall())

    async def add_rep_attempt(self, user_id, attempt) -> int:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT count(*) AS n FROM rep_attempt WHERE user_id = %s AND competency_id = %s",
                (user_id, attempt.get("competency_id")),
            )
            n = (await cur.fetchone())["n"] + 1
            await conn.execute(
                """
                INSERT INTO rep_attempt
                    (user_id, competency_id, rep_id, type, target_level, level_awarded,
                     passed, confidence, hints_used, attempt_no)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, attempt.get("competency_id"), attempt.get("rep_id"), attempt.get("type"),
                 attempt.get("target_level"), attempt.get("level_awarded"), attempt.get("passed"),
                 attempt.get("confidence"), attempt.get("hints_used", 0), n),
            )
        return n

    async def get_rep_attempts(self, user_id, competency_id=None) -> list[dict]:
        q = ("SELECT competency_id, rep_id, type, target_level, level_awarded, passed, "
             "confidence, hints_used, attempt_no FROM rep_attempt WHERE user_id = %s")
        params: tuple = (user_id,)
        if competency_id is not None:
            q += " AND competency_id = %s"
            params = (user_id, competency_id)
        q += " ORDER BY id"
        async with self._pool.connection() as conn:
            cur = await conn.execute(q, params)
            return list(await cur.fetchall())

    async def get_mastery(self, user_id, competency_id) -> dict | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT * FROM mastery WHERE user_id = %s AND competency_id = %s",
                (user_id, competency_id),
            )
            row = await cur.fetchone()
        if row:
            row.pop("user_id", None)
        return row

    async def get_all_mastery(self, user_id) -> dict[str, dict]:
        async with self._pool.connection() as conn:
            cur = await conn.execute("SELECT * FROM mastery WHERE user_id = %s", (user_id,))
            rows = await cur.fetchall()
        out = {}
        for r in rows:
            r.pop("user_id", None)
            out[r["competency_id"]] = r
        return out

    async def upsert_mastery(self, user_id, competency_id, data) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO mastery
                    (user_id, competency_id, level, confidence, reps_cleared_at_target,
                     status, last_practiced_at, next_rep_due_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, competency_id) DO UPDATE
                  SET level = EXCLUDED.level,
                      confidence = EXCLUDED.confidence,
                      reps_cleared_at_target = EXCLUDED.reps_cleared_at_target,
                      status = EXCLUDED.status,
                      last_practiced_at = EXCLUDED.last_practiced_at,
                      next_rep_due_at = EXCLUDED.next_rep_due_at
                """,
                (user_id, competency_id, data.get("level", 0), data.get("confidence", 0.0),
                 data.get("reps_cleared_at_target", 0), data.get("status", "unseen"),
                 data.get("last_practiced_at"), data.get("next_rep_due_at")),
            )
