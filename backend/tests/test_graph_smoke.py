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


@pytest.mark.asyncio
async def test_interview_mode_runs_to_debrief_with_verdict():
    """Interview mode loops through questions and ends in a debrief with a
    hiring verdict on the report — never a coaching offer."""
    repo = MemoryRepository()
    graph = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": "iv1", "repo": repo}}
    initial = {
        "thread_id": "iv1",
        "user_id": "u1",
        "session_id": "iv1",
        "profile": {"goal": "senior Gen AI role", "background": "backend dev"},
        "requested_mode": "interview",
        "scores": {},
        "focus_index": 0,
    }

    result = await graph.ainvoke(initial, config=config)

    guard = 0
    while result.get("__interrupt__"):
        guard += 1
        assert guard < 200, "interview loop did not converge"
        # Every pause in interview mode awaits an interview answer.
        assert result["__interrupt__"][0].value.get("type") == "interview_answer"
        result = await graph.ainvoke(Command(resume=_ANSWER), config=config)

    assert result.get("phase") == "done"

    report = result.get("report")
    assert report and report.get("interview") is True
    assert report.get("verdict") in {"Strong hire", "Lean hire", "Borderline", "Not yet"}
    assert result.get("verdict") == report.get("verdict")
