"""Regression tests for the hardening pass: thread ownership on the WebSocket,
abuse/cost guards, degraded grading, router state, and rep generation."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _session(client) -> dict:
    return client.post("/auth/session").json()


def _first_event_thread(ws) -> str:
    while True:
        ev = ws.receive_json()
        if ev.get("thread_id"):
            return ev["thread_id"]


def test_ws_never_runs_on_another_users_thread(client):
    a, b = _session(client), _session(client)
    with client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start", "token": a["token"], "profile": {}})
        a_thread = _first_event_thread(ws)

    with client.websocket_connect("/ws/session") as ws:
        ws.send_json({"type": "start", "token": b["token"], "thread_id": a_thread, "profile": {}})
        b_thread = _first_event_thread(ws)
    assert b_thread != a_thread

    # A's checkpoint still belongs to A.
    h = {"Authorization": f"Bearer {a['token']}"}
    r = client.post("/session/resume", json={"thread_id": a_thread}, headers=h)
    assert r.status_code == 200


def test_minting_sessions_is_rate_limited_per_ip(client):
    from app.config import get_settings

    s = get_settings()
    orig = s.auth_sessions_per_min
    s.auth_sessions_per_min = 3
    try:
        codes = [client.post("/auth/session").status_code for _ in range(4)]
        assert codes == [200, 200, 200, 429]
    finally:
        s.auth_sessions_per_min = orig


def test_code_diagnosis_is_charged_for_its_fan_out(client):
    from app.api.limits import _usage
    from app.config import get_settings
    from app.eval.exercises import get_exercise_bank

    sess = _session(client)
    code = "import asyncio\n" + "async def f():\n    await asyncio.sleep(0)\n" * 3
    r = client.post(
        "/diagnose/code",
        json={"source": "paste", "content": code},
        headers={"Authorization": f"Bearer {sess['token']}"},
    )
    assert r.status_code == 200
    expected = len(get_exercise_bank().exercises) * max(1, get_settings().judge_samples)
    assert _usage[sess["user_id"]] == expected


@pytest.mark.asyncio
async def test_degraded_grading_never_passes(monkeypatch):
    from app.coaching import reps
    from app.coaching.reps import Rep

    class Down:
        async def complete_json(self, *a, **k):
            raise RuntimeError("all providers down")

    monkeypatch.setattr(reps, "get_router", lambda: Down())
    rep = Rep(id="r", competency_id="rag.when_not", type="design", target_level=2,
              difficulty=2, prompt="…", rubric=[])
    g = await reps.grade_rep(rep, "anything")
    assert g["passed"] is False and g["degraded"] is True


@pytest.mark.asyncio
async def test_router_clears_degraded_once_a_real_provider_answers():
    from app.llm.providers import FakeProvider
    from app.llm.router import LLMRouter

    r = LLMRouter()
    r._degraded = True
    r._providers["openai"] = FakeProvider()  # stands in for a recovered real provider
    await r.complete_json("score", [{"role": "user", "content": "x"}], schema={"type": "object"})
    assert r.degraded is False


@pytest.mark.asyncio
async def test_missing_critique_artifact_is_none_not_the_string(monkeypatch):
    from app.coaching import reps

    class Gen:
        async def complete_json(self, *a, **k):
            return {
                "prompt": "Critique this retrieval setup.",
                "criteria": [{"id": f"c{i}", "description": f"criterion {i}", "weight": 1,
                              "level_signal": "x"} for i in range(3)],
                "given_artifact": None,
            }

    async def ok(_rep):
        return True

    monkeypatch.setattr(reps, "get_router", lambda: Gen())
    monkeypatch.setattr(reps, "validate_rep", ok)
    rep = await reps.generate_rep("safety.prompt_injection", 3, "critique")
    assert rep.source == "generated" and rep.given_artifact is None
