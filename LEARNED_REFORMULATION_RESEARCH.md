# LEARNED_REFORMULATION_RESEARCH.md — Stage LR charter

**Status: charter only. No research has started.** Per Practice.md §0.2 /
`ROADMAP.md`'s own header discipline, a charter names a direction and its
evaluation bar — it does not authorize starting the work. That is a
separate, later decision.

## Name

**Stage LR — Learned Reformulation.** "LR" is short for *Learned
Reformulation* — this stage's whole subject: replacing or supplementing
part of the frozen rule/gate pipeline with a learned component. Named
this way instead of a number by direct instruction (2026-08-30, see
`DECISION_LOG.md` 2026-08-30-C) because the earlier candidate number,
"Stage 8," was accurate but harder to say/remember than what it stood
for. It still sits after this project's existing numbered stages
(Stage 2 scope narrowing, Stage 3 `RESEARCH.md`, Stage 4A the
difficulty profile, Stage 5 `REFORMULATION_RESEARCH.md`, Stage 6 the
`reformulate.py` evaluation, Stage 7 the human pilot — see
`DOCS.md`/`HANDOFF.md`) and does not reuse "Stage 5," which already
names a different, existing document — the letter name just replaces
"8" as the label for that same slot.

## What this is

The reformulation architecture frozen in `VALIDATION.md` §56
(`architecture-freeze-v1`, commit `7451ec4`) plateaued at 31-34% CLEAN
on its own tuning corpus and 21.4% on a fresh one, with the dominant
defect class (WRONG_WORD_OR_SENSE) diagnosed as structurally a
*ranking* problem (§53) — not something any further hand-written gate
touches. Stage LR is the space for exploring a genuinely different,
likely learned, approach to that ranking problem — e.g. the reranker
direction named and set aside in §55's Option B.

`VALIDATION.md` §57 records the external framing this charter is a
direct response to: this project's own arc is a small-scale instance of
the pattern Rich Sutton's "The Bitter Lesson" describes (hand-engineered
rules plateauing on a problem shape general/learned methods are
typically better suited to) — with the caveat, also recorded there, that
the essay's mechanism only applies once the general method actually has
enough data and compute, which is the open question this stage exists
to resolve, not assume.

## Relationship to the frozen baseline — this does not bypass the freeze

`VALIDATION.md` §56 names two, and only two, conditions under which
optimization work may resume:

1. A substantially larger, independently collected labeled dataset —
   not built the same way (same small Claude-judged corpus, same thin
   per-defect-class samples) as the evidence the freeze rests on.
2. A genuinely different modeling approach, evaluated against this
   project's own held-out generalization bar (the Phase 9B/9C
   precedent — a prior learned validator that predicted DEFECTIVE 99%
   of the time on genuinely held-out data) *before* being trusted over
   the frozen baseline.

Stage LR is condition (2)'s work. It is explicitly **not** authorized to
land on `main` or replace the frozen pipeline until it has cleared that
bar on real held-out data — training-set or tuned-corpus numbers alone
do not meet it, per the same Phase 9B/9C precedent. Until then, the
frozen baseline (`architecture-freeze-v1`) remains the shipped
implementation and the reference number any Stage LR result is compared
against: 21.4% fresh-corpus CLEAN, 0% dense-profile CLEAN, ~5-11%
dangerous-reversal rate (`VALIDATION.md` §55).

## Where this lives

All Stage LR work happens on the `stage-lr` branch (opened as
`research/stage8-learned-reformulation` per `DECISION_LOG.md`
2026-08-30-B, renamed to `stage-lr` per 2026-08-30-C), not on `main`.
`main` stays the frozen, shipped implementation partners build against —
see `HANDOFF.md`'s freeze banner. Promotion of any Stage LR result to
`main` is a separate, later, explicitly-ratified decision, following the
same discipline that closed the Architecture Go/No-Go arc — not an
automatic merge once something looks better on a training corpus.

## Scope — not yet decided

Left deliberately open for the first real Stage LR research pass, per
Practice.md §19's own step ordering (define the problem before choosing
an architecture): what a "genuinely different modeling approach" means
concretely here (a learned reranker over the existing candidate pool,
per §55's Option B; a different candidate-generation mechanism; or
something not yet considered), what data it would train/validate
against given condition (1) above is not yet met, and what the
held-out generalization bar's pass criterion is, stated as a number in
advance — not reconstructed after seeing a result, per the gap
`VALIDATION.md` §55 itself disclosed about the Go/No-Go arc's own
criteria.
