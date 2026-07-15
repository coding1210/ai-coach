"""onboard — greet, detect returning users, and route into baseline vs
re-assessment.

If the user already has a proficiency ledger, we enter `reassess` mode: the
coach welcomes them back, names their prior top gaps, and (via mode-aware
selection) re-probes exactly those to detect growth. Otherwise it's a fresh
`baseline` assessment. The profile is supplied on the WS `start` message.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from app.competency.loader import get_competency_map
from app.competency.selection import reassess_targets
from app.graph.state import CoachState
from app.graph.streaming import emit


async def onboard(state: CoachState, config: RunnableConfig) -> dict:
    repo = (config.get("configurable") or {}).get("repo")
    prior_levels: dict[str, int] = {}
    if repo is not None:
        try:
            entries = await repo.get_progress(state.get("user_id") or "")
            prior_levels = {
                e.competency_id: e.current_level
                for e in entries
                if e.current_level is not None
            }
        except Exception:  # noqa: BLE001 — never block a session on the ledger read
            prior_levels = {}

    if prior_levels:
        cmap = get_competency_map()
        targets = reassess_targets(cmap, prior_levels)[:3]
        names = (
            ", ".join(cmap.competency(c).name for c in targets)
            if targets
            else "your focus areas"
        )
        greeting = (
            "Welcome back. I remember where we left off — last time your biggest "
            f"gaps were {names}. Let's re-check those and see how you've moved. "
            "Answer as you would today."
        )
        emit({"type": "assistant_message", "content": greeting})
        return {
            "phase": "assess",
            "mode": "reassess",
            "prior_levels": prior_levels,
            "messages": [{"role": "assistant", "content": greeting}],
        }

    greeting = (
        "Hey — good to meet you. I'm your Gen AI coach, and this is a conversation, "
        "not a test: I'll ask a few real questions to find where you're strong and where "
        "the biggest leverage is. Answer like you would on the job — let's dive in."
    )
    emit({"type": "assistant_message", "content": greeting})
    return {
        "phase": "assess",
        "mode": "baseline",
        "prior_levels": {},
        "messages": [{"role": "assistant", "content": greeting}],
    }
