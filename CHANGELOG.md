# CHANGELOG.md — Fast-scan index

One line per change, reverse-chronological, backfilled from `git log`
(2026-08-08). Each line points into `DECISION_LOG.md` where a fuller
entry exists; most commits below have no decision-log entry because they
were routine/incremental — per Practice.md §14, the changelog is the fast
index, the decision log is the full record, and not every line needs both.

- **2026-08-28, ninth** docs: Architecture Go/No-Go Step 4 RATIFIED —
  the user explicitly froze the current reformulation architecture as
  the maintained/shipped baseline, ending the Architecture Go/No-Go arc.
  No further rules, gates, ranking tweaks, thresholds, or learned
  components authorized on current evidence; routine maintenance
  continues. Frozen code confirmed unchanged since `7451ec4`. Explicit
  reopening conditions recorded: a substantially larger independently-
  collected labeled dataset, or a genuinely different modeling approach
  clearing this project's own Phase 9B/9C-precedent generalization bar.
  Not project abandonment — the frozen architecture is now the reference
  baseline for any future approach. Tagged `architecture-freeze-v1`.
  Documentation/versioning only, no production code touched. →
  `DECISION_LOG.md` 2026-08-28-I, `VALIDATION.md` §56.
- **2026-08-28, eighth** docs: Architecture Go/No-Go Step 3 (formal
  assessment) + Step 4 (recommendation, pending ratification) — the
  arc's culmination. Synthesized all evidence since Phase 10 against
  the 8 named criteria; disclosed that numeric thresholds were never
  actually pre-registered. Key finding: dense/multi-constraint profiles
  score 0% CLEAN on both the original frozen corpus and a completely
  fresh one, unmoved across the whole optimization arc; fresh-material
  CLEAN rate sits ~10-13 points below the tuned corpus. Recommendation:
  Option C (freeze current architecture as shipped, no learned
  component) — reasoning grounded in this project's own Phase 9B/9C
  generalization-failure precedent plus this arc's own fresh-corpus
  result. Analysis + recommendation only, no production code touched,
  awaiting user ratification. → `DECISION_LOG.md` 2026-08-28-H,
  `VALIDATION.md` §55.
- **2026-08-27/28, seventh** docs: Architecture Go/No-Go Step 3 prep —
  a generalization check on an 18-sentence/36-run corpus genuinely new
  to this project (fresh Wikipedia topics + hand-authored general
  sentences), closing the gap that every evaluation since Phase 10 had
  re-verified the same frozen R10 corpus. Result: CLEAN rate 6/28
  (21.4%) on fresh material, ~10 points below every R10-corpus figure
  this architecture has produced (26.1%→34.0%), outside the established
  noise band, with dense_mixed profiles at 0/10 CLEAN. Also disclosed
  and fixed an undisclosed non-verbatim trim in 4 of the corpus's 10
  technical sentences before reporting results. Analysis only, no
  production code touched. → `DECISION_LOG.md` 2026-08-27/28-G,
  `VALIDATION.md` §54.
- **2026-08-27, sixth** docs: Architecture Go/No-Go Step 2 — diagnosed
  whether the dominant remaining defect (WRONG_WORD_OR_SENSE) is a
  candidate-generation gap or a ranking failure. Re-instrumented all 88
  currently-DEFECTIVE cases to expose the full candidate pool actually
  considered (not just the winner), classified with full context by 4
  subagents. Self-caught and fixed a diagnostic-tooling bug (19
  crashed cases) before reporting. Result: 71% are PRESENT_BUT_
  MISRANKED — a better candidate was already in the pipeline's own
  pool — with a specific, mechanistically confirmed cause traced for
  several cases to combined_score()'s 90%/10% semantic/frequency blend
  favoring a common-but-wrong word over a rarer-but-correct one.
  Weighting flagged as evidence for a future, separate decision, not
  changed. Analysis only, no production code touched. →
  `DECISION_LOG.md` 2026-08-27-F, `VALIDATION.md` §53.
- **2026-08-27, fifth** feat: Architecture Go/No-Go Step 1 — ported
  R45/R46's phoneme-aware decoding-time constraint (the largest
  measured improvement in this project's history, previously stuck
  behind an experimental opt-in toggle) into production
  _try_escalation(), exactly as built. Self-caught a real pre-existing
  test bug from Phase 11C's own verification gap before reporting any
  number. Result deliberately reported as mixed, not spun: 16/42
  hardest previously-stuck cases now produce a candidate (real coverage
  gain), but overall CLEAN rate dipped slightly (34.0% → 31.2%) because
  most newly-covered cases land DEFECTIVE — confirming R45's own
  prediction that the validation side (now installed) still can't
  catch the dominant remaining defect, WRONG_WORD_OR_SENSE. First-ever
  measured computational cost in this project: +3% total harvest
  latency. This is Step 1 of 4 (generation fix → failure diagnosis →
  formal architecture assessment → decision) — not a verdict on its
  own. → `DECISION_LOG.md` 2026-08-27-E, `VALIDATION.md` §52.
- **2026-08-27, fourth** feat: Phase 11C — research pass then ported
  R45/R46's already-built NLI entailment gate and LanguageTool grammar
  gate from the experimental reformulate_v2()/opt-in-toggle path into
  production, plus two new mechanisms: an escalation-tier duplicate-
  word check and a countability/mass-noun set. Self-caught 2 real bugs
  (duplicate-check over-flagging any new word; a WSD test that never
  actually verified candidate quality) before reporting any number, and
  measured a real, plan-anticipated tradeoff (substitution-tier NLI's
  7/102 false-positive rate) rather than assuming it away. Full
  398-run harvest: 21 genuine fixes, 10 regressions all traced to
  pre-existing nondeterminism. CLEAN rate: 26.1% → 31.6% → 34.0%,
  clearing the established re-harvest noise band. →
  `DECISION_LOG.md` 2026-08-27-D, `VALIDATION.md` §51.
- **2026-08-27, third** feat: Phase 11B — categories 4/6/7 of Phase
  10B's fixable batch. Added dictionary/real-word validation on
  generated output (reused as a substitution-tier gate too, not just
  escalation/phrase-tier, after a mid-phase finding), a generalizable
  number-word preservation check, and five more verified blocklist
  pairs. Explicitly deferred general T5-output grammar/agreement
  checking and polarity-without-negation detection (need a new
  mechanism). This phase's own re-harvesting caught and fixed 3 real
  bugs before reporting any number: an overly aggressive spellcheck
  gate that regressed 2 previously-CLEAN outputs, a number-word set
  missing digit/hyphenated forms, and a genuine root-cause bug in
  grammar.inflect()'s pluralization fallback ("weekdays" -> "dayss").
  Also confirmed a real limit (not chased further): two words whose
  candidate pools keep surfacing a new bad match every time the
  previous one is blocked. Result: 17 genuine fixes, 8 apparent
  regressions all traced to pre-existing candidate-pool/T5
  nondeterminism unrelated to this phase's code. CLEAN rate: 31.6%,
  up from Phase 10's 26.1%, flat against Phase 11's 32.6% within a
  newly-confirmed ~1-point re-harvest noise band. →
  `DECISION_LOG.md` 2026-08-27-C, `VALIDATION.md` §50.
- **2026-08-27, second** fix: Phase 11 re-verification — blind
  re-judged all Phase 11 changes (full 398-run re-harvest, not just
  the 83 targeted cases) and found a real regression: `IDIOM_PHRASES`
  is consumed by a third free-text path (`_try_phrase_replacement()`)
  Phase 11 hadn't gated, and two entries ("small intestine"/"large
  intestine") were never actually verified against a real failure.
  Fixed both (removed the unverified entries, added the same
  preservation gate to the phrase-tier function), re-ran the full
  harvest from the corrected code. Final result: 15 genuine
  DEFECTIVE→CLEAN fixes, 9 SEVERE-defect-to-safe-refusal conversions,
  only 2 regressions (both a pre-existing, unrelated nondeterminism
  gap). Overall CLEAN rate among reformulated runs: 26.1% → 32.6%,
  blind-judged. → `DECISION_LOG.md` 2026-08-27-B, `VALIDATION.md` §49.
- **2026-08-27, first** feat: Phase 11 — implemented categories 1-3 of Phase
  10B's "92% fixable" batch. Expanded `semantic.py`'s fixed-term
  protection list and extended its enforcement to escalation-tier T5
  output (a gap found during implementation); added a duplicate-word-
  in-sentence rejection check to `_try_substitution()`; added a
  52-pair bad-pair blocklist, each pair individually re-verified
  against its named Phase 10 run_id (per explicit plan-mode-rejection
  feedback demanding this, not bulk-copied), catching two real bugs
  (wrong grammatical form on 4 pairs; blocklist needed to normalize
  unlemmatized Datamuse candidates). All tests pass, smoke.py
  byte-identical to baseline. Targeted re-run of the 83 R10 cases these
  categories target: 77/83 (93%) no longer reproduce their original
  defect; the remaining 6 are a named, deferred gap (escalation-tier
  duplicate-word extension, and one Category-4 grammar case). →
  `DECISION_LOG.md` 2026-08-27-A, `VALIDATION.md` §48.
- **2026-08-26, third** docs: Phase 10B — detailed failure analysis,
  architecture-vs-custom-model evidence. All 176 Phase 10 DEFECTIVE
  outputs re-examined with full mechanism context by 4 independent
  subagents, classified into fixable-now / needs-new-mechanism /
  needs-custom-model. Result: 92% fixable within current architecture
  (GRAMMAR and FIXED_TERM_OR_IDIOM 100% rule-fixable,
  FACTUAL_OR_LOGICAL_REVERSAL 85%), 7% needs a new but still
  non-learned mechanism (three recurring patterns: cross-substitution
  coherence checking, pre-ranking WSD gate, restructuring
  content-coverage check), only 1% (2 cases, both escalation-tier
  chemistry causal/state reasoning) potentially needs a custom trained
  model. Decisive evidence against training something huge now.
  Analysis only, no fixes implemented, no production changes. →
  `DECISION_LOG.md` 2026-08-26-C.
- **2026-08-26, second** docs: consolidated the orphaned R42/R43/R43-A
  architecture documents into one archival file
  (`ARCHITECTURE_RESEARCH_R42_R43.md`), updated all cross-references,
  added a `DOCS.md` entry marking it archival. Documentation hygiene
  only. → `DECISION_LOG.md` 2026-08-26-B.
- **2026-08-26, first** feat: Phase 10 — broad stratified stress test
  of the current architecture. 133 new sentences (0 contamination vs
  154 prior sentences), 398 (sentence,profile) runs frozen before
  execution, harvested via live production reformulate(), blind-judged
  by 5 parallel subagents (no domain/category/difficulty shown), plus
  the frozen Phase 9B/9C validator checkpoints run unmodified on the
  same new material. Result: 26% CLEAN / 74% DEFECTIVE overall.
  Domain only a 6pt gap - content density/length predict failure far
  better than subject-matter label (chemistry/engineering/narrative
  0% CLEAN, math/stats 83% CLEAN). Difficulty gradient not smooth -
  moderate (18% CLEAN) worse than hard (30%). Profile constraint
  density is the cleanest predictor: multi_word profiles 0% CLEAN.
  Escalation ties substitution on quality, not a rescue mechanism.
  Neither validator checkpoint generalizes cleanly - 9C predicts
  DEFECTIVE 99% of the time (non-functional), 9B's CLEAN retention
  collapsed 62%->34% on new material. Evaluation only, no production
  changes, no training. → `DECISION_LOG.md` 2026-08-26-A.
- **2026-08-25, third** feat: Phase 9C — independent replication, seed
  change only. Exact re-run of 9B's pipeline (seed 42→123), paused
  mid-run and resumed cleanly via checkpoint. Conservative threshold's
  recall identical across seeds (0.65, both beat baseline on all three
  metrics). Aggressive threshold-selection not robust — healthy in 9B,
  but clean_recall crashed to 0.38 (below baseline) in 9C due to a
  tiny 6-example val CLEAN sample. Ranking stability: Spearman ρ=0.90,
  Pearson r=0.92 (p<0.0001) between the two models' scores. 9B's core
  finding replicates; the 77-91% recall headlines were partly
  threshold-selection luck, ~65% is the honest number. No production
  changes. → `DECISION_LOG.md` 2026-08-25-C.
- **2026-08-25, second** feat: Phase 9B — training instability fixed,
  controlled retry succeeded. Corrected R9's own diagnosis (gradient
  clipping and fp32 were already active by default; the real culprit
  was pos_weight~11 + lr=2e-5 + too-small adam_epsilon destabilizing
  DeBERTa). Retrained with lr=3e-6, pos_weight=4.0, explicit clipping,
  adam_epsilon=1e-6, early stopping, and a new abort-on-non-finite
  safety net — same unchanged dataset/split. Sanity pass then full
  8-epoch run both completed stably (confirmed: 0 NaN/0 Inf across
  70.8M params). Caught and fixed two evaluation bugs (a too-coarse
  threshold grid, and test-set leakage in threshold selection) before
  reporting. Final, methodologically clean result on the frozen test
  set: defect recall 0.77 vs baseline's 0.60, precision 0.92 vs 0.90,
  clean recall tied at 0.62 — a real improvement, not favorable
  threshold-picking. Justifies further development, not yet
  production-ready. No production changes. →
  `DECISION_LOG.md` 2026-08-25-B.
- **2026-08-25, first** feat: Phase 9 — learned validator prototype,
  training run diverged. Assembled the final 313-record dataset (252
  unique groups) and a unified leakage-safe split respecting R50's/
  Phase 8's frozen test assignments; computed existing-signal baselines
  fresh (best combo: SBERT<0.95 OR NLI OR grammar = 60% DEFECTIVE
  recall / 90% precision / 63% CLEAN recall). Fine-tuned a small
  cross-encoder (deberta-v3-xsmall, binary ACCEPT/REJECT,
  pos_weight~11) — training diverged to NaN at epoch 3.08 after a
  warning-sign gradient spike at epoch 2.69; saved model confirmed
  100% NaN weights. Evaluation ran exactly as planned and is reported
  in full, including that its output only numerically matched the
  reject-everything baseline by coincidence of `nan >= threshold`
  semantics — not a real result. None of the three gate questions
  answered. Root-cause hypothesis and fix recommended for a future
  attempt, not executed — no re-run performed, per instruction. →
  `DECISION_LOG.md` 2026-08-25-A.
- **2026-08-24, sixth** docs: R50 Phase 8B — targeted finalization,
  final GO/NO-GO decision. Targeted organic harvest on 4 causal-dense
  topics raised organic FACTUAL_OR_LOGICAL_REVERSAL yield ~6x (1/68 to
  9/58). A strict 3-step decision procedure raised GRAMMAR/WRONG_WORD_
  OR_SENSE inter-rater agreement to 56%/78% but left NATURALNESS_OR_
  REGISTER unchanged at 33% - retired as a primary label. The
  isolation-vs-whole-sentence labeling convention resolved and applied
  retroactively (18 records corrected). Final counts: FIXED_TERM_OR_
  IDIOM 53 unique (62% non-constructed), FACTUAL_OR_LOGICAL_REVERSAL 33
  unique (61% still constructed). Decision: GO scoped per class -
  proceed to validator prototype, with FACTUAL_OR_LOGICAL_REVERSAL
  results flagged directional/low-confidence pending more organic
  evidence. No training performed, no production changes. →
  `DECISION_LOG.md` 2026-08-24-F.
- **2026-08-24, fifth** docs: R50 Phase 8 — building the missing
  human-labeled dataset. 54 new real sentences (5 Wikipedia topics never
  used before) through today's live reformulate() across R40's 4
  profiles, yielding 68 unique blind-labeled cases; supplemented with 50
  disclosed non-blind constructed examples targeting the two thin
  classes; a second, independent subagent rater checked a 33-case
  stratified sample blind to the primary labels. Combined unique-case
  counts: FACTUAL_OR_LOGICAL_REVERSAL 7->28 (95% constructed, organic
  yield only 1/68), FIXED_TERM_OR_IDIOM 8->41 (organic yield 13/68,
  well above the ~8% estimate). Second-rater agreement: 88%
  acceptability, 70% primary defect type overall, but only 25%/33% on
  GRAMMAR/NATURALNESS_OR_REGISTER - a real taxonomy-boundary problem.
  Sufficiency: (B) - more organic factual-reversal data and a
  taxonomy-boundary refinement needed before training. Data collection
  only, no model trained, no production changes. →
  `DECISION_LOG.md` 2026-08-24-E.
- **2026-08-24, fourth** docs: R50 Phase 2/3/7/9 — dataset construction,
  defect-typed labeling, and baseline report. Joined/deduped R40/R44/
  R47/R48/v5 into 135 labeled records / 88 unique cases, added a
  structured defect taxonomy alongside existing severity, repaired R48's
  under-documented per-case verdicts (3/12 documented, 9/12 freshly
  re-read and tagged), benchmarked NLI/grammar/contextual_fit against
  the new taxonomy, froze a leakage-safe split. Finding:
  FACTUAL_OR_LOGICAL_REVERSAL and FIXED_TERM_OR_IDIOM (the two R49
  blind-spot classes) have only 7-8 unique labeled cases each — not
  enough to train or trustworthily evaluate a validator. Fixed-term
  erosion turns out to be a third, previously undifferentiated blind
  spot (0/5 caught); contextual_fit scores factual reversals ~40x
  higher than CLEAN cases, actively counter-indicative for that class.
  Sufficiency: (C) leaning (B) — a dedicated labeling pass is the
  evidenced next step, not validator training on what exists today.
  Research-only, no model trained, no production changes. →
  `DECISION_LOG.md` 2026-08-24-D.
- **2026-08-24, third** feat: R49 — the two remaining cheap escalation
  levers, both tried, both hit a real wall. Wider candidate sampling
  (beam 13-21 + independent temp/top_p sampling, n=23-24) on the 11
  cases v3 still refuses: rescued 0/11. Found/fixed a KeyError (raw vs.
  sanitized text mismatch) and a literal -inf in
  PhonemeConstraintLogitsProcessor that produced NaN under sampling
  (do_sample) though it was safe for beam search - switched to a finite
  _KILL_SCORE=-1e9. A prompted local-LLM validator (Qwen2.5-0.5B/1.5B,
  both already cached, verdict-first and reasoning-first prompts) on 8
  hand-picked BAD/GOOD cases: 0.5B=4/8, 1.5B verdict-first=5/8, 1.5B
  reasoning-first=3/8 - unreliable in different, non-convergent ways
  per configuration. Per the user's own pre-set threshold, this marks
  "build something custom" as the evidenced answer for the wrong-word-
  substitution and factual-reversal blind spots specifically - not a
  claim the rest of the architecture is obsolete. → `DECISION_LOG.md`
  2026-08-24-C.
- **2026-08-24, second** feat: R47/R48 — architecture pushed to its
  evidenced ceiling. R47: 10 fresh sentences through both pipelines,
  found a third independent instance of the sanitize_input() SVA bug.
  R48: a substitution-tier fix hypothesis tested and correctly
  abandoned (fails against R31's own known-good cases); an escalation
  fix (phoneme constraint + iterative regeneration combined) built,
  found to have a real over-blocking bug (degenerates to gibberish),
  fixed, then found to ship a "rational"->"irrational" antonym flip
  that only NLI caught - fixed by making NLI a real gate inside
  escalation. Final: 12/23 (52%, same count, safer set) - antonym flip
  now refused, "starch"->"glucose" replaced by correct "cornstarch".
  Manual read: 5 CLEAN/4 MINOR/3 SEVERE of 12, down from R40's 74%
  severe. Full suite passes throughout. → `DECISION_LOG.md`
  2026-08-24-B.
- **2026-08-24, first** feat: R46 wired into app.py behind an opt-in
  sidebar toggle ("Try next-gen escalation"), defaulting to unchecked.
  Off = byte-identical to before (full app_test.py suite passes
  unchanged). On = routes to reformulate_v2(), shows a diagnostic
  validator banner (never blocking), adds NLI/grammar detail to the
  Verification tab. Verified with a new headless toggle smoke test and
  a live app launch. → `DECISION_LOG.md` 2026-08-24-A.
- **2026-08-23, fourth** feat: R46 — R45's architecture built as real,
  tested, additive code. rephrase.generate_candidates_phoneme_
  constrained(), semantic.logical_consistency_check()/
  grammar_issue_count(), reformulate.reformulate_v2()/
  _try_escalation_v2() - new functions only, reformulate()/app.py
  untouched (full suite passes, smoke.py byte-identical to baseline).
  reformulate_v2() reproduces R45's measured 52% escalation success
  rate exactly on the real integrated pipeline; new validator caught
  the "slower->faster" inversion and the "glucose" case for real.
  Not wired into app.py - additive code, not a shipped feature. →
  `DECISION_LOG.md` 2026-08-23-D.
- **2026-08-23, third** test/docs: R45 — two bounded prototypes and the
  architecture decision. Prototype 1 (combined NLI+grammar validator,
  all 79 substitution-tier pairs): 32% recall on SEVERE, vs ~20% for
  either check alone. Prototype 2 (phoneme-aware decoding-time
  constraint via a custom LogitsProcessor, 23 escalation cases): the
  largest improvement in the whole arc - leak-free 4%->100%, usable
  candidates 9%->52%. Manual read found ~half of "accepted" outputs
  still carry a meaning/logic defect (never a leak) - exactly what
  Prototype 1 targets. Decision: both work, combine them into the
  next-generation hybrid; fine-tuning explicitly not justified. →
  `DECISION_LOG.md` 2026-08-23-C.
- **2026-08-23, second** test/docs: R44 — bounded v5 human evaluation,
  the pre-redesign baseline. n=1, 20 sentences from R40's Track C
  corpus. Strong aggregate agreement with R40's audit (monotonic
  CLEAN>MINOR>SEVERE across meaning/naturalness/ease/preference), but
  SEVERE splits near-evenly: nonsense/wrong-sense/register-confusion
  reliably rejected (7/12), grammar/fixed-term/subtle-factual/logical-
  inversion defects tolerated and often preferred (5/12) - including
  one case correctly named in free text ("slower easier are not fine")
  yet still preferred overall. Overall preference 70%. →
  `DECISION_LOG.md` 2026-08-23-B.
- **2026-08-23, first** docs: R42/R43/R43-A — architecture reassessment,
  T5 escalation instrumentation, four bounded fixes tested and stacked.
  Escalation fails 96% of the time from constraint-satisfaction failure,
  not generation quality (76% pass SBERT). 68% of leaks are the blocked
  word's own morphological variants, not unrelated same-sound words -
  corrects R42's initial hypothesis. Stacking every validated fix
  (A1+A3+A4) still leaves only 1/23 dense-profile sentences with a
  candidate that clears a comprehensive check - the ceiling is the
  candidate pool, not the checks. Points toward redesigning the
  escalation tier's generation mechanism. No production changes. →
  `DECISION_LOG.md` 2026-08-23-A.
- **2026-08-22, second** test/docs: R41 — bounded validation of
  contextual_fit as a candidate substitution-quality gate, against
  R40's 112 labeled changes. Real signal (CLEAN median 0.0078 vs.
  SEVERE median 0.00004) but heavy overlap — at threshold 0.01, 94% of
  severe defects caught but 62% of genuinely fine substitutions also
  wrongly rejected. Blind to factual/logical-correctness errors
  ("palaeolithic", "half-century" score 0.6-0.999). Revises R40's
  earlier 6-example optimism. No threshold promoted, no gate, no fix.
  → `DECISION_LOG.md` 2026-08-22-B.
- **2026-08-22, first** test/docs: R40 completed — systematic audit of
  all 112 individual substitutions (not just a curated worst-of list).
  8/112 CLEAN (7%), 21/112 MINOR (19%), 83/112 SEVERE (74%). New
  findings: `sanitize_input()`'s spellchecker independently corrupts
  "optimises"→"optimists"; worst single case "slower"→"easier" inverts
  its sentence's logic while `antonym_check` passed it. → `DECISION_LOG.md`
  2026-08-22-A.
- **2026-08-21, second** test/docs: R40 — ceiling probe (192 real
  sentence×profile pairs, live engine) + direct linguistic audit of the
  79 "successful" outputs, on user request. 11% fail both tiers; T5
  restructuring succeeds in only 2/192 runs (1 sentence) — not
  functioning as a fallback. Direct reading found real defects the
  pipeline scores as passing: nonsense fragments, a ~50,000-year factual
  error dressed as synonymy, substitution-introduced grammar errors, a
  fixed term ("small talk") eroding 6x. R37's contextual_fit
  (reported-only) scores ≤0.0007 on 5/6 of the worst cases — an unused
  signal that would catch most of this. Findings only, no fix
  implemented. → `DECISION_LOG.md` 2026-08-21-A.
- **2026-08-21, first** test/docs: R39 — current-state human evaluation
  executed (n=1). 20 pairs regenerated through today's live engine
  (live Datamuse). Group A matched-pair delta vs. v3: 2 confirmed
  fixes (R19/R25, R27), 1 confirmed regression ("sleep"→"nap"), 1 case
  where R30's fix works but exposed a separate open problem
  ("after-hours"), 3 stable known defects reconfirmed. Group B: 80%
  preference. v3 data archived to eval/archive_v3/, not overwritten.
  → `DECISION_LOG.md` 2026-08-20/21-A.
- **2026-08-19, twelfth** docs: R38 — final system-level evaluation,
  closes the R17-R37 arc. Safety + SBERT-enforced meaning are the
  strongest claims; preference is unresolved (only stale pre-R19
  data exists). Retroactive contextual-fit check on real pilot data
  found 2 new false positives beyond "rest." Recommends a genuine
  current-state human evaluation next. → `DECISION_LOG.md`
  2026-08-19-L.
- **2026-08-19, eleventh** feat: R37 — contextual-fit signal wired in as
  a reported-only diagnostic (Option A). First production code change
  in the R28-R36 investigation arc. Substitution-sourced changes only,
  scored against the final sentence, never gates anything. 12 new
  tests, 131 total pass, zero collateral change on the regression
  baseline. → `DECISION_LOG.md` 2026-08-19-K.
- **2026-08-19, tenth** docs: R36 — larger naturalness-signal validation
  (38 new cases). Zero false negatives at every threshold; false
  positives concentrate specifically on "rest." Register-mismatch
  blind spot confirmed real but not universal (2/5 stress cases, not
  5/5). Inflection/word-class confirmed as a complementary catch.
  Multi-substitution: no cross-contamination between positions,
  validating the Phase-2 design. Evidence supports Option A
  (reported-only) now, not yet Option B. → `DECISION_LOG.md`
  2026-08-19-J.
- **2026-08-19, ninth** docs: R35 — human validation of the DistilBERT
  signal, 17/18 agreement. Both R34's critical seize/clutch cases
  confirmed by a human rater. One real blind spot found: R30's own fix
  ("belated") rated Unnatural despite being the highest-scoring
  sentence in the set — a register/formality mismatch the signal
  doesn't catch. Carried forward into trigger design, not smoothed
  over. → `DECISION_LOG.md` 2026-08-19-I.
- **2026-08-19, eighth** docs: R33+R34 — GPT-2 perplexity rejected
  (rated R30's own fix worse than its bug). DistilBERT masked-LM
  word-probability found strong on matched contrast pairs; the one
  open ambiguity (seize/clutch scoring like known-bad cases) resolved
  directly — natural context scores 0.05-0.44, forced context 0.0000,
  a real mismatch signal not a rarity bias. Not yet human-validated or
  implemented. → `DECISION_LOG.md` 2026-08-19-H.
- **2026-08-19, seventh** docs: R32 — multi-substitution interaction
  ruled out as a distinct mechanism. 5/5 real+constructed cases (not
  just the original 3) show every failure traces to one bad
  substitution, never interaction between two. Redirects next
  investigation toward a general grammaticality signal (R33). →
  `DECISION_LOG.md` 2026-08-19-G.
- **2026-08-19, sixth** docs: R31 — built a broader evaluation corpus
  and found R29's genericness signal flags two real pilot cases humans
  rated 5/5/5 and preferred. Not promoted; stays research-only. →
  `DECISION_LOG.md` 2026-08-19-F.
- **2026-08-19, fifth** fix: R30 — fixed the predicate-adjective
  POS-tagging bug behind pair_13 ("was late" mis-tagged RB, producing
  "was recently again"). Curated flat-adverb list, not a general
  re-tagger (a broader WordNet-sense check over-fired on "here").
  3 new tests, zero collateral change. → `DECISION_LOG.md` 2026-08-19-E.
- **2026-08-19, fourth** docs: R29 — designed and validated a candidate
  specificity/genericness signal for R26/R27's "grab"→"take" pattern
  (WordNet hypernym-depth delta + Zipf-frequency delta, requiring both
  to flag). Validated across 4 real cases; not implemented — no ranking
  weights or code changed. → `DECISION_LOG.md` 2026-08-19-D.
- **2026-08-19, third** test/docs: R28 — grammaticality resolved and
  measured (negative: LanguageTool caught 0/7 known-broken outputs, ruled
  out for this use case, not just unblocked), plus a latent
  `grammar.py` attribute bug found and disclosed (not fixed). Added
  `tests/meaningbert_test.py` (9 tests), closing the zero-coverage gap
  the prior audit found. → `DECISION_LOG.md` 2026-08-19-C.
- **2026-08-19, second** chore/docs: repo cleanup + doc refresh. Removed
  `changes.md` (superseded by this file, described removed features).
  Confirmed `paths.py`/`grammar.py`/`config.yaml`/`rewrite/`/`profiling/`/
  `eval/study/` are all still load-bearing or active comparison-baseline
  evidence, not unused. Refreshed `HANDOFF.md`/`DOCS.md`/`README.md` —
  all three were frozen at the pre-R19 (2026-08-16) state and materially
  misdescribed the current engine (no mention of the idiom guard, WSD,
  phrase-level tier, or MeaningBERT); corrected specific stale/false
  claims rather than just adding notes (the R5/R6 comparison "not yet run"
  claim, the R9 keep/revert feedback loop "not wired" claim). →
  `DECISION_LOG.md` 2026-08-19-B.
- **2026-08-19** feat: R27 — bounded investigation of R26's ranking
  mechanism and grammaticality, then MeaningBERT wiring + idiom-guard
  extension. Found two distinct causes for `push`→`force`/`grab`→`take`
  (missing WordNet sense; generic-word embedding bias, not primarily a
  frequency-weight problem). Confirmed the output-verification path has
  no grammaticality check anywhere; LanguageTool is blocked by a Java
  version mismatch (needs 17+, has 8), not absence — corrects R23's
  guess. MeaningBERT wired in as a read-only reported signal (verified
  against R24's own recorded scores); idiom guard extended with "push
  the meeting" (verified: exactly one pilot pair changed, zero
  collateral). Grammaticality wiring did not proceed — blocked, surfaced
  for a decision. An orchestration principle for a future quality-based
  escalation trigger (substitution stays default; full-sentence rewrite
  is an alternative, not a replacement) recorded per direct instruction,
  not implemented. → `DECISION_LOG.md` 2026-08-19-A; `VALIDATION.md`
  §18-20; `ROADMAP.md` R27.
- **2026-08-18** docs: R26 — re-examined the pilot's `multi_difficulty`
  category against the live phrase tier (Option E). Pure analysis, no
  new code. Corrects §2.7's own prior hypothesis: only 1 of 3 cases
  involves an idiom span (a mixed case R25 correctly excludes by
  design); the other 2 trace to a separate, already-named pattern
  (generic overused replacement words), not idiom-blindness. Factor 2.7
  stays open as its own problem. → `DECISION_LOG.md` 2026-08-18-D;
  `VALIDATION.md` §17; `ROADMAP.md` R26.
- **2026-08-18** feat: R25 — phrase-level replacement tier (Option A of
  the approved C → A → E sequence). New `semantic.idiom_spans()` and
  `reformulate._try_phrase_replacement()`: when a sentence's only
  difficulty is idiom-locked, tries a local-window T5 replacement
  (reusing `rephrase.generate_candidates` unchanged) instead of only
  leaving it alone, spliced into and verified against the full
  sentence. Falls back to R19's exact prior behavior when nothing
  clears every gate. Verified with an isolated `git stash` before/after
  against the frozen pilot corpus: recovered exactly one case
  (pair_01), byte-identical everywhere else across three corpora. One
  honest limitation surfaced: the recovered output is grammatically
  thin despite passing every automated gate. 8 new regression tests. →
  `DECISION_LOG.md` 2026-08-18-C; `VALIDATION.md` §16; `ROADMAP.md` R25.
- **2026-08-18** test: R24 — validated MeaningBERT as a candidate
  second semantic-preservation signal, scoped tightly (14 already-
  recorded pairs, one small model, no long-running sweep) per direct
  instruction after R21-R23 closed the model-swap avenue. Real but
  partial: catches several idiom-adjacent breaks SBERT missed badly,
  but completely misses the single worst-rated case on record — the
  same class the (not-yet-built) phrase-level tier targets
  structurally. Proceed as a reported-alongside signal only, never a
  replacement for SBERT. Engine wiring not yet built. →
  `DECISION_LOG.md` 2026-08-18-B; `VALIDATION.md` §15; `ROADMAP.md` R24.
- **2026-08-18** test: R23 — decoder-only instruction-tuned model
  (Qwen2.5-0.5B/1.5B-Instruct) benchmarked against the T5 escalation
  baseline on R21's 22 failing cases. Closed negative: worse meaning
  preservation than both the baseline and R21's flan-t5-base result,
  10-40x slower per case, and the smaller model often failed to perform
  the rewrite task at all. Closes `REFORMULATION_PROBLEM_MAP.md` §5
  item 3's investigation on a third independent angle — none of
  prompting, constrained decoding, or a model-family swap cleared the
  bar. The current T5 baseline stands. →
  `DECISION_LOG.md` 2026-08-18-A; `VALIDATION.md` §14; `ROADMAP.md` R23.
- **2026-08-17** feat: R20 — word-sense disambiguation before candidate
  generation, `REFORMULATION_PROBLEM_MAP.md` §5's item 2. Fixes the
  general "right"→"justly"/"properly" sense-confusion bug (VALIDATION.md
  §9.9), not just the "right now" phrase R19 already covered. Re-running
  Stage 6's corpus (per direct instruction) found two real regressions
  before this was done — a candidate colliding with another declared-
  difficult word, and whole-sentence context failing to disambiguate two
  occurrences of the same word in one sentence — both root-caused and
  fixed in the same pass. Re-confirmed at scale on the 210-case ordinary-
  text corpus: escalation-trigger rate rose 10.4%→14.1% at an unchanged
  ~42% success rate, a real, disclosed cost that raises R18's priority.
  Re-checked against the real pilot data: two of P1's own articulated
  grammar complaints now directly fixed. → `DECISION_LOG.md` 2026-08-17-J;
  `VALIDATION.md` §11; `ROADMAP.md` R20.
- **2026-08-17** feat: R19 — idiom/fixed-expression guard for
  substitution, `REFORMULATION_PROBLEM_MAP.md` §5's item 1.
  `semantic.py` gained a curated idiom-phrase list + pronoun-wildcard
  pattern, reusing the existing `protected_positions()` mechanism.
  Verified against real pilot data: the exact broken outputs P1 rated
  poorly ("how's it taking", "going me crazy") no longer occur; 26/30
  pilot pairs and both Stage 6/escalation-rate eval corpora (18 + 210
  cases) are byte-identical, zero collateral change. Found and fixed a
  follow-up metrics bug in the same pass (idiom-protected words were
  silently excluded from flagged-word counts, making "difficulty
  resolved" misleading) — now correctly reported as unresolved instead.
  Honest trade-off disclosed: an idiom-locked difficulty is now left
  unaddressed rather than shipped broken. New tests
  (`tests/semantic_test.py`, 3 new cases in `tests/reformulate_test.py`)
  and a new diagnostic (`eval/idiom_guard_recheck.py`). →
  `DECISION_LOG.md` 2026-08-17-I; `VALIDATION.md` §10; `ROADMAP.md` R19.
- **2026-08-17** feat: interface audit of `app.py` — removed dead
  `.pipe-card` CSS, softened three places implying the SBERT meaning-check
  is a stronger guarantee than pilot evidence supports (sidebar banner,
  "How it works" blurb gained a "Known limits" note, results metric
  relabeled "Meaning similarity" with a new caveat caption). No layout,
  feature, or engine change. `tests/app_test.py` + `tests/smoke.py`
  reconfirmed passing. → `DECISION_LOG.md` 2026-08-17-H.
- **2026-08-17** docs: added `REFORMULATION_PROBLEM_MAP.md` — a new
  **living** Problem Definition/Research Map for the reformulation engine
  (nine factors: input-intent inference, in-context meaning preservation,
  grammaticality, naturalness/idiomaticity, profile-difficulty resolution,
  word sense, cross-substitution interaction, restructuring vs.
  substitution, change-amount trade-off), each checked against real pilot
  data and, for the interaction factor, against `reformulate.py`/
  `semantic.py` source directly. Includes a sourced research pass (idiom/
  MWE detection, WSD, constrained generation, GEC/clarification precedent,
  stuttering/AAC literature, semantic-preservation metrics) with
  feasibility ratings and a proposed implementation order. `CLAUDE.md`
  reading order and `DOCS.md` index updated to point to it. →
  `DECISION_LOG.md` 2026-08-17-H.
- **2026-08-17** docs: analyzed P1's real 30-item v3 pilot data —
  meaning=4.13/5, naturalness=4.07/5, ease=+1.10, preferred-reformulated
  73.3%. Sharp category split (content-word targets near-perfect,
  sound-based targets weaker, multi-difficulty worst). Best-evidenced
  finding: SBERT overestimates meaning preservation relative to the
  human rater in every disagreement case (never the reverse), most
  often when substitution breaks a fixed idiom — replicates an earlier
  single example as a repeatable pattern. Also found: a reproducible
  "right now" sense-disambiguation bug, a frequency-bias pattern in
  candidate ranking, two under-counted human-missed/human-tolerated
  errors, and an unanticipated reversal (restructuring outperformed
  substitution on every human axis, n=8 vs n=22). No code changed —
  analysis only, per explicit user instruction. →
  `DECISION_LOG.md` 2026-08-17-G; `VALIDATION.md` §9.6-9.11.
- **2026-08-17** feat: Stage 7 v3 — P1 actually completed v2's 20-pair
  pilot (first real human-judgment data collected: meaning 4.65/5,
  naturalness 4.70/5, ease +1.75, preferred reformulated 19/20). That
  real use found a genuine UI bug — boxes labeled "Sentence 1/2" plus a
  separate caption meant P1's free-text comments sometimes described the
  reformulated text as if it were the input. Rebuilt as v3 per direct
  user review: single participant, 30 short/natural/everyday sentences
  only (18 global-sound / 5 declared-word / 4 word-pattern / 3
  multi-difficulty), Original/Reformulated labeled directly on each box,
  full per-item profile-traceability metadata, and human ratings now
  explicitly scoped to meaning/naturalness/ease/preference only —
  profile-match effectiveness is automated and reported separately,
  never asked of the participant. A second bug (an `AppTest` test-
  harness fragility across many sequential form-submits, not the pilot
  app) found and fixed while verifying the new 30-pair flow end-to-end
  with synthetic data. v2's real P1 data and pair set archived at
  `eval/archive_v2/`, not deleted. Zero `reformulate.py` changes — full
  suite (78 tests) + `tests/smoke.py` re-confirmed. →
  `DECISION_LOG.md` 2026-08-17-E/F; `VALIDATION.md` §8.7, §9;
  `ROADMAP.md` R4.
- **2026-08-17** feat: Stage 7 — built and verified (synthetic data) a
  human-evaluation pilot for `reformulate.py`: `eval/pilot_select_pairs.py`
  (deliberate, non-random 20-pair selection from a 69-case eligible pool,
  including known-weak Stage-6 cases and two newly-found genuine errors),
  `eval/pilot_app.py` (minimal Streamlit collection instrument,
  counterbalanced), `eval/pilot_analyze.py` (per-pair summaries +
  proxy-vs-human disagreement flagging). Full workflow driven end-to-end
  with synthetic responses via `AppTest` before any real participant —
  all checks passed. Real 4x20 data collection not yet run. Zero changes
  to `reformulate.py` — confirmed via full suite (78 tests) +
  `tests/smoke.py`. → `DECISION_LOG.md` 2026-08-17-C; `VALIDATION.md` §8;
  `ROADMAP.md` R4.
- **2026-08-17** feat: R9 — Keep/Revert toggles now record a feedback
  signal (kept/reverted counts) against the declared word/sound entry
  responsible for each substitution, stored in that entry's existing
  `meta` field and shown as a small badge in the profile panel.
  Prototype scope only — nothing reads this field back into
  `reformulate.py`'s ranking yet, by design. New:
  `reformulate.feedback_targets()`,
  `difficulty_profile.record_feedback()`/`undo_feedback()`. 11 new
  tests; full suite (78) and `tests/smoke.py` confirm the reformulation
  engine itself is unaffected. → `DECISION_LOG.md` 2026-08-17-A;
  `ROADMAP.md` R9.
- **2026-08-16** eval: Stage 6 — ran `reformulate.py` against both
  retained legacy pipelines on a new 18-case failure-mode corpus
  (`tests/reformulation_eval_corpus.json`, `eval/reformulation_eval.py`).
  New engine: highest meaning preservation (0.979) and smallest edits
  (0.068), but lowest reformulation rate (0.556 vs. 0.889/0.833) — fully
  explained by a 0/4 T5-restructuring-escalation success rate, root-caused
  into a fixable case-sensitivity bug in `rephrase.py::_bad_words_ids()`
  (`ROADMAP.md` R17) and a deeper paraphrase-model/phoneme-avoidance
  mismatch (`ROADMAP.md` R18, confirms `REFORMULATION_RESEARCH.md` §24.E
  with evidence for the first time). Also found: a pre-existing
  `SentenceRewriter` inflection bug, the context-dependent-substitution
  failure mode persisting in all three systems, and a directly-observed
  case where SBERT scored a redundant rewrite at 0.965 — concrete evidence
  for the proxy-metric warning, not just a restatement. Measurement only,
  nothing tuned. → `VALIDATION.md` §6; `DECISION_LOG.md` 2026-08-16-G;
  `ROADMAP.md` R6 (superseded)/R17/R18.
- **2026-08-16** chore: pre-evaluation cleanup pass — removed dead surface
  the D′/UI redesign left behind: `run_app.ps1` (broken paths, described
  a removed ASR feature), `profile_store.py`'s `load_preferences`/
  `save_preferences` and the on-disk `preferences`/`custom_replacements`
  fields (zero live consumers — traced every caller before removing),
  `tests/persistence_test.py` (tested only that now-removed round-trip),
  `freq.py::active_wordlist()` (zero call sites), two unused imports in
  `reformulate.py`, `torchvision` from `requirements.txt` (flagged unused
  and deferred back in 2026-08-15-A, now actually removed), and a stale
  `.gitignore` line. `grammar.py::SentenceRewriter`, `rewrite/`,
  `profiling/`, `eval/`, `config.yaml`, `scripts/` all investigated and
  kept — confirmed still genuinely exercised (by `smoke.py`/
  `threshold_sweep.py`/`evaluate.py`/`roadmap_test.py`/`eval/metrics.py`)
  and load-bearing for the upcoming evaluation-stage comparison. `README.md`
  rewritten where it still described the removed v7 UI as current. No
  reformulation behavior changed — `tests/smoke.py` byte-identical to
  baseline; 56 unittest cases + 2 script suites all pass. →
  `DECISION_LOG.md` 2026-08-16-F.
- **2026-08-16** feat: implement Architecture D′ (`reformulate.py`) and
  redesign `app.py` (v7 → v8) around it — one linear workflow (text →
  difficulty profile → Reformulate → changes/skipped/verification review
  with per-change Keep/revert) replacing the old dual-pipeline UI (word
  pickers, separate word/sentence/multi-sentence modes, profile-rewrite
  card, rephrase card, allowlist panel, the onset-risk chart, which was
  quietly re-displaying declared sounds as if learned from sessions that
  no longer exist in this module's scope). New `naturalness.py`
  (edit-ratio metric, R11). `semantic.py` extended additively
  (`is_known_antonym`, `negation_consistent`). Two real bugs found via
  live smoke tests, not unit tests, and fixed before shipping: escalation
  wrongly rejected everything when SBERT was offline (contradicted
  `semantic.py`'s own documented fallback); escalation's word-block set
  included non-substitutable words (numerals), guaranteeing failure
  whenever one was present. `grammar.py::SentenceRewriter` and
  `rewrite/rewriter.py::DifficultyAwareRewriter` untouched, just no longer
  called. `tests/smoke.py` byte-identical to `baseline_sbert.txt`. New
  `tests/reformulate_test.py` (12 tests); `tests/app_test.py` rewritten
  for the new UI (all scenarios pass). → `DECISION_LOG.md` 2026-08-16-E;
  `ROADMAP.md` R5/R6/R9/R10/R11/R12/R13.
- **2026-08-16** docs: append Stage 5B critical review (§24–31) to
  `REFORMULATION_RESEARCH.md` — challenged and revised Stage 5's
  recommendation (tiered semantic verification instead of flat NLI, MLM
  candidates deferred pending measurement, position/stress corrected to
  logged-not-scored per this project's own Practice.md §6 discipline, a
  new count-threshold restructuring trigger, T5's constraint-mechanism
  limit found by reading `rephrase.py`'s actual code), then produced the
  exact input/output contract, MVP/Strong/Future split, evaluation plan,
  failure-handling states, and implementation blueprint. Architecture
  declared implementation-ready. Zero reformulation code changed. →
  `DECISION_LOG.md` 2026-08-16-D.
- **2026-08-16** docs: add `REFORMULATION_RESEARCH.md` — Stage 5 deep
  research pass on the reformulation-engine architecture itself: Brown's
  four stuttering-loci factors, a second close prior system (SpeechAgent,
  2026), minimal-edit tagging architectures (GECToR/FELIX, researched and
  found infeasible here for lack of training data, not hardware), concrete
  CPU-feasible NLI/constrained-decoding tooling, ten constructed failure
  modes, and a ranked architecture recommendation (candidate-gen+rank with
  a generation escalation path and symbolic final verification). Pure
  research — zero lines changed in `grammar.py`/`semantic.py`/`engine.py`/
  `rewrite/`/`rephrase.py`. → `DECISION_LOG.md` 2026-08-16-C; updates to
  `ROADMAP.md` R2/R6/R8/R9/R10/R11.
- **2026-08-16** fix: foundation audit found and fixed two real ambiguities,
  verified against live CMU data — heteronym words (`"read"`, `"the"`, etc.)
  silently used only the first CMU pronunciation variant, now flagged
  (`has_alternate_pronunciations`); `add_sound_from_phones()`'s promoted
  entries could silently fail to round-trip through the legacy matching
  bridge for phones with no natural English spelling (e.g. ZH), now flagged
  (`legacy_bridge_unreliable`). Both surfaced as UI warnings, not silent
  gaps. `tests/difficulty_profile_test.py` 38→44, `tests/app_test.py`
  6→7 scenarios. → `DECISION_LOG.md` 2026-08-16-B; `PROBLEM_FORMULATION.md`
  §11; `ROADMAP.md` R15/R16.
- **2026-08-16** feat: word-specific sound patterns (`problem_phones` on word
  entries — "three" difficult ≠ "TH"/"R" globally difficult, unless
  explicitly promoted) via a new inline pattern-editor panel in `app.py`,
  phone display via a new `phonetic.friendly_phone_label()` respelling
  table. Multi-user system removed: `auth.py`/`user_store.py` deleted, new
  `profile_store.py` loads one default profile automatically (no login),
  keeping a `profile_name` parameter throughout for future extensibility.
  `users/bobcat.json` deleted; `users/default.json` rewritten with no
  `password_hash`/`phoneme_profile` fields. Zero changes to
  `grammar.py`/`engine.py`/`semantic.py`/`rewrite/`/`rephrase.py`/
  `profiling/profile.py` — `tests/smoke.py` byte-identical to baseline.
  Tests: `tests/difficulty_profile_test.py` 38/38 (12 new);
  `tests/app_test.py` extended to 6 scenarios; `tests/persistence_test.py`
  rewritten against `profile_store.py`. → `DECISION_LOG.md` 2026-08-16-A;
  `PROBLEM_FORMULATION.md` (rewritten in place); `ROADMAP.md` R0/R12/R13.
- **2026-08-15** feat: add `difficulty_profile.py` — persistent, user-declared
  speaker difficulty profile (sounds/words/phrases, kept explicitly
  independent). New `app.py` "Speaker Difficulty Profile" panel replaces the
  old Phoneme-Profile panel and absorbs the redundant Blocklist column.
  Additive-only to the reformulation pipeline: `phonetic.py` gains one new
  informational function, `user_store.py` gains a difficulty-profile store
  that auto-mirrors the legacy `phoneme_profile` fields. Zero changes to
  `grammar.py`/`engine.py`/`semantic.py`/`rewrite/`/`rephrase.py`/
  `profiling/profile.py` — verified via `tests/smoke.py` being
  byte-identical to baseline. New tests: `tests/difficulty_profile_test.py`
  (26 tests); `tests/app_test.py` extended with a live-widget scenario.
  Full design record in `PROBLEM_FORMULATION.md`. → `DECISION_LOG.md`
  2026-08-15-C; `ROADMAP.md` R12–R14.
- **2026-08-15** docs: add `RESEARCH.md` — literature/technical-approach
  review across paraphrase generation, lexical substitution, simplification,
  semantic-preservation evaluation, controlled generation, phoneme-aware
  NLP/speech accessibility, and personalization, plus a component-by-
  component critical assessment of this repo's implementation against it.
  Closes `ROADMAP.md` R3; adds R8–R11. No implementation changed. →
  `DECISION_LOG.md` 2026-08-15-B.
- **2026-08-15** repo: narrow scope to the text reformulation module —
  move `voice.py`, `profiling/asr.py`, `profiling/detect.py`,
  `sample_stutter.json` to `out_of_scope/`; strip the corresponding UI from
  `app.py`; split `tests/roadmap_test.py`; fix README's stale `0.65/0.35`
  semantic-weight description. No rewrite algorithm/threshold/weight
  changed. → `DECISION_LOG.md` 2026-08-15-A.
- **2026-06-13** `11ef678` test: add `sample_stutter.json` fixture for
  profile-update testing without CrisperWhisper.
- **2026-06-13** `7abfe97` docs: v6.0.1 changelog (model-loading
  reliability + low-RAM support). → see `DECISION_LOG.md` 2026-06-08-E.
- **2026-06-13** `d292cfb` feat: fluency rephrase + mic profiling fixes,
  low-RAM model loading. → `DECISION_LOG.md` 2026-06-08-E.
- **2026-06-13** `043b331` merge: resolve conflicts from remote main.
- **2026-06-13** `3c1b5a1` merge: `feature/roadmap-implementation`.
- **2026-06-13** `daba899` docs: README + changes.md for v6.0.0 fluency
  rewrite roadmap.
- **2026-06-13** `fc8bece` feat(eval): add eval harness and roadmap
  regression tests. → `VALIDATION.md` §1.
- **2026-06-13** `8d7cb04` feat(ui): integrate profile-aware rewrite card
  and fluency profile chart into Streamlit app.
- **2026-06-13** `f238e88` feat(prefs): add `profile_rewrite_enabled`
  preference, default true.
- **2026-06-13** `277a205` feat(config): add `config.yaml`, update
  gitignore/requirements for profiling stack.
- **2026-06-13** `09610be` feat(rewrite): add profile-aware rewrite
  engine. → `DOCS.md` (`rewrite/` module), `ROADMAP.md` R5.
- **2026-06-13** `a0b632e` feat(profiling): add fluency profiling, ASR,
  and disfluency detection.
- **2026-06-12** `5648765` Implement roadmap PDF: voice uploads,
  profile-aware rewrites, evaluation harness.
- **2026-06-09** `f0ac889` Optional model added in comments.
- **2026-06-09** `f58ff6d` docs: README update — voice input/output
  support.
- **2026-06-09** `0d2cf0e` Add voice integration and speech improvements.
  → `ROADMAP.md` H1 (unverified `st.iframe` usage).
- **2026-06-09** `0f793b1` Make rephraser clone-and-run: add
  sentencepiece+tiktoken, disable hf-xet to prevent download hangs,
  document teammate setup.
- **2026-06-08** `1855813` Task K: rephrase fine-tuning scaffolding.
- **2026-06-08** `a53eb6b` Task J: deterministic evaluation harness.
  → `VALIDATION.md` §1.
- **2026-06-08** `74d7338` Task I: persist allowlist and rephrase
  preference.
- **2026-06-08** `bdbe6c9` Task H: wire optional fluency rephrase UI.
- **2026-06-08** `2e1a189` Task G: add optional rephrase module
  (`rephrase.py`).
- **2026-06-08** `b0280e1` Task F: repair Streamlit `AppTest` harness.
- **2026-06-08** `b7593f0` Task E: add `tests/threshold_sweep.py`
  diagnostic — recommends `MIN_SEMANTIC~0.80` vs. current `0.85`; default
  left unchanged. → **`DECISION_LOG.md` 2026-06-08-A** (unresolved finding
  — see `ROADMAP.md` R1).
- **2026-06-08** `02b54c4` Task D: smoke WORD MODE mirrors app behavior;
  regenerate `baseline.txt` / `baseline_sbert.txt`.
- **2026-06-08** `b1b71ad` Task C: fix paragraph rebuild off-by-one.
- **2026-06-08** `b04a4a6` Task B: allowlist locks words in place. →
  **`DECISION_LOG.md` 2026-06-08-D**.
- **2026-06-08** `5c8b149` Task A: strip edge punctuation/case in engine
  token split (fixes word-mode "No synonyms found" for trailing-punct
  input).
- **2026-06-08** `39c1d78` Pre-flight: fix `requirements.txt` line
  endings; capture behavior baseline.
- **2026-06-08** `0fecf23` Fix adjective overcorrection, remove double
  `sanitize_input` call, add custom-word phoneme checks, harden word-mode
  renderer. → notable: this is the commit era where the semantic-scoring
  re-weighting (`DECISION_LOG.md` 2026-06-08-B) also happened.
- **2026-06-08** `4904ba2` Upgrade grammar engine: spelling correction +
  LanguageTool integration.
- **2026-06-08** `902c0a8` docs: update `AUTH_README.md`. → contains the
  `.gitignore` claim later found stale, see `DECISION_LOG.md` 2026-06-13-A.
- **2026-06-08** `b0a5c03` docs: update README.
- **2026-06-07** `50f5d18` docs: update README.
- **2026-06-07** `249f107` remove previous preference backup files.
- **2026-06-07** `a465f3c` feat: multi-user architecture, grammar
  rewriting, UI enhancements, semantic rules update. → introduces
  `user_store.py`/`auth.py`, see `DECISION_LOG.md` 2026-06-07-A.
- **2026-06-07** `fc66876` Grammar integration and UI validation fixes.
- **2026-06-07** `cb78157` chore: requirements update.
- **2026-06-07** `fbe9254` feat: stutter-assistance feature, smarter
  grammar, UI polish & fixes.
- **2026-06-07** `bb4afd0` docs: update README.
- **2026-06-07** `f0ca322` chore: add project files.
- **2026-06-06** `8a4498c` Replace project with new content.
- **2026-06-06** `59a4215` docs: update README.
- **2026-06-05** `9361294`, `25af484`, `32624a1`, `d50ad22`, `a5317b7`,
  `31646c3` — bootstrap: initial commit, README, `.gitignore`,
  `requirements.txt`. → `DECISION_LOG.md` 2026-06-05.

---

*This changelog was generated in one backfilling pass on 2026-08-08 from
`git log`. Going forward, per Practice.md §14, new entries should be added
here at commit time, one line per change, pointing to a `DECISION_LOG.md`
entry whenever the change represents a non-trivial decision, result, bug,
or finding rather than routine maintenance.*
