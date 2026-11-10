"""Keep the test suite hermetic.

A local `.env` may hold real provider keys (for the app + demo), but tests must
never make network/paid calls. Blanking these env vars *before* any test imports
app.config forces the router onto the deterministic FakeProvider and the
in-memory repository, so `pytest` stays fast, offline, and free.
"""

import os

for _key in (
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "TAVILY_API_KEY",
    "DATABASE_URL",
):
    os.environ[_key] = ""


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_limits():
    """In-process rate/budget counters are global — reset them around every test."""
    from app.api.limits import reset_limits

    reset_limits()
    yield
    reset_limits()
