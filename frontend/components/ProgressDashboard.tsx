"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { HTTP_BASE, ensureSession } from "@/lib/api";
import type { Report } from "@/lib/types";
import RadarChart from "./RadarChart";

interface ProgressEntry {
  competency_id: string;
  competency_name: string;
  domain_name: string;
  baseline_level: number | null;
  current_level: number | null;
  target_level: number | null;
  growth: number | null;
}

// baseline (faint) → current (accent) → target (marker), on the L1–L5 scale.
function TrackBar({ e }: { e: ProgressEntry }) {
  const cur = e.current_level ?? 0;
  const base = e.baseline_level ?? cur;
  const tgt = e.target_level ?? 5;
  return (
    <div className="relative mt-2 h-1.5 w-full rounded-full bg-edge">
      <div
        className="absolute h-full rounded-full bg-dim/50"
        style={{ width: `${(base / 5) * 100}%` }}
      />
      <div
        className="absolute h-full rounded-full bg-accent"
        style={{ width: `${(cur / 5) * 100}%` }}
      />
      <div
        className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 rounded-full bg-hi/70"
        style={{ left: `${(tgt / 5) * 100}%` }}
        title={`Target L${tgt}`}
      />
    </div>
  );
}

export default function ProgressDashboard() {
  const [entries, setEntries] = useState<ProgressEntry[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { token } = await ensureSession();
        const headers = { Authorization: `Bearer ${token}` };
        const [p, r] = await Promise.all([
          fetch(`${HTTP_BASE}/progress`, { headers }).then((x) => (x.ok ? x.json() : { entries: [] })),
          fetch(`${HTTP_BASE}/report`, { headers }).then((x) => (x.ok ? x.json() : null)),
        ]);
        setEntries(p.entries ?? []);
        setReport(r);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const totalGrowth = entries.reduce((s, e) => s + (e.growth ?? 0), 0);
  const atTarget = entries.filter(
    (e) => (e.current_level ?? 0) >= (e.target_level ?? 5)
  ).length;

  if (loading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-16 animate-pulse rounded-xl border border-edge/60 bg-raised"
          />
        ))}
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="animate-rise-in rounded-2xl border border-edge/70 bg-white/[0.015] p-1.5 shadow-panel">
        <div className="rounded-[13px] border border-edge/60 bg-panel p-10 text-center">
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
            No baseline yet
          </span>
          <p className="mx-auto mt-3 max-w-xs text-sm leading-relaxed text-dim text-pretty">
            Do an assessment first — your coach records a baseline you can grow
            from.
          </p>
          <Link
            href="/"
            className="group mt-5 inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-accent-ink transition-[transform,box-shadow] duration-200 ease-out-quart hover:shadow-accent active:scale-[0.98]"
          >
            Start an assessment
            <span className="grid h-5 w-5 place-items-center rounded-full bg-accent-ink/15 transition-transform duration-200 ease-out-quart group-hover:translate-x-0.5">
              →
            </span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-3">
        <Stat label="Tracked" value={entries.length} />
        <Stat label="At / above target" value={`${atTarget}/${entries.length}`} />
        <Stat label="Growth (levels)" value={`+${totalGrowth}`} accent={totalGrowth > 0} />
      </div>

      {report && report.radar.length >= 3 && (
        <div className="flex justify-center rounded-2xl border border-edge/70 bg-white/[0.015] p-1.5 shadow-panel">
          <div className="flex w-full justify-center rounded-[13px] border border-edge/60 bg-ink/40 p-4">
            <RadarChart radar={report.radar} />
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-edge/70 bg-white/[0.015] p-1.5 shadow-panel">
        <div className="rounded-[13px] border border-edge/60 bg-panel p-4">
          <div className="mb-3.5 flex items-center justify-between">
            <h2 className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
              Proficiency ledger
            </h2>
            <span className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.12em] text-faint">
              <Legend swatch="bg-dim/50" label="baseline" />
              <Legend swatch="bg-accent" label="current" />
              <Legend swatch="bg-hi/70" label="target" />
            </span>
          </div>
          <ul className="space-y-2.5">
            {entries.map((e) => (
              <li
                key={e.competency_id}
                className="rounded-md border border-edge/50 bg-raised px-3 py-2.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-hi">
                    {e.competency_name}
                  </span>
                  <span className="nums whitespace-nowrap font-mono text-[11px] text-dim">
                    L{e.baseline_level}
                    <span className="text-faint"> → </span>L{e.current_level}
                    <span className="text-faint"> / </span>L{e.target_level}
                    {e.growth !== null && e.growth > 0 && (
                      <span className="ml-1.5 text-accent">▲ {e.growth}</span>
                    )}
                  </span>
                </div>
                <TrackBar e={e} />
                <span className="mt-1.5 block font-mono text-[10px] uppercase tracking-[0.12em] text-faint">
                  {e.domain_name}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: boolean;
}) {
  return (
    <div className="rounded-xl border border-edge/60 bg-raised px-4 py-3.5 text-center">
      <div
        className={`nums text-2xl font-semibold tracking-tight ${
          accent ? "text-accent" : "text-hi"
        }`}
      >
        {value}
      </div>
      <div className="mt-1 font-mono text-[9.5px] uppercase tracking-[0.14em] text-dim">
        {label}
      </div>
    </div>
  );
}

function Legend({ swatch, label }: { swatch: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={`h-1.5 w-1.5 rounded-full ${swatch}`} />
      {label}
    </span>
  );
}
