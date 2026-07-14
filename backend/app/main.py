"""FastAPI application wiring.

Lifespan builds the three runtime singletons and stores them on app.state:
  - checkpointer  (AsyncPostgresSaver → local Postgres; InMemorySaver fallback)
  - repo          (PostgresRepository; MemoryRepository fallback)
  - graph         (compiled coaching graph bound to the checkpointer)

Everything degrades to in-memory so the server always boots for a demo, even
with no database reachable.
"""

from __future__ import annotations

import contextlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes, ws
from app.config import get_settings
from app.graph.build import build_graph
from app.persistence.memory_repo import MemoryRepository

log = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    async with contextlib.AsyncExitStack() as stack:
        checkpointer = None
        repo = None

        if settings.has_postgres:
            try:
                from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

                from app.persistence.postgres_repo import PostgresRepository

                checkpointer = await stack.enter_async_context(
                    AsyncPostgresSaver.from_conn_string(settings.database_url)
                )
                await checkpointer.setup()
                repo = await PostgresRepository.create(settings.database_url)
                stack.push_async_callback(repo.close)
                log.info("Persistence: Postgres (%s)", settings.database_url)
            except Exception as e:  # noqa: BLE001 — demo must still boot
                log.warning("Postgres unavailable (%s); falling back to in-memory.", e)
                checkpointer, repo = None, None

        if checkpointer is None:
            from langgraph.checkpoint.memory import InMemorySaver

            checkpointer = InMemorySaver()
            repo = MemoryRepository()
            log.info("Persistence: in-memory (checkpointer + repository)")

        app.state.graph = build_graph(checkpointer)
        app.state.repo = repo
        yield


app = FastAPI(title="AI Coach — Gen AI Engineer", version="0.1.0", lifespan=lifespan)

# CORS for the Next.js frontend. Local dev by exact origin; tunneled demo links
# (Cloudflare / ngrok) by regex so a shared URL's REST calls aren't blocked.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"https://.*\.(trycloudflare\.com|ngrok-free\.app|ngrok\.io|ngrok\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws.router)
app.include_router(routes.router)


@app.get("/health")
async def health() -> dict:
    from app.llm.router import get_router

    return {"status": "ok", "llm_providers": get_router().available}
