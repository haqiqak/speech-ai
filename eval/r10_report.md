# Phase 10 — Broad Stratified Stress Test of the Current Reformulation Architecture

**Status: evaluation only. No production code changed. No training.**
Corpus: `eval/r10_corpus.json` (133 sentences, hash-frozen before any run).
Run plan: `eval/r10_run_plan.json` (398 sentence×profile combinations).
Raw output: `eval/r10_raw_results.json` (frozen before judging). Blind
judgments: `eval/r10_blind_batch_{1-5}_results.json` (238 rows, 5
independent subagents, each blind to domain/category/difficulty).
Validator predictions: `eval/r10_validator_predictions.json` (frozen
Phase 9B/9C checkpoints, no retraining). Merged table + full analysis:
`eval/r10_merged.json`, `eval/r10_analysis.py`.

## Headline numbers

- **398 runs**: 238 `reformulated` (60%), 98 `no_change_needed` (25%),
  62 `could_not_safely_reformulate` (16%).
- Of the 238 actually-reformulated outputs: **62 CLEAN (26%), 176
  DEFECTIVE (74%)** — 106 SEVERE, 70 MINOR.
- Primary defect breakdown (of 176 defective): WRONG_WORD_OR_SENSE 95
  (54%), GRAMMAR 37 (21%), FACTUAL_OR_LOGICAL_REVERSAL 20 (11%),
  FIXED_TERM_OR_IDIOM 16 (9%), OTHER 8 (5%).
- This is a **harder, more adversarial corpus than any prior R-phase by
  design** (deliberately stratified for difficulty, not curated for
  success) — the 26% clean rate should not be compared directly to
  earlier, narrower rounds' numbers.

## Domain: the "technical fails disproportionately" hypothesis is only partly true

| Domain | n | CLEAN |
|---|---|---|
| general | 121 | 29% |
| technical | 117 | 23% |

**A 6-point gap — real, but far smaller than the working hypothesis
predicted.** The subcategory breakdown tells the actual story:

| Subcategory | n | CLEAN | SEVERE |
|---|---|---|---|
| chemistry | 9 | **0%** | 33% |
| engineering | 9 | **0%** | 56% |
| **narrative (general!)** | 15 | **0%** | 73% |
| economics | 13 | 8% | 69% |
| biology | 12 | 8% | 58% |
| ... | | | |
| astronomy | 9 | 44% | 44% |
| descriptions | 11 | 55% | 45% |
| **mathematics/statistics (technical!)** | 6 | **83%** | 0% |
| computer_science | 9 | 33% | **0%** |

**[FINDING] Domain label (general vs. technical) is a weak predictor.
Content density is the real one.** `narrative` (general) is tied for
worst; `mathematics/statistics` and `computer_science` (both technical)
are among the best. The evidence contradicts a clean "science is hard"
story and instead points at:

- **Technical terminology density** (`technical_terminology` tag: 17%
  clean, the single worst linguistic tag) — chemistry, engineering,
  biology all score badly and are terminology-dense.
- **Sentence length** (`long` tag: 12% clean, the worst structural
  factor of all) — narrative's failure is driven by long, proper-noun-
  and-date-dense biographical sentences, not by any scientific content.
- Mathematics/statistics succeeds specifically because its sentences are
  short, quantity-focused, and largely free of ambiguous vocabulary —
  the opposite of what "technical" was assumed to mean going in.

## Linguistic category: length and terminology dominate, not subject matter

| Tag | n | CLEAN |
|---|---|---|
| technical_terminology | 72 | 17% |
| long | 34 | 12% |
| narrative | 15 | 0% |
| passive_construction | 7 | 0% |
| negation | 40 | 40% |
| short | 30 | 43% |
| simple_substitution | 14 | 43% |

Negation, quantities, and comparison — all flagged as likely risk
factors going in — land in the **middle** of the distribution (27–40%
clean), not at the bottom. **Length and terminology density are the
dominant, load-bearing failure predictors**, not the specific semantic
category of the linguistic structure.

## Difficulty gradient: not a clean slope — moderate is a genuine trough

| expected_opportunity | n | CLEAN | SEVERE |
|---|---|---|---|
| easy | 48 | **40%** | 29% |
| moderate | 100 | **18%** | 50% |
| hard | 71 | 30% | 46% |
| very_hard | 19 | 21% | 47% |

**[FINDING, not what was predicted]** This is not a gradual degradation
curve. `moderate` performs *worse* than `hard` on both metrics. Reading
the pre-assigned rationale for `moderate` sentences (§3–4 of the plan:
"several plausible substitution points + contextual ambiguity in which
one is right") against the actual failures suggests why: ambiguity
about *which* substitution is correct is a bigger risk factor than
sheer *number* of flagged words. `hard` sentences more often force
escalation (restructuring), which — see below — performs about the same
as substitution rather than worse, partially offsetting their higher
raw difficulty. `easy` sentences perform best as predicted, but the
gap between `moderate`/`hard`/`very_hard` is not the smooth cliff a
simple density-of-difficulty story would predict.

## Profile type: dense and incidental-match profiles are the clearest hazard

| Profile type | n | CLEAN |
|---|---|---|
| multi_word (3–4 flagged words) | 13 | **0%** |
| sparse_common_sound | 21 | **10%** |
| multi_sound | 19 | 16% |
| dense_mixed_generic | 29 | 24% |
| sentence_specific_word | 111 | 28% |
| word_plus_sound | 21 | 38% |
| single_word | 21 | **48%** |

**[FINDING, confirms the hypothesis cleanly]** This is the one place the
evidence lines up with expectation precisely: `multi_word` (flag several
words in one sentence at once) is a **complete failure mode** — 0/13
clean. `sparse_common_sound` (a common sound that incidentally flags
many unrelated words, e.g. "s") is nearly as bad. Profiles that flag
exactly one thing (`single_word`, `word_plus_sound`) are the system's
best case by a wide margin. **Constraint density, at the profile level,
is the single cleanest predictor in this entire dataset.**

## Generation pathway: escalation does not rescue quality — but doesn't cost more either

| Pathway | n | CLEAN rate |
|---|---|---|
| substitution-only | 171 | 44/171 = 26% |
| escalation-invoked | 67 | 18/67 = 27% |

**[FINDING]** Essentially tied. Escalation is invoked specifically
*because* substitution alone couldn't safely handle the case — so a
naive expectation would be that escalation handles a harder slice and
should underperform. It doesn't underperform, but it also doesn't
outperform — restructuring is not currently a meaningfully safer
fallback than substitution, just a differently-shaped one. Plus: 62
runs (16% of all 398) refused outright (`could_not_safely_reformulate`)
— the safety gate is working as a real backstop, not a formality.

## Failure-type breakdown — consistent with every prior R-phase, at new scale

WRONG_WORD_OR_SENSE (54% of defects) and GRAMMAR (21%) dominate, same
ranking as R40/Phase 8/Phase 8B. FACTUAL_OR_LOGICAL_REVERSAL (11%, 20
cases) and FIXED_TERM_OR_IDIOM (9%, 16 cases) are smaller but
real — and this corpus, being fresh, surfaced **new, independent
examples** of the project's most dangerous class: "held together by"→
"surrounded by" (a star's self-gravity, reversing the actual physical
relationship), "negative effects"→"positive effects" (inflation),
"reducing unemployment"→"a reduction of employment" (a sign flip),
dropping "of hydrogen into" from a fusion equation, and a swapped
"third"/"fourth" birth-order fact in the narrative set.

## Validator generalization — the most consequential finding of this phase

Both Phase 9B and 9C checkpoints were run, unmodified, on this entirely
new corpus (disjoint from their own training data and every prior
R-phase):

| | Defect recall | Defect precision | CLEAN recall |
|---|---|---|---|
| Phase 9B (own test set, Aug 25) | 77% | 92% | 62% |
| **Phase 9B (this corpus)** | **90%** | **80%** | **34%** |
| Phase 9C (own test set, Aug 25) | 91% | 89% | 38% |
| **Phase 9C (this corpus)** | **99%** | **74%** | **3%** |

**[FINDING, the most important result of this phase]** Neither
checkpoint generalizes cleanly to new material. **9C is effectively
non-functional here** — it predicts DEFECTIVE for 235/238 rows (99%),
so its near-perfect recall is not a real signal, it is the same
"reject-everything" degenerate behavior Phase 9C's own report already
flagged as a known instability, now fully realized on genuinely new
data. **9B is directionally useful but has a real generalization
gap**: recall improved (77%→90%) but CLEAN retention collapsed (62%→
34%) — on new material, it is far more likely to wrongly reject a good
reformulation than its own test-set numbers suggested. 9B and 9C agree
with each other on only 84% of rows, underscoring that neither has
converged on a stable, portable decision boundary yet.

**This directly answers Phase 9B/9C's own open question** ("does its
advantage survive on genuinely new word-pairs and domains?") — partially
for 9B, not at all for 9C.

## Where the architecture actually breaks — synthesis

1. **Not "technical vs. general."** Content density (terminology load,
   sentence length) predicts failure far better than subject-matter
   label. A short, quantity-focused technical sentence (math/stats) beats
   a long, proper-noun-dense general sentence (narrative) by a wide
   margin.
2. **Constraint density at the profile level is the cleanest, most
   reliable predictor in the whole dataset** — multi-word profiles are
   close to a hard failure mode (0% clean), not just a degraded case.
3. **Difficulty is not a smooth gradient.** `moderate`'s dip below `hard`
   suggests *ambiguity about which substitution is correct* is a
   distinct, and currently unaddressed, risk factor from *raw count of
   constraints* — worth its own investigation rather than assuming more
   constraints always means more risk.
4. **Escalation is a lateral move, not a safety net**, quality-wise —
   it handles harder cases about as well as substitution handles easier
   ones, no better, no worse.
5. **The learned validator prototype does not yet generalize safely** —
   useful evidence for further development (per Phase 9B/9C's own
   framing), but not evidence it is ready to gate anything in production.

## Limitations, stated plainly

- Full domain×category factorial not attempted (disclosed in the
  approved plan); the subcategory table above is the closest available
  cut and is itself noisy at n=6–15 per cell.
- `expected_opportunity` is a design-time prediction, not ground truth —
  the moderate/hard inversion is a real finding about the corpus as
  built, not a claim about the concept of difficulty in general.
- Evaluators (5 parallel subagents) are all Claude instances, same
  epistemic status as every prior labeling pass in this project.
- Hand-authored general-domain sentences and verbatim technical
  sentences remain methodologically different sources, as flagged in
  the approved plan.
