"use client";

import { useState } from "react";
import { restoreSession } from "@/lib/api";

/** "Coming back?" — restore a session from a recovery code so progress survives a
 *  cleared browser or a new device. On success the app reloads and resumes. */
export default function RestoreProgress() {
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [state, setState] = useState<"idle" | "checking" | "error">("idle");

  async function submit() {
    setState("checking");
    const acct = await restoreSession(code);
    if (acct) {
      window.location.reload();
    } else {
      setState("error");
    }
  }

  if (!open) {
    return (
      <div className="mt-4 text-center">
        <button
          onClick={() => setOpen(true)}
          className="text-xs text-dim transition-colors hover:text-hi"
        >
          Coming back? Restore your progress
        </button>
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-xl border border-edge/70 bg-panel/60 p-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-dim">
        Restore with your recovery code
      </p>
      <div className="mt-2 flex gap-2">
        <input
          value={code}
          onChange={(e) => {
            setCode(e.target.value);
            setState("idle");
          }}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="paste your recovery code"
          className="min-w-0 flex-1 rounded-md border border-edge bg-black/40 px-2.5 py-1.5 font-mono text-[11px] text-hi outline-none focus:border-accent/60"
        />
        <button
          onClick={submit}
          disabled={!code.trim() || state === "checking"}
          className="shrink-0 rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-accent-ink disabled:opacity-40"
        >
          {state === "checking" ? "…" : "Restore"}
        </button>
      </div>
      {state === "error" && (
        <p className="mt-1.5 text-[11px] text-warn">
          That code didn&apos;t match a saved session. Check it and try again.
        </p>
      )}
    </div>
  );
}
