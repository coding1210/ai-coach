"""Pydantic models for the API surface and durable records.

Kept separate from the LangGraph state (app/graph/state.py), which is a
TypedDict tuned for graph reducers. These are the typed boundaries for HTTP/WS
payloads and the proficiency ledger.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


# ─── Ledger / progress ───────────────────────────────────────────
class LedgerEntry(BaseModel):
    competency_id: str
    baseline_level: int | None = None
    current_level: int | None = None
    target_level: int | None = None
    updated_at: datetime | None = None

    @property
    def growth(self) -> int | None:
        if self.baseline_level is None or self.current_level is None:
            return None
        return self.current_level - self.baseline_level


class AssessmentEvent(BaseModel):
    competency_id: str
    level: int
    evidence: str = ""
    confidence: float = 0.5


# ─── Auth ────────────────────────────────────────────────────────
class AuthSessionOut(BaseModel):
    token: str
    user_id: str  # for display only; never trusted for access control


# ─── Behavioral exercises ────────────────────────────────────────
class ExerciseOut(BaseModel):
    """Exercise shown to the client — checks/rubric withheld so it can't be gamed."""

    competency_id: str
    title: str
    language: str
    prompt: str


class GradeRequest(BaseModel):
    competency_id: str
    submission: str
    session_id: str | None = None


class CheckResult(BaseModel):
    id: str
    description: str
    passed: bool


class GradeResponse(BaseModel):
    competency_id: str
    level: int
    target_level: int
    confidence: float
    deterministic_score: float
    evidence: str
    checks: list[CheckResult]
    execution: dict | None = None  # sandbox run result when enabled (ran/passed/error)


# ─── WebSocket protocol ──────────────────────────────────────────
class WSClientMessage(BaseModel):
    """Inbound over /ws/session."""

    type: str = "user_message"  # user_message | start
    thread_id: str | None = None
    token: str | None = None  # bearer token (on start) → resolves the user
    content: str = ""
    profile: dict | None = None  # goal, background, target_role, role (on start)
    mode: str | None = None  # coach | interview (on start)


# ─── Program features (code diagnosis / outcomes / sharing) ──────
class CodeDiagnoseRequest(BaseModel):
    source: str = "paste"  # paste | github
    content: str = ""  # pasted code (source=paste)
    url: str = ""  # public repo URL (source=github)
    profile: dict | None = None
    role: str | None = None  # optional role preset key


class OutcomeIn(BaseModel):
    status: str  # interviewing | offer | hired | promoted | no_offer
    role: str = ""
    notes: str = ""


class ShareOut(BaseModel):
    token: str
    url: str


class WSServerEvent(BaseModel):
    """Outbound over /ws/session (one of several event kinds)."""

    type: str  # token | assistant_message | phase | report | error | done
    thread_id: str | None = None
    content: str | None = None
    phase: str | None = None
    data: dict | None = None
