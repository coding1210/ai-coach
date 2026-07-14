# Demo runbook

Everything needed to run the AI Coach live — reliably.

## Prerequisites (one time)

- **Docker** running (for Postgres), **uv** (backend), **Node** (frontend).
- Backend deps + env:
  ```bash
  cd backend && uv sync --extra dev && cp .env.example .env
  ```
  Add your keys to `backend/.env` (see [backend/README.md](backend/README.md)):
  `OPENAI_API_KEY` (scoring/report), `GROQ_API_KEY` (fast turns/coaching). With no
  keys it still runs on the deterministic FakeProvider.
- Frontend deps:
  ```bash
  cd frontend && npm install && cp .env.local.example .env.local
  ```

## Start the demo

```bash
./serve_demo.sh
```

Brings up Postgres (Docker, host port **5433** to avoid a local Postgres on 5432),
the backend (:8000), and the frontend (:3000), waits until each is healthy, and
prints the URLs. **Ctrl-C** stops the backend, frontend, and tunnels; Postgres is
left running so the proficiency ledger persists between runs.

- Coach: http://localhost:3000
- Progress: http://localhost:3000/progress
- Health: http://localhost:8000/health → lists active providers

## Pre-demo dry run (do this before you present)

In a second terminal, with the server running:

```bash
cd backend && uv run python scripts/dry_run.py
```

Drives a full session over the WebSocket (start → answer → report → coaching →
done) and confirms streaming, the research tool, and that the report + ledger
persisted. Exits non-zero on any failure. Also verify providers directly:

```bash
uv run python scripts/check_providers.py      # per-provider latency + routing
uv run python scripts/calibrate_judge.py       # judge agreement (Cohen's κ)
```

## Show status promotion (growth)

A returning user (same `user_id` / browser) is auto-detected: the coach welcomes
them back, re-probes their prior gaps, and the `/progress` ledger shows growth
deltas (baseline → current, ▲). To demonstrate it end-to-end against a running
server:

```bash
cd backend && uv run python scripts/reassess_demo.py
```

Runs a weak baseline then a strong re-assessment for one user and prints the
per-competency level gains (e.g. `Hybrid search & re-ranking: L1 → L4 (+3)`).
The dashboard reports **net** movement, so genuine regressions/no-changes show
too — an honest coach, not a cheerleader.

## Shareable public link

```bash
./serve_demo.sh --tunnel
```

Adds a Cloudflare quick tunnel for both services (no account needed), points the
frontend at the backend's public URL, and prints a shareable
`https://<name>.trycloudflare.com` link. The backend already allows
`*.trycloudflare.com` / `*.ngrok*` origins (CORS), so the shared link's REST
calls work. Tunnel URLs are random per run.

## Reset / troubleshooting

| Symptom | Fix |
| --- | --- |
| Backend logs `Persistence: in-memory` | Postgres unreachable — `docker compose up -d`; check `DATABASE_URL` port is **5433** |
| Port 5432 conflict | A local/brew Postgres owns 5432; the container uses 5433 on purpose |
| Wipe all coaching data | `docker compose down -v` (removes the volume) |
| Stop Postgres, keep data | `docker compose down` |
| Provider shows `fake` unexpectedly | Key missing/empty in `backend/.env`; run `scripts/check_providers.py` |
| Voice doesn't speak | Needs Chrome + mic permission; falls back to Web Speech if Kokoro/WebGPU fails |

## Security

Rotate the OpenAI and Groq keys after the demo (delete + recreate in each
provider console). Keys live only in the gitignored `backend/.env`.
