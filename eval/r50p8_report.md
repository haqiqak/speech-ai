# R50 Phase 8 — Build the missing human-labeled dataset

**Status: data collection only. No model trained. No production code
touched.** Scripts: `eval/r50p8_corpus.py` (new source sentences),
`eval/r50p8_harvest.py` (live-pipeline run), `eval/r50p8_labels.py`
(blind labels), `eval/r50p8_constructed.py` (supplementary examples),
`eval/r50p8_build.py` (assembly + leakage check against R50),
`eval/r50p8_stats.py`, `eval/r50p8_make_split.py` (frozen Phase 8 split),
`eval/r50p8_agreement.py` (inter-rater agreement). Outputs in
`eval/r50_dataset/phase8_*.json`.

## 1–2. How the corpus was constructed and selected

**Organic arm (preferred, run first):** 54 real sentences, verbatim from
five live Wikipedia articles never used in R40–R50 (Photosynthesis, Solar
System, Exercise, Industrial Revolution, Internet — chosen for
causal/temporal/directional claim density, a known source of
`FACTUAL_OR_LOGICAL_REVERSAL`), run through **today's actual production
`reformulate.reformulate()`** across R40's exact 4 difficulty profiles —
216 (sentence × profile) combinations, exactly R40's own methodology
reused on genuinely new material. This produced 100 individual raw
changes, deduplicated to **68 unique (word-pair or restructuring) cases**.

**Constructed arm (supplementary, disclosed as such):** R50 showed the
two target classes occur at roughly an 8% incidental rate in real
substitution output — confirmed here (see §12). Reaching 40–60
independent examples of each organically would require auditing many
hundreds more sentences, outside this phase's scope. Per instruction
("do NOT manufacture... unless necessary"), 50 examples were
hand-authored: 20 `FACTUAL_OR_LOGICAL_REVERSAL` (covering directionality,
causal, physical, temporal, and factual-scope subtypes, modeled on the
exact mechanism already observed in real output — a near-antonym that is
distributionally plausible in context, not a random word, per R40's
"slower"→"easier"), 20 `FIXED_TERM_OR_IDIOM` (idioms, lexicalized
phrases, fixed collocations, technical terminology), and **10 hard-CLEAN
controls built on the same sentence templates** so a future validator
cannot learn "reject anything near cause/effect language" or "reject
anything idiom-shaped" as a shortcut.

## 3. Labeling protocol

**Organic arm — genuinely blind.** A sheet containing only
`original_word`/`replacement_word` + `original_sentence`/
`reformulated_sentence` (no `contextual_fit`, no `sbert_sim`, no source
profile/experiment metadata) was generated and read cold; every one of
the 68 unique cases was labeled from that sheet alone
(`eval/r50p8_blind_sheet.txt`), assigning `human_acceptability`,
`human_severity`, primary + optional secondary `defect_type`, and a
rationale — the full field set requested.

**Constructed arm — not blind, disclosed.** These examples were written
*to instantiate* a named defect, so blind labeling is not a meaningful
concept for them; they are pre-labeled at authoring time and flagged
`labeling_protocol: "not blind"` throughout the dataset. This is a real,
named limitation (§11), not concealed.

**Rater identity:** the primary rater is Claude — same epistemic status
as R40's and R50's labeling passes, not an independent human. A genuinely
separate check (§10, below) was run via a second, independent Claude
instance (a subagent with no access to this conversation, the primary
rater's labels, or the taxonomy's origin — given only the raw text pairs
and the taxonomy definitions) to get an actual inter-rater signal rather
than one rater's self-consistency.

## 4–6. Dataset size, unique cases, defect distribution

118 total records (68 organic + 50 constructed). **2 organic records
collided by dedup key with the frozen R50 baseline** (`such`→`much`,
`surface`→`open` — the same recurring structural bugs R40 already
recorded on different sentences) and are excluded from every count below
as not-independent evidence, per instruction. **116 new, independent
records — and all 116 landed in distinct dedup groups** (zero additional
internal duplication within Phase 8 itself).

| | Severity | n |
|---|---|---|
| | SEVERE | 85 |
| | MINOR | 9 |
| | CLEAN | 22 |

| Primary defect type | n (new records) | organic | constructed |
|---|---|---|---|
| FIXED_TERM_OR_IDIOM | 33 | 13 | 20 |
| WRONG_WORD_OR_SENSE | 24 | 24 | 0 |
| CLEAN | 22 | 12 | 10 |
| **FACTUAL_OR_LOGICAL_REVERSAL** | **21** | **1** | **20** |
| GRAMMAR | 9 | 9 | 0 |
| NATURALNESS_OR_REGISTER | 5 | 5 | 0 |
| OTHER_DEFECT | 2 | 2 | 0 |

16/116 records carry a secondary label alongside the primary (multi-label
cases, as expected).

**[FINDING, unprompted]** The organic harvest alone produced **13 real
`FIXED_TERM_OR_IDIOM` cases** — far above the ~8% base rate R50 predicted
— because these five new topics (astronomy, biology, networking,
industrial history) are dense with fixed scientific/technical terminology
("protoplanetary disc", "reaction centers", "cellular respiration",
"protocol suite", "respiratory tract", "textile spinning", "water
splitting") that the substitution engine keeps breaking. This is real,
organically-observed evidence, not a constructed artifact — one case
(`water splitting`→`water breaking`) is especially notable: the broken
term accidentally collides with a completely unrelated, extremely common
idiom ("water breaking" = going into labor), producing an unintentional
and jarring misreading.

**[FINDING]** `FACTUAL_OR_LOGICAL_REVERSAL` organic yield was nearly
zero — **1 case out of 68** (the escalation-tier restructuring case
`P8-organic-040`, a genuine causal-relationship reversal the live T5
escalation path produced on a real sentence about resistance training and
muscle hypertrophy). This confirms R50's ~8% estimate was, if anything,
optimistic for this specific class in a substitution-dominated sample —
almost all of this class's real occurrences in R40 came from
restructuring, not word substitution, and restructuring is rare in
ordinary pipeline output.

## 8. Controls

32/116 records are CLEAN (22 new — 12 organic near-misses genuinely fine
on their own reading, 10 constructed hard controls built on the same
templates as the defect examples specifically to prevent shortcut
learning). This is a meaningfully larger and more deliberate control set
than R50's baseline had (7 unique CLEAN cases).

## 9. Duplicate / near-duplicate analysis

- 2/118 records (both organic) duplicate an R50-baseline lexical
  phenomenon by dedup key — excluded from every "new" count above.
- 0 internal duplicate dedup groups among the remaining 116.
- **A different, real nuance surfaced during the agreement check (§10):**
  several organic records share the same underlying *sentence* (two
  separate word-pairs both changed in one delivered output, e.g.
  `Rapid`→`Fast` and `spinning`→`twisting` in the same sentence). The
  primary rater's convention (matching R40's own precedent) labels each
  word-pair's contribution *in isolation*; a rater reading the *whole
  delivered sentence* will reasonably score the "clean-in-isolation" half
  of such a pair as defective too, since that is the sentence a real user
  would actually see. This is flagged explicitly rather than silently
  smoothed over — see §10.

## 7, 10. Inter-rater agreement

A stratified 33-record sample (spanning all defect classes, both
organic and constructed) was independently re-labeled by a second,
genuinely separate rater (a fresh Claude subagent, blind to the primary
rater's labels and to which arm — organic or constructed — each record
came from, given only the text pairs and the taxonomy definitions).

| Dimension | Agreement |
|---|---|
| Acceptability (CLEAN / DEFECTIVE) | 29/33 = **88%** |
| Severity, exact (CLEAN/MINOR/SEVERE) | 21/33 = **64%** |
| Severity, collapsed (SEVERE vs. not) | 25/33 = **76%** |
| Primary defect type, exact | 23/33 = **70%** |
| Primary defect type, allowing either rater's secondary label | 25/33 = **76%** |

**By class** (primary rater's label as reference, n per class = 2–6, too
small for precise rates but directionally real):

| Class | Agreement |
|---|---|
| FACTUAL_OR_LOGICAL_REVERSAL | 6/6 = 100% |
| OTHER_DEFECT | 2/2 = 100% |
| FIXED_TERM_OR_IDIOM | 5/6 = 83% |
| WRONG_WORD_OR_SENSE | 4/6 = 67% |
| CLEAN | 4/6 = 67% |
| NATURALNESS_OR_REGISTER | 1/3 = 33% |
| **GRAMMAR** | **1/4 = 25%** |

**[FINDING, honest]** Two distinct sources of disagreement, not one:

1. **A genuine taxonomy-boundary problem.** `GRAMMAR` vs.
   `WRONG_WORD_OR_SENSE` vs. `NATURALNESS_OR_REGISTER` is where the two
   raters diverge most (e.g. "distributed" for "spread" used
   intransitively: primary rater called GRAMMAR, second rater called
   WRONG_WORD_OR_SENSE — both defensible readings of the same sentence).
   This is a taxonomy-refinement question, not just a data-quantity one,
   and the proposal's own §6 anticipated exactly this ("we may later
   discover the taxonomy needs refinement").
2. **A labeling-convention confound, not a disagreement about the
   text.** 3 of the 4 CLEAN-vs-DEFECTIVE mismatches (`organic-026`,
   `-046`, `-050`) trace directly to the isolation-vs-whole-sentence
   convention named in §9 — the second rater, given only the delivered
   sentence, correctly scored a co-occurring defect the primary rater's
   per-word-isolation convention had assigned to a *different* uid in
   the same sentence. This is not evidence the labels are wrong so much
   as evidence the two conventions need to be reconciled before this
   dataset is used for anything beyond directional analysis.

**[LIMITATION]** The 100% agreement on `FACTUAL_OR_LOGICAL_REVERSAL` is
encouraging but should not be over-read: all 6 sampled cases were
constructed (deliberately unambiguous antonym-flip constructions). The
one organic example in the whole dataset was not in this 33-record
sample. We do not yet have inter-rater evidence on how reliably two
raters agree on *subtle, organically-occurring* factual reversals — only
on the clean, deliberately-obvious constructed ones.

## 11. Limitations (consolidated)

- Both raters are Claude, not independent humans (same limitation as
  every prior labeling pass in this project).
- Constructed examples are not blind-labeled and are somewhat easier/more
  obvious by construction than real pipeline failures — a validator
  trained partly on them may perform better on this dataset than on the
  live system's actual organic error distribution.
- `FACTUAL_OR_LOGICAL_REVERSAL` is 20/21 (95%) constructed; confidence in
  this class rests almost entirely on examples the primary rater wrote,
  not observed.
- Overall exact primary-defect-type agreement (70%) and severity
  agreement (64%) are moderate, not high; `GRAMMAR` and
  `NATURALNESS_OR_REGISTER` in particular are not yet reliably
  distinguishable between raters.
- Agreement was measured on n=33, not the full 116 — real but a small
  sample for by-class rates.

## 12. Comparison against R50 baseline

| Class | R50 baseline (unique cases) | Phase 8 new | Combined |
|---|---|---|---|
| FACTUAL_OR_LOGICAL_REVERSAL | 7 | 21 | **28** |
| FIXED_TERM_OR_IDIOM | 8 | 33 | **41** |

Target was 40–60 *new* examples per class. `FIXED_TERM_OR_IDIOM` (33 new)
came reasonably close and crosses the 40 floor once combined with R50;
`FACTUAL_OR_LOGICAL_REVERSAL` (21 new, 28 combined) fell short of the
target range and — per §11 — the shortfall is compounded by being almost
entirely constructed rather than organically observed. Per instruction,
these numbers are reported as-achieved, not adjusted toward the target.

## 13. Sufficiency decision: A, B, or C?

**[RECOMMENDATION] (B) — more labeling required, direction still
justified. Not (A); not (C) either.**

- **Not (A):** `FACTUAL_OR_LOGICAL_REVERSAL` is short of target and
  overwhelmingly constructed (needs more *organic* examples specifically,
  not just more examples); `GRAMMAR`/`NATURALNESS_OR_REGISTER` inter-rater
  agreement (25%/33%) is too low to trust a trained classifier's reported
  performance on those classes; the isolation-vs-whole-sentence labeling
  convention needs to be resolved (pick one, relabel the affected
  records) before this dataset is training-ready.
- **Not (C):** `FACTUAL_OR_LOGICAL_REVERSAL` and `OTHER_DEFECT` hit 100%
  agreement, `FIXED_TERM_OR_IDIOM` hit 83%, and acceptability (the
  coarsest, most decision-relevant judgment) hit 88% — there is a real,
  learnable signal here, and the taxonomy is not fundamentally broken,
  just imprecise at specific boundaries.
- **Concretely missing before (A):** (i) more *organic*
  `FACTUAL_OR_LOGICAL_REVERSAL` examples — targeted escalation-tier runs
  (this class showed up via restructuring, not substitution) on a larger
  fresh sentence set, since organic yield here was 1/68; (ii) a decision
  and re-labeling pass reconciling the per-word vs. whole-sentence
  labeling convention; (iii) either a refined taxonomy boundary between
  GRAMMAR/WRONG_WORD_OR_SENSE/NATURALNESS_OR_REGISTER, or acceptance that
  a validator will be evaluated on the coarser, more reliable
  CLEAN/DEFECTIVE + severity axes rather than exact defect-type
  classification for those three classes specifically.

**Central question, answered directly:** No — we do not yet have data
reliable and independent enough, specifically for
`FACTUAL_OR_LOGICAL_REVERSAL`, to train and trustworthily evaluate a
small custom validator. `FIXED_TERM_OR_IDIOM` and `WRONG_WORD_OR_SENSE`
are closer, with `CLEAN`/`OTHER_DEFECT` controls now genuinely adequate.
Per instruction, **no training proceeds from this phase.** The path
forward is a second, narrower data-collection pass targeting organic
factual-reversal examples specifically, plus a short taxonomy/convention
reconciliation pass on the existing 116+88 records — both smaller,
cheaper efforts than a full second Phase 8, since the infrastructure
(corpus-harvesting scripts, blind-labeling sheet generator,
second-rater subagent process) now exists and is reusable.

## Frozen artifacts

- `eval/r50_dataset/phase8_dataset.json` — 118 records, R50-overlap flagged.
- `eval/r50_dataset/phase8_split.json` — a **separate**, frozen 68/24/24
  train/val/test split (by dedup group, stratified), independent of
  R50's own frozen split (`eval/r50_dataset/split.json`, untouched).
  Neither split has been used for label refinement, threshold selection,
  or training.
