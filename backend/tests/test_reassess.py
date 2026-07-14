"""Re-assessment loop: targeting prior gaps, delta computation, and end-to-end
growth in the ledger — all offline on the FakeProvider (which scores L3)."""

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.competency.loader import load_competency_map
from app.competency.selection import reassess_targets
from app.graph.build import build_graph
from app.graph.nodes.report import build_report
from app.persistence.memory_repo import MemoryRepository

_ANSWER = "Async with retries, schemas for JSON, hybrid retrieval with re-ranking, recall/precision eval."


def test_reassess_targets_orders_by_gap_weight_and_excludes_at_target():
    cmap = load_competency_map()
    prior = {
        "agents.langgraph": 1,  # critical, target 4, gap 3 → 15
        "rag.chunking": 2,      # critical, target 4, gap 2 → 10
        "py.async": 3,          # medium, target 3, gap 0 → excluded
    }
    assert reassess_targets(cmap, prior) == ["agents.langgraph", "rag.chunking"]


def test_build_report_computes_deltas_and_growth():
    cmap = load_competency_map()
    scores = {
        "rag.chunking": {"competency_id": "rag.chunking", "level": 4, "evidence": "e", "confidence": 0.9},
        "agents.langgraph": {"competency_id": "agents.langgraph", "level": 3, "evidence": "e", "confidence": 0.9},
    }
    prior = {"rag.chunking": 2, "agents.langgraph": 3}
    report = build_report(scores, cmap, prior_levels=prior)
    by_id = {e["competency_id"]: e for e in report["strengths"] + report["weaknesses"]}
    assert by_id["rag.chunking"]["delta"] == 2  # 2 → 4
    assert by_id["agents.langgraph"]["delta"] == 0  # 3 → 3
    assert report["growth"]["improved_count"] == 1
    assert report["growth"]["total_delta"] == 2


@pytest.mark.asyncio
async def test_memory_ledger_preserves_baseline_across_reassessment():
    repo = MemoryRepository()
    await repo.upsert_ledger_entry("u", "rag.chunking", current_level=2, target_level=4)
    await repo.upsert_ledger_entry("u", "rag.chunking", current_level=4, target_level=4)
    (entry,) = [e for e in await repo.get_progress("u") if e.competency_id == "rag.chunking"]
    assert entry.baseline_level == 2 and entry.current_level == 4 and entry.growth == 2


@pytest.mark.asyncio
async def test_returning_user_reassesses_gaps_and_shows_growth():
    # Seed a returning user with low prior levels. Use competencies WITHOUT a
    # graded exercise so this isolates pure re-scoring growth (the challenge path
    # is covered separately); py.async is seeded at target so it isn't re-probed.
    repo = MemoryRepository()
    await repo.upsert_ledger_entry("u2", "agents.langgraph", current_level=1, target_level=4)
    await repo.upsert_ledger_entry("u2", "rag.embeddings", current_level=2, target_level=4)
    await repo.upsert_ledger_entry("u2", "py.async", current_level=3, target_level=3)  # at target

    graph = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": "t2", "repo": repo}}
    result = await graph.ainvoke(
        {"thread_id": "t2", "user_id": "u2", "session_id": "t2", "profile": {}, "scores": {}, "focus_index": 0},
        config=config,
    )
    guard = 0
    while result.get("__interrupt__"):
        guard += 1
        assert guard < 50
        result = await graph.ainvoke(Command(resume=_ANSWER), config=config)

    # Entered re-assessment and re-probed exactly the two below-target competencies.
    assert result["mode"] == "reassess"
    assert "Welcome back" in result["messages"][0]["content"]
    assert result["asked"] == ["agents.langgraph", "rag.embeddings"]

    # Ledger shows growth: FakeProvider scores L3, so 1→3 and 2→3; baselines preserved.
    progress = {e.competency_id: e for e in await repo.get_progress("u2")}
    assert progress["agents.langgraph"].baseline_level == 1
    assert progress["agents.langgraph"].current_level == 3
    assert progress["agents.langgraph"].growth == 2
    assert progress["rag.embeddings"].growth == 1
    assert progress["py.async"].growth == 0  # untouched (was at target)
    assert sum(max(0, e.growth) for e in await repo.get_progress("u2")) == 3
