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

# Leveled adaptive assessment: start easy, ramp up, gate on mastery.
QUESTIONS_PER_LEVEL = 3
MAX_LEVEL = 3
PASS_MAX_WEAK = 1  # a level is "passed" with at most this many weak answers

LEVELS = {
    1: {
        "name": "Foundations",
        "expected": 2,  # judged level below this = a weak spot at this tier
        "probe": "a foundational question that checks whether they genuinely understand the basics of {name}",
    },
    2: {
        "name": "Application",
        "expected": 3,
        "probe": "how they've applied {name} in a real project — push on the deliberate trade-offs they made",
    },
    3: {
        "name": "Design & Debugging",
        "expected": 4,
        "probe": "a realistic failure or design scenario for {name} and ask how they'd diagnose or architect it",
    },
}


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

    # leveled assessment
    level: int                                       # 1..MAX_LEVEL (difficulty tier)
    beginner: bool                                   # little/no Python-AI background — keep it plain
    level_q_count: int                               # questions asked in current level
    level_competencies: list[str]                    # competency_ids probed this level
    weak_spots: list[str]                            # competency_ids flagged this level
    intent: str                                      # triage of the last answer (answer|distress|…)
    level_passed: bool                               # cleared the mastery gate this level
    wants_coaching: bool                             # user opted into coaching on weak spots
    stop_requested: bool                             # user ended assessment early

    # report + coaching
    report: dict | None
    focus_areas: list[str]                           # competency_ids to coach (legacy)
    focus_index: int

    # re-assessment (returning user)
    mode: str                                        # baseline | reassess
    prior_levels: dict[str, int]                     # competency_id -> last current_level

    # JD-targeted diagnosis
    jd_targets: dict[str, int]                       # domain_id -> required level (from the JD)
    role_title: str                                  # role parsed from the JD

    phase: str  # onboard | assess | review | coach | done
