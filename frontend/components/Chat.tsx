"use client";

import { useEffect, useRef, useState } from "react";
import type { ChatMessage, SessionStatus } from "@/lib/types";

const PHASE_LABEL: Record<string, string> = {
  onboard: "Getting started",
  assess: "Assessing",
  report: "Building evaluation",
  coach: "Coaching",
  challenge: "Challenge",
  interview: "Interview",
  done: "Session complete",
};

export interface VoiceControls {
  enabled: boolean;
  toggle: () => void;
  handsFree: boolean;
  toggleHandsFree: () => void;
  listening: boolean;
  onMic: () => void;
  sttSupported: boolean;
  ttsEngine: string;
}

export default function Chat({
  messages,
  status,
  phase,
  onSend,
  onFinish,
  voice,
}: {
  messages: ChatMessage[];
  status: SessionStatus;
  phase: string;
  onSend: (content: string) => void;
  onFinish: () => void;
  voice: VoiceControls;
}) {
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  const canSend = status === "awaiting_input";
  const isChallenge = phase === "challenge";
  const submit = () => {
    if (!canSend || !draft.trim()) return;
    onSend(draft);
    setDraft("");
  };

  const placeholder = !canSend
    ? status === "done"
      ? "Session complete."
      : "…"
    : isChallenge
      ? "Paste your solution code… (Enter to submit)"
      : "Answer as you actually would on the job… (Enter to send)";

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-edge/70 px-4 py-3.5">
        <div>
          <div className="flex items-center gap-2">
            <span
              className={`h-1.5 w-1.5 rounded-full transition-colors duration-300 ${
                status === "thinking" ? "bg-accent" : "bg-edge-strong"
              }`}
            />
            <h1 className="text-sm font-semibold tracking-[-0.01em] text-hi">
              Your Gen AI Coach
            </h1>
          </div>
          <p className="mt-0.5 pl-3.5 text-xs text-faint">
            {phase === "interview"
              ? "mock interview — probing your depth for the role"
              : "coaching, not a course — diagnosing your gaps"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {phase === "interview" && <InterviewTimer minutes={15} />}
          <span className="rounded-md border border-edge bg-ink/50 px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-dim">
            {PHASE_LABEL[phase] ?? phase}
          </span>
          {voice.sttSupported && (
            <button
              onClick={voice.toggleHandsFree}
              aria-pressed={voice.handsFree}
              title={voice.handsFree ? "Hands-free on — mic opens after the coach speaks" : "Hands-free mode"}
              className={`grid h-8 w-8 place-items-center rounded-md border text-[11px] font-semibold transition-[transform,border-color,color,background-color] duration-200 ease-out-quart active:scale-95 ${
                voice.handsFree
                  ? "border-accent/40 bg-accent/10 text-accent"
                  : "border-edge text-dim hover:border-edge-strong hover:text-mid"
              }`}
            >
              HF
            </button>
          )}
          <button
            onClick={voice.toggle}
            aria-pressed={voice.enabled}
            title={
              voice.enabled
                ? `Voice on${voice.ttsEngine !== "none" ? ` · ${voice.ttsEngine}` : ""}`
                : "Enable voice"
            }
            className={`grid h-8 w-8 place-items-center rounded-md border transition-[transform,border-color,color,background-color] duration-200 ease-out-quart active:scale-95 ${
              voice.enabled
                ? "border-accent/40 bg-accent/10 text-accent"
                : "border-edge text-dim hover:border-edge-strong hover:text-mid"
            }`}
          >
            <SpeakerIcon on={voice.enabled} />
          </button>
        </div>
      </header>

      <div className="scroll-thin flex-1 space-y-3 overflow-y-auto px-4 py-5">
        {messages.map((m, i) => (
          <Bubble key={i} message={m} />
        ))}
        {status === "thinking" && <Thinking />}
        <div ref={endRef} />
      </div>

      <div className="border-t border-edge/70 p-3">
        {canSend &&
          (phase === "assess" || phase === "coach" || phase === "interview") && (
            <div className="mb-2 flex items-center justify-between gap-3">
              {phase !== "interview" ? (
                <button
                  onClick={() =>
                    onSend("Can you explain that in simple terms before I answer?")
                  }
                  title="Not sure what this means? The coach explains it plainly, then re-asks."
                  className="flex items-center gap-1.5 text-xs text-dim transition-colors duration-200 hover:text-accent"
                >
                  <span aria-hidden="true">💡</span> Explain this
                </button>
              ) : (
                <span />
              )}
              {(phase === "assess" || phase === "interview") && (
                <button
                  onClick={onFinish}
                  className="group flex items-center gap-1.5 text-xs text-dim transition-colors duration-200 hover:text-accent"
                >
                  {phase === "interview"
                    ? "Wrap up the interview & debrief"
                    : "Answered enough? See my evaluation"}
                  <span className="transition-transform duration-200 ease-out-quart group-hover:translate-x-0.5">
                    →
                  </span>
                </button>
              )}
            </div>
          )}
        <div className="flex items-end gap-2">
          {voice.enabled && voice.sttSupported && (
            <button
              onClick={voice.onMic}
              disabled={!canSend}
              title="Tap and speak your answer"
              className={`grid h-11 w-11 shrink-0 place-items-center rounded-md border transition-[transform,border-color,color] duration-200 ease-out-quart active:scale-95 ${
                voice.listening
                  ? "border-accent/50 bg-accent/10 text-accent"
                  : "border-edge text-dim enabled:hover:border-edge-strong enabled:hover:text-mid disabled:opacity-40"
              }`}
            >
              {voice.listening ? <RecordingDot /> : <MicIcon />}
            </button>
          )}
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={isChallenge ? 6 : 2}
            disabled={!canSend}
            placeholder={placeholder}
            className={`scroll-thin flex-1 resize-none rounded-md border border-edge bg-ink px-3.5 py-2.5 text-sm text-hi placeholder:text-faint outline-none transition-[border-color,box-shadow] duration-200 ease-out-quart focus:border-accent/70 focus:shadow-[0_0_0_3px_rgba(200,241,105,0.12)] disabled:opacity-50 ${
              isChallenge ? "font-mono text-[13px] leading-relaxed" : ""
            }`}
          />
          <button
            onClick={submit}
            disabled={!canSend || !draft.trim()}
            className="grid h-11 w-11 shrink-0 place-items-center rounded-md bg-accent text-accent-ink transition-[transform,box-shadow] duration-200 ease-out-quart hover:shadow-accent active:scale-95 disabled:opacity-30 disabled:shadow-none disabled:active:scale-100"
            aria-label="Send"
          >
            <SendIcon />
          </button>
        </div>
      </div>
    </div>
  );
}

function Bubble({ message }: { message: ChatMessage }) {
  if (message.role === "grade" && message.grade) {
    const g = message.grade;
    const passed = g.checks.filter((c) => c.passed).length;
    return (
      <div className="flex animate-rise-in justify-start">
        <div className="w-[85%] rounded-xl rounded-bl-sm border border-accent/25 bg-accent/[0.06] p-3.5">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
              Graded · behavioral
            </span>
            <span className="nums font-mono text-sm font-semibold text-accent">
              L{g.level}
              <span className="text-faint">/5</span>
            </span>
          </div>
          <ul className="mt-2.5 space-y-1">
            {g.checks.map((c) => (
              <li key={c.id} className="flex items-center gap-2 text-xs">
                <span className={c.passed ? "text-accent" : "text-faint"}>
                  {c.passed ? "✓" : "○"}
                </span>
                <span className={c.passed ? "text-mid" : "text-faint line-through"}>
                  {c.description}
                </span>
              </li>
            ))}
          </ul>
          <div className="mt-2.5 flex items-center gap-2">
            <div className="h-1 flex-1 rounded-full bg-edge">
              <div
                className="h-full rounded-full bg-accent"
                style={{ width: `${Math.round(g.deterministic_score * 100)}%` }}
              />
            </div>
            <span className="nums font-mono text-[10px] text-dim">
              {Math.round(g.deterministic_score * 100)}% objective
            </span>
          </div>
          {g.evidence && (
            <p className="mt-2.5 text-xs leading-relaxed text-dim">{g.evidence}</p>
          )}
        </div>
      </div>
    );
  }

  if (message.role === "tool" && message.tool) {
    const r = message.tool.result;
    return (
      <div className="flex animate-rise-in justify-start">
        <a
          href={r.url}
          target="_blank"
          rel="noreferrer"
          className="group inline-flex items-center gap-2 rounded-md border border-edge bg-ink/60 px-3 py-1.5 text-xs text-dim transition-[transform,border-color,color] duration-200 ease-out-quart hover:border-accent/50 hover:text-hi active:scale-[0.98]"
        >
          <LinkIcon />
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">
            resource
          </span>
          <span className="font-medium text-mid group-hover:text-hi">
            {r.title}
          </span>
          {r.source === "web_search" && (
            <span className="rounded border border-accent/30 bg-accent/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-accent">
              live
            </span>
          )}
        </a>
      </div>
    );
  }

  const isUser = message.role === "user";
  return (
    <div className={`flex animate-rise-in ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[82%] whitespace-pre-wrap rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "rounded-br-sm border border-accent/25 bg-accent/[0.09] text-hi"
            : "rounded-bl-sm border border-edge bg-raised text-mid"
        }`}
      >
        {message.content}
        {message.streaming && (
          <span className="ml-0.5 inline-block h-[1.05em] w-[2px] translate-y-[2px] animate-pulse bg-accent align-middle" />
        )}
      </div>
    </div>
  );
}

function InterviewTimer({ minutes }: { minutes: number }) {
  const [left, setLeft] = useState(minutes * 60);
  const endRef = useRef<number>(Date.now() + minutes * 60 * 1000);
  useEffect(() => {
    const id = setInterval(() => {
      setLeft(Math.max(0, Math.round((endRef.current - Date.now()) / 1000)));
    }, 1000);
    return () => clearInterval(id);
  }, []);
  const mm = Math.floor(left / 60);
  const ss = String(left % 60).padStart(2, "0");
  const low = left <= 120;
  return (
    <span
      title="Interview time remaining"
      className={`nums rounded-md border px-2 py-1 font-mono text-[10px] tracking-[0.1em] ${
        left === 0
          ? "border-warn/50 bg-warn/10 text-warn"
          : low
            ? "border-warn/40 text-warn"
            : "border-edge bg-ink/50 text-dim"
      }`}
    >
      {left === 0 ? "TIME" : `${mm}:${ss}`}
    </span>
  );
}

function Thinking() {
  return (
    <div className="flex animate-fade-in justify-start">
      <div className="flex gap-1.5 rounded-xl rounded-bl-sm border border-edge bg-raised px-4 py-3.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-dim"
            style={{ animation: `coachPulse 1.1s ${i * 0.18}s ease-in-out infinite` }}
          />
        ))}
        <style jsx>{`
          @keyframes coachPulse {
            0%,
            100% {
              opacity: 0.25;
            }
            50% {
              opacity: 1;
            }
          }
        `}</style>
      </div>
    </div>
  );
}

/* ── Icons (consistent 1.6px stroke, currentColor) ─────────────── */
const S = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

function SpeakerIcon({ on }: { on: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" {...S}>
      <path d="M4 9v6h3l5 4V5L7 9H4Z" />
      {on ? (
        <>
          <path d="M16 9.5a3.5 3.5 0 0 1 0 5" />
          <path d="M18.5 7a7 7 0 0 1 0 10" />
        </>
      ) : (
        <path d="M16 9.5 21 14.5M21 9.5 16 14.5" />
      )}
    </svg>
  );
}

function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" {...S}>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </svg>
  );
}

function RecordingDot() {
  return (
    <span className="relative flex h-3 w-3">
      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent/60" />
      <span className="relative inline-flex h-3 w-3 rounded-full bg-accent" />
    </span>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" {...S}>
      <path d="M5 12h13M12 5l7 7-7 7" />
    </svg>
  );
}

function LinkIcon() {
  return (
    <svg viewBox="0 0 24 24" width="13" height="13" {...S}>
      <path d="M9 15 15 9M10.5 6.5l1-1a4 4 0 0 1 6 6l-1 1M13.5 17.5l-1 1a4 4 0 0 1-6-6l1-1" />
    </svg>
  );
}
