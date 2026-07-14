import type { Config } from "tailwindcss";

// "Instrument" design tokens — graphite base, one signal-lime accent,
// Geist Sans + Geist Mono, tinted depth, custom easing. Existing token names
// (ink/panel/edge/accent/good/warn) are kept and re-pointed so components need
// no className churn; new tokens (hi/mid/dim/faint/raised/edge-strong) add the
// hierarchy the old palette lacked.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-geist)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        ink: "#0d0e11", // app base
        panel: "#15171c", // surface / inner core
        raised: "#1b1e25", // raised surface (bubbles, rows, stats)
        edge: "#262a32", // hairline border
        "edge-strong": "#343a45",
        hi: "#e9ebef", // high-emphasis text
        mid: "#aeb4bf", // body text
        dim: "#767d89", // secondary text
        faint: "#565c67", // tertiary text
        accent: "#c8f169", // signal lime — current state + interactive
        "accent-ink": "#12160a", // text on accent fills
        good: "#c8f169", // current state unified to the single accent
        warn: "#d8a86a", // muted clay — functional "gap" tint only
      },
      borderRadius: {
        DEFAULT: "10px",
        md: "8px",
        lg: "12px",
        xl: "16px",
        "2xl": "18px",
      },
      boxShadow: {
        panel:
          "inset 0 1px 0 0 rgba(255,255,255,0.03), 0 24px 60px -32px rgba(0,0,0,0.85)",
        raised:
          "inset 0 1px 0 0 rgba(255,255,255,0.04), 0 12px 30px -20px rgba(0,0,0,0.8)",
        accent:
          "0 0 0 1px rgba(200,241,105,0.25), 0 10px 34px -12px rgba(200,241,105,0.28)",
      },
      transitionTimingFunction: {
        "out-quart": "cubic-bezier(0.23, 1, 0.32, 1)",
        "in-out-strong": "cubic-bezier(0.77, 0, 0.175, 1)",
        drawer: "cubic-bezier(0.32, 0.72, 0, 1)",
      },
      keyframes: {
        "rise-in": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
      },
      animation: {
        "rise-in": "rise-in 320ms cubic-bezier(0.23,1,0.32,1) both",
        "fade-in": "fade-in 240ms ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;
