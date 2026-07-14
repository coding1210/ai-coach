"""Custom event streaming out of graph nodes.

Nodes emit user-facing output via `emit(event)` rather than having the transport
infer it from state diffs. The WebSocket consumes these with
`graph.astream(..., stream_mode=["custom", "updates"])` and forwards them.

Event shapes (all dicts):
  {"type": "assistant_message", "content": str}      non-streamed text
  {"type": "message_start"}                            begin a streamed message
  {"type": "token", "text": str}                       one streamed token
  {"type": "message_end"}                              end a streamed message
  {"type": "report", "data": {...}}                    structured evaluation
  {"type": "tool_call", "name": str, ...}              agentic tool use (observability)

`emit` is a no-op when there is no custom-stream consumer (e.g. under ainvoke in
tests), so nodes behave identically whether streamed or invoked.
"""

from __future__ import annotations


def emit(event: dict) -> None:
    try:
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
    except Exception:
        return
    if writer:
        writer(event)


async def emit_streamed_text(provider, messages, *, temperature: float, max_tokens: int) -> str:
    """Stream a provider completion token-by-token as custom events and return
    the full text (still committed to state for history/persistence)."""
    emit({"type": "message_start"})
    parts: list[str] = []
    async for token in provider.stream(
        messages, temperature=temperature, max_tokens=max_tokens
    ):
        parts.append(token)
        emit({"type": "token", "text": token})
    emit({"type": "message_end"})
    return "".join(parts)
