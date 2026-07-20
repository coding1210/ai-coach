"""Per-session guards for the LLM-heavy endpoints.

Two checks, both keyed to the authenticated user (a session's bearer token):
  - a sliding-window rate limit (requests/min), and
  - a hard per-session cap on total LLM-heavy operations.

Without these, a public URL on live keys is an open wallet. Counters are
in-process — correct for a single worker; put Redis behind a load balancer.
"""

from __future__ import annotations

import time
from collections import deque

from fastapi import Depends, HTTPException, Request

from app.auth import current_user
from app.config import get_settings

_WINDOW = 60.0
_hits: dict[str, deque[float]] = {}   # user_id -> request timestamps in the window
_usage: dict[str, int] = {}           # user_id -> total LLM-heavy ops this session


async def llm_guard(request: Request, user_id: str = Depends(current_user)) -> str:
    """Depend on this instead of `current_user` on any endpoint that spends LLM
    tokens. Raises 429 when the rate or the session cap is exceeded."""
    s = get_settings()
    now = time.monotonic()

    dq = _hits.setdefault(user_id, deque())
    while dq and now - dq[0] > _WINDOW:
        dq.popleft()
    if len(dq) >= s.rate_limit_per_min:
        raise HTTPException(status_code=429, detail="Too many requests — give it a few seconds.")
    dq.append(now)

    used = _usage.get(user_id, 0)
    if used >= s.llm_session_cap:
        raise HTTPException(
            status_code=429,
            detail="You've hit this session's practice limit. Come back later to keep going.",
        )
    _usage[user_id] = used + 1
    return user_id


def reset_limits() -> None:
    """Clear counters (tests)."""
    _hits.clear()
    _usage.clear()
