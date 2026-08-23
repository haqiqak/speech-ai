# ARCHITECTURE_TRANSITION_R43.md — R43: Instrumented Escalation Analysis and Transition Decision

**Status: investigation only.** No production code, threshold, gate, or model
was changed. This document extends `ARCHITECTURE_REASSESSMENT_R42.md` — it
does not repeat R42's full code walkthrough or R17–R41 recap verbatim;
where content is unchanged from R42 it is cited, not re-derived. What's new
here: (1) R43's instrumentation of the T5 escalation path — an actual
measurement, not a hypothesis, of *why* it fails; (2) a refined, 7-category
failure taxonomy; (3) the four architectures reframed exactly as specified
for this pass, with Architecture D (hybrid constrained generation) given the
deep treatment requested; (4) a corrected mechanism-level answer to "how
should difficulty be represented to a generator," which changes one of
R42's own proposals. Evidence tags per Practice.md §5 throughout.

---

## A. Current architecture

Unchanged from `ARCHITECTURE_REASSESSMENT_R42.md` §B.1 — re-verified against
`reformulate.py`/`semantic.py`/`engine.py`/`rephrase.py`/`phonetic.py` again
this pass, no discrepancy found. Restated in one paragraph: tag flagged
positions → if too many are flagged at once (>2 words or >60% of content
words), skip straight to escalation → otherwise attempt substitution
all-or-nothing (every flagged position needs a candidate clearing SBERT +
antonym + phoneme + profile-collision gates, or the whole sentence
escalates) → escalation calls T5 (`Vamsi/T5_Paraphrase_Paws`) for up to 5
whole-sentence paraphrases, each gated by SBERT similarity, a negation-
marker-count parity check, and a post-hoc scan for the flagged sound/words
in every content word of the candidate → best-by-similarity wins, or the
sentence ships unchanged and is reported as `could_not_safely_reformulate`.
**Substitution is primary; generation is a rarely-reached fallback** — this
characterization, given in the task prompt, is confirmed accurate by the
code, not merely assumed.

---

## B. Evidence from R17–R42 (cited, not re-derived — full detail in R42 §C)

The load-bearing findings, in one line each: R29/R31 — a real structural
signal (candidate genericness) whose assumed consequence was directly
contradicted by human evidence twice; not promoted. R32 — multi-substitution
"interaction" isn't real (5/5 cases trace to one bad substitution), but
named a genuine mechanism: wrong grammatical form landing in the wrong slot.
R33–R37 — `contextual_fit` validated as a real fluency signal, shipped
reported-only. R40 — 192 real sentence×profile pairs; 74% of 112 individual
substitutions have a real defect; T5 escalation succeeded in 2/192 runs (one
sentence). R41 — `contextual_fit` has real signal (~200× median separation)
but no threshold safely gates on it (0.01 catches 94% of defects, wrongly
rejects 62% of good output); structurally blind to fluent-but-wrong
factual/logical errors. R12/R21, R14/R23 — two independent attempts to fix
T5's escalation output by changing the *model* (reason-prompted flan-t5;
decoder-only Qwen) both failed, in opposite ways (meaning vs. constraint
satisfaction), at up to 3.5× and 3.1× model scale respectively.

**[INTERPRETATION, carried from R42, now sharpened by R43]** R12/R21 and
R14/R23 already showed that changing *what generates* the candidate doesn't
close the gap. R43 (§C below) answers the question those two experiments
left open: *why not* — down to the mechanism, not just the outcome.

---

## C. R43 results — instrumenting the T5 escalation path

### C.1 Method

Per instruction: reuse R40's existing 192-case corpus, no new sentences. Of
the 192 (sentence, profile) pairs, exactly **23** ever invoked
`_try_escalation` (21 ended `could_not_safely_reformulate`, 2 succeeded —
both the same sentence, confirmed independently, matching R40's finding
exactly). New script `eval/r43_escalation_instrumentation.py` calls the
same library functions production code calls
(`rephrase.generate_candidates`, `semantic.semantic_similarity`,
`semantic.negation_consistent`, `phonetic.matches_any`) — `reformulate.py`
and `rephrase.py` are not modified — but logs **every individual T5
candidate's fate**, not just the single best one `_try_escalation` keeps.
Every one of T5's 5 candidates per case was independently checked against
all three gates (not short-circuited on first failure), so a candidate's
*complete* gate profile is visible, not just which gate happened to reject
it first.

### C.2 The headline number: it is not fluency, and it is not meaning

**[FACT]** Across 23 cases, T5 generated 115 candidates (5/case). 92 (80%)
were non-duplicates of the input (T5 is not simply refusing/returning the
input — it is actively trying). Of those 92:

| Gate | Pass rate |
|---|---|
| SBERT similarity ≥ 0.85 | **76% (70/92)** |
| Negation-marker parity | **100% (92/92)** |
| Leak-free (no flagged sound/word in any content word) | **4% (4/92)** |
| **Accepted (all three)** | **2% (2/92)** |

**[FINDING]** T5 is, on this evidence, a reasonably competent local
paraphraser — three-quarters of its candidates preserve enough meaning to
clear a strict 0.85 SBERT floor, and negation is never the problem. **The
escalation tier's near-total failure (2/192 across the full R40 corpus, 2/92
non-duplicate candidates here) is overwhelmingly a constraint-satisfaction
failure, not a generation-quality failure.** This directly answers §5 of the
task's list of candidate causes: not (1) generation quality, not (5) SBERT
being too restrictive (it's the least-limiting gate here), not (6)
negation. It is (3)/(4): how the constraint is represented and enforced.

### C.3 The mechanism, read directly from the leaked candidates

**[FINDING, corrects R42's own hypothesis]** R42 §F.2 hypothesized the
leak mechanism was "T5 is free to use *other* common words that happen to
share the flagged sound." Reading the actual 92 candidates and classifying
every leaked word:

| Leak type | Count | Share |
|---|---|---|
| The exact blocked word, appearing **verbatim** | 14 | 9% |
| A **morphological/orthographic variant** of a blocked word (different case, hyphenation, or inflection) | 87 | 59% |
| A genuinely **unrelated** word merely sharing the flagged sound | 48 | 32% |

Concrete examples of the dominant pattern (blocked = `["pre-trained"]`, all
four T5 candidates for the same sentence):
`"pretrained"`, `"pre-training"`, `"pre-trainers"` — three different
respellings/re-inflections of the **same blocked root**, none a genuinely
different word. Blocked = `["reasoning", "such", "systems"]`: the word
**"reasoning" appears verbatim** in multiple candidates despite being
explicitly blocked — `rephrase.py::_bad_words_ids()`'s own docstring already
documents a precedent for this exact class of leak (case/spacing variants
producing different token-ID sequences than the one encoded and blocked,
`VALIDATION.md` §6.3 Cause A) — **this is that same class of leak,
recurring at the escalation-tier level specifically, not fully closed by
the existing fix.**

**[INTERPRETATION]** T5, as a paraphrase-tuned model, is trained to stay
close to its input. When a word is blocked, the path of least resistance is
not "find a different concept" — it's "keep using essentially the same
word in a form that technically isn't the one blocked." This is a different,
more specific, and cheaper-to-fix problem than R42's original hypothesis:
the fix isn't primarily "block a wider vocabulary of same-sound words" (that
addresses only the 32% "unrelated word" category) — it's primarily "block
the flagged word more robustly across its own inflections/spellings," which
addresses the 59%+9%=68% majority.

### C.4 What happens when T5 *does* try harder to avoid the word (the SBERT-failing cases)

**[FINDING]** In the cases where none of T5's candidates cleared SBERT (4
of 23), reading the actual text shows T5 reaching for a genuinely different
word — and landing on the **same defect classes R40 already found in
WordNet/Datamuse substitution**: "surface"→"topography" (wrong technical
term — the same failure shape as R40's "surface"→"layer"/"open"/"rise"),
"steaming"→"soaking" (a different, incompatible cooking process — a
meaning-breaking substitution, not a style change), "small"→"Klein" (a
hallucinated proper noun where a plain adjective was needed), "strategy"→
"strategic" (wrong word class — the exact "wrong grammatical form in the
wrong slot" mechanism R32 already named). **[INTERPRETATION]** This is
strong, direct evidence that the *quality* problem in R40's substitution
audit and the *quality* problem visible here inside T5's own generation are
the **same underlying gap** — no signal anywhere in this pipeline checks
propositional correctness or grammatical fit, regardless of whether the
candidate came from WordNet, Datamuse, or T5. Swapping which component
*generates* the candidate does not touch this gap, because the gap is in
what happens *after* generation, identically for both sources.

### C.5 The one working case, re-examined

**[FACT, revising a small overclaim in R42]** The 2 accepted candidates
(both the same sentence) are "Long-chain sugars **like glucose** tend to
break down into more digestible sugars," replacing "such as starch." R42
§33.6 already flagged this as scientifically backwards on manual review
(glucose is the simple sugar starch breaks *into*, not an example of a
long-chain sugar). **This pass's aggregate confirms it more starkly: the
escalation tier's only success in 92 candidates is itself a quality-
questionable output.** Not one candidate across the full instrumented set
is an unambiguously clean win.

---

## D. Failure taxonomy (refined, per the 7-category structure requested)

| Category | Example | Origin, now precisely located |
|---|---|---|
| **A. Surface/candidate corruption** | `sulfur→s`; `gas gases`; `optimises→optimists` | Mixed origins, now separated: `optimises→optimists` is `sanitize_input()`'s spellchecker (`grammar.py`), confirmed by direct reproduction (R40 §33.6) — **not** the reformulation engine at all. `sulfur→s`/`gas gases` are substitution-tier candidate-ranking failures (a low-information candidate cleared SBERT because a one-word change rarely moves sentence-embedding similarity enough to reject) |
| **B. Grammatical failure** | `programs→softwares`; four `was→were` cases; T5's `strategy→strategic` (C.4) | No re-inflection/agreement check on the assembled sentence, in *either* substitution or escalation output (C.4 confirms this is not substitution-specific) — a missing verification stage, not a candidate-source-specific bug |
| **C. Contextual/collocational failure** | `small talk→little talk`; `serves→helps` | The curated `IDIOM_PHRASES` list only protects what's on it (a disclosed, deliberate tradeoff, `REFORMULATION_PROBLEM_MAP.md` §3.1); collocation has no detector at all (§4's own feasibility table already names this, unbuilt) |
| **D. Semantic/sense failure** | `space→place`; `surface→topography` (T5, C.4) | SBERT/MeaningBERT both measure embedding similarity, which one wrong-sense word in an otherwise-similar sentence rarely moves enough to fail; occurs identically in substitution and escalation output |
| **E. Logical/factual relation failure** | `slower→easier` (substitution); `pre-industrial→palaeolithic` | No signal anywhere checks propositional/factual correctness; `is_known_antonym()` only catches *lexical* antonym pairs, not context-specific inversion — confirmed by direct reproduction that `antonym_check` recorded `"pass"` |
| **F. Constraint-satisfaction failure** | 96% of T5's non-duplicate candidates leak (C.2/C.3) | **Now precisely measured, not inferred**: 68% of leaks are the blocked word (or a variant of it) surviving `bad_words_ids`; 32% are a different word sharing the sound. `bad_words_ids` operates on exact tokenized strings, is not morphology-aware, and (per the existing case-variant precedent in `rephrase.py`'s own docstring) is not fully robust to tokenization-context differences either |
| **G. Dense-profile failure** | `heavy_dense` 31% both-tiers-failure rate (R40) | Compounds B/D/F: more flagged positions means more chances for one substitution to fail, and pre-escalation routes dense sentences to the tier F shows is the weakest link — not a separate mechanism, an amplifier of the others |

**[INTERPRETATION]** Categories B and D are now confirmed, by C.4's direct
reading, to occur identically whether the candidate comes from WordNet/
Datamuse or from T5. This is the single most important structural fact this
pass adds: **the bottleneck is not which component generates the candidate,
it is the absence of two verification stages (propositional/logical
correctness, and grammatical re-check on the assembled sentence) that would
catch these regardless of source.**

---

## E. Ceiling analysis — what exactly is the ceiling

Per §4 of the task: separate bad candidate generation, bad constraint
representation, inadequate verification, inadequate sentence-level
generation, or a combination.

**[RECOMMENDATION, the honest read of C+D together]** It is a combination,
but not an equal one — **inadequate verification is the dominant,
common-mode cause**, present in both substitution and escalation output
identically (categories B, D, E). **Constraint representation is the
dominant cause specifically within the escalation tier** (category F,
now measured at 96% failure and mechanistically explained in §C.3).
**Generation quality itself — T5's raw ability to produce a fluent,
meaning-preserving paraphrase — is not the bottleneck**: 76% of its
candidates clear a strict SBERT floor, and two independent prior
experiments (R12/R21, R14/R23) already showed that neither a differently-
prompted nor a differently-architected model closes the gap, because
the gap isn't there.

What the current architecture is genuinely good at, restated precisely
from R42 §B.2 and reconfirmed here: hard safety gates (0/112 phoneme/
profile-collision violations across the full R40 audit), zero-training-
data operation, and the light-profile case (R40's `light_single_sound`:
3/3 correct). What it fundamentally struggles with — restated with C.4's
addition — is **exactly the shape of problem the task names**: generating
or selecting a sentence that simultaneously satisfies an arbitrary,
speaker-specific avoidance constraint while preserving meaning, logic,
grammar, and naturalness, **regardless of whether that sentence comes from
local substitution or whole-sentence generation.** Adding more synonym
sources will not fix categories B/D/E — they occur after candidate
generation, at the verification stage, identically for any source.

---

## F. Architecture comparison (A/B/C/D as specified for this pass)

### Architecture A — Current candidate substitution (unmodified baseline)

Strengths/weaknesses unchanged from R42 §E.1. **New in this pass:** C.4's
finding that T5 output has the *same* quality problems as substitution
output means Architecture A's core weakness (missing propositional/
grammatical verification) is not a substitution-specific defect that a
different generation source would sidestep — it would need fixing
regardless of which architecture is chosen. **Ceiling: the 7% CLEAN rate
from R40, bounded above by the missing verification stages, not by the
substitution mechanism itself.**

### Architecture B — Stronger substitution (A + NLI + grammar check + better ranking, escalation unchanged)

This is R42 §E.2, unchanged in substance. **New in this pass:** because
categories B/D/E occur identically in escalation output, adding NLI and a
grammaticality re-check to the *final assembled output* (not just
substitution's per-candidate loop) would catch these defects **regardless
of whether the sentence came from substitution or from T5** — meaning
Architecture B's verification additions are not wasted even if the
escalation mechanism is later redesigned; they sit downstream of both.
**This is the highest confidence-to-effort option of the four**, precisely
because C.4 shows it targets the common-mode cause, not a source-specific
one. **Does not address category F** (the escalation tier's near-total
practical failure) — `heavy_dense`'s 31% failure rate would not
meaningfully improve from B alone.

### Architecture C — Generator-first (generation becomes primary, not fallback)

**[RECOMMENDATION, directly evidenced]** Not supported as a standalone
change. Making generation primary means *every* sentence, not just the 11%
substitution can't handle today, would be exposed to category F's 96%
constraint-leak rate. Flipping the order without also fixing how the
constraint is represented and enforced would very likely be a regression,
not an improvement — R43's own numbers show this precisely: only 2% of
T5's candidates currently pass every gate, dramatically below substitution's
demonstrated (if imperfect, 26% CLEAN+MINOR) success rate. **Architecture C
only becomes viable paired with Architecture D's constraint-mechanism
fix** — as a standalone reordering, it is not recommended.

### Architecture D — Hybrid constrained generation (generation + independent multi-signal verification) — the option most wanted for this pass

This is the architecture worth building toward, but §C.3's finding changes
*what the generation side needs*, compared to R42's original proposal.

**[RECOMMENDATION]** Two candidate fixes for the constraint-representation
problem, now ranked by C.3's actual leak-composition data rather than
assumption:

1. **Robust morphological/orthographic blocking of the named flagged
   words** (addresses the 68% majority of leaks — literal-word and
   morphological-variant leaks combined). Concretely: encode every
   inflected form of each blocked word (not just case/spacing variants,
   which `_bad_words_ids()` already handles) before calling
   `generate_candidates`. **Lower effort than R42's original proposal**,
   because it targets a precisely-measured majority cause with a narrow,
   well-scoped fix — generate the inflected forms via the same
   `grammar.inflect()`/lemmatization machinery `reformulate.py` already
   uses for substitution, no new dependency.
2. **Generate → verify → regenerate with targeted feedback**, instead of a
   static pre-generation blocklist: when a candidate leaks, tell the model
   *specifically which word leaked* and ask for a genuine alternative,
   rather than silently trying a fixed beam-search budget and giving up.
   This directly targets the *behavioral* pattern C.3 observed (T5's
   default move is a minimal edit that dodges the letter of the block, not
   the spirit of it) by making the failure explicit in the next prompt
   rather than implicit in a blocklist it can route around.
3. Sound-class-aware blocking (R42's original proposal) remains worth
   doing but is now correctly sized as addressing the smaller, 32%
   minority of leaks — a secondary improvement, not the primary fix.

Layered on top, per R42 §F.1/F.4 (unchanged by this pass): an NLI/logical-
consistency check and a grammaticality re-check on the assembled output,
run identically regardless of candidate source, per §E's finding that
categories B/D/E are source-agnostic.

**Strengths:** directly targets the two dominant, now-measured cause
classes (verification gaps, constraint-representation mechanism) rather
than a source swap. **Weaknesses:** more moving pieces than B; the
generate-verify-regenerate loop (item 2) adds latency (multiple T5 calls
per sentence in the worst case) not yet measured. **Data requirements:**
none for items 1/2/3 above or the verification additions — all inference-
time mechanism changes, no training. **Engineering complexity:**
moderate — item 1 is small (reuses existing inflection code); item 2 is a
real control-flow change to `_try_escalation`; item 3 is small. **Research
value:** item 2 (targeted regeneration) is, per this project's own prior
literature review, not templated anywhere found — a genuine, if modest,
contribution. **Likely ceiling:** unknown without building it — stated
honestly, not guessed. **Fit to objective:** the best fit of the four,
*because* it's now aimed at measured causes rather than a hypothesized one.

---

## G. Fine-tuning decision

**Not yet — and R43 strengthens, not weakens, this conclusion.** R42 §G
already found 2 of 5 preconditions unmet (no training data, no collection
pipeline). R43 adds a sharper reason specific to the escalation tier: fine-
tuning implicitly assumes the *model* is the limiting factor. C.2 shows
T5's raw output quality (76% clear a strict meaning-similarity floor) is
**not** the limiting factor — the limiting factor is a **mechanism**
(how the constraint is enforced) that a fine-tuned model driven through the
*same* `bad_words_ids`-based application would inherit unchanged. Fine-
tuning a model without first fixing the constraint-application mechanism
would very plausibly reproduce the same 96% leak rate on a better-sounding
model — an expensive way to not fix the actual problem. **Fix the mechanism
first (§F.3's items 1–2); only reconsider fine-tuning if a mechanism fix,
properly measured, still leaves a gap that looks like a generation-capacity
problem rather than a constraint-representation one.**

---

## H. Data strategy

Unchanged from R42 §H — no new data-scale claims are made or needed by
R43's findings, since none of §F.3's recommended next steps require
training data. Restated once: no dataset of the required shape exists
today; realistic scale estimates (low hundreds for proof-of-concept, low
thousands for a useful fine-tune, tens of thousands for a robust research
model) remain explicitly labeled as literature-derived estimates, not
measurements, per R42 §H.4's own fabrication warning.

---

## I. Next bounded experiments

Only what's needed to resolve remaining architectural uncertainty, in
order:

1. **Implement and test §F.3 item 1 (robust inflected-form blocking) as an
   isolated diagnostic, not production code** — re-run against the same 23
   escalation-invoked cases from this pass. If the 68%-majority leak class
   drops substantially, this is strong, cheap, evidence-based grounds to
   propose it for production (a separate, future decision). If it doesn't
   move the number much, that itself is important — it would mean the
   leak-composition read in §C.3 needs revisiting.
2. **Prototype §F.3 item 2 (generate-verify-regenerate with targeted
   feedback) as a standalone script**, same 23-case corpus, measuring
   acceptance rate and latency — both currently unmeasured for this
   specific mechanism.
3. **Test an NLI check against R40's 112-change labeled ground truth**
   (unchanged from R42 §J item 2) — still not done, still the right next
   step for category E.
4. **Re-test a grammaticality checker against R40's specific grammar-
   corruption cases** (unchanged from R42 §J item 3) — for category B,
   which C.4 confirms also occurs in escalation output, so this check's
   value is not substitution-specific.

Each of these is a diagnostic script against existing corpora — no new
large uncontrolled corpus, no production change, matching the constraint
given for this phase.

---

## J. Final recommendation

**Begin building a bounded, separate research prototype around the
constraint-representation fixes in §F.3 (items 1–2) and the two missing
verification stages (NLI, grammaticality re-check), evaluated against the
existing R40/R43 corpora — without replacing or modifying the current
production substitution-first system, which continues serving as the
baseline, safety fallback, and source of both training-adjacent examples
(§H) and regression tests.** This is a hybrid-transition strategy, not a
full swap: Architecture A stays in production; Architecture D's specific,
now-evidenced components are prototyped and measured against it, in
isolation, before any of them is proposed for production integration. Fine-
tuning remains explicitly not started, and not justified by anything found
in this pass — if anything, R43 makes the case *against* fine-tuning as the
next step slightly stronger, by showing the dominant escalation-tier
failure is a fixable mechanism problem, not a raw model-capability one.
