"""Mock-interview mode — the coach becomes a technical interviewer.

  interview_ask     → ask a realistic, role-tailored question, probing deeper on
                      the previous answer like a real interviewer. Streams.
  interview_await   → collect the answer (shared triage handles safety).
  interview_debrief → an honest hiring-style debrief + verdict, plus the same
                      evaluation report/radar for the panel.

Answers are scored by the shared `score` node; routing loops until
INTERVIEW_QUESTIONS is reached, then debriefs.
"""

from __future__ import annotations

from langgraph.types import interrupt

from app.competency.loader import get_competency_map
from app.competency.selection import next_competency
from app.graph.nodes.report import build_report
from app.graph.state import FINISH_ASSESSMENT, CoachState
from app.graph.streaming import emit, emit_streamed_text
from app.llm.persona import INTERVIEWER_PERSONA
from app.llm.providers import Message


async def interview_ask(state: CoachState) -> dict:
    cmap = get_competency_map()
    competency = next_competency(cmap, state.get("asked", []), state.get("scores", {}))
    if competency is None:
        return {"phase": "interview"}

    role = state.get("role_title") or "a senior Gen AI engineer"
    count = state.get("iv_count", 0)
    last = next((m["content"] for m in reversed(state.get("messages", [])) if m["role"] == "user"), None)

    if count == 0 or not last:
        task = (
            f"Open the interview for the {role} role in one line, then ask your FIRST question "
            f"probing {competency.name} — realistic, scenario-based, senior-level, based on: "
            f'"{competency.sample_question}". Do not coach or explain. 2-3 sentences.'
        )
    else:
        task = (
            f'Their last answer: "{last}"\n\n'
            "React like an interviewer in one short clause (neutral — a quick follow-up or 'got it'), "
            f"then ask your next question probing {competency.name}, based on: "
            f'"{competency.sample_question}". Do NOT teach or give the answer. 2-3 sentences.'
        )

    messages: list[Message] = [
        {"role": "system", "content": INTERVIEWER_PERSONA},
        {"role": "user", "content": task},
    ]
    content = await emit_streamed_text("coach", messages, temperature=0.6, max_tokens=220)
    return {
        "phase": "interview",
        "asked": [competency.id],
        "current_competency_id": competency.id,
        "current_question": content,
        "iv_count": count + 1,
        "messages": [{"role": "assistant", "content": content}],
    }


async def interview_await(state: CoachState) -> dict:
    answer = interrupt(
        {"type": "interview_answer", "competency_id": state.get("current_competency_id")}
    )
    answer = (answer or "").strip() if isinstance(answer, str) else str(answer)
    if answer == FINISH_ASSESSMENT:
        return {"stop_requested": True}
    return {"messages": [{"role": "user", "content": answer}]}


def _verdict(scores: dict) -> str:
    levels = [s["level"] for s in scores.values()]
    avg = sum(levels) / len(levels) if levels else 0
    if avg >= 4:
        return "Strong hire"
    if avg >= 3.3:
        return "Lean hire"
    if avg >= 2.5:
        return "Borderline"
    return "Not yet"


async def interview_debrief(state: CoachState) -> dict:
    cmap = get_competency_map()
    scores = state.get("scores", {})
    built = build_report(scores, cmap, jd_targets=state.get("jd_targets") or {})
    verdict = _verdict(scores)
    built["role_title"] = state.get("role_title", "")
    built["verdict"] = verdict
    built["interview"] = True
    emit({"type": "report", "data": built})

    role = state.get("role_title") or "a senior Gen AI engineer"
    strong = ", ".join(s["competency_name"] for s in built["strengths"][:3]) or "not much stood out"
    concerns = ", ".join(w["competency_name"] for w in built["weaknesses"][:3]) or "no major concerns"
    task = (
        f"You just finished interviewing a candidate for {role}. Overall read: {verdict}. "
        f"What stood out: {strong}. Concerns: {concerns}. Give a short, honest interviewer DEBRIEF "
        "(3-4 sentences): your impression, what impressed you, the biggest concern, and whether "
        "you'd advance them. Direct and professional — this is feedback, so you can be constructive."
    )
    narrative = await emit_streamed_text(
        "report",
        [{"role": "system", "content": INTERVIEWER_PERSONA}, {"role": "user", "content": task}],
        temperature=0.4,
        max_tokens=400,
    )
    return {
        "phase": "done",
        "report": built,
        "verdict": verdict,
        "messages": [{"role": "assistant", "content": narrative}],
    }
