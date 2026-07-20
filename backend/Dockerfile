# AI Coach backend — container for any host (Fly / Render / Railway / Cloud Run).
# Build from the REPO ROOT so competency_map.json (a repo-root file) is in context:
#   docker build -f backend/Dockerfile -t ai-coach-backend .
#   docker run -p 8000:8000 --env-file backend/.env ai-coach-backend

FROM python:3.12-slim

# uv for fast, locked installs (official static binaries).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    COMPETENCY_MAP_PATH=/app/competency_map.json

# Dependencies first (cached layer). uv.lock is optional; fall back to a resolve.
COPY backend/pyproject.toml backend/uv.lock* /app/
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Application code + the competency map (lives at the repo root).
COPY backend/ /app/
COPY competency_map.json /app/competency_map.json

EXPOSE 8000
# Hosts inject $PORT; default to 8000 locally.
CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
