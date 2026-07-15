"""Per-task model routing with resilient failover (techstack.md §2).

Task → preferred provider chain:
  turn / coach   → Groq, then Gemini, then OpenAI, then Fake
  score / report → OpenAI (GPT) first, then Gemini, then Fake

Resilience: every call has a per-call timeout and fails over down the chain,
ending in the deterministic FakeProvider — so a flaky/slow/rate-limited provider
degrades the session instead of killing it. When a call falls back to Fake (or
no real provider is configured), `degraded` flips true so the UI can warn that
scores are placeholders.
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, Awaitable, Callable, Literal

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
    "turn": ["groq", "gemini", "openai", "fake"],
    "coach": ["groq", "gemini", "openai", "fake"],
    "score": ["openai", "gemini", "fake"],
    "report": ["openai", "gemini", "fake"],
}

_CALL_TIMEOUT = 25.0  # seconds per attempt before failing over


class LLMRouter:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._providers: dict[str, LLMProvider] = {"fake": FakeProvider()}
        self._build()
        # If there's no real provider at all, we're already in degraded (fake) mode.
        self._degraded = not any(k in self._providers for k in ("groq", "openai", "gemini"))

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
        """First available provider in the task's preference chain (no failover)."""
        for name in _PREFERENCES[task]:
            if name in self._providers:
                return self._providers[name]
        return self._providers["fake"]

    # ── resilient execution ──────────────────────────────────────
    async def _failover(self, task: Task, call: Callable[[LLMProvider], Awaitable]):
        last_exc: Exception | None = None
        for name in _PREFERENCES[task]:
            provider = self._providers.get(name)
            if provider is None:
                continue
            try:
                result = await asyncio.wait_for(call(provider), timeout=_CALL_TIMEOUT)
                if name == "fake":
                    self._degraded = True
                return result
            except Exception as e:  # noqa: BLE001 — try the next provider
                last_exc = e
                log.warning("Provider %r failed for task %r: %s — failing over", name, task, e)
        self._degraded = True
        raise last_exc or RuntimeError("no provider available")

    async def complete(self, task: Task, messages, **kw) -> str:
        return await self._failover(task, lambda p: p.complete(messages, **kw))

    async def complete_json(self, task: Task, messages, *, schema, **kw) -> dict:
        return await self._failover(task, lambda p: p.complete_json(messages, schema=schema, **kw))

    async def stream(self, task: Task, messages, **kw) -> AsyncIterator[str]:
        """Stream with failover *before the first token* (the common failure mode:
        auth/rate-limit/connection errors surface on the first chunk)."""
        for name in _PREFERENCES[task]:
            provider = self._providers.get(name)
            if provider is None:
                continue
            gen = provider.stream(messages, **kw)
            try:
                first = await asyncio.wait_for(gen.__anext__(), timeout=_CALL_TIMEOUT)
            except StopAsyncIteration:
                if name == "fake":
                    self._degraded = True
                return
            except Exception as e:  # noqa: BLE001 — try the next provider
                log.warning("Stream provider %r failed for %r: %s — failing over", name, task, e)
                continue
            if name == "fake":
                self._degraded = True
            yield first
            try:
                async for tok in gen:
                    yield tok
            except Exception as e:  # noqa: BLE001 — mid-stream break; stop gracefully
                log.warning("Stream %r broke mid-way for %r: %s", name, task, e)
            return
        self._degraded = True

    @property
    def degraded(self) -> bool:
        return self._degraded

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
