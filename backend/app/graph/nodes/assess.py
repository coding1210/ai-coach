"""assess — split into two nodes so interrupt-resume never re-runs work and the
question flows to the user as a normal message (Design.md §5).

  assess_ask    → pick the highest-weight unprobed competency, commit its
                  question to `messages`, mark it asked. No interrupt.
  assess_await  → interrupt for the user's answer, commit it. Nothing expensive
                  runs before the interrupt, so resume is idempotent.

v1 uses the competency map's seed question verbatim (deterministic). Adaptive
LLM-generated follow-ups are a deliberate Phase-2 extension of `assess_ask`.
"""

from __future__ import annotations

from langgraph.types import interrupt

from app.competency.loader import get_competency_map
from app.competency.selection import next_competency, reassess_targets
from app.graph.state import CoachState
from app.graph.streaming import emit


async def assess_ask(state: CoachState) -> dict:
    cmap = get_competency_map()
    asked = state.get("asked", [])

    if state.get("mode") == "reassess":
        # Re-probe prior weak areas in priority order, one at a time.
        remaining = [c for c in reassess_targets(cmap, state.get("prior_levels", {})) if c not in asked]
        competency = cmap.competency(remaining[0]) if remaining else None
    else:
        competency = next_competency(cmap, asked)

    if competency is None:  # routing guards this; belt-and-braces
        return {"phase": "report"}

    emit({"type": "assistant_message", "content": competency.sample_question})
    return {
        "phase": "assess",
        "asked": [competency.id],
        "current_competency_id": competency.id,
        "current_question": competency.sample_question,
        "messages": [{"role": "assistant", "content": competency.sample_question}],
    }


async def assess_await(state: CoachState) -> dict:
    answer = interrupt(
        {
            "type": "awaiting_answer",
            "competency_id": state.get("current_competency_id"),
        }
    )
    answer = (answer or "").strip() if isinstance(answer, str) else str(answer)
    return {"messages": [{"role": "user", "content": answer}]}
