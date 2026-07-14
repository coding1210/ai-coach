"""Pre-demo dry run — end-to-end smoke test against a RUNNING server.

Drives a real coaching session over the WebSocket exactly as the browser does:
start → answer every question → report → coaching → done, then confirms the
report and ledger persisted via REST. Exercises the real streaming pipeline,
the live LLM providers, and the database. Prints PASS/FAIL per check + timings.

    uv run python scripts/dry_run.py                 # localhost
    uv run python scripts/dry_run.py --http http://... --ws ws://...

Exits non-zero if any check fails — run it right before a demo.
Note: with real keys this makes a full assessment's worth of LLM calls
(~cents, ~1-2 min). Point it at a server started with a low COVERAGE_THRESHOLD
for a faster check.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time

import httpx
import websockets

_ANSWER = (
    "I'd use async with a concurrency limit plus retries and timeouts; get "
    "structured JSON via schemas with validation; for RAG I chunk to document "
    "structure, use hybrid search with a re-ranker, and evaluate retrieval with "
    "recall/precision on a labeled set; I route models by cost and latency and "
    "trace tokens per request."
)


async def run(http_base: str, ws_base: str, max_turns: int) -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))

    print(f"Dry run → {http_base}\n")

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{http_base}/health")
        health = r.json() if r.status_code == 200 else {}
        check(
            "health endpoint",
            r.status_code == 200 and health.get("status") == "ok",
            f"providers={health.get('llm_providers')}",
        )
        sess = (await client.post(f"{http_base}/auth/session")).json()
        token, user_id = sess["token"], sess["user_id"]
        check("auth session minted", bool(token), f"user_id={user_id}")

    headers = {"Authorization": f"Bearer {token}"}
    report = None
    assistant_msgs = tool_calls = turns = 0
    first_response = None
    t0 = time.perf_counter()

    try:
        async with websockets.connect(f"{ws_base}/ws/session", max_size=None) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "start",
                        "token": token,
                        "profile": {"goal": "senior Gen AI role", "background": "backend dev"},
                    }
                )
            )
            while True:
                evt = json.loads(await asyncio.wait_for(ws.recv(), timeout=90))
                kind = evt.get("type")
                if kind == "assistant_message":
                    assistant_msgs += 1
                    if first_response is None:
                        first_response = time.perf_counter() - t0
                elif kind == "tool_call":
                    tool_calls += 1
                elif kind == "report":
                    report = evt.get("data")
                elif kind == "phase":
                    turns += 1
                    if turns > max_turns:
                        check("turn cap", False, f"exceeded {max_turns}")
                        break
                    await ws.send(json.dumps({"type": "user_message", "content": _ANSWER}))
                elif kind == "done":
                    break
                elif kind == "error":
                    check("no websocket error", False, evt.get("content", ""))
                    break
    except Exception as e:  # noqa: BLE001
        check("websocket session", False, str(e))

    total = time.perf_counter() - t0

    check("assistant messages streamed", assistant_msgs > 0, f"{assistant_msgs} messages")
    check(
        "evaluation report produced",
        bool(report) and report.get("competencies_assessed", 0) > 0,
        f"assessed={report.get('competencies_assessed') if report else None}",
    )
    check(
        "focus areas chosen",
        bool(report) and len(report.get("priorities", [])) > 0,
        f"priorities={report.get('priorities') if report else None}",
    )
    check("research tool fired", tool_calls > 0, f"{tool_calls} tool_calls")

    async with httpx.AsyncClient(timeout=15) as client:
        rep = await client.get(f"{http_base}/report", headers=headers)
        prog = await client.get(f"{http_base}/progress", headers=headers)
        noauth = await client.get(f"{http_base}/progress")
    check("unauthenticated /progress is rejected", noauth.status_code == 401, f"status={noauth.status_code}")
    check("report persisted (GET /report)", rep.status_code == 200)
    entries = prog.json().get("entries", []) if prog.status_code == 200 else []
    check("ledger persisted (GET /progress)", len(entries) > 0, f"{len(entries)} competencies")

    fr = f"{first_response:.2f}s" if first_response else "n/a"
    print(f"\n  timings: first response {fr} · total {total:.1f}s · {turns} turns")
    passed = all(ok for _, ok, _ in checks)
    print(f"\n{'=' * 46}\n{'DRY RUN PASSED' if passed else 'DRY RUN FAILED'}  ·  user_id={user_id}\n{'=' * 46}")
    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--http", default="http://localhost:8000")
    ap.add_argument("--ws", default="ws://localhost:8000")
    ap.add_argument("--max-turns", type=int, default=60)
    args = ap.parse_args()
    return asyncio.run(run(args.http, args.ws, args.max_turns))


if __name__ == "__main__":
    raise SystemExit(main())
