"""WebSocket transport for the coaching loop (streaming).

Protocol (JSON both ways):
  client → {type:"start", user_id?, thread_id?, profile:{goal,background,target_role}}
  client → {type:"user_message", content}
  server → {type:"assistant_message", content}      non-streamed text (greeting, Q)
  server → {type:"message_start"} / {type:"token", text} / {type:"message_end"}
  server → {type:"tool_call", name, result}          agentic tool use
  server → {type:"report", data}                     structured evaluation
  server → {type:"phase", phase, data}               awaiting user input
  server → {type:"done", phase} | {type:"error", content}

Nodes emit user-facing output via the custom stream (app/graph/streaming.emit);
we run `graph.astream(..., stream_mode=["custom","updates"])`, forward custom
events verbatim, and detect interrupt/END from the updates stream. On interrupt
the graph pauses until the next client message resumes it via Command(resume=...).
"""

from __future__ import annotations

import contextlib
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langgraph.types import Command

from app.graph.state import FINISH_ASSESSMENT
from app.llm.router import get_router
from app.models import WSClientMessage, WSServerEvent

_DEGRADED_NOTICE = (
    "Heads up: the coach isn't reaching the real models right now, so it's running "
    "in demo mode — scores and answers are placeholders, not a real diagnosis."
)

log = logging.getLogger(__name__)
router = APIRouter()


async def _run_turn(ws: WebSocket, graph, config: dict, payload, thread_id: str) -> bool:
    """Stream one turn. Returns True if the graph paused on an interrupt."""
    interrupt_value = None
    async for mode, chunk in graph.astream(
        payload, config=config, stream_mode=["custom", "updates"]
    ):
        if mode == "custom" and isinstance(chunk, dict):
            await ws.send_json({**chunk, "thread_id": thread_id})
        elif mode == "updates" and isinstance(chunk, dict) and "__interrupt__" in chunk:
            interrupts = chunk["__interrupt__"]
            interrupt_value = getattr(interrupts[0], "value", None) if interrupts else None

    if interrupt_value is not None:
        ptype = interrupt_value.get("type") if isinstance(interrupt_value, dict) else None
        phase = {
            "coach_prompt": "coach",
            "awaiting_submission": "challenge",
        }.get(ptype, "assess")
        await ws.send_json(
            WSServerEvent(
                type="phase",
                thread_id=thread_id,
                phase=phase,
                data=interrupt_value if isinstance(interrupt_value, dict) else None,
            ).model_dump(exclude_none=True)
        )
        return True
    return False


async def _resume(ws: WebSocket, graph, config: dict, thread_id: str, user_id: str) -> bool:
    """Replay a checkpointed session to the client and re-signal its phase.
    Returns False if there's no owned checkpoint (caller falls back to a fresh start)."""
    snap = await graph.aget_state(config)
    if not snap.created_at or snap.values.get("user_id") != user_id:
        return False

    for m in snap.values.get("messages", []):
        if m.get("role") == "assistant":
            await ws.send_json(
                {"type": "assistant_message", "content": m["content"], "thread_id": thread_id}
            )
    if snap.values.get("report"):
        await ws.send_json(
            WSServerEvent(
                type="report", thread_id=thread_id, data=snap.values["report"]
            ).model_dump(exclude_none=True)
        )

    if snap.next:  # paused at an interrupt → tell the client what it's awaiting
        interrupts = [i for t in snap.tasks for i in getattr(t, "interrupts", ())]
        pv = interrupts[0].value if interrupts and isinstance(interrupts[0].value, dict) else {}
        phase = {"coach_prompt": "coach", "awaiting_submission": "challenge"}.get(
            pv.get("type"), "assess"
        )
        await ws.send_json(
            WSServerEvent(
                type="phase", thread_id=thread_id, phase=phase, data=pv or None
            ).model_dump(exclude_none=True)
        )
    else:
        await ws.send_json(
            WSServerEvent(
                type="done", thread_id=thread_id, phase=snap.values.get("phase")
            ).model_dump(exclude_none=True)
        )
    return True


@router.websocket("/ws/session")
async def session(ws: WebSocket) -> None:
    await ws.accept()
    graph = ws.app.state.graph
    repo = ws.app.state.repo

    thread_id: str | None = None
    config: dict | None = None
    notified_degraded = False

    try:
        while True:
            raw = await ws.receive_json()
            msg = WSClientMessage.model_validate(raw)

            if thread_id is None or msg.type == "start":
                user_id = await repo.user_for_token(msg.token or "")
                if not user_id:
                    await ws.send_json(
                        WSServerEvent(
                            type="error", content="Unauthorized: missing or invalid token."
                        ).model_dump(exclude_none=True)
                    )
                    await ws.close()
                    return
                thread_id = msg.thread_id or str(uuid.uuid4())
                config = {"configurable": {"thread_id": thread_id, "repo": repo}}

                # Resume an existing, owned thread: replay the transcript + report
                # from the checkpoint and re-signal the current phase — no re-run.
                if msg.thread_id and await _resume(ws, graph, config, thread_id, user_id):
                    continue

                payload = {
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "session_id": thread_id,
                    "profile": msg.profile or {},
                    "scores": {},
                    "focus_index": 0,
                }
            else:
                resume_value = FINISH_ASSESSMENT if msg.type == "finish" else msg.content
                payload = Command(resume=resume_value)

            paused = await _run_turn(ws, graph, config, payload, thread_id)

            # If a provider failed and we fell back to Fake, tell the user once.
            if not notified_degraded and get_router().degraded:
                notified_degraded = True
                await ws.send_json(
                    WSServerEvent(
                        type="notice", thread_id=thread_id, content=_DEGRADED_NOTICE
                    ).model_dump(exclude_none=True)
                )

            if paused:
                continue

            snapshot = await graph.aget_state(config)
            await ws.send_json(
                WSServerEvent(
                    type="done", thread_id=thread_id, phase=snapshot.values.get("phase")
                ).model_dump(exclude_none=True)
            )
            break

    except WebSocketDisconnect:
        return
    except Exception as e:  # noqa: BLE001 — surface, never silently hang the client
        log.exception("WS session error")
        with contextlib.suppress(Exception):
            await ws.send_json(
                WSServerEvent(type="error", content=str(e)).model_dump(exclude_none=True)
            )
