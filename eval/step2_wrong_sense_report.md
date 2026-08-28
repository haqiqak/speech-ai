# Architecture Go/No-Go — Step 2: is WRONG_WORD_OR_SENSE a generation problem or a ranking problem?

Per the agreed 4-step plan (Step 1 report: `eval/arch_gate1_report.md`).
Analysis only — no production code changed. The question, verbatim
from the approved proposal: *"determine whether the correct
reformulation is absent from the candidate pool or merely ranked
incorrectly."*

## Method

All 88 currently-DEFECTIVE, WRONG_WORD_OR_SENSE-labeled runs (the
dominant remaining defect class, confirmed across Phase 11B/11C/Step 1)
were re-run with full instrumentation exposing what the pipeline
actually considered, not just what it shipped:

- **Substitution-tier** (64 cases): the exact ranked candidate list
  `rank_candidates_contextually()` produced, at production's real
  `top_k=10`, plus an extended query at `top_k=30` to check whether a
  good candidate exists in the underlying WordNet/Datamuse resource at
  all even if production's window missed it.
- **Restructuring-tier** (24 cases): all `k=5` candidates
  `generate_candidates_phoneme_constrained()` actually generated, plus
  an extended `k=15` pass, to check the same question for T5's
  paraphrase output distribution.

4 independent subagents then classified each case **with full context**
(not blind — this is root-cause diagnosis, not acceptability judging,
the same methodological distinction Phase 10B drew) into: `ABSENT_FROM_
POOL` (no good candidate anywhere, even at the extended size),
`PRESENT_BUT_MISRANKED` (a good candidate exists but scored/ranked
below the shipped one, or exists only at the extended size), `NO_GOOD_
OPTION_POSSIBLE` (the task is genuinely hard — no substitution or
restructuring could work), or `OTHER`.

**A real bug in this phase's own diagnostic tooling was found and
fixed before any number was reported**: the first pass crashed on 19 of
24 restructuring-tier cases (`'DifficultyEntry' object has no attribute
'lower'` — a dead line of code that iterated `profile.words`, a list of
objects, calling `.lower()` directly instead of using the string
values already extracted correctly two lines below it). Fixed by
deleting the dead line; all 19 were re-diagnosed and re-classified from
real data before merging into the final counts below — the earlier,
data-free classifications for those 19 were discarded, not averaged in.

## Result

**98 classification objects across the 88 cases** (a few cases have two
implicated changes):

| Classification | Count | % |
|---|---|---|
| **PRESENT_BUT_MISRANKED** | **70** | **71%** |
| ABSENT_FROM_POOL | 20 | 20% |
| NO_GOOD_OPTION_POSSIBLE | 5 | 5% |
| OTHER | 3 | 3% |

**The dominant answer is unambiguous: for 71% of WRONG_WORD_OR_SENSE
defects, the correct or a better word/restructuring was already
sitting in the pipeline's own candidate pool.** This is not primarily a
lexical-resource coverage gap (WordNet/Datamuse/T5 not knowing the
right word) — it is a **selection problem**: candidate generation is
finding acceptable options; the pipeline is choosing badly among them.

Within the 70 PRESENT_BUT_MISRANKED cases, a further split matters for
what kind of fix this implies:
- **~57 cases**: the better candidate was already in **production's own
  top_k=10 / k=5 pool** — a pure ranking-function problem, not a
  cutoff-size problem. Raising `top_k`/`k` would not fix these.
- **~13 cases**: the better candidate only appeared once the pool was
  extended (`top_k=30` / `k=15`) — a genuine "the window is too small"
  case, separable from the above, and cheaper to address if pursued.

## A concrete, mechanistically confirmed sub-finding

Several of the clearest ranking-failure cases (`R10-007`'s "biochemical
and physiological" → "chemical and physical," among others) share an
exact, traceable mechanism, verified directly against `semantic.
combined_score()`, not inferred:

```
combined(chemical,   sim=0.9897) = 0.9733   <- shipped, WRONG sense (drops "biological")
combined(biological, sim=0.9911) = 0.9723   <- correct sense, higher raw similarity, LOWER combined score

combined(physical,   sim=0.9954) = 0.9815   <- shipped, WRONG sense
combined(biological, sim=0.9973) = 0.9779   <- correct sense, higher raw similarity, LOWER combined score
```

`biological` has the **higher** raw SBERT similarity in both cases —
and loses anyway, because `combined_score()`'s documented 90%
semantic / 10% Zipf-frequency blend rewards `chemical`/`physical` for
simply being more common English words (Zipf 4.57/4.94 vs.
`biological`'s 4.31). When two candidates' semantic similarity is this
close (a ~0.001-0.002 gap), the 10% frequency term is large enough to
flip the order — and it flips it toward the less meaning-preserving
word. This is not a bug in the sense of broken code; it's the formula
working exactly as designed and documented (`semantic.py`'s own module
docstring: "Frequency normalisation... weak naturalness only") — but
the evidence here shows that weak signal is strong enough, often
enough, to be a real contributor to the dominant remaining defect class.

**Per Practice.md's standing rule, this is flagged as evidence for a
future, separate, explicit decision — the 0.90/0.10 weighting is NOT
changed here.** It is named specifically because Step 3's architecture
assessment needs to know this isn't a vague "the ranker is imperfect"
impression — it's a specific, load-bearing design parameter with a
demonstrated causal path to real defects.

## The 20% ABSENT_FROM_POOL and 5% NO_GOOD_OPTION_POSSIBLE cases

These are the cases where more/better candidate generation genuinely
would help (or where nothing could help). Two recurring resource-gap
patterns: category/hypernym words with no true single-word synonym in
WordNet (`carbohydrates`, `hydroelectricity`, `smaller and smaller`'s
progressive-decrease sense), and polysemous words where every returned
sense is wrong except the identical restatement (`second`, `surface`,
`shellfish`→`shell`). `NO_GOOD_OPTION_POSSIBLE` cases are genuinely
irreplaceable technical/fixed-collocation terms (`economics` the
discipline, `century` in an ordinal-collocation slot) — no engineering
fix, learned or not, changes this without changing what the user is
allowed to say.

## What this means for Step 3 (not decided here)

This is direct, load-bearing evidence for the formal architecture
assessment: **the dominant remaining problem (WRONG_WORD_OR_SENSE, 71%
of it specifically a selection/ranking failure) is not primarily a
"we need better candidate generation" problem** — Step 1's generation-
side fix (phoneme-aware decoding) and every rule-based gate added
across Phase 11/11B/11C operate on a *filter* or *generate* layer that
this evidence says isn't where most of the remaining damage happens.
If Step 3 concludes a learned component is warranted, **this evidence
points specifically at a learned reranker/scorer** — something that
replaces or augments `combined_score()`'s fixed linear blend with a
model that can tell `biological` and `chemical` apart in context — not
a bigger candidate generator. Per the agreed criteria, any such
component still needs to clear the Phase 9B/9C generalization bar
(held-out testing, not training-set numbers) before being trusted.

## Limitations

- All 4 classifying subagents are Claude instances, given full context
  (not blind) — appropriate for root-cause diagnosis per Phase 10B's
  precedent, but the same epistemic caveat as every prior labeling pass
  applies.
- The ~57/~13 split within PRESENT_BUT_MISRANKED was computed by a
  keyword heuristic over the subagents' free-text rationale, spot-
  checked directly against several cases' raw pool data (confirmed
  accurate on inspection) but not independently re-verified for every
  one of the 70.
- This diagnoses the 88 currently-DEFECTIVE WRONG_WORD_OR_SENSE cases
  in the R10 corpus specifically, not a claim about every possible
  future input.
