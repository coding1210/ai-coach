"""Postgres-backed Repository (local Postgres now, Supabase later — same SQL).

Uses an async psycopg connection pool. The evaluation report is stashed as JSON
in `session.summary`; `get_latest_report` returns the most recently finished
session's report for a user.
"""

from __future__ import annotations

import json
from pathlib import Path

from psycopg.rows import dict_row
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
