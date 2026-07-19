"use client";

import { useState } from "react";
import { createShare } from "@/lib/api";
import { glossForCompetency, glossForDomain } from "@/lib/glossary";
import type { CompetencyEntry, Report, RoadmapMilestone } from "@/lib/types";
import ChallengePanel from "./ChallengePanel";
import RadarChart from "./RadarChart";

function ShareButton() {
  const [state, setState] = useState<"idle" | "creating" | "done" | "error">("idle");
  const [url, setUrl] = useState("");
  async function share() {
    setState("creating");
    try {
      const token = await createShare();
      const link = `${window.location.origin}/shared/${token}`;
      setUrl(link);
      setState("done");
      try {
        await navigator.clipboard.writeText(link);
      } catch {
        /* clipboard may be blocked; link is shown regardless */
      }
    } catch {
      setState("error");
    }
  }
  if (state === "done") {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="shrink-0 rounded-md border border-accent/40 bg-accent/10 px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-accent"
        title="Copied — opens the read-only shared report"
      >
        Link copied ↗
      </a>
    );
  }
  return (
    <button
      onClick={share}
      disabled={state === "creating"}
      className="shrink-0 rounded-md border border-edge px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-dim transition-colors hover:border-accent/50 hover:text-accent disabled:opacity-40"
    >
      {state === "creating" ? "Sharing…" : state === "error" ? "Try again" : "Share growth"}
    </button>
  );
}

function SaveProgress() {
  const [code, setCode] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  function reveal() {
    try {
      const s = JSON.parse(localStorage.getItem("coach_session") || "{}");
      if (s.token) {
        setCode(s.token);
        navigator.clipboard?.writeText(s.token).then(
          () => setCopied(true),
          () => {}
        );
      }
    } catch {
      /* no session yet */
    }
  }
  return (
    <div className="rounded-xl border border-edge/60 bg-ink/40 p-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
        Your progress is saved
      </p>
      <p className="mt-1.5 text-xs leading-relaxed text-dim">
        Keep this recovery code to pick up on another device or after clearing your
        browser. It&apos;s the key to your baseline, plan, and growth.
      </p>
      {code ? (
        <div className="mt-2.5">
          <code className="block break-all rounded-md border border-edge bg-black/40 px-2.5 py-1.5 font-mono text-[11px] text-hi">
            {code}
          </code>
          <p className="mt-1 text-[11px] text-accent">
            {copied ? "Copied to clipboard — store it somewhere safe." : "Copy and store it somewhere safe."}
          </p>
        </div>
      ) : (
        <button
          onClick={reveal}
          className="mt-2.5 rounded-md border border-edge px-3 py-1.5 text-xs font-medium text-mid transition-colors hover:border-accent/50 hover:text-accent"
        >
          Reveal my recovery code
        </button>
      )}
    </div>
  );
}

function WinsSection({ growth }: { growth: NonNullable<Report["growth"]> }) {
  return (
    <section>
      <SectionLabel tone="accent">What you&apos;ve gained since last time</SectionLabel>
      <ul className="space-y-2">
        {growth.improved.map((g) => (
          <li
            key={g.competency_name}
            className="flex items-center justify-between gap-2 rounded-md border border-accent/30 bg-accent/[0.06] px-3 py-2"
          >
            <span className="text-sm font-medium text-hi">{g.competency_name}</span>
            <span className="nums whitespace-nowrap font-mono text-[11px] text-accent">
              L{g.from} → L{g.to} ↑
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function LevelBar({ current, target }: { current: number; target: number }) {
  return (
    <div className="mt-2 h-1.5 w-full overflow-visible rounded-full bg-edge">
      <div className="relative h-full">
        <div
          className="bar-fill absolute h-full rounded-full bg-accent"
          style={{ width: `${(current / 5) * 100}%` }}
        />
        <div
          className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 rounded-full bg-hi/70"
          style={{ left: `${(target / 5) * 100}%` }}
          title={`Target L${target}`}
        />
      </div>
    </div>
  );
}

function CompetencyRow({ c, showGap }: { c: CompetencyEntry; showGap?: boolean }) {
  const gloss = glossForCompetency(c.competency_id);
  return (
    <li className="rounded-md border border-edge/60 bg-raised px-3 py-2.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-hi">{c.competency_name}</span>
        <span className="nums whitespace-nowrap font-mono text-[11px] text-dim">
          L{c.current_level}
          <span className="text-faint"> → </span>L{c.target_level}
          {showGap && c.gap > 0 && (
            <span className="ml-1.5 text-warn">gap {c.gap}</span>
          )}
        </span>
      </div>
      {gloss && <p className="mt-0.5 text-[11px] leading-snug text-faint">{gloss}</p>}
      <LevelBar current={c.current_level} target={c.target_level} />
      {c.evidence && (
        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-dim">
          {c.evidence}
        </p>
      )}
    </li>
  );
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const positive = verdict === "Strong hire" || verdict === "Lean hire";
  const negative = verdict === "Not yet";
  const cls = positive
    ? "border-accent/40 bg-accent/10 text-accent"
    : negative
      ? "border-warn/40 bg-warn/10 text-warn"
      : "border-edge-strong bg-ink/50 text-mid";
  return (
    <span
      className={`shrink-0 rounded-md border px-2.5 py-1 font-mono text-[10px] font-medium uppercase tracking-[0.14em] ${cls}`}
    >
      {verdict}
    </span>
  );
}

function MilestoneCard({ m }: { m: RoadmapMilestone }) {
  const [achieved, setAchieved] = useState<number | null>(null);
  const gloss = glossForCompetency(m.competency_id);
  return (
    <li className="rounded-md border border-edge/60 bg-raised px-3 py-3">
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-accent/15 font-mono text-[11px] font-semibold text-accent">
          {m.rank}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-hi">{m.competency_name}</span>
            <span className="nums whitespace-nowrap font-mono text-[11px] text-dim">
              L{m.from_level}
              <span className="text-faint"> → </span>L{m.target_level}
              {achieved !== null && (
                <span
                  className={
                    achieved >= m.target_level ? "text-accent" : "text-mid"
                  }
                >
                  {" "}
                  · now L{achieved}
                </span>
              )}
            </span>
          </div>
          {gloss && <p className="mt-0.5 text-[11px] leading-snug text-faint">{gloss}</p>}
          <p className="mt-1.5 text-[11px] text-faint">{m.why}</p>

          {m.effort && (
            <span className="mt-2 inline-flex items-center gap-1 rounded-md border border-edge bg-ink/50 px-2 py-0.5 font-mono text-[10px] text-mid">
              ⏱ {m.effort}
            </span>
          )}

          <p className="mt-2 text-xs leading-relaxed text-dim">
            <span className="text-mid">What good looks like: </span>
            {m.focus}
          </p>

          <ul className="mt-2 space-y-1">
            {m.practice.map((p, i) => (
              <li key={i} className="flex gap-1.5 text-xs leading-relaxed text-mid">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" />
                <span>{p}</span>
              </li>
            ))}
          </ul>

          <p className="mt-2 border-t border-edge/50 pt-2 text-xs leading-relaxed text-dim">
            <span className="text-accent">Signal · </span>
            {m.signal}
          </p>

          {m.resources && m.resources.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
              {m.resources.map((r) => (
                <a
                  key={r.url}
                  href={r.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] text-dim underline decoration-edge-strong underline-offset-2 transition-colors hover:text-accent"
                >
                  {r.title} ↗
                </a>
              ))}
            </div>
          )}

          {m.has_exercise && (
            <ChallengePanel milestone={m} onGraded={setAchieved} />
          )}
        </div>
      </div>
    </li>
  );
}

function BenchmarkBar({ b }: { b: import("@/lib/types").BenchmarkDomain }) {
  const tone =
    b.standing === "ahead of most"
      ? "text-accent"
      : b.standing === "behind most"
        ? "text-warn"
        : "text-mid";
  return (
    <li className="rounded-md border border-edge/60 bg-raised px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <span
          className="text-sm font-medium text-hi"
          title={glossForDomain(b.domain_id) || undefined}
        >
          {b.domain_name}
        </span>
        <span className={`font-mono text-[11px] ${tone}`}>{b.standing}</span>
      </div>
      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-edge">
        <div
          className="bar-fill h-full rounded-full bg-accent/70"
          style={{ width: `${b.percentile}%` }}
        />
      </div>
      <p className="nums mt-1 text-[11px] text-dim">
        {b.percentile}th percentile · you L{b.you} vs typical L{b.typical}
      </p>
    </li>
  );
}

function SectionLabel({ tone, children }: { tone: "warn" | "accent"; children: React.ReactNode }) {
  return (
    <h3
      className={`mb-2.5 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] ${
        tone === "warn" ? "text-warn" : "text-accent"
      }`}
    >
      <span className={`h-1 w-1 rounded-full ${tone === "warn" ? "bg-warn" : "bg-accent"}`} />
      {children}
    </h3>
  );
}

export default function ReportPanel({
  report,
  speaking,
  shareable,
}: {
  report: Report;
  speaking?: boolean;
  shareable?: boolean;
}) {
  const label = report.interview
    ? "Interview debrief"
    : report.source === "code"
      ? "Diagnosed from your code"
      : "Evaluation";
  // Reframe for someone at the very start: encouragement over percentiles.
  const early = !!report.early_stage && !report.interview;
  const firstStep = report.roadmap?.milestones?.[0]?.competency_name;
  return (
    <div className="report-reveal space-y-7">
      <div>
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
            {label}
            {speaking && (
              <span className="signal-speaking inline-block h-1.5 w-1.5 rounded-full bg-accent" />
            )}
          </span>
          {shareable && !report.interview && <ShareButton />}
        </div>
        <div className="mt-1 flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold tracking-[-0.01em] text-hi">
            Where you stand
          </h2>
          {report.verdict && <VerdictBadge verdict={report.verdict} />}
        </div>
        {report.role_title && (
          <p className="mt-1 text-xs text-accent">
            Targets set for: {report.role_title}
          </p>
        )}
        <p className="nums mt-1 text-xs text-dim">
          {report.competencies_assessed} competencies assessed · current
          <span className="mx-1 inline-block h-2 w-2 translate-y-[1px] rounded-full bg-accent" />
          vs target
          <span className="mx-1 inline-block h-2 w-2 translate-y-[1px] rounded-full border border-hi/60" />
        </p>
      </div>

      {early && (
        <div className="rounded-xl border border-accent/40 bg-accent/[0.06] p-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
            You&apos;re at the start — right where you should be
          </p>
          <p className="mt-2 text-sm leading-relaxed text-mid">
            Everyone starts here. You don&apos;t need to know everything — just the
            next thing.
            {firstStep && (
              <>
                {" "}
                Begin with <span className="font-medium text-hi">{firstStep}</span>;
                your growth path below breaks it into small, doable steps.
              </>
            )}
          </p>
        </div>
      )}

      {report.growth && report.growth.improved_count > 0 && (
        <WinsSection growth={report.growth} />
      )}

      <div className="flex justify-center rounded-xl border border-edge/60 bg-ink/40 p-4">
        <RadarChart radar={report.radar} />
      </div>

      {/* Peer benchmark can demotivate a beginner — hidden until they're past the start. */}
      {!early && report.benchmark && report.benchmark.length > 0 && (
        <section>
          <SectionLabel tone="accent">Benchmark · vs a typical Gen AI engineer</SectionLabel>
          <ul className="space-y-2">
            {report.benchmark.slice(0, 6).map((b) => (
              <BenchmarkBar key={b.domain_id} b={b} />
            ))}
          </ul>
        </section>
      )}

      {report.weaknesses.length > 0 && (
        <section>
          <SectionLabel tone="warn">
            {early ? "Where to start" : "Focus areas · gap × weight"}
          </SectionLabel>
          <ul className="space-y-2">
            {report.weaknesses.slice(0, 5).map((c) => (
              <CompetencyRow key={c.competency_id} c={c} showGap={!early} />
            ))}
          </ul>
        </section>
      )}

      {report.roadmap && report.roadmap.milestones.length > 0 && (
        <section>
          <SectionLabel tone="accent">
            Your growth path · {report.roadmap.horizon}
          </SectionLabel>
          <ul className="stagger-list space-y-2">
            {report.roadmap.milestones.map((m) => (
              <MilestoneCard key={m.competency_id} m={m} />
            ))}
          </ul>
        </section>
      )}

      {report.strengths.length > 0 && (
        <section>
          <SectionLabel tone="accent">Strengths · at or above target</SectionLabel>
          <ul className="space-y-2">
            {report.strengths.slice(0, 5).map((c) => (
              <CompetencyRow key={c.competency_id} c={c} />
            ))}
          </ul>
        </section>
      )}

      {shareable && !report.interview && <SaveProgress />}
    </div>
  );
}
