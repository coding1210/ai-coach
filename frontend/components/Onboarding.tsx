"use client";

import { useState } from "react";
import type { Profile } from "@/lib/types";

const PRESETS: { label: string; profile: Profile }[] = [
  {
    label: "Leveling-up Lena",
    profile: {
      goal: "become a job-ready Gen AI engineer",
      background: "1–3 yrs Python, some LangChain/RAG from tutorials",
      target_role: "Mid-level Gen AI Engineer",
    },
  },
  {
    label: "Pivoting Pavan",
    profile: {
      goal: "move into a senior Gen AI role",
      background: "experienced backend dev, strong Python, new to LLMs/agents",
      target_role: "Senior Gen AI Engineer",
    },
  },
];

export default function Onboarding({
  onStart,
  disabled,
}: {
  onStart: (p: Profile) => void;
  disabled?: boolean;
}) {
  const [profile, setProfile] = useState<Profile>({
    goal: "",
    background: "",
    target_role: "",
  });

  const set = (k: keyof Profile) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setProfile((p) => ({ ...p, [k]: e.target.value }));

  const ready = profile.goal.trim() && profile.background.trim();

  return (
    <div className="mx-auto max-w-lg animate-rise-in rounded-2xl border border-edge/70 bg-white/[0.015] p-1.5 shadow-panel">
      <div className="rounded-[13px] border border-edge/60 bg-panel p-6 sm:p-7">
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
          New assessment
        </span>
        <h2 className="mt-2.5 text-xl font-semibold tracking-[-0.01em] text-hi">
          Tell your coach where you&apos;re headed
        </h2>
        <p className="mt-1.5 text-sm leading-relaxed text-dim text-pretty">
          No syllabus. The coach uses this to diagnose your specific gaps and
          coach those — progress means movement on your own weak areas.
        </p>

        <div className="mt-6 space-y-4">
          <Field label="Your goal">
            <input
              className="coach-input"
              value={profile.goal}
              onChange={set("goal")}
              placeholder="e.g. become a senior Gen AI engineer"
            />
          </Field>
          <Field label="Your background">
            <input
              className="coach-input"
              value={profile.background}
              onChange={set("background")}
              placeholder="e.g. backend dev, strong Python, new to agents"
            />
          </Field>
          <Field label="Target role (optional)">
            <input
              className="coach-input"
              value={profile.target_role}
              onChange={set("target_role")}
              placeholder="e.g. Senior Gen AI Engineer"
            />
          </Field>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
            or load a persona
          </span>
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => setProfile(p.profile)}
              className="rounded-md border border-edge px-3 py-1.5 text-xs font-medium text-mid transition-[transform,border-color,color] duration-200 ease-out-quart hover:border-accent/60 hover:text-hi active:scale-[0.97]"
            >
              {p.label}
            </button>
          ))}
        </div>

        <button
          disabled={!ready || disabled}
          onClick={() => onStart(profile)}
          className="group mt-7 flex w-full items-center justify-center gap-2.5 rounded-md bg-accent px-4 py-3 text-sm font-semibold text-accent-ink transition-[transform,box-shadow] duration-200 ease-out-quart hover:shadow-accent active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-30 disabled:shadow-none disabled:active:scale-100"
        >
          Start assessment
          <span className="grid h-5 w-5 place-items-center rounded-full bg-accent-ink/15 transition-transform duration-200 ease-out-quart group-hover:translate-x-0.5">
            →
          </span>
        </button>
      </div>

      <style jsx>{`
        .coach-input {
          width: 100%;
          border-radius: 8px;
          border: 1px solid #262a32;
          background: #0d0e11;
          padding: 0.7rem 0.85rem;
          font-size: 0.875rem;
          color: #e9ebef;
          outline: none;
          transition: border-color 200ms var(--ease-out-quart),
            box-shadow 200ms var(--ease-out-quart);
        }
        .coach-input::placeholder {
          color: #565c67;
        }
        .coach-input:focus {
          border-color: rgba(200, 241, 105, 0.7);
          box-shadow: 0 0 0 3px rgba(200, 241, 105, 0.12);
        }
      `}</style>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block font-mono text-[10px] uppercase tracking-[0.16em] text-dim">
        {label}
      </span>
      {children}
    </label>
  );
}
