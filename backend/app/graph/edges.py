"""Conditional edges for the leveled coaching graph.

Flow: onboard → (ask → await → score)×N per level → level_review →
[weak? coach_offer → consent → maybe coach_light] → mastery gate →
next_level (loop) or report → persist.
"""

from __future__ import annotations

from app.competency.loader import get_competency_map
from app.competency.selection import next_competency, reassess_targets
from app.graph.state import MAX_LEVEL, QUESTIONS_PER_LEVEL, CoachState


def _reassess_remaining(state: CoachState) -> list[str]:
    targets = reassess_targets(get_competency_map(), state.get("prior_levels", {}))
    asked = set(state.get("asked", []))
    return [c for c in targets if c not in asked]


def _more_to_ask(state: CoachState) -> bool:
    if state.get("mode") == "reassess":
        return bool(_reassess_remaining(state))
    return next_competency(get_competency_map(), state.get("asked", [])) is not None


def route_after_onboard(state: CoachState) -> str:
    if state.get("mode") == "reassess" and not _reassess_remaining(state):
        return "report"
    return "ask"


def route_after_score(state: CoachState) -> str:
    """Keep asking until the level's batch is done (or we run out), then review."""
    if state.get("stop_requested"):
        return "report"
    if state.get("level_q_count", 0) < QUESTIONS_PER_LEVEL and _more_to_ask(state):
        return "ask"
    return "review"


def _gate(state: CoachState) -> str:
    """Mastery gate: advance only if the level was passed and there's a level left."""
    if state.get("level_passed") and state.get("level", 1) < MAX_LEVEL and _more_to_ask(state):
        return "next_level"
    return "report"


def route_after_review(state: CoachState) -> str:
    """Offer coaching if there are weak spots; otherwise apply the gate."""
    if state.get("weak_spots"):
        return "offer"
    return _gate(state)


def route_after_consent(state: CoachState) -> str:
    if state.get("wants_coaching"):
        return "coach_light"
    return _gate(state)


def route_after_coach_light(state: CoachState) -> str:
    return _gate(state)
