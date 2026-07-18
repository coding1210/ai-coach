"""Triage routing: genuine attempts are scored; distress / out-of-scope /
injection / questions-back / contests get an aside instead."""

import pytest

from app.graph.edges import route_after_triage
from app.graph.nodes.triage import triage


def test_answer_intent_routes_to_score():
    assert route_after_triage({"intent": "answer"}) == "score"
    assert route_after_triage({}) == "score"  # default


@pytest.mark.parametrize("intent", ["distress", "out_of_scope", "injection", "question_back", "contest"])
def test_non_answer_intents_route_to_aside(intent):
    assert route_after_triage({"intent": intent}) == "aside"


@pytest.mark.asyncio
async def test_finish_short_circuits_to_answer():
    # A finish request shouldn't be classified — it passes through to scoring,
    # which skips and routes to the report.
    out = await triage({"stop_requested": True, "messages": []})
    assert out["intent"] == "answer"
