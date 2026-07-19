"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { speak, stopSpeaking, warmupKokoro, type TtsEngine } from "./tts";

// Speech-to-text via the browser Web Speech API (keyless, zero infra). Groq
// Whisper via a /stt proxy is the higher-accuracy upgrade (techstack.md) and
// slots in behind this same interface.

function getRecognition(): any {
  if (typeof window === "undefined") return null;
  const Ctor =
    (window as any).SpeechRecognition ||
    (window as any).webkitSpeechRecognition;
  return Ctor ? new Ctor() : null;
}

export function useVoice() {
  const recRef = useRef<any>(null);
  // Voice on by default: the 'Start' click unlocks browser audio, so the
  // greeting and replies speak automatically. Users can mute with the toggle.
  const [enabled, setEnabled] = useState(true);
  const [handsFree, setHandsFree] = useState(false);
  const [listening, setListening] = useState(false);
  const [sttSupported, setSttSupported] = useState(true);
  const [ttsEngine, setTtsEngine] = useState<TtsEngine>("none");
  const [speaking, setSpeaking] = useState(false);
  const speakingCount = useRef(0);

  useEffect(() => {
    const rec = getRecognition();
    if (!rec) {
      setSttSupported(false);
      return;
    }
    rec.lang = "en-US";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    recRef.current = rec;
    return () => {
      try {
        rec.abort();
      } catch {
        /* noop */
      }
    };
  }, []);

  const toggleEnabled = useCallback(() => {
    setEnabled((prev) => {
      const next = !prev;
      if (next) warmupKokoro();
      else stopSpeaking();
      return next;
    });
  }, []);

  // Hands-free implies voice on; the caller auto-listens after the coach speaks.
  const toggleHandsFree = useCallback(() => {
    setHandsFree((prev) => {
      const next = !prev;
      if (next) {
        setEnabled(true);
        warmupKokoro();
      }
      return next;
    });
  }, []);

  const listen = useCallback((onFinal: (text: string) => void) => {
    const rec = recRef.current;
    if (!rec) return;
    stopSpeaking(); // don't transcribe our own voice
    rec.onresult = (e: any) => {
      const transcript = Array.from(e.results)
        .map((r: any) => r[0].transcript)
        .join(" ")
        .trim();
      if (transcript) onFinal(transcript);
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    try {
      rec.start();
      setListening(true);
    } catch {
      setListening(false);
    }
  }, []);

  const stopListening = useCallback(() => {
    try {
      recRef.current?.stop();
    } catch {
      /* noop */
    }
    setListening(false);
  }, []);

  // Speak and track a `speaking` flag (ref-counted so overlapping calls behave).
  const runSpeak = useCallback(async (text: string) => {
    speakingCount.current += 1;
    setSpeaking(true);
    try {
      const engine = await speak(text);
      setTtsEngine(engine);
    } finally {
      speakingCount.current -= 1;
      if (speakingCount.current <= 0) setSpeaking(false);
    }
  }, []);

  const say = useCallback(
    async (text: string) => {
      if (!enabled) return;
      await runSpeak(text);
    },
    [enabled, runSpeak]
  );

  // Speak regardless of the enabled flag (used when the user just turned voice on).
  const speakNow = useCallback((text: string) => runSpeak(text), [runSpeak]);

  return {
    enabled,
    toggleEnabled,
    handsFree,
    toggleHandsFree,
    listening,
    listen,
    stopListening,
    sttSupported,
    say,
    speakNow,
    ttsEngine,
    speaking,
  };
}
