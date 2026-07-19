"""Graduated hints — unblock with the minimum, never hand over the answer.

Three tiers, revealed one at a time on request:
  1 nudge          — point at what's missing without naming it
  2 targeted       — name the concept and roughly where it belongs
  3 worked fragment— a partial example, only after real attempts

Best-effort via the coach model; falls back to a tier-appropriate template so
hints work offline/degraded.
"""

from __future__ import annotations

import logging

from app.llm.persona import COACH_PERSONA
from app.llm.router import get_router

log = logging.getLogger(__name__)

_TIER_BRIEF = {
    1: "Give a NUDGE: one question or observation that points at what's missing, "
    "without naming the concept or giving any of the answer. One sentence.",
    2: "Give a TARGETED hint: name the specific concept they're missing and roughly "
    "where it belongs, but do not write the solution. Two sentences max.",
    3: "Give a WORKED FRAGMENT: a small partial example or the shape of the answer for "
    "the weakest part only — never the whole solution. Keep it short.",
}

_TIER_FALLBACK = {
    1: "What happens at the edges — the case you haven't accounted for yet?",
    2: "There's a specific technique this calls for; think about what a proficient answer "
    "would name here, and where it fits.",
    3: "Sketch the smallest version of the missing piece first, then build outward from it.",
}


async def hint(rep, submission: str, tier: int) -> str:
    """Return a tier-appropriate hint for the current attempt."""
    tier = max(1, min(3, int(tier)))
    task = (
        "A learner is working a practice task and asked for help. Coach them — do NOT reveal "
        "the full answer.\n"
        f"TASK: {rep.prompt}\n"
        + (f"ARTIFACT: {rep.given_artifact}\n" if rep.given_artifact else "")
        + f"THEIR ATTEMPT SO FAR:\n{submission or '(nothing yet)'}\n\n"
        f"{_TIER_BRIEF[tier]}"
    )
    try:
        out = await get_router().complete(
            "coach",
            [{"role": "system", "content": COACH_PERSONA}, {"role": "user", "content": task}],
            temperature=0.4, max_tokens=160,
        )
        text = (out or "").strip()
        # Guard against the fake provider echoing the prompt back.
        if text and not text.lower().startswith("[fake-llm]"):
            return text
    except Exception as e:  # noqa: BLE001
        log.warning("hint generation failed: %s", e)
    return _TIER_FALLBACK[tier]
