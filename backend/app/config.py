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

    @property
    def has_postgres(self) -> bool:
        return bool(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
