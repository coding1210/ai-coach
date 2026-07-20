# AI Coach — User Experience

A walkthrough of the product end to end, captured by driving the running app
through a full journey: onboarding → coaching diagnosis → evaluation + roadmap →
the practice/learning loop.

> Persona used for the run: a backend dev with a couple of RAG apps and a small
> agent, weak on evaluation, aiming for a senior Gen AI role.

## 1. Arrival — the front door disarms you

The landing page doesn't open with a form; it opens with **"How this works"** in
three plain lines ("Answer a few questions — there are no wrong answers → See
where you stand → Get a plan"). Under it, just two fields — goal and background —
and *Start assessment*. Everything advanced (mock interview, from-code, role
targeting, JD) is folded behind **"More options."**

**Feel:** calm and un-intimidating. A newcomer isn't asked to self-classify or
face a wall of choices. The most reassuring detail is the tiny **"Coming back?
Restore your progress"** at the bottom — it signals your work is saved before
you've done any.

## 2. Coaching — a conversation, not a quiz

It greets you like a person: *"Hey — good to meet you. I'm your Gen AI coach, and
this is a conversation, not a test."* Then it asks a **real, scenario-based
question** ("walk me through chunking a company's legal contracts — what
trade-offs did you make?"), adapting to what you say. The right pane sits in a
quiet **"Coach speaking…"** state, promising the evaluation will build there.

**Feel:** genuinely coach-like. The phase badge, a voice toggle, and a hands-free
("HF") mode are unobtrusive in the header. It never feels like filling in a
scantron. The one honest friction: if you're vague, it probes rather than teaches
— good for the confident, occasionally frustrating for the truly lost (the
"Explain this" affordance and beginner reframing exist to catch that).

## 3. The evaluation — honest, and it lands

When enough is probed, the report reveals in the right pane — sections **stagger
in**, the **radar shape grows** from the center, and the **level bars fill**. It
shows *Where you stand*: competencies assessed, a current-vs-target radar, and a
benchmark. Crucially the benchmark is labeled **"vs a reference prior (not a live
cohort)"** — the product refuses to pass a seeded estimate off as real peer data.
The run read "RAG — 81st percentile, ahead of most."

**Feel:** the motion makes a dense screen legible instead of dumping it. The
honesty of the benchmark label is unusual and builds trust rather than eroding it.

## 4. The plan — a roadmap, not a syllabus

Below the radar: **"Your growth path · the next couple of months."** Each
milestone (e.g. *LLM-as-a-judge, L1→L4*) carries a one-line **plain-language
gloss** ("Using an LLM to grade outputs — fairly, without it fooling itself"), a
**"⏱ a couple of weeks"** effort chip, *what good looks like*, concrete practice
steps, a success **Signal**, two **resource links**, and a **"Try the graded
challenge"** button. There's a **Share growth** control and a **recovery-code**
save.

**Feel:** this is where "coach, not course" becomes concrete — everything is about
*your* gaps, prioritized, sized, and doable. It reads as a personal plan, not a
catalog.

## 5. Learning — the practice loop (the new heart)

Hitting **Practice**, the surface is already seeded by the diagnosis: **"Today's
reps"** lists your exact gaps (Tokenization, Sampling params, Eval design), plus
*Practice my top gap*, *Real-world project*, and a competency picker. *Top gap*
generated the **LLM-as-a-judge code rep**. Asking for a **hint** returned a
Socratic nudge ("what's the first thing you do with `answer` and `reference`…
given `answer` could be anything?") — a prompt to think, not the answer. A real
`judge()` implementation graded **L4, target L4, "Cleared — you hit the target,"
95% confidence**, with code-judge evidence citing the actual lines. Then **"Next
rep · L4"** to keep climbing toward mastery, and a **mastery panel** ("0 held · 1
in progress") tracking it.

**Feel:** this is the moment the product stops being an examiner and becomes a
coach. Attempt → honest grade → hint if stuck → push to the next rung. It works
for competencies that have *no* code exercise too (design/critique/explain reps),
so the whole map is practicable.

## What's genuinely strong

- **Coaching-not-teaching is real, not a slogan** — every screen is about your own
  weak areas.
- **Honesty as a feature** — evidence-cited grades, the relabeled benchmark,
  "reference prior not a cohort," confidence shown.
- **Beginner-first craft** — glosses, effort estimates, encouragement, plain
  language lower the intimidation that kills most learning tools at the door.
- **Motion with purpose** — the report reveal aids comprehension; nothing is
  animated for show.
- **The loop closes** — diagnosis flows straight into a seeded, prioritized
  practice queue.

## Honest friction (what to watch)

- **Grading calibration on judgment reps** runs a touch strict (a strong answer
  landing a level below target); the multi-rep mastery model smooths this, but
  single reps can feel harsh.
- **The conversational coach can over-probe** a genuinely lost beginner instead of
  teaching — the philosophy's sharpest edge.
- **Session durability** — mastery/history live in-process today, so a server
  restart loses them; the recovery-code covers the token, not the practice trail
  yet (durable Postgres tables are a go-live item).
- **It still can't *prove* it makes you job-ready** — the data path
  (outcome↔mastery) exists, but the claim is honestly scoped to "demonstrated
  practice," not "you'll pass the interview."

## One-line summary

It takes you from *"I don't know where I stand"* → *a truthful, personal
diagnosis* → *a sized, resourced plan* → *actual graded practice that pushes you
up the levels* — a coach that both **tells you the truth and works the reps with
you**, while being unusually honest about the limits of what it can claim.
