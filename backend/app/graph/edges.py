"""Conditional edges for the coaching graph (Design.md §2)."""

from __future__ import annotations

from app.competency.loader import get_competency_map
from app.competency.selection import next_competency, reassess_targets
from app.config import get_settings
from app.graph.state import CoachState


def _reassess_remaining(state: CoachState) -> list[str]:
    targets = reassess_targets(get_competency_map(), state.get("prior_levels", {}))
    asked = set(state.get("asked", []))
    return [c for c in targets if c not in asked]


def route_after_onboard(state: CoachState) -> str:
    """A returning user with nothing below target skips straight to the report;
    everyone else starts assessing."""
    if state.get("mode") == "reassess" and not _reassess_remaining(state):
        return "report"
    return "assess"


def route_after_score(state: CoachState) -> str:
    """Keep assessing, then move to the report.

    baseline: until weighted coverage clears the threshold (or the map is
    exhausted). reassess: until the prior weak-area worklist is exhausted."""
    if state.get("mode") == "reassess":
        return "assess" if _reassess_remaining(state) else "report"

    threshold = get_settings().coverage_threshold
    coverage = state.get("coverage", 0.0)
    more_to_ask = next_competency(get_competency_map(), state.get("asked", [])) is not None
    if coverage < threshold and more_to_ask:
        return "assess"
    return "report"


def route_after_coach(state: CoachState) -> str:
    """After teaching a focus area: if it has a graded exercise, run the
    challenge; otherwise just ask for a reply."""
    from app.eval.exercises import get_exercise_bank

    focus = state.get("focus_areas", [])
    idx = state.get("focus_index", 0)
    if idx < len(focus) and get_exercise_bank().by_competency(focus[idx]) is not None:
        return "challenge"
    return "reply"


def route_after_coach_await(state: CoachState) -> str:
    """Loop through focus areas, then persist."""
    if state.get("focus_index", 0) < len(state.get("focus_areas", [])):
        return "coach"
    return "persist"
