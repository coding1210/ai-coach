"""assess — a listening, adaptive assessment turn (Reality phase of GROW).

  assess_ask    → reflect on what they just said (one genuine line), then ask ONE
                  open question probing the next competency — generated live so it
                  responds to them, not a canned script. Streams. No interrupt.
  assess_await  → collect the answer (or the finish sentinel). Nothing expensive
                  before the interrupt, so resume is idempotent.

The competency it targets is chosen by breadth-first weight (baseline) or the
prior-gap worklist (reassess); the LLM just phrases the reflection + question.
"""

from __future__ import annotations

from langgraph.types import interrupt

from app.competency.loader import get_competency_map
from app.competency.selection import next_competency, reassess_targets
from app.graph.state import FINISH_ASSESSMENT, CoachState
from app.graph.streaming import emit_streamed_text
from app.llm.persona import COACH_PERSONA
from app.llm.providers import Message


def _last_answer(state: CoachState) -> str | None:
    for m in reversed(state.get("messages", [])):
        if m.get("role") == "user":
            return m["content"]
    return None


async def assess_ask(state: CoachState) -> dict:
    cmap = get_competency_map()
    asked = state.get("asked", [])

    if state.get("mode") == "reassess":
        remaining = [c for c in reassess_targets(cmap, state.get("prior_levels", {})) if c not in asked]
        competency = cmap.competency(remaining[0]) if remaining else None
    else:
        # Confidence-driven: bias toward weak/uncertain domains via prior scores.
        competency = next_competency(cmap, asked, state.get("scores", {}))

    if competency is None:  # routing guards this
        return {"phase": "report"}

    last = _last_answer(state)
    if last:
        task = (
            f'They just said: "{last}"\n\n'
            "In ONE short line, reflect back something specific and genuine about that answer "
            "(acknowledge what's sharp, or gently note what's thin — no scoring, no praise-padding). "
            f"Then ask ONE open question that probes: {competency.name}. "
            f"Use this as the intent to probe (rephrase it naturally, adapt to what they just told you): "
            f'"{competency.sample_question}". Keep the whole turn to 2-3 sentences.'
        )
    else:
        profile = state.get("profile") or {}
        task = (
            f"Open the session warmly in one short line (they're {profile.get('background', 'an engineer')} "
            f"aiming to {profile.get('goal', 'grow in Gen AI')}). Then ask ONE open question probing "
            f'{competency.name}, based on: "{competency.sample_question}". 1-2 sentences.'
        )

    messages: list[Message] = [
        {"role": "system", "content": COACH_PERSONA},
        {"role": "user", "content": task},
    ]
    content = await emit_streamed_text("turn", messages, temperature=0.5, max_tokens=200)

    return {
        "phase": "assess",
        "asked": [competency.id],
        "current_competency_id": competency.id,
        "current_question": content,
        "messages": [{"role": "assistant", "content": content}],
    }


async def assess_await(state: CoachState) -> dict:
    answer = interrupt(
        {"type": "awaiting_answer", "competency_id": state.get("current_competency_id")}
    )
    answer = (answer or "").strip() if isinstance(answer, str) else str(answer)
    if answer == FINISH_ASSESSMENT:
        return {"stop_requested": True}
    return {"messages": [{"role": "user", "content": answer}]}
