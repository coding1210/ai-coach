"""End-to-end smoke test of the coaching loop with the FakeProvider, an
InMemorySaver checkpointer, and the in-memory repository — no keys, no DB.

Drives the interrupt loop the way the WS transport does: ainvoke, then resume
with a canned answer for each interrupt until the graph reaches `done`.
"""

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graph.build import build_graph
from app.persistence.memory_repo import MemoryRepository

_ANSWER = (
    "I'd use async with a concurrency limit and backoff/retries, get structured "
    "JSON via schemas, and evaluate retrieval with recall/precision on a labeled set."
)


@pytest.mark.asyncio
async def test_full_loop_runs_to_done_and_persists():
    repo = MemoryRepository()
    graph = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": "t1", "repo": repo}}
    initial = {
        "thread_id": "t1",
        "user_id": "u1",
        "session_id": "t1",
        "profile": {"goal": "senior Gen AI role", "background": "backend dev"},
        "scores": {},
        "focus_index": 0,
    }

    result = await graph.ainvoke(initial, config=config)

    guard = 0
    while result.get("__interrupt__"):
        guard += 1
        assert guard < 200, "loop did not converge"
        result = await graph.ainvoke(Command(resume=_ANSWER), config=config)

    # Reached the end of the graph.
    assert result.get("phase") == "done"

    # A structured report was built after the leveled assessment.
    report = result.get("report")
    assert report and report["competencies_assessed"] >= 3
    assert isinstance(report["priorities"], list)

    # It climbed through the difficulty levels (fake judge clears L1/L2, hits its
    # ceiling at L3 where the tier expects L4).
    assert result.get("level", 1) >= 2

    # The ledger + report were persisted.
    progress = await repo.get_progress("u1")
    assert len(progress) >= 1
    entry = progress[0]
    assert entry.baseline_level is not None and entry.target_level is not None
    assert await repo.get_latest_report("u1") is not None
