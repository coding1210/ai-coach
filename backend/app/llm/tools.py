"""Agentic tools for the coach (FR5).

`research_resource` fetches a relevant, current learning resource for a
competency the coach is working on. It demonstrates tool-calling while staying
bulletproof for the demo:

  - If TAVILY_API_KEY is set, it does a live web search (httpx, no extra dep).
  - Otherwise it returns a curated, domain-matched resource.

Either way it returns the same shape and is logged as a tool_call event for the
observability narrative ("here's the coach reaching for a resource").
"""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

# Curated, domain-level fallbacks (stable, high-signal references).
_CURATED: dict[str, dict[str, str]] = {
    "rag": {"title": "Anthropic — Contextual Retrieval", "url": "https://www.anthropic.com/news/contextual-retrieval"},
    "agents": {"title": "LangGraph — Concepts & agent patterns", "url": "https://langchain-ai.github.io/langgraph/concepts/"},
    "evaluation": {"title": "RAGAS — Evaluating RAG & agents", "url": "https://docs.ragas.io/"},
    "llm_fundamentals": {"title": "OpenAI — Structured Outputs guide", "url": "https://platform.openai.com/docs/guides/structured-outputs"},
    "context_prompt": {"title": "Anthropic — Prompt engineering overview", "url": "https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview"},
    "production": {"title": "FastAPI — Streaming & WebSockets", "url": "https://fastapi.tiangolo.com/advanced/websockets/"},
    "observability": {"title": "Langfuse — LLM observability docs", "url": "https://langfuse.com/docs"},
    "python": {"title": "Real Python — Async IO in Python", "url": "https://realpython.com/async-io-python/"},
    "safety": {"title": "OWASP — Top 10 for LLM Applications", "url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/"},
    "finetuning": {"title": "Hugging Face — PEFT (LoRA/QLoRA)", "url": "https://huggingface.co/docs/peft"},
}

_DEFAULT = {"title": "Anthropic — Building effective agents", "url": "https://www.anthropic.com/research/building-effective-agents"}


async def _tavily_search(query: str, api_key: str) -> dict[str, str] | None:
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": api_key, "query": query, "max_results": 1},
            )
            r.raise_for_status()
            results = r.json().get("results") or []
            if results:
                return {"title": results[0].get("title", query), "url": results[0]["url"]}
    except Exception as e:  # noqa: BLE001 — degrade to curated
        log.warning("Tavily search failed (%s); using curated resource.", e)
    return None


async def research_resource(domain_id: str, competency_name: str) -> dict:
    """Return {title, url, source} for a coaching resource on this competency."""
    settings = get_settings()
    if settings.tavily_api_key:
        hit = await _tavily_search(
            f"best 2026 guide: {competency_name} for Gen AI engineers", settings.tavily_api_key
        )
        if hit:
            return {**hit, "source": "web_search"}
    resource = _CURATED.get(domain_id, _DEFAULT)
    return {**resource, "source": "curated"}
