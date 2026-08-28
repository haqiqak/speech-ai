# Architecture Go/No-Go — Step 1: porting R45's phoneme-aware decoding-time constraint

Per approved plan mode (`C:\Users\BURRAQ LAPTOPS\.claude\plans\
gleaming-swinging-nova.md`): the first of four agreed steps toward a
formal architecture Go/No-Go decision. **This report is evidence for
Steps 2-3, not itself a verdict** — per the explicit agreement not to
decide the architecture question on one number.

## What was done

Production `_try_escalation()` now generates candidates via `rephrase.
generate_candidates_phoneme_constrained()` (R45 Prototype 2,
`VALIDATION.md` §36.2, built into real code in R46 §37) instead of the
plain post-hoc-rejection generator — a decoding-time `LogitsProcessor`
that kills a beam the instant its in-progress text matches a blocked
sound, instead of generating a full candidate and rejecting it
afterward. Ported exactly as built, per instruction not to redesign it:
the same call `_try_escalation_v2()` already made, every one of v1's 9
existing gates (4 shared with v2, plus 5 added across Phase 11/11B/11C
— `dropped_protected_phrases`, `has_unknown_tokens`, `introduces_new_
duplicate`, the NLI contradiction check, the grammar gate) left
unchanged. `_try_phrase_replacement()` was deliberately NOT touched —
nothing blocks it technically, but it's never been tried there even
experimentally, and extending to an untested path would have gone
beyond "port the validated thing."

## A real, pre-existing bug found and fixed during this phase's own verification

Running `tests/reformulate_v2_test.py` (not run during Phase 11C's own
verification — a gap in that phase's own discipline, acknowledged
here) surfaced `test_validation_never_gates_status_or_final_
verification` failing. Root cause: Phase 11C added an NLI contradiction
gate to the SHARED `_try_substitution()` (used by both `reformulate()`
and `reformulate_v2()`), which this pre-existing test's global mock of
`logical_consistency_check` now also tripped, breaking its actual
target (confirming `reformulate_v2()`'s own separate, reported-only
final validation pass never gates). Fixed by mocking `grammar_issue_
count` instead — confirmed neither `_try_substitution()` nor `_try_
escalation_v3()` gate on that signal internally, so it correctly
isolates what the test means to check. Not caused by today's port, but
found and fixed as part of it, per this project's standing discipline.

## Targeted verification

`eval/arch_gate1_targeted_rerun.py` re-ran the 42 R10 corpus cases with
dense/multi-sound profiles (`dense_mixed_generic`/`multi_sound`/`word_
plus_sound`) that were refused (`could_not_safely_reformulate`) as of
the post-Phase-11C harvest — exactly the population R45's Prototype 2
was built to help. **16/42 (38%) now produce a candidate at all**,
where previously none did. Latency for this specific targeted set:
mean 8.14s vs. the prior generator's 6.35s on the same 42 cases (+28%).

This targeted-set gain (38%) is smaller than R45's own originally
reported figure (~52% of dense cases producing a usable candidate,
measured on a different, smaller 23-case corpus). The most likely
reason, confirmed by design rather than assumed: R45's original number
was measured *before* Phase 11/11B/11C's five additional post-generation
gates existed. Today's port has to clear a substantially stricter
validator stack that didn't exist when Prototype 2 was first validated
— this interaction was explicitly flagged as new, unmeasured territory
before this phase started, and this is the first real measurement of it.

## Full-harvest result

Full 398-run harvest (`eval/r11_reverify_harvest.py`, reused as-is)
diffed against `eval/r10_raw_results.json`: **162 runs changed** — 114
`reformulated → reformulated`, 34 `reformulated → could_not_safely_
reformulate`, and **14 `could_not_safely_reformulate → reformulated`**
(vs. 1 in every prior phase's re-verification, which was itself
attributable to pre-existing nondeterminism — this is a real,
substantially larger coverage effect, consistent with the targeted
verification above).

**128 runs still `reformulated` after the change were blind-judged**
(6 independent parallel subagents, no metadata): **23 CLEAN, 105
DEFECTIVE (69 SEVERE, 36 MINOR)**.

Transition against Phase 10's original judgment: 20 DEFECTIVE→CLEAN
genuine fixes, 82 still-defective, 12 CLEAN→DEFECTIVE (every one
individually checked — all trace to this project's already-documented
candidate-pool nondeterminism, the same recurring run_ids seen in
Phase 11C's own report: `R10-024`, `R10-037`, `R10-049`, `R10-097`,
`R10-112`, `R10-123`, `R10-124` — none caused by today's port), **3
N/A→CLEAN** (previously-refused cases now producing a genuinely clean
simplification — a real, confirmed quality win, not just coverage:
`R10-106-core-dense_mixed_generic`, `R10-109-calib-multi_sound`,
`R10-109-calib-dense_mixed_generic`), 11 N/A→DEFECTIVE (previously
refused, now attempt something but it's still not good enough).

**Overall CLEAN rate among all currently-reformulated runs: 68/218
(31.2%)** — this is genuinely mixed evidence, not a clean win or a
clean loss:
- Absolute CLEAN count rose slightly (66→68).
- Reformulated-status count rose substantially (194→218, +24) as
  refused-status count fell (106→82) — real, measured coverage gain,
  consistent with both the targeted verification and the 14 refused→
  reformulated transitions.
- The CLEAN *rate* dipped (34.0%→31.2%) because a majority of the newly
  covered cases landed DEFECTIVE, not CLEAN — the coverage gain did not
  translate proportionally into quality gain.

This is precisely the finding R45's own hand-review anticipated
("roughly half [of newly accepted candidates] still carry a real
defect... exactly the defects the *validation* side targets") — except
the validation side (NLI + grammar) is now actually installed in
production (Phase 11C) and *still* isn't enough, because the dominant
remaining defect type is WRONG_WORD_OR_SENSE, which neither the NLI
contradiction check nor the grammar checker is built to catch (a
wrong-but-grammatical, wrong-but-non-contradictory word choice is
invisible to both).

## Computational cost, measured

- Targeted set (42 hardest previously-stuck cases): mean latency
  6.35s→8.14s (+28%).
- Full escalation-invoked population (67→82 cases, since more sentences
  now reach/complete escalation): mean latency 8.08s→8.70s (+8%).
- Total 398-run harvest wall time: 1930s→1991s (**+3%** overall).

The full-corpus cost is small; the cost concentrates specifically on
the hardest, densest-profile cases the mechanism is designed to help —
an intuitive, disclosed pattern, not a surprise.

## What this means for Steps 2-3 (not decided here)

The still-DEFECTIVE population (82 cases) needs the Step 2 diagnosis
this whole 4-step plan called for: for the dominant WRONG_WORD_OR_SENSE
defects, is the correct word simply absent from the candidate pool T5/
WordNet/Datamuse generates, or is it present but ranked below a worse
one? This report does not answer that — it establishes that the
generation-mechanism lever (this step) and the validation-mechanism
lever (Phase 11C) have both now been pulled, with real but bounded
effect, and the dominant remaining problem doesn't yield to either.
That is exactly the evidence Step 3's formal architecture assessment
needs, not a reason to conclude anything about it here.

## Limitations

- All 6 (this pass) + prior phases' judges are Claude instances.
- The targeted-set-vs-full-population gap in coverage gain (38% vs.
  R45's ~52%) is explained by design (a stricter gate stack now exists)
  but not independently re-verified against R45's original 23-case
  corpus directly — a possible follow-up if the exact comparison
  matters later.
- This is Phase 11C's own ~consistent nondeterminism population being
  re-observed a third time, not a fresh finding each time — worth
  remembering when reading the CLEAN-rate delta, per the ~1-2 point
  noise band already established.
