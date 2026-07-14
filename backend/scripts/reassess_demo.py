"""Demonstrate status promotion end-to-end against a RUNNING server.

Runs two sessions for the SAME user: a baseline with weak answers, then a
re-assessment with strong answers. The coach re-probes the prior gaps and the
ledger's growth deltas (baseline → current) turn positive — the visible proof
that progress = movement on your own weak areas.

    uv run python scripts/reassess_demo.py

Tip: point it at a server started with a low COVERAGE_THRESHOLD for a quick/cheap
run (fewer baseline competencies to re-probe).
"""

from __future__ import annotations

import argparse
import asyncio
import json

import httpx
import websockets

_WEAK = (
    "I split the text into fixed 500-character chunks and do a top-k similarity "
    "search. If it's slow I might add threads. I use GPT-4 for everything and "
    "eyeball a few outputs to check if they look right."
)
_STRONG = (
    "I use async with a concurrency limit plus retries and timeouts; structured "
    "JSON via schemas with validation; for RAG I chunk to document structure, use "
    "hybrid search with a re-ranker, and evaluate retrieval with recall/precision "
    "on a labeled set; I route models by cost and latency and trace tokens."
)


async def drive(ws_base: str, token: str, answer: str, max_turns: int = 60) -> None:
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
        turns = 0
        while True:
            evt = json.loads(await asyncio.wait_for(ws.recv(), timeout=120))
            kind = evt.get("type")
            if kind == "phase":
                turns += 1
                if turns > max_turns:
                    return
                await ws.send(json.dumps({"type": "user_message", "content": answer}))
            elif kind == "done":
                return
            elif kind == "error":
                raise RuntimeError(evt.get("content", "ws error"))


async def progress(http_base: str, token: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{http_base}/progress", headers={"Authorization": f"Bearer {token}"})
    return r.json().get("entries", []) if r.status_code == 200 else []


async def main(http_base: str, ws_base: str) -> int:
    async with httpx.AsyncClient(timeout=15) as c:
        sess = (await c.post(f"{http_base}/auth/session")).json()
    token, uid = sess["token"], sess["user_id"]
    print(f"user = {uid}\n")

    print("▸ Session 1 — baseline (weak answers)")
    await drive(ws_base, token, _WEAK)
    p1 = await progress(http_base, token)
    if not p1:
        print("  ! no baseline recorded")
        return 1
    avg1 = sum(e["current_level"] for e in p1) / len(p1)
    print(f"  baseline set on {len(p1)} competencies · avg L{avg1:.1f}\n")

    print("▸ Session 2 — re-assessment (strong answers)")
    await drive(ws_base, token, _STRONG)
    p2 = await progress(http_base, token)

    grown = [e for e in p2 if (e.get("growth") or 0) > 0]
    total = sum(max(0, e.get("growth") or 0) for e in p2)
    print(f"\n  Growth: {len(grown)} competencies improved · +{total} levels total")
    for e in sorted(grown, key=lambda x: -(x.get("growth") or 0))[:10]:
        print(f"    ▲ {e['competency_name']}: L{e['baseline_level']} → L{e['current_level']} (+{e['growth']})")

    ok = total > 0
    print(f"\n{'=' * 48}\n{'STATUS PROMOTION PROVEN' if ok else 'NO GROWTH — check answers/threshold'}  ·  user={uid}\n{'=' * 48}")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--http", default="http://localhost:8000")
    ap.add_argument("--ws", default="ws://localhost:8000")
    args = ap.parse_args()
    raise SystemExit(asyncio.run(main(args.http, args.ws)))
