"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchMap, fetchProgress, ensureSession } from "@/lib/api";
import { glossForDomain } from "@/lib/glossary";
import type { FieldDomain, LedgerEntry } from "@/lib/types";

const WEIGHT_LABEL: Record<string, string> = {
  critical: "core",
  high: "high",
  "medium-high": "useful",
  medium: "useful",
  "low-medium": "later",
};

export default function FieldMap() {
  const [domains, setDomains] = useState<FieldDomain[]>([]);
  const [levels, setLevels] = useState<Record<string, number>>({});
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    fetchMap()
      .then(setDomains)
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  // Average current level per domain from the user's ledger → "you are here".
  // Runs once domains load so we can map each competency to its domain.
  useEffect(() => {
    if (!domains.length) return;
    (async () => {
      try {
        const { token } = await ensureSession();
        const entries: LedgerEntry[] = await fetchProgress(token);
        const cidToDomain: Record<string, string> = {};
        domains.forEach((d) => d.competencies.forEach((c) => (cidToDomain[c.id] = d.id)));
        const acc: Record<string, number[]> = {};
        entries.forEach((e) => {
          const did = cidToDomain[e.competency_id];
          if (did && e.current_level != null) (acc[did] ||= []).push(e.current_level);
        });
        const avg: Record<string, number> = {};
        Object.entries(acc).forEach(([did, xs]) => {
          avg[did] = Math.round((xs.reduce((a, b) => a + b, 0) / xs.length) * 10) / 10;
        });
        setLevels(avg);
      } catch {
        /* ignore */
      }
    })();
  }, [domains]);

  return (
    <main className="mx-auto min-h-[100dvh] w-full max-w-3xl px-5 py-10 sm:px-8">
      <header className="mb-8 flex items-end justify-between gap-4">
        <div>
          <div className="mb-2.5 flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-accent shadow-accent" />
            <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-dim">
              The field at a glance
            </span>
          </div>
          <h1 className="text-2xl font-semibold tracking-[-0.02em] text-hi sm:text-3xl">
            What a Gen AI engineer knows
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-dim text-pretty">
            The whole territory in one view — the areas the field is built on. You
            don&apos;t need all of it at once; your plan picks where to start.
            {loaded && Object.keys(levels).length > 0 && (
              <> The green marks show roughly where you are today.</>
            )}
          </p>
        </div>
        <Link
          href="/"
          className="hidden shrink-0 rounded-md border border-edge px-3.5 py-2 text-xs font-medium text-mid transition-colors hover:border-edge-strong hover:text-hi sm:block"
        >
          ← Back
        </Link>
      </header>

      <div className="space-y-3">
        {domains.map((d) => {
          const you = levels[d.id];
          return (
            <div key={d.id} className="rounded-xl border border-edge/70 bg-panel p-4">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-base font-semibold text-hi">{d.name}</h2>
                <div className="flex items-center gap-2">
                  {you != null && (
                    <span className="nums rounded-md border border-accent/40 bg-accent/10 px-2 py-0.5 font-mono text-[10px] text-accent">
                      you ~L{you}
                    </span>
                  )}
                  <span className="rounded-md border border-edge bg-ink/50 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] text-dim">
                    {WEIGHT_LABEL[d.weight] ?? d.weight}
                  </span>
                </div>
              </div>
              <p className="mt-1.5 text-sm leading-relaxed text-mid">
                {glossForDomain(d.id) ?? ""}
              </p>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {d.competencies.map((c) => (
                  <span
                    key={c.id}
                    className="rounded border border-edge/70 px-2 py-0.5 text-[11px] text-faint"
                  >
                    {c.name}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </main>
  );
}
