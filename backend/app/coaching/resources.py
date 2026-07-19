"""Curated learning resources per competency.

A small, hand-picked set attached to roadmap milestones so "what to practice"
comes with somewhere to start. This is a static curated map (stable, no live
crawl in this runtime); `refresh_resources` is the documented hook for pulling
current links from a search/index when one is available, so it stays fresh in a
fast-moving field.
"""

from __future__ import annotations

_RESOURCES: dict[str, list[dict]] = {
    "rag.chunking": [
        {"title": "Chunking strategies for LLM applications (Pinecone)", "url": "https://www.pinecone.io/learn/chunking-strategies/"},
        {"title": "LangChain text splitters", "url": "https://python.langchain.com/docs/how_to/#text-splitters"},
    ],
    "rag.embeddings": [
        {"title": "MTEB embedding benchmark", "url": "https://huggingface.co/spaces/mteb/leaderboard"},
        {"title": "OpenAI embeddings guide", "url": "https://platform.openai.com/docs/guides/embeddings"},
    ],
    "rag.hybrid_rerank": [
        {"title": "Hybrid search & Reciprocal Rank Fusion", "url": "https://www.pinecone.io/learn/hybrid-search-intro/"},
        {"title": "Cohere Rerank", "url": "https://docs.cohere.com/docs/reranking"},
    ],
    "rag.retrieval_eval": [
        {"title": "RAGAS retrieval metrics", "url": "https://docs.ragas.io/"},
        {"title": "Evaluating RAG (recall/precision/MRR)", "url": "https://www.pinecone.io/learn/series/rag/"},
    ],
    "agents.tool_calling": [
        {"title": "OpenAI function calling", "url": "https://platform.openai.com/docs/guides/function-calling"},
        {"title": "Anthropic tool use", "url": "https://docs.anthropic.com/en/docs/build-with-claude/tool-use"},
    ],
    "agents.react_planning": [
        {"title": "ReAct: Reasoning + Acting (paper)", "url": "https://arxiv.org/abs/2210.03629"},
        {"title": "LangGraph agent patterns", "url": "https://langchain-ai.github.io/langgraph/"},
    ],
    "eval.llm_judge": [
        {"title": "Judging LLM-as-a-judge (paper)", "url": "https://arxiv.org/abs/2306.05685"},
        {"title": "LLM-as-judge best practices", "url": "https://huggingface.co/learn/cookbook/llm_judge"},
    ],
    "eval.design_golden": [
        {"title": "Your AI product needs evals (Hamel Husain)", "url": "https://hamel.dev/blog/posts/evals/"},
        {"title": "OpenAI Evals", "url": "https://github.com/openai/evals"},
    ],
    "llm.streaming": [
        {"title": "OpenAI streaming responses", "url": "https://platform.openai.com/docs/api-reference/streaming"},
    ],
    "prod.routing_fallback": [
        {"title": "LiteLLM routing & fallbacks", "url": "https://docs.litellm.ai/docs/routing"},
    ],
    "py.error_handling": [
        {"title": "tenacity: retries in Python", "url": "https://tenacity.readthedocs.io/"},
    ],
    "safety.prompt_injection": [
        {"title": "OWASP LLM Top 10", "url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/"},
    ],
    "safety.pii": [
        {"title": "Microsoft Presidio (PII detection)", "url": "https://microsoft.github.io/presidio/"},
    ],
}


def resources_for(competency_id: str) -> list[dict]:
    return list(_RESOURCES.get(competency_id, []))


def refresh_resources(competency_id: str, search_fn=None) -> list[dict]:
    """Hook: when a live search/index is available, pull current links here.
    Falls back to the curated set so behaviour is stable without one."""
    if search_fn is None:
        return resources_for(competency_id)
    try:
        fresh = search_fn(competency_id)
        return fresh or resources_for(competency_id)
    except Exception:  # noqa: BLE001 — never let a bad fetch break the roadmap
        return resources_for(competency_id)
