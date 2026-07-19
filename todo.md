# Development-Coach Loop — Build Plan

Turns the product from **examiner + GPS** (diagnose + plan) into a **development
coach** (polish skill) with a practice→feedback→revise→master loop that spans all
~59 competencies, not just the 16 with code exercises.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done. Each phase ships something usable.

---

## Shared data model (define once, in Phase 1)

- [x] `Rep` type: `{id, competency_id, type(code|design|critique|explain|project), target_level, difficulty, prompt, language?, given_artifact?, audience?, rubric, checks?, tests?, source(seed|generated), exemplar_of?}`
- [x] `RepAttempt` (persisted): `{id, user_id, competency_id, rep_id, type, target_level, submission, level_awarded, passed, confidence, feedback, hints_used, attempt_no, created_at}`
- [x] `Mastery` (per user×competency): `{competency_id, level, confidence, reps_cleared_at_level, last_practiced_at, next_rep_due_at, status(unseen|practicing|held|needs_refresh)}`
- [x] Client-safe Rep view (rubric/checks/tests withheld) — mirror the ExerciseOut pattern

---

## Phase 1 — Rep engine (generate → validate → grade), read-only mastery

**Goal:** practice a competency with no code exercise and get developmental feedback.

### Generation
- [x] `app/coaching/reps.py` with per-type prompt templates (code, design, critique, explain)
- [x] `generate_rep(competency, target_level, type)` via `router.complete_json`, grounded in level anchors + weight
- [x] Few-shot exemplars: reuse the 16 code exercises; add `backend/exercises/rep_exemplars.json` (≥2 hand-written per non-code type)
- [x] Rep cache in repo aux store, keyed `(competency_id, type, level)`; reuse validated reps

### Validation (load-bearing)
- [x] `validate_rep(rep)` — 2nd LLM pass: unambiguous, gradable rubric present, requires reasoning (not googleable recall), difficulty matches target_level, self-contained
- [x] Bounded regenerate on reject; fall back to a seed rep when available
- [x] Unit test: planted ambiguous/googleable rep is rejected

### Grading
- [x] `grade_rep(rep, submission) -> {level, passed, confidence, evidence, criteria_results[]}`
- [x] Code reps reuse `grader.grade_submission` (checks + sandbox + code-judge)
- [x] Non-code reps: rubric-judge citing per-criterion hit/miss; ensemble for level; require concrete evidence to pass (e.g., must name the failure mode)
- [x] Extend `judge.py` schema/prompt for rubric-criteria grading

### API + frontend
- [x] `POST /practice/rep` {competency_id, type?} → client-safe Rep (auth-scoped)
- [x] `POST /practice/grade` {rep_id|rep, submission} → grade result
- [x] `RepCard` component (text input or code editor by type); reuse ChallengePanel bones
- [x] Minimal Practice entry: "practice my top gap" → RepCard → grade + criteria breakdown

### Tests / acceptance
- [x] Batch test: valid gradable rep for ≥90% of top ~15 code-less high-weight competencies
- [x] Grading discriminates strong vs hand-wavy (structure via FakeProvider + small real-model batch)
- [x] `/practice/rep` leaks no rubric/tests to client (test)
- [x] Live round-trip on a non-code competency (e.g. `rag.when_not`, `eval.design_golden`)
- [x] tsc + build + `pytest` + `ruff` green

---

## Phase 2 — Iterate loop + graduated hints + evidence-weighted mastery

**Goal:** the actual polishing, and an honest measure of movement.

### Practice sub-graph (LangGraph)
> Implemented as a REST loop (/practice/rep · /grade · /hint · /next), not graph nodes — the submit→grade→hint→advance mechanic is request/response and needs no interrupt machinery (YAGNI).
- [x] State fields for practice mode in `app/graph/state.py`
- [x] Nodes: `select_competency → generate_or_fetch_rep → await_submission(interrupt) → grade_rep → feedback → route`
- [x] Wire in `build.py` + `edges.py`; `requested_mode == "practice"` alongside coach/interview
- [x] Route logic: cleared → advance; struggling → revise/scaffold; enough clears → schedule respacing

### Graduated hints
- [x] `app/coaching/hints.py`: `hint(rep, submission, tier)` — nudge → targeted → worked fragment
- [x] Reveal on request; track `hints_used`; never emit the full answer
- [x] `POST /practice/hint`

### Advance / difficulty
- [x] Clear a rep → serve next-harder rep up the L-ladder toward target
- [x] Fails + hints exhausted → drop difficulty or serve a scaffolded rep (no dead-ends)
- [x] "Held at Ln" = N spaced clears at level (config, e.g. `MASTERY_CLEARS=2`)

### Mastery + persistence
- [x] Repo: `upsert_rep_attempt`, `get_rep_attempts`, `get_mastery`, `upsert_mastery` (memory + postgres + base)
- [ ] `schema.sql` tables: `rep_attempts`, `mastery`
- [x] Recompute ledger `current_level` **evidence-weighted**: demonstrated reps override conversational scores; confidence rises with reps + code/critique type
- [x] Report: show "earned by: demonstrated vs stated" + confidence

### Scheduling / sequencing
- [x] Extend scheduler: cleared competency → spaced *practice* re-rep (SM-2-lite by mastery)
- [x] `GET /practice/next` = roadmap priority × due × mastery status (the session queue)
- [x] `GET /practice/mastery`
- [x] `backend/competency/prereqs.json`; selection respects prereqs (no `hybrid_rerank` before `embeddings`)

### Frontend
- [x] Full Practice surface: session queue ("today's reps"), revise/resubmit, "get a hint" (escalating)
- [x] Per-competency mastery trajectory (attempts over time)
- [x] "Next rep" / "next competency" flow; wire as a mode in `page.tsx`
- [x] DueNudge can launch practice (not just re-assessment)

### Tests / acceptance
- [x] Live: L1→target climb flips mastery to "held" + confidence rises
- [x] Hint-exhaustion path drops difficulty / scaffolds — never a dead-end
- [x] Practiced competency reads high-confidence; never-practiced stays low-confidence
- [ ] Spaced re-rep appears in `/practice/next` after interval (time-controlled test)
- [x] Prereq gating verified (test)
- [x] tsc + build + `pytest` + `ruff` green

---

## Phase 3 — Real-world reps, honest trajectory, telemetry, retention

**Goal:** extend to real work, replace the invented benchmark, self-improve reps, close retention.

### Project (real-world) reps
- [ ] `project` rep type: assign a real task + "bring your artifact/repo" checkpoint
- [ ] Grade returned artifact via existing `code_diagnosis`, scoped to the competency
- [ ] `/practice/next` can surface a project rep with a "come back with X" instruction + submit path

### Honest trajectory UI
- [ ] Per-competency level-over-time from `rep_attempts`
- [ ] Overall "demonstrated readiness" view (demonstrated vs stated, confidence, reps behind each level)
- [ ] Remove the seeded benchmark for individuals OR relabel clearly "reference prior, not a cohort"

### Telemetry + self-pruning
- [ ] Log rep outcomes: abandon rate, flag rate, pass-rate distribution, hint-exhaustion
- [ ] `flag rep` action from the UI
- [ ] Auto-demote reps with bad stats; internal rep-quality view

### Retention
- [ ] Substance-based streak (reps cleared, not logins — stays anti-gamified)
- [ ] In-app spaced-practice nudges; resume-your-queue
- [ ] Optional lightweight goal ("clear 3 reps this week")

### Validity groundwork + freshness
- [ ] Join `record_outcome` to mastery snapshots (data path only; no predictive claim yet)
- [ ] Wire `refresh_resources` hook / periodic exemplar regeneration so reps + anchors don't rot

### Tests / acceptance
- [ ] `project` rep round-trips: assigned → repo → code_diagnosis → mastery updates
- [ ] Individual report shows a real trajectory; fake benchmark gone or relabeled
- [ ] Flagging removes a rep from rotation; telemetry view shows per-rep pass/abandon rates
- [ ] Spaced nudge returns user to a non-empty practice queue (time-controlled test)
- [ ] Outcome↔mastery join exists in a query
- [ ] tsc + build + `pytest` + `ruff` green

---

## Cross-cutting prerequisites (block Phase 2+)

- [ ] Rate-limit + per-session usage cap (the loop is LLM-heavy) — also needed for go-live
- [ ] Rep caching in place (cost + consistency)
- [ ] Sandbox stays opt-in (`ENABLE_SANDBOX` off by default)
- [ ] Postgres in prod (mastery/history must survive restarts)
- [ ] Minimal CI (pytest+ruff / tsc+build) so branch merges are gated

## Working rules

- [ ] One feature branch off `main` per phase (`feature/practice-loop-p1`, `-p2`, `-p3`)
- [ ] Verify live in the browser before each merge; keep the build green at every commit
- [ ] Scan every commit for API-key strings; keys stay in gitignored `.env`

## Honest limits to keep visible

- Judgment reps (design/critique/explain) are more gameable than code reps — weight code/critique higher in the mastery signal.
- Generated-rep quality is the whole ballgame; the validator + telemetry are what keep it trustworthy.
- Mastery predicting real hiring outcomes stays an **assumption** until outcome data proves it — the trajectory claims "demonstrated practice," not "job guaranteed."
