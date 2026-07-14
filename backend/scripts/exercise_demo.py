"""Demonstrate behavioral grading against a RUNNING server.

Grades three submissions for the same task — complete code, an incomplete
attempt, and an all-talk comment — and prints the level + objective checks for
each. Shows the coach scores what the code DOES, not how it's described.

    uv run python scripts/exercise_demo.py
"""

from __future__ import annotations

import argparse
import asyncio

import httpx

_COMPLETE = """
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

_INCOMPLETE = """
async def run_batch(prompts, call_llm):
    results = []
    for p in prompts:
        results.append(await call_llm(p))
    return results
"""

_ALL_TALK = """
# I would use asyncio with a Semaphore to cap concurrency, add retries with
# exponential backoff, set a per-call timeout, and gather with return_exceptions
# so one failure does not sink the batch.
def run_batch(prompts, call_llm):
    pass
"""


async def main(http_base: str) -> int:
    async with httpx.AsyncClient(timeout=40) as c:
        sess = (await c.post(f"{http_base}/auth/session")).json()
        headers = {"Authorization": f"Bearer {sess['token']}"}
        ex = (await c.get(f"{http_base}/exercise/py.async")).json()
        print(f"TASK: {ex['title']}\n  {ex['prompt']}\n")

        for label, sub in [("COMPLETE code", _COMPLETE), ("INCOMPLETE code", _INCOMPLETE), ("ALL TALK (comments)", _ALL_TALK)]:
            r = (await c.post(f"{http_base}/grade", json={"competency_id": "py.async", "submission": sub}, headers=headers)).json()
            passed = "".join("✓" if ck["passed"] else "·" for ck in r["checks"])
            print(f"{label:22} → L{r['level']}/{r['target_level']}  checks[{passed}]  objective={r['deterministic_score']}")
        print()
        prog = (await c.get(f"{http_base}/progress", headers=headers)).json()["entries"]
        print(f"Persisted to ledger: {[(e['competency_name'], 'L'+str(e['current_level'])) for e in prog]}")
    print("\n(The all-talk submission names every technique but implements none — "
          "objective checks and the code-judge both refuse to credit it.)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--http", default="http://localhost:8000")
    raise SystemExit(asyncio.run(main(ap.parse_args().http)))
