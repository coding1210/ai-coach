#!/usr/bin/env bash
# One-command demo launcher: Postgres + backend + frontend, with clean teardown.
#
#   ./serve_demo.sh              # local demo   → http://localhost:3000
#   ./serve_demo.sh --tunnel     # + public Cloudflare links to share
#
# Ctrl-C stops the backend, frontend, and any tunnels. Postgres (Docker) is left
# running so the proficiency ledger persists between runs; stop it with:
#   docker compose down            (keep data)   |   docker compose down -v  (wipe)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TUNNEL=0
[ "${1:-}" = "--tunnel" ] && TUNNEL=1

pids=()
cleanup() {
  echo
  echo "▸ Stopping backend / frontend / tunnels (Postgres stays up) …"
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  # Backstop: kill the child process trees the subshell PIDs don't cover.
  pkill -f "uvicorn app.main:app" 2>/dev/null || true
  pkill -f "next dev" 2>/dev/null || true
  pkill -f "cloudflared tunnel --url" 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

wait_url() { until curl -sf "$1" >/dev/null 2>&1; do sleep 1; done; }

capture_tunnel() { # $1=port → prints public https URL
  local port="$1" log; log="$(mktemp)"
  cloudflared tunnel --url "http://localhost:$port" >"$log" 2>&1 &
  pids+=($!)
  local url=""
  for _ in $(seq 1 30); do
    url="$(grep -oE 'https://[a-z0-9.-]+\.trycloudflare\.com' "$log" | head -1)"
    [ -n "$url" ] && break
    sleep 1
  done
  echo "$url"
}

# ── 1. Postgres ──────────────────────────────────────────────────
echo "▸ Postgres"
docker compose -f "$ROOT/docker-compose.yml" up -d >/dev/null
until [ "$(docker inspect -f '{{.State.Health.Status}}' aicoach-postgres 2>/dev/null)" = "healthy" ]; do sleep 1; done
echo "  healthy on :5433"

# ── 2. Backend ───────────────────────────────────────────────────
echo "▸ Backend (:8000)"
( cd "$ROOT/backend" && PYTHONPATH=. uv run uvicorn app.main:app --port 8000 --log-level warning ) &
pids+=($!)
wait_url http://localhost:8000/health
echo "  $(curl -s http://localhost:8000/health)"

# ── 3. Frontend (with optional public API base) ──────────────────
FRONT_URL="http://localhost:3000"
if [ "$TUNNEL" = "1" ]; then
  echo "▸ Tunnel: backend"
  API="$(capture_tunnel 8000)"
  [ -z "$API" ] && { echo "  ! could not get backend tunnel URL"; cleanup; }
  export NEXT_PUBLIC_HTTP_BASE="$API"
  export NEXT_PUBLIC_WS_BASE="${API/https:/wss:}"
  echo "  backend public: $API"
fi

echo "▸ Frontend (:3000)"
( cd "$ROOT/frontend" && npm run dev ) &
pids+=($!)
wait_url http://localhost:3000

if [ "$TUNNEL" = "1" ]; then
  echo "▸ Tunnel: frontend"
  FRONT_URL="$(capture_tunnel 3000)"
  echo "  frontend public: $FRONT_URL"
fi

echo
echo "  ────────────────────────────────────────────"
echo "  Coach:     $FRONT_URL"
echo "  Progress:  $FRONT_URL/progress"
echo "  Backend:   http://localhost:8000/health"
echo "  Dry run:   (new terminal) cd backend && uv run python scripts/dry_run.py"
echo "  ────────────────────────────────────────────"
echo "  Ctrl-C to stop."
wait
