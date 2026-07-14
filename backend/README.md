# AI Coach — Backend (Phase 1)

FastAPI + LangGraph text coaching loop for a Gen AI engineer.
Coaching, **not** teaching: diagnose → evaluate → coach the individual's gaps.

```
onboard → assess_ask → assess_await → score → report
        → plan_focus → coach → coach_await → persist
```

The competency map (`../competency_map.json`) is the coach's internal diagnostic
rubric, read by the `assess`/`score` nodes. It is never delivered as a curriculum.

## Layout

```
app/
  main.py            FastAPI app + lifespan (checkpointer, repo, graph)
  config.py          pydantic-settings (keys, model IDs, thresholds)
  models.py          API / WS / ledger Pydantic models
  api/               ws.py (WS /ws/session), routes.py (report/progress/resume)
  graph/             state.py, build.py, edges.py, nodes/*
  llm/               router.py (per-task routing+fallback), providers.py, judge.py
  competency/        loader.py (typed map), selection.py (adaptive pick, coverage)
  persistence/       repository.py + postgres_repo.py + memory_repo.py, schema.sql
  prompts/           versioned prompt notes
tests/               loader, selection, judge (fake), full-loop smoke
```

## Design choices

- **Fake-LLM by default.** With no API keys, every task resolves to a
  deterministic `FakeProvider`, so the graph and tests run offline. Set keys in
  `.env` to activate Groq (turns/coaching), GPT (scoring/report), Gemini
  (fallback) — per `techstack.md` model routing.
- **Postgres persistence, in-memory fallback.** Local Postgres backs the
  LangGraph checkpointer + proficiency ledger (Supabase is the same SQL later).
  If Postgres is unreachable, the app boots on `InMemorySaver` + `MemoryRepository`
  so a demo never dies.
- **Interrupt-driven turns.** `assess_await` / `coach_await` pause via
  LangGraph `interrupt()`; the WS resumes with `Command(resume=...)`.

## Run

```bash
# 1. deps (uv + Python 3.12)
uv sync --extra dev

# 2. (optional) local Postgres for durable persistence
docker compose up -d          # from repo root
cp .env.example .env          # DATABASE_URL already points at it

# 3. tests (no DB / keys needed)
uv run pytest

# 4. dev server
uv run uvicorn app.main:app --reload --port 8000
#   GET  /health
#   POST /auth/session          → { token, user_id }   (mint a bearer token)
#   WS   /ws/session            (start message carries the token)
#   GET  /report  GET /progress  POST /grade  POST /session/resume
#                                (all require Authorization: Bearer <token>)
```

**Auth:** data endpoints are scoped to the token's user — no `user_id` in URLs,
so ids can't be enumerated. The WS `start` message carries the token; the server
resolves the user from it. See `app/auth.py`.

## Going live with real models

With no keys the app runs on the deterministic `FakeProvider`. To activate real
coaching, add keys to `.env` and verify connectivity:

```bash
# Add to backend/.env (all optional; each activates its provider):
#   GROQ_API_KEY=...     free — console.groq.com          (fast turns + coaching)
#   OPENAI_API_KEY=...   paid, cents at demo scale         (scoring + report)
#   GEMINI_API_KEY=...   free — aistudio.google.com        (fallback)
#   TAVILY_API_KEY=...   free — tavily.com                 (live research tool)

uv run python scripts/check_providers.py   # one text + one JSON call per key
```

The check reports latency, the JSON (judge) path, and the per-task routing
(turns → Groq, scoring/report → GPT, fallback → Gemini). Non-zero exit if any
configured provider fails — use it as a pre-demo smoke test. `GET /health` also
lists the active providers.

## Judge calibration

The credibility story for the diagnosis: prove the LLM-as-judge agrees with a
human rater before trusting its scores (Design.md §6).

```bash
uv run python scripts/calibrate_judge.py
```

It scores a small human-labeled set (`calibration/labeled_sample.json`) with the
live judge and reports exact accuracy, within-one agreement, MAE, **Cohen's κ**,
and **quadratic-weighted κ** (ordinal-aware), plus a confusion matrix and the
disagreements. Artifacts land in `calibration/results.json` + `report.md`.

Latest run (GPT-4o, n=22): accuracy **0.82**, within-one **1.00**, Cohen's κ
**0.75** (substantial), weighted κ **0.94** (almost perfect). Metric functions
live in `app/eval/metrics.py` (dependency-free, unit-tested); tune the judge
prompt in `app/llm/judge.py` and re-run to move κ. On the FakeProvider every
prediction is L3, which the metrics correctly report as chance-level — a sanity
check that the harness detects a bad judge.

## Behavioral exercises (graded)

Measures *doing*, not *describing*: the coach sets a concrete coding task and
grades the **submitted artifact**. Two signals combine — objective `checks`
(regexes over the code, comments stripped so prose doesn't count) that **cap**
the score, and a code-reading rubric judge.

```
GET  /exercise/{competency_id}   # task prompt (checks/rubric withheld)
POST /grade                       # {user_id, competency_id, submission} → level + checks
uv run python scripts/exercise_demo.py   # complete vs incomplete vs all-talk
```

Bank in `exercises/exercises.json` (5 competencies); engine in
`app/llm/grader.py` + `app/eval/exercises.py`. Live example (py.async, GPT):
complete code → **L4** (5/5 checks), incomplete → **L2** (1/5), an all-talk
comment that names every technique → **L1** (0/5).

**Wired into the coaching loop**: when a focus competency has an exercise, the
graph runs `coach → challenge → challenge_await` — the coach teaches, sets the
task, grades the submitted code, and the **behavioral score supersedes the
self-report** for that competency in the ledger (so `described L2 → demonstrated
L4` shows up in `/progress`). Competencies without an exercise use the normal
reply path.

## Phase 2 (done)

- **Token streaming** — nodes emit custom events via `app/graph/streaming.py`;
  the WS runs `graph.astream(stream_mode=["custom","updates"])` and forwards
  tokens/tool-calls/report events. Fake provider streams word-by-word so it's
  visible with no keys.
- **Agentic tool-calling (FR5)** — `app/llm/tools.py::research_resource` fetches
  a resource per gap in the `coach` node (live Tavily search behind
  `TAVILY_API_KEY`, curated fallback otherwise), surfaced as a `tool_call` event.
- **Progress** — `GET /progress/{user_id}` enriched with competency/domain names
  for the dashboard.

## Still stubbed

- `POST /stt` proxy to Groq Whisper (frontend uses browser Web Speech STT today).
- Adaptive LLM follow-up questions in `assess_ask`.
- Judge calibration against a human-labeled sample.
