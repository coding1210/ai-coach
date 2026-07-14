"""Behavioral grading: objective checks discriminate real code, and the
objective score caps the judged level so weak code can't be talked up.
Runs offline (FakeProvider judge returns L3; the cap does the discriminating)."""

import pytest

from app.eval.exercises import load_exercise_bank
from app.llm.grader import grade_submission, run_checks

BANK = load_exercise_bank()

_STRONG_ASYNC = """
import asyncio
sem = asyncio.Semaphore(10)
async def run_batch(prompts, call_llm):
    async def one(p):
        async with sem:
            for attempt in range(3):
                try:
                    return await asyncio.wait_for(call_llm(p), timeout=30)
                except Exception:
                    await asyncio.sleep(2 ** attempt)
    return await asyncio.gather(*[one(p) for p in prompts], return_exceptions=True)
"""

_WEAK_ASYNC = """
def run_batch(prompts, call_llm):
    return [call_llm(p) for p in prompts]
"""


def test_checks_discriminate_real_code():
    ex = BANK.by_competency("py.async")
    _, strong = run_checks(ex, _STRONG_ASYNC)
    _, weak = run_checks(ex, _WEAK_ASYNC)
    assert strong > 0.9  # async + semaphore + retry + timeout + isolation
    assert weak < 0.2    # a plain synchronous list comprehension
    assert strong > weak


def test_comments_do_not_count_as_code():
    # Naming techniques in comments must not pass the objective checks.
    ex = BANK.by_competency("py.async")
    all_talk = (
        "# I would use asyncio with a Semaphore, retries with backoff, and a timeout.\n"
        "def run_batch(prompts, call_llm):\n    pass\n"
    )
    _, score = run_checks(ex, all_talk)
    assert score < 0.2


def test_absent_check_flags_antipattern():
    ex = BANK.by_competency("safety.prompt_injection")
    safe = 'ALLOWED = {"search"}\nprompt = f"""<document>{user_doc}</document>"""'
    unsafe = "eval(user_doc)"
    safe_checks, _ = run_checks(ex, safe)
    unsafe_checks, _ = run_checks(ex, unsafe)
    assert next(c for c in safe_checks if c["id"] == "no_exec")["passed"] is True
    assert next(c for c in unsafe_checks if c["id"] == "no_exec")["passed"] is False


@pytest.mark.asyncio
async def test_weak_code_is_capped_below_strong():
    ex = BANK.by_competency("py.async")
    strong = await grade_submission(ex, _STRONG_ASYNC)
    weak = await grade_submission(ex, _WEAK_ASYNC)
    # FakeProvider judges both L3; the objective cap pulls weak code down.
    assert weak["level"] < strong["level"]
    assert weak["level"] <= 2
    assert weak["deterministic_score"] < strong["deterministic_score"]
    assert "Capped" in weak["evidence"]


@pytest.mark.asyncio
async def test_grade_shape_and_checks_returned():
    ex = BANK.by_competency("llm.structured_output")
    result = await grade_submission(ex, "from pydantic import BaseModel\n# ...")
    assert result["competency_id"] == "llm.structured_output"
    assert 1 <= result["level"] <= 5
    assert isinstance(result["checks"], list) and result["checks"]
