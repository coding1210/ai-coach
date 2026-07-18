import type { Exercise, GradeResult, LedgerEntry, Report } from "./types";

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
