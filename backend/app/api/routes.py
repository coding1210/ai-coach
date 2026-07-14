"""REST surface for auth / report / progress / grade / resume (Design.md §10).

The live conversation runs over the WebSocket. These endpoints are scoped to the
authenticated user: the client mints a bearer token (POST /auth/session) and the
user is resolved from that token — never from a URL/body id.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.auth import current_user, new_token, new_user_id
from app.models import (
    AssessmentEvent,
    AuthSessionOut,
    ExerciseOut,
    GradeRequest,
    GradeResponse,
)

router = APIRouter()


@router.post("/auth/session", response_model=AuthSessionOut)
async def create_session(request: Request) -> AuthSessionOut:
    """Mint an anonymous session: a fresh user_id + an opaque bearer token."""
    user_id = new_user_id()
    token = new_token()
    repo = request.app.state.repo
    await repo.upsert_user(user_id, None, None, None)
    await repo.store_token(token, user_id)
    return AuthSessionOut(token=token, user_id=user_id)


@router.get("/report")
async def get_report(request: Request, user_id: str = Depends(current_user)) -> dict:
    report = await request.app.state.repo.get_latest_report(user_id)
    if report is None:
        raise HTTPException(status_code=404, detail="No report for this user yet.")
    return report


@router.get("/progress")
async def get_progress(request: Request, user_id: str = Depends(current_user)) -> dict:
    from app.competency.loader import get_competency_map

    cmap = get_competency_map()
    entries = await request.app.state.repo.get_progress(user_id)

    enriched = []
    for e in entries:
        try:
            name = cmap.competency(e.competency_id).name
            domain_name = cmap.domain_of(e.competency_id).name
        except KeyError:
            name, domain_name = e.competency_id, ""
        enriched.append(
            {**e.model_dump(), "growth": e.growth, "competency_name": name, "domain_name": domain_name}
        )
    return {"user_id": user_id, "entries": enriched}


@router.get("/exercise/{competency_id}", response_model=ExerciseOut)
async def get_exercise(competency_id: str) -> ExerciseOut:
    from app.eval.exercises import get_exercise_bank

    ex = get_exercise_bank().by_competency(competency_id)
    if ex is None:
        raise HTTPException(status_code=404, detail="No exercise for this competency.")
    return ExerciseOut(
        competency_id=ex.competency_id, title=ex.title, language=ex.language, prompt=ex.prompt
    )


@router.post("/grade", response_model=GradeResponse)
async def grade(
    body: GradeRequest, request: Request, user_id: str = Depends(current_user)
) -> GradeResponse:
    """Grade a submitted artifact and persist the behavioral score to the
    authenticated user's ledger."""
    from app.competency.loader import get_competency_map
    from app.competency.selection import target_level_for
    from app.eval.exercises import get_exercise_bank
    from app.llm.grader import grade_submission

    ex = get_exercise_bank().by_competency(body.competency_id)
    if ex is None:
        raise HTTPException(status_code=404, detail="No exercise for this competency.")

    result = await grade_submission(ex, body.submission)
    target = target_level_for(get_competency_map().domain_of(body.competency_id).weight)

    repo = request.app.state.repo
    session_id = body.session_id or ("exercise_" + uuid.uuid4().hex[:8])
    await repo.start_session(session_id, user_id, session_id)
    await repo.record_assessments(
        session_id,
        user_id,
        [
            AssessmentEvent(
                competency_id=body.competency_id,
                level=result["level"],
                evidence=result["evidence"],
                confidence=result["confidence"],
            )
        ],
    )
    await repo.upsert_ledger_entry(
        user_id, body.competency_id, current_level=result["level"], target_level=target
    )

    return GradeResponse(
        competency_id=body.competency_id,
        level=result["level"],
        target_level=target,
        confidence=result["confidence"],
        deterministic_score=result["deterministic_score"],
        evidence=result["evidence"],
        checks=result["checks"],
    )


class ResumeRequest(BaseModel):
    thread_id: str


@router.post("/session/resume")
async def resume_session(
    body: ResumeRequest, request: Request, user_id: str = Depends(current_user)
) -> dict:
    """Report where a checkpointed thread is paused — only if it belongs to the
    authenticated user."""
    graph = request.app.state.graph
    snapshot = await graph.aget_state({"configurable": {"thread_id": body.thread_id}})
    if not snapshot.created_at:
        raise HTTPException(status_code=404, detail="Unknown thread_id.")
    if snapshot.values.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your session.")
    return {
        "thread_id": body.thread_id,
        "phase": snapshot.values.get("phase"),
        "next": list(snapshot.next),
        "awaiting_input": bool(snapshot.next),
    }
