"""A/B test two coach-persona variants on the same scenarios.

Generates a reply from each variant for every scenario, then a blind pairwise
meta-judge (order randomized per item to control position bias) picks the better
reply. Reports a win rate so a prompt change is decided by evidence, not vibes.

    uv run python scripts/ab_prompt.py

Edit VARIANT_A / VARIANT_B to compare a proposed persona against the current one.
Needs a real provider (OPENAI/GROQ) to be meaningful.
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm.persona import COACH_PERSONA  # noqa: E402
from app.llm.router import get_router  # noqa: E402
from scripts.coach_meta_eval import SCENARIOS  # noqa: E402

VARIANT_A = ("A (current)", COACH_PERSONA)
VARIANT_B = (
    "B (more Socratic)",
    COACH_PERSONA + "\nBias hard toward ONE probing question; never give the answer outright.",
)

PICK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"winner": {"type": "string", "enum": ["first", "second", "tie"]}, "why": {"type": "string"}},
    "required": ["winner", "why"],
}


async def _reply(persona: str, user_msg: str) -> str:
    return await get_router().complete(
        "coach",
        [{"role": "system", "content": persona}, {"role": "user", "content": user_msg}],
        temperature=0.5,
        max_tokens=300,
    )


async def _pick(user_msg: str, first: str, second: str) -> str:
    sys_msg = (
        "You compare two COACH replies to the same learner. The better coach guides with questions, "
        "is on-target, safe, and warmly calibrated. Pick 'first' or 'second' (or 'tie'). JSON only."
    )
    user = f"LEARNER:\n{user_msg}\n\nREPLY 1:\n{first}\n\nREPLY 2:\n{second}\n\nReturn {{winner, why}}."
    out = await get_router().complete_json(
        "score", [{"role": "system", "content": sys_msg}, {"role": "user", "content": user}], schema=PICK_SCHEMA
    )
    return out.get("winner", "tie")


async def main() -> int:
    wins = {VARIANT_A[0]: 0, VARIANT_B[0]: 0, "tie": 0}
    for i, sc in enumerate(SCENARIOS):
        a = await _reply(VARIANT_A[1], sc["user"])
        b = await _reply(VARIANT_B[1], sc["user"])
        # Randomize presentation order by index parity to blunt position bias.
        swap = i % 2 == 1
        first, second = (b, a) if swap else (a, b)
        pick = await _pick(sc["user"], first, second)
        if pick == "tie":
            winner = "tie"
        else:
            picked_first = pick == "first"
            winner = (VARIANT_B[0] if swap else VARIANT_A[0]) if picked_first else (VARIANT_A[0] if swap else VARIANT_B[0])
        wins[winner] += 1
        print(f"  [{sc['id']:9}] winner: {winner}")

    print("\n  tally:", wins)
    a_w, b_w = wins[VARIANT_A[0]], wins[VARIANT_B[0]]
    verdict = VARIANT_A[0] if a_w > b_w else VARIANT_B[0] if b_w > a_w else "tie"
    print(f"  → {verdict} wins" if verdict != "tie" else "  → no clear winner")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
