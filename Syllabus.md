# Syllabus — Gen AI Engineer Competency Map (Coaching Rubric)

**Status:** Draft v1 · **Date:** 2026-07-14
**Companion to:** [PRD.md](PRD.md) · [Design.md](Design.md) · [techstack.md](techstack.md)

> **Important framing:** despite the filename, this is **not a teaching curriculum**. It is the coach's internal **diagnostic rubric** — the reference the agent assesses a user *against* to find their strengths and gaps. It is never delivered to the user as sequential lessons. This distinction (coaching vs teaching) is the core product principle in [PRD.md §3](PRD.md).
>
> Think of it as the **map the coach uses to locate you**, then chart *your* personalized path — not a syllabus everyone walks in order.

This map is materialized as `competency_map.json` and consumed by the `assess` and `score` nodes ([Design.md](Design.md)).

---

## 1. Proficiency rubric (Dreyfus model)

Every competency is scored on this 5-level scale. Level descriptors are given per competency below.

| Level | Name | General meaning |
| --- | --- | --- |
| **L1** | Novice | Knows the term; needs step-by-step guidance; no real project use |
| **L2** | Advanced Beginner | Uses it in tutorials/toy projects; misses edge cases |
| **L3** | Competent | Ships it in real projects; makes deliberate trade-offs |
| **L4** | Proficient | Designs it; debugs failure modes; optimizes cost/latency |
| **L5** | Expert | Sets patterns for others; handles novel/ambiguous cases; mentors |

The coach records **baseline → current → target** per competency. Target is derived from the user's stated goal (e.g., "senior Gen AI role" → mostly L4). **Gap = target − current**, weighted by domain weight, drives coaching priority.

## 2. Domain weights

Derived from 2026 hiring signal (RAG, agents, evaluation lead). Weight sets assessment depth and coaching priority.

| # | Domain | Weight |
| --- | --- | --- |
| 4 | RAG | **Critical** |
| 5 | Agents & Orchestration | **Critical** |
| 6 | Evaluation & Testing | **Critical** |
| 2 | LLM Fundamentals & APIs | High |
| 3 | Context & Prompt Engineering | High |
| 7 | Production Architecture & Serving | High |
| 8 | Observability & LLMOps | Medium-High |
| 1 | Python Engineering Foundations | Medium |
| 9 | Safety, Security & Responsible AI | Medium |
| 10 | Fine-tuning & Dataset Engineering | Low-Medium |

Assessment order: **Critical → High → Medium** so short sessions still cover what matters most.

---

## 3. The competency map

Each domain lists its competencies, a **sample assessment question** (open-ended, interview-style — the coach adapts follow-ups), and **level anchors** (what L2 vs L4 sounds like) to guide the LLM-judge.

### Domain 1 — Python Engineering Foundations · *Medium*
Competencies: `async/await & concurrency` · `type hints & Pydantic` · `testing (pytest, mocking LLM calls)` · `packaging & dependency management` · `clean architecture / project structure` · `error handling, retries & timeouts`

- **Sample Q:** "You're calling an LLM API 500 times in a batch job. How do you structure that in Python for speed and resilience?"
- **L2 anchor:** loops calls synchronously; basic try/except.
- **L4 anchor:** async with concurrency limits, backoff/retry, timeouts, typed models, testable design.

### Domain 2 — LLM Fundamentals & APIs · *High*
Competencies: `tokenization & context windows` · `sampling params (temp, top-p)` · `structured outputs / JSON mode` · `streaming` · `multi-provider APIs (OpenAI/Anthropic/Groq)` · `model selection & trade-offs` · `cost/token awareness`

- **Sample Q:** "How do you decide which model to use for a task, and how do you get reliable JSON out of it?"
- **L2 anchor:** picks one model by default; parses JSON with hope.
- **L4 anchor:** routes by task/cost/latency; uses structured-output modes/schemas; reasons about context limits and token cost.

### Domain 3 — Context & Prompt Engineering · *High*
Competencies: `system prompt design` · `few-shot & role prompting` · `context-window management` · `tool/function description quality` · `prompt templating & versioning` · `hallucination reduction via prompting`

- **Sample Q:** "An agent keeps misusing a tool. Walk me through how you'd debug and fix it via context/prompt design."
- **L2 anchor:** tweaks wording ad hoc.
- **L4 anchor:** treats it as context engineering — tool description quality, examples, context budgeting, versioned prompts, measurable iteration.

### Domain 4 — RAG (Retrieval-Augmented Generation) · *Critical*
Competencies: `chunking strategies` · `embeddings & embedding models` · `vector DBs (Qdrant/Pinecone/Weaviate/pgvector)` · `hybrid search & re-ranking` · `retrieval evaluation` · `graph RAG (Neo4j)` · `when NOT to use RAG`

- **Sample Q:** "Design a RAG system over a company's legal contracts. Where do retrieval failures come from and how do you catch them?"
- **L2 anchor:** naive fixed-size chunking + top-k similarity.
- **L4 anchor:** chunking tuned to structure, hybrid + re-ranking, retrieval eval (recall/precision), knows RAG's limits and alternatives.

### Domain 5 — Agents & Orchestration · *Critical*
Competencies: `function/tool calling` · `ReAct & planning loops` · `LangGraph (state machines, checkpointing, HITL)` · `multi-agent patterns (CrewAI)` · `agent memory` · `MCP (build/consume servers)` · `failure-mode handling`

- **Sample Q:** "Your agent sometimes loops forever or calls the wrong tool. How do you make it reliable?"
- **L2 anchor:** single tool-calling loop, no guardrails.
- **L4 anchor:** explicit state machine (LangGraph), checkpointing, step limits, HITL, structured failure handling; understands MCP.

### Domain 6 — Evaluation & Testing · *Critical*
Competencies: `eval design & golden datasets` · `LLM-as-a-judge` · `frameworks (RAGAS/DeepEval/Promptfoo/LangSmith)` · `regression testing` · `offline vs online eval` · `measuring agent quality`

- **Sample Q:** "How do you know your LLM app is actually good, and how do you stop it regressing when you change a prompt?"
- **L2 anchor:** eyeballs a few outputs.
- **L4 anchor:** golden datasets, LLM-as-judge with calibrated rubrics (bias-controlled), regression suites in CI, offline+online eval.

### Domain 7 — Production Architecture & Serving · *High*
Competencies: `FastAPI + streaming/WebSockets` · `caching (prompt/response)` · `model routing & fallbacks` · `latency & cost optimization` · `rate-limit & concurrency handling` · `deployment`

- **Sample Q:** "Take a working notebook prototype to a production API serving many users. What changes?"
- **L2 anchor:** wraps it in a basic endpoint.
- **L4 anchor:** streaming, caching, routing/fallbacks, concurrency + rate-limit handling, cost/latency budgets, real deployment.

### Domain 8 — Observability & LLMOps · *Medium-High*
Competencies: `tracing (LangFuse/LangSmith/Helicone)` · `token/cost monitoring` · `prompt versioning with code` · `logging I/O for debugging` · `CI/CD for LLM apps`

- **Sample Q:** "Something's wrong in production — responses got worse yesterday. How do you find out what and why?"
- **L2 anchor:** adds print statements.
- **L4 anchor:** traces per-request tokens/cost/latency, versioned prompts to reproduce, dashboards/alerts, CI for LLM changes.

### Domain 9 — Safety, Security & Responsible AI · *Medium*
Competencies: `prompt-injection defense` · `jailbreak resistance` · `guardrails` · `PII handling` · `red teaming` · `content filtering`

- **Sample Q:** "Your agent can read user-supplied documents and call tools. What could go wrong and how do you defend it?"
- **L2 anchor:** trusts inputs; basic filtering.
- **L4 anchor:** treats external content as untrusted, injection defenses, tool-permission boundaries, PII handling, red-teams proactively.

### Domain 10 — Fine-tuning & Dataset Engineering · *Low-Medium (specialization)*
Competencies: `when to fine-tune vs RAG vs prompt` · `LoRA / QLoRA` · `dataset curation` · `evaluating fine-tuned models`

- **Sample Q:** "When would you fine-tune instead of using RAG or better prompting, and how would you do it cheaply?"
- **L2 anchor:** thinks fine-tuning is the default fix.
- **L4 anchor:** decision framework (prompt→RAG→FT), LoRA/QLoRA trade-offs, dataset quality, eval of the tuned model.

---

## 4. How the coach uses this map

1. **Assess** — pick questions by weight (Critical first), adapt follow-ups to answers.
2. **Score** — LLM-judge maps each answer to L1–L5 using the level anchors above, with cited evidence (see [Design.md §6](Design.md)).
3. **Report** — strengths (≥ target), weaknesses (largest weighted gaps), current vs target radar.
4. **Coach** — target the top 2–3 gap×weight competencies; explain → challenge → exercise → resource.
5. **Track** — persist baseline→current→target; show growth on re-assessment.

## 5. Machine-readable form (`competency_map.json`) — shape

```json
{
  "proficiency_levels": [
    {"level": 1, "name": "Novice", "meaning": "..."},
    {"level": 5, "name": "Expert", "meaning": "..."}
  ],
  "domains": [
    {
      "id": "rag",
      "name": "RAG",
      "weight": "critical",
      "competencies": [
        {
          "id": "rag.chunking",
          "name": "Chunking strategies",
          "sample_question": "Design a RAG system over legal contracts...",
          "level_anchors": {
            "2": "naive fixed-size chunking + top-k",
            "4": "structure-aware chunking, hybrid + re-rank, retrieval eval"
          }
        }
      ]
    }
  ]
}
```

*Next step: generate the full `competency_map.json` from this document.*
