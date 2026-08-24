# R50 Phase 2/3/7/9 — Dataset construction, labeling, and baseline report

**Status: research/dataset-construction only. No model trained. No production
code touched.** Scripts: `eval/r50_build_dataset.py` (join + label),
`eval/r50_dataset_stats.py` (statistics), `eval/r50_make_split.py`
(leakage-safe split). Outputs: `eval/r50_dataset/labeled_dataset.json`,
`eval/r50_dataset/stats_summary.json`, `eval/r50_dataset/split.json`.

## 0. What this is and isn't

This assembles every sentence pair across R40/R44/R47/R48/R49/v5 that has,
or can defensibly be given, a human defect-type label, joins them into one
dataset, and attaches automated signals (NLI/grammar/contextual_fit/SBERT)
as a separate, non-authoritative block. It answers Phase 3's baseline
question and Phase 8's sufficiency question. It does not build, tune, or
select thresholds for anything.

## 1. Repairing R48 — what was actually recoverable

`VALIDATION.md` §38.3's "5 CLEAN, 4 MINOR, 3 SEVERE" tally for R48's 12
successful escalation cases was **never attached to specific sentences in a
stored artifact beyond 3 of the 12** (the two defect-class examples and the
fixed-term-erosion example named in prose). The other 9 only ever existed as
an aggregate count.

Per instruction not to infer where evidence is ambiguous: those 3 documented
cases carry their **documented** verdict (`human_rationale_source:
documented-VALIDATION-38.3`). The remaining 9 were given a **fresh** read
just now, from the actual sentence text in `r48_v3_verification_results.json`
— clearly tagged `human_rationale_source: fresh-2026-08-24`, distinct from a
reconstruction of the original tally. One of the 9 (`R48-17`, "small
talk"→"short talk") reads slightly worse on this fresh pass than R48's prose
characterization ("genuinely fine... one grammar slip") — the fresh read
also flags a secondary sense loss on "social function"→"function in the
community". This discrepancy is left visible in the record rather than
silently reconciled.

One further case was reconstructed from prose only: the "rational"→
"irrational" antonym flip that R48 caught and correctly rejected (never
shipped, so never written to any results JSON). Its full sentence text is
**not verified against a stored artifact** — flagged `text_verification:
UNCERTAIN` in the dataset — but its word-level defect (a direct antonym
substitution, confirmed by NLI, the worst class of error this project
tracks) is solidly documented and worth keeping as a negative example.

## 2–6. Unified dataset — headline counts

| Metric | Value |
|---|---|
| **Total labeled records** | 135 |
| **Unique underlying cases** (dedup by word-pair or normalized sentence) | **88** |
| Records with a human severity + defect-type label | 135/135 (100%) |
| Records also carrying v5's 1–5 human ratings (meaning/naturalness/ease/preference) | 16 |
| Records also carrying R44's automated NLI+grammar flags | 47 |
| Records with any automated signal at all (NLI, grammar, or contextual_fit) | 110 |

**Severity:** SEVERE 92, MINOR 29, CLEAN 9, ORIGINAL_NO_CHANGE 5 (raw
records) — **55 SEVERE / 21 MINOR / 7 CLEAN / 5 NO-CHANGE at the unique-case
level.**

**Granularity:** substitution 114, restructuring/escalation 15, n/a
(refusals / pipeline-mutation bug) 6.

**Clean+no-change vs. defective:** 121 defective / 14 clean-or-no-change
(raw); **28/88 (32%) clean-or-no-change at the unique-case level** — this
is the honest, deduplicated version of R40's original 26% CLEAN+MINOR
figure, and it lands close to it.

**Multiple labels:** 20/135 records carry a secondary defect label
alongside the primary (e.g. a factual reversal that is *also* a wrong-word
substitution). This is expected — Phase 1 explicitly asked for it — and is
concentrated in the FACTUAL_OR_LOGICAL_REVERSAL and WRONG_WORD_OR_SENSE
classes, which co-occur often (a wrong word is frequently *how* a factual
reversal gets introduced).

**UNCERTAIN:** 1/135 (the reconstructed "rational"→"irrational" text, flagged
above).

**Provenance:** R40 only 65, R40+R44 31, R40+R44+v5 16, R47 11, R48 11,
R48+R49-crosscheck 1.

## 7. Class imbalance — the honest version

Raw-record primary-defect counts look reasonable (WRONG_WORD_OR_SENSE 44,
NATURALNESS_OR_REGISTER 19, FIXED_TERM_OR_IDIOM 18, GRAMMAR 16, OTHER_DEFECT
12, FACTUAL_OR_LOGICAL_REVERSAL 12, CLEAN 9). **That is misleading** — R40's
corpus reuses the same word-pair substitution across many sentences (e.g.
"small"→"little" appears 9 times, "strategy"→"way" 5 times), so raw counts
overstate how much *independent* evidence exists per class.

**At the unique-case level (88 groups), the picture is much thinner:**

| Defect type (primary) | Unique cases |
|---|---|
| WRONG_WORD_OR_SENSE | 33 |
| NATURALNESS_OR_REGISTER | 12 |
| GRAMMAR | 9 |
| FIXED_TERM_OR_IDIOM | 8 |
| CLEAN | 7 |
| OTHER_DEFECT | 7 |
| **FACTUAL_OR_LOGICAL_REVERSAL** | **7** |
| ORIGINAL_NO_CHANGE | 5 |

**[FINDING] The two classes this whole research phase exists to address —
factual/logical reversal and (within it) the fluent-wrong-word subtype —
are the thinnest in the dataset: 7 unique factual-reversal cases total,**
and even generously counting WRONG_WORD_OR_SENSE's overlap with it, nowhere
near enough to train a reliable classifier for either class alone. This is
stated explicitly per instruction: **we do not have more than a handful of
factual reversals.**

## 3. Baselines on the new, defect-typed dataset

**Combined NLI+grammar recall, broken down by defect type** (n=64 records
with an automated signal attached; this is a new cut R44 never computed —
R44 only measured overall SEVERE recall, not recall per defect class):

| Defect type | SEVERE n | Caught by NLI or grammar |
|---|---|---|
| GRAMMAR | 7 | 4/7 (57%) |
| FACTUAL_OR_LOGICAL_REVERSAL | 7 | 4/7 (57%) |
| OTHER_DEFECT | 6 | 2/6 (33%) |
| WRONG_WORD_OR_SENSE | 17 | 4/17 (24%) |
| **FIXED_TERM_OR_IDIOM** | 5 | **0/5 (0%)** |

Overall: 14/42 SEVERE caught (33%), 2/22 CLEAN+MINOR false-positives (9%) —
close to R44's original 32%/14% (same signal, an overlapping but not
identical sample). **[FINDING, new]** Fixed-term-idiom erosion ("small
talk"→"little talk", "search engines"→"research engines") is a **complete**
blind spot for NLI and grammar checking — 0/5 — a third defect class the
existing stack cannot see at all, not previously isolated this cleanly
because R44 only measured an undifferentiated SEVERE bucket.

**contextual_fit median score, by defect type** (n=110):

| Defect type | median contextual_fit |
|---|---|
| **FACTUAL_OR_LOGICAL_REVERSAL** | **0.305** |
| CLEAN | 0.0078 |
| NATURALNESS_OR_REGISTER | 0.0077 |
| FIXED_TERM_OR_IDIOM | 0.0007 |
| GRAMMAR | 0.00001 |
| OTHER_DEFECT | 0.000003 |
| WRONG_WORD_OR_SENSE | 0.000033 |

**[FINDING, new and sharper than R41's]** Factual/logical reversals score
*higher* on contextual_fit than CLEAN substitutions do — almost 40× higher
at the median. This isn't noise around a weak signal; it's the signal
pointing the wrong way for exactly the class we most need it to catch,
because a fluent factual reversal (by construction) reads as *more*
plausible in context, not less. contextual_fit is actively counter-
indicative for this class specifically, confirming and quantifying R40/R41's
anecdotal "pre-industrial→palaeolithic scores 0.999" observation across all
7 unique factual-reversal cases rather than one.

## 9. Leakage-safe split (frozen)

Split by dedup **group** (word-pair or normalized sentence), not by record,
stratified by primary defect type, sorted deterministically (no RNG):

| | groups | records |
|---|---|---|
| train | 62 | 101 |
| val | 13 | 17 |
| **test (frozen, untouched from here on)** | **13** | **17** |

Per-stratum test coverage is thin by necessity: the split is stratified by
each dedup **group's** representative label (its most-severe member), and
the rare strata (CLEAN, FACTUAL_OR_LOGICAL_REVERSAL, OTHER_DEFECT, GRAMMAR,
FIXED_TERM_OR_IDIOM) each contribute exactly **1 unique group** to the
frozen test set (15% of 7-9 groups rounds to 1). Because a handful of
groups are keyed on the *original* sentence only (multiple independent
restructuring attempts on the same source sentence, e.g. "starch"→
"cornstarch" (CLEAN) and "starch"→"glucose" (FACTUAL_OR_LOGICAL_REVERSAL)
both starting from the same long-chain-sugars sentence), a single test
group can carry records of more than one label — correct for leakage
(the same source sentence never crosses a split boundary) but worth
naming as a labeling nuance, not a bug. `eval/r50_dataset/split.json`
records the exact uids; per instruction, this file is not to be touched
again for label refinement, threshold selection, or training.

## 8. Assessment: A, B, or C?

**[RECOMMENDATION] This is (C), leaning toward (B) for the classes with
more data — it is not (A).**

- For **WRONG_WORD_OR_SENSE** (33 unique cases) and, more weakly,
  **NATURALNESS_OR_REGISTER**/**GRAMMAR** (12/9 unique cases): enough for
  **baseline evaluation** of candidate signals (which is what this report
  just did), and arguably enough to *attempt* a first small validator
  experiment as a directional check — but not enough to trust its measured
  performance as anything but directional, given 13-record test strata.
- For **FACTUAL_OR_LOGICAL_REVERSAL** (7 unique cases) and
  **FIXED_TERM_OR_IDIOM** (8 unique cases) — the two classes this entire R49
  → R50 chain exists to close — **the data is too sparse for either training
  or a trustworthy held-out evaluation.** A classifier trained on 5-6 train
  examples of a class, tested on 1-2, would produce a number with no
  statistical meaning; per instruction, that must be said plainly rather
  than dressed up because the total N (135, or even 88) looks respectable.

**Answering the central question directly:** we do **not** yet have enough
trustworthy, defect-typed human data to justify training a small custom
validator for the two blind-spot classes that motivated this work. We do
have enough to run baseline comparisons (done above) and to know precisely
what a dedicated labeling phase needs to produce.

**Concrete ask for a labeling phase, if pursued:** the gap is specifically
in **FACTUAL_OR_LOGICAL_REVERSAL** and **FIXED_TERM_OR_IDIOM** — at least
40-60 more unique, human-labeled examples of each (not sentences reusing the
same word-pair) would bring those classes roughly to where
WRONG_WORD_OR_SENSE sits today, which itself is only borderline-sufficient.
This aligns with Phase 8's instinct to start human data collection in
parallel rather than after — that data does not exist yet in this
repository's evidence base and cannot be extracted from it no matter how
carefully R40–R49 are re-read.
