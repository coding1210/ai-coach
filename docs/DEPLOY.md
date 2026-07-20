# Deploying AI Coach

Two pieces: a **backend container** (FastAPI + LangGraph) and the **Next.js
frontend** (Vercel). You provision the hosts; this doc is the wiring.

## Prerequisites (do these first)

- **Rotate the API keys** — the OpenAI/Groq keys shared during development must be
  regenerated before anything public-facing.
- **A managed Postgres** (Supabase, Neon, RDS, Fly Postgres…). Without it the app
  falls back to in-memory and loses all data — reports, ledger, and practice
  mastery — on every restart.
- Keep the code sandbox **off** in prod (`ENABLE_SANDBOX` unset/false) unless you
  add real container isolation — it executes user-submitted code.

## Backend (container)

Build from the **repo root** (the Dockerfile pulls in `competency_map.json`):

```bash
docker build -f backend/Dockerfile -t ai-coach-backend .
docker run -p 8000:8000 --env-file backend/.env ai-coach-backend   # local check
```

On Fly / Render / Railway / Cloud Run, point the service at `backend/Dockerfile`
with build context `.` (repo root). The host injects `$PORT`; the image respects it.

### Backend env vars

| Var | Purpose |
| --- | --- |
| `OPENAI_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY` | LLM providers (at least one; rotate before deploy) |
| `DATABASE_URL` | Managed Postgres — **required in prod** for durable data |
| `ALLOWED_ORIGINS` | Comma-separated frontend origin(s), e.g. `https://your-app.vercel.app` |
| `RATE_LIMIT_PER_MIN`, `LLM_SESSION_CAP`, `WS_TURN_CAP` | Abuse/cost guards (sensible defaults ship) |
| `ENABLE_SANDBOX` | Leave unset/false unless you've added isolation |

`*.vercel.app` and tunnel domains (ngrok/cloudflare) are already allowed by regex,
so preview URLs work without touching `ALLOWED_ORIGINS`.

> Scaling note: the rate-limit/usage counters are **in-process**. On a single
> instance that's correct; behind a load balancer or with >1 worker, move them to
> Redis (swap the dicts in `app/api/limits.py`).

## Frontend (Vercel)

Import the repo, set **Root Directory = `frontend`** (framework auto-detected as
Next.js). Set:

| Var | Value |
| --- | --- |
| `NEXT_PUBLIC_HTTP_BASE` | `https://<your-backend-host>` |
| `NEXT_PUBLIC_WS_BASE` | `wss://<your-backend-host>` (secure WebSocket) |

Then add the resulting Vercel URL to the backend's `ALLOWED_ORIGINS` (or rely on
the `*.vercel.app` regex).

## Post-deploy smoke check

- `GET https://<backend>/health` → `{"status":"ok", ...}`
- Open the frontend, run a diagnosis end-to-end, confirm the report renders (no
  CORS errors in the console, WebSocket connects over `wss://`).
- Restart the backend and confirm progress/mastery persist (proves Postgres, not
  the in-memory fallback, is in use).
