# Tech Stack — AI Coach for Gen AI Engineers

**Status:** Draft v1 · **Date:** 2026-07-14
**Companion to:** [PRD.md](PRD.md) · [Design.md](Design.md)

Selection criteria, in priority order: **(1) lowest latency**, **(2) ~zero cost at prototype scale**, **(3) simplicity / fast AI-first build**, **(4) demo reliability**. GPT API is available and used surgically where quality matters most.

---

## 1. Stack at a glance

| Layer | Choice | Cost | Why |
| --- | --- | --- | --- |
| **LLM — fast turns** | **Groq** `llama-3.3-70b-versatile` (+ `llama-3.1-8b-instant` for routing/scoring helpers) | Free tier | Fastest hosted inference (280–390 TPS on 70B; 560–840 on 8B). Free, no card. Dominates perceived voice latency. |
| **LLM — scoring & report** | **GPT** (reasoning-grade) | Paid, pennies at demo scale | High-stakes diagnosis quality; where correctness shows. Used only for `score`/`report` nodes. |
| **LLM — fallback** | **Google Gemini 3.5 Flash** | Free tier (~1,500 req/day) | Larger context + resilience if Groq rate-limits mid-demo. |
| **STT** | **Groq Whisper** `whisper-large-v3-turbo` | Free (~2,000 req/day) | Near-realtime (164–299× speed), same vendor/key as the LLM. |
| **STT fallback** | **Browser Web Speech API** | \$0 | Zero infra, no server round-trip. |
| **TTS** | **Kokoro-82M** (in-browser, WebGPU/WASM) | \$0 | Runs client-side → no network hop, natural voice, Apache-2.0, faster-than-realtime. |
| **TTS fallback** | **Web Speech `SpeechSynthesis`** | \$0 | Instant, bulletproof backup. |
| **Agent orchestration** | **LangGraph** | OSS | Coaching flow is a stateful graph; checkpointing + HITL; interviewer expects it. |
| **Backend** | **FastAPI + WebSockets** | OSS | Streaming for low perceived latency; interviewer-named. |
| **Frontend** | **Next.js + React** | OSS | Fast to scaffold AI-first; hosts client-side Kokoro/Web Speech. |
| **Persistence / memory** | **Supabase** (Postgres + pgvector) | Free tier | Proficiency ledger, sessions; pgvector = optional RAG; also LangGraph PostgresSaver. |
| **Demo hosting** | **Local + Cloudflare Tunnel / ngrok** | \$0 | No cold starts, lowest latency, most reliable live demo. |
| **Persistent URL (optional)** | **Render free** or **HF Spaces** | Free tier | For a shareable link; note free tiers *sleep* (cold starts). |

**Effective running cost at demo scale: ~\$0** (GPT scoring is cents).

## 2. Model routing strategy

Per-task model selection is itself part of the "business/architecture thinking" the interviewer wanted:

| Task | Model | Rationale |
| --- | --- | --- |
| Conversational assessment turns | Groq 70B | Speed dominates the felt experience |
| Question/ follow-up generation | Groq 8B or 70B | Cheap, fast, good enough |
| **Scoring (LLM-as-judge)** | **GPT** | Accuracy is the product's credibility |
| **Evaluation report synthesis** | **GPT** | High-value, user-facing quality |
| Coaching explanations | Groq 70B (GPT if depth needed) | Fast, conversational |
| Fallback (any) | Gemini Flash free | Resilience / rate-limit safety |

## 3. Voice pipeline rationale

Chose a **simple stitched pipeline** (STT → LLM → TTS) over real-time speech-to-speech (deliberately, per product decision):

```
mic → Groq Whisper (STT) → LangGraph/LLM → Kokoro (TTS) → speaker
```

- Latency ~<1s median — natural for coaching, far simpler to build.
- Cost ~\$0 (free STT + browser TTS).
- Three swappable parts → graceful degradation, not demo death.
- Rejected **OpenAI Realtime API**: sub-300ms but paid ($32/$64 per 1M audio tokens) and more coupling than needed for v1.

## 4. Alternatives considered & rejected

| Option | Verdict | Reason |
| --- | --- | --- |
| **Cerebras** (LLM) | Keep as backup | Even faster (up to 2,000 TPS) but Groq's ecosystem/tooling is more mature for a 1–2 wk build |
| **Deepgram** (STT) | Rejected v1 | Lowest streaming latency (200–400ms) but paid; Groq Whisper is free + fast enough |
| **OpenAI Whisper/TTS** | Rejected | We have the key, but Groq STT is free/faster and Kokoro TTS is free/local |
| **Piper** (TTS) | Rejected | Slightly faster than Kokoro but more robotic; coach should sound human |
| **Pipecat / LiveKit** | Deferred to "production path" | Right for production voice at scale; too much complexity for a demo. Mention as scaling story. |
| **OpenAI Realtime API** | Deferred | Best latency but paid + coupled; revisit if voice becomes the headline feature |
| **Fly.io** (hosting) | Rejected | No longer a free tier for new users |
| **Railway** (hosting) | Marginal | Only ~\$1/mo credit — can't stay online 24/7 |

## 5. Cost analysis (prototype scale)

| Item | Cost |
| --- | --- |
| Groq LLM + Whisper STT | \$0 (free tier) |
| Gemini fallback | \$0 (free tier) |
| Kokoro / Web Speech TTS | \$0 (client-side) |
| Supabase | \$0 (free tier) |
| Hosting (local + tunnel) | \$0 |
| GPT (scoring/report) | ~cents per demo session |
| **Total** | **≈ \$0** |

Scaling path (post-demo): move scoring volume to Groq/Gemini, add caching + model routing, adopt Pipecat/LiveKit for production voice, upgrade Supabase/hosting tiers.

## 6. Build tooling (AI-first)

Per interviewer expectation — generate specs and code, validate, integrate, focus on architecture:
- **Claude Code / Cursor** for scaffolding and codegen.
- Specs (this doc set) drive generation.
- Target timeline: **1.5–2 weeks**.

---

## Sources
- [Free LLM APIs 2026 — OpenRouter](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/)
- [Free LLM API Tiers 2026 — Paterson](https://ianlpaterson.com/blog/free-llm-api-2026/)
- [Groq Free Tier Limits 2026 — TokenMix](https://tokenmix.ai/blog/groq-free-tier-limits-2026)
- [Groq Speech-to-Text — GroqDocs](https://console.groq.com/docs/speech-to-text)
- [Best STT Providers 2026 — Coval](https://www.coval.ai/blog/best-speech-to-text-providers-in-2026-independent-benchmarks-and-how-to-choose/)
- [Browser TTS Showdown: Kokoro vs Piper — OfflineTTS](https://offlinetts.com/blog/browser-tts-showdown-kokoro-piper-kitten/)
- [OpenAI Realtime voice cost & latency 2026 — TokenMix](https://tokenmix.ai/blog/openai-realtime-voice-api-2026-cost-latency)
- [Voice Agent Frameworks: LiveKit & Pipecat — Arun Baby](https://www.arunbaby.com/ai-agents/0018-voice-agent-frameworks/)
- [Free Backend Hosting 2026 — SnapDeploy](https://snapdeploy.dev/blog/free-backend-hosting-2026-apis-servers)
- [LangGraph Persistence — LangChain docs](https://docs.langchain.com/oss/python/langgraph/persistence)
