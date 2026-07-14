"use client";

import { useCallback, useRef, useState } from "react";
import { WS_BASE, ensureSession } from "./api";
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

// Drives one coaching session over the WebSocket. Nodes stream custom events;
// we render assistant text (streamed token-by-token or whole), tool calls, and
// the structured report, and reflect interrupt/END as `status`.
export function useCoachSession(opts: Options = {}) {
  const wsRef = useRef<WebSocket | null>(null);
  const streamingRef = useRef<boolean>(false);
  const onDone = useRef(opts.onAssistantDone);
  onDone.current = opts.onAssistantDone;

  const [status, setStatus] = useState<SessionStatus>("idle");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [phase, setPhase] = useState<string>("onboard");
  const [error, setError] = useState<string | null>(null);
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
        // The exercise prompt arrives as an assistant_message; nothing extra to do.
        break;
      case "report":
        if (evt.data) setReport(evt.data as Report);
        break;
      case "phase":
        if (evt.phase) setPhase(evt.phase);
        setStatus("awaiting_input");
        break;
      case "done":
        if (evt.phase) setPhase(evt.phase);
        setStatus("done");
        wsRef.current?.close();
        break;
      case "error":
        setError(evt.content ?? "Unknown error");
        setStatus("error");
        break;
    }
  }, []);

  const start = useCallback(
    async (profile: Profile) => {
      setMessages([]);
      setReport(null);
      setError(null);
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

      const ws = new WebSocket(`${WS_BASE}/ws/session`);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("thinking");
        ws.send(JSON.stringify({ type: "start", token: session.token, profile }));
      };
      ws.onmessage = (e) => handleEvent(JSON.parse(e.data) as ServerEvent);
      ws.onerror = () => {
        setError("Could not reach the coach backend. Is it running on :8000?");
        setStatus("error");
      };
    },
    [handleEvent]
  );

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

  return { status, messages, report, phase, error, userId, start, send };
}
