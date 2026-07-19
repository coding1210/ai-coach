"""Mastery loop + prerequisites."""

import pytest

from app.coaching.mastery import MASTERY_CLEARS, competency_target, update_mastery
from app.competency.prereqs import prereqs_for, prereqs_met
from app.coaching.reps import Rep
from app.persistence.memory_repo import MemoryRepository


def _rep(cid, level):
    return Rep(id=f"rep_{cid}_{level}", competency_id=cid, type="design",
               target_level=level, difficulty=level, prompt="…", rubric=[])


@pytest.mark.asyncio
async def test_held_after_enough_clears_at_target():
    repo = MemoryRepository()
    cid = "rag.when_not"
    tgt = competency_target(cid)
    rep = _rep(cid, tgt)
    grade = {"level": tgt, "passed": True, "confidence": 0.8}
    last = None
    for _ in range(MASTERY_CLEARS):
        last = await update_mastery(repo, "u1", rep, grade, hints_used=0)
    assert last["held"] is True
    m = await repo.get_mastery("u1", cid)
    assert m["status"] == "held" and m["level"] == tgt
    # ledger got the demonstrated level (write-through)
    entries = await repo.get_progress("u1")
    assert any(e.competency_id == cid and e.current_level == tgt for e in entries)


@pytest.mark.asyncio
async def test_level_is_max_demonstrated():
    repo = MemoryRepository()
    cid = "rag.when_not"
    await update_mastery(repo, "u1", _rep(cid, 3), {"level": 3, "passed": True, "confidence": 0.7}, 0)
    await update_mastery(repo, "u1", _rep(cid, 2), {"level": 2, "passed": True, "confidence": 0.7}, 0)
    m = await repo.get_mastery("u1", cid)
    assert m["level"] == 3  # a later weaker rep doesn't lower it


@pytest.mark.asyncio
async def test_struggle_scaffolds_down():
    repo = MemoryRepository()
    cid = "rag.when_not"
    p = await update_mastery(repo, "u1", _rep(cid, 4), {"level": 2, "passed": False, "confidence": 0.5}, hints_used=2)
    assert p["scaffolded"] is True and p["next_level"] == 3


@pytest.mark.asyncio
async def test_revise_same_level_without_hints():
    repo = MemoryRepository()
    p = await update_mastery(repo, "u1", _rep("rag.when_not", 4), {"level": 2, "passed": False, "confidence": 0.5}, hints_used=0)
    assert p["scaffolded"] is False and p["next_level"] == 4


def test_prereqs_gate():
    assert "rag.embeddings" in prereqs_for("rag.hybrid_rerank")
    assert prereqs_met("rag.hybrid_rerank", {"rag.embeddings": 3}) is True
    assert prereqs_met("rag.hybrid_rerank", {"rag.embeddings": 1}) is False
    assert prereqs_met("rag.chunking", {}) is True  # no prereqs
