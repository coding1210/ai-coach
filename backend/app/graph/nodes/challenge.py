"""challenge — a graded, hands-on exercise inside the coaching loop.

For a focus competency that has an exercise, after the coach teaches it we set a
concrete coding task and grade the SUBMITTED CODE (behavioral evidence), then
supersede that competency's self-report score with the demonstrated one so the
ledger reflects doing, not describing.

  challenge        → present the exercise. No interrupt.
  challenge_await  → interrupt for the code submission, grade it, give feedback,
                     advance the focus cursor. Grading runs only on resume.
"""

from __future__ import annotations

from langgraph.types import interrupt

from app.eval.exercises import get_exercise_bank
from app.graph.state import CoachState
from app.graph.streaming import emit
from app.llm.grader import grade_submission


async def challenge(state: CoachState) -> dict:
    focus = state.get("focus_areas", [])
    idx = state.get("focus_index", 0)
    if idx >= len(focus):
        return {}
    ex = get_exercise_bank().by_competency(focus[idx])
    if ex is None:  # routing guards this
        return {}

    intro = (
        f"Now let's make it real — a hands-on challenge for {ex.title}:\n\n"
        f"{ex.prompt}\n\n"
        f"Reply with your {ex.language} code and I'll grade what it actually does."
    )
    emit({"type": "assistant_message", "content": intro})
    emit(
        {
            "type": "exercise",
            "competency_id": ex.competency_id,
            "title": ex.title,
            "language": ex.language,
            "prompt": ex.prompt,
        }
    )
    return {"messages": [{"role": "assistant", "content": intro}]}


async def challenge_await(state: CoachState) -> dict:
    focus = state.get("focus_areas", [])
    idx = state.get("focus_index", 0)
    comp_id = focus[idx] if idx < len(focus) else None

    submission = interrupt({"type": "awaiting_submission", "competency_id": comp_id})
    submission = submission if isinstance(submission, str) else str(submission)

    ex = get_exercise_bank().by_competency(comp_id) if comp_id else None
    if ex is None:
        return {"focus_index": idx + 1}

    result = await grade_submission(ex, submission)
    passed = sum(1 for c in result["checks"] if c["passed"])
    prior = (state.get("scores") or {}).get(comp_id, {}).get("level")
    delta_note = ""
    if prior is not None:
        verb = "confirmed" if result["level"] >= prior else "adjusted down"
        delta_note = (
            f" You described this at L{prior}; you demonstrated L{result['level']} — {verb}."
        )
    # Short spoken line; the rich detail (checks + evidence) rides the grade card.
    feedback = (
        f"Graded L{result['level']}/5 on {ex.title} — "
        f"{passed}/{len(result['checks'])} objective checks passed.{delta_note}"
    )

    emit(
        {
            "type": "grade",
            "competency_id": comp_id,
            "level": result["level"],
            "deterministic_score": result["deterministic_score"],
            "checks": result["checks"],
            "evidence": result["evidence"],
        }
    )
    emit({"type": "assistant_message", "content": feedback})

    # Behavioral score supersedes the self-report for this competency.
    scores = dict(state.get("scores") or {})
    scores[comp_id] = {
        "competency_id": comp_id,
        "level": result["level"],
        "evidence": "[behavioral] " + result["evidence"],
        "confidence": result["confidence"],
    }
    return {
        "scores": scores,
        "focus_index": idx + 1,
        "messages": [
            {"role": "user", "content": submission},
            {"role": "assistant", "content": feedback},
        ],
    }
