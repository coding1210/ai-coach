"""Bearer-token auth. A client mints an opaque token (POST /auth/session); the
server maps it to a user_id. All data access resolves the user from the token,
never from a URL/body — so ids can't be enumerated (closes the IDOR).

This is prototype-grade identity (no passwords/OAuth): unguessable tokens +
server-side scoping, which is the part that actually stops the leak.
"""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, Request


def new_user_id() -> str:
    return "u_" + secrets.token_hex(8)


def new_token() -> str:
    return secrets.token_urlsafe(24)


def bearer(authorization: str | None) -> str | None:
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1].strip() or None
    return None


async def resolve_user(request: Request, token: str | None) -> str | None:
    if not token:
        return None
    return await request.app.state.repo.user_for_token(token)


async def current_user(
    request: Request, authorization: str | None = Header(default=None)
) -> str:
    """FastAPI dependency: the authenticated user_id, or 401."""
    user_id = await resolve_user(request, bearer(authorization))
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token.")
    return user_id
