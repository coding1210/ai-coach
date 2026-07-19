import type {
  Account,
  DueItem,
  Exercise,
  FieldDomain,
  GradeResult,
  LedgerEntry,
  PracticeRep,
  Profile,
  Report,
  RepGrade,
  RolePreset,
} from "./types";

export const HTTP_BASE =
  process.env.NEXT_PUBLIC_HTTP_BASE ?? "http://localhost:8000";
export const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE ?? "ws://localhost:8000";

export interface Session {
  token: string;
  user_id: string;
}

let _session: Session | null = null;

// Mint (once) an opaque bearer session and cache it. All data access is scoped
// to this token server-side — no user_id is ever put in a URL.
export async function ensureSession(): Promise<Session> {
  if (_session) return _session;
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("coach_session");
    if (stored) {
      _session = JSON.parse(stored) as Session;
      return _session;
    }
  }
  const r = await fetch(`${HTTP_BASE}/auth/session`, { method: "POST" });
  if (!r.ok) throw new Error("Could not start a session.");
  const s = (await r.json()) as Session;
  _session = s;
  if (typeof window !== "undefined") {
    localStorage.setItem("coach_session", JSON.stringify(s));
  }
  return s;
}

// Forget the cached/stored session — used when the backend rejects the token
// (e.g. it was restarted in-memory and no longer knows this token).
export function clearSession(): void {
  _session = null;
  if (typeof window !== "undefined") localStorage.removeItem("coach_session");
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export async function fetchProgress(token: string): Promise<LedgerEntry[]> {
  const r = await fetch(`${HTTP_BASE}/progress`, { headers: authHeaders(token) });
  if (!r.ok) return [];
  return (await r.json()).entries ?? [];
}

export async function fetchReport(token: string): Promise<Report | null> {
  const r = await fetch(`${HTTP_BASE}/report`, { headers: authHeaders(token) });
  if (!r.ok) return null;
  return r.json();
}

export async function fetchExercise(competencyId: string): Promise<Exercise> {
  const r = await fetch(`${HTTP_BASE}/exercise/${competencyId}`);
  if (!r.ok) throw new Error("No challenge available for this competency.");
  return r.json();
}

export async function gradeSubmission(
  competencyId: string,
  submission: string
): Promise<GradeResult> {
  const { token } = await ensureSession();
  const r = await fetch(`${HTTP_BASE}/grade`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ competency_id: competencyId, submission }),
  });
  if (!r.ok) throw new Error("Grading failed. Is the backend running?");
  return r.json();
}

export async function fetchRoles(): Promise<RolePreset[]> {
  const r = await fetch(`${HTTP_BASE}/roles`);
  if (!r.ok) return [];
  return (await r.json()).roles ?? [];
}

export async function diagnoseCode(body: {
  source: "paste" | "github";
  content?: string;
  url?: string;
  role?: string | null;
  profile?: Profile;
}): Promise<Report> {
  const { token } = await ensureSession();
  const r = await fetch(`${HTTP_BASE}/diagnose/code`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = await r.json().catch(() => ({}));
    throw new Error(detail.detail || "Diagnosis failed.");
  }
  return r.json();
}

export async function fetchDue(): Promise<DueItem[]> {
  const { token } = await ensureSession();
  const r = await fetch(`${HTTP_BASE}/due`, { headers: authHeaders(token) });
  if (!r.ok) return [];
  return (await r.json()).due ?? [];
}

export async function createShare(): Promise<string> {
  const { token } = await ensureSession();
  const r = await fetch(`${HTTP_BASE}/share`, {
    method: "POST",
    headers: authHeaders(token),
  });
  if (!r.ok) throw new Error("Nothing to share yet.");
  return (await r.json()).token as string;
}

export async function fetchShared(
  token: string
): Promise<{ report: Report; progress: LedgerEntry[] } | null> {
  const r = await fetch(`${HTTP_BASE}/shared/${token}`);
  if (!r.ok) return null;
  return r.json();
}

export async function fetchAccount(): Promise<Account | null> {
  const { token } = await ensureSession();
  const r = await fetch(`${HTTP_BASE}/account`, { headers: authHeaders(token) });
  if (!r.ok) return null;
  return r.json();
}

/** Restore a session from a recovery code (a bearer token). Returns the account
 *  it unlocks, or null if the code is invalid. On success, caches the session. */
export async function restoreSession(code: string): Promise<Account | null> {
  const token = code.trim();
  if (!token) return null;
  const r = await fetch(`${HTTP_BASE}/account`, { headers: authHeaders(token) });
  if (!r.ok) return null;
  const acct = (await r.json()) as Account;
  const session: Session = { token, user_id: acct.user_id };
  _session = session;
  if (typeof window !== "undefined") {
    localStorage.setItem("coach_session", JSON.stringify(session));
    if (acct.latest_thread) localStorage.setItem("coach_active", acct.latest_thread);
  }
  return acct;
}

export async function fetchRep(body: {
  competency_id?: string;
  type?: string;
  target_level?: number;
}): Promise<PracticeRep> {
  const { token } = await ensureSession();
  const r = await fetch(`${HTTP_BASE}/practice/rep`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = await r.json().catch(() => ({}));
    throw new Error(detail.detail || "Couldn't start a rep.");
  }
  return r.json();
}

export async function gradeRep(repId: string, submission: string): Promise<RepGrade> {
  const { token } = await ensureSession();
  const r = await fetch(`${HTTP_BASE}/practice/grade`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ rep_id: repId, submission }),
  });
  if (!r.ok) throw new Error("Grading failed.");
  return r.json();
}

export async function fetchMap(): Promise<FieldDomain[]> {
  const r = await fetch(`${HTTP_BASE}/map`);
  if (!r.ok) return [];
  return (await r.json()).domains ?? [];
}

export async function recordOutcome(body: {
  status: string;
  role?: string;
  notes?: string;
}): Promise<void> {
  const { token } = await ensureSession();
  await fetch(`${HTTP_BASE}/outcome`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
