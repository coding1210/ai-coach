"use client";

import { useEffect, useState } from "react";
import { fetchDue } from "@/lib/api";
import type { DueItem } from "@/lib/types";

/** Spaced re-assessment nudge: if the coach has weak spots due for a re-check,
 *  surface them with a one-click "re-check now". Silent when nothing's due. */
export default function DueNudge({ onRecheck }: { onRecheck: () => void }) {
  const [due, setDue] = useState<DueItem[]>([]);

  useEffect(() => {
    fetchDue()
      .then((d) => setDue(d))
      .catch(() => {});
  }, []);

  if (due.length === 0) return null;

  const top = due[0];
  const days = top.days_overdue;
  const when = days <= 0 ? "now" : `${days} day${days === 1 ? "" : "s"} ago`;

  return (
    <div className="animate-fade-in rounded-xl border border-accent/40 bg-accent/[0.06] p-4">
      <div className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-accent shadow-accent" />
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
          Due for a re-check
        </span>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-mid">
        {when === "now" ? "Time to revisit" : `${when} `}
        <span className="font-medium text-hi">{top.competency_name}</span>
        {top.still_weak ? " was shaky" : " is due"}
        {due.length > 1 && (
          <span className="text-dim">
            {" "}
            (+{due.length - 1} more)
          </span>
        )}
        . A 60-second re-check keeps your growth honest.
      </p>
      <button
        onClick={onRecheck}
        className="group mt-3 flex items-center gap-1.5 text-xs font-medium text-accent transition-colors hover:text-hi"
      >
        Re-check now
        <span className="transition-transform duration-200 ease-out-quart group-hover:translate-x-0.5">
          →
        </span>
      </button>
    </div>
  );
}
