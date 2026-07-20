"""Central configuration (pydantic-settings), loaded from environment / .env.

Every external dependency is optional: with no API keys and no reachable
database, the app still boots on the FakeProvider + in-memory repository so the
coaching loop and tests run with zero setup. Keys/DB activate the real paths.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ─── LLM providers ───────────────────────────────────────────
    groq_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    tavily_api_key: str | None = None  # optional live web-search for the research tool

    groq_model: str = "llama-3.3-70b-versatile"
    groq_model_fast: str = "llama-3.1-8b-instant"
    openai_model: str = "gpt-4o"
    gemini_model: str = "gemini-2.5-flash"

    # ─── Persistence ─────────────────────────────────────────────
    database_url: str | None = None

    # ─── App ─────────────────────────────────────────────────────
    competency_map_path: Path = Path("../competency_map.json")
    coverage_threshold: float = 0.7
    log_level: str = "INFO"

    # Production frontend origin(s), comma-separated (e.g. "https://coach.vercel.app").
    # Added to the CORS allow-list alongside localhost + tunnel links.
    allowed_origins: str = ""

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # ─── Judging ─────────────────────────────────────────────────
    # Ensemble judging: run N independent judges concurrently and aggregate,
    # so a single noisy read can't swing the score. 1 = legacy single-judge.
    judge_samples: int = 3

    # ─── Sandbox ─────────────────────────────────────────────────
    # Actually execute graded submissions against their hidden tests. OFF by
    # default — running user code is a real risk; enable only in a trusted env.
    enable_sandbox: bool = False

    # ─── Abuse / cost guards ─────────────────────────────────────
    # The LLM-heavy endpoints are metered per authenticated session. Without
    # these, a public URL on live keys is an open wallet. In-process counters
    # (fine for a single worker; use Redis behind a load balancer).
    rate_limit_per_min: int = 60      # requests/min per session on LLM endpoints
    llm_session_cap: int = 150        # total LLM-heavy ops per session
    ws_turn_cap: int = 80             # max coaching/interview turns per WS session

    @property
    def has_postgres(self) -> bool:
        return bool(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
