"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchMap, fetchRep, gradeRep } from "@/lib/api";
import { glossForCompetency } from "@/lib/glossary";
import type { FieldDomain, PracticeRep, RepGrade } from "@/lib/types";

const TYPE_LABEL: Record<string, string> = {
  code: "Code rep",
  design: "Design rep",
  critique: "Critique rep",
  explain: "Explain rep",
};

type Status = "picking" | "loading" | "ready" | "grading" | "graded" | "error";

export default function Practice() {
  const [domains, setDomains] = useState<FieldDomain[]>([]);
  const [status, setStatus] = useState<Status>("picking");
  const [rep, setRep] = useState<PracticeRep | null>(null);
  const [answer, setAnswer] = useState("");
  const [grade, setGrade] = useState<RepGrade | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    fetchMap().then(setDomains).catch(() => {});
  }, []);

  async function startRep(competencyId?: string) {
    setStatus("loading");
    setErr("");
    setGrade(null);
    setAnswer("");
    try {
      const r = await fetchRep(competencyId ? { competency_id: competencyId } : {});
      setRep(r);
      setStatus("ready");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Couldn't start a rep.");
      setStatus("error");
    }
  }

  async function submit() {
    if (!rep || !answer.trim()) return;
    setStatus("grading");
    try {
      setGrade(await gradeRep(rep.id, answer));
      setStatus("graded");
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
            A calibrated practice task with honest feedback. Attempt it, get graded on
            what you actually demonstrate, and revise.
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

      {/* Picker */}
      <div className="rounded-xl border border-edge/70 bg-panel p-5">
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => startRep()}
            disabled={status === "loading"}
            className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-ink transition-transform duration-200 ease-out-quart active:scale-[0.98] disabled:opacity-40"
          >
            Practice my top gap
          </button>
          <span className="text-xs text-faint">or pick a competency:</span>
          <select
            onChange={(e) => e.target.value && startRep(e.target.value)}
            value=""
            className="min-w-0 flex-1 rounded-md border border-edge bg-black/40 px-2.5 py-2 text-xs text-hi outline-none focus:border-accent/60"
          >
            <option value="">Choose…</option>
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

      {status === "loading" && (
        <p className="mt-6 text-sm text-dim">Generating a rep…</p>
      )}

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
          {rep.audience && (
            <p className="mt-1.5 text-xs text-dim">Audience: {rep.audience}</p>
          )}
          {rep.given_artifact && (
            <pre className="scroll-thin mt-3 overflow-x-auto rounded-md border border-edge bg-black/40 p-3 font-mono text-[12px] leading-relaxed text-mid">
              {rep.given_artifact}
            </pre>
          )}

          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            disabled={status === "grading"}
            spellCheck={rep.type !== "code"}
            rows={rep.type === "code" ? 10 : 6}
            placeholder={rep.type === "code" ? "# your solution" : "Your answer — be specific and concrete."}
            className={`mt-4 w-full resize-y rounded-md border border-edge bg-black/40 p-3 text-sm leading-relaxed text-hi outline-none transition-colors focus:border-accent/60 disabled:opacity-60 ${
              rep.type === "code" ? "font-mono text-[12px]" : ""
            }`}
          />

          <div className="mt-3 flex items-center gap-3">
            <button
              onClick={submit}
              disabled={status === "grading" || !answer.trim()}
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-ink transition-transform duration-200 ease-out-quart active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {status === "grading" ? "Grading…" : grade ? "Resubmit" : "Submit"}
            </button>
            <button
              onClick={() => startRep(rep.competency_id)}
              className="text-xs text-dim transition-colors hover:text-hi"
            >
              ↻ New rep
            </button>
          </div>

          {status === "graded" && grade && <GradeView grade={grade} />}
        </div>
      )}
    </main>
  );
}

function GradeView({ grade }: { grade: RepGrade }) {
  const cleared = grade.passed;
  return (
    <div className="mt-4 space-y-2.5 border-t border-edge/60 pt-4">
      <div
        className={`flex items-center justify-between rounded-md border px-3 py-2 ${
          cleared ? "border-accent/40 bg-accent/10" : "border-warn/40 bg-warn/10"
        }`}
      >
        <span className={`text-sm font-medium ${cleared ? "text-accent" : "text-warn"}`}>
          {cleared ? "Cleared — you hit the target" : "Not there yet"}
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

      {grade.evidence && (
        <p className="text-xs leading-relaxed text-dim">{grade.evidence}</p>
      )}
    </div>
  );
}
