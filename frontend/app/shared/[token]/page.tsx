"use client";

import { use, useEffect, useState } from "react";
import ReportPanel from "@/components/ReportPanel";
import { fetchShared } from "@/lib/api";
import type { Report } from "@/lib/types";

export default function SharedReport({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);
  const [report, setReport] = useState<Report | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "missing">("loading");

  useEffect(() => {
    fetchShared(token)
      .then((snap) => {
        if (snap?.report) {
          setReport(snap.report);
          setState("ok");
        } else {
          setState("missing");
        }
      })
      .catch(() => setState("missing"));
  }, [token]);

  return (
    <main className="mx-auto min-h-[100dvh] w-full max-w-2xl px-5 py-10 sm:px-8">
      <header className="mb-8">
        <div className="mb-2.5 flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-accent shadow-accent" />
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-dim">
            Shared growth report
          </span>
        </div>
        <h1 className="text-2xl font-semibold tracking-[-0.02em] text-hi">
          AI Coach <span className="text-faint">/</span> Gen&nbsp;AI Engineer
        </h1>
        <p className="mt-2 text-sm text-dim">A read-only snapshot shared by the learner.</p>
      </header>

      {state === "loading" && (
        <p className="text-sm text-dim">Loading…</p>
      )}
      {state === "missing" && (
        <div className="rounded-lg border border-edge/70 bg-panel p-6 text-sm text-dim">
          This shared report is unavailable — the link may be invalid or the demo backend restarted.
        </div>
      )}
      {state === "ok" && report && (
        <div className="rounded-2xl border border-edge/70 bg-white/[0.015] p-1.5 shadow-panel">
          <div className="scroll-thin max-h-[84dvh] overflow-y-auto rounded-[13px] border border-edge/60 bg-panel p-5">
            <ReportPanel report={report} />
          </div>
        </div>
      )}
    </main>
  );
}
