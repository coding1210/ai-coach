# Development-Coach Loop — Build Plan

Turns the product from **examiner + GPS** (diagnose + plan) into a **development
coach** (polish skill) with a practice→feedback→revise→master loop that spans all
~59 competencies, not just the 16 with code exercises.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done. Each phase ships something usable.

---

## Shared data model (define once, in Phase 1)

- [ ] `Rep` type: `{id, competency_id, type(code|design|critique|explain|project), target_level, difficulty, prompt, language?, given_artifact?, audience?, rubric, checks?, tests?, source(seed|generated), exemplar_of?}`
- [ ] `RepAttempt` (persisted): `{id, user_id, competency_id, rep_id, type, target_level, submission, level_awarded, passed, confidence, feedback, hints_used, attempt_no, created_at}`
- [ ] `Mastery` (per user×competency): `{competency_id, level, confidence, reps_cleared_at_level, last_practiced_at, next_rep_due_at, status(unseen|practicing|held|needs_refresh)}`
- [ ] Client-safe Rep view (rubric/checks/tests withheld) — mirror the ExerciseOut pattern

---

## Phase 1 — Rep engine (generate → validate → grade), read-only mastery

**Goal:** practice a competency with no code exercise and get developmental feedback.

### Generation
- [ ] `app/coaching/reps.py` with per-type prompt templates (code, design, critique, explain)
- [ ] `generate_rep(competency, target_level, type)` via `router.complete_json`, grounded in level anchors + weight
- [ ] Few-shot exemplars: reuse the 16 code exercises; add `backend/exercises/rep_exemplars.json` (≥2 hand-written per non-code type)
- [ ] Rep cache in repo aux store, keyed `(competency_id, type, level)`; reuse validated reps

### Validation (load-bearing)
- [ ] `validate_rep(rep)` — 2nd LLM pass: unambiguous, gradable rubric present, requires reasoning (not googleable recall), difficulty matches target_level, self-contained
- [ ] Bounded regenerate on reject; fall back to a seed rep when available
- [ ] Unit test: planted ambiguous/googleable rep is rejected

### Grading
- [ ] `grade_rep(rep, submission) -> {level, passed, confidence, evidence, criteria_results[]}`
- [ ] Code reps reuse `grader.grade_submission` (checks + sandbox + code-judge)
- [ ] Non-code reps: rubric-judge citing per-criterion hit/miss; ensemble for level; require concrete evidence to pass (e.g., must name the failure mode)
- [ ] Extend `judge.py` schema/prompt for rubric-criteria grading

### API + frontend
- [ ] `POST /practice/rep` {competency_id, type?} → client-safe Rep (auth-scoped)
- [ ] `POST /practice/grade` {rep_id|rep, submission} → grade result
- [ ] `RepCard` component (text input or code editor by type); reuse ChallengePanel bones
- [ ] Minimal Practice entry: "practice my top gap" → RepCard → grade + criteria breakdown

### Tests / acceptance
- [ ] Batch test: valid gradable rep for ≥90% of top ~15 code-less high-weight competencies
- [ ] Grading discriminates strong vs hand-wavy (structure via FakeProvider + small real-model batch)
- [ ] `/practice/rep` leaks no rubric/tests to client (test)
- [ ] Live round-trip on a non-code competency (e.g. `rag.when_not`, `eval.design_golden`)
- [ ] tsc + build + `pytest` + `ruff` green

---

## Phase 2 — Iterate loop + graduated hints + evidence-weighted mastery

**Goal:** the actual polishing, and an honest measure of movement.

### Practice sub-graph (LangGraph)
- [ ] State fields for practice mode in `app/graph/state.py`
- [ ] Nodes: `select_competency → generate_or_fetch_rep → await_submission(interrupt) → grade_rep → feedback → route`
- [ ] Wire in `build.py` + `edges.py`; `requested_mode == "practice"` alongside coach/interview
- [ ] Route logic: cleared → advance; struggling → revise/scaffold; enough clears → schedule respacing

### Graduated hints
- [ ] `app/coaching/hints.py`: `hint(rep, submission, tier)` — nudge → targeted → worked fragment
- [ ] Reveal on request; track `hints_used`; never emit the full answer
- [ ] `POST /practice/hint`

### Advance / difficulty
- [ ] Clear a rep → serve next-harder rep up the L-ladder toward target
- [ ] Fails + hints exhausted → drop difficulty or serve a scaffolded rep (no dead-ends)
- [ ] "Held at Ln" = N spaced clears at level (config, e.g. `MASTERY_CLEARS=2`)

### Mastery + persistence
- [ ] Repo: `upsert_rep_attempt`, `get_rep_attempts`, `get_mastery`, `upsert_mastery` (memory + postgres + base)
- [ ] `schema.sql` tables: `rep_attempts`, `mastery`
- [ ] Recompute ledger `current_level` **evidence-weighted**: demonstrated reps override conversational scores; confidence rises with reps + code/critique type
- [ ] Report: show "earned by: demonstrated vs stated" + confidence

### Scheduling / sequencing
- [ ] Extend scheduler: cleared competency → spaced *practice* re-rep (SM-2-lite by mastery)
- [ ] `GET /practice/next` = roadmap priority × due × mastery status (the session queue)
- [ ] `GET /practice/mastery`
- [ ] `backend/competency/prereqs.json`; selection respects prereqs (no `hybrid_rerank` before `embeddings`)

### Frontend
- [ ] Full Practice surface: session queue ("today's reps"), revise/resubmit, "get a hint" (escalating)
- [ ] Per-competency mastery trajectory (attempts over time)
- [ ] "Next rep" / "next competency" flow; wire as a mode in `page.tsx`
- [ ] DueNudge can launch practice (not just re-assessment)

### Tests / acceptance
- [ ] Live: L1→target climb flips mastery to "held" + confidence rises
- [ ] Hint-exhaustion path drops difficulty / scaffolds — never a dead-end
- [ ] Practiced competency reads high-confidence; never-practiced stays low-confidence
- [ ] Spaced re-rep appears in `/practice/next` after interval (time-controlled test)
- [ ] Prereq gating verified (test)
- [ ] tsc + build + `pytest` + `ruff` green

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
