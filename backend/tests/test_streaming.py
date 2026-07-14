"""Verify the custom event stream: tokens, tool_call, and report events flow
out of the graph the way the WebSocket consumes them."""

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graph.build import build_graph
from app.persistence.memory_repo import MemoryRepository

_ANSWER = "I'd use async with retries, schemas for JSON, and recall/precision eval."


async def _drain(graph, config, payload, collected):
    """Run one turn via astream, collecting custom events; return True if paused."""
    interrupted = False
    async for mode, chunk in graph.astream(
        payload, config=config, stream_mode=["custom", "updates"]
    ):
        if mode == "custom":
            collected.append(chunk)
        elif mode == "updates" and isinstance(chunk, dict) and "__interrupt__" in chunk:
            interrupted = True
    return interrupted


@pytest.mark.asyncio
async def test_stream_emits_tokens_tool_calls_and_report():
    repo = MemoryRepository()
    graph = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": "s1", "repo": repo}}
    events: list[dict] = []

    payload = {
        "thread_id": "s1",
        "user_id": "s1",
        "session_id": "s1",
        "profile": {"goal": "senior Gen AI role", "background": "backend dev"},
        "scores": {},
        "focus_index": 0,
    }

    guard = 0
    paused = await _drain(graph, config, payload, events)
    while paused:
        guard += 1
        assert guard < 200
        paused = await _drain(graph, config, Command(resume=_ANSWER), events)

    types = [e.get("type") for e in events]
    # Non-streamed greeting/question.
    assert "assistant_message" in types
    # Streamed report narrative + coaching turns.
    assert types.count("message_start") >= 2
    assert "token" in types
    assert "message_end" in types
    # Structured report event.
    report_events = [e for e in events if e.get("type") == "report"]
    assert report_events and report_events[0]["data"]["competencies_assessed"] >= 1
    # Agentic tool use during coaching.
    tool_events = [e for e in events if e.get("type") == "tool_call"]
    assert tool_events and tool_events[0]["name"] == "research_resource"
    assert tool_events[0]["result"]["url"].startswith("http")

    # A graded challenge fires for a focus area that has an exercise, and a
    # behavioral grade comes back with objective checks.
    assert any(e.get("type") == "exercise" for e in events)
    grades = [e for e in events if e.get("type") == "grade"]
    assert grades and isinstance(grades[0]["checks"], list)
