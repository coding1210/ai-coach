"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import Chat from "@/components/Chat";
import DueNudge from "@/components/DueNudge";
import Onboarding from "@/components/Onboarding";
import ReportPanel from "@/components/ReportPanel";
import RestoreProgress from "@/components/RestoreProgress";
import { diagnoseCode } from "@/lib/api";
import type { Profile, Report } from "@/lib/types";
import { useCoachSession } from "@/lib/useCoachSession";
import { useVoice } from "@/lib/useVoice";

export default function Home() {
  const voice = useVoice();
  const { status, messages, report, phase, error, notice, start, send, finish } =
    useCoachSession({ onAssistantDone: voice.say });

  const [codeReport, setCodeReport] = useState<Report | null>(null);
  const [diagnosing, setDiagnosing] = useState(false);
  const [codeError, setCodeError] = useState<string | null>(null);

  const started = status !== "idle";

  // Hands-free: when the coach finishes speaking, auto-open the mic for the reply.
  const prevSpeaking = useRef(false);
  useEffect(() => {
    const finished = prevSpeaking.current && !voice.speaking;
    prevSpeaking.current = voice.speaking;
    const inputPhase = ["assess", "coach", "interview"].includes(phase);
    if (
      finished &&
      voice.handsFree &&
      started &&
      inputPhase &&
      voice.sttSupported &&
      !voice.listening &&
      status !== "thinking"
    ) {
      voice.listen(send);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [voice.speaking, voice.handsFree, phase, status, started]);

  async function handleDiagnose(payload: {
    source: "paste" | "github";
    content?: string;
    url?: string;
    role?: string | null;
    profile: Profile;
  }) {
    setDiagnosing(true);
    setCodeError(null);
    try {
      const r = await diagnoseCode(payload);
      setCodeReport(r);
    } catch (e) {
      setCodeError(e instanceof Error ? e.message : "Diagnosis failed.");
    } finally {
      setDiagnosing(false);
    }
  }

  // Toggling voice on reads the message currently on screen (so the coach
  // "speaks" from where you are, including the opening greeting/question).
  const toggleVoice = () => {
    const enabling = !voice.enabled;
    voice.toggleEnabled();
    if (enabling) {
      const last = [...messages].reverse().find((m) => m.role === "assistant");
      if (last?.content) voice.speakNow(last.content);
    }
  };

  return (
    <main className="mx-auto min-h-[100dvh] w-full max-w-6xl px-5 py-8 sm:px-8 sm:py-11">
      <header className="mb-9 flex items-end justify-between gap-4">
        <div className="animate-fade-in">
          <div className="mb-2.5 flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-accent shadow-accent" />
            <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-dim">
              Diagnostic session
            </span>
          </div>
          <h1 className="text-[2rem] font-semibold leading-[1.04] tracking-[-0.02em] text-hi sm:text-[2.6rem]">
            AI Coach <span className="text-faint">/</span> Gen&nbsp;AI Engineer
          </h1>
          <p className="mt-3 max-w-xl text-[0.95rem] leading-relaxed text-dim text-pretty">
            Diagnoses where you actually are, tells you the truth about your
            gaps, and coaches you forward.
          </p>
        </div>
        <div className="hidden shrink-0 items-center gap-2 sm:flex">
          <Link
            href="/map"
            className="group flex items-center gap-2 rounded-md border border-edge px-3.5 py-2 text-xs font-medium text-mid transition-[transform,border-color,color] duration-200 ease-out-quart hover:border-edge-strong hover:text-hi active:scale-[0.98]"
          >
            The field
          </Link>
          <Link
            href="/progress"
            className="group flex items-center gap-2 rounded-md border border-edge px-3.5 py-2 text-xs font-medium text-mid transition-[transform,border-color,color] duration-200 ease-out-quart hover:border-edge-strong hover:text-hi active:scale-[0.98]"
          >
            Progress
            <span className="text-accent transition-transform duration-200 ease-out-quart group-hover:translate-x-0.5">
              →
            </span>
          </Link>
        </div>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/[0.07] px-4 py-2.5 text-sm text-red-300">
          {error}
        </div>
      )}

      {notice && (
        <div className="mx-auto mb-6 flex max-w-2xl items-start gap-2 rounded-lg border border-warn/40 bg-warn/10 px-4 py-2.5 text-sm text-warn">
          <span aria-hidden="true">⚠</span>
          <span>{notice}</span>
        </div>
      )}

      {codeError && (
        <div className="mx-auto mb-6 max-w-2xl rounded-lg border border-red-500/30 bg-red-500/[0.07] px-4 py-2.5 text-sm text-red-300">
          {codeError}
        </div>
      )}

      {codeReport ? (
        <div className="mx-auto max-w-2xl space-y-4">
          <button
            onClick={() => setCodeReport(null)}
            className="text-xs text-dim transition-colors hover:text-hi"
          >
            ← New diagnosis
          </button>
          <Panel scroll>
            <ReportPanel report={codeReport} shareable />
          </Panel>
        </div>
      ) : !started ? (
        <div className="mx-auto max-w-lg space-y-4">
          <DueNudge onRecheck={() => start({ goal: "re-check my gaps", background: "returning learner", target_role: "" }, "coach")} />
          <Onboarding onStart={start} onDiagnoseCode={handleDiagnose} diagnosing={diagnosing} />
          <RestoreProgress />
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[1.15fr_1fr]">
          <Panel>
            <Chat
              messages={messages}
              status={status}
              phase={phase}
              onSend={send}
              onFinish={finish}
              voice={{
                enabled: voice.enabled,
                toggle: toggleVoice,
                handsFree: voice.handsFree,
                toggleHandsFree: voice.toggleHandsFree,
                listening: voice.listening,
                onMic: () => voice.listen(send),
                sttSupported: voice.sttSupported,
                ttsEngine: voice.ttsEngine,
              }}
            />
          </Panel>

          <Panel scroll>
            {report ? (
              <ReportPanel report={report} speaking={voice.speaking} shareable />
            ) : (
              <EmptyReport speaking={voice.speaking} />
            )}
          </Panel>
        </div>
      )}
    </main>
  );
}

/** Double-bezel enclosure: outer shell + inner core with concentric radii. */
function Panel({
  children,
  scroll,
}: {
  children: React.ReactNode;
  scroll?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-edge/70 bg-white/[0.015] p-1.5 shadow-panel">
      <div
        className={`h-[74dvh] rounded-[13px] border border-edge/60 bg-panel ${
          scroll ? "scroll-thin overflow-y-auto p-5" : "overflow-hidden"
        }`}
      >
        {children}
      </div>
    </div>
  );
}

function EmptyReport({ speaking }: { speaking?: boolean }) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <svg
        viewBox="0 0 96 96"
        className={`h-20 w-20 opacity-70 ${speaking ? "signal-speaking" : ""}`}
        aria-hidden="true"
      >
        <path d="M48 10 86 48 48 86 10 48Z" fill="none" stroke="#262a32" strokeWidth="1.5" />
        <path d="M48 26 70 48 48 70 26 48Z" fill="none" stroke="#262a32" strokeWidth="1.5" />
        <path
          d="M48 40 56 48 48 56 40 48Z"
          fill="rgba(200,241,105,0.12)"
          stroke="#c8f169"
          strokeWidth="1.75"
          strokeLinejoin="round"
        />
      </svg>
      <p className="mt-5 font-mono text-[11px] uppercase tracking-[0.2em] text-faint">
        {speaking ? "Coach speaking…" : "Awaiting signal"}
      </p>
      <p className="mt-2 max-w-xs text-sm leading-relaxed text-dim text-pretty">
        Your evaluation — strengths, gaps, and a current-vs-target radar — builds
        here once the coach has probed enough of what matters most.
      </p>
    </div>
  );
}
