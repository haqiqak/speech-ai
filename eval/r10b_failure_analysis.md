# Phase 10B — Detailed Failure Analysis: What's Actually Missing

## The request this answers

Verbatim, from the direct instruction that triggered this phase:

> "I'd have next task be a detailed R10 failure analysis, especially the
> 238 outputs, asking it to identify exactly what kind of generation
> capability is missing and separate: fixable within current
> architecture → needs a new generation mechanism → potentially requires
> a custom trained model. Then we can make the architecture-vs-custom-
> model decision based on that, rather than jumping straight into
> training something huge."

Alongside a documentation-hygiene request (handled separately — see
`DECISION_LOG.md` 2026-08-26-B and `ARCHITECTURE_RESEARCH_R42_R43.md`).

**Status: evaluation/analysis only. No production code touched, no
training, no fixes implemented.** This phase produces a decision input,
not a decision execution.

## Method

All 176 DEFECTIVE outputs from Phase 10 (`eval/r10_report.md`) were
re-examined — this time with full context (the actual word-level
changes, which mechanism produced them, domain/profile metadata) rather
than blind, since diagnosing *mechanism* is a different task from
judging *acceptability* and doesn't carry the same independence
requirement. Split into 4 batches of 44, each sent to an independent
subagent with:

- The original/reformulated text and the exact `changes` list
  (word-level substitutions or restructuring, with `source` and
  `triggered_by`).
- The prior blind judgment (severity, primary/secondary defect,
  rationale) as *established fact*, not something to re-litigate.
- A concrete definition of the three buckets, each with worked examples,
  and an explicit instruction not to default to the "safe middle"
  category — every case had to be argued on its own mechanical merits.

Full per-case output: `eval/r10b_batch_{1-4}_results.json`, merged into
`eval/r10b_fixability_merged.json`.

## Headline result

| Bucket | n | % |
|---|---|---|
| **fixable_within_current_architecture** | **162** | **92%** |
| needs_new_generation_mechanism | 12 | 7% |
| potentially_requires_custom_model | **2** | **1%** |

**This is a decisive, evidence-based answer to the architecture-vs-
custom-model question: building a custom trained model is not justified
by this failure population.** Only 2 of 176 real defects — barely over
1% — resisted every rule-based or engineered explanation the analysis
attempted.

## By defect type — where the fixable/unfixable split actually falls

| Primary defect | fixable | needs new mechanism | needs custom model |
|---|---|---|---|
| GRAMMAR (37) | **37 (100%)** | 0 | 0 |
| FIXED_TERM_OR_IDIOM (16) | **16 (100%)** | 0 | 0 |
| WRONG_WORD_OR_SENSE (95) | 86 (91%) | 8 (8%) | 1 (1%) |
| FACTUAL_OR_LOGICAL_REVERSAL (20) | 17 (85%) | 2 (10%) | 1 (5%) |
| OTHER (8) | 6 (75%) | 2 (25%) | 0 |

**Grammar and fixed-term erosion are entirely rule-fixable** — every
single case. These are the two most mechanical defect classes, and the
analysis confirms it: a grammar/agreement post-check and an expanded
fixed-term protection list would close both categories close to
completely. `FACTUAL_OR_LOGICAL_REVERSAL` — the class this whole project
has treated as most dangerous — is *also* 85% rule-fixable (mostly
antonym/polarity checks and specific bad-pair blocking), with the
remaining 15% split between a genuinely new coherence mechanism and the
2 true custom-model cases.

## By profile type — confirms Phase 10's own finding from a new angle

`multi_word` profiles (the ones that scored 0% CLEAN in the main Phase
10 report) have their defects classified: 11 fixable, 2 needs-new-
mechanism, **0 needs-custom-model**. The 0% clean rate is not evidence
the architecture needs a learned generator — it's evidence the current
independent-per-word substitution mechanism lacks two specific,
buildable things: better per-word gating (fixable now) and joint
cross-substitution coherence checking (a new but still engineerable
mechanism, not a model).

## The `needs_new_generation_mechanism` bucket (12 cases) — three recurring patterns

1. **No joint coherence check across simultaneous substitutions in one
   sentence** (the largest sub-pattern). Example: two independently
   flagged, individually-defensible substitutions combine to assert
   something neither one alone would — "self-proclaimed"→"declared" +
   "civil"→"official" together read as "declared official," near-
   opposite of "self-proclaimed." Fix shape: a coherence check that
   scores the *combination* of all changes in a sentence, not each in
   isolation.
2. **No local word-sense-disambiguation step before ranking.** Example:
   "solution" (chemistry sense, "comes out of solution") ranked against
   "answer" (its far more common sense) with nothing checking which
   sense the surrounding sentence actually uses. Fix shape: a cheap WSD
   pass (e.g. gloss-overlap against surrounding words) gating candidates
   before the existing semantic-fit ranker runs, not a learned model.
3. **No content-coverage check on restructured output.** Example:
   escalation silently dropped an entire clause ("with distinction")
   rather than rephrasing it. Fix shape: a diff-style check that every
   source clause survives in some form post-restructuring.

None of these three require a trained model — they require a new
*check/gate* added to the pipeline, not a new *generator*.

## The `potentially_requires_custom_model` bucket (2 cases) — both from escalation, both chemistry state/causal reasoning

1. **R10-006** (bile/surfactant sentence): restructuring flipped "two
   liquids" → "two solids," reversing the physical claim about what a
   surfactant acts between, while also degrading "surfactant"→
   "lubricant" and inventing the non-word "emollidate" for "emulsify."
   The invented word and generic-term swaps are separately rule-
   fixable; the liquid→solid reversal specifically requires
   understanding what a surfactant physically does.
2. **R10-034** (gradient descent / dissolution sentence): restructuring
   replaced "dissolved" (an already-completed state) with "soluble"
   (a mere capability), silently breaking the causal logic of the
   following clause. Both words are individually fluent and
   grammatical — no collocation or agreement rule would flag the pair;
   catching it requires state-vs-capability causal reasoning in the
   chemistry domain specifically.

**Both cases are escalation-tier (T5 restructuring) failures, not
substitution-tier failures, and both are domain-specific causal/state
reasoning errors — not general fluency or word-choice problems.** This
is a narrow, specific finding: *if* a custom-trained component is ever
built, this evidence points at a targeted role (verifying or
constraining escalation-tier restructuring's causal/state claims in
technical domains) — not a wholesale replacement of the generation
architecture.

## Decision this evidence supports

**Do not jump to training something huge.** The evidenced, staged path
is:

1. **First** (92% of the problem): a concrete batch of rule/blocklist/
   check additions — fixed-term protection list expansion, antonym/
   polarity checks, POS-agreement post-checks, duplicate-word
   rejection, category-consistency checks (day-scope, object-vs-action,
   etc.) — each grounded in a specific, named failure instance from
   this analysis, not speculative.
2. **Second** (7% of the problem): three specific new *mechanisms*
   (still rule/heuristic-engineered, not learned) — cross-substitution
   coherence scoring, a lightweight pre-ranking WSD gate, and a
   restructuring content-coverage check.
3. **Only after 1-2**, and only for the narrow surviving slice (escalation-
   tier, technical-domain causal/state claims): reconsider whether a
   custom-trained component is justified — which is exactly the 1%
   this analysis found, not the 74%-defective headline number Phase 10
   reported before this deeper diagnosis.

## Limitations

- All 4 classifying subagents are Claude instances, same epistemic
  status as every prior labeling pass in this project.
- The three-bucket judgment is itself somewhat subjective at the
  fixable/needs-new-mechanism boundary; the batch results include the
  concrete `root_cause`/`fix_sketch` reasoning per case for anyone who
  wants to re-examine a specific classification.
- This is a diagnosis of *this specific 176-case failure population*
  from Phase 10's stress-test corpus — not a claim that 92% of all
  conceivable future defects will be similarly fixable, though it is
  the best evidence this project currently has on the question.
