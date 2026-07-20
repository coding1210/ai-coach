"""Program features over REST: roles, code diagnosis, due, share, outcomes.

Runs against the in-memory app with the FakeProvider (no keys/network).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

_CODE = (
    "import asyncio\n"
    "async def run_batch(prompts, call_llm):\n"
    "    sem = asyncio.Semaphore(10)\n"
    "    async def one(p):\n"
    "        async with sem:\n"
    "            for attempt in range(3):\n"
    "                try:\n"
    "                    return await asyncio.wait_for(call_llm(p), timeout=5)\n"
    "                except Exception:\n"
    "                    await asyncio.sleep(2 ** attempt)\n"
    "    return await asyncio.gather(*[one(p) for p in prompts])\n"
)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _auth(client):
    s = client.post("/auth/session").json()
    return {"Authorization": f"Bearer {s['token']}"}


def test_roles_are_public(client):
    r = client.get("/roles")
    assert r.status_code == 200
    assert any(x["key"] == "rag_engineer" for x in r.json()["roles"])


def test_code_diagnosis_produces_report_and_schedules(client):
    h = _auth(client)
    r = client.post("/diagnose/code", json={"source": "paste", "content": _CODE, "role": "rag_engineer"}, headers=h)
    assert r.status_code == 200
    report = r.json()
    assert report["source"] == "code"
    assert report["competencies_assessed"] >= 1
    assert "benchmark" in report and "roadmap" in report

    # It persisted → /report returns it, and scheduling makes items due later (none now).
    assert client.get("/report", headers=h).status_code == 200
    assert "due" in client.get("/due", headers=h).json()


def test_code_diagnosis_rejects_thin_input(client):
    h = _auth(client)
    assert client.post("/diagnose/code", json={"source": "paste", "content": "x"}, headers=h).status_code == 400


def test_share_creates_public_snapshot(client):
    h = _auth(client)
    # No report yet → 404
    assert client.post("/share", headers=h).status_code == 404
    client.post("/diagnose/code", json={"source": "paste", "content": _CODE}, headers=h)
    share = client.post("/share", headers=h).json()
    assert share["token"]
    # Public read — no auth needed.
    snap = client.get(f"/shared/{share['token']}")
    assert snap.status_code == 200
    assert "report" in snap.json()


def test_map_is_public_and_lists_domains(client):
    r = client.get("/map")
    assert r.status_code == 200
    domains = r.json()["domains"]
    assert any(d["id"] == "rag" for d in domains)
    assert all(d["competencies"] for d in domains)


def test_account_recovery_code_reflects_saved_work(client):
    h = _auth(client)
    # Fresh session: nothing saved yet.
    acct = client.get("/account", headers=h).json()
    assert acct["has_report"] is False and acct["competencies_tracked"] == 0
    # After a diagnosis, the same code unlocks saved work.
    client.post("/diagnose/code", json={"source": "paste", "content": _CODE}, headers=h)
    acct2 = client.get("/account", headers=h).json()
    assert acct2["has_report"] is True and acct2["competencies_tracked"] >= 1


def test_practice_rep_and_grade_roundtrip(client):
    h = _auth(client)
    # Explicit competency → generate a rep (rubric withheld), then grade it.
    r = client.post("/practice/rep", json={"competency_id": "rag.when_not"}, headers=h)
    assert r.status_code == 200
    rep = r.json()
    assert rep["competency_id"] == "rag.when_not" and rep["prompt"]
    assert "rubric" not in rep and "checks" not in rep  # server-held only
    g = client.post(
        "/practice/grade",
        json={"rep_id": rep["id"], "submission": "Skip RAG when the corpus fits in context or the "
              "task needs global reasoning; prompt directly or fine-tune instead."},
        headers=h,
    )
    assert g.status_code == 200
    body = g.json()
    assert 1 <= body["level"] <= 5 and isinstance(body["passed"], bool)


def test_practice_rep_needs_a_target(client):
    h = _auth(client)
    # No competency and no prior report → can't pick a gap.
    assert client.post("/practice/rep", json={}, headers=h).status_code == 400


def test_practice_grade_unknown_rep_404(client):
    h = _auth(client)
    assert client.post("/practice/grade", json={"rep_id": "rep_nope", "submission": "x"}, headers=h).status_code == 404


def test_practice_grade_updates_mastery_and_next(client):
    h = _auth(client)
    rep = client.post("/practice/rep", json={"competency_id": "rag.when_not"}, headers=h).json()
    g = client.post(
        "/practice/grade",
        json={"rep_id": rep["id"], "submission": "Skip RAG when the corpus fits in context.", "hints_used": 0},
        headers=h,
    ).json()
    assert "held" in g and "next_level" in g and "mastery" in g
    # mastery endpoint now reflects the attempt
    m = client.get("/practice/mastery", headers=h).json()["mastery"]
    assert any(x["competency_id"] == "rag.when_not" and x["trajectory"] for x in m)


def test_practice_hint_tiers(client):
    h = _auth(client)
    rep = client.post("/practice/rep", json={"competency_id": "rag.when_not"}, headers=h).json()
    r = client.post("/practice/hint", json={"rep_id": rep["id"], "tier": 1, "submission": ""}, headers=h)
    assert r.status_code == 200 and r.json()["hint"]


def test_practice_next_queue_is_prereq_gated(client):
    h = _auth(client)
    # A code diagnosis seeds weaknesses; the queue is built from them, prereq-gated.
    client.post("/diagnose/code", json={"source": "paste", "content": _CODE}, headers=h)
    q = client.get("/practice/next", headers=h).json()["queue"]
    assert isinstance(q, list)
    # hybrid_rerank must not appear before embeddings is demonstrated
    assert not any(x["competency_id"] == "rag.hybrid_rerank" for x in q)


def test_practice_flag_and_stats(client):
    h = _auth(client)
    rep = client.post("/practice/rep", json={"competency_id": "rag.when_not"}, headers=h).json()
    client.post("/practice/grade", json={"rep_id": rep["id"], "submission": "Skip RAG when the corpus fits in context."}, headers=h)
    assert client.post("/practice/flag", json={"rep_id": rep["id"]}, headers=h).json()["ok"] is True
    stats = client.get("/practice/rep-stats", headers=h).json()["stats"]
    row = next((s for s in stats if s["rep_id"] == rep["id"]), None)
    assert row and row["attempts"] >= 1 and row["flags"] >= 1


def test_outcomes_include_mastery_snapshot(client):
    h = _auth(client)
    client.post("/outcome", json={"status": "interviewing", "role": "Gen AI Eng"}, headers=h)
    body = client.get("/outcomes", headers=h).json()
    assert "mastery_snapshot" in body and "held_count" in body["mastery_snapshot"]


def test_llm_endpoint_enforces_session_cap(client):
    from app.api.limits import reset_limits
    from app.config import get_settings

    s = get_settings()
    orig = s.llm_session_cap
    s.llm_session_cap = 2
    reset_limits()
    try:
        h = _auth(client)
        codes = [
            client.post("/practice/rep", json={"competency_id": "rag.when_not"}, headers=h).status_code
            for _ in range(3)
        ]
        assert 200 in codes and codes[-1] == 429  # 3rd op over the cap of 2
    finally:
        s.llm_session_cap = orig
        reset_limits()


def test_outcome_tracking_roundtrip(client):
    h = _auth(client)
    client.post("/outcome", json={"status": "hired", "role": "Gen AI Engineer", "notes": "offer!"}, headers=h)
    outcomes = client.get("/outcomes", headers=h).json()["outcomes"]
    assert outcomes and outcomes[0]["status"] == "hired"
