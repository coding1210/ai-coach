"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { WS_BASE, clearSession, ensureSession } from "./api";
import type {
  ChatMessage,
  Profile,
  Report,
  ServerEvent,
  SessionStatus,
} from "./types";

interface Options {
  // Called with the full text whenever an assistant message completes
  // (streamed or not) — used to drive text-to-speech.
  onAssistantDone?: (text: string) => void;
}

const ACTIVE_KEY = "coach_active"; // thread_id of an in-progress session

function storedThread(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACTIVE_KEY);
}
function setActive(threadId: string) {
  if (typeof window !== "undefined") localStorage.setItem(ACTIVE_KEY, threadId);
}
function clearActive() {
  if (typeof window !== "undefined") localStorage.removeItem(ACTIVE_KEY);
}

// Drives one coaching session over the WebSocket. Survives page refresh: the
// active thread_id is persisted and the session is resumed (the graph state
// lives in the Postgres checkpoint), so a reload continues where you left off.
export function useCoachSession(opts: Options = {}) {
  const wsRef = useRef<WebSocket | null>(null);
  const streamingRef = useRef<boolean>(false);
  const threadRef = useRef<string | null>(null);
  const onDone = useRef(opts.onAssistantDone);
  onDone.current = opts.onAssistantDone;

  // Start in "connecting" if we're going to auto-resume, to avoid a flash of
  // the onboarding page on refresh.
  const [status, setStatus] = useState<SessionStatus>(() =>
    storedThread() ? "connecting" : "idle"
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [phase, setPhase] = useState<string>("onboard");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [userId, setUserId] = useState<string>("");

  const append = (m: ChatMessage) => setMessages((prev) => [...prev, m]);

  const appendToLast = (text: string) =>
    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (last && last.role === "assistant") {
        next[next.length - 1] = { ...last, content: last.content + text };
      }
      return next;
    });

  const finalizeLast = () =>
    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (last && last.role === "assistant") {
        next[next.length - 1] = { ...last, streaming: false };
        onDone.current?.(last.content);
      }
      return next;
    });

  const handleEvent = useCallback((evt: ServerEvent) => {
    if (evt.thread_id && threadRef.current !== evt.thread_id) {
      threadRef.current = evt.thread_id;
      setActive(evt.thread_id);
    }
    switch (evt.type) {
      case "assistant_message":
        if (evt.content) {
          append({ role: "assistant", content: evt.content });
          onDone.current?.(evt.content);
        }
        break;
      case "message_start":
        streamingRef.current = true;
        append({ role: "assistant", content: "", streaming: true });
        break;
      case "token":
        if (evt.text) appendToLast(evt.text);
        break;
      case "message_end":
        streamingRef.current = false;
        finalizeLast();
        break;
      case "tool_call":
        if (evt.result)
          append({
            role: "tool",
            content: evt.name ?? "tool",
            tool: { name: evt.name ?? "tool", result: evt.result },
          });
        break;
      case "grade":
        append({
          role: "grade",
          content: "",
          grade: {
            competency_id: evt.competency_id ?? "",
            level: evt.level ?? 0,
            deterministic_score: evt.deterministic_score ?? 0,
            checks: evt.checks ?? [],
            evidence: evt.evidence ?? "",
          },
        });
        break;
      case "exercise":
        break;
      case "report":
        if (evt.data) setReport(evt.data as Report);
        break;
      case "notice":
        if (evt.content) setNotice(evt.content);
        break;
      case "phase":
        if (evt.phase) setPhase(evt.phase);
        setStatus("awaiting_input");
        break;
      case "done":
        if (evt.phase) setPhase(evt.phase);
        setStatus("done");
        clearActive();
        wsRef.current?.close();
        break;
      case "error": {
        const msg = evt.content ?? "Unknown error";
        // Stale token (e.g. backend restarted in-memory) — forget it and drop
        // cleanly back to onboarding so the next Start mints a fresh session.
        if (/unauthor|token/i.test(msg)) {
          clearSession();
          clearActive();
          setMessages([]);
          setError(null);
          setStatus("idle");
        } else {
          setError(msg);
          setStatus("error");
        }
        break;
      }
    }
  }, []);

  const connect = useCallback(
    (startMsg: Record<string, unknown>) => {
      const ws = new WebSocket(`${WS_BASE}/ws/session`);
      wsRef.current = ws;
      ws.onopen = () => {
        setStatus("thinking");
        ws.send(JSON.stringify(startMsg));
      };
      ws.onmessage = (e) => handleEvent(JSON.parse(e.data) as ServerEvent);
      ws.onerror = () => {
        setError("Could not reach the coach backend. Is it running on :8000?");
        setStatus("error");
      };
    },
    [handleEvent]
  );

  const start = useCallback(
    async (profile: Profile) => {
      clearActive();
      threadRef.current = null;
      setMessages([]);
      setReport(null);
      setError(null);
      setNotice(null);
      setStatus("connecting");

      let session;
      try {
        session = await ensureSession();
      } catch {
        setError("Could not reach the coach backend. Is it running on :8000?");
        setStatus("error");
        return;
      }
      setUserId(session.user_id);
      connect({ type: "start", token: session.token, profile });
    },
    [connect]
  );

  const resume = useCallback(async () => {
    const tid = storedThread();
    if (!tid) {
      setStatus("idle");
      return;
    }
    threadRef.current = tid;
    setMessages([]);
    setReport(null);
    setError(null);
    setStatus("connecting");

    let session;
    try {
      session = await ensureSession();
    } catch {
      clearActive();
      setStatus("idle");
      return;
    }
    setUserId(session.user_id);
    connect({ type: "start", token: session.token, thread_id: tid });
  }, [connect]);

  // Auto-resume an in-progress session on mount (once).
  const resumedRef = useRef(false);
  useEffect(() => {
    if (resumedRef.current) return;
    resumedRef.current = true;
    if (storedThread()) resume();
  }, [resume]);

  const send = useCallback(
    (content: string) => {
      const ws = wsRef.current;
      if (!ws || status !== "awaiting_input" || !content.trim()) return;
      append({ role: "user", content });
      setStatus("thinking");
      ws.send(JSON.stringify({ type: "user_message", content }));
    },
    [status]
  );

  // End assessment early and jump to the evaluation (no visible message).
  const finish = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || status !== "awaiting_input") return;
    setStatus("thinking");
    ws.send(JSON.stringify({ type: "finish" }));
  }, [status]);

  return { status, messages, report, phase, error, notice, userId, start, send, finish };
}
