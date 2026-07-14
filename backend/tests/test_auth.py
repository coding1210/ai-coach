"""Auth: data endpoints require a valid bearer token and are scoped to its user
(the IDOR fix). Uses FastAPI's TestClient against the in-memory app."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_progress_requires_token(client):
    assert client.get("/progress").status_code == 401
    assert client.get("/report").status_code == 401
    assert client.get("/progress", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_session_mints_token_and_scopes_access(client):
    sess = client.post("/auth/session").json()
    assert sess["token"] and sess["user_id"]
    headers = {"Authorization": f"Bearer {sess['token']}"}

    # Valid token: allowed (empty ledger, but 200 not 401).
    r = client.get("/progress", headers=headers)
    assert r.status_code == 200
    assert r.json()["user_id"] == sess["user_id"]


def test_grade_scopes_to_token_user(client):
    a = client.post("/auth/session").json()
    b = client.post("/auth/session").json()

    client.post(
        "/grade",
        json={"competency_id": "py.async", "submission": "import asyncio\nasync def f(): ..."},
        headers={"Authorization": f"Bearer {a['token']}"},
    )
    # A's grade lands under A; B (different token) can't see it.
    a_entries = client.get("/progress", headers={"Authorization": f"Bearer {a['token']}"}).json()["entries"]
    b_entries = client.get("/progress", headers={"Authorization": f"Bearer {b['token']}"}).json()["entries"]
    assert any(e["competency_id"] == "py.async" for e in a_entries)
    assert b_entries == []
