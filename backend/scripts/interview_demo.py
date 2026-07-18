"""Interview-mode dry run — drives a full mock-interview over the WebSocket.

Starts a session with mode="interview", answers every interviewer question,
wraps up, and asserts the debrief report carries a hiring verdict.

    uv run python scripts/interview_demo.py            # localhost

Exits non-zero if any check fails. With real keys this makes a full
interview's worth of LLM calls (~cents, ~1 min).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time

import httpx
import websockets

_ANSWER = (
    "I'd run tools async with a concurrency limit, retries, and timeouts, and "
    "return structured JSON validated against a schema. For RAG I chunk to "
    "document structure, use hybrid search with a re-ranker, and measure "
    "retrieval with recall/precision on a labeled set. I route models by cost "
    "and latency and trace tokens per request to watch spend."
)

_VERDICTS = {"Strong hire", "Lean hire", "Borderline", "Not yet"}


async def run(http_base: str, ws_base: str, max_turns: int) -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

    print(f"Interview dry run → {http_base}\n")

    async with httpx.AsyncClient(timeout=15) as client:
        sess = (await client.post(f"{http_base}/auth/session")).json()
        token, user_id = sess["token"], sess["user_id"]
        check("auth session minted", bool(token), f"user_id={user_id}")

    report = None
    interview_phases = questions = 0
    t0 = time.perf_counter()

    try:
        async with websockets.connect(f"{ws_base}/ws/session", max_size=None) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "start",
                        "token": token,
                        "mode": "interview",
                        "profile": {
                            "goal": "senior Gen AI role",
                            "background": "backend dev, some LLM apps",
                            "target_role": "Senior Gen AI Engineer",
                        },
                    }
                )
            )
            while True:
                evt = json.loads(await asyncio.wait_for(ws.recv(), timeout=90))
                kind = evt.get("type")
                if kind == "report":
                    report = evt.get("data")
                elif kind == "phase":
                    if evt.get("phase") == "interview":
                        interview_phases += 1
                    questions += 1
                    if questions > max_turns:
                        check("turn cap", False, f"exceeded {max_turns}")
                        break
                    # Wrap up after a few answers to exercise the early-finish path too.
                    if questions >= 4:
                        await ws.send(json.dumps({"type": "finish"}))
                    else:
                        await ws.send(json.dumps({"type": "user_message", "content": _ANSWER}))
                elif kind == "done":
                    break
                elif kind == "error":
                    check("no websocket error", False, evt.get("content", ""))
                    break
    except Exception as e:  # noqa: BLE001
        check("websocket session", False, str(e))

    total = time.perf_counter() - t0

    check("interview questions asked", questions > 0, f"{questions} turns")
    check("phases labeled 'interview'", interview_phases > 0, f"{interview_phases} interview phases")
    check("debrief report produced", bool(report), f"assessed={report.get('competencies_assessed') if report else None}")
    check("report flagged as interview", bool(report) and report.get("interview") is True)
    verdict = report.get("verdict") if report else None
    check("hiring verdict present & valid", verdict in _VERDICTS, f"verdict={verdict}")

    print(f"\n  timings: total {total:.1f}s · {questions} turns")
    passed = all(ok for _, ok, _ in checks)
    print(f"\n{'=' * 46}\n{'INTERVIEW RUN PASSED' if passed else 'INTERVIEW RUN FAILED'}\n{'=' * 46}")
    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--http", default="http://localhost:8000")
    ap.add_argument("--ws", default="ws://localhost:8000")
    ap.add_argument("--max-turns", type=int, default=20)
    args = ap.parse_args()
    return asyncio.run(run(args.http, args.ws, args.max_turns))


if __name__ == "__main__":
    raise SystemExit(main())
