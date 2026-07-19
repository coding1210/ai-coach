"""Turn an evaluation into a personalized coaching roadmap.

Coaching, not teaching: the roadmap is built from *this* person's weak spots
(priority-ordered from the report), not a fixed syllabus. Each milestone names
where they are, the next rung to aim for, what "good" looks like at that rung
(the rubric anchor), and how they'll know they've arrived.

Structure is deterministic — derived from the report + rubric so it never lies
about levels or gaps. A single LLM pass enriches each milestone with concrete,
evidence-specific practice steps; if that call is unavailable or malformed the
templated fallback still stands on its own (same contract as build_report).
"""

from __future__ import annotations

import logging

from app.coaching.resources import resources_for
from app.eval.exercises import get_exercise_bank
from app.llm.router import get_router

log = logging.getLogger(__name__)

_MAX_MILESTONES = 4


def _level_name(cmap, level: int) -> str:
    for p in cmap.proficiency_levels:
        if p.level == level:
            return p.name
    return f"Level {level}"


def _target_anchor(anchors: dict[str, str], current: int, target: int) -> tuple[int, str]:
    """The rubric description of what *good* looks like — the aspirational rung.

    Anchors are sparse (often just a weak L2 and a strong L4 pole), so for a
    growth target we want the HIGHEST anchor above the current level (the
    proficient/expert description), not the next rung up which may itself
    describe weak behavior. Falls back to the highest anchor, then to no text.
    Returns (level, text)."""
    keyed = sorted((int(k), v) for k, v in (anchors or {}).items())
    if not keyed:
        return target, ""
    above = [(lvl, txt) for lvl, txt in keyed if lvl > current]
    if above:
        return above[-1]  # highest aspirational rung
    return keyed[-1]


def _horizon(total_gap: int) -> str:
    if total_gap <= 2:
        return "the next couple of weeks"
    if total_gap <= 5:
        return "the next month or so"
    return "the next couple of months"


def build_roadmap(report: dict, cmap) -> dict:
    """Deterministic skeleton: one milestone per top weak spot, priority-ordered."""
    weaknesses = report.get("weaknesses", [])[:_MAX_MILESTONES]
    bank = get_exercise_bank()
    milestones: list[dict] = []

    for rank, w in enumerate(weaknesses, start=1):
        cid = w["competency_id"]
        name = w["competency_name"]
        current = w["current_level"]
        target = w["target_level"]
        domain = cmap.domain_of(cid)
        has_exercise = bank.by_competency(cid) is not None
        anchor_level, anchor_text = _target_anchor(
            cmap.competency(cid).level_anchors, current, target
        )

        why = (
            f"{domain.name} is a {domain.weight}-weight area for your target, and this is "
            + ("your biggest gap right now." if rank == 1 else f"gap #{rank} on your list.")
        )
        focus = anchor_text or f"operating at {_level_name(cmap, target)} level on {name}."
        first = (
            f"Take the graded {name} challenge below and iterate until it passes."
            if has_exercise
            else f"Build a small artifact that forces {name} — then explain the trade-offs you made."
        )
        practice = [
            first,
            f"Read a strong reference implementation of {name} and note what it does that yours doesn't.",
        ]
        signal = (
            f"You can show {_level_name(cmap, target)} judgement on {name}: {focus}"
            if focus
            else f"You consistently operate at {_level_name(cmap, target)} on {name}."
        )

        milestones.append(
            {
                "rank": rank,
                "competency_id": cid,
                "competency_name": name,
                "domain_name": domain.name,
                "domain_weight": domain.weight,
                "from_level": current,
                "from_level_name": _level_name(cmap, current),
                "target_level": target,
                "target_level_name": _level_name(cmap, target),
                "focus": focus,
                "why": why,
                "practice": practice,
                "signal": signal,
                "has_exercise": has_exercise,
                "resources": resources_for(cid),
            }
        )

    total_gap = sum(w.get("gap", 0) for w in weaknesses)
    return {
        "horizon": _horizon(total_gap),
        "milestones": milestones,
    }


_ENRICH_SCHEMA = {
    "type": "object",
    "properties": {
        "milestones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "competency_id": {"type": "string"},
                    "practice": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "maxItems": 3,
                    },
                    "signal": {"type": "string"},
                },
                "required": ["competency_id", "practice", "signal"],
            },
        }
    },
    "required": ["milestones"],
}


def _coerce_entries(out: dict) -> list[dict]:
    """Pull a list of {competency_id, practice, signal} out of whatever JSON shape
    the model returned — a {milestones:[...]} wrapper, a bare list, or (when there's
    a single milestone) a flat object."""
    if not isinstance(out, dict):
        return []
    for key in ("milestones", "items", "results", "plan"):
        val = out.get(key)
        if isinstance(val, list):
            return [e for e in val if isinstance(e, dict)]
    # Flat single-milestone object.
    if "competency_id" in out:
        return [out]
    return []


def _as_list(practice) -> list[str]:
    if isinstance(practice, list):
        return [p.strip() for p in practice if isinstance(p, str) and p.strip()]
    if isinstance(practice, str) and practice.strip():
        return [practice.strip()]
    return []


async def enrich_roadmap(roadmap: dict, profile: dict, role_title: str = "") -> dict:
    """Overlay concrete, person-specific practice steps + success signals via the
    coach model. Any failure leaves the deterministic templates untouched."""
    milestones = roadmap.get("milestones", [])
    if not milestones:
        return roadmap

    brief = [
        {
            "competency_id": m["competency_id"],
            "name": m["competency_name"],
            "from": f"L{m['from_level']} ({m['from_level_name']})",
            "target": f"L{m['target_level']} ({m['target_level_name']})",
            "what_good_looks_like": m["focus"],
        }
        for m in milestones
    ]
    role_line = f" They're aiming for a {role_title} role." if role_title else ""
    background = (profile or {}).get("background", "")
    ids = ", ".join(m["competency_id"] for m in milestones)
    prompt = (
        "You are a coach building a growth plan for a Gen AI engineer."
        + role_line
        + (f" Background: {background}." if background else "")
        + " For EACH competency below, write 2-3 CONCRETE, specific practice actions that move "
        "them toward the target — real things to build, read, or measure (never vague advice like "
        '"study more"). Then one observable success signal completing "You\'ll know you\'re there '
        'when...". Ground each in what the target level looks like.\n\n'
        f"Competencies (JSON): {brief}\n\n"
        "Respond with JSON in EXACTLY this shape, one entry per competency, echoing the "
        f"competency_id verbatim (ids: {ids}):\n"
        '{"milestones": [{"competency_id": "<id>", '
        '"practice": ["action 1", "action 2"], "signal": "You\'ll know you\'re there when ..."}]}'
    )
    try:
        out = await get_router().complete_json(
            "coach",
            [{"role": "user", "content": prompt}],
            schema=_ENRICH_SCHEMA,
            temperature=0.3,
        )
    except Exception as e:  # noqa: BLE001 — enrichment is best-effort
        log.warning("Roadmap enrichment failed, keeping templates: %s", e)
        return roadmap

    entries = _coerce_entries(out)
    by_id = {e.get("competency_id"): e for e in entries}
    # If ids didn't come back but the counts line up, zip positionally.
    matched = 0
    for i, m in enumerate(milestones):
        e = by_id.get(m["competency_id"]) or (
            entries[i] if len(entries) == len(milestones) else None
        )
        if not e:
            continue
        practice = _as_list(e.get("practice"))
        signal = e.get("signal")
        if practice:
            m["practice"] = practice[:3]
            matched += 1
        if isinstance(signal, str) and signal.strip():
            m["signal"] = signal.strip()

    if not matched:
        log.warning("Roadmap enrichment returned no usable entries; keeping templates")
    return roadmap
