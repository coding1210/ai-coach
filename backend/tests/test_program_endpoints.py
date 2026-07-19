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


def test_outcome_tracking_roundtrip(client):
    h = _auth(client)
    client.post("/outcome", json={"status": "hired", "role": "Gen AI Engineer", "notes": "offer!"}, headers=h)
    outcomes = client.get("/outcomes", headers=h).json()["outcomes"]
    assert outcomes and outcomes[0]["status"] == "hired"
