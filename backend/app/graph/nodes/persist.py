"""persist — write the durable coaching record and close the session.

Writes the proficiency ledger (baseline→current→target), the scoring audit
trail, and the evaluation report. The repository comes from the graph config
(`configurable.repo`) so the node stays backend-agnostic; if absent, persistence
is skipped (keeps the graph runnable in bare unit tests).
"""

from __future__ import annotations

from datetime import datetime, timezone

from langchain_core.runnables import RunnableConfig

from app.coaching.scheduler import schedule_after_session
from app.competency.loader import get_competency_map
from app.competency.selection import target_for
from app.graph.state import CoachState
from app.graph.streaming import emit
from app.models import AssessmentEvent
from app.persistence.repository import Repository


async def persist(state: CoachState, config: RunnableConfig) -> dict:
    repo: Repository | None = (config.get("configurable") or {}).get("repo")
    closing_text = (
        "I've saved your baseline and the focus areas we worked on. Come back and "
        "we'll re-check those and track your growth — progress here means movement "
        "on your own gaps, not finishing a course."
    )
    emit({"type": "assistant_message", "content": closing_text})
    closing = {"role": "assistant", "content": closing_text}
    if repo is None:
        return {"phase": "done", "messages": [closing]}

    cmap = get_competency_map()
    user_id = state["user_id"]
    session_id = state.get("session_id") or state["thread_id"]
    profile = state.get("profile") or {}
    scores = state.get("scores", {})

    await repo.upsert_user(
        user_id, profile.get("goal"), profile.get("background"), profile.get("target_role")
    )
    await repo.start_session(session_id, user_id, state["thread_id"])

    events = [
        AssessmentEvent(
            competency_id=cid,
            level=s["level"],
            evidence=s["evidence"],
            confidence=s["confidence"],
        )
        for cid, s in scores.items()
    ]
    await repo.record_assessments(session_id, user_id, events)

    for cid, s in scores.items():
        target = target_for(cmap, cid, state.get("jd_targets"))
        await repo.upsert_ledger_entry(
            user_id, cid, current_level=s["level"], target_level=target
        )

    await repo.finish_session(session_id, state.get("report"))

    # Schedule spaced re-assessment so the coach resurfaces weak spots over time.
    entries = await repo.get_progress(user_id)
    for cid, when in schedule_after_session(entries, datetime.now(timezone.utc)).items():
        await repo.set_next_review(user_id, cid, when)

    return {"phase": "done", "messages": [closing]}
