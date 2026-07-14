"""coach — mentor the current focus competency, then pause for the user.

Split into two nodes so the LLM generation is never re-run by interrupt resume:
  coach        → generate the explain → challenge → exercise → resource turn
                 (LLM), commit it as a message. No interrupt here.
  coach_await  → interrupt for the user's reply, advance the focus cursor.

Resource fetching is inline/LLM-suggested in v1; wiring a real research tool-call
(FR5) is a Phase-2 extension that slots into the `coach` node.
"""

from __future__ import annotations

from langgraph.types import interrupt

from app.competency.loader import get_competency_map
from app.graph.state import CoachState
from app.graph.streaming import emit, emit_streamed_text
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
    score = (state.get("scores") or {}).get(competency.id, {})
    level = score.get("level", 2)

    # Agentic step (FR5): fetch a resource for this gap, surfaced as a tool_call.
    resource = await research_resource(domain.id, competency.name)
    emit(
        {
            "type": "tool_call",
            "name": "research_resource",
            "competency_id": competency.id,
            "result": resource,
        }
    )

    messages: list[Message] = [
        {
            "role": "system",
            "content": (
                "You are a senior Gen AI engineering coach running a focused mentoring "
                "turn on ONE competency. Meet the engineer at their current level and "
                "move them one step up. Structure the turn as: (1) a crisp explanation "
                "pitched just above their level, (2) a realistic scenario/challenge, "
                "(3) one small concrete exercise, (4) point to the provided resource by "
                "name. Keep it conversational and encouraging — coaching, not lecturing. "
                "End by inviting them to try the exercise or ask to move on."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Competency: {competency.name} ({competency.id})\n"
                f"Their current level: L{level} of 5.\n"
                f"L2 looks like: {competency.level_anchors.get('2', 'n/a')}\n"
                f"L4 looks like: {competency.level_anchors.get('4', 'n/a')}\n"
                f"Resource to recommend: {resource['title']} ({resource['url']})\n"
                "Coach them on this now."
            ),
        },
    ]
    provider = get_router().for_task("coach")
    content = await emit_streamed_text(provider, messages, temperature=0.6, max_tokens=700)
    return {"phase": "coach", "messages": [{"role": "assistant", "content": content}]}


async def coach_await(state: CoachState) -> dict:
    focus = state.get("focus_areas", [])
    idx = state.get("focus_index", 0)
    competency_id = focus[idx] if idx < len(focus) else None

    reply = interrupt(
        {
            "type": "coach_prompt",
            "competency_id": competency_id,
            "focus_index": idx,
            "remaining": max(0, len(focus) - idx - 1),
        }
    )
    reply = (reply or "").strip() if isinstance(reply, str) else str(reply)

    # v1: acknowledge and advance to the next focus area. Interpreting "tell me
    # more" to stay on the same area is a small Phase-2 refinement.
    return {
        "focus_index": idx + 1,
        "messages": [{"role": "user", "content": reply}],
    }
