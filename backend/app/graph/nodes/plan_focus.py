"""plan_focus — lock in the top gap×weight competencies to coach (Design.md §7→§8).

The report already ranked priorities; this node commits them to `focus_areas`
and resets the coaching cursor. Kept as its own node so the selection policy can
evolve (e.g. honor a user's explicit "I want to work on X") independently.
"""

from __future__ import annotations

from app.graph.state import CoachState


async def plan_focus(state: CoachState) -> dict:
    report = state.get("report") or {}
    focus = list(report.get("priorities", []))[:3]
    return {"phase": "coach", "focus_areas": focus, "focus_index": 0}
