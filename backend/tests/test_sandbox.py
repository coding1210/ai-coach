"""Sandbox runner — actually executes a submission against a test harness."""

import pytest

from app.eval.sandbox import run_submission


@pytest.mark.asyncio
async def test_passing_submission_runs_and_passes():
    submission = "def add(a, b):\n    return a + b\n"
    tests = "assert add(2, 3) == 5\nprint('SANDBOX_PASS')"
    r = await run_submission(submission, tests, timeout=5)
    assert r["ran"] and r["passed"]


@pytest.mark.asyncio
async def test_failing_submission_runs_but_fails():
    submission = "def add(a, b):\n    return a - b\n"  # wrong
    tests = "assert add(2, 3) == 5\nprint('SANDBOX_PASS')"
    r = await run_submission(submission, tests, timeout=5)
    assert r["ran"] and not r["passed"]


@pytest.mark.asyncio
async def test_timeout_is_bounded():
    submission = "def go():\n    while True:\n        pass\n"
    tests = "go()\nprint('SANDBOX_PASS')"
    r = await run_submission(submission, tests, timeout=2)
    assert not r["passed"]
