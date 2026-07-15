"""score — LLM-as-judge scores the just-answered competency, then recompute
weighted coverage (Design.md §6).

Merges the new score into the scores map (default channel overwrite → return the
full merged dict) and stores the audit-worthy evidence for persistence.
"""

from __future__ import annotations

from app.competency.loader import get_competency_map
from app.competency.selection import weighted_coverage
from app.graph.state import CoachState
from app.llm.judge import score_answer


async def score(state: CoachState) -> dict:
    if state.get("stop_requested"):
        return {}  # user ended assessment early; nothing to score
    cmap = get_competency_map()
    competency_id = state.get("current_competency_id")
    if not competency_id:
        return {}

    competency = cmap.competency(competency_id)
    question = state.get("current_question") or competency.sample_question

    # The user's answer is the last user message.
    answer = ""
    for m in reversed(state.get("messages", [])):
        if m["role"] == "user":
            answer = m["content"]
            break

    judgement = await score_answer(competency, question, answer)

    scores = dict(state.get("scores", {}))
    scores[competency_id] = {
        "competency_id": competency_id,
        "level": judgement["level"],
        "evidence": judgement["evidence"],
        "confidence": judgement["confidence"],
    }

    coverage = weighted_coverage(cmap, state.get("asked", []))
    return {"scores": scores, "coverage": coverage}
