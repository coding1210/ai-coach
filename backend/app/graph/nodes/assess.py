"""Leveled assessment turns.

  ask           → pick the next competency (breadth-first by weight, or the prior
                  gaps in reassess mode) and ask ONE question phrased at the
                  CURRENT difficulty level (Foundations → Application → Design).
                  Reflects on the previous answer first. Streams. No interrupt.
  await_answer  → collect the answer (or the finish sentinel).

Difficulty ramps with `level`; the judge still scores each answer L1–L5 against
the competency's rubric, and the mastery gate (in level_review) decides whether
to advance.
"""

from __future__ import annotations

from langgraph.types import interrupt

from app.competency.loader import get_competency_map
from app.competency.selection import next_competency, reassess_targets
from app.graph.state import LEVELS, FINISH_ASSESSMENT, CoachState
from app.graph.streaming import emit_streamed_text
from app.llm.persona import COACH_PERSONA
from app.llm.providers import Message


def _last_answer(state: CoachState) -> str | None:
    for m in reversed(state.get("messages", [])):
        if m.get("role") == "user":
            return m["content"]
    return None


def _pick(state: CoachState):
    cmap = get_competency_map()
    asked = state.get("asked", [])
    if state.get("mode") == "reassess":
        remaining = [c for c in reassess_targets(cmap, state.get("prior_levels", {})) if c not in asked]
        return cmap.competency(remaining[0]) if remaining else None
    return next_competency(cmap, asked, state.get("scores", {}))


async def ask(state: CoachState) -> dict:
    competency = _pick(state)
    if competency is None:  # ran out — let routing wrap up
        return {"phase": "review"}

    level = state.get("level", 1)
    beginner = state.get("beginner", False)
    tier = LEVELS[level]

    # Level 1 is genuinely foundational — an awareness/understanding check in plain
    # language, NOT the advanced design scenario from the competency's seed question.
    if level == 1:
        if beginner:
            probe_instr = (
                f"whether they've come across {competency.name} and what they make of it — in "
                "plain everyday language, NO jargon, easy to answer even if the honest answer is 'not really'"
            )
        else:
            probe_instr = f"their basic understanding of {competency.name} — a simple foundational question, not a design scenario"
        ground = ""
    else:
        probe_instr = tier["probe"].format(name=competency.name)
        ground = f' Ground it in this intent (rephrase naturally): "{competency.sample_question}".'

    last = _last_answer(state)
    if last:
        task = (
            f'They just said: "{last}"\n\n'
            "In ONE short line, reflect genuinely on that answer. If they didn't know or were "
            "unsure, reassure them warmly and explain it in ONE plain sentence. Then ask a question "
            f"probing {probe_instr}.{ground} Keep the whole turn to 2-3 short sentences."
        )
    else:
        opener = "Open warmly in one short line" + (" (keep it beginner-friendly)" if beginner else "")
        task = f"{opener}, then ask a question probing {probe_instr}.{ground} 1-2 sentences."

    messages: list[Message] = [
        {"role": "system", "content": COACH_PERSONA},
        {"role": "user", "content": task},
    ]
    content = await emit_streamed_text("turn", messages, temperature=0.5, max_tokens=200)

    return {
        "phase": "assess",
        "asked": [competency.id],
        "level_competencies": [*state.get("level_competencies", []), competency.id],
        "level_q_count": state.get("level_q_count", 0) + 1,
        "current_competency_id": competency.id,
        "current_question": content,
        "messages": [{"role": "assistant", "content": content}],
    }


async def await_answer(state: CoachState) -> dict:
    answer = interrupt(
        {"type": "awaiting_answer", "competency_id": state.get("current_competency_id")}
    )
    answer = (answer or "").strip() if isinstance(answer, str) else str(answer)
    if answer == FINISH_ASSESSMENT:
        return {"stop_requested": True}
    return {"messages": [{"role": "user", "content": answer}]}
