"use client";

import { useState } from "react";
import { fetchExercise, gradeSubmission } from "@/lib/api";
import type { Exercise, GradeResult, RoadmapMilestone } from "@/lib/types";

type Status = "idle" | "loading" | "ready" | "grading" | "done" | "error";

export default function ChallengePanel({
  milestone,
  onGraded,
}: {
  milestone: RoadmapMilestone;
  onGraded: (level: number) => void;
}) {
  const [status, setStatus] = useState<Status>("idle");
  const [exercise, setExercise] = useState<Exercise | null>(null);
  const [code, setCode] = useState("");
  const [result, setResult] = useState<GradeResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  async function open() {
    setStatus("loading");
    try {
      const ex = await fetchExercise(milestone.competency_id);
      setExercise(ex);
      setStatus("ready");
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Could not load the challenge.");
      setStatus("error");
    }
  }

  async function submit() {
    if (!code.trim()) return;
    setStatus("grading");
    try {
      const r = await gradeSubmission(milestone.competency_id, code);
      setResult(r);
      setStatus("done");
      onGraded(r.level);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Grading failed.");
      setStatus("error");
    }
  }

  if (status === "idle") {
    return (
      <button
        onClick={open}
        className="group mt-2.5 flex items-center gap-1.5 rounded-md border border-accent/40 bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent transition-[transform,background-color] duration-200 ease-out-quart hover:bg-accent/15 active:scale-[0.98]"
      >
        Try the graded challenge
        <span className="transition-transform duration-200 ease-out-quart group-hover:translate-x-0.5">
          →
        </span>
      </button>
    );
  }

  return (
    <div className="mt-2.5 rounded-md border border-edge/70 bg-ink/50 p-3">
      {status === "loading" && (
        <p className="text-xs text-dim">Loading challenge…</p>
      )}

      {status === "error" && (
        <div className="space-y-2">
          <p className="text-xs text-warn">{errorMsg}</p>
          <button
            onClick={() => setStatus(exercise ? "ready" : "idle")}
            className="text-xs text-dim hover:text-hi"
          >
            ← Back
          </button>
        </div>
      )}

      {exercise && (status === "ready" || status === "grading") && (
        <div className="space-y-2.5">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-accent">
              Challenge · {exercise.language}
            </p>
            <p className="mt-1 text-sm font-medium text-hi">{exercise.title}</p>
            <p className="mt-1 whitespace-pre-wrap text-xs leading-relaxed text-dim">
              {exercise.prompt}
            </p>
          </div>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            disabled={status === "grading"}
            spellCheck={false}
            rows={8}
            placeholder={`# your ${exercise.language} here`}
            className="w-full resize-y rounded-md border border-edge bg-black/40 p-2.5 font-mono text-[12px] leading-relaxed text-hi outline-none transition-colors focus:border-accent/60 disabled:opacity-60"
          />
          <div className="flex items-center gap-3">
            <button
              onClick={submit}
              disabled={status === "grading" || !code.trim()}
              className="rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-accent-ink transition-[transform] duration-200 ease-out-quart active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {status === "grading" ? "Grading…" : "Submit for grading"}
            </button>
            {status === "ready" && (
              <button
                onClick={() => setStatus("idle")}
                className="text-xs text-dim hover:text-hi"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      )}

      {status === "done" && result && (
        <GradeResultView
          result={result}
          onRetry={() => setStatus("ready")}
        />
      )}
    </div>
  );
}

function GradeResultView({
  result,
  onRetry,
}: {
  result: GradeResult;
  onRetry: () => void;
}) {
  const cleared = result.level >= result.target_level;
  return (
    <div className="space-y-2.5">
      <div
        className={`flex items-center justify-between rounded-md border px-3 py-2 ${
          cleared
            ? "border-accent/40 bg-accent/10"
            : "border-edge-strong bg-raised"
        }`}
      >
        <span className="text-sm font-medium text-hi">
          {cleared ? "Cleared — you hit the target" : "Graded"}
        </span>
        <span className="nums font-mono text-[11px] text-dim">
          scored L{result.level}
          <span className="text-faint"> · target </span>L{result.target_level}
        </span>
      </div>

      {result.execution && result.execution.ran && (
        <p
          className={`font-mono text-[11px] ${
            result.execution.passed ? "text-accent" : "text-warn"
          }`}
        >
          {result.execution.passed
            ? "▸ ran in sandbox — tests passed"
            : `▸ ran in sandbox — tests failed${result.execution.error ? `: ${result.execution.error}` : ""}`}
        </p>
      )}

      <ul className="space-y-1">
        {result.checks.map((c) => (
          <li
            key={c.id}
            className="flex items-start gap-1.5 text-xs leading-relaxed text-mid"
          >
            <span
              className={`mt-0.5 shrink-0 font-mono ${
                c.passed ? "text-accent" : "text-warn"
              }`}
            >
              {c.passed ? "✓" : "✕"}
            </span>
            <span className={c.passed ? "text-mid" : "text-dim"}>
              {c.description}
            </span>
          </li>
        ))}
      </ul>

      {result.evidence && (
        <p className="border-t border-edge/50 pt-2 text-xs leading-relaxed text-dim">
          {result.evidence}
        </p>
      )}

      <button
        onClick={onRetry}
        className="text-xs text-accent hover:text-hi"
      >
        ↻ Revise & resubmit
      </button>
    </div>
  );
}
