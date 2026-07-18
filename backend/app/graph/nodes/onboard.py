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
from app.llm.router import get_router

_CALIBRATE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"start_level": {"type": "integer"}, "beginner": {"type": "boolean"}},
    "required": ["start_level", "beginner"],
}


async def _calibrate(profile: dict) -> tuple[int, bool]:
    """Estimate where to start from the stated background — so a beginner gets a
    gentle Level 1 and someone experienced skips the trivial. Defaults to L1."""
    bg = (profile or {}).get("background", "").strip()
    if not bg:
        return 1, False
    try:
        r = await get_router().complete_json(
            "turn",
            [
                {"role": "system", "content": "You calibrate a Gen AI engineering assessment. JSON only."},
                {
                    "role": "user",
                    "content": (
                        f"Background: {bg}\nGoal: {(profile or {}).get('goal', '')}\n\n"
                        "start_level: 1 = little/no Python or AI (needs foundations), "
                        "2 = some Python + tutorial-level LLM/AI, 3 = ships AI features / strong. "
                        "beginner: true if they have little or no coding OR AI background. "
                        "Return {start_level, beginner}."
                    ),
                },
            ],
            schema=_CALIBRATE_SCHEMA,
            temperature=0,
        )
        # Cap the skip at L2 so no one is thrown straight into design-level questions.
        return min(2, max(1, int(r.get("start_level", 1)))), bool(r.get("beginner", False))
    except Exception:  # noqa: BLE001
        return 1, False


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
            "level": 1,
            "level_q_count": 0,
            "level_competencies": [],
            "messages": [{"role": "assistant", "content": greeting}],
        }

    level, beginner = await _calibrate(state.get("profile") or {})
    if beginner:
        greeting = (
            "Hey — great to have you here. No pressure and no jargon: I'll ask a few plain "
            "questions to see what you already know, and wherever something's new I'll explain "
            "it simply. There are no wrong answers — let's start easy."
        )
    else:
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
        "level": level,
        "beginner": beginner,
        "level_q_count": 0,
        "level_competencies": [],
        "messages": [{"role": "assistant", "content": greeting}],
    }
