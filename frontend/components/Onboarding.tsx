"use client";

import { useEffect, useState } from "react";
import { fetchRoles } from "@/lib/api";
import type { Profile, RolePreset } from "@/lib/types";

const PRESETS: { label: string; profile: Profile }[] = [
  {
    label: "Leveling-up Layla",
    profile: {
      goal: "become a job-ready Gen AI engineer",
      background: "1–3 yrs Python, some LangChain/RAG from tutorials",
      target_role: "Mid-level Gen AI Engineer",
    },
  },
  {
    label: "Pivoting Omar",
    profile: {
      goal: "move into a senior Gen AI role",
      background: "experienced backend dev, strong Python, new to LLMs/agents",
      target_role: "Senior Gen AI Engineer",
    },
  },
];

type Mode = "coach" | "interview" | "code";

const HEADINGS: Record<Mode, { tag: string; title: string; blurb: string }> = {
  coach: {
    tag: "New assessment",
    title: "Tell your coach where you're headed",
    blurb:
      "No syllabus. The coach diagnoses your specific gaps and coaches those — progress means movement on your own weak areas.",
  },
  interview: {
    tag: "Mock interview",
    title: "Sit a mock interview for the role",
    blurb:
      "A realistic interviewer probes your depth, then debriefs with a hire verdict and where you stand. No coaching mid-interview.",
  },
  code: {
    tag: "Diagnose from code",
    title: "Diagnose me from my real code",
    blurb:
      "Paste a project or point at a public GitHub repo. The coach reads what your code actually does — async, retries, structured output, retrieval eval — and grades from evidence, not self-report.",
  },
};

export default function Onboarding({
  onStart,
  onDiagnoseCode,
  disabled,
  diagnosing,
}: {
  onStart: (p: Profile, mode: string) => void;
  onDiagnoseCode: (payload: {
    source: "paste" | "github";
    content?: string;
    url?: string;
    role?: string | null;
    profile: Profile;
  }) => void;
  disabled?: boolean;
  diagnosing?: boolean;
}) {
  const [profile, setProfile] = useState<Profile>({
    goal: "",
    background: "",
    target_role: "",
    jd: "",
  });
  const [mode, setMode] = useState<Mode>("coach");
  const [role, setRole] = useState<string>("");
  const [roles, setRoles] = useState<RolePreset[]>([]);
  const [code, setCode] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    fetchRoles().then(setRoles).catch(() => {});
  }, []);

  const set = (k: keyof Profile) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setProfile((p) => ({ ...p, [k]: e.target.value }));

  const withRole = (): Profile => ({ ...profile, role: role || undefined });

  const ready =
    mode === "code"
      ? code.trim().length > 40 || repoUrl.trim().length > 0
      : Boolean(profile.goal.trim() && profile.background.trim());

  const h = HEADINGS[mode];

  function submit() {
    if (mode === "code") {
      const useRepo = repoUrl.trim().length > 0;
      onDiagnoseCode({
        source: useRepo ? "github" : "paste",
        content: useRepo ? undefined : code,
        url: useRepo ? repoUrl.trim() : undefined,
        role: role || null,
        profile: withRole(),
      });
    } else {
      onStart(withRole(), mode);
    }
  }

  return (
    <div className="mx-auto max-w-lg animate-rise-in rounded-2xl border border-edge/70 bg-white/[0.015] p-1.5 shadow-panel">
      <div className="rounded-[13px] border border-edge/60 bg-panel p-6 sm:p-7">
        {/* How it works — a calm 20-second orientation before any input. */}
        <div className="mb-6 rounded-lg border border-edge/60 bg-black/20 p-4">
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
            How this works
          </span>
          <ol className="mt-2 space-y-1 text-xs leading-relaxed text-mid">
            <li>
              <span className="text-faint">1 · </span>Answer a few questions — there
              are no wrong answers.
            </li>
            <li>
              <span className="text-faint">2 · </span>See where you actually stand
              today.
            </li>
            <li>
              <span className="text-faint">3 · </span>Get a plan built around your
              own gaps.
            </li>
          </ol>
        </div>

        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
          {h.tag}
        </span>
        <h2 className="mt-2.5 text-xl font-semibold tracking-[-0.01em] text-hi">
          {h.title}
        </h2>
        <p className="mt-1.5 text-sm leading-relaxed text-dim text-pretty">{h.blurb}</p>

        {mode === "code" ? (
          <div className="mt-5 space-y-4">
            <Field label="Public GitHub repo URL (optional)">
              <input
                className="coach-input"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/you/your-genai-project"
              />
            </Field>
            <Field label={repoUrl.trim() ? "Or paste code (ignored — using the repo)" : "Paste your code"}>
              <textarea
                className="coach-input font-mono text-xs"
                rows={9}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="Paste one or more Python files from your project…"
              />
            </Field>
          </div>
        ) : (
          <div className="mt-5 space-y-4">
            <Field label="Your goal">
              <input
                className="coach-input"
                value={profile.goal}
                onChange={set("goal")}
                placeholder="e.g. become a Gen AI engineer"
              />
            </Field>
            <Field label="Your background">
              <input
                className="coach-input"
                value={profile.background}
                onChange={set("background")}
                placeholder="e.g. some Python, new to LLMs — or just starting out"
              />
            </Field>
          </div>
        )}

        <button
          disabled={!ready || disabled || diagnosing}
          onClick={submit}
          className="group mt-7 flex w-full items-center justify-center gap-2.5 rounded-md bg-accent px-4 py-3 text-sm font-semibold text-accent-ink transition-[transform,box-shadow] duration-200 ease-out-quart hover:shadow-accent active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-30 disabled:shadow-none disabled:active:scale-100"
        >
          {mode === "code"
            ? diagnosing
              ? "Reading your code…"
              : "Diagnose my code"
            : mode === "interview"
              ? "Start interview"
              : "Start assessment"}
          <span className="grid h-5 w-5 place-items-center rounded-full bg-accent-ink/15 transition-transform duration-200 ease-out-quart group-hover:translate-x-0.5">
            →
          </span>
        </button>

        {/* Advanced — hidden by default so a newcomer sees one obvious path. */}
        <button
          onClick={() => setShowAdvanced((v) => !v)}
          className="mt-4 flex w-full items-center justify-center gap-1.5 text-xs text-dim transition-colors hover:text-hi"
        >
          {showAdvanced ? "Fewer options" : "More options"}
          <span className="text-faint">{showAdvanced ? "▲" : "▾"}</span>
        </button>

        {showAdvanced && (
          <div className="mt-4 space-y-4 border-t border-edge/50 pt-4">
            <div>
              <span className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.16em] text-dim">
                Session type
              </span>
              <div className="grid grid-cols-3 gap-1 rounded-lg border border-edge/70 bg-black/20 p-1">
                {(
                  [
                    ["coach", "Coaching"],
                    ["interview", "Interview"],
                    ["code", "From code"],
                  ] as const
                ).map(([m, label]) => (
                  <button
                    key={m}
                    onClick={() => setMode(m)}
                    className={`rounded-md px-3 py-2 text-xs font-medium transition-[background,color] duration-200 ease-out-quart ${
                      mode === m ? "bg-accent text-accent-ink" : "text-mid hover:text-hi"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {roles.length > 0 && (
              <Field label="Target role (sets the bar)">
                <select
                  className="coach-input"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                >
                  <option value="">Generic senior bar</option>
                  {roles.map((r) => (
                    <option key={r.key} value={r.key}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </Field>
            )}

            {mode !== "code" && (
              <>
                <Field label="Target job description (optional)">
                  <textarea
                    className="coach-input"
                    rows={3}
                    value={profile.jd ?? ""}
                    onChange={(e) => setProfile((p) => ({ ...p, jd: e.target.value }))}
                    placeholder="Paste a JD and the coach measures your gaps against that exact role."
                  />
                </Field>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
                    or load a persona
                  </span>
                  {PRESETS.map((p) => (
                    <button
                      key={p.label}
                      onClick={() => setProfile(p.profile)}
                      className="rounded-md border border-edge px-3 py-1.5 text-xs font-medium text-mid transition-[transform,border-color,color] duration-200 ease-out-quart hover:border-accent/60 hover:text-hi active:scale-[0.97]"
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      <style jsx>{`
        .coach-input {
          width: 100%;
          border-radius: 8px;
          border: 1px solid #262a32;
          background: #0d0e11;
          padding: 0.7rem 0.85rem;
          font-size: 0.875rem;
          color: #e9ebef;
          outline: none;
          transition: border-color 200ms var(--ease-out-quart),
            box-shadow 200ms var(--ease-out-quart);
        }
        .coach-input::placeholder {
          color: #565c67;
        }
        .coach-input:focus {
          border-color: rgba(200, 241, 105, 0.7);
          box-shadow: 0 0 0 3px rgba(200, 241, 105, 0.12);
        }
      `}</style>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.16em] text-dim">
        {label}
      </span>
      {children}
    </label>
  );
}
