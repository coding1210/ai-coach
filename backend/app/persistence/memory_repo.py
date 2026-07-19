"""In-memory Repository — zero setup, used by tests and as a demo fallback.

Not persistent across process restarts; that's fine for its two jobs. Baseline
level is captured on first sighting of a competency so growth deltas behave the
same as the Postgres implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models import AssessmentEvent, LedgerEntry
from app.persistence.repository import Repository


class MemoryRepository(Repository):
    def __init__(self) -> None:
        self._users: dict[str, dict] = {}
        self._sessions: dict[str, dict] = {}
        self._ledger: dict[tuple[str, str], LedgerEntry] = {}
        self._events: list[dict] = []
        self._reports: dict[str, dict] = {}  # user_id -> latest report
        self._tokens: dict[str, str] = {}  # token -> user_id

    async def upsert_user(self, user_id, goal, background, target_role) -> None:
        self._users[user_id] = {
            "goal": goal,
            "background": background,
            "target_role": target_role,
        }

    async def start_session(self, session_id, user_id, thread_id) -> None:
        self._sessions[session_id] = {
            "user_id": user_id,
            "thread_id": thread_id,
            "report": None,
        }

    async def finish_session(self, session_id, report) -> None:
        sess = self._sessions.get(session_id)
        if sess is not None:
            sess["report"] = report
            if report is not None:
                self._reports[sess["user_id"]] = report

    async def record_assessments(self, session_id, user_id, events: list[AssessmentEvent]) -> None:
        for e in events:
            self._events.append(
                {"session_id": session_id, "user_id": user_id, **e.model_dump()}
            )

    async def upsert_ledger_entry(
        self, user_id, competency_id, *, current_level, target_level
    ) -> None:
        key = (user_id, competency_id)
        existing = self._ledger.get(key)
        baseline = existing.baseline_level if existing else current_level
        self._ledger[key] = LedgerEntry(
            competency_id=competency_id,
            baseline_level=baseline,
            current_level=current_level,
            target_level=target_level,
            updated_at=datetime.now(timezone.utc),
        )

    async def get_progress(self, user_id) -> list[LedgerEntry]:
        return [v for (u, _), v in self._ledger.items() if u == user_id]

    async def get_latest_report(self, user_id) -> dict | None:
        return self._reports.get(user_id)

    async def store_token(self, token, user_id) -> None:
        self._tokens[token] = user_id

    async def user_for_token(self, token) -> str | None:
        return self._tokens.get(token)

    async def latest_thread(self, user_id) -> str | None:
        # Dicts preserve insertion order → the last-added session is the most recent.
        for sess in reversed(self._sessions.values()):
            if sess.get("user_id") == user_id:
                return sess.get("thread_id")
        return None
