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
    CodeDiagnoseRequest,
    ExerciseOut,
    GradeRequest,
    GradeResponse,
    OutcomeIn,
    PracticeGradeRequest,
    PracticeHintRequest,
    PracticeRepRequest,
    ShareOut,
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
        execution=result.get("execution"),
    )


@router.get("/roles")
async def list_role_presets() -> dict:
    from app.coaching.roles import list_roles

    return {"roles": list_roles()}


@router.get("/account")
async def get_account(request: Request, user_id: str = Depends(current_user)) -> dict:
    """What this session's recovery code unlocks — powers 'save / restore progress'.
    The bearer token IS the recovery code (no email infra); this validates it and
    reports whether there's saved work to come back to."""
    repo = request.app.state.repo
    report = await repo.get_latest_report(user_id)
    progress = await repo.get_progress(user_id)
    return {
        "user_id": user_id,
        "has_report": report is not None,
        "competencies_tracked": len(progress),
        "latest_thread": await repo.latest_thread(user_id),
    }


@router.get("/map")
async def field_map() -> dict:
    """The territory: every domain with its competencies — a one-glance map of
    Gen AI engineering for a newcomer to orient against."""
    from app.competency.loader import get_competency_map

    cmap = get_competency_map()
    return {
        "domains": [
            {
                "id": d.id,
                "name": d.name,
                "weight": d.weight,
                "competencies": [{"id": c.id, "name": c.name} for c in d.competencies],
            }
            for d in cmap.domains
        ]
    }


@router.get("/due")
async def get_due(request: Request, user_id: str = Depends(current_user)) -> dict:
    """Competencies due for a spaced re-check, most-overdue first."""
    from datetime import datetime, timezone

    from app.coaching.scheduler import due_items
    from app.competency.loader import get_competency_map

    repo = request.app.state.repo
    entries = await repo.get_progress(user_id)
    reviews = await repo.get_next_reviews(user_id)
    items = due_items(entries, reviews, datetime.now(timezone.utc), cmap=get_competency_map())
    return {"due": items}


@router.post("/diagnose/code")
async def diagnose_from_code(
    body: CodeDiagnoseRequest, request: Request, user_id: str = Depends(current_user)
) -> dict:
    """Diagnose the user from real code (pasted or a public GitHub repo)."""
    from datetime import datetime, timezone

    from app.coaching.roles import role_label, targets_for_role
    from app.coaching.scheduler import schedule_after_session
    from app.competency.loader import get_competency_map
    from app.competency.selection import target_for
    from app.eval.code_diagnosis import diagnose_code, fetch_github

    if body.source == "github":
        try:
            code = await fetch_github(body.url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
    else:
        code = body.content or ""
    if len(code.strip()) < 40:
        raise HTTPException(status_code=400, detail="Please provide more code to diagnose from.")

    jd_targets = targets_for_role(body.role)
    report = await diagnose_code(
        code, profile=body.profile or {}, jd_targets=jd_targets, role_title=role_label(body.role)
    )

    # Persist like a session so /report, /progress, and scheduling all work.
    cmap = get_competency_map()
    repo = request.app.state.repo
    session_id = "code_" + uuid.uuid4().hex[:8]
    await repo.start_session(session_id, user_id, session_id)
    events = []
    for entry in report.get("weaknesses", []) + report.get("strengths", []):
        cid = entry["competency_id"]
        events.append(
            AssessmentEvent(competency_id=cid, level=entry["current_level"], evidence=entry.get("evidence", ""), confidence=0.6)
        )
        await repo.upsert_ledger_entry(
            user_id, cid, current_level=entry["current_level"], target_level=target_for(cmap, cid, jd_targets)
        )
    await repo.record_assessments(session_id, user_id, events)
    await repo.finish_session(session_id, report)
    entries = await repo.get_progress(user_id)
    for cid, when in schedule_after_session(entries, datetime.now(timezone.utc)).items():
        await repo.set_next_review(user_id, cid, when)

    return report


@router.post("/practice/rep")
async def practice_rep(
    body: PracticeRepRequest, request: Request, user_id: str = Depends(current_user)
) -> dict:
    """Generate (or reuse) a calibrated practice rep. Rubric is withheld from the
    response — grade via /practice/grade with the returned rep_id."""
    from app.coaching.reps import Rep, default_rep_type, generate_rep
    from app.competency.loader import get_competency_map
    from app.competency.selection import target_level_for

    cmap = get_competency_map()
    repo = request.app.state.repo

    competency_id = body.competency_id
    target_level = body.target_level
    if not competency_id:
        report = await repo.get_latest_report(user_id)
        weaknesses = (report or {}).get("weaknesses") or []
        if not weaknesses:
            raise HTTPException(status_code=400, detail="Pick a competency to practise, or run a diagnosis first.")
        competency_id = weaknesses[0]["competency_id"]
        target_level = target_level or weaknesses[0].get("target_level")

    try:
        cmap.competency(competency_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="Unknown competency.") from e

    rep_type = body.type or default_rep_type(competency_id)
    if target_level is None:
        target_level = target_level_for(cmap.domain_of(competency_id).weight)
    target_level = max(1, min(5, int(target_level)))

    cached = await repo.get_cached_rep(competency_id, rep_type, target_level)
    if cached:
        rep = Rep.model_validate(cached)
    else:
        rep = await generate_rep(competency_id, target_level, rep_type)
        await repo.save_rep(rep.id, competency_id, rep_type, target_level, rep.model_dump())
    return rep.client_view()


@router.post("/practice/grade")
async def practice_grade(
    body: PracticeGradeRequest, request: Request, user_id: str = Depends(current_user)
) -> dict:
    """Grade a submission, record the attempt, update mastery, and say what's next."""
    from app.coaching.mastery import update_mastery
    from app.coaching.reps import Rep, grade_rep

    repo = request.app.state.repo
    data = await repo.get_rep(body.rep_id)
    if not data:
        raise HTTPException(status_code=404, detail="Rep not found — generate a new one.")
    rep = Rep.model_validate(data)
    grade = await grade_rep(rep, body.submission)
    progress = await update_mastery(repo, user_id, rep, grade, max(0, body.hints_used))
    return {**grade, **progress}


@router.post("/practice/hint")
async def practice_hint(
    body: PracticeHintRequest, request: Request, user_id: str = Depends(current_user)
) -> dict:
    """A graduated hint (tier 1-3) for the current rep."""
    from app.coaching.hints import hint
    from app.coaching.reps import Rep

    data = await request.app.state.repo.get_rep(body.rep_id)
    if not data:
        raise HTTPException(status_code=404, detail="Rep not found — generate a new one.")
    rep = Rep.model_validate(data)
    return {"tier": max(1, min(3, body.tier)), "hint": await hint(rep, body.submission, body.tier)}


@router.get("/practice/mastery")
async def practice_mastery(request: Request, user_id: str = Depends(current_user)) -> dict:
    """All practice mastery + a compact attempt trajectory per competency."""
    from app.competency.loader import get_competency_map

    cmap = get_competency_map()
    repo = request.app.state.repo
    mastery = await repo.get_all_mastery(user_id)
    attempts = await repo.get_rep_attempts(user_id)
    traj: dict[str, list] = {}
    for a in attempts:
        traj.setdefault(a["competency_id"], []).append(
            {"attempt_no": a.get("attempt_no"), "level": a.get("level_awarded"), "passed": a.get("passed")}
        )
    out = []
    for cid, m in mastery.items():
        try:
            name = cmap.competency(cid).name
        except KeyError:
            name = cid
        out.append({**m, "competency_name": name, "trajectory": traj.get(cid, [])})
    out.sort(key=lambda x: (x.get("status") != "held", x.get("competency_name", "")))
    return {"mastery": out}


@router.get("/practice/next")
async def practice_next(request: Request, user_id: str = Depends(current_user)) -> dict:
    """The session queue: what to practise next, priority × due × mastery, prereq-gated."""
    from datetime import datetime, timezone

    from app.competency.loader import get_competency_map
    from app.competency.prereqs import prereqs_met
    from app.competency.selection import target_for

    cmap = get_competency_map()
    repo = request.app.state.repo
    report = await repo.get_latest_report(user_id)
    mastery = await repo.get_all_mastery(user_id)
    levels = {cid: int(m.get("level") or 0) for cid, m in mastery.items()}
    now = datetime.now(timezone.utc).isoformat()

    def entry(cid: str, reason: str) -> dict:
        m = mastery.get(cid, {})
        return {
            "competency_id": cid,
            "competency_name": cmap.competency(cid).name,
            "status": m.get("status", "unseen"),
            "target_level": target_for(cmap, cid, (report or {}).get("jd_targets") if report else None),
            "current_level": int(m.get("level") or 0),
            "reason": reason,
        }

    queue: list[dict] = []
    seen: set[str] = set()

    # 1) Anything due for a spaced re-rep (and not yet held).
    for cid, m in mastery.items():
        if m.get("status") != "held" and (m.get("next_rep_due_at") or "") <= now:
            queue.append(entry(cid, "due for a re-check"))
            seen.add(cid)

    # 2) Top gaps from the report, prereq-gated, skipping held/blocked.
    for w in (report or {}).get("weaknesses", []):
        cid = w["competency_id"]
        if cid in seen or mastery.get(cid, {}).get("status") == "held":
            continue
        if not prereqs_met(cid, levels):
            continue
        queue.append(entry(cid, "a top gap for your target"))
        seen.add(cid)
        if len(queue) >= 6:
            break

    return {"queue": queue}


@router.post("/outcome")
async def record_outcome(
    body: OutcomeIn, request: Request, user_id: str = Depends(current_user)
) -> dict:
    """Track a real-world outcome — the credibility signal (coaching → result)."""
    from datetime import datetime, timezone

    outcome = {
        "status": body.status,
        "role": body.role,
        "notes": body.notes,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    await request.app.state.repo.record_outcome(user_id, outcome)
    return {"ok": True, "outcome": outcome}


@router.get("/outcomes")
async def get_outcomes(request: Request, user_id: str = Depends(current_user)) -> dict:
    return {"outcomes": await request.app.state.repo.get_outcomes(user_id)}


@router.post("/share", response_model=ShareOut)
async def share_report(request: Request, user_id: str = Depends(current_user)) -> ShareOut:
    """Create an opaque, read-only share token for the latest growth report."""
    repo = request.app.state.repo
    report = await repo.get_latest_report(user_id)
    if report is None:
        raise HTTPException(status_code=404, detail="No report to share yet.")
    progress = await repo.get_progress(user_id)
    token = uuid.uuid4().hex
    snapshot = {
        "report": report,
        "progress": [{**e.model_dump(), "growth": e.growth} for e in progress],
    }
    await repo.create_share(token, snapshot)
    return ShareOut(token=token, url=f"/shared/{token}")


@router.get("/shared/{token}")
async def get_shared(token: str, request: Request) -> dict:
    """Public, read-only snapshot — no auth (the opaque token is the capability)."""
    snapshot = await request.app.state.repo.get_share(token)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Shared report not found.")
    return snapshot


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
