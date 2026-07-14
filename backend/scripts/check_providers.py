"""Connectivity check for the real LLM providers.

Run after adding keys to backend/.env:

    uv run python scripts/check_providers.py

For every provider that has a key, it makes one text call and one JSON call
(the judge path), reporting status + latency. Prints the per-task routing so you
can confirm turns → Groq and scoring/report → GPT. Exits non-zero if any
configured provider fails, so it doubles as a pre-demo smoke test.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

# Make `app` importable regardless of where the script is launched from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings  # noqa: E402
from app.llm.judge import JUDGE_SCHEMA  # noqa: E402
from app.llm.router import get_router  # noqa: E402

_TEXT = [{"role": "user", "content": "Reply with exactly one word: ready"}]
_JSON = [
    {"role": "system", "content": "You are a scorer. Return JSON only."},
    {"role": "user", "content": 'Return {"level":3,"evidence":"ok","confidence":0.5}'},
]


async def _check(name: str, provider) -> bool:
    ok = True

    t0 = time.perf_counter()
    try:
        txt = await provider.complete(_TEXT, max_tokens=16, temperature=0)
        dt = (time.perf_counter() - t0) * 1000
        print(f"  ok  {name:7} complete {dt:6.0f}ms  -> {txt.strip()[:50]!r}")
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"  XX  {name:7} complete FAILED: {e}")

    t0 = time.perf_counter()
    try:
        out = await provider.complete_json(_JSON, schema=JUDGE_SCHEMA, temperature=0)
        dt = (time.perf_counter() - t0) * 1000
        print(f"  ok  {name:7} json     {dt:6.0f}ms  -> {out}")
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"  XX  {name:7} json     FAILED: {e}")

    return ok


async def main() -> int:
    s = get_settings()
    configured = {
        "groq": bool(s.groq_api_key),
        "openai": bool(s.openai_api_key),
        "gemini": bool(s.gemini_api_key),
    }
    print("Keys present:", {k: v for k, v in configured.items()})

    router = get_router()
    real = {k: v for k, v in router.providers.items() if k != "fake"}
    if not real:
        print(
            "\nNo real providers configured. Add keys to backend/.env "
            "(GROQ/OPENAI/GEMINI). The app still runs on FakeProvider."
        )
        return 0

    print(f"\nTesting: {', '.join(sorted(real))}\n")
    results = {name: await _check(name, p) for name, p in sorted(real.items())}

    print("\nPer-task routing:")
    for task in ("turn", "score", "report", "coach"):
        print(f"  {task:7} -> {router.for_task(task).name}")

    failed = [n for n, ok in results.items() if not ok]
    if failed:
        print(f"\nFAILED: {', '.join(failed)}")
        return 1
    print("\nAll configured providers responding.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
