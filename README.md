# AI Coach — Gen AI Engineer

An AI **coach** (not a course) for Gen AI engineers. It holds a real
conversation, **diagnoses** your actual strengths and gaps against a competency
rubric, produces an **evaluation report**, and **coaches** your specific
weak areas — tracking growth over time. Progress means movement on *your* gaps,
never "% of a syllabus completed."

> Source-of-truth docs: [PRD.md](PRD.md) · [Design.md](Design.md) ·
> [techstack.md](techstack.md) · [Syllabus.md](Syllabus.md) ·
> [competency_map.json](competency_map.json)

## Engineering highlights

- **Agent as an explicit state machine.** A LangGraph `StateGraph` (16 nodes,
  conditional routing) drives onboarding → leveled assessment → triage →
  coaching → interview mode → report. See
  [`backend/app/graph/build.py`](backend/app/graph/build.py).
- **Resumable, human-in-the-loop runs.** Nodes pause with `interrupt()` and
  resume with `Command(resume=...)`; state lives in a Postgres checkpointer, so a
  session survives a page refresh and is replayed to the client
  ([`backend/app/api/ws.py`](backend/app/api/ws.py)).
- **Per-task model routing with failover.** Conversational turns prefer Groq;
  scoring and reports prefer GPT. Every call has a timeout and falls through
  Gemini → OpenAI → a deterministic fake provider, and the UI is told when it is
  running degraded ([`backend/app/llm/router.py`](backend/app/llm/router.py)).
- **Tool calling.** The coach reaches for a live web-research tool (Tavily) with
  a curated fallback, surfaced to the UI as tool-call events
  ([`backend/app/llm/tools.py`](backend/app/llm/tools.py)).
- **Rubric-grounded LLM-as-judge.** Scores are checked against a competency
  rubric; the rubric is withheld from the client so practice reps can't be gamed.
- **Production basics.** Token streaming over WebSockets, bearer-token auth, rate
  limiting and a usage cap ([`backend/app/api/limits.py`](backend/app/api/limits.py)),
  Docker, and GitHub Actions CI (ruff + **91 backend tests** that run offline,
  plus the frontend).

## Status

- **Phase 1 ✓** — text coaching loop, backend + frontend, end to end.
- **Phase 2 ✓** — token streaming, agentic tool-calling, voice loop, progress dashboard.
- **Phase 3 ✓** — leveled adaptive assessment with a mastery gate, mock-interview
  mode, JD-targeted diagnosis, coaching roadmap, practice-rep engine
  (generate → validate → grade), LLM failover, and go-live hardening.

## Architecture — text coaching loop, end to end

```
        Next.js (chat + report/radar)  ⇄  FastAPI / WebSocket
                                           └─ LangGraph coaching graph:
   onboard → assess_ask → assess_await → score → report
           → plan_focus → coach → coach_await → persist
                                           ├─ LLM router (Groq/GPT/Gemini, fake default)
                                           └─ Postgres (checkpointer + proficiency ledger)
```

- **[backend/](backend)** — FastAPI + LangGraph. Rubric-grounded LLM-as-judge
  scoring, adaptive weight-driven assessment, evaluation report, coaching loop
  with an agentic **research tool** (FR5), **token streaming** over the WS, and
  a proficiency ledger. Runs offline on a deterministic fake LLM; real providers
  activate behind API keys. See [backend/README.md](backend/README.md).
- **[frontend/](frontend)** — Next.js. Streaming chat, a **voice toggle**
  (Web Speech STT + Kokoro-82M TTS, Web Speech fallback), live evaluation report
  with a current-vs-target radar, tool-call chips, and a **`/progress`
  dashboard** (baseline→current→target, growth deltas).

## Run it (two terminals)

```bash
# ── backend ──────────────────────────────────────────────
cd backend
uv sync --extra dev
uv run pytest                                   # 91 tests, no DB/keys needed
docker compose up -d                            # (optional) local Postgres
cp .env.example .env                            # add GROQ/OPENAI/GEMINI keys to go live
uv run uvicorn app.main:app --reload --port 8000

# ── frontend ─────────────────────────────────────────────
cd frontend
npm install
cp .env.local.example .env.local                # points at http://localhost:8000
npm run dev                                      # http://localhost:3000
```

With no API keys and no database, everything still runs: a deterministic
FakeProvider drives the graph and an in-memory store backs persistence, so the
demo never hard-fails. Add keys for real Groq/GPT/Gemini behavior; start Postgres
for durable, cross-session progress.

## Remaining / future

- **Groq Whisper STT** via a `/stt` proxy as the accuracy upgrade over browser
  Web Speech (needs a key).
- **Kokoro TTS audio** is wired (dynamic-imported, WebGPU/WASM) with a Web
  Speech fallback; it needs a real WebGPU browser + model download to voice —
  not exercised in headless CI.
- **Growth deltas** populate once a user **re-assesses** (baseline is captured on
  the first session; the ledger diffs against it).
- Adaptive LLM follow-up questions in `assess_ask`; judge calibration against a
  human-labeled sample; local + tunnel demo packaging.
