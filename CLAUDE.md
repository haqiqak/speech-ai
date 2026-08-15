# CLAUDE.md — Orientation

**Read `Practice.md` first.** It is the methodology this document set is
built to satisfy — the vocabulary, the evidence standard, and the review
protocol (§19) all come from there, not from this file. This file exists
only to tell you where to go next.

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
7. `ROADMAP.md` — what's next, and the finding or gap that justifies each item
8. `CHANGELOG.md` — fast-scan index into the decision log

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
