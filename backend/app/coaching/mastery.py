"""Mastery — turn graded reps into an honest, evidence-weighted signal of skill.

A competency is only "held" after clearing several reps at its target level. The
level a competency shows is driven by *demonstrated* reps (with confidence that
rises with reps and with the rigor of the rep type), not by one conversational
answer. Each graded attempt also writes through to the ledger so the report and
progress reflect real practice.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.coaching.scheduler import interval_days
from app.competency.loader import get_competency_map
from app.competency.selection import target_for

MASTERY_CLEARS = 2  # spaced clears at the target level to count as "held"

_TYPE_CONFIDENCE = {"code": 0.2, "critique": 0.15, "design": 0.12, "explain": 0.08}


def competency_target(competency_id: str, jd_targets: dict | None = None) -> int:
    return target_for(get_competency_map(), competency_id, jd_targets)


def _confidence(reps_cleared: int, rep_type: str) -> float:
    base = 0.4 + 0.18 * reps_cleared + _TYPE_CONFIDENCE.get(rep_type, 0.1)
    return round(min(1.0, base), 3)


async def update_mastery(
    repo, user_id: str, rep, grade: dict, hints_used: int, now: datetime | None = None
) -> dict:
    """Record the attempt, update mastery, write through to the ledger, and decide
    what to serve next. Returns a summary for the client."""
    now = now or datetime.now(timezone.utc)
    cid = rep.competency_id
    target = competency_target(cid)
    level = int(grade.get("level", 1))
    passed = bool(grade.get("passed"))

    attempt_no = await repo.add_rep_attempt(
        user_id,
        {
            "competency_id": cid, "rep_id": rep.id, "type": rep.type,
            "target_level": rep.target_level, "level_awarded": level, "passed": passed,
            "confidence": float(grade.get("confidence", 0.0)), "hints_used": hints_used,
            "created_at": now.isoformat(),
        },
    )

    m = await repo.get_mastery(user_id, cid) or {
        "competency_id": cid, "level": 0, "confidence": 0.0,
        "reps_cleared_at_target": 0, "status": "unseen",
    }
    demonstrated = max(int(m.get("level") or 0), level)

    # Count a clear at the competency's TARGET level toward mastery.
    cleared_at_target = int(m.get("reps_cleared_at_target") or 0)
    if passed and rep.target_level >= target:
        cleared_at_target += 1

    held = cleared_at_target >= MASTERY_CLEARS
    status = "held" if held else "practicing"
    confidence = _confidence(cleared_at_target, rep.type) if demonstrated >= target else round(
        min(0.75, 0.35 + 0.1 * attempt_no), 3
    )

    # Spaced next review after a clear; sooner if still working.
    days = interval_days(demonstrated, target) if passed else 1
    next_due = (now + timedelta(days=days)).isoformat()

    new_m = {
        "competency_id": cid, "level": demonstrated, "confidence": confidence,
        "reps_cleared_at_target": cleared_at_target, "status": status,
        "last_practiced_at": now.isoformat(), "next_rep_due_at": next_due,
    }
    await repo.upsert_mastery(user_id, cid, new_m)

    # Write through to the ledger — practice is demonstrated evidence.
    await repo.upsert_ledger_entry(user_id, cid, current_level=demonstrated, target_level=target)
    await repo.set_next_review(user_id, cid, next_due)

    # Decide what to serve next.
    scaffolded = False
    if held:
        next_level = None  # move on to another competency
    elif not passed and hints_used >= 2 and rep.target_level > 1:
        next_level = rep.target_level - 1  # struggling → scaffold down
        scaffolded = True
    elif not passed:
        next_level = rep.target_level  # revise at the same rung
    elif rep.target_level < target:
        next_level = rep.target_level + 1  # cleared → step up the ladder
    else:
        next_level = target  # cleared at target but not yet held → another at target

    return {
        "attempt_no": attempt_no,
        "mastery": new_m,
        "held": held,
        "target_level": target,
        "next_level": next_level,
        "scaffolded": scaffolded,
        "reps_cleared_at_target": cleared_at_target,
    }
