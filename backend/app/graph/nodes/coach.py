"""coach — Socratic, short-turn coaching (Options + Will phases of GROW).

Instead of a four-part lecture, the coach opens each focus area with a brief
frame and ONE question that gets the engineer thinking (ask-more-than-tell),
then reacts to their reply with a short reflection that fills the single most
important gap. Where a competency has a graded exercise, the coach tees up the
hands-on challenge instead of a talk-only question.

  coach        → resource tool-call + a short opener (frame + question OR lead-in
                 to the challenge). Streams. No interrupt.
  coach_await  → collect the reply, reflect briefly, advance the focus cursor.
"""

from __future__ import annotations

from langgraph.types import interrupt

from app.competency.loader import get_competency_map
from app.eval.exercises import get_exercise_bank
from app.graph.state import FINISH_ASSESSMENT, CoachState
from app.graph.streaming import emit, emit_streamed_text
from app.llm.persona import COACH_PERSONA
from app.llm.providers import Message
from app.llm.router import get_router
from app.llm.tools import research_resource


async def coach(state: CoachState) -> dict:
    cmap = get_competency_map()
    focus = state.get("focus_areas", [])
    idx = state.get("focus_index", 0)
    if idx >= len(focus):
        return {}

    competency = cmap.competency(focus[idx])
    domain = cmap.domain_of(competency.id)
    level = (state.get("scores") or {}).get(competency.id, {}).get("level", 2)
    has_exercise = get_exercise_bank().by_competency(competency.id) is not None

    resource = await research_resource(domain.id, competency.name)
    emit(
        {
            "type": "tool_call",
            "name": "research_resource",
            "competency_id": competency.id,
            "result": resource,
        }
    )

    if has_exercise:
        task = (
            f"You're moving to coach them on {competency.name} (they're around L{level}/5). "
            "In 2 short sentences: one warm line on why this matters at their level, then say "
            "you'd rather see it than talk about it — you're going to give them a quick hands-on "
            "task. Don't explain the solution. (A resource is on hand: "
            f"'{resource['title']}'.)"
        )
    else:
        task = (
            f"Coach them on {competency.name} (they're around L{level}/5). In 2-3 short sentences: "
            "one warm framing line, then ONE Socratic question that makes them reason about the core "
            "of this at their level. Don't give the answer — draw it out. You may nod to the resource "
            f"'{resource['title']}' in a clause."
        )

    messages: list[Message] = [
        {"role": "system", "content": COACH_PERSONA},
        {"role": "user", "content": task},
    ]
    content = await emit_streamed_text(
        get_router().for_task("coach"), messages, temperature=0.6, max_tokens=220
    )
    return {"phase": "coach", "messages": [{"role": "assistant", "content": content}]}


async def coach_await(state: CoachState) -> dict:
    focus = state.get("focus_areas", [])
    idx = state.get("focus_index", 0)
    comp_id = focus[idx] if idx < len(focus) else None

    reply = interrupt(
        {"type": "coach_prompt", "competency_id": comp_id, "focus_index": idx}
    )
    reply = (reply or "").strip() if isinstance(reply, str) else str(reply)

    # A stray finish signal here just means "move on" — don't reflect on it.
    if reply == FINISH_ASSESSMENT:
        return {"focus_index": idx + 1}

    out_messages: list[dict] = [{"role": "user", "content": reply}]
    if comp_id:
        competency = get_competency_map().competency(comp_id)
        task = (
            f'They answered your coaching question about {competency.name} with: "{reply}"\n\n'
            "In ONE or TWO short sentences: reflect what they got right, gently fill the single most "
            "important gap, and encourage them to keep going. No lecture, no list."
        )
        content = await emit_streamed_text(
            get_router().for_task("coach"),
            [{"role": "system", "content": COACH_PERSONA}, {"role": "user", "content": task}],
            temperature=0.5,
            max_tokens=180,
        )
        out_messages.append({"role": "assistant", "content": content})

    return {"focus_index": idx + 1, "messages": out_messages}
