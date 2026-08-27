# Phase 11C — porting the R45/R46 NLI+grammar validator, escalation-tier duplicates, countability

Per approved plan mode (`C:\Users\BURRAQ LAPTOPS\.claude\plans\
gleaming-swinging-nova.md`): the four evidence-backed mechanisms named
in the research/design pass, implemented in the order the plan
specified (NLI → duplicate-word → grammar → countability), each
verified against its own evidence, then a full re-harvest and blind
re-judging — the same discipline Phase 11/11B/Phase-11-reverify
established.

## What was built

1. **NLI entailment/contradiction gate**
   (`semantic.logical_consistency_check()`, `cross-encoder/nli-
   deberta-v3-xsmall`) — ported from the experimental
   `_try_escalation_v3()` (never wired to `app.py`'s default path) into
   production's `_try_escalation()` and `_try_phrase_replacement()`.
   Also added as a single whole-sentence check on `_try_substitution()`'s
   final assembled output (once per successful attempt, not
   per-candidate), per R45's own explicit recommendation
   (`VALIDATION.md` §36.3).
2. **Escalation-tier duplicate-word check**
   (`reformulate.introduces_new_duplicate()`) — a new function, since
   Phase 11's `_duplicates_sentence_word()` only ever gated
   substitution-tier candidates. Counts content-word keys (Porter stem
   for short words, 6-char prefix for long ones — the same logic as
   Phase 11's existing check, reshaped into a `Counter`) in the original
   sentence as a baseline, and only flags a key that already occurred
   at least once AND occurs *more* often in the candidate — not any
   brand-new word. Wired into `_try_escalation()` and
   `_try_phrase_replacement()`.
3. **Grammar gate** (`semantic.grammar_issue_count()`, LanguageTool via
   `language_tool_python`) — ported from `reformulate_v2()`'s
   reported-only `validation` dict into an actual reject gate in the
   same two production functions.
4. **Countability/mass-noun check** (`semantic.is_mass_noun_
   substitution()`, a small curated `_MASS_NOUNS` set) — wired into
   `_try_substitution()`'s loop.

## Two real bugs found and fixed during this phase's own verification

Following the discipline every prior phase used — nothing was reported
until the code that produced the number had already been corrected:

1. **`introduces_new_duplicate()`'s first version flagged ANY word new
   to the candidate**, not just an increased repeat of an existing one
   — which would have rejected almost every legitimate paraphrase
   ("requires"→"needs" is not a duplicate of anything, but the broken
   rule treated any word absent from the original as "exceeding" its
   0 count). Caught immediately by the existing test suite (`test_
   count_threshold_triggers_restructuring` and three sibling tests
   failed) before being trusted. Fixed: only flag a key with a prior
   count ≥ 1 in the original whose candidate count is now higher.
2. **A pre-existing WSD test (`test_repeated_word_different_senses_
   get_different_replacements`) failed** once the new substitution-tier
   NLI gate was added — not a false positive in the gate, but a real,
   previously-invisible defect the gate correctly caught: under this
   test module's `DISABLE_DATAMUSE=1` determinism setting, WordNet's
   only candidate for "runs" (jogging sense) in that exact sentence was
   "pass," producing "he passes three miles" — genuinely wrong, now
   correctly rejected. The test asserted only that the two occurrences
   of "runs" got *different* candidates, not that the candidates were
   individually good, so it was rewritten to test the local-context-
   window disambiguation mechanism directly (candidate-set generation)
   rather than end-to-end pipeline output, which depends on other
   gates that can legitimately intervene for unrelated reasons.

## A measured, expected tradeoff — not a bug

The approved plan explicitly flagged this risk before implementation:
*"NLI models are also known... to occasionally flag legitimate
paraphrases as contradictions... a real, not zero, risk."* Direct
investigation of the 7 previously-CLEAN cases that now refuse found
the substitution-tier whole-sentence NLI check does exactly this —
e.g. `R10-112`'s "remove the paper" → "take the paper" (a fine,
context-appropriate synonym) was flagged `contradiction: True` by the
NLI model. This is the mechanism working as designed, with a real
precision cost the plan anticipated, not a defect in the
implementation — verified directly (not assumed) that the *same*
mechanism also delivers a confirmed true positive: `R10-005`'s
"reabsorbed"→"eliminated" (a genuine reversal) is correctly rejected
by the identical check while "reabsorbed"→"absorbed" (a fine
simplification) passes cleanly. The net effect of this tradeoff is
measured, not assumed, in the Result section below.

## Targeted verification (before the full harvest)

`eval/r11c_targeted_rerun.py` re-ran the 20 specific evidenced
`run_id`s across all four mechanisms through live production
`reformulate()`: **16/20 changed from their original Phase 10 defect**
(several via genuine text improvement, several via a safe refusal that
replaced a shipped SEVERE defect — `R10-005`, `R10-011`, `R10-024`,
`R10-025`, `R10-061` ×2, `R10-088` all confirmed fixed this way). The 4
unchanged (`R10-002`, `R10-013`, `R10-037` — LanguageTool doesn't flag
these specific grammar patterns, matching its already-disclosed ~25%
partial recall; `R10-101` — the NLI model doesn't flag this specific
psych-verb role-flip as a contradiction, matching its disclosed ~18%
recall) are expected partial-recall misses, not new bugs — directly
confirmed by re-checking each signal in isolation.

## Full-harvest result

Full 398-run harvest (`eval/r11_reverify_harvest.py`, reused as-is,
run once after both bug fixes above) diffed against
`eval/r10_raw_results.json`: **147 runs changed** — 101
`reformulated → reformulated`, 45 `reformulated → could_not_safely_
reformulate` (38 of 45 were previously DEFECTIVE, 7 previously CLEAN —
the NLI precision cost described above), 1 `could_not_safely_
reformulate → reformulated`.

**102 runs still `reformulated` after the change were blind-judged**
(5 independent parallel subagents, same no-metadata discipline as
every prior phase): **21 CLEAN, 81 DEFECTIVE (56 SEVERE, 25 MINOR)**.

Transition against Phase 10's original judgment: **21 DEFECTIVE→CLEAN**
genuine fixes (including `R10-005`, the direct NLI-attributable win;
`R10-001` ×3 and `R10-079` ×3, duplicate/blocklist-adjacent fixes; `R10-
091` ×3, mass-noun fixes), 70 still-defective, **10 CLEAN→DEFECTIVE**
regressions. All 10 were individually checked against which mechanism
(if any) could have caused them: none involve the duplicate-word,
NLI-substitution, grammar, or mass-noun gates rejecting a previously-
used candidate — every one is a plain `source: substitution` case where
a *different* WordNet/Datamuse candidate simply won the ranking this
run (`R10-037` "continuously"→"continually", `R10-049` ×2 and `R10-097`
×3 — the same already-disclosed Category-4 POS/argument-structure gap
seen in every prior phase's re-verification, `R10-123` "rebuilt" vs
"renovated" — previously identified in Phase 11B's own re-verification
as this same nondeterminism class, `R10-024`-dense-variant — the SAME
declared word ["second"] flagged twice independently getting two
*different* replacements ["forward"/"intermediate"] this run, a
distinct and not-yet-addressed defect shape, not a duplicate-word
issue). None are new bugs introduced by this phase's code.

**Overall CLEAN rate among all currently-`reformulated` runs: 66/194
(34.0%)** — up from Phase 10's 26.1%, and up from Phase 11B's 31.6%
(clearing the ~1-point re-harvest noise band Phase 11B's own
verification established, so this is a real improvement, not noise).
Refusal rate: 106/398 (26.6%), up from Phase 11B's 75/398 (18.8%) — a
substantial rise, expected given four new, independently-gating
mechanisms were added in this single pass; every case checked directly
confirms this is the safety gate doing more work correctly (converting
shipped defects into honest refusals), not a coverage regression on
previously-good output beyond the disclosed NLI precision cost above.

## What's still broken (70 DEFECTIVE→DEFECTIVE cases)

WRONG_WORD_OR_SENSE 46, GRAMMAR 13, FIXED_TERM_OR_IDIOM 7,
NATURALNESS_OR_REGISTER 2, FACTUAL_OR_LOGICAL_REVERSAL 1, OTHER 1.
WRONG_WORD_OR_SENSE remains completely dominant — matching Phase 11B's
own finding that this class needs candidate-pool-level word-sense
disambiguation, a fundamentally different kind of mechanism than any
of Phase 11/11B/11C's rule/model-gate additions, none of which touch
*which* candidates are generated in the first place, only which ones
survive after generation.

## Limitations

- All 5 (this pass) + prior phases' judges are Claude instances, same
  epistemic status as every prior labeling pass.
- The substitution-tier whole-sentence NLI check has a real, now-
  measured precision cost (7/102 previously-CLEAN cases now refuse) —
  disclosed plainly, not minimized. Whether to narrow its scope (e.g.
  restrict to multi-position substitutions, or use a larger/different
  NLI checkpoint) is a legitimate follow-up question, not resolved
  here — the net effect measured above is positive, but the tradeoff
  itself is real and should inform any future refinement.
- `grammar_issue_count()`'s recall on the GRAMMAR-labeled defect class
  remains partial (~25%, confirmed again directly against this phase's
  own evidence, not just cited from R45) — it will not materially move
  the dominant WRONG_WORD_OR_SENSE population.
- `R10-024`'s same-declared-word-different-replacement pattern (the
  same word flagged twice, substituted with two different words) is a
  newly-surfaced, distinct defect shape, not previously named as its
  own category — worth tracking as a candidate item for a future phase
  rather than conflated with the duplicate-word mechanism this phase
  built (which addresses the opposite direction: a word appearing MORE
  often than the original, not two DIFFERENT words for one repeated
  original word).
