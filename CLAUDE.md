# CLAUDE.md — Orientation

**Read `Practice.md` first.** It is the methodology this document set is
built to satisfy — the vocabulary, the evidence standard, and the review
protocol (§19) all come from there, not from this file. This file exists
only to tell you where to go next.

## ARCHITECTURE FREEZE IN EFFECT (ratified 2026-08-28) — read this before touching the reformulation engine

The reformulation pipeline (`reformulate.py`, `rephrase.py`,
`semantic.py`, `combined_score()`'s ranking formula, and every gate/
blocklist accumulated across Phases 11/11B/11C and Architecture Gate
Step 1 — code unchanged since commit `7451ec4`, tagged
`architecture-freeze-v1`) is **frozen as the maintained/shipped
baseline**, per the user's explicit ratification after a formal 4-step
Architecture Go/No-Go assessment. Full record: `VALIDATION.md` §§52-56,
`DECISION_LOG.md` 2026-08-27-E through 2026-08-28-I, `eval/
step3_architecture_assessment.md`, `eval/step4_recommendation.md`.

**Do not propose or implement further rules, gates, ranking-weight
changes, threshold changes, or blocklist entries in response to an
individually-observed failure** — that is exactly the "Phase 11D/E/F"
pattern this arc was opened to stop, and the evidence (measured CLEAN
rate plateaued at 31-34% across three further phases of real fixes;
dense/multi-constraint profiles at 0% CLEAN on both the original and a
completely fresh corpus; a ~10-13 point fresh-corpus generalization
gap) says that style of fix has hit its ceiling. Do not propose a
learned component (reranker, WSD model, etc.) on the current evidence
either — this project's own Phase 9B/9C precedent (a prior learned
validator failing 99% of the time on held-out data) plus the fresh-
corpus result argue against it generalizing any better, for reasons
detailed in the documents above.

This is **not** project abandonment: routine maintenance continues, and
the frozen architecture is the **reference baseline** any future,
fundamentally different approach must beat. Reopening optimization
work requires new evidence: (1) a substantially larger, independently
collected labeled dataset, or (2) a genuinely different modeling
approach that clears this project's own held-out generalization bar
before being trusted over the frozen baseline. **Condition (2) now has
a named container**, opened 2026-08-30: `LEARNED_REFORMULATION_RESEARCH.md`
(Stage 8), developed on branch `research/stage8-learned-reformulation`,
never on `main` — see `DECISION_LOG.md` 2026-08-30-B. `main` stays the
frozen, shipped implementation; anyone building against this repo
(including partners integrating it with the separate Audio Module)
should track `main`, not that branch. If neither condition is
met, the correct response to a newly observed failure is to note it
(e.g. in `REFORMULATION_PROBLEM_MAP.md`, still useful as a living
record of failure modes) — not to patch it.

## Reading order for a cold start

1. `Practice.md` (external — the governing methodology; not reproduced here)
2. `HANDOFF.md` — what's proven vs. hypothesis, how to run things, pitfalls
3. `DOCS.md` — one line per file in the repo, so you know what to open
4. `DECISION_LOG.md` — the append-only record of why things are the way they are
5. `VALIDATION.md` — what has actually been measured, and its named limitations
6. `RESEARCH.md` — the literature/technical-approach review (Practice.md §7's
   literature pass) and the resulting critical assessment of this repo's own
   implementation, component by component — read before proposing any
   architecture change
7. `PROBLEM_FORMULATION.md` — the Stage 4A design record for the persistent
   speaker difficulty profile (sounds/words/phrases): schema, representation
   research, the text-entry/flagging interaction, and what's deliberately
   deferred — read before touching `difficulty_profile.py` or the profile UI
8. `REFORMULATION_RESEARCH.md` — Stage 5's deep research pass on the
   reformulation engine itself: minimal-edit architectures, phoneme-position/
   stress granularity, hardware feasibility, failure modes, and a ranked,
   evidence-based architecture recommendation — **read this before designing
   or implementing any reformulation-engine change**; it's the document that
   should drive that decision, not `RESEARCH.md` alone
9. `REFORMULATION_PROBLEM_MAP.md` — the **living** Problem Definition /
   Research Map for the reformulation engine, opened 2026-08-17 once real
   pilot evidence showed the engine is a multi-factor research problem
   (intent inference from malformed input, in-context meaning preservation,
   grammaticality, naturalness/idiomaticity, profile-difficulty resolution,
   word sense, cross-substitution interaction, restructuring vs.
   substitution, and the help-vs-harm change budget), not a single
   word-substitution problem — still useful as a living record of failure
   modes under the architecture freeze above, but **not** a queue of fixes
   to implement against the frozen baseline
10. `VALIDATION.md` §§52-56 / `eval/step3_architecture_assessment.md` /
    `eval/step4_recommendation.md` — the Architecture Go/No-Go arc: the
    formal 4-step evidence-gathering process (port the best-known
    generation fix, diagnose the dominant failure class, assess against
    8 named criteria including a fresh-corpus generalization check, then
    a ratified 3-way decision) that produced the freeze above — **read
    this before forming any opinion on whether the reformulation engine
    needs more engineering work**; it's the most complete evidence this
    project has on that exact question
11. `ROADMAP.md` — what's next (now: nothing on the reformulation engine
    itself, per the freeze; other items are unaffected), and the finding
    or gap that justifies each item
12. `CHANGELOG.md` — fast-scan index into the decision log

## The handful of standing rules (from Practice.md, restated briefly)

- The research objective (Practice.md §1) is the only yardstick: does a
  rewrite stay faithful to the author's meaning **and** get easier for
  *this* speaker to say. Everything else — code cleanliness, model choice,
  formula elegance — is subordinate to that.
- Architecture is evidence-constrained, not preservation-constrained
  (§3): nothing here is kept because it's already there, and nothing gets
  replaced just because something newer exists.
- Every claim gets classified as fact / observation / hypothesis /
  engineering decision / limitation / future work (§5). This document set
  uses that vocabulary explicitly, including in places where the honest
  label is "hypothesis" or "limitation" rather than something more
  reassuring.
- Config values and weights (SBERT threshold, λ/μ, the difficulty
  formula's coefficients) are not retuned in response to a finding
  without a separate, explicit go-ahead (§6).
- This document set was produced by a **first pass per §19, steps 1–7**
  (read, study docs, note the literature gap, identify assumptions, sort
  which need validation, document current state). It does **not**
  constitute step 9 (validation/implementation) — nothing here has been
  changed, retuned, or fixed in the repository as a result of this pass.

## A note on how this document set was produced

This set (`HANDOFF.md`, `DOCS.md`, `DECISION_LOG.md`, `VALIDATION.md`,
`ROADMAP.md`, `CHANGELOG.md`) did not exist before this review. It was
built in one pass from the current code, git history, and README/AUTH_README/
changes.md, rather than continuously as decisions were made (the discipline
§14 actually asks for going forward). That makes this set itself a
**limitation** in Practice.md's sense: dates and rationale for pre-existing
decisions are reconstructed from commit messages and code comments, not
captured at decision time, and should be read with correspondingly less
confidence than a live, continuously-maintained log. This is stated
explicitly, per §5, rather than presented as an original append-only
record.
