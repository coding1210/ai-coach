import pytest

from app.competency.loader import load_competency_map
from app.llm.judge import build_judge_messages, score_answer


def test_judge_prompt_is_rubric_grounded_and_bias_controlled():
    cmap = load_competency_map()
    comp = cmap.competency("rag.chunking")
    messages = build_judge_messages(comp, comp.sample_question, "I use fixed-size chunks.")
    system = messages[0]["content"]
    user = messages[1]["content"]
    # Bias controls from the map must be injected into the judge system prompt.
    assert "verbosity" in system.lower()
    # Level anchors ground the scoring.
    assert "L2" in user and "L4" in user
    assert comp.level_anchors["4"] in user


@pytest.mark.asyncio
async def test_score_answer_shape_with_fake_provider():
    # No API keys in the test env → FakeProvider handles the judge call.
    cmap = load_competency_map()
    comp = cmap.competency("agents.langgraph")
    result = await score_answer(comp, comp.sample_question, "I've built LangGraph agents.")
    assert result["competency_id"] == "agents.langgraph"
    assert 1 <= result["level"] <= 5
    assert 0.0 <= result["confidence"] <= 1.0
    assert isinstance(result["evidence"], str)
