"""Level review + interleaved, opt-in coaching (the leveled loop).

After each level's batch of questions:
  level_review   → judge the batch against the tier's expected level, name weak
                   spots, decide pass/fail (mastery gate). Streams a short,
                   honest reaction.
  coach_offer    → if there are weak spots, ask whether they want coaching.
  consent_await  → capture yes/no.
  coach_light    → coach the weak spots in small, simple, encouraging messages.
  next_level     → advance the difficulty tier (state reset only).
"""

from __future__ import annotations

from langgraph.types import interrupt

from app.competency.loader import get_competency_map
from app.graph.state import LEVELS, PASS_MAX_WEAK, CoachState
from app.graph.streaming import emit, emit_streamed_text
from app.llm.persona import COACH_PERSONA
from app.llm.providers import Message

_YES = ("y", "yes", "yeah", "yep", "sure", "ok", "okay", "please", "go", "do it")


def _names(cmap, ids: list[str]) -> list[str]:
    out = []
    for cid in ids:
        try:
            out.append(cmap.competency(cid).name)
        except KeyError:
            out.append(cid)
    return out


async def level_review(state: CoachState) -> dict:
    cmap = get_competency_map()
    level = state.get("level", 1)
    tier = LEVELS[level]
    scores = state.get("scores", {})
    probed = state.get("level_competencies", [])

    weak = [cid for cid in probed if scores.get(cid, {}).get("level", 0) < tier["expected"]]
    passed = len(weak) <= PASS_MAX_WEAK
    weak_names = _names(cmap, weak)

    if not weak:
        task = (
            f"They just cleared Level {level} ({tier['name']}) cleanly. In ONE short line, "
            "give genuine, specific appreciation and say you're stepping the difficulty up."
        )
    elif passed:
        task = (
            f"They passed Level {level} ({tier['name']}) but were a little shaky on: "
            f"{', '.join(weak_names)}. In ONE-TWO short lines, appreciate the strong parts, "
            "name that soft spot plainly, and stay encouraging."
        )
    else:
        task = (
            f"They struggled at Level {level} ({tier['name']}). Weak spots: {', '.join(weak_names)}. "
            "In ONE-TWO short lines, be honest but kind — this looks like their current ceiling, "
            "and that's exactly what's worth working on. No lecture."
        )

    messages: list[Message] = [
        {"role": "system", "content": COACH_PERSONA},
        {"role": "user", "content": task},
    ]
    await emit_streamed_text("coach", messages, temperature=0.5, max_tokens=160)

    return {"phase": "review", "weak_spots": weak, "level_passed": passed}


async def coach_offer(state: CoachState) -> dict:
    names = _names(get_competency_map(), state.get("weak_spots", []))
    listed = ", ".join(names) if names else "those areas"
    msg = f"Want a quick coaching hit on {listed} before we go on? (yes or no)"
    emit({"type": "assistant_message", "content": msg})
    return {"messages": [{"role": "assistant", "content": msg}]}


async def consent_await(state: CoachState) -> dict:
    reply = interrupt({"type": "coaching_consent", "weak_spots": state.get("weak_spots", [])})
    reply = (reply or "").strip().lower() if isinstance(reply, str) else str(reply).lower()
    wants = any(reply == w or reply.startswith(w + " ") or w in reply.split() for w in _YES)
    return {"wants_coaching": wants, "messages": [{"role": "user", "content": reply}]}


async def coach_light(state: CoachState) -> dict:
    names = _names(get_competency_map(), state.get("weak_spots", []))
    task = (
        f"Coach them on these soft spots, in simple and easy language: {', '.join(names)}. "
        "For EACH, one plain-English sentence on the gap and one small, concrete tip they can try. "
        "Keep it short and encouraging — no jargon dumps, no lists longer than the items themselves."
    )
    messages: list[Message] = [
        {"role": "system", "content": COACH_PERSONA},
        {"role": "user", "content": task},
    ]
    content = await emit_streamed_text("coach", messages, temperature=0.55, max_tokens=280)
    return {"messages": [{"role": "assistant", "content": content}]}


async def next_level(state: CoachState) -> dict:
    return {
        "level": state.get("level", 1) + 1,
        "level_q_count": 0,
        "level_competencies": [],
        "weak_spots": [],
        "wants_coaching": False,
    }
