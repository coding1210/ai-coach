"""Benchmarking (percentiles vs a reference prior) + role presets."""

from app.coaching.benchmark import benchmark_report, refine_with_population
from app.coaching.roles import list_roles, role_label, targets_for_role


def _radar(current):
    return [{"domain_id": "rag", "domain_name": "RAG", "weight": "critical", "current": current, "target": 5}]


def test_benchmark_standing_moves_with_level():
    behind = benchmark_report(_radar(1.0))[0]
    ahead = benchmark_report(_radar(5.0))[0]
    assert behind["percentile"] < ahead["percentile"]
    assert behind["standing"] == "behind most"
    assert ahead["standing"] == "ahead of most"
    assert ahead["typical"] > 0


def test_population_override_beats_prior():
    stats = refine_with_population({"rag": [4.5, 4.6, 4.4]})
    # Against a strong real cohort, a mid score should read as behind.
    r = benchmark_report(_radar(3.0), population=stats)[0]
    assert r["percentile"] < 50


def test_role_presets_set_targets():
    t = targets_for_role("rag_engineer")
    assert t.get("rag") == 5
    assert role_label("rag_engineer") == "RAG Engineer"
    assert targets_for_role(None) == {}
    assert any(r["key"] == "agent_engineer" for r in list_roles())
