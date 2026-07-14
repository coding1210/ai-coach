import type { CompetencyEntry, Report } from "@/lib/types";
import RadarChart from "./RadarChart";

function LevelBar({ current, target }: { current: number; target: number }) {
  return (
    <div className="mt-2 h-1.5 w-full overflow-visible rounded-full bg-edge">
      <div className="relative h-full">
        <div
          className="absolute h-full rounded-full bg-accent"
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
      <LevelBar current={c.current_level} target={c.target_level} />
      {c.evidence && (
        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-dim">
          {c.evidence}
        </p>
      )}
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

export default function ReportPanel({ report }: { report: Report }) {
  return (
    <div className="space-y-7">
      <div>
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
          Evaluation
        </span>
        <h2 className="mt-1 text-lg font-semibold tracking-[-0.01em] text-hi">
          Where you stand
        </h2>
        <p className="nums mt-1 text-xs text-dim">
          {report.competencies_assessed} competencies assessed · current
          <span className="mx-1 inline-block h-2 w-2 translate-y-[1px] rounded-full bg-accent" />
          vs target
          <span className="mx-1 inline-block h-2 w-2 translate-y-[1px] rounded-full border border-hi/60" />
        </p>
      </div>

      <div className="flex justify-center rounded-xl border border-edge/60 bg-ink/40 p-4">
        <RadarChart radar={report.radar} />
      </div>

      {report.weaknesses.length > 0 && (
        <section>
          <SectionLabel tone="warn">Focus areas · gap × weight</SectionLabel>
          <ul className="space-y-2">
            {report.weaknesses.slice(0, 5).map((c) => (
              <CompetencyRow key={c.competency_id} c={c} showGap />
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
    </div>
  );
}
