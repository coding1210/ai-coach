"use client";

// Text-to-speech with graceful degradation (Design.md §9):
//   Kokoro-82M in-browser (WebGPU/WASM, natural) → Web Speech SpeechSynthesis.
// Kokoro is loaded lazily and only on demand; any failure (no WebGPU, model
// download blocked, unsupported browser) falls back to Web Speech so the voice
// demo never hard-fails.

export type TtsEngine = "kokoro" | "webspeech" | "none";

const KOKORO_MODEL = "onnx-community/Kokoro-82M-v1.0-ONNX";
const KOKORO_VOICE = "af_heart";

let kokoroPromise: Promise<any> | null = null;
let audioEl: HTMLAudioElement | null = null;

async function loadKokoro(): Promise<any> {
  if (!kokoroPromise) {
    kokoroPromise = (async () => {
      const { KokoroTTS } = await import("kokoro-js");
      const device =
        typeof navigator !== "undefined" && (navigator as any).gpu
          ? "webgpu"
          : "wasm";
      return KokoroTTS.from_pretrained(KOKORO_MODEL, { dtype: "q8", device });
    })().catch((e) => {
      kokoroPromise = null; // allow retry / fall back
      throw e;
    });
  }
  return kokoroPromise;
}

/** Kick off the Kokoro model download early (e.g. when the user enables voice). */
export function warmupKokoro(): void {
  loadKokoro().catch(() => {
    /* fall back silently at speak time */
  });
}

function speakWebSpeech(text: string): void {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.03;
  u.pitch = 1.0;
  window.speechSynthesis.speak(u);
}

async function speakKokoro(text: string): Promise<void> {
  const tts = await loadKokoro();
  const audio = await tts.generate(text, { voice: KOKORO_VOICE });
  const url = URL.createObjectURL(audio.toBlob());
  audioEl?.pause();
  audioEl = new Audio(url);
  audioEl.onended = () => URL.revokeObjectURL(url);
  await audioEl.play();
}

/** Speak `text`, preferring Kokoro, returning the engine that actually spoke. */
export async function speak(text: string): Promise<TtsEngine> {
  const clean = text.replace(/\s+/g, " ").trim();
  if (!clean) return "none";
  try {
    await speakKokoro(clean);
    return "kokoro";
  } catch {
    speakWebSpeech(clean);
    return "webspeech";
  }
}

export function stopSpeaking(): void {
  audioEl?.pause();
  if (typeof window !== "undefined" && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}
