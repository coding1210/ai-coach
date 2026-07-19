"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  fetchHint,
  fetchMap,
  fetchMastery,
  fetchPracticeNext,
  fetchRep,
  flagRep,
  gradeRep,
} from "@/lib/api";
import { glossForCompetency } from "@/lib/glossary";
import type {
  FieldDomain,
  MasteryItem,
  PracticeRep,
  QueueItem,
  RepGrade,
} from "@/lib/types";

const TYPE_LABEL: Record<string, string> = {
  code: "Code rep",
  design: "Design rep",
  critique: "Critique rep",
  explain: "Explain rep",
  project: "Real-world project",
};

type Status = "idle" | "loading" | "ready" | "grading" | "graded" | "error";

export default function Practice() {
  const [domains, setDomains] = useState<FieldDomain[]>([]);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [mastery, setMastery] = useState<MasteryItem[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [rep, setRep] = useState<PracticeRep | null>(null);
  const [answer, setAnswer] = useState("");
  const [hints, setHints] = useState<string[]>([]);
  const [grade, setGrade] = useState<RepGrade | null>(null);
  const [err, setErr] = useState("");

  const refreshState = useCallback(() => {
    fetchPracticeNext().then(setQueue).catch(() => {});
    fetchMastery().then(setMastery).catch(() => {});
  }, []);

  useEffect(() => {
    fetchMap().then(setDomains).catch(() => {});
    refreshState();
  }, [refreshState]);

  async function startRep(competencyId?: string, targetLevel?: number, repType?: string) {
    setStatus("loading");
    setErr("");
    setGrade(null);
    setAnswer("");
    setHints([]);
    try {
      const r = await fetchRep({
        ...(competencyId ? { competency_id: competencyId } : {}),
        ...(targetLevel ? { target_level: targetLevel } : {}),
        ...(repType ? { type: repType } : {}),
      });
      setRep(r);
      setStatus("ready");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Couldn't start a rep.");
      setStatus("error");
    }
  }

  async function getHint() {
    if (!rep || hints.length >= 3) return;
    const h = await fetchHint(rep.id, answer, hints.length + 1);
    if (h) setHints((prev) => [...prev, h]);
  }

  async function submit() {
    if (!rep || !answer.trim()) return;
    setStatus("grading");
    try {
      const g = await gradeRep(rep.id, answer, hints.length);
      setGrade(g);
      setStatus("graded");
      refreshState();
    } catch {
      setErr("Grading failed.");
      setStatus("error");
    }
  }

  return (
    <main className="mx-auto min-h-[100dvh] w-full max-w-2xl px-5 py-10 sm:px-8">
      <header className="mb-8 flex items-end justify-between gap-4">
        <div>
          <div className="mb-2.5 flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-accent shadow-accent" />
            <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-dim">
              Practice
            </span>
          </div>
          <h1 className="text-2xl font-semibold tracking-[-0.02em] text-hi sm:text-3xl">
            Work a rep
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-dim text-pretty">
            Calibrated practice with honest feedback. Attempt, get graded on what you
            demonstrate, take a hint if you&apos;re stuck, and climb the levels.
          </p>
        </div>
        <Link
          href="/"
          className="hidden shrink-0 rounded-md border border-edge px-3.5 py-2 text-xs font-medium text-mid transition-colors hover:border-edge-strong hover:text-hi sm:block"
        >
          ← Back
        </Link>
      </header>

      {err && (
        <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/[0.07] px-4 py-2.5 text-sm text-red-300">
          {err}
        </div>
      )}

      {/* Session queue + picker */}
      <div className="rounded-xl border border-edge/70 bg-panel p-5">
        {queue.length > 0 && (
          <div className="mb-4">
            <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-accent">
              Today&apos;s reps
            </span>
            <div className="mt-2 flex flex-wrap gap-2">
              {queue.map((q) => (
                <button
                  key={q.competency_id}
                  onClick={() => startRep(q.competency_id)}
                  title={q.reason}
                  className="rounded-md border border-edge px-3 py-1.5 text-xs font-medium text-mid transition-colors hover:border-accent/60 hover:text-hi"
                >
                  {q.competency_name}
                  <span className="ml-1.5 font-mono text-[10px] text-faint">→L{q.target_level}</span>
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => startRep()}
            disabled={status === "loading"}
            className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-ink transition-transform duration-200 ease-out-quart active:scale-[0.98] disabled:opacity-40"
          >
            Practice my top gap
          </button>
          <button
            onClick={() => startRep(undefined, undefined, "project")}
            disabled={status === "loading"}
            title="Build a real artifact in your own editor and bring it back to be graded"
            className="rounded-md border border-edge px-3 py-2 text-xs font-medium text-mid transition-colors hover:border-accent/60 hover:text-hi disabled:opacity-40"
          >
            Real-world project
          </button>
          <span className="text-xs text-faint">or pick:</span>
          <select
            onChange={(e) => e.target.value && startRep(e.target.value)}
            value=""
            className="min-w-0 flex-1 rounded-md border border-edge bg-black/40 px-2.5 py-2 text-xs text-hi outline-none focus:border-accent/60"
          >
            <option value="">Choose a competency…</option>
            {domains.map((d) => (
              <optgroup key={d.id} label={d.name}>
                {d.competencies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
      </div>

      {status === "loading" && <p className="mt-6 text-sm text-dim">Generating a rep…</p>}

      {/* Rep card */}
      {rep && (status === "ready" || status === "grading" || status === "graded") && (
        <div className="mt-6 rounded-xl border border-edge/70 bg-panel p-5">
          <div className="flex items-center justify-between gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
              {TYPE_LABEL[rep.type] ?? "Rep"} · target L{rep.target_level}
            </span>
            <span className="font-mono text-[10px] text-faint">{rep.competency_id}</span>
          </div>
          {glossForCompetency(rep.competency_id) && (
            <p className="mt-1 text-[11px] leading-snug text-faint">
              {glossForCompetency(rep.competency_id)}
            </p>
          )}

          <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-hi">{rep.prompt}</p>
          {rep.audience && <p className="mt-1.5 text-xs text-dim">Audience: {rep.audience}</p>}
          {rep.given_artifact && (
            <pre className="scroll-thin mt-3 overflow-x-auto rounded-md border border-edge bg-black/40 p-3 font-mono text-[12px] leading-relaxed text-mid">
              {rep.given_artifact}
            </pre>
          )}

          {rep.type === "project" && (
            <p className="mt-3 rounded-md border border-accent/30 bg-accent/[0.06] px-3 py-2 text-xs leading-relaxed text-mid">
              Build this in your own editor, then paste the code (or a key file) below. It&apos;s
              graded on whether the real artifact demonstrates the competency.
            </p>
          )}
          {(() => {
            const codeLike = rep.type === "code" || rep.type === "project";
            return (
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                disabled={status === "grading"}
                spellCheck={!codeLike}
                rows={codeLike ? 10 : 6}
                placeholder={codeLike ? "# your code" : "Your answer — be specific and concrete."}
                className={`mt-4 w-full resize-y rounded-md border border-edge bg-black/40 p-3 text-sm leading-relaxed text-hi outline-none transition-colors focus:border-accent/60 disabled:opacity-60 ${
                  codeLike ? "font-mono text-[12px]" : ""
                }`}
              />
            );
          })()}

          {hints.length > 0 && (
            <ul className="mt-3 space-y-1.5">
              {hints.map((hint, i) => (
                <li key={i} className="flex gap-1.5 rounded-md border border-edge/60 bg-ink/40 px-3 py-2 text-xs leading-relaxed text-mid">
                  <span className="shrink-0 text-accent">Hint {i + 1}</span>
                  <span>{hint}</span>
                </li>
              ))}
            </ul>
          )}

          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              onClick={submit}
              disabled={status === "grading" || !answer.trim()}
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-ink transition-transform duration-200 ease-out-quart active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {status === "grading" ? "Grading…" : grade ? "Resubmit" : "Submit"}
            </button>
            {hints.length < 3 && (
              <button onClick={getHint} className="text-xs text-dim transition-colors hover:text-accent">
                💡 {hints.length === 0 ? "Get a hint" : "Another hint"}
              </button>
            )}
            <button
              onClick={() => startRep(rep.competency_id)}
              className="text-xs text-dim transition-colors hover:text-hi"
            >
              ↻ New rep
            </button>
            <button
              onClick={() => {
                flagRep(rep.id).catch(() => {});
                startRep(rep.competency_id);
              }}
              title="This rep is confusing or off-topic — flag it and get another"
              className="ml-auto text-xs text-faint transition-colors hover:text-warn"
            >
              ⚑ Report this rep
            </button>
          </div>

          {status === "graded" && grade && (
            <GradeView grade={grade} onAdvance={(cid, lvl) => startRep(cid, lvl)} repCompetency={rep.competency_id} />
          )}
        </div>
      )}

      {mastery.length > 0 && <MasteryPanel mastery={mastery} />}
    </main>
  );
}

function GradeView({
  grade,
  onAdvance,
  repCompetency,
}: {
  grade: RepGrade;
  onAdvance: (competencyId: string, level?: number) => void;
  repCompetency: string;
}) {
  const cleared = grade.passed;
  return (
    <div className="mt-4 space-y-2.5 border-t border-edge/60 pt-4">
      <div
        className={`flex items-center justify-between rounded-md border px-3 py-2 ${
          grade.held
            ? "border-accent/50 bg-accent/15"
            : cleared
              ? "border-accent/40 bg-accent/10"
              : "border-warn/40 bg-warn/10"
        }`}
      >
        <span className={`text-sm font-medium ${cleared ? "text-accent" : "text-warn"}`}>
          {grade.held ? "Held — you've got this one" : cleared ? "Cleared — you hit the target" : "Not there yet"}
        </span>
        <span className="nums font-mono text-[11px] text-dim">
          scored L{grade.level}
          <span className="text-faint"> · target </span>L{grade.target_level}
          <span className="text-faint"> · </span>
          {Math.round(grade.confidence * 100)}% conf
        </span>
      </div>

      {grade.criteria_results && grade.criteria_results.length > 0 && (
        <ul className="space-y-1">
          {grade.criteria_results.map((c) => (
            <li key={c.id} className="flex items-start gap-1.5 text-xs leading-relaxed text-mid">
              <span className={`mt-0.5 shrink-0 font-mono ${c.met ? "text-accent" : "text-warn"}`}>
                {c.met ? "✓" : "✕"}
              </span>
              <span className={c.met ? "text-mid" : "text-dim"}>{c.note || c.id}</span>
            </li>
          ))}
        </ul>
      )}

      {grade.evidence && <p className="text-xs leading-relaxed text-dim">{grade.evidence}</p>}

      <div className="flex items-center gap-3 pt-1">
        {grade.held ? (
          <button
            onClick={() => onAdvance("")}
            className="rounded-md border border-accent/40 bg-accent/10 px-3 py-1.5 text-xs font-semibold text-accent"
          >
            Practice my next gap →
          </button>
        ) : grade.next_level != null ? (
          <button
            onClick={() => onAdvance(repCompetency, grade.next_level ?? undefined)}
            className="rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-accent-ink"
          >
            {cleared ? `Next rep · L${grade.next_level}` : grade.scaffolded ? `Ease off · L${grade.next_level}` : "Try again"}
          </button>
        ) : null}
      </div>
    </div>
  );
}

const STATUS_TONE: Record<string, string> = {
  held: "text-accent border-accent/40 bg-accent/10",
  practicing: "text-mid border-edge-strong bg-ink/50",
  needs_refresh: "text-warn border-warn/40 bg-warn/10",
};

function MasteryPanel({ mastery }: { mastery: MasteryItem[] }) {
  const held = mastery.filter((m) => m.status === "held").length;
  const practicing = mastery.filter((m) => m.status === "practicing").length;
  return (
    <section className="mt-8">
      <h3 className="mb-2.5 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
        <span className="h-1 w-1 rounded-full bg-accent" />
        Your practice
        <span className="ml-1 font-normal normal-case tracking-normal text-faint">
          · {held} held · {practicing} in progress
        </span>
      </h3>
      <ul className="space-y-2">
        {mastery.map((m) => (
          <li key={m.competency_id} className="rounded-md border border-edge/60 bg-raised px-3 py-2.5">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium text-hi">{m.competency_name}</span>
              <span
                className={`rounded border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] ${
                  STATUS_TONE[m.status] ?? "text-dim border-edge"
                }`}
              >
                {m.status}
              </span>
            </div>
            <div className="mt-1.5 flex items-center gap-2 font-mono text-[11px] text-dim">
              <span className="nums">L{m.level}</span>
              <span className="text-faint">·</span>
              <span>{Math.round(m.confidence * 100)}% conf</span>
              {m.trajectory && m.trajectory.length > 0 && (
                <span className="ml-1 flex items-center gap-0.5">
                  {m.trajectory.slice(-8).map((a, i) => (
                    <span
                      key={i}
                      title={`attempt ${a.attempt_no}: L${a.level}`}
                      className={`inline-block h-2.5 w-2.5 rounded-sm ${a.passed ? "bg-accent" : "bg-edge-strong"}`}
                    />
                  ))}
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
