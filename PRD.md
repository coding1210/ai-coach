# PRD — AI Coach for Gen AI Engineers (Python)

**Status:** Draft v1 · **Date:** 2026-07-14
**Context:** Prototype built from an AI Engineer technical-interview brief. The goal is a *working, live-demoable* AI **coaching** agent — not a teaching/course platform.

---

## 1. Vision

An AI coach that behaves like a senior mentor for a Generative-AI engineer. It holds a real conversation, **diagnoses** the person's actual strengths and weaknesses across the skills a 2026 Gen AI engineer needs, produces a personalized **evaluation report**, and then **coaches** them through their specific gaps — tracking growth over time.

> One-line pitch: *"A mentor that figures out where you actually are, tells you the truth about your gaps, and coaches you forward — personalized to you, not a course everyone takes."*

## 2. Problem statement

Engineers wanting to grow in Gen AI face two bad options: (a) generic courses with fixed syllabi that ignore what they already know, or (b) expensive human mentorship that doesn't scale. There is no tool that **assesses an individual**, identifies *their* weak spots, and delivers **personalized, adaptive coaching** with a memory of their journey.

This mirrors the interview brief: *design an AI coaching platform that understands employee weaknesses, provides coaching, recommends improvements, and supports different professional backgrounds.*

## 3. Guiding principle — Coaching, NOT teaching

This is the single most important product decision. Every feature must respect it.

| Teaching (explicitly rejected) | Coaching (what we build) |
| --- | --- |
| Fixed syllabus, everyone same path | Diagnose the individual, personalized focus |
| Sequential lessons → quizzes → unlock next level | Adaptive conversation → identify gaps → coach those |
| Progress = % of course completed | Progress = movement on *your* weak areas over time |
| Content delivery | Mentorship, challenge, growth mindset |

The competency framework (see [Syllabus.md](Syllabus.md)) is used as an **internal diagnostic rubric** the coach assesses *against* — it is never "delivered" to the user as a curriculum.

## 4. Target users & personas

**Primary persona — "Leveling-up Lena"**
- 1–3 yrs Python, moving into Gen AI engineering.
- Knows some LangChain/RAG from tutorials, unsure what she's actually weak at.
- Goal: become job-ready / promotable as a Gen AI engineer.

**Secondary persona — "Pivoting Pavan"**
- Experienced backend dev, strong Python, new to LLMs/agents.
- Needs to know which Gen AI skills to prioritize given his existing strengths.

Both need: honest diagnosis, prioritized focus, and a coach that remembers them.

## 5. Goals & non-goals

**Goals (MVP)**
- G1 — Conduct an adaptive, interview-style **assessment** across the Gen AI competency map.
- G2 — Score each competency to a proficiency level (L1–L5) with evidence.
- G3 — Produce a clear **evaluation report**: strengths, weaknesses, current vs target.
- G4 — Deliver **personalized coaching** on the top-priority gaps (explain, challenge, assign a practical exercise, point to resources).
- G5 — Persist a **progress ledger** and show growth deltas on re-assessment.
- G6 — Work in **chat and voice**, with a reliable **live demo**.

**Non-goals (v1)**
- Not a course/LMS with lessons and unlockable levels.
- No fine-tuning, certificates, or multi-user cohorts.
- No mobile app (responsive web only).
- Not tied to real-time speech-to-speech APIs (using simple STT+TTS — see [techstack.md](techstack.md)).

## 6. Success metrics

Because this is a prototype, "success" = **demonstrated capability + business framing**, not scale.

| Metric | Target |
| --- | --- |
| Assessment → report round trip | Completes in a single session, < 10 min |
| Voice turn latency (STT→LLM→TTS) | < 1s median (perceived-conversational) |
| Diagnosis quality | Scores agree with a human rater on a small labeled sample (rubric-calibrated) |
| Coaching relevance | Coaching targets the diagnosed top-gap competencies, not generic advice |
| Reliability | Live demo runs end-to-end with zero hard failures (fallbacks wired) |
| Cost | ~\$0 at demo scale (free tiers + browser voice) |

## 7. Core user journey

1. **Onboard** — user states goal/role and background (e.g., "backend dev targeting senior Gen AI role").
2. **Assess** — coach asks adaptive, open-ended questions, probing Critical→High→Medium competencies; adjusts depth to answers.
3. **Report** — coach presents an evaluation: strengths, weaknesses, current vs target per domain (radar view).
4. **Coach** — coach picks the top 2–3 highest-gap/highest-weight competencies and mentors on them: explains, poses a scenario/challenge, assigns a small exercise, offers resources (via tool call).
5. **Return** — later, coach remembers the user, re-assesses focus areas, and shows growth ("RAG evaluation: Aware → Working").

## 8. Functional requirements

- **FR1 Adaptive assessment** — question selection driven by competency weights and prior answers; conversational, not a quiz form.
- **FR2 Proficiency scoring** — LLM-as-judge scores each competency L1–L5 against the rubric with cited evidence; controls for verbosity/position bias (see [Design.md](Design.md)).
- **FR3 Evaluation report** — strengths, weaknesses, per-domain current vs target, prioritized focus list.
- **FR4 Personalized coaching** — targeted at diagnosed gaps; includes explanation, challenge, exercise, resource.
- **FR5 Tool use** — at minimum: internet research for resources; schedule/return follow-up (demonstrates agentic tool-calling).
- **FR6 Memory & progress** — persistent per-user proficiency ledger (baseline → current → target) with growth deltas.
- **FR7 Multi-background support** — assessment adapts to the user's stated background/goal.
- **FR8 Interfaces** — chat (primary) + voice (STT in, TTS out), responsive web UI with report/progress views.

## 9. Non-functional requirements

- **Latency:** conversational feel; token streaming; voice turn < ~1s median.
- **Cost:** free tiers + client-side voice → ~\$0 at demo scale; GPT used surgically for high-value scoring.
- **Reliability:** every external dependency has a fallback; demo runs locally + tunnel to avoid cold starts.
- **AI-first build:** specs and code generated with AI coding assistants; target 1.5–2 week build.
- **Observability:** trace LLM calls, token/cost, and scoring decisions for debugging and the demo narrative.

## 10. Scope & phasing (MVP)

- **Phase 0 (~2d):** competency map as data (`competency_map.json`), this PRD, [Design.md](Design.md), [techstack.md](techstack.md), [Syllabus.md](Syllabus.md).
- **Phase 1 (~4–5d):** text coaching loop — FastAPI + LangGraph (Assess→Score→Report→Coach→Re-assess), Supabase ledger, Next.js chat + report view.
- **Phase 2 (~3–4d):** voice loop (Groq Whisper → agent → Kokoro), progress dashboard (radar + history), tool-calling demo, reliability/fallback pass, local+tunnel demo.

## 11. Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Drifts back into "teaching" | Principle §3 enforced in prompts, report, and coaching nodes; competency map stays internal |
| Live-demo failure risk | Run locally + tunnel; fallbacks on every dependency; dry-run script |
| Scoring feels arbitrary | Rubric-based LLM-judge with cited evidence; calibrate on a small human-labeled sample |
| Free-tier rate limits mid-demo | Groq→Gemini fallback; GPT as paid backstop for scoring |
| Voice latency too high | Browser-side TTS (Kokoro/Web Speech); STT via fast Groq Whisper |

## 12. Open questions

- Depth of voice in the demo — full voice loop or voice as a "wow" add-on to a chat-first demo?
- Target-role presets (Junior/Mid/Senior Gen AI) — ship presets or infer target from the conversation?
- How many competencies to assess in one session vs. progressive assessment across sessions?

---
*Related: [Design.md](Design.md) · [techstack.md](techstack.md) · [Syllabus.md](Syllabus.md)*
