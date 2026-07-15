"""LangGraph state schema (Design.md §3).

A TypedDict updated across nodes. `messages` and `asked` use append reducers;
other channels are overwritten wholesale by the node that owns them.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

# Sentinel the client sends (via a "finish" WS message) to end assessment early
# and jump to the evaluation.
FINISH_ASSESSMENT = "__finish_assessment__"


class CompetencyScore(TypedDict):
    competency_id: str
    level: int          # 1..5 (Dreyfus)
    evidence: str       # judge's justification; quotes the user
    confidence: float   # 0..1


class CoachState(TypedDict, total=False):
    # identity / persistence
    thread_id: str
    user_id: str
    session_id: str

    # who the user is (goal, background, target_role)
    profile: dict

    # conversation + assessment progress
    messages: Annotated[list[dict], operator.add]   # {role, content}
    asked: Annotated[list[str], operator.add]        # competency_ids probed
    scores: dict[str, CompetencyScore]               # competency_id -> score
    coverage: float                                  # 0..1 weighted coverage

    # transient assessment cursor
    current_competency_id: str | None
    current_question: str | None
    stop_requested: bool  # user opted to see results early

    # report + coaching
    report: dict | None
    focus_areas: list[str]                           # competency_ids to coach
    focus_index: int                                 # cursor into focus_areas

    # re-assessment (returning user)
    mode: str                                        # baseline | reassess
    prior_levels: dict[str, int]                     # competency_id -> last current_level

    phase: str  # onboard | assess | report | coach | done
