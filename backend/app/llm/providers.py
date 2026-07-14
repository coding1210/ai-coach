"""LLM provider abstraction.

One small interface (`LLMProvider`) with concrete implementations for Groq,
OpenAI, and Gemini, plus a deterministic `FakeProvider` used when no keys are
present. SDKs are imported lazily so the app boots without any of them
installed/configured — critical for a bulletproof demo and for CI.

`Message` is a plain dict: {"role": "system"|"user"|"assistant", "content": str}.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

Message = dict[str, str]


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def complete(
        self, messages: list[Message], *, temperature: float = 0.7, max_tokens: int = 1024
    ) -> str:
        ...

    @abstractmethod
    async def complete_json(
        self, messages: list[Message], *, schema: dict[str, Any], temperature: float = 0.0
    ) -> dict[str, Any]:
        ...

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.7, max_tokens: int = 1024
    ) -> AsyncIterator[str]:
        """Default: emit the full completion as one chunk. Overridden where the
        SDK supports token streaming."""
        yield await self.complete(messages, temperature=temperature, max_tokens=max_tokens)


# ─────────────────────────────────────────────────────────────────
# Fake provider — deterministic, offline, dependency-free.
# ─────────────────────────────────────────────────────────────────
class FakeProvider(LLMProvider):
    """Deterministic stand-in so the graph + tests run with no keys/network.

    Returns plausible, structurally-valid output shaped by the task. Judge calls
    (complete_json) return a mid-scale score so the end-to-end loop produces a
    coherent report and coaching plan.
    """

    name = "fake"

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.7, max_tokens: int = 1024
    ) -> str:
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        return (
            "[fake-llm] "
            + (last_user[:120] if last_user else "Let's continue.")
            + " — could you say more about how you'd approach that in practice?"
        )

    async def complete_json(
        self, messages: list[Message], *, schema: dict[str, Any], temperature: float = 0.0
    ) -> dict[str, Any]:
        # Best-effort: satisfy a judge-style schema deterministically.
        props = (schema or {}).get("properties", {})
        out: dict[str, Any] = {}
        if "level" in props:
            out["level"] = 3
        if "evidence" in props:
            out["evidence"] = "[fake-llm] Answer shows working familiarity; mid-scale by default."
        if "confidence" in props:
            out["confidence"] = 0.5
        return out or {"result": "[fake-llm] ok"}

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.7, max_tokens: int = 1024
    ) -> AsyncIterator[str]:
        # Chunk the fake completion word-by-word so streaming is visible with no keys.
        text = await self.complete(messages, temperature=temperature, max_tokens=max_tokens)
        for word in text.split(" "):
            yield word + " "


# ─────────────────────────────────────────────────────────────────
# Real providers — lazy SDK imports keep them optional.
# ─────────────────────────────────────────────────────────────────
class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, api_key: str, model: str) -> None:
        from groq import AsyncGroq

        self._client = AsyncGroq(api_key=api_key)
        self._model = model

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.7, max_tokens: int = 1024
    ) -> str:
        resp = await self._client.chat.completions.create(
            model=self._model, messages=messages, temperature=temperature, max_tokens=max_tokens
        )
        return resp.choices[0].message.content or ""

    async def complete_json(
        self, messages: list[Message], *, schema: dict[str, Any], temperature: float = 0.0
    ) -> dict[str, Any]:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content or "{}")

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.7, max_tokens: int = 1024
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.7, max_tokens: int = 1024
    ) -> str:
        resp = await self._client.chat.completions.create(
            model=self._model, messages=messages, temperature=temperature, max_tokens=max_tokens
        )
        return resp.choices[0].message.content or ""

    async def complete_json(
        self, messages: list[Message], *, schema: dict[str, Any], temperature: float = 0.0
    ) -> dict[str, Any]:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "judgement", "schema": schema, "strict": True},
            },
        )
        return json.loads(resp.choices[0].message.content or "{}")

    async def stream(
        self, messages: list[Message], *, temperature: float = 0.7, max_tokens: int = 1024
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    @staticmethod
    def _to_contents(messages: list[Message]) -> tuple[str | None, str]:
        system = next((m["content"] for m in messages if m["role"] == "system"), None)
        convo = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages if m["role"] != "system"
        )
        return system, convo

    async def complete(
        self, messages: list[Message], *, temperature: float = 0.7, max_tokens: int = 1024
    ) -> str:
        from google.genai import types

        system, convo = self._to_contents(messages)
        resp = await self._client.aio.models.generate_content(
            model=self._model,
            contents=convo,
            config=types.GenerateContentConfig(
                system_instruction=system, temperature=temperature, max_output_tokens=max_tokens
            ),
        )
        return resp.text or ""

    async def complete_json(
        self, messages: list[Message], *, schema: dict[str, Any], temperature: float = 0.0
    ) -> dict[str, Any]:
        from google.genai import types

        system, convo = self._to_contents(messages)
        resp = await self._client.aio.models.generate_content(
            model=self._model,
            contents=convo,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
        return json.loads(resp.text or "{}")
