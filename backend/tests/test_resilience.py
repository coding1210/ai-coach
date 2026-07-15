"""Router resilience: a failing provider fails over to Fake instead of killing
the turn, and flips `degraded` so the UI can warn. Also the dig-into-weakness
traversal. All offline."""

from typing import AsyncIterator

import pytest

from app.competency.loader import load_competency_map
from app.competency.selection import next_competency
from app.llm.providers import LLMProvider, Message
from app.llm.router import LLMRouter

_JUDGE_SCHEMA = {"type": "object", "properties": {"level": {}, "evidence": {}, "confidence": {}}}


class BoomProvider(LLMProvider):
    name = "boom"

    async def complete(self, messages, *, temperature=0.7, max_tokens=1024) -> str:
        raise RuntimeError("provider down")

    async def complete_json(self, messages, *, schema, temperature=0.0) -> dict:
        raise RuntimeError("provider down")

    async def stream(self, messages, *, temperature=0.7, max_tokens=1024) -> AsyncIterator[str]:
        raise RuntimeError("provider down")
        yield  # pragma: no cover — makes this an async generator


def test_no_real_providers_is_degraded():
    # Test env blanks all keys (conftest) → only Fake → degraded from the start.
    assert LLMRouter().degraded is True


@pytest.mark.asyncio
async def test_complete_json_fails_over_to_fake_and_flags_degraded():
    r = LLMRouter()
    r._providers["openai"] = BoomProvider()  # broken primary for the score task
    r._degraded = False
    out = await r.complete_json("score", [{"role": "user", "content": "x"}], schema=_JUDGE_SCHEMA)
    assert isinstance(out, dict) and "level" in out  # Fake answered
    assert r.degraded is True


@pytest.mark.asyncio
async def test_stream_fails_over_to_fake():
    r = LLMRouter()
    r._providers["groq"] = BoomProvider()  # broken primary for the turn task
    r._degraded = False
    msgs: list[Message] = [{"role": "user", "content": "hello there coach"}]
    tokens = [t async for t in r.stream("turn", msgs, temperature=0.0, max_tokens=16)]
    assert "".join(tokens).strip()  # Fake streamed something
    assert r.degraded is True


def test_traversal_digs_into_weak_domain():
    cmap = load_competency_map()
    asked = ["rag.chunking"]
    weak = {"rag.chunking": {"competency_id": "rag.chunking", "level": 1, "evidence": "", "confidence": 0.9}}
    # A weak score in RAG should pull the coach back into RAG rather than marching
    # on to a fresh domain (which is what pure breadth-first would do).
    assert cmap.domain_of(next_competency(cmap, asked, weak).id).id == "rag"
    # With no weakness signal, it moves on breadth-first to a new domain.
    assert cmap.domain_of(next_competency(cmap, asked, {}).id).id != "rag"
