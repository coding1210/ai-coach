"""JD-targeted diagnosis: targets (and therefore gaps) follow the job
description's per-domain requirements, not the generic weights."""

from app.competency.loader import load_competency_map
from app.competency.selection import target_for, target_level_for
from app.graph.nodes.report import build_report

CMAP = load_competency_map()


def test_target_for_prefers_jd_over_generic_weight():
    # RAG is critical → generic target 4; a role that de-emphasizes RAG overrides it.
    assert target_for(CMAP, "rag.chunking", {"rag": 2}) == 2
    # 0 / missing → fall back to the weight-derived target.
    assert target_for(CMAP, "rag.chunking", {"rag": 0}) == target_level_for("critical")
    assert target_for(CMAP, "rag.chunking", {}) == target_level_for("critical")


def test_gaps_reshape_to_the_role():
    scores = {"py.async": {"competency_id": "py.async", "level": 3, "evidence": "", "confidence": 0.9}}

    # Generic: Python is "medium" (target 3) → L3 reads as a strength.
    generic = build_report(scores, CMAP)
    assert any(e["competency_id"] == "py.async" for e in generic["strengths"])

    # A role that demands strong Python (target 5) → the same L3 becomes a gap.
    jd = build_report(scores, CMAP, jd_targets={"python": 5})
    gap_entry = next(e for e in jd["weaknesses"] if e["competency_id"] == "py.async")
    assert gap_entry["gap"] == 2 and gap_entry["target_level"] == 5
