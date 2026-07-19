"""Rep engine — type selection, generation (offline fallback), grading, client safety."""

import pytest

from app.coaching.reps import (
    Rep,
    _templated_rep,
    default_rep_type,
    generate_rep,
    grade_rep,
    validate_rep,
)
from app.competency.loader import get_competency_map


def test_default_rep_type_maps_sensibly():
    assert default_rep_type("rag.chunking") == "code"          # has an exercise
    assert default_rep_type("agents.failure_modes") == "code"  # also has an exercise
    assert default_rep_type("rag.when_not") == "design"        # judgement, no exercise
    assert default_rep_type("llm.tokens_context") == "explain"
    assert default_rep_type("ctx.hallucination") == "critique"


def test_templated_rep_is_valid_and_gradeable():
    cmap = get_competency_map()
    comp = cmap.competency("rag.when_not")
    rep = _templated_rep(comp, "design", 4)
    assert rep.prompt and rep.target_level == 4
    assert len(rep.rubric) >= 3
    # client view withholds the rubric
    assert "rubric" not in rep.client_view()
    assert rep.client_view()["prompt"] == rep.prompt


@pytest.mark.asyncio
async def test_generate_rep_offline_falls_back(monkeypatch=None):
    # No keys in the test env → generation can't reach a model; must still return
    # a valid, gradeable rep via the templated fallback.
    rep = await generate_rep("eval.design_golden", 3, "design")
    assert isinstance(rep, Rep)
    assert rep.prompt and len(rep.rubric) >= 3
    assert rep.competency_id == "eval.design_golden"


@pytest.mark.asyncio
async def test_code_rep_reuses_exercise():
    rep = await generate_rep("rag.chunking", 4, "code")
    assert rep.type == "code" and rep.language == "python"
    assert "chunk" in rep.prompt.lower()
    assert rep.source == "seed"


@pytest.mark.asyncio
async def test_validate_rep_is_permissive_offline():
    cmap = get_competency_map()
    rep = _templated_rep(cmap.competency("rag.when_not"), "design", 3)
    # Offline (no judge) → validator must not block (templated fallback is the net).
    assert await validate_rep(rep) is True


@pytest.mark.asyncio
async def test_grade_rep_returns_structured_result():
    rep = await generate_rep("rag.when_not", 3, "design")
    g = await grade_rep(rep, "RAG is wrong when the answer needs reasoning over the whole corpus, "
                              "or the data fits in the context window; then just prompt directly.")
    assert 1 <= g["level"] <= 5
    assert isinstance(g["passed"], bool)
    assert 0.0 <= g["confidence"] <= 1.0
    assert g["target_level"] == 3
