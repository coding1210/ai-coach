"""Behavioral grading — score a SUBMITTED ARTIFACT, not a self-report.

Two signals combined:
  1. Objective `checks` — regexes over the submission (does the code actually
     use a Semaphore? validate output? isolate untrusted content?). Deterministic,
     keyless, testable.
  2. A code-reading rubric judge (GPT) that reads the real submission and the
     check results and scores against the exercise rubric.

The objective score *caps* the judged level, so a confident-but-wrong submission
can't be talked up to Proficient when the required properties are absent — the
core fix for "measures describing, not doing".
"""

from __future__ import annotations

import re
from typing import Any

from app.eval.exercises import Exercise
from app.llm.judge import JUDGE_SCHEMA
from app.llm.providers import Message
from app.llm.router import get_router


def _strip_comments(text: str) -> str:
    """Drop `#` line comments so keywords *described* in comments don't count as
    *done* in code. (String literals are kept — some techniques live there.)"""
    return re.sub(r"#.*", "", text)


def run_checks(exercise: Exercise, submission: str) -> tuple[list[dict], float]:
    """Return (per-check results, weighted pass ratio 0..1)."""
    code = _strip_comments(submission)
    results: list[dict] = []
    total = passed = 0
    for c in exercise.checks:
        match = re.search(c.pattern, code, re.IGNORECASE) is not None
        ok = (not match) if c.kind == "absent" else match
        results.append({"id": c.id, "description": c.description, "passed": ok})
        total += c.weight
        if ok:
            passed += c.weight
    return results, (passed / total if total else 0.0)


def _cap_for(score: float) -> int:
    """Objective ceiling: you can't be Proficient at a task whose required
    properties your code lacks."""
    if score < 0.34:
        return 2
    if score < 0.67:
        return 3
    return 5


def _judge_messages(exercise: Exercise, submission: str, checks: list[dict]) -> list[Message]:
    check_lines = "\n".join(
        f"  [{'x' if c['passed'] else ' '}] {c['description']}" for c in checks
    )
    system = (
        "You are grading a Gen AI engineer's CODE SUBMISSION for one competency on a "
        "1-5 Dreyfus scale. Score the code that is actually present — not how it's "
        "described. Weight the objective checks heavily: missing required properties "
        "must lower the score. Evidence must reference specific lines/constructs in the "
        "submission. Return JSON only."
    )
    user = (
        f"TASK: {exercise.prompt}\n\n"
        f"RUBRIC: {exercise.rubric}\n\n"
        f"OBJECTIVE CHECKS (auto-detected in the code):\n{check_lines}\n\n"
        f"SUBMISSION:\n```{exercise.language}\n{submission or '(empty)'}\n```\n\n"
        "Return {level, evidence, confidence}."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


async def grade_submission(exercise: Exercise, submission: str) -> dict[str, Any]:
    """Return {competency_id, level, evidence, confidence, checks, deterministic_score}."""
    checks, det_score = run_checks(exercise, submission)

    raw = await get_router().complete_json(
        "score", _judge_messages(exercise, submission, checks), schema=JUDGE_SCHEMA, temperature=0.0
    )

    judged = max(1, min(5, int(raw.get("level", 3))))
    cap = _cap_for(det_score)
    level = min(judged, cap)

    evidence = str(raw.get("evidence", "")).strip()
    if level < judged:
        missing = ", ".join(c["description"] for c in checks if not c["passed"])
        evidence = (
            f"{evidence} [Capped at L{level}: objective checks failed — missing {missing}.]"
        )

    return {
        "competency_id": exercise.competency_id,
        "level": level,
        "evidence": evidence,
        "confidence": max(0.0, min(1.0, float(raw.get("confidence", 0.5)))),
        "checks": checks,
        "deterministic_score": round(det_score, 2),
    }
