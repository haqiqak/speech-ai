# Architecture Go/No-Go — Step 3: formal assessment

Per the 4-step plan agreed 2026-08-27 (`DECISION_LOG.md` 2026-08-27-E):
give the current rule/gate-based architecture one final, serious
evidence-gathering opportunity, then assess it against explicit
criteria, then make a genuine three-way decision (Step 4) — instead of
an open-ended sequence of "Phase 11D/E/F" patches. This document is
Step 3: the synthesis. It does not itself decide anything; Step 4,
immediately following, makes the call and asks for the user's
ratification before being treated as final.

## Process note, disclosed honestly before the assessment starts

The agreed plan called for "a formal architecture assessment against
pre-registered criteria." The **8 criteria themselves** were named
explicitly at the time (CLEAN rate, defective-output rate, dangerous
semantic reversals, refusal/escalation rate, dense-profile performance,
generalization to unseen material, consistency/reproducibility,
computational cost) and have been used, unchanged, to steer what
evidence got gathered at every step since. What was **not** actually
written down anywhere as a concrete artifact, despite the intention
being agreed, is a numeric pass/fail threshold per criterion (e.g. "if
fresh-corpus CLEAN rate is below X%, that's Option C"). This is a real
gap against the original refinement both parties agreed to, named here
rather than silently patched over. The practical consequence: the
reasoning below is a qualitative synthesis across all 8 criteria's
actual evidence, not a threshold checklist — which is more exposed to
hindsight bias than a true pre-registered test would have been. The
mitigations actually in place: (1) every number cited below was
recorded in `VALIDATION.md`/`DECISION_LOG.md` *before* this synthesis
was written, so the evidence itself isn't being reshaped after the
fact; (2) the fresh-corpus check (§54) was deliberately run and
recorded as its own standalone finding, with its own interpretation,
before this document was started, for the same reason.

## 1. CLEAN rate

| Phase | Corpus | CLEAN rate |
|---|---|---|
| 10 (original) | R10 (frozen) | 62/238 (26.1%) |
| 11 | R10 (frozen) | 75/230 (32.6%) |
| 11B | R10 (frozen) | 71/225 (31.6%) |
| 11C | R10 (frozen) | 66/194 (34.0%) |
| Architecture Gate Step 1 | R10 (frozen) | 68/218 (31.2%) |
| Step 3 generalization check | fresh, unseen | **6/28 (21.4%)** |

On the corpus this architecture has been iteratively tuned against, six
phases of real, individually-verified fixes moved CLEAN rate from 26.1%
to a range that has oscillated 31-34% since Phase 11 — i.e. gains
mostly happened once (Phase 11), then plateaued within a ~3-point band
despite three more substantial phases of work (11B, 11C, Architecture
Gate 1). On a corpus this architecture has never seen, CLEAN rate is
21.4% — below even Phase 10's *original*, pre-any-fix number, on
material that should benefit from every fix made since. This is the
single most important number in this assessment: **the fixes did not
transfer**, or transferred only partially.

## 2. Defective-output rate

Direct complement of (1) among `reformulated`-status runs: R10-corpus
current state 150/218 (68.8%) defective; fresh-corpus 22/28 (78.6%)
defective. Same story from the other side — a system that is, at best,
in the current state, right less than a third of the time it decides to
rewrite something, and right about a fifth of the time on fresh input.

## 3. Dangerous semantic reversals specifically

| Phase | FACTUAL_OR_LOGICAL_REVERSAL share of defects |
|---|---|
| 10 (original) | 20/176 (11.4%) |
| 11 | 5/65 (7.7%) |
| 11B | 5/72-80 (~6-7%) |
| 11C | not separately itemized in that phase's report (WRONG_WORD_OR_SENSE 46/70 was; the remaining 24 were not broken out by type) |
| Architecture Gate Step 1 | **not measured** — no defect-type breakdown was recorded for this phase's 105 DEFECTIVE population |
| Step 3 generalization check | 1/22 (4.5%) |

**[LIMITATION, disclosed rather than papered over]** This is the
criterion the user specifically called out as needing separate
attention ("dangerous semantic reversals specifically"), and it is the
one with the thinnest recent evidence — Architecture Gate Step 1 never
re-instrumented this breakdown, so there is no reversal-rate figure at
all for the current production architecture's largest single change.
What evidence does exist is consistent across four independent
measurements (Phase 10, 11, 11B, and now the fresh corpus): this defect
class has held in a **~5-11% band and never been the dominant class**,
including on genuinely unseen material. Read as: reversals are a real,
persistent minority risk, not eliminated by any phase's fixes, but also
not the primary driver of the CLEAN-rate problem — that role belongs to
WRONG_WORD_OR_SENSE throughout, at every measurement.

## 4. Refusal / escalation rate

| Phase | Refusal rate |
|---|---|
| 10 (original) | 62/398 (15.6%) |
| 11 | 70/398 (17.6%) |
| 11C | 106/398 (26.6%) (Phase 11C's own report cites the pre-phase baseline as 75/398, 18.8% — a ~5-point discrepancy against Phase 11's own self-reported 70/398, itself a small data point for criterion 7) |
| Architecture Gate Step 1 | 82/398 (20.6%) — fell from 11C's 106 as the new generation mechanism recovered coverage on previously-refused dense cases |
| Step 3 generalization check | 8/36 (22.2%) |

Refusal rate roughly tracks the same shape as CLEAN rate's plateau:
rose substantially through 11C as safety gates accumulated, partially
recovered in Architecture Gate 1 as the phoneme-constrained generator
restored coverage, and sits at a similar ~20-27% band across the last
three R10-corpus measurements. The fresh corpus's 22.2% falls squarely
inside that same band — refusal behavior, unlike CLEAN rate, appears to
generalize reasonably well. The system is about as willing to refuse
unseen material as familiar material; it is specifically the *quality
of what it does attempt* that drops on unseen material.

## 5. Performance under dense profiles

This is the cleanest, most reproducible finding in the entire project.
**Phase 10's original stress test, on the frozen corpus, before any
fix**: `multi_word` profiles (3-4 flagged words at once) scored **0%
CLEAN (0/13)** — already flagged then as "a near-total failure mode,"
the single cleanest predictor in that dataset. **The Step 3 fresh-corpus
check, on a corpus this project has never touched, after six phases of
fixes**: `dense_mixed` profiles (2 declared words + a declared sound
pattern) scored **0/10 CLEAN** — the identical failure mode, at the
identical rate, on completely different sentences, after a large
amount of engineering work explicitly aimed at parts of this exact
problem (Architecture Gate Step 1's whole purpose was dense/multi-sound
profile coverage). Two independent corpora, separated by this project's
entire optimization history, agree exactly: **dense/multi-constraint
input is not something six phases of rule-and-gate engineering have
measurably improved.**

## 6. Generalization to unseen material

Covered fully in `VALIDATION.md` §54 / `DECISION_LOG.md`
2026-08-27/28-G. Summary: 21.4% CLEAN on fresh material vs. 31.2%
(Architecture Gate 1) to 34.0% (11C, this architecture's best-ever
R10-corpus figure) on the frozen corpus — a ~10-13 point gap, well
outside the independently-established ~1-2 point noise band, and
concentrated exactly on dense profiles (criterion 5) and
WRONG_WORD_OR_SENSE (criterion 1/2's dominant defect throughout this
project's history). The straightforward reading: a meaningful share of
the R10-corpus CLEAN-rate gains measured across Phases 11/11B/11C/
Architecture-Gate-1 reflect the architecture (its blocklists,
gates, and specific bad-pair rules) being shaped by repeated exposure to
that corpus's own failures, not a generalizable improvement in how well
it handles constrained rewriting in general.

## 7. Consistency / reproducibility

Independently established and re-confirmed three separate times
(Phase 11B, 11C, Architecture Gate Step 1) that re-running the
*identical* 398-run harvest with *no code change* flips a small number
of individual outcomes (~1-2 points of CLEAN rate), traced every single
time to live Datamuse network-call and T5 sampling nondeterminism, not
code bugs — each phase's regressions were individually checked against
the actual code diff and confirmed unrelated. The refusal-rate
bookkeeping discrepancy noted under criterion 4 (Phase 11's self-
reported 70/398 vs. Phase 11C's citation of 75/398 for what should be
the same state) is a further, smaller data point in the same direction.
Net assessment: the system's *quality* is not perfectly reproducible
run-to-run at the ~1-2 point level, which is small relative to the
~10-13 point generalization gap in criterion 6 — reproducibility noise
does not explain the fresh-corpus result.

## 8. Computational cost

Measured directly for the first time in Architecture Gate Step 1
(`VALIDATION.md` §52): phoneme-constrained decoding costs +28% latency
on the hardest targeted cases, +8% on the full escalation-invoked
population, +3% on total harvest wall time. The Step 3 fresh-corpus
check's mean per-run latency (7.44s) is consistent with that same
escalation-tier figure — no fresh-material cost anomaly. Cost is
bounded, understood, and concentrates predictably on exactly the
hardest cases the mechanism targets. This criterion does not argue
against the current architecture on its own; the constraint is quality,
not resource cost.

## Synthesis

Two internally consistent stories run through all 8 criteria:

**Where six phases of engineering clearly worked:** refusal behavior is
a real, working safety backstop (criterion 4) that generalizes
reasonably well (criterion 6's refusal-rate comparison); computational
cost is bounded and well-understood (criterion 8); dangerous reversals,
while never eliminated, have held in a persistent-but-minority ~5-11%
band rather than growing (criterion 3); and Step 2 already produced a
mechanistically specific, actionable finding (71% of WRONG_WORD_OR_SENSE
defects are ranking failures with a demonstrated cause in
`combined_score()`'s frequency term) that no phase before Step 2 had.

**Where six phases of engineering demonstrably did not work:** CLEAN
rate has plateaued in a 3-point band since Phase 11 despite three more
full phases of individually-verified, real fixes (criterion 1); dense/
multi-constraint profiles score 0% CLEAN on both the original frozen
corpus (before any fix) and a completely fresh corpus (after every fix)
— the exact same failure mode, unmoved, six phases apart (criterion 5);
and CLEAN rate on genuinely unseen material sits at 21.4%, ~10-13 points
below what the frozen corpus shows, a gap large enough to indicate that
a real share of the corpus-measured gains were fitting to that corpus,
not general improvement (criterion 6). Reproducibility noise (criterion
7) is measured and too small to explain this gap.

The dominant remaining defect class (WRONG_WORD_OR_SENSE) has been the
largest class at every single measurement across this project's entire
history — Phase 10 through the fresh-corpus check — and Step 2 already
showed it is structurally a **ranking/selection problem**: the correct
candidate is usually already generated, `combined_score()`'s fixed
90/10 semantic/frequency blend just doesn't reliably pick it. Every
mechanism added across Phases 11/11B/11C/Architecture-Gate-1 operates
either on generation (what candidates get produced) or on rejection
(a binary gate: does this candidate get thrown out) — none of them
touch *ranking among survivors*, which is exactly where Step 2 located
the dominant problem. This is a structural gap in what kind of fix this
architecture is capable of expressing, not a gap that has been tried
and failed — it has simply never been the lever any phase pulled.

This synthesis feeds directly into Step 4's decision, presented
separately as its own document/section so the recommendation and its
ratification are visibly distinct from the evidence above.
