"""Unit tests for the deterministic coaching-roadmap builder."""

from app.coaching.roadmap import _target_anchor, build_roadmap
from app.competency.loader import get_competency_map


def _report_with_weakness(cmap):
    """A minimal report shaped like build_report's output, one clear weak spot."""
    comp = cmap.all_competencies()[0]
    domain = cmap.domain_of(comp.id)
    return {
        "weaknesses": [
            {
                "competency_id": comp.id,
                "competency_name": comp.name,
                "domain_id": domain.id,
                "current_level": 2,
                "target_level": 4,
                "gap": 2,
                "priority": 10,
                "evidence": "Understands the basics but hasn't shown depth.",
            }
        ],
    }


def test_target_anchor_picks_aspirational_rung():
    anchors = {"2": "naive", "4": "structure-aware"}
    # from L1 we want the *proficient* description, not the weak next rung.
    assert _target_anchor(anchors, 1, 4) == (4, "structure-aware")
    assert _target_anchor(anchors, 2, 4) == (4, "structure-aware")
    # nothing above current → fall back to the highest anchor
    assert _target_anchor(anchors, 5, 5) == (4, "structure-aware")
    # no anchors at all → aim at target with no text
    assert _target_anchor({}, 2, 4) == (4, "")


def test_build_roadmap_is_grounded_and_ordered():
    cmap = get_competency_map()
    report = _report_with_weakness(cmap)
    roadmap = build_roadmap(report, cmap)

    assert roadmap["horizon"]
    assert len(roadmap["milestones"]) == 1
    m = roadmap["milestones"][0]

    # Levels mirror the report, never invented.
    assert m["from_level"] == 2 and m["target_level"] == 4
    assert m["rank"] == 1
    # Level names come from the rubric.
    assert m["from_level_name"] and m["target_level_name"]
    # Deterministic fallback always yields actionable content.
    assert len(m["practice"]) >= 2
    assert m["signal"] and m["focus"] and m["why"]
    # A finishable-feeling time estimate is always present.
    assert m["effort"]
    # The 'why' cites the domain weight (coaching prioritization).
    assert m["domain_weight"] in m["why"]


def test_beginner_roadmap_scaffolds_a_gentle_first_step():
    cmap = get_competency_map()
    report = _report_with_weakness(cmap)
    normal = build_roadmap(report, cmap)["milestones"][0]
    beginner = build_roadmap(report, cmap, beginner=True)["milestones"][0]
    # Beginner first step starts small (read/tiny), not "build an artifact".
    assert beginner["practice"][0] != normal["practice"][0]
    assert "small" in beginner["practice"][0].lower() or "tiny" in beginner["practice"][0].lower()


def test_build_roadmap_caps_milestones_at_four():
    cmap = get_competency_map()
    comps = cmap.all_competencies()[:6]
    report = {
        "weaknesses": [
            {
                "competency_id": c.id,
                "competency_name": c.name,
                "domain_id": cmap.domain_of(c.id).id,
                "current_level": 2,
                "target_level": 4,
                "gap": 2,
                "priority": 6 - i,  # already priority-sorted
            }
            for i, c in enumerate(comps)
        ],
    }
    roadmap = build_roadmap(report, cmap)
    assert len(roadmap["milestones"]) == 4
    assert [m["rank"] for m in roadmap["milestones"]] == [1, 2, 3, 4]


def test_build_roadmap_handles_no_weaknesses():
    cmap = get_competency_map()
    roadmap = build_roadmap({"weaknesses": []}, cmap)
    assert roadmap["milestones"] == []
