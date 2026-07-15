from app.competency.loader import load_competency_map
from app.competency.selection import (
    next_competency,
    target_level_for,
    weighted_coverage,
)


def test_next_competency_prefers_highest_weight():
    cmap = load_competency_map()
    first = next_competency(cmap, asked=[])
    # Highest weight is "critical"; first pick must come from a critical domain.
    assert cmap.domain_of(first.id).weight == "critical"


def test_next_competency_is_breadth_first_across_domains():
    cmap = load_competency_map()
    asked: list[str] = []
    domains_hit = []
    for _ in range(6):
        c = next_competency(cmap, asked)
        asked.append(c.id)
        domains_hit.append(cmap.domain_of(c.id).id)
    # First 6 questions span 6 distinct domains, led by the highest-weight one.
    assert len(set(domains_hit)) == 6
    assert domains_hit[0] == "rag"


def test_route_after_score_honors_stop_request():
    from app.graph.edges import route_after_score

    assert route_after_score({"stop_requested": True}) == "report"


def test_coverage_grows_and_reaches_one():
    cmap = load_competency_map()
    assert weighted_coverage(cmap, asked=[]) == 0.0
    all_ids = [c.id for c in cmap.all_competencies()]
    assert weighted_coverage(cmap, asked=all_ids) == 1.0


def test_next_competency_none_when_exhausted():
    cmap = load_competency_map()
    all_ids = [c.id for c in cmap.all_competencies()]
    assert next_competency(cmap, asked=all_ids) is None


def test_target_levels():
    assert target_level_for("critical") == 4
    assert target_level_for("low-medium") == 2
