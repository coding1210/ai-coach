# Design — AI Coach for Gen AI Engineers

**Status:** Draft v1 · **Date:** 2026-07-14
**Companion to:** [PRD.md](PRD.md) · [techstack.md](techstack.md) · [Syllabus.md](Syllabus.md)

This document defines the technical architecture: the LangGraph coaching graph, state schema, data models, scoring engine, and the voice pipeline.

---

## 1. Architecture overview

```
                         ┌──────────────────────────────────────┐
   Browser (Next.js)     │              Backend (FastAPI)        │
 ┌───────────────────┐   │                                       │
 │  Chat UI           │   │   /ws/session  (WebSocket, streaming) │
 │  Report / Radar    │◄──┼──► LangGraph Coaching Agent           │
 │  Progress view     │   │        (checkpointed state graph)     │
 │                    │   │            │                          │
 │  Voice:            │   │            ├─► LLM router (GPT/Groq)   │
 │   mic ──► STT ─────┼───┼──► Groq Whisper (STT)                 │
 │   TTS ◄── Kokoro   │   │            ├─► LLM-as-judge (scoring)  │
 └───────────────────┘   │            ├─► Tools (research, sched) │
                         │            └─► Persistence             │
                         │                 ├─ Postgres checkpoint  │
                         │                 └─ Supabase (ledger)    │
                         └──────────────────────────────────────┘
                                  Competency map (competency_map.json)
```

- **Voice is client-side where possible:** STT audio is streamed to Groq Whisper; TTS (Kokoro) runs *in the browser* → no server TTS hop, lowest latency, zero cost.
- **LangGraph** owns the coaching flow as an explicit, checkpointed state machine.
- **Two persistence layers:** LangGraph checkpointer (conversation/thread state, resumable) + Supabase (durable per-user proficiency ledger across sessions).

## 2. The coaching state graph (LangGraph)

Modeled as nodes (computation) + conditional edges (transitions), the canonical LangGraph pattern. The graph is compiled with a **PostgresSaver checkpointer** keyed by `thread_id` so a session survives restarts and supports human-in-the-loop pause/resume.

```
        ┌─────────────┐
        │  onboard    │  gather goal, background, target role
        └──────┬──────┘
               ▼
        ┌─────────────┐        selects next competency by weight + gaps
        │  assess     │◄───────────────────────────┐
        │ (ask Q)     │                             │
        └──────┬──────┘                             │
               ▼                                    │
        ┌─────────────┐                             │
        │  score      │  LLM-as-judge → L1..L5 + evidence
        │ (judge)     │                             │
        └──────┬──────┘                             │
               ▼                                    │
         «enough coverage?» ──── no ────────────────┘
               │ yes
               ▼
        ┌─────────────┐
        │  report     │  strengths / weaknesses / current vs target
        └──────┬──────┘
               ▼
        ┌─────────────┐   picks top 2–3 gap×weight competencies
        │  plan_focus │
        └──────┬──────┘
               ▼
        ┌─────────────┐   explain → challenge → exercise → resource(tool)
        │  coach      │◄──────── loop within focus area ────────┐
        └──────┬──────┘                                         │
               ▼                                                │
         «user wants more / next?» ─── continue ────────────────┘
               │ done
               ▼
        ┌─────────────┐  write baseline/current/target to Supabase ledger
        │  persist    │
        └─────────────┘
```

**Modularity:** `assess`→`score` is implemented as a **subgraph** (its own state schema), embedded as a node in the top-level orchestrator, so the assessment logic can evolve independently.

## 3. State schema

LangGraph state is a `TypedDict` updated across nodes.

```python
class CompetencyScore(TypedDict):
    competency_id: str
    level: int            # 1..5 (Dreyfus)
    evidence: str         # judge's justification, quotes user
    confidence: float     # 0..1

class CoachState(TypedDict):
    thread_id: str
    user_id: str
    profile: dict                      # goal, background, target_role
    messages: list                     # conversation (add_messages reducer)
    asked: list[str]                   # competency_ids already probed
    scores: dict[str, CompetencyScore] # competency_id -> score
    coverage: float                    # 0..1 weighted assessment coverage
    report: dict | None
    focus_areas: list[str]             # chosen competency_ids to coach
    phase: str                         # onboard|assess|report|coach|done
```

## 4. Data models (Supabase / Postgres)

```
users(id, created_at, goal, background, target_role)

proficiency_ledger(
  id, user_id, competency_id,
  baseline_level, current_level, target_level,
  updated_at)                          -- one row per user × competency

session(id, user_id, thread_id, started_at, ended_at, summary)

assessment_event(                      -- audit trail of scoring
  id, session_id, competency_id,
  level, evidence, confidence, created_at)
```

`proficiency_ledger` is the **progress mechanism**: growth = `current_level − baseline_level` per competency; the dashboard renders deltas over `updated_at`.

## 5. Assessment engine (adaptive)

- **Question selection:** rank competencies by `weight` (from `competency_map.json`), skip well-covered ones, prefer high-weight/low-coverage. Seed questions come from the map; the `assess` node may generate a targeted follow-up based on the last answer.
- **Adaptivity:** strong answer → move on or probe one level deeper; weak/uncertain answer → note the gap and move on (coaching, not interrogation).
- **Stop condition:** weighted `coverage ≥ threshold` (e.g., 0.7 of Critical+High weight) OR user opts to see results.

## 6. Scoring — LLM-as-a-judge (rubric-based)

Per best practice, the judge is **rubric-grounded** and bias-controlled.

- **Rubric-based:** each competency ships explicit L1–L5 descriptors (in [Syllabus.md](Syllabus.md) / `competency_map.json`). Rubrics are *specific, measurable, non-overlapping, exhaustive*.
- **Structured output:** judge returns `{level, evidence, confidence}` as JSON (schema-validated) — evidence must quote/reference the user's actual answer.
- **Bias controls:** instruct against **verbosity bias** (long ≠ better) and **self-preference**; use a fixed rubric so scoring isn't position-dependent.
- **Calibration:** validate the judge against a small **human-labeled sample** (Cohen's kappa) and tune the prompt until agreement is acceptable. This is the credibility story for the demo.
- **Model:** GPT for scoring (quality where it matters); Groq/Gemini for cheaper conversational turns — a per-task model routing decision (see [techstack.md](techstack.md)).

## 7. Report generation

`report` node synthesizes `scores` into:
- **Strengths** (competencies at/above target),
- **Weaknesses** (largest `target − current` gaps, weighted),
- **Per-domain current vs target** (radar data),
- **Prioritized focus list** (top 2–3 gap×weight) → feeds `plan_focus`.

Output is both conversational (spoken/streamed) and structured (JSON for the UI radar/report view).

## 8. Coaching loop

For each focus competency, the `coach` node runs a mentorship micro-loop:
1. **Explain** the concept at the user's level (meet them where they are).
2. **Challenge** with a realistic scenario ("your RAG returns irrelevant chunks for long contracts — what do you check?").
3. **Exercise** — assign a small, concrete practical task.
4. **Resource** — tool-call to fetch a relevant, current resource.
5. **Reflect** — offer to re-probe to detect improvement.

Growth mindset framing throughout; never "you failed lesson X."

## 9. Voice pipeline (simple STT + TTS)

```
🎤 → (browser captures audio) → Groq Whisper large-v3-turbo (STT)
   → CoachState / LangGraph (LLM) → streamed text
   → Kokoro-82M in-browser (TTS) → 🔊
```

- **STT:** Groq Whisper (free, near-realtime). Fallback: browser Web Speech API.
- **TTS:** Kokoro-82M via WebGPU/WASM in the browser (free, low latency, natural). Fallback: Web Speech `SpeechSynthesis`.
- **Latency budget:** STT ~150–300ms + LLM first-token (Groq ~fast) + TTS local ~near-instant → ~<1s perceived turn.
- Each stage is independently swappable so a single failure degrades gracefully instead of killing the demo.

## 10. API surface (FastAPI)

| Endpoint | Purpose |
| --- | --- |
| `WS /ws/session` | Streaming chat/voice turns ↔ LangGraph (token + event stream) |
| `POST /stt` | Audio → text (proxy to Groq Whisper) |
| `GET /report/{user_id}` | Latest evaluation report (JSON) |
| `GET /progress/{user_id}` | Proficiency ledger + deltas for dashboard |
| `POST /session/resume` | Resume a checkpointed thread by `thread_id` |

## 11. Reliability & fallback strategy

- **LLM:** GPT (scoring) / Groq (turns) → Gemini free tier → local error message. Never a silent hang.
- **STT/TTS:** cloud → browser-native fallbacks.
- **Persistence:** Postgres checkpointer; if unavailable, in-memory SqliteSaver for the demo.
- **Demo:** run locally + Cloudflare Tunnel/ngrok (no cold starts), with a scripted dry run beforehand.

## 12. Observability

Trace every LLM call (prompt, tokens, latency, cost) and every scoring decision (rubric + evidence). Useful for debugging *and* as a demo narrative ("here's exactly why the coach scored RAG at L3").

---
*Next build artifact: `competency_map.json` derived from [Syllabus.md](Syllabus.md), consumed by the `assess`/`score` nodes.*
