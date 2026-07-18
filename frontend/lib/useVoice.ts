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
  const [listening, setListening] = useState(false);
  const [sttSupported, setSttSupported] = useState(true);
  const [ttsEngine, setTtsEngine] = useState<TtsEngine>("none");

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

  const say = useCallback(
    async (text: string) => {
      if (!enabled) return;
      const engine = await speak(text);
      setTtsEngine(engine);
    },
    [enabled]
  );

  // Speak regardless of the enabled flag (used when the user just turned voice
  // on, to read the message already on screen).
  const speakNow = useCallback(async (text: string) => {
    const engine = await speak(text);
    setTtsEngine(engine);
  }, []);

  return {
    enabled,
    toggleEnabled,
    listening,
    listen,
    stopListening,
    sttSupported,
    say,
    speakNow,
    ttsEngine,
  };
}
