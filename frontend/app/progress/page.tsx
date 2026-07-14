import Link from "next/link";
import ProgressDashboard from "@/components/ProgressDashboard";

export default function ProgressPage() {
  return (
    <main className="mx-auto min-h-[100dvh] w-full max-w-3xl px-5 py-8 sm:px-8 sm:py-11">
      <header className="mb-8 animate-fade-in">
        <Link
          href="/"
          className="group inline-flex items-center gap-1.5 text-xs font-medium text-dim transition-colors duration-200 hover:text-mid"
        >
          <span className="transition-transform duration-200 ease-out-quart group-hover:-translate-x-0.5">
            ←
          </span>
          Back to coach
        </Link>
        <div className="mt-4 mb-2.5 flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-accent shadow-accent" />
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-dim">
            Progress ledger
          </span>
        </div>
        <h1 className="text-3xl font-semibold tracking-[-0.02em] text-hi">
          Your progress
        </h1>
        <p className="mt-2.5 max-w-xl text-sm leading-relaxed text-dim text-pretty">
          Growth means movement on <em className="text-mid not-italic">your</em>{" "}
          weak areas over time — not a course completed. Baseline is set on first
          assessment; re-assess to see the delta.
        </p>
      </header>
      <ProgressDashboard />
    </main>
  );
}
