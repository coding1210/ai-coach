"""Repository interface for the durable coaching records.

Two implementations behind one interface:
  - PostgresRepository  → local Postgres now, Supabase later (same SQL).
  - MemoryRepository     → zero-setup, used by tests and as a demo fallback.

The graph's `persist` node depends only on this interface, so swapping the
backend never touches coaching logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import AssessmentEvent, LedgerEntry


class Repository(ABC):
    @abstractmethod
    async def upsert_user(
        self, user_id: str, goal: str | None, background: str | None, target_role: str | None
    ) -> None: ...

    @abstractmethod
    async def start_session(self, session_id: str, user_id: str, thread_id: str) -> None: ...

    @abstractmethod
    async def finish_session(self, session_id: str, report: dict | None) -> None:
        """Mark a session ended and stash its evaluation report (as JSON)."""

    @abstractmethod
    async def record_assessments(
        self, session_id: str, user_id: str, events: list[AssessmentEvent]
    ) -> None: ...

    @abstractmethod
    async def upsert_ledger_entry(
        self,
        user_id: str,
        competency_id: str,
        *,
        current_level: int,
        target_level: int,
    ) -> None:
        """Upsert one ledger row. baseline_level is set once (first sighting) and
        never overwritten, so growth = current - baseline is meaningful."""

    @abstractmethod
    async def get_progress(self, user_id: str) -> list[LedgerEntry]: ...

    @abstractmethod
    async def get_latest_report(self, user_id: str) -> dict | None: ...

    # ── auth ─────────────────────────────────────────────────────
    @abstractmethod
    async def store_token(self, token: str, user_id: str) -> None: ...

    @abstractmethod
    async def user_for_token(self, token: str) -> str | None:
        """Resolve a bearer token to its user_id, or None if unknown."""

    # ── auxiliary records (outcomes / shares / review schedule) ──
    # Concrete, lightweight storage shared by every backend. These power the
    # program features (spaced re-assessment, sharing, outcome tracking) without
    # needing per-backend schema; the core ledger/report/auth stay authoritative.
    def _aux(self, name: str) -> dict:
        store = getattr(self, "_aux_store", None)
        if store is None:
            store = {}
            object.__setattr__(self, "_aux_store", store)
        return store.setdefault(name, {})

    async def record_outcome(self, user_id: str, outcome: dict) -> None:
        self._aux("outcomes").setdefault(user_id, []).append(outcome)

    async def get_outcomes(self, user_id: str) -> list[dict]:
        return list(self._aux("outcomes").get(user_id, []))

    async def create_share(self, token: str, snapshot: dict) -> None:
        self._aux("shares")[token] = snapshot

    async def get_share(self, token: str) -> dict | None:
        return self._aux("shares").get(token)

    async def set_next_review(self, user_id: str, competency_id: str, when_iso: str) -> None:
        self._aux("reviews").setdefault(user_id, {})[competency_id] = when_iso

    async def get_next_reviews(self, user_id: str) -> dict[str, str]:
        return dict(self._aux("reviews").get(user_id, {}))

    async def close(self) -> None:  # optional lifecycle hook
        return None
