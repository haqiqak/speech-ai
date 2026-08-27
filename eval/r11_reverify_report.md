# Phase 11 re-verification — blind re-judging + a regression found and fixed

Per direct instruction: Phase 11's own §48 write-up disclosed that "no
longer reproduces the old defect" is a narrower, cheaper claim than "now
judged CLEAN," since no blind re-judging had been performed. This phase
closes that gap: re-run the full Phase 10 corpus (all 398 runs, not just
the 83 originally targeted) through today's production `reformulate()`,
diff against the frozen Phase 10 raw results, and blind-judge every run
whose output actually changed — using the same no-metadata, independent-
parallel-subagent method as Phase 10 itself.

## Method

1. `eval/r11_reverify_harvest.py` — re-ran the frozen Phase 10 corpus +
   run plan (398 runs) through today's live production `reformulate()`.
2. `eval/r11_diff_and_prepare_batches.py` — diffed against
   `eval/r10_raw_results.json` by `(status, reformulated_text)`. An
   unchanged run's prior blind judgment still applies by definition
   (judgment is a function of the text pair alone); only changed runs
   need fresh judging. Deliberately the full 398, not the 83 originally
   targeted — this is the actual regression check, not just a
   confirmation of the intended fixes.
3. 4 independent parallel subagents blind-judged every changed run still
   in `reformulated` status, given only `(original_text,
   reformulated_text)` — no domain/category/difficulty, identical
   discipline to Phase 10's `VALIDATION.md` §46.

## A regression found mid-verification, and fixed before this report was finalized

The first re-harvest (94 changed runs) surfaced 3 CLEAN→DEFECTIVE
regressions. Investigating them found a real gap Phase 11 had not
covered:

**Root cause:** `IDIOM_PHRASES` is consumed by *three* free-text-
generating paths, not two. Phase 11 added the post-generation
`dropped_protected_phrases()` gate to `_try_escalation()` only. A third
path, `_try_phrase_replacement()` (the phrase-tier used when a flagged
word's *only* difficulty is that it sits inside a protected phrase),
had no such gate — and it is exactly the path triggered when the
phrase's own internal word is the user's declared difficulty. For
"golden brown" (R10-092), "with distinction" (R10-133), and "money
supply" (R10-057), the flagged word (`golden`/`distinction`/`money` or
`supply`) is explicitly blocked from T5's output by
`_try_phrase_replacement()`'s own `blocked_words` set, so it can
*never* produce a candidate that preserves the exact phrase — every one
of these cases was silently shipping a broken phrase
("gold brown", "with distinguished", "money market").

**Second, separate finding from the same investigation:** `"small
intestine"` and `"large intestine"` were never actually verified
against a real failure in the first place. R10-004's actual defect was
`"small"→"little"` (an unrelated global-sound substitution); R10-005's
was `"reabsorbed"→"assumed"` (already correctly handled by the
blocklist) — `"large intestine"` survived intact in R10-005's own
defective output. Protecting `"small intestine"` had the effect of
*rerouting* R10-004's `"intestine"` (the user's own declared
difficulty) away from a working substitution (`"small bowel"`, CLEAN in
Phase 10) into the phrase tier, which then produced
`"small intestinal tract"` with a stray capitalization bug — a
regression directly caused by an unverified addition, exactly the
failure mode the plan-rejection feedback had warned against.

**Fix applied:** removed `"small intestine"`/`"large intestine"` from
`IDIOM_PHRASES` (never evidenced); added the same
`dropped_protected_phrases()` gate to `_try_phrase_replacement()`. For
phrases whose internal word IS the declared difficulty, this correctly
makes the phrase tier return `None` (no candidate can pass), so the
sentence is left unchanged and honestly reported as skipped —
converting what were SEVERE defects into safe refusals, consistent with
this codebase's established "never ship a bad guess" discipline
(`IdiomGuardTest`). Full test suite + `smoke.py` re-verified clean after
the fix; the full 398-run harvest was re-run and re-diffed from
scratch, and all judging below reflects the corrected code, not the
version that had the regression.

## Result (final, post-fix)

- 398 total runs; **92 changed** (text and/or status differs from the
  frozen Phase 10 output) after Phase 11's categories 1–3; 306
  unchanged (prior judgment still applies).
- Status transitions among the 92: 82 `reformulated → reformulated`, 9
  `reformulated → could_not_safely_reformulate` (8 of these 9 were
  previously judged DEFECTIVE — SEVERE in 7 of 8 cases — now an honest
  refusal instead of shipped garbage), 1
  `could_not_safely_reformulate → reformulated` (a single case,
  `R10-041`, attributable to this project's already-documented
  Datamuse-dependent candidate-pool nondeterminism, not to any Phase 11
  mechanism).
- **83 runs still `reformulated` after the change were blind-judged.**
  Result: **15 CLEAN, 68 DEFECTIVE** (52 SEVERE, 16 MINOR).
- Transition breakdown against the original Phase 10 judgment: **15
  DEFECTIVE→CLEAN** (genuine fixes), **65 DEFECTIVE→DEFECTIVE**
  (changed text, still a defect — often a different defect than
  before), **2 CLEAN→DEFECTIVE** (`R10-049` × 2 profile variants of the
  same sentence — a pre-existing, unrelated Category-4 POS-agreement
  gap, `"probability"→"possible"`, not touched by any Phase 11
  mechanism; see Limitations), **1 N/A→DEFECTIVE** (`R10-041`,
  nondeterminism, see above).

**[FACT] Overall CLEAN rate among all currently-`reformulated`-status
runs: 75/230 (32.6%), up from Phase 10's 62/238 (26.1%).** Refusal rate
70/398 (17.6%), up from 62/398 (15.6%) — the safety gate is doing more
work, correctly, not less. This is the actual, blind-judged answer to
"did Phase 11 help": yes, a genuine ~6.5-point CLEAN-rate improvement,
not just "the specific old defect text is gone."

## What's still broken (65 DEFECTIVE→DEFECTIVE cases)

Primary defect among the still-broken cases: WRONG_WORD_OR_SENSE 35,
FIXED_TERM_OR_IDIOM 8, GRAMMAR 8, FACTUAL_OR_LOGICAL_REVERSAL 5,
NATURALNESS_OR_REGISTER 5, OTHER 4. This matches Phase 10B's own
Categories 4-7 breakdown (POS/grammatical-agreement, antonym/polarity
gaps, number/scope preservation, escalation dictionary validation) —
confirms that scope, rather than surfacing a new pattern this pass
didn't anticipate.

## Limitations

- All 4 (this pass) + 5 (Phase 10) blind judges are Claude instances,
  same epistemic status as every prior labeling pass in this project.
- The `R10-049` "probability"→"possible" case demonstrates this
  project's already-documented candidate-ranking nondeterminism
  (network-dependent Datamuse results contributing to near-tied
  candidate scores) can flip a judgment between process runs
  independent of any code change — a reproducibility caveat for this
  and future re-verification passes, not new to Phase 11.
- This re-verifies Phase 11's specific 92-run change population, not a
  fresh, disjoint corpus — it answers "did this pass's changes help,"
  not "what's the system's current CLEAN rate on unseen material"
  (that remains Phase 10's 26% baseline until a new stress test is run).
