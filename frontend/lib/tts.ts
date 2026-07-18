"use client";

// Text-to-speech with graceful degradation (Design.md §9):
//   Kokoro-82M in-browser (WebGPU/WASM, natural) → Web Speech SpeechSynthesis.
// Kokoro is loaded lazily and only on demand; any failure (no WebGPU, model
// download blocked, unsupported browser) falls back to Web Speech so the voice
// demo never hard-fails.

export type TtsEngine = "kokoro" | "webspeech" | "none";

// Web Speech is the default: instant, no download, reliable for a live demo.
// Kokoro (premium in-browser neural TTS) is opt-in — set localStorage
// coach_tts="kokoro" to prefer it (it lazy-downloads an ~80MB model).
function preferKokoro(): boolean {
  return typeof window !== "undefined" && localStorage.getItem("coach_tts") === "kokoro";
}

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

/** Kick off the Kokoro model download early (only if it's the preferred engine). */
export function warmupKokoro(): void {
  if (!preferKokoro()) return;
  loadKokoro().catch(() => {
    /* fall back silently at speak time */
  });
}

// Resolves when speech actually FINISHES (so callers can track "speaking").
// A length-based timeout is a safety net so the flag never sticks on.
function speakWebSpeech(text: string): Promise<void> {
  return new Promise((resolve) => {
    if (typeof window === "undefined" || !window.speechSynthesis) return resolve();
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.03;
    u.pitch = 1.0;
    let done = false;
    const finish = () => {
      if (!done) {
        done = true;
        resolve();
      }
    };
    u.onend = finish;
    u.onerror = finish;
    window.speechSynthesis.speak(u);
    setTimeout(finish, Math.min(30000, Math.max(1500, text.length * 70)));
  });
}

async function speakKokoro(text: string): Promise<void> {
  const tts = await loadKokoro();
  const audio = await tts.generate(text, { voice: KOKORO_VOICE });
  const url = URL.createObjectURL(audio.toBlob());
  audioEl?.pause();
  audioEl = new Audio(url);
  await new Promise<void>((resolve) => {
    let done = false;
    const finish = () => {
      if (!done) {
        done = true;
        URL.revokeObjectURL(url);
        resolve();
      }
    };
    audioEl!.onended = finish;
    audioEl!.onerror = finish;
    audioEl!.play().catch(finish);
    setTimeout(finish, Math.min(30000, Math.max(1500, text.length * 70)));
  });
}

/** Speak `text`, returning the engine that actually spoke. Web Speech by
 * default; Kokoro only when preferred (with Web Speech fallback on any error). */
export async function speak(text: string): Promise<TtsEngine> {
  const clean = text.replace(/\s+/g, " ").trim();
  if (!clean) return "none";
  if (preferKokoro()) {
    try {
      await speakKokoro(clean);
      return "kokoro";
    } catch {
      /* fall through to Web Speech */
    }
  }
  await speakWebSpeech(clean);
  return "webspeech";
}

export function stopSpeaking(): void {
  audioEl?.pause();
  if (typeof window !== "undefined" && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}
