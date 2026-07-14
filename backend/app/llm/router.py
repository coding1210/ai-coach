"""Per-task model routing with graceful fallback (techstack.md §2).

Task → preferred provider chain:
  turn / coach   → Groq (speed dominates the felt experience)
  score / report → OpenAI GPT (diagnosis quality is the product's credibility)
  any            → Gemini free tier as resilience, then FakeProvider as the
                   never-fail backstop.

Whichever providers have keys are instantiated once at startup; missing ones are
simply skipped. With no keys at all, every task resolves to FakeProvider so the
coaching loop still runs end-to-end.
"""

from __future__ import annotations

import logging
from typing import Literal

from app.config import Settings, get_settings
from app.llm.providers import (
    FakeProvider,
    GeminiProvider,
    GroqProvider,
    LLMProvider,
    OpenAIProvider,
)

log = logging.getLogger(__name__)

Task = Literal["turn", "coach", "score", "report"]

_PREFERENCES: dict[Task, list[str]] = {
    # Speed-first tasks prefer Groq, then Gemini; OpenAI is a capable (pricier)
    # fallback so a single OpenAI key still powers the whole loop.
    "turn": ["groq", "gemini", "openai", "fake"],
    "coach": ["groq", "gemini", "openai", "fake"],
    # Quality-first tasks lead with GPT.
    "score": ["openai", "gemini", "fake"],
    "report": ["openai", "gemini", "fake"],
}


class LLMRouter:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._providers: dict[str, LLMProvider] = {"fake": FakeProvider()}
        self._build()

    def _build(self) -> None:
        s = self._settings
        if s.groq_api_key:
            try:
                self._providers["groq"] = GroqProvider(s.groq_api_key, s.groq_model)
            except Exception as e:  # SDK missing / bad config — stay degraded, don't crash
                log.warning("Groq provider unavailable: %s", e)
        if s.openai_api_key:
            try:
                self._providers["openai"] = OpenAIProvider(s.openai_api_key, s.openai_model)
            except Exception as e:
                log.warning("OpenAI provider unavailable: %s", e)
        if s.gemini_api_key:
            try:
                self._providers["gemini"] = GeminiProvider(s.gemini_api_key, s.gemini_model)
            except Exception as e:
                log.warning("Gemini provider unavailable: %s", e)
        log.info("LLM providers ready: %s", ", ".join(sorted(self._providers)))

    def for_task(self, task: Task) -> LLMProvider:
        """First available provider in the task's preference chain."""
        for name in _PREFERENCES[task]:
            if name in self._providers:
                return self._providers[name]
        return self._providers["fake"]

    @property
    def available(self) -> list[str]:
        return sorted(self._providers)

    @property
    def providers(self) -> dict[str, LLMProvider]:
        return dict(self._providers)


_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
