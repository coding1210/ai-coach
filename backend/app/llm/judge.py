"""LLM-as-a-judge scoring (Design.md §6, competency_map.json "scoring").

Rubric-grounded and bias-controlled: the judge scores a user's answer against a
single competency's L1–L5 anchors, returns structured JSON, and must cite the
user's own words as evidence. Bias controls (verbosity / self-preference /
position) are injected from the competency map so the rubric stays the source of
truth.
"""

from __future__ import annotations

from typing import Any

from app.competency.loader import Competency, get_competency_map
from app.llm.providers import Message
from app.llm.router import get_router

# JSON schema the judge must satisfy (matches CompetencyScore, minus the id).
JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "level": {"type": "integer", "minimum": 1, "maximum": 5},
        "evidence": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["level", "evidence", "confidence"],
}


def _anchor_block(competency: Competency, levels: list[dict]) -> str:
    lines = []
    for lvl in levels:
        n = str(lvl["level"])
        anchor = competency.level_anchors.get(n)
        general = lvl["meaning"]
        lines.append(f"  L{n} ({lvl['name']}): {anchor or general}")
    return "\n".join(lines)


def build_judge_messages(
    competency: Competency, question: str, answer: str
) -> list[Message]:
    cmap = get_competency_map()
    bias = "; ".join(cmap.scoring.bias_controls)
    anchors = _anchor_block(competency, [lvl.model_dump() for lvl in cmap.proficiency_levels])
    system = (
        "You are a rigorous but fair technical assessor scoring one competency of a "
        "Gen AI engineer on a 1–5 Dreyfus scale. Score ONLY against the level anchors "
        "below — do not invent criteria.\n"
        f"Bias controls (enforce strictly): {bias}.\n"
        "Evidence MUST quote or closely paraphrase the candidate's own answer. If the "
        "answer is empty or evasive, score low with low confidence. Return JSON only."
    )
    user = (
        f"COMPETENCY: {competency.name} ({competency.id})\n\n"
        f"LEVEL ANCHORS:\n{anchors}\n\n"
        f"QUESTION ASKED:\n{question}\n\n"
        f"CANDIDATE ANSWER:\n{answer or '(no answer given)'}\n\n"
        "Return {level, evidence, confidence}."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


async def score_answer(
    competency: Competency, question: str, answer: str
) -> dict[str, Any]:
    """Return a CompetencyScore-shaped dict: {competency_id, level, evidence, confidence}."""
    messages = build_judge_messages(competency, question, answer)
    raw = await get_router().complete_json("score", messages, schema=JUDGE_SCHEMA, temperature=0.0)

    level = int(raw.get("level", 3))
    level = max(1, min(5, level))
    confidence = float(raw.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))
    return {
        "competency_id": competency.id,
        "level": level,
        "evidence": str(raw.get("evidence", "")).strip(),
        "confidence": confidence,
    }
