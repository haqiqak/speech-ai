# R50 Phase 8B — Targeted finalization of the validator dataset

**Status: research/data phase. No model trained. No production code
touched.** Scripts: `eval/r50p8b_corpus.py`, `_harvest.py`, `_labels.py`,
`_build.py` (task 1); `_taxonomy_agreement.py` (task 2, using a subagent
run with a refined 3-step decision procedure); `_convention.py` (task 3);
`_final_stats.py` (task 5). Outputs in `eval/r50_dataset/phase8b_*.json`
and the two `*_v2_convention.json` corrected datasets.

## 1. Organic factual-reversal harvest

42 new real sentences, verbatim from 4 Wikipedia topics never used
anywhere in R40–Phase 8 (Vaccine, Plate Tectonics, Antimicrobial
Resistance, Supply and Demand — deliberately chosen this time for
causal/directional claim *density*, not just topic novelty), run through
today's live `reformulate()` across R40's 4 profiles (168 combinations).
84 raw changes → **58 unique delivered-sentence groups**, each
blind-labeled as a **complete original→reformulated pair** (task 3's
resolved convention, applied from the start this time rather than
retrofitted).

**[FINDING] Organic factual-reversal yield jumped from 1/68 (Phase 8) to
8 sentence-groups / 9 records out of 58 (Phase 8B) — roughly a 6× rate
increase** — confirming the hypothesis that topic *causal density*, not
just topic novelty, drives organic yield of this class. Concrete new
organic examples found, unprompted, covering exactly the subtypes named
in the task: **directionality/factual-scope** — "Vaccines led to the
eradication of vaccination, one of the most contagious and deadly
diseases in humans" (calls the cure a disease; the actual historical
claim is about smallpox); **causal misattribution** — "A fall in
production costs would increase demand, shifting the demand curve to the
left" (production cost is a supply-side variable, not demand-side, and
the direction is internally inconsistent even on its own terms);
**physical-relationship reversal** — "Tectonic plates are about fixed...
The lithosphere is... more fixed" (asserts plates are immobile in an
article whose entire subject is that they move — "rigid"≠"fixed", and
the substitution picked the wrong one, independently, twice);
**measurement-paradigm reversal** — "the absolute movement of the
plates" for "the relative movement" (changes the actual physics
convention being described). None of these were constructed or seeded —
they are exactly what the live pipeline produced when pointed at
causal-dense real text.

**Purpose-relevant conclusion:** the defect **does** occur naturally
often enough to be worth learning from real system behavior — but at a
low enough rate (9/58 ≈ 16% record-level, 8/58 ≈ 14% group-level, still
concentrated in specific sentence types) that organic evidence alone
remains a minority contributor to the class's total count (see §4).

## 2. Taxonomy reconciliation

A stratified 27-case sample from the exact pool where Phase 8's blind
second-rater study found weak agreement (GRAMMAR 25%, NATURALNESS_OR_
REGISTER 33%) was re-judged by a fresh, independent rater using a
**strict, ordered 3-step decision procedure** (check grammaticality of
the reformulated text alone first; only if grammatical, check whether a
substituted word's sense fits; only if both pass, check naturalness/
register) — giving Option A (retain the fine-grained taxonomy) a real,
fair test with a precise operational definition, not just the original
prose descriptions.

| Class | Original agreement (Phase 8) | Refined-procedure agreement (Phase 8B) |
|---|---|---|
| GRAMMAR | 25% | **56%** |
| WRONG_WORD_OR_SENSE | 67% | **78%** |
| NATURALNESS_OR_REGISTER | 33% | **33% (unchanged)** |

**[FINDING, decisive]** The refined procedure materially improved
GRAMMAR and WRONG_WORD_OR_SENSE separability — a clearer decision rule
helps for those two. **It did nothing for NATURALNESS_OR_REGISTER**: all
6 disagreements on that class went to WRONG_WORD_OR_SENSE (3) or GRAMMAR
(3) — raters essentially never independently converge on "this is merely
awkward" as the *primary* call; they instead find a more specific
problem. This isn't a definition-clarity problem (the same fix that
helped the other two classes didn't touch this one); it looks like a
genuine property of the category.

**Decision: Option A for GRAMMAR vs. WRONG_WORD_OR_SENSE (retain,
imperfect but real — 56-78%, a usable signal, not a coin flip). Option B
for NATURALNESS_OR_REGISTER (coarsen).** Concretely:
`NATURALNESS_OR_REGISTER` is dropped as a primary label a validator is
trained or evaluated to predict; it is retained only as an optional
**secondary** annotation when a rater independently also assigns
GRAMMAR or WRONG_WORD_OR_SENSE as primary. This is narrower than the
proposal's suggested blanket `LINGUISTIC_OR_LEXICAL_DEFECT` merge — data
didn't support merging GRAMMAR and WRONG_WORD_OR_SENSE together (they
responded differently to the same fix), only removing
NATURALNESS_OR_REGISTER's primary-label role specifically.

## 3. Labeling convention — resolved and applied retroactively

Adopted verbatim: **judge the complete original→reformulated pair as
delivered, not an isolated word change.** Applied going forward to all of
Phase 8B's labels (§1). Applied backward by finding every sentence that
resulted from 2+ *distinct* simultaneous substitutions and upgrading any
record whose own word-pair looked "clean in isolation" to match that
sentence's actual worst delivered severity:

| Dataset | Sentence-groups with genuine co-occurring changes | Records upgraded |
|---|---|---|
| R50 baseline | 28 | **12** |
| Phase 8 | 11 | **6** |
| **Total** | | **18** |

Every upgraded record keeps its original word-level rationale
(`human_rationale_word_level`) alongside the new sentence-level one
(`human_rationale_sentence_level`) and is flagged `convention_adjusted:
true` — traceable, not silently overwritten. Corrected files:
`labeled_dataset_v2_convention.json`, `phase8_dataset_v2_convention.json`.

## 4. Evidence-quality breakdown (task 4)

Every record now carries `evidence_quality`: `ORGANIC_OBSERVED`,
`CONSTRUCTED`, or `HUMAN_REVIEW_OF_EXISTING_CASE` (R40–R49 re-audited
material). Final combined unique-case counts:

| Class | Total unique | HUMAN_REVIEW | ORGANIC_OBSERVED | CONSTRUCTED |
|---|---|---|---|---|
| **FACTUAL_OR_LOGICAL_REVERSAL** | **33** | 7 | **6** | 20 |
| **FIXED_TERM_OR_IDIOM** | **53** | 8 | **25** | 20 |
| WRONG_WORD_OR_SENSE | 72 | — | — | — |
| CLEAN | 32 | — | — | — |
| GRAMMAR | 26 | — | — | — |
| NATURALNESS_OR_REGISTER | 22 (now secondary-only) | — | — | — |
| OTHER_DEFECT | 9 | — | — | — |

`FIXED_TERM_OR_IDIOM` is now genuinely evidence-rich: 33/53 (62%) organic
or human-reviewed, not constructed, and comfortably past the original
40-60 target. `FACTUAL_OR_LOGICAL_REVERSAL` improved substantially
(organic count 1→6, a 6× increase) but remains short of target (33 vs.
40-60) and still majority-constructed (20/33, 61%).

## 5. Updated dataset statistics (full combined base)

313 total records (R50 135 + Phase 8 new 116 + Phase 8B new 62), **252
unique dedup groups**. Unique-case severity: 191 SEVERE / 32 MINOR / 24
CLEAN / 5 no-change. 74/313 records carry a secondary label.
`substitution` 235 / `restructuring` 22 / non-reformulated or constructed
56 (raw record granularity).

**[LIMITATION, named plainly]** CLEAN controls (24 unique) remain thin
relative to SEVERE cases (191 unique) — roughly 1:8. This is a real class
imbalance a future training run needs to address (e.g. weighting, or
deliberately expanding CLEAN examples specifically), not a blocker to
starting.

## 6. Final decision — do not move the goalposts

**GO, scoped per class — not a uniform yes across the whole taxonomy,
and not a request for more data.**

- **WRONG_WORD_OR_SENSE (72 unique), FIXED_TERM_OR_IDIOM (53 unique,
  62% organic/human-reviewed), CLEAN/acceptability (88% inter-rater
  agreement, the coarsest and most decision-relevant target):
  sufficient. Proceed.**
- **GRAMMAR (26 unique, 56% inter-rater agreement with the refined
  procedure): sufficient to proceed as a distinguishable label, with the
  explicit caveat that ~1 in 2 disagreements with WRONG_WORD_OR_SENSE
  should be expected and is an acceptable, disclosed error mode, not a
  blocker.**
- **NATURALNESS_OR_REGISTER: retired as a primary validator target**
  (§2) — not because of insufficient data, but because two independent
  tests (Phase 8's blind second rater and Phase 8B's refined-procedure
  third rater) agree it cannot be reliably assigned as a primary label.
- **FACTUAL_OR_LOGICAL_REVERSAL: proceed, but flagged.** 33 unique cases
  clears a usable floor for a first experiment, and the organic evidence
  (6 cases) — while still the thinnest slice of any class — is no longer
  zero-to-one, and is qualitatively convincing (the vaccination-eradication
  and supply-demand-swap examples in particular are unambiguous, real
  system failures). But 61% of this class's evidence is constructed, so
  **any reported validator performance on this specific class must be
  labeled directional/low-confidence, evaluated separately from the
  other classes, and not presented with the same confidence as
  WRONG_WORD_OR_SENSE or FIXED_TERM_OR_IDIOM results.**

This is not (C): the taxonomy is not fundamentally broken (GRAMMAR/
WRONG_WORD_OR_SENSE are learnable, CLEAN/DEFECTIVE is highly reliable at
88%), and the defect classes do occur in real, observable system
behavior at a non-trivial rate once the right source material is used.
It is not an unqualified (A) either — the honest position is: **build
the validator now, evaluate every class separately using the
`evidence_quality` field already attached to every record, and report
FACTUAL_OR_LOGICAL_REVERSAL results with an explicit confidence discount
until more of its evidence is organic.** That is a decision, not a
deferral.

## 7. Remaining limitations

- Both primary and second/third raters are Claude instances, not
  independent humans — an unresolved, structural limitation across this
  entire project's evidence base, disclosed consistently since R40.
- FACTUAL_OR_LOGICAL_REVERSAL's organic examples (6) are still too few to
  characterize the *shape* of that failure mode statistically — they
  establish existence and rough rate, not a representative sample of
  every way it happens.
- The NATURALNESS_OR_REGISTER retirement is based on n=27 (task 2's
  sample); it is a reasoned, evidence-based call, not a large-sample
  statistical certainty.
- Class imbalance (CLEAN vs. SEVERE, ~1:8 at the unique-case level) is
  unresolved and will need handling at training time, not before.

## Frozen artifacts (all separate, none merged silently)

- `eval/r50_dataset/split.json` — R50's original frozen split, untouched.
- `eval/r50_dataset/phase8_split.json` — Phase 8's frozen split, untouched.
- `eval/r50_dataset/labeled_dataset_v2_convention.json`,
  `phase8_dataset_v2_convention.json` — convention-corrected supersets of
  the originals (originals preserved, not deleted).
- `eval/r50_dataset/phase8b_dataset.json` — Phase 8B's 72 new records (62
  independent of prior evidence).
