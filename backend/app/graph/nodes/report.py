"""report — synthesize scores into an evaluation report (Design.md §7).

Structured data (strengths / weaknesses / per-domain radar / priorities) is
computed deterministically from the scores + rubric. In re-assessment mode the
prior levels are carried in for competencies not re-probed, so the radar shows
the full current standing, and each re-scored competency gets a delta vs. last
time (the visible "status promotion"). A short conversational narrative is
generated on top (GPT via the `report` task) — the numbers never depend on it.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

from app.coaching.benchmark import benchmark_report
from app.coaching.roadmap import build_roadmap, enrich_roadmap
from app.competency.loader import get_competency_map
from app.competency.selection import target_for
from app.graph.state import CoachState
from app.graph.streaming import emit, emit_streamed_text
from app.llm.persona import COACH_PERSONA
from app.llm.providers import Message


def build_report(
    scores: dict, cmap, prior_levels: dict[str, int] | None = None, jd_targets: dict | None = None
) -> dict:
    prior_levels = prior_levels or {}
    strengths: list[dict] = []
    weaknesses: list[dict] = []
    domain_agg: dict[str, dict] = defaultdict(
        lambda: {"cur": [], "tgt": [], "name": "", "weight": ""}
    )

    scored = []
    for cid, s in scores.items():
        domain = cmap.domain_of(cid)
        target = target_for(cmap, cid, jd_targets)
        gap = max(0, target - s["level"])
        priority = gap * cmap.weight_scale[domain.weight]
        prev = prior_levels.get(cid)
        entry = {
            "competency_id": cid,
            "competency_name": cmap.competency(cid).name,
            "domain_id": domain.id,
            "current_level": s["level"],
            "target_level": target,
            "gap": gap,
            "priority": priority,
            "evidence": s["evidence"],
            "previous_level": prev,
            "delta": (s["level"] - prev) if prev is not None else None,
        }
        scored.append(entry)
        (strengths if gap == 0 else weaknesses).append(entry)

        agg = domain_agg[domain.id]
        agg["name"] = domain.name
        agg["weight"] = domain.weight
        agg["cur"].append(s["level"])
        agg["tgt"].append(target)

    weaknesses.sort(key=lambda e: e["priority"], reverse=True)

    radar = [
        {
            "domain_id": did,
            "domain_name": a["name"],
            "weight": a["weight"],
            "current": round(sum(a["cur"]) / len(a["cur"]), 2),
            "target": round(sum(a["tgt"]) / len(a["tgt"]), 2),
        }
        for did, a in domain_agg.items()
    ]

    priorities = [w["competency_id"] for w in weaknesses[:3]]

    improved = [e for e in scored if e.get("delta") and e["delta"] > 0]
    growth = {
        "improved_count": len(improved),
        "total_delta": sum(e["delta"] for e in improved),
        "improved": [
            {"competency_name": e["competency_name"], "from": e["previous_level"], "to": e["current_level"]}
            for e in improved
        ],
    }

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "radar": radar,
        "priorities": priorities,
        "competencies_assessed": len(scored),
        "growth": growth,
    }


async def _narrative(report: dict, profile: dict, reassess: bool, level: int, beginner: bool = False) -> str:
    top = ", ".join(w["competency_name"] for w in report["weaknesses"][:3]) or "none major"
    strong = ", ".join(s["competency_name"] for s in report["strengths"][:3]) or "still forming"
    growth = report.get("growth", {})

    if beginner and not reassess:
        user_msg = (
            f"They're early in the Gen AI journey. Strengths so far: {strong}. First things to learn: {top}. "
            "In 2-3 warm sentences: be encouraging, honest that this coach assumes a little Python/AI exposure, "
            "and name the ONE foundational thing worth starting with. No jargon."
        )
    elif reassess:
        moved = "; ".join(
            f"{g['competency_name']} L{g['from']}→L{g['to']}" for g in growth.get("improved", [])[:4]
        ) or "no measurable movement yet"
        user_msg = (
            f"This is a RE-ASSESSMENT. Movement since last time: {moved}. "
            f"Remaining top gaps: {top}. Write a short, encouraging spoken update that "
            "celebrates the growth specifically, is honest about what still needs work."
        )
    else:
        role = report.get("role_title", "")
        role_line = f"Targets are set against the {role} role they're aiming for. " if role else ""
        user_msg = (
            f"{role_line}They just finished a leveled assessment and reached Level {level} of 3 "
            f"(Foundations → Application → Design). Strengths: {strong}. Soft spots vs that bar: {top}. "
            "Give a short, warm CLOSING summary — where they landed relative to the target and the one "
            "or two things worth sharpening next. 2-3 sentences."
        )

    messages: list[Message] = [
        {
            "role": "system",
            "content": (
                COACH_PERSONA
                + "\nRight now you're giving a short spoken summary of their evaluation — "
                "2-3 sentences, honest and encouraging, naming the focus areas plainly."
            ),
        },
        {"role": "user", "content": user_msg},
    ]
    return await emit_streamed_text("report", messages, temperature=0.4, max_tokens=400)


async def report(state: CoachState) -> dict:
    cmap = get_competency_map()
    reassess = state.get("mode") == "reassess"
    prior = state.get("prior_levels", {}) if reassess else {}
    scores = state.get("scores", {})

    # In reassess mode, carry prior levels for competencies we didn't re-probe so
    # the radar reflects the full current standing; new scores override.
    merged = {}
    if reassess:
        for cid, lvl in prior.items():
            merged[cid] = {
                "competency_id": cid,
                "level": lvl,
                "evidence": "Carried from your last assessment (not re-probed this session).",
                "confidence": 0.5,
            }
    merged.update(scores)

    built = build_report(merged, cmap, prior_levels=prior, jd_targets=state.get("jd_targets") or {})
    built["role_title"] = state.get("role_title", "")
    built["benchmark"] = benchmark_report(built["radar"])
    built["roadmap"] = build_roadmap(built, cmap)

    profile = state.get("profile") or {}
    # Enrich the roadmap and stream the spoken summary concurrently — the roadmap
    # is mutated in place, so it's fully enriched by the time we emit the report.
    _, narrative = await asyncio.gather(
        enrich_roadmap(built["roadmap"], profile, built.get("role_title", "")),
        _narrative(built, profile, reassess, state.get("level", 1), state.get("beginner", False)),
    )
    emit({"type": "report", "data": built})
    return {
        "phase": "report",
        "report": built,
        "messages": [{"role": "assistant", "content": narrative}],
    }
