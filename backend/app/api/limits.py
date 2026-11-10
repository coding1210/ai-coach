"""Abuse / cost guards for the LLM-heavy endpoints.

Three checks:
  - a per-IP rate limit on minting anonymous sessions, so the per-session
    guards below can't be reset by simply asking for a new token;
  - a sliding-window rate limit (requests/min) per authenticated session; and
  - a hard per-session budget on LLM-heavy work, charged by how many model
    calls an operation actually fans out to (not one unit per request).

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
_SWEEP_AT = 10_000                    # sweep idle windows once this many keys are tracked
_hits: dict[str, deque[float]] = {}   # key -> request timestamps in the window
_usage: dict[str, int] = {}           # user_id -> LLM budget units spent this session


def _rate_limit(key: str, limit: int, detail: str) -> None:
    now = time.monotonic()
    if len(_hits) >= _SWEEP_AT:
        for k in [k for k, dq in _hits.items() if not dq or now - dq[-1] > _WINDOW]:
            del _hits[k]
    dq = _hits.setdefault(key, deque())
    while dq and now - dq[0] > _WINDOW:
        dq.popleft()
    if len(dq) >= limit:
        raise HTTPException(status_code=429, detail=detail)
    dq.append(now)


def charge(user_id: str, units: int = 1) -> None:
    """Spend `units` of the session's LLM budget, or raise 429 if it won't fit."""
    used = _usage.get(user_id, 0)
    if used + units > get_settings().llm_session_cap:
        raise HTTPException(
            status_code=429,
            detail="You've hit this session's practice limit. Come back later to keep going.",
        )
    _usage[user_id] = used + units


async def session_mint_guard(request: Request) -> None:
    """Dependency for POST /auth/session: cap new anonymous sessions per client IP."""
    ip = request.client.host if request.client else "unknown"
    _rate_limit(
        f"mint:{ip}",
        get_settings().auth_sessions_per_min,
        "Too many new sessions from this address — try again in a minute.",
    )


async def llm_guard(request: Request, user_id: str = Depends(current_user)) -> str:
    """Depend on this instead of `current_user` on any endpoint that spends LLM
    tokens. Charges one budget unit; endpoints that fan out call `charge` for
    the rest. Raises 429 when the rate or the session budget is exceeded."""
    _rate_limit(
        f"user:{user_id}",
        get_settings().rate_limit_per_min,
        "Too many requests — give it a few seconds.",
    )
    charge(user_id, 1)
    return user_id


def reset_limits() -> None:
    """Clear counters (tests)."""
    _hits.clear()
    _usage.clear()
