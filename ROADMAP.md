# ROADMAP.md — Forward-looking priority list

Per Practice.md §15: one list, priority order, each item linked to the
specific finding or gap that justifies it. Proposed-but-unvalidated
directions are labeled as exactly that, not written with the confidence
of an item a completed finding already justifies. Per §0.2 of Practice.md,
**this document does not authorize starting any of these** — it is a
prioritized list produced by §19 steps 1–8; step 9 (actually doing the
work) is a separate, deliberate decision outside the scope of this pass.

---

## ARCHITECTURE FREEZE IN EFFECT (ratified 2026-08-28)

**The reformulation architecture (the rule/gate/candidate-generation
pipeline in `reformulate.py`, `rephrase.py`, `semantic.py`,
`combined_score()`'s ranking formula, and every gate accumulated across
Phases 11/11B/11C and Architecture Gate Step 1) is frozen as the
maintained/shipped baseline, per the user's explicit ratification of
the Step 4 recommendation.** Full record: `VALIDATION.md` §56,
`DECISION_LOG.md` 2026-08-28-I, `eval/step3_architecture_assessment.md`,
`eval/step4_recommendation.md`, git tag `architecture-freeze-v1`.

**This is not project abandonment.** It means: no further rule, gate,
threshold, ranking-weight, or blocklist changes in response to
individually-observed failures (the "Phase 11D/E/F" pattern this
project's Architecture Go/No-Go arc was explicitly started to stop);
no learned-component work (reranker, WSD model, or otherwise) on the
current evidence base; routine maintenance (dependency updates,
non-behavioral bug fixes) continues normally. The frozen architecture
is now the **reference baseline** any future, fundamentally different
approach would need to beat — not a dead end.

**Reopening optimization requires new evidence, specifically either:**
(1) a substantially larger, independently collected labeled dataset —
not built the same way (same small Claude-judged corpus, same limited
per-defect-class sample sizes) as the evidence this freeze rests on; or
(2) a genuinely different modeling approach, evaluated against this
project's own generalization bar (per the Phase 9B/9C precedent that
informed this freeze) before being trusted over the frozen baseline.
Everything below this banner reflects roadmap items identified *before*
the freeze and is retained as historical record / candidate material
for a future re-opening, not active work.

**Added context, 2026-08-30 (no change to the two conditions above):**
this arc's own shape — hand-engineered rules plateauing while the
dominant defect is a ranking problem — is a small-scale instance of the
pattern Rich Sutton's "The Bitter Lesson" describes; see `VALIDATION.md`
§57 / `DECISION_LOG.md` 2026-08-30-A for the connection and its own
caveat (the essay's argument presupposes sufficient data/compute are
actually available to the general method, which is precisely what
condition (1) above requires before it applies here).

**Stage LR opened, 2026-08-30 (condition (2)'s container, not yet
condition (2) met):** `LEARNED_REFORMULATION_RESEARCH.md` charters a
learned-reformulation research direction ("LR") on its own branch
(`stage-lr`), kept off `main` until it clears the freeze's held-out
generalization bar. `main` remains the frozen, shipped implementation
partners should build against — see `DECISION_LOG.md` 2026-08-30-B/C.

---

## Highest priority — not a research question, an exposure

### R0. Remediate committed credential/user data
**Linked finding:** `DECISION_LOG.md` 2026-06-13-A — `users/default.json`
and `users/bobcat.json`, including SHA-256 password hashes, are committed
to git history despite documentation claiming otherwise.
**Why highest priority:** This is not gated on the research objective at
all — it's a live exposure of real (if weakly-hashed) credential material
in what the repository presents as a public project. Practice.md's
evidence-driven prioritization logic (§15) is about *research* priorities;
this item sits outside that logic entirely and should not wait for a
roadmap-blind reassessment to surface it.
**Status update (Stage 4A refinement, 2026-08-16):** Partially addressed
going forward, not remediated retroactively — see `DECISION_LOG.md`
2026-08-16-A. The multi-user auth system was removed entirely (`auth.py`,
`user_store.py` deleted); no password is hashed or stored anywhere anymore,
and the current `users/default.json` was rewritten to a schema with no
`password_hash` field. `users/bobcat.json` (a second test account, no
longer meaningful under a single-profile design) was deleted outright. What
this does **not** do: purge the old password hashes from git *history* —
those commits still exist and are still fetchable by anyone with repo
access. Rewriting published history (force-push, coordination with anyone
else who may have cloned) is a separate, deliberate action, not taken here
without explicit authorization. **Status: exposure surface reduced to zero
for new activity; historical exposure unchanged — still open.**

---

## High priority — directly reopens an unresolved, same-day contradiction

### R1. Resolve the MIN_SEMANTIC threshold contradiction
**Linked finding:** `DECISION_LOG.md` 2026-06-08-A and 2026-06-08-B. On
the same day, one change raised `MIN_SEMANTIC` from 0.72 to 0.85 (argued
by example, not by a dataset-level measurement), and a separate diagnostic
script recommended moving it back down to ~0.80, additionally suggesting
per-POS thresholds might help — and that recommendation was explicitly
left unapplied.
**What this roadmap item actually is:** Re-run `tests/threshold_sweep.py`
(or its successor) against the *current* code, pre-register (§8) what
"better" means for this comparison (meaning-preservation rate at matched
or improved acceptance rate — reported separately, never blended, per
§10), and either confirm 0.85 is in fact the better-supported value or
act on the sweep's original recommendation with the reasoning recorded.
**Labeled as:** Directly evidence-linked (not a fresh hypothesis) — the
evidence already exists in git history, it was simply never resolved or
written to a durable record.

---

## High priority — the proxy-metric gap named by §12

### R2. Validate the difficulty formula(s) against real disfluency data
**Linked finding:** `VALIDATION.md` §2 — both difficulty formulas
(`phonetic.word_difficulty()` and `profiling/profile.py`'s weighted
variant) use hand-picked, unfitted coefficients, and the profile's own
AUC evaluation (`eval/profile_eval.py`) checks against a rule-based
disfluency labeler rather than an independent ground truth.
**What this roadmap item actually is:** Once the Audio Module produces
real paired (utterance, disfluency) data per speaker — per Practice.md
§7's exact framing of this same gap — validate the formula weights
against it, and separately check whether the literature (§7) suggests
syllable structure, word length, semantic load, or sentence position
predict difficulty comparably to or better than onset alone.
**Labeled as:** **Future work**, explicitly blocked on real data from the
Audio Module — not actionable today, but should not silently drop off
the list once that data exists.
**Update (Stage 5, 2026-08-16):** The "does the literature suggest other
factors" half of this item is now answered, independent of the
still-blocked weight-fitting half — `REFORMULATION_RESEARCH.md` §2.1 cites
Brown's four factors (word-initial phoneme, grammatical function, sentence
position, word length) plus stress and consonant-cluster effects from the
stuttering-loci literature. Two of these (sentence position, stress) are
missing from both current formulas entirely, and the stress data (CMU
stress digits) is already present in our own phone data and currently
discarded, not unavailable — see `REFORMULATION_RESEARCH.md` §22 item 4
for the proposed cheap, pre-fitting experiment (add the terms, check
whether rankings change) that doesn't require waiting on R2's data
dependency.

### R3. Run the literature pass called for in §7 — **DONE, 2026-08-15**
**Linked finding:** `VALIDATION.md` §5 — this review did not perform it.
**What this roadmap item actually is:** A dedicated literature review
(speech-language pathology, lexical-substitution/paraphrase NLP,
stutter-therapy/AAC research, readability/simplification literature),
written as its own document per §7's format, addressing specifically
whether fixed onset-matching is the right primary signal.
**Status:** Completed — see `RESEARCH.md` and `DECISION_LOG.md` 2026-08-15-B.
Headline answer to "is fixed onset-matching the right primary signal":
**partially** — onset phoneme class is a real, clinically-grounded factor,
but the speech-motor-control literature indicates articulatory difficulty is
richer than onset-cluster-length alone, and word frequency (used as a
secondary signal in both current difficulty formulas) is a better-evidenced
proxy for *lexical access* ease than for *articulatory/motor* ease — the
mechanism most relevant to stuttering specifically. See `RESEARCH.md` §1.2
and §5.4 for the full argument and citations. This is a literature-grounded
**reinforcement** of `VALIDATION.md`'s existing "unfitted weights" limitation,
not a new, separate problem.
**Labeled as:** Directly named by Practice.md itself as a concrete,
overdue gap — closed by this pass, not a hypothesis this review is
proposing.

### R4. Confirm or run the human-judgment study (`eval/study/`)
**Linked finding:** `VALIDATION.md` §1/§2 — the one piece of evaluation
machinery aimed at the real outcome (not a cheap proxy) has no confirmed
run in the repository.
**What this roadmap item actually is:** Either locate the run record (if
one exists outside this repo) and bring it into `VALIDATION.md`, or run
the counterbalanced study per its existing scaffolding, pre-registered
per §8.
**Labeled as:** Gap identified by this review, not yet a hypothesis about
outcome — the question here is "has this been done," not "would this
help."
**Update (2026-08-17) — infrastructure verified working; the real blocker
identified, and it isn't a bug.** `VALIDATION.md` §7: `counterbalance.py`
and `stats.py` were actually run against synthetic data (not just read)
and work correctly — balanced condition assignment, a real Friedman-test
result. Nothing needed fixing. Three real, non-code blockers found
instead: `collect.py` is a CSV schema, not an actual collection
instrument; the condition labels (`original`/`generic`/`personal`) are
scoped to the pre-`reformulate.py` `rewrite/`-era comparison, not the
current three-pipeline landscape; and the schema's headline metric
(`disfluency_count`) requires spoken-performance data this text-only
module cannot capture itself, since audio is out of scope
(`out_of_scope/`). A realistic pilot within this repo's actual scope
would use only `ease_likert_1_7`/`forced_choice_preference` (no audio
needed) against a deliberately-chosen current comparison, reusing
`counterbalance.py`/`stats.py` unmodified. Still blocked on recruiting
actual participants — that's a scope decision for whoever can realistically
do it, not something this pass could resolve.
**Update (2026-08-17) — the pilot is built, verified, and ready to run;
no longer blocked on infrastructure, only on real participants
completing it.** `VALIDATION.md` §8: a scoped, honest pilot design (4
participants x 20 pairs = 80 ratings, `reformulate.py` only — the legacy
pipelines were already compared quantitatively in §6 and are out of scope
here), a deliberately non-random 20-pair selection from a 69-case
eligible pool (`eval/pilot_select_pairs.py`) that specifically includes
cases already suspected to be qualitatively weak despite passing
automated gates, a minimal Streamlit collection instrument
(`eval/pilot_app.py`) with per-participant order/position
counterbalancing, and an analysis script
(`eval/pilot_analyze.py`) that merges human ratings against each pair's
existing automated metrics to flag proxy-vs-human disagreement directly —
the specific, actionable signal this pilot exists to produce. The full
workflow was driven end-to-end with synthetic responses via `AppTest`
(`tests/pilot_app_test.py`) before any real participant touched it, per
this item's own "confirm, don't just build" discipline: exactly 20 rows
per participant, zero cross-contamination, counterbalancing verified to
actually vary, and the resulting data confirmed analyzable. **Not yet
done:** the actual 4x20 data collection with real people — that's the
only remaining step, and it's not one this pass could do on its own.
**Update (2026-08-17, same day) — pilot redesigned (v2) per direct user
review before any real data collection started.** v1's pairs were too
uniform in length/register; v2 mixes 10 short single sentences, 3
long/complex sentences, 6 multi-sentence passages, and 1 real public-
domain speech paragraph (Gettysburg Address, sourced and verified public
domain), plus a new "input sentence itself was ungrammatical" diagnostic
option and an optional free-text comment field. Also found and disclosed
a genuine T5-escalation non-determinism (identical code/input producing
different `reformulate.py` outcomes across separate process launches —
`VALIDATION.md` §8.4) while verifying candidate pairs; worked around via
per-item process isolation and multi-trial stability confirmation, not
fixed in `rephrase.py` (out of scope here). Full record:
`DECISION_LOG.md` 2026-08-17-D.
**Update (2026-08-17, same day) — v2 actually run (P1, real data); found
a real UI labeling bug from that use; pilot rebuilt again as v3.** P1
completed all 20 v2 pairs (`VALIDATION.md` §8.7) — the project's first
real human-judgment data. That real use surfaced a genuine bug: v2's two
text boxes were labeled "Sentence 1"/"Sentence 2" with a separate
caption saying which was Original vs. Reformulated; since display order
is randomized per pair, several of P1's comments describe the
reformulated text as if it were the input. Per direct user review: pilot
rebuilt as v3 — single participant, 30 short/natural sentences only (long
sentences tested worse — too little signal per item), Original/
Reformulated now labeled directly on each box, full profile-traceability
metadata per item, and an explicit, now-locked-in methodology rule:
human ratings cover meaning/naturalness/ease/preference only, never
whether the declared difficulty was actually resolved (that's automated,
reported separately). A second, unrelated bug was found and fixed while
building v3's verification — an `AppTest` test-harness fragility across
many sequential form-submit cycles, not a bug in the pilot app itself.
Full record: `DECISION_LOG.md` 2026-08-17-E/F; `VALIDATION.md` §9.

---

## Medium priority — architectural duplication, evidence-constrained framing

### R5. Reconcile the two parallel rewrite paths
**Linked finding:** `DOCS.md` — `grammar.py::SentenceRewriter` (the "hard"
phoneme-onset-gated path) and `rewrite/` (the "soft"
`similarity - λ·difficulty + μ·frequency` path) independently
re-implement protected-word detection, POS-filtering, and inflection.
**What this roadmap item actually is:** This is explicitly **not** a
recommendation to delete either path — per Practice.md §3, neither
"simpler/older" nor "more sophisticated/newer" gets automatic priority.
The actual next step is R6 below (an ablation comparing the two paths on
the same objective), and only once that comparison exists does a
consolidation decision have evidence behind it. Filed here as the
maintenance-risk observation that motivates running that comparison sooner
rather than later, not as a pre-decided outcome.
**Update from the literature pass (`RESEARCH.md` §6, 2026-08-15):** the
literature's actual argument for keeping multiple pipeline components is
*complementary failure modes* (a generator paired with an independent
verifier). Pipeline A and B don't fit that pattern — they attack the same
sub-problem with the same candidate source and a similarly-shaped score,
differing mainly in binary-vs-continuous difficulty gating. This is
evidence *for* running the R6 ablation sooner rather than later (there's
now a literature-grounded reason to expect consolidation is the right
outcome), but it is still **not** itself the ablation — `RESEARCH.md`
explicitly declines to make this a decision, per the Stage 3 restriction
against redesigning based on research alone.
**Labeled as:** Observation (duplication is real and confirmed by reading
both code paths), now with literature-grounded reasoning behind it, driving
a **future** evidence-gathering step, not an implementation decision.
**Update (2026-08-16) — resolved, not by ablation:** `reformulate.py`
(`DECISION_LOG.md` 2026-08-16-E) supersedes both paths with a single new
engine per the Stage 5B blueprint, rather than picking a winner between
them via the R6 ablation below. `grammar.py::SentenceRewriter` and
`rewrite/rewriter.py::DifficultyAwareRewriter` remain in the repo,
untouched, but `app.py` no longer calls either — closing the duplication
concern this item named, without needing the ablation to have run first.

### R6. Ablation: does the phoneme-onset gate change accepted candidates, and does Pipeline A or B produce better output?
**Linked finding:** Practice.md §11, applied directly — named as a
Speech-AI-shaped candidate ablation once a benchmark exists. Scope widened
slightly during the Stage 3 research pass to explicitly include the A-vs-B
comparison R5 is blocked on, since both are the same class of question
(does this specific gating/scoring choice change what gets accepted).
**Labeled as:** Future work, blocked on R1–R4 producing a usable benchmark
first.
**Update (Stage 5, 2026-08-16):** `REFORMULATION_RESEARCH.md` §22 lists this
ablation as the literal first item to implement, ahead of every other
Stage 5 recommendation — everything else (NLI signal, difficulty-formula
terms, the escalation path) is easier to evaluate correctly once this
ablation's answer is known, not before.
**Update (Stage 6, 2026-08-16) — superseded by an actual three-way
comparison, not the originally-planned two-way ablation.** `VALIDATION.md`
§6 ran `reformulate.py` against both `SentenceRewriter` and
`DifficultyAwareRewriter` on an 18-case corpus with uniform metrics —
`reformulate.py` shows higher meaning preservation (0.979 vs. 0.938/0.929)
and smaller edits (0.068 vs. 0.147/0.143) but a lower reformulation rate
(0.556 vs. 0.889/0.833), entirely explained by a 0/4 escalation-path
success rate (root-caused into two separate findings — a fixable
case-sensitivity bug in `rephrase.py::_bad_words_ids()`, and a deeper
model-choice mismatch between T5's meaning-preserving paraphrase
objective and this task's phoneme-avoidance requirement). This item's
original question (does the phoneme-onset gate change what's accepted) is
now subsumed by the broader comparison — closing this as originally
scoped; see `VALIDATION.md` §6 for the actual numbers rather than
restating them here.

### R7. Ablation: is the frequency term in the ranking formula doing real work?
**Linked finding:** Practice.md §11, same source as R6.
**Labeled as:** Future work, same blocking condition as R6.

### R8. Add a second, orthogonal semantic-preservation signal (NLI/bidirectional entailment) alongside SBERT
**Linked finding:** `RESEARCH.md` §2.D/§5.3 — SBERT-family sentence
embeddings have a documented, specific blind spot for negation/antonym
drift, driven by high lexical overlap suppressing the similarity score's
sensitivity to the one word that changed. Nothing in the current pipeline
catches this failure mode.
**What this roadmap item actually is:** Prototype an NLI-based
bidirectional-entailment check as an *additional* gate alongside (not
replacing) the existing SBERT threshold, and measure whether it changes
acceptance decisions on cases the current gate gets wrong.
**Labeled as:** Literature-grounded future work — the gap is a documented
finding, whether closing it changes real outcomes for our candidate
distribution (which skews toward true synonyms, not antonyms, by
construction of the WordNet/Datamuse retrieval step) is untested.
**Update (Stage 5, 2026-08-16):** No longer just "an NLI model exists" —
`REFORMULATION_RESEARCH.md` §9 names specific, confirmed-CPU-feasible
models (`cross-encoder/nli-deberta-v3-xsmall`/`-small`, `EttinX-nli-s`),
comparable in size/cost to the SBERT model already running in this repo.
Sequenced third in `REFORMULATION_RESEARCH.md` §22's implementation order
(after the R6 ablation and the naturalness-of-intervention metric, R11).

### R9. Prototype a feedback loop from accept/reject decisions into the difficulty profile
**Linked finding:** `RESEARCH.md` §2.F/§5.5 — the closest known prior system
(`Fluent`, ASSETS 2021) uses an active-learning loop where user accept/
reject signal on suggestions directly trains the difficulty classifier.
Our `SpeakerDifficultyProfile.update()` already accepts arbitrary events but
nothing in `app.py`/`rewrite/` wires the UI's accept/reject clicks back into
it — the profile currently only updates from disfluency *events* (which, in
this narrowed repo, come from self-report, not observed data).
**What this roadmap item actually is:** Wire the existing accept/reject UI
signal into `profile.update()` as a new event type, and evaluate whether it
measurably improves suggestion quality over a session.
**Labeled as:** Directly transferable idea from the closest comparable prior
system, not yet implemented or validated in this codebase.
**Update (Stage 4A, 2026-08-15):** A second, more direct feedback surface
now exists alongside this one: `difficulty_profile.py`'s `DifficultyEntry`
already carries an unused, reserved `source="system_observed"` value and an
empty, forward-compatible `meta` dict per entry — see `DECISION_LOG.md`
2026-08-15-C and `PROBLEM_FORMULATION.md` §8/§9. Wiring accept/reject into
*this* profile (not just `SpeakerDifficultyProfile.update()`) is now also a
live option, and reconciling the two profiles (R12 below) is a prerequisite
either way.
**Update (Stage 5, 2026-08-16):** `REFORMULATION_RESEARCH.md` §11 finds the
current field trend for exactly this kind of small-data, single-user
adaptation is a **contextual-bandit** framing (arm = which onset/word gets
flagged risky, reward = accept/reject) — lightweight, CPU-trivial, no
neural network required at our data scale. Explicitly flagged there as an
*algorithm* worth borrowing, not a system to adopt wholesale (the cited
papers target much larger-scale systems). Still sequenced after the core
substitution/escalation pipeline (R6/R10) — there must be something to
accept or reject before this is buildable.
**Update (2026-08-16) — prerequisite now exists, wiring still doesn't.**
`app.py`'s new review UI has a real per-change Keep/revert signal
(`DECISION_LOG.md` 2026-08-16-E) — the "something to accept or reject"
this item was blocked on. Nothing yet feeds that signal back into
`difficulty_profile.py` or a bandit-style weighting; this item stays open.
**Update (2026-08-17) — wired, recording only, DONE at prototype scope.**
Each Keep/Revert toggle now calls `reformulate.feedback_targets(change,
profile)` (new, read-only, additive — attributes a substitution-sourced
change to the declared word/sound entry that triggered it; returns `[]`
for restructuring, since a whole-sentence rewrite can't be cleanly
attributed to one entry) and records the vote via
`difficulty_profile.record_feedback()`/`undo_feedback()` into that
entry's existing, reserved `meta` field as plain kept/reverted counters
— re-toggling flips the vote net rather than accumulating raw clicks.
Persists via the existing `profile.save()` path; a small badge
(`✓2 ↺1`) surfaces it in the difficulty-profile panel so the data isn't
silently invisible. **This is the "prototype" the field's contextual-
bandit framing (§11, above) called for — recording the reward signal,
not yet acting on it.** Nothing in `reformulate.py`'s candidate ranking
reads this field; using it to influence future substitution choices is
separate, further work, deliberately not done here (this session's own
discipline: don't change ranking without evaluation evidence for it —
see `VALIDATION.md` §6.9's conclusion on this exact point). 17 new tests
(`difficulty_profile_test.FeedbackTest`, `reformulate_test.FeedbackTargetsTest`,
plus an `app_test.py` scenario exercising the full toggle → persist →
reload → re-toggle round trip through the real UI) — full existing suite
(78 tests total) and `tests/smoke.py` both confirm the reformulation
engine itself is byte-for-byte unaffected. Full record:
`DECISION_LOG.md` 2026-08-17-A.

### R10. Investigate a restructuring/escalation path for when substitution has no valid candidate
**Linked finding:** `RESEARCH.md` §5.6/§7 — the single largest capability
gap this pass surfaced. Neither pipeline can restructure a clause; both
report "no valid synonym" and leave the word untouched when substitution
fails, even though the user's own original problem statement named
"syntactic restructuring... clause restructuring... sentence-level
paraphrasing" as in-scope capabilities.
**What this roadmap item actually is:** Investigate `rephrase.py`'s
existing constrained-T5 layer as a fallback specifically for this failure
case (escalate to generation only when substitution provably fails),
following the generate-then-verify pattern `RESEARCH.md` §2.E/§6 identifies
as the field's preferred architecture for this kind of problem, rather than
running rephrase as an independent, always-optional toggle.
**Labeled as:** The clearest architecture recommendation to come out of the
research pass (`RESEARCH.md` §8) — still a recommendation, not a decision;
needs Stage 4 to actually evaluate it against alternatives.
**Update (Stage 5, 2026-08-16):** Independently re-confirmed as the right
direction by a second, more detailed research pass —
`REFORMULATION_RESEARCH.md` §20 makes this the "escalation" stage of the
recommended hybrid architecture, and §17's constructed failure modes show
it's the *only* one of the ten constructed test cases that the recommended
architecture solves structurally (the others are either already handled or
explicitly named as still-unsolved). Deliberately sequenced **after**
R6/R8/R11/R2's position-stress terms in `REFORMULATION_RESEARCH.md` §22–23
— building the escalation path before the substitution path's own quality
is measured would conflate two different sources of improvement.
A concrete architecture-level alternative was researched and explicitly
**rejected**: a learned minimal-edit tagger (GECToR/FELIX-style) instead of
this escalation approach. Not rejected for hardware reasons — rejected
because no paired training data (difficult-input → easier-output) exists
for this task, and synthesizing it from our own rule-based outputs would
just teach a model to imitate rules we already have (`REFORMULATION_RESEARCH.md`
§6). Filed as future work only if real speaker-reformulation-pair data
ever exists (same blocking condition as R2).
**Update (2026-08-16) — DONE.** Built in `reformulate.py::_try_escalation`
(`DECISION_LOG.md` 2026-08-16-E): triggered by the count-threshold/
degenerate-fraction pre-check or by any substitution failure within a
sentence (all-or-nothing, never a partial patchwork), using `rephrase.py`
unchanged, generate-then-verify against the original sentence.

### R11. Design a "naturalness of intervention" metric
**Linked finding:** `RESEARCH.md` §4 — none of our current metrics, and
none found in the literature search, cleanly distinguish "this edit was
necessary" from "this edit was correct." `substitution_rate` (already
computed) is the closest existing proxy and conflates the two.
**Labeled as:** Open evaluation-methodology gap, future work — no
literature answer found, flagged as a genuine open question in
`RESEARCH.md` §9 rather than assigned a false solution.
**Update (Stage 5, 2026-08-16) — no longer a fully open question:**
`REFORMULATION_RESEARCH.md` §10/§17 finds a concrete, established
technique this pass's search didn't surface before: revision-quality
literature uses **Levenshtein/character-edit-distance-based penalties**
specifically "to penalize unnecessary changes" while preserving intent.
This doesn't invent a *correctness* signal (still needs the semantic/
difficulty gates), but it does give a literature-grounded, implementable
answer to the *how-much-changed* half of the metric. Sequenced second in
`REFORMULATION_RESEARCH.md` §22's implementation order — needed as a
shared before/after baseline before R6's ablation or R8's NLI addition can
be meaningfully compared.
**Update (2026-08-16) — DONE.** Built as `naturalness.py`
(`edit_ratio`/`changed_word_count`, word-level `difflib.SequenceMatcher`)
and wired into `reformulate.py`'s metrics output as
`naturalness_edit_ratio`, reported separately from meaning-preservation
and difficulty-reduction, never blended into one score (Practice.md §10).

---

## New from Stage 4A (2026-08-15) — the profile foundation and what it exposes

### R12. Reconcile the new user-declared `DifficultyProfile` with the old learned `SpeakerDifficultyProfile`
**Linked finding:** `PROBLEM_FORMULATION.md` §5/§9 and `DECISION_LOG.md`
2026-08-15-C. Stage 4A deliberately built the new, structured,
user-declared profile (`difficulty_profile.py`) as a *separate* thing from
the existing, learned, EWMA-scored `SpeakerDifficultyProfile`
(`profiling/profile.py`, unchanged, still driving `rewrite/`) — a direct,
correct consequence of not touching the reformulation engine this stage,
not a design endorsement of leaving them separate forever.
**What this roadmap item actually is:** Before or as part of the actual
reformulation redesign, decide how declared difficulty (sounds/words/
phrases, from Stage 4A) and learned difficulty (continuous onset-risk, from
the existing profile) combine into whatever single signal a rebuilt
reformulation engine consumes — per `RESEARCH.md` §8's recommendation to
collapse binary/continuous difficulty signals into one, this is the same
kind of consolidation question, now with a second data source added to it.
**Labeled as:** Directly evidence-linked (not a fresh hypothesis) — the
duplication is a stated, deliberate, and named limitation of Stage 4A's own
design, not a newly-discovered problem.
**Update (Stage 4A refinement, 2026-08-16):** A third difficulty signal now
exists alongside the two named above — word-specific `problem_phones`
(`DifficultyEntry`, per-word sound patterns). This doesn't add a new
open question, it sharpens this one: whatever reconciliation R12 designs
needs to account for three granularities (learned continuous onset risk,
declared global sounds/words/phrases, and declared word-specific patterns),
not two. See `PROBLEM_FORMULATION.md` §1/§2/§6.
**Update (2026-08-16) — resolved for the reformulation engine specifically.**
`reformulate.py` consumes only the declared `DifficultyProfile` (sounds,
words, and word-specific patterns — phrases still have no consumer, see
R13) — the learned `SpeakerDifficultyProfile`
is not read by the new engine at all, and its onset-risk chart was removed
from `app.py` (`DECISION_LOG.md` 2026-08-16-E) since, with no audio/ASR
pipeline in scope, it had no real learned data to show. This resolves the
reconciliation by *not* combining the two signals rather than by merging
them — `profiling/profile.py` remains in the repo, untouched, in case
audio input returns to scope later.

### R13. Give `difficulty_profile.phrases` (and now `problem_phones`) a consumer
**Linked finding:** `PROBLEM_FORMULATION.md` §6/§10 — phrases and (as of
the Stage 4A refinement) word-specific `problem_phones` are declared and
persisted but nothing in the current reformulation pipeline accepts or acts
on either. `problem_phones` is arguably the higher-value of the two once a
redesigned engine exists — it's a more precise signal than a whole-word
block, but currently degrades to exactly whole-word blocking today.
**What this roadmap item actually is:** Once the reformulation engine is
being redesigned, decide (a) how a stored phrase gets matched against new
input text (exact substring vs. fuzzy/reordered vs. partial overlap —
genuinely undecided, per `PROBLEM_FORMULATION.md` §3.5), and (b) how a
word-specific pattern should change substitution candidate scoring
differently than a plain word-level flag would.
**Labeled as:** Future work, explicitly deferred by Stage 4A's own scope
restriction, not overlooked.
**Update (2026-08-16) — half done.** `problem_phones` now has a consumer:
`reformulate.py::_flagged_positions`/`_trigger_reasons` reads a word's
`problem_phones` and surfaces it as the `word_specific_pattern` trigger
reason (`DECISION_LOG.md` 2026-08-16-E), resolving part (b) above by
treating a word-specific pattern the same as a whole-word flag for
*triggering* substitution (it doesn't yet narrow candidate scoring
differently than a plain word-level flag would — that finer distinction
is still open). Part (a), phrase matching, is untouched — `phrase_values()`
is not called anywhere in `reformulate.py`. Still open.

### R14. Build and browser-verify the inline text-selection flagging component
**Linked finding:** `PROBLEM_FORMULATION.md` §7 — a true "select text
in-place, a small button appears" interaction was researched and its
technical approach fully specified (`st.components.v1.html` +
`window.getSelection()` + a hand-rolled, locally-vendored Streamlit
component-value channel) but deliberately not built, because this
environment cannot verify real browser JS and shipping it unverified would
repeat the exact, already-on-record `voice.py`/`st.iframe` pitfall
(`ROADMAP.md` H1).
**What this roadmap item actually is:** Implement the specified approach in
a session with real browser access, verify it actually works before
presenting it as done, and keep the current native-Streamlit path
(free-text + quick-pick dropdown) as the fallback either way — the
component would be a UX upgrade to the interaction, not a replacement for
having a reliable one.
**Labeled as:** Future work with an already-specified technical approach —
not a fresh unknown, an implementation task deferred for a verifiability
reason, stated as such in `PROBLEM_FORMULATION.md` §7.2.

### R15. Build a pronunciation-variant picker for heteronyms
**Linked finding:** `PROBLEM_FORMULATION.md` §11.3, `DECISION_LOG.md`
2026-08-16-B — confirmed against real CMU data, not hypothetical:
`"read"` has 2 pronunciation variants, `"the"` has 3, `"object"`/`"often"`/
`"route"` each have 2. `full_pronunciation()` silently uses the first-listed
one; a word entry now flags `meta["has_alternate_pronunciations"]` when
this applies (fixed, 2026-08-16), but nothing yet lets the user say *which*
variant they meant.
**What this roadmap item actually is:** Design and build a small UI (e.g. a
selectbox of the CMU variants, each rendered via `friendly_phone_label()`)
that appears when `has_alternate_pronunciations` is set, letting the user
pick the intended pronunciation; store the choice (which CMU list index,
or the resolved phone tuple) on the entry.
**Labeled as:** Future work — real new UI and tests, correctly out of scope
for the audit adjustment that found the gap; not started.

### R16. Word-sense-specific difficulty (same spelling, different context)
**Linked finding:** `PROBLEM_FORMULATION.md` §11.3 — a word that's
difficult in one grammatical sense/role but not another (a deeper version
of the heteronym case above) cannot be represented today; the profile is
type-level (one entry per spelling), not occurrence- or sense-level.
**What this roadmap item actually is:** This is word-sense disambiguation,
already named as a real, unsolved problem for the reformulation engine
generally in `RESEARCH.md` §2.B/§7 — not a profile-schema gap to close in
isolation. Revisit only once the reformulation engine has some WSD-capable
component (e.g. an MLM-based contextual candidate generator, per
`RESEARCH.md` §2.B) to actually make use of a sense-scoped difficulty
declaration; building the storage for it first would be speculative.
**Labeled as:** Explicitly named out-of-scope future work, not a near-term
item — blocked on reformulation-engine capability that doesn't exist yet.

### R17. Fix `rephrase.py::_bad_words_ids()`'s case-sensitivity gap
**Linked finding:** `VALIDATION.md` §6.3, Cause A — directly measured, not
inferred: blocking `"researcher"` does not block `"Researcher"`, confirmed
by tokenizing both (different token IDs) and by a controlled
`_model.generate()` repro showing the lowercase form never leaks (0/6
beams) while the capitalized form leaks in 5/6. Contributed to 2 of the
4 escalation failures observed in Stage 6's evaluation corpus.
**What this roadmap item actually is:** Encode capitalized/title-case
(and plausibly all-caps) variants of each blocked word in
`_bad_words_ids()`, not just the form passed in. Small, mechanical,
low-risk — does not touch the escalation trigger logic, the verification
gates, or any scoring formula.
**Labeled as:** A confirmed bug with root-cause evidence, not a
hypothesis — explicitly not fixed during Stage 6 per that stage's
no-tuning boundary. Next concrete implementation candidate.
**Update (2026-08-16) — FIXED and measured, DONE, but did not move the
metric it was expected to move.** `_bad_words_ids()` now encodes each
blocked word's lowercase and capitalized forms (each with/without a
leading space). 8 new regression tests (`tests/rephrase_test.py`, all
pass) confirm the fix works: the original repro's 5/6 capitalized-form
leak is now 0/6. Re-running Stage 6's exact corpus afterward found **the
fix recovered 0 of the 4 `could_not_safely_reformulate` cases** — the
literal-word leak was real and is now closed, but it was never the
dominant failure cause; R18 (below) already accounted for the remaining
4/4. An unplanned second finding surfaced while verifying this: blocking
more token forms also pushes T5's beam search toward lower-similarity
paraphrases (observed 0.49–0.61 post-fix vs. 0.81–0.91 pre-fix on the
same case), which then fail the SBERT gate instead of the phoneme gate —
so the specific rejection reason shifted without the outcome changing.
Full record: `VALIDATION.md` §6.8, `DECISION_LOG.md` 2026-08-16-H. Closed
as implemented and measured; R18 is now the only lever left for the
escalation path's success rate.

### R18. Escalation-model mismatch: T5 paraphrase objective vs. phoneme-avoidance requirement
**Linked finding:** `VALIDATION.md` §6.3, Cause B — the deeper of the two
escalation-failure causes. `Vamsi/T5_Paraphrase_Paws` is trained to
produce near-identical-meaning paraphrases, which tends to preserve the
original vocabulary's semantic field — so when the flagged phoneme
cluster is semantically central to the sentence (e.g. "struggle"/
"stress"/"strategy" all sharing STR), paraphrasing tends to reintroduce
the same sound via unblocked synonyms/inflections, even with perfect
word-level blocking. This confirms, with concrete evidence for the first
time, the limitation `REFORMULATION_RESEARCH.md` §24.E only theorized.
**What this roadmap item actually is:** An open research question, not a
scoped fix — possible directions (none evaluated yet): a different/
fine-tuned paraphrase model with phoneme-awareness; a hybrid approach that
also swaps individual words within the T5 candidate post-hoc; accepting
this as a hard limit and improving the honesty of the "could not safely
reformulate" messaging instead of chasing a fix. Needs its own research
pass before any implementation decision, consistent with §6/§9's
"be willing to discard, but verify before you replace" discipline.
**Labeled as:** Confirmed limitation (not fixed here), future work.
**Update (2026-08-16) — now the sole remaining lever, plus one new
consideration.** R17's fix (above) confirmed this is the dominant cause:
fixing the case-sensitivity leak recovered 0/4 escalation failures. A
second effect surfaced while verifying R17: more aggressive word-level
blocking measurably pushes T5 toward lower-similarity paraphrases (§6.8),
so any future fix here that works by blocking *more* terms (e.g. also
blocking known synonyms/inflections of flagged words) should be checked
against this side effect specifically, not assumed to only improve
things — it may trade a phoneme-veto rejection for a semantic-gate
rejection instead of an actual pass.
**Update (2026-08-16) — real, but its urgency just dropped, measured.**
`VALIDATION.md` §6.9 ran a 210-case corpus of ordinary text (36
already-committed sentences + 6 ordinary paragraphs) against 5 realistic,
non-adversarial profiles, specifically to check whether Stage 6's 0/4 was
representative. It wasn't: escalation succeeded 12/28 times (42.9%) when
triggered, and the profile modeled directly on this repo's own real
`users/default.json` never reached escalation at all across all 42
texts. Cause B is still real and reproducible on Stage 6's own two
cases — this doesn't retract the finding — but it's now clear it
dominates specifically when several instances of one onset are
semantically load-bearing in a single sentence, not typical ordinary
usage. **Re-prioritized, not closed:** R9 (wire the review UI's
keep/revert signal into the profile) and the still-never-run human-
judgment study (`eval/study/`, §1/§5) are no longer obviously lower
priority than R18 by comparison — left for the next planning step to
decide, not decided here.
**Update (2026-08-17):** `REFORMULATION_PROBLEM_MAP.md` §3.3 found the
most actionable lever for this item specifically: HuggingFace
`transformers` already supports constrained beam search with disjunctive
constraints (`force_words_ids`), a strictly more expressive drop-in
replacement for the current manual `bad_words_ids`-only blocking, same
library, no new model. It does not close Cause B outright (still
token-level, not phoneme-class blocking) but may reduce the R17-follow-up
side effect (tighter blocking → lower-similarity survivors, §6.8). Ranked
item 3 in that document's §5 implementation order, after the idiom guard
(R19, done) and word-sense disambiguation — not started yet.
**Update (2026-08-17, second):** R20 (word-sense disambiguation, done)
measurably raised this item's urgency, not just its ranking position —
`VALIDATION.md` §11.7 found the escalation-trigger rate on ordinary text
rose from 10.4% to 14.1% as a direct effect of R20, at the same ~42%
escalation success rate. More of the engine's real workload now depends
on this item's unimproved success rate than before R19/R20 existed.

### R19. Idiom/fixed-expression guard for substitution — **DONE, 2026-08-17**
**Linked finding:** `VALIDATION.md` §9.7/§9.9 — the pilot's single
best-evidenced problem (two independent analyses, the largest SBERT-
vs-human gaps and the largest category-score gap, converge on the same
mechanism): substituting a word that's a load-bearing component of a
fixed idiom or collocation ("how's it going," "drives me crazy," "right
now") breaks the phrase even though the substitution passes every
per-word check. Named and ranked item 1 in `REFORMULATION_PROBLEM_MAP.md`
§5, the project's new living problem/research map.
**What was done:** `semantic.py` gained a curated idiom-phrase guard
(`IDIOM_PHRASES` + a pronoun-wildcard `IDIOM_PHRASE_PATTERNS`), reusing
the existing `protected_positions()` substitution-blocking mechanism.
Verified against the exact real pilot data, not just synthetic tests:
the specific broken outputs P1 rated poorly no longer occur, 26/30 other
pilot pairs are byte-identical (no collateral change), Stage 6's corpus
is unaffected (zero phrase overlap). Found and fixed one follow-up
correctness bug in the same pass — an early version silently excluded
idiom-locked-but-profile-matching words from the flagged-word counts
entirely, which would have made "difficulty resolved" misleading in a
new way; fixed so the metric now correctly reports these as unresolved
instead. Full record: `VALIDATION.md` §10; `DECISION_LOG.md` 2026-08-17-I.
**Labeled as:** Done, with a disclosed trade-off, not a free win — when
the only word matching a declared difficulty sits inside a protected
idiom, that difficulty is now correctly left unaddressed (reported
honestly) rather than incorrectly reported as resolved via a broken
substitution. A curated list, not a general MWE detector (`REFORMULATION_
PROBLEM_MAP.md` §3.1's `[GAP]`) — a novel idiom not on the list will
still break as before.

### R20. Word-sense disambiguation before candidate generation — **DONE, 2026-08-17**
**Linked finding:** `VALIDATION.md` §9.9 — "right" in "right now"
(immediate sense) substituted using the correct/fair sense
("justly"/"properly"), twice, independently. Item 2 in
`REFORMULATION_PROBLEM_MAP.md` §5.
**What was done:** `semantic.py::disambiguate_synset()` picks one
WordNet synset via SBERT gloss-matching against a local context window
before `engine.py` generates candidates (reuses the existing SBERT
model, no new dependency). Fixes the general sense-confusion problem,
not just "right now" — verified on a sentence outside the idiom guard's
coverage. **Not a clean first pass:** re-running Stage 6's corpus (per
direct instruction) found two real regressions before this was called
done — a candidate colliding with another declared-difficult word
(`_try_substitution` now also rejects those), and whole-sentence
context failing to disambiguate two occurrences of the same word in one
sentence (fixed with a local token window instead). Both root-caused
and fixed in the same pass. Re-confirmed at scale against the 210-case
ordinary-text corpus: escalation-trigger rate rose 10.4%→14.1% (same
~42% success rate once triggered) — a real, quantified cost of smaller
sense-pure candidate pools, not engineered around. Full record:
`VALIDATION.md` §11; `DECISION_LOG.md` 2026-08-17-J.
**Labeled as:** Done, with two disclosed costs, not a free win — (1)
single-sense candidate pools are sometimes smaller/lower-scoring than
the old sense-mixed ones even when correct, measurably shifting more
sentences onto the escalation path (§11.7); (2) the local-window fix
repairs the *structural* bug for repeated words with different senses,
not full correctness for that already-documented hard case
(`REFORMULATION_RESEARCH.md` §17 row 5) — still open.
**Update (2026-08-17):** §11.7's escalation-rate increase directly
raises R18's priority relative to where it stood after R19 alone — more
of the workload now depends on escalation's success rate, which this
item did not touch.
**Update (2026-08-17, second):** R21 (below) tested one candidate fix —
a stronger, promptable model given the constraint's reason — and it
failed to meaningfully improve pass rate, at two model sizes. This is
evidence *for* Cause B being a structural limitation (not just a Vamsi-
model-specific quirk or a "the model needs more context" gap), which
somewhat lowers confidence that a model swap alone will resolve this
item — the next test (constrained beam search, R21's own next-step
recommendation) targets the decoding *mechanism* instead, a genuinely
different lever, not a repeat of what R21 already ruled out.

### R21. Diagnostic: promptable model + constraint reason vs. blocklist-only escalation — **TESTED, 2026-08-17, negative result**
**Linked finding:** Two research passes (`REFORMULATION_PROBLEM_MAP.md`
§3.8/§3.9, prompted by direct user questions) independently converged
on the same recommendation: before building a phrase-level tier or
fine-tuning anything, test whether giving the escalation model the
*reason* for a constraint (not just a blocklist) improves the ~42%
escalation success rate. Item 3 in `REFORMULATION_PROBLEM_MAP.md` §5.
**What was done:** `eval/escalation_model_comparison.py` — all 22 real
sentences where production escalation currently triggers and fails
(re-derived from `reformulate.reformulate()`, not hand-picked) were run
through `google/flan-t5-base` (247.6M params, comparable to the current
model's 222.9M) prompted with the flagged words plus a natural-language
reason, with no `bad_words_ids`, and a hybrid variant with both. Every
candidate, from every condition, was scored with the exact same three
checks `reformulate.py::_try_escalation` already applies.
**Result:** Reason-based prompting robustly improved meaning
preservation (avg. SBERT similarity 0.865 → 0.950) but barely moved the
actual pass rate (0% → 4.5%, or 9.1% hybrid) — because the bottleneck is
constraint satisfaction, not fluency, and a prose explanation does not
reliably make the model obey a phonological rule. Re-tested at 3.5×
model size (`flan-t5-large`, 783M params, 8-case stratified sample):
same picture, meaning preservation improved further (0.982) while pass
rate stayed flat — ruling out "the model was just too small" as the
explanation. A new failure mode was also found: the hybrid condition
produced one case of the model echoing a fragment of its own
instruction prompt as the "rewritten" output — a risk pure-blocklist
approaches don't share. Full record: `VALIDATION.md` §12;
`DECISION_LOG.md` 2026-08-17-L.
**Labeled as:** A real, informative negative result, not a failed
experiment — it rules out a specific, plausible-sounding fix
(model-swap-with-explanation) with real evidence rather than leaving it
as an untested assumption, and reframes R18/the constrained-beam-search
item as worth testing *combined with* reason-prompting rather than as
an alternative to it. Per the plan's own condition, the phrase-level
tier (`REFORMULATION_PROBLEM_MAP.md` §5 item 4) was **not** started, and
the current engine was not modified or replaced — this was a
side-by-side diagnostic only.

### R22. Evaluate constrained beam search (`force_words_ids`) — **BLOCKED, 2026-08-17, not evaluated**
**Linked finding:** The next item in the plan after R21, independently
justified regardless of R21's result — `REFORMULATION_PROBLEM_MAP.md`
§3.3 named `force_words_ids` as the most actionable lever for R18,
based on published HuggingFace documentation describing it as built
into `transformers`, no new dependency.
**What was found, by testing directly rather than trusting the
documentation:** `transformers==5.10.2` (this project's installed
version) has moved constrained beam search out of the core library.
`model.generate(force_words_ids=...)` now raises `ValueError` unless
`trust_remote_code=True` is passed (a new class of risk — Hub-fetched
code executed at call time — not taken on anywhere else in this
project), and even with that flag set, the replacement community repo
(`transformers-community/constrained-beam-search`) does not currently
contain a loadable `generate.py` — confirmed via `OSError`, not
assumed. The underlying `DisjunctiveConstraint`/`PhrasalConstraint`
classes are also no longer importable in this version as a lower-level
fallback. **The technique's actual behavior was never measured — the
packaging path was found to not exist before any evaluation could
happen.**
**Labeled as:** Blocked, not evaluated — the item's feasibility rating
in `REFORMULATION_PROBLEM_MAP.md` §4 corrected from "Small" to
"Medium+, blocked." Real options exist (pin an older `transformers`,
accept `trust_remote_code=True`, or hand-implement disjunctive
decoding) but each is a real decision with implications beyond this
one item — pinning an older library version affects every model call
in this project (SBERT, both T5 checkpoints), so this is surfaced for
the user to weigh in on rather than decided unilaterally mid-diagnostic.
Full record: `VALIDATION.md` §13; `DECISION_LOG.md` 2026-08-17-M.

### R23. Decoder-only instruction-tuned model vs. T5 baseline — **TESTED, 2026-08-18, negative result**
**Linked finding:** Per direct instruction, after R21 (prompting a
comparable-size encoder-decoder model) and R22 (blocked): does a
genuinely different architecture family — decoder-only, instruction-
tuned — beat the current T5 escalation path, within this project's
actual constraints (no `transformers` version change, no
`trust_remote_code`, no new heavy dependency)?
**What was done:** `eval/escalation_model_comparison_decoder.py`, reusing
R21's case-finding and verification directly. Two candidates chosen and
verified to actually load in this environment first (no gating, no
`trust_remote_code`) rather than assumed from reputation: Qwen2.5-0.5B-
Instruct (494.0M params) and Qwen2.5-1.5B-Instruct (1543.7M params).
Gemma and Llama were excluded — both gated, and this project makes
unauthenticated Hub requests only.
**Result:** Qwen2.5-0.5B (n=8, complete): 0/8 passed, avg. meaning
similarity 0.663 (reason-only) / 0.571 (hybrid) — **worse** than the
T5 baseline's 0.861, and far worse than R21's flan-t5-base result
(0.950). The model often didn't perform the rewrite task at all
(hallucinated unrelated content, or produced confused meta-commentary
about the instruction itself). Qwen2.5-1.5B (n=2, pilot only — not
completed to n=8, per direct instruction to stop the session): better
task-following, but stilted phrasing and one outright factual error
("a fresh pastry" → "an unbaked treat"). Both sizes were dramatically
slower than the T5 family: ~31s/case (0.5B) and ~97s/case (1.5B) versus
~2.6s/case for flan-t5-base — a 10-40x gap, most likely a structural
cost of decoder-only generation via plain `transformers` CPU inference
(no quantization/optimized runtime), not a "wrong checkpoint" problem.
A real implementation bug (missing `no_repeat_ngram_size` after
switching to greedy decoding, causing degenerate repeated-prompt output)
was found and fixed before any reported result was trusted. Full
record: `VALIDATION.md` §14; `DECISION_LOG.md` 2026-08-18-A.
**Labeled as:** A real, informative negative result, not an
incomplete experiment — the 1.5B run's smaller sample (n=2 vs the
planned n=8) is a completeness gap, not an uncertainty gap: the
quality/speed trend across the two sizes is consistent and large enough
that more samples would narrow confidence around the same conclusion,
not plausibly reverse it. This closes item 3 in
`REFORMULATION_PROBLEM_MAP.md` §5 on a third independent angle (after
prompting and constrained decoding) — none of the three cleared the
bar for a model/decoding swap. The one remaining lever that could
plausibly change this verdict (an optimized/quantized local-inference
runtime, e.g. `llama.cpp`/GGUF) is a new-dependency decision, not a
model choice — surfaced as a separate, explicit, not-yet-decided
question, same category as R22.

### R24. Validate a second semantic-preservation signal (MeaningBERT) — **VALIDATED, 2026-08-18, real but partial**
**Linked finding:** After R21-R23 closed the model/decoding-swap
avenue, the user approved a new sequence — C (validate a second
semantic signal) → A (phrase-level tier) → E (re-examine multi-
difficulty) → reassess — explicitly requesting Option C proceed first,
with a strict scope limit so it wouldn't become another long-running
experiment. `REFORMULATION_PROBLEM_MAP.md` §5 item 6; §3.7's `[GAP]`
("does an alternative to SBERT actually catch idiom-breaking better, or
is that unverified").
**What was done, within the agreed limits:** one small model
(MeaningBERT, 109.5M params, BERT-base scale, no `trust_remote_code`,
no gating), 14 sentence pairs pulled directly from already-recorded
pilot data (the 9 known SBERT-vs-human disagreement cases from
`VALIDATION.md` §9.7 plus 5 control pairs where SBERT and the human
rater already agreed), single forward passes only — no new corpus, no
generation, no long-running sweep.
**Result:** real but partial. MeaningBERT catches several idiom-
adjacent breaks SBERT missed badly (largest: SBERT 0.968 vs.
MeaningBERT 48.0 on a genuine causative-construction break). But it
**completely misses the single worst-rated case on record** (human
meaning=1/5; MeaningBERT scores it 94.5, indistinguishable from clean
control pairs — the same mistake SBERT made). Not a strict improvement
— a different, overlapping-but-not-superset blind spot. Full record:
`VALIDATION.md` §15; `DECISION_LOG.md` 2026-08-18-B.
**Labeled as:** Proceed with wiring MeaningBERT in as a genuine second,
reported-alongside signal (never replacing SBERT, never silently
blended — Practice.md §10) — exactly the scope already planned, not
upgraded to "the fix" by this result. Its real value is flagging
disagreement between the two signals, not replacing either one. The
case it missed is concrete evidence (not just an architectural
argument) that R24 doesn't substitute for item 4's structural detection
approach (R25, below) — reinforces rather than delays that item.
**Not yet done:** the actual engine wiring (`reformulate.py`/`app.py`)
— this entry covers the validation step only, per explicit scope.

### R25. Phrase-level replacement tier — **DONE, 2026-08-18**
**Linked finding:** Option A of the user's own approved C → A → E →
reassess sequence, built directly rather than waiting on item 3's
original "meaningful improvement" gate — the user's explicit
reassessment superseded that gate. `REFORMULATION_PROBLEM_MAP.md` §5
item 4; §2.4's single best-evidenced pilot problem.
**What was done:** `semantic.py` gained `idiom_spans()` (the actual
span boundaries R19's curated idiom list matches, not just a flattened
position set — `idiom_protected_positions()` refactored to derive from
it, behavior-preserving). `reformulate.py` gained
`_try_phrase_replacement()`: fires only when a sentence's *only*
difficulty is idiom-locked (nothing else flagged); reuses
`rephrase.generate_candidates()` unchanged, scoped to a local window
(span ± 5 tokens) rather than the whole sentence; splices the result
into the full sentence and verifies *that* — never the window alone —
with the same checks the sentence-restructuring tier already uses, plus
the R20 candidate-collision check; falls back to R19's exact prior
behavior when nothing clears every gate. `app.py` got two small,
consistent changes for the new `source: "phrase"` (keep/revert, a CSS
tag); `feedback_targets()` extended to attribute phrase changes
correctly. No new dependency.
**Verification, isolated precisely rather than assumed:** a `git
stash`-based before/after (not inference from a stale target list)
against the frozen 30-item pilot corpus found the tier changed exactly
**one** pair — pair_01 (`gs_hows_it_going`), from left-alone-and-
unresolved to resolved (SBERT 0.9522) — with every other pair,
including Stage 6's 18-case corpus and the 210-case ordinary-text
corpus, byte-identical. Full regression suite (27 `reformulate_test.py`,
16 `semantic_test.py`, plus `app_test`/`difficulty_profile_test`/
`roadmap_test`/`rephrase_test`) all pass, including 8 new tests written
with the same T5-determinism-via-mocking discipline `EscalationTest`
already established. Full record: `VALIDATION.md` §16; `DECISION_LOG.md`
2026-08-18-C.
**Labeled as:** Done, with one honest limitation surfaced rather than
hidden — the recovered case's actual output ("Hey, how's it today?")
is grammatically thin despite passing every automated gate, the same
class of proxy-metric blind spot already found on SBERT (§9.7) and
MeaningBERT (R24) — a third independent confirmation that "passed
verification" is not the same claim as "confirmed high quality."
Doesn't re-establish the pilot's category-level numbers (would need a
new human-rated pilot round, not run here) and doesn't fix factor 2.3
(grammaticality), which now has its own accumulating evidence across
three separate mechanisms (substitution, and now phrase replacement).

### R26. Re-examine multi-difficulty interaction after the phrase tier (Option E) — **DONE, 2026-08-18, hypothesis corrected**
**Linked finding:** Option E of the approved C → A → E sequence —
`REFORMULATION_PROBLEM_MAP.md` §5 item 7, testing §2.7's own prior
hypothesis that multi-difficulty compounding "may already be explained
by §2.4 [idiomaticity] rather than needing its own separate fix," now
that R25's phrase tier exists to test it against.
**What was done:** pure re-analysis of data already gathered while
verifying R25 — no new code, no new corpus, no new experiment. Each of
the pilot's three `multi_difficulty` pairs was traced directly (not
inferred from output text) against `reformulate._flagged_positions()`/
`_idiom_protected_matches()`/`semantic.idiom_spans()` with its real
profile spec, to see exactly why each did or didn't change.
**Result:** none of the three changed (zero regressions). Why: only 1
of 3 (pair_28) involves an idiom span at all, and it's a *mixed* case
R25 correctly excludes by design (one substitutable word, one
idiom-locked word — substitution already resolves the former on its
own). The other 2 of 3 (pair_29, pair_30) have **no idiom span
whatsoever** — two ordinary, unrelated substitutable words — and trace
instead to the already-documented "generic overused replacement"
pattern (`VALIDATION.md` §9.9). Full record: `VALIDATION.md` §17.
**Labeled as:** The original §2.7 hypothesis is corrected, not
confirmed — multi-difficulty compounding is **not** substantially
explained by idiom-blindness in this sample, 2 of 3 cases trace to a
different mechanism entirely. Factor 2.7 stays open as its own problem;
n=3 remains too small to generalize beyond this specific finding, and
per explicit scope, no further investigation (larger sample, a fix for
the frequency-bias pattern, or anything else) was started here.

### R27. Bounded investigation of R26's ranking mechanism + grammaticality, then MeaningBERT wiring + idiom-guard extension — **DONE, 2026-08-19 (partial: grammaticality blocked)**
**Linked finding:** direct instruction to investigate (not implement)
why `push`→`force`/`urge` and `grab`→`catch`/`take` outrank better
alternatives (R26/§18.2), and what signal could realistically catch this
project's known grammaticality failures, before touching the previously
proposed order (MeaningBERT wiring, grammaticality wiring, idiom-guard
extension). Also: record, per direct user instruction, an orchestration
principle for a future quality-based escalation trigger (local
substitution stays the default; full-sentence rewriting is a first-class
alternative, not a replacement, triggered when substitution is genuinely
inadequate) — explicitly not implemented this pass, recorded only.
**What was done:** re-ran the actual production candidate-ranking path
(`engine.get_synonyms` → `reformulate._raw_candidates` →
`semantic.rank_candidates_contextually`) directly for the real pilot
sentences; inspected the reformulation-output verification path for any
grammar check (none exists) and the existing, already-built but
input-only LanguageTool integration in `grammar.py`; attempted to
directly instantiate LanguageTool (not just check for the package).
`REFORMULATION_PROBLEM_MAP.md` §2.8 updated with the orchestration
principle and §5 gained items 11 (deferred), 12, 13. Then, per the
evidence: MeaningBERT (item 6) wired into `semantic.py`/`reformulate.py`/
`app.py` as a read-only reported signal, verified against R24's own
recorded scores; the idiom guard (item 13) extended with the literal
phrase "push the meeting" in `semantic.py`'s `IDIOM_PHRASES`, verified
with the same `git stash` isolation technique R25/R26 established.
**Result:** two distinct root causes for R26's pattern, not one — a
missing WordNet sense for "push [a meeting]" (postpone), and a genuine
sentence-embedding bias toward generic/high-frequency words that the
0.10-weighted frequency term reinforces rather than causes; neither is
fixable by reweighting `w_sim`/`w_freq`. LanguageTool is blocked by a
**Java version mismatch** (`SystemError: Detected java 1.8. LanguageTool
requires Java >= 17`), correcting R23's speculative "most likely Java
isn't installed" guess — three options surfaced, none decided
unilaterally. MeaningBERT wiring and the idiom-guard extension both
verified with zero collateral change (107 tests pass; Stage 6's 18-case
corpus byte-identical to committed baseline; the idiom-guard extension
changed exactly one pilot pair, pair_29, and even there only partially —
"push" is now honestly unresolved rather than mis-substituted, while
pair_29's separate "grab" problem remains open by design).
**Labeled as:** R26's ranking pattern is now mechanistically understood,
not just described (§9.9's framing corrected: the semantic term, not the
frequency term, is the dominant driver). Grammaticality-as-a-signal is
blocked on an infrastructure decision (same category as R13/item 5's
constrained-beam-search block), not abandoned. MeaningBERT wiring and
the idiom-guard extension are both done and verified. Full record:
`VALIDATION.md` §18-20.

### R28. Grammaticality resolved-and-measured (negative); MeaningBERT test coverage added — **DONE, 2026-08-19**
**Linked finding:** approved reordering of the four-item next-steps plan
(grammaticality + MeaningBERT tests first, deliberately before designing
the generic-word signal or the quality-based escalation trigger, on the
methodological ground that neither should be designed around a signal
whose usefulness hasn't been established yet).
**What was done:** resolved the R27 Java-version blocker with a portable,
project-local JRE 17 (no system install); ran `language_tool_python`
directly against R27's own known-broken/clean-control corpus; added
`tests/meaningbert_test.py` (9 tests) closing the zero-coverage gap the
R27 audit found.
**Result:** LanguageTool caught **0 of 7** known-broken outputs and
produced **0** false positives on 3 clean controls — a real, confirmed
negative (a direct sanity check verified the tool correctly catches
classic textbook grammar errors it simply was never given a chance to
fail on here). This project's specific failures are syntactically
well-formed sentences built from the wrong word, a class outside a
rule-based grammar checker's detection surface. A latent attribute-name
bug was also found (not fixed) in `grammar.py::_correct_with_
languagetool()` that would have crashed `sanitize_input()` the first
time LanguageTool ever found an actionable match in production. All 9
new MeaningBERT tests pass; full suite now 116 tests.
**Labeled as:** LanguageTool is now closed for this use case, not
blocked — §5 item 12 updated accordingly. A future grammaticality signal
needs a different kind of tool. MeaningBERT test coverage is done. Full
record: `VALIDATION.md` §21.

### R29. Design and validate a candidate specificity/genericness signal for "grab"→"take" — **DESIGNED AND VALIDATED, 2026-08-19, not implemented**
**Linked finding:** R26/R27's mechanistic finding that the sentence-
embedding similarity term, not the frequency weight, drives the
generic-word pattern — this item is the approved next step (design and
validate a signal before designing the escalation trigger), not a
ranking retune.
**What was done:** read `engine.py::_wordnet_synonyms()` directly to
find where a candidate actually comes from — a disambiguated synset's
direct lemmas (same specificity) or its hypernym lemmas (structurally
broader). Computed two candidate-level signals — WordNet hypernym-depth
delta and Zipf-frequency delta, both relative to the original word's
disambiguated sense — for the real production candidate pool across 3
independent "grab" contexts (pair_16, pair_17, pair_29) plus "push"
(pair_29) as a comparison case.
**Result:** depth-delta alone consistently flags "take" across all 3
grab contexts but also false-positives on legitimate rarer synonyms
("seize," "clutch"). Requiring **both** conditions — structurally
broader (depth) **and** anomalously more common (Zipf) — cleanly
separates "take" from the legitimate alternatives in every case tested.
The exact threshold is not settled by 4 cases; validated as directionally
correct and discriminating, not as a tuned cutoff.
**Labeled as:** a validated candidate signal, ready for a future,
separately-approved implementation decision as an additional hard gate
(same shape as the existing antonym/phoneme/profile-collision checks),
not folded into the weighted ranking formula. **Not implemented** — no
code changed, no weights touched. Full record: `VALIDATION.md` §22.

### R30. Fix the predicate-adjective POS-tagging bug behind pair_13 — **DONE, 2026-08-19**
**Linked finding:** surfaced as a side finding during the R30
escalation-trigger design investigation (traced directly, not assumed):
`pos_tag()` mis-tags "late" as RB (adverb) in "The bus was late again,"
when it's a predicate adjective after the copula — restricting candidate
generation to wrong-POS adverb synonyms ("recently"/"lately"). A
different bug category from CONAN's escalation-trigger work; approved
separately for immediate implementation.
**What was done:** `reformulate.py` gained
`_correct_predicate_adjective_tags()`, applied at both `pos_tag()` call
sites — reclassifies RB to JJ only for a curated `_FLAT_ADVERBS` list
directly following a BE-form. A broader "any WordNet adjective sense"
check was tried first and found to over-fire on "here" (a rare
satellite-adjective WordNet sense) before switching to the curated list.
**Result:** target case fixed (`"was late again"` → `"was belated
again"`, correctly resolves the flagged word); zero false positives on 8
adversarial controls; 3 new regression tests
(`PredicateAdjectiveTaggingTest`); full suite 119 tests, all pass;
`tests/smoke.py` byte-identical to baseline — zero collateral change,
confirmed by diff.
**Labeled as:** done and verified. Full record: `VALIDATION.md` §23.

### R31. Build and validate an evaluation corpus for R29/R30 — **DONE, 2026-08-19 — result: R29 not promoted**
**Linked finding:** Tier 2 of the approved reordered plan — test R29's
genericness signal against a broader, explicitly-labeled corpus (real
pilot cases with human ratings + new constructed cases) before deciding
whether to promote it.
**What was done:** reused the exact production candidate-ranking call
chain; built a corpus mixing REAL pilot cases (human ratings read
directly from `eval/pilot_responses/P1.csv`) and NEW constructed cases,
clearly labeled. Found and corrected a methodological error mid-run
(`DISABLE_DATAMUSE=1` gave a non-representative candidate pool).
**Result:** R29's signal flags "grab"→"take" in two real pilot cases the
human rated 5/5/5 and preferred — a confirmed, direct contradiction on
its own target pattern. 7/7 correct on unrelated ordinary substitutions
(not broadly broken, just wrong about this pattern). SBERT/MeaningBERT
disagreement magnitude tested against R24's own data: no clean
relationship to human-judged severity. Multi-substitution interaction
flagged as the strongest remaining lead.
**Labeled as:** R29 **not promoted** — stays research-only. Full record:
`VALIDATION.md` §24.

### R32. Multi-substitution interaction is not a distinct mechanism — **DONE, 2026-08-19**
**Linked finding:** R31's strongest remaining lead — the `multi_difficulty`
category's real, large rating gap (§9.6) — investigated directly rather
than assumed to be a genuine interaction effect.
**What was done:** traced the substitution loop directly (sequential,
each candidate scored against the pristine original sentence, no
explicit interaction check anywhere); analyzed `pair_28`/`29`/`30` in
full using their real `changes_made`/human comments; ran all three
through **today's live engine** to see what's changed since the frozen
capture; built 2 new cases pairing words each independently confirmed
good in R31.
**Result:** 5 of 5 cases (3 real + 2 new), zero exceptions — every
failure traces to exactly one bad substitution, never to the combination
of two. Two of the three original pilot defects are already fixed by
unrelated prior work (R19, R27's idiom-guard entries), not by anything
related to multiple substitutions. A new, previously-unnamed failure
class surfaced: inflection/word-class mismatch (distinct from R30's
predicate-adjective bug, same general shape).
**Labeled as:** multi-substitution interaction **not supported** as a
distinct mechanism — actively contradicted, not merely unconfirmed. Do
not design a signal around it. A general per-word grammaticality/fluency
check is the better-motivated next investigation (R33). Full record:
`VALIDATION.md` §25.

### R33. Fluency/naturalness signal investigation — **DONE, 2026-08-19 — GPT-2 rejected, DistilBERT promising**
**Linked finding:** R32's redirect — a general per-word naturalness
check, not an interaction-specific one.
**What was done:** tested two candidates via already-installed
`transformers` (new checkpoints, no new dependency): GPT-2 sentence
perplexity, and DistilBERT masked-LM word-probability at the substituted
word's position specifically.
**Result:** GPT-2 rejected — rated R30's own fix as *less* fluent than
the bug it replaced. DistilBERT showed strong separation on matched
contrast pairs (e.g. start 0.2578 vs. starting 0.0001 in the same
sentence) but left one ambiguity open: legitimate rare synonyms (seize/
clutch) scored 0.0000, indistinguishable from known-bad cases.
**Labeled as:** GPT-2 — reject. DistilBERT — promising, ambiguity
investigated next (R34). Full record: `VALIDATION.md` §26.

### R34. Resolving R33's ambiguity: rarity vs. genuine mismatch — **DONE, 2026-08-19**
**Linked finding:** R33's one open question — is DistilBERT's low score
for seize/clutch a rarity bias (bad) or real collocation-mismatch
detection (good)?
**What was done:** tested the same words (plus grasp, snatch) in both a
natural, idiomatic context and the forced grab-substitute context.
**Result:** uniform, decisive swing across all 4 words — high-confidence
scores (0.05-0.44) in natural context, collapsing to 0.0000 only when
forced into the mismatched context (ratios of 2,259× to 468,789×). Not a
rarity artifact — genuine collocation-mismatch detection. Zero confirmed
false positives, zero false negatives across R33+R34 combined.
**Labeled as:** DistilBERT masked-LM word-probability is the strongest
candidate signal found across R28-R34. Not yet human-validated (n=25,
model-judgment only) — that's the explicit next step before any
implementation. Full record: `VALIDATION.md` §27.

### R35. Human validation of the DistilBERT signal — **DONE, 2026-08-19 — 17/18 agreement, one real blind spot found**
**Linked finding:** R34 closed the door on rarity-bias as an
explanation but remained model-judgment only — the explicit next step
was direct human confirmation.
**What was done:** 18 sentences (known-bad + known-good/legitimate-rare,
per R33/R34), presented blind and shuffled, rated Natural/Acceptable/
Unnatural by a single rater (same disclosed n=1 limitation as the
original P1 pilot).
**Result:** 17/18 agreement, including both R34-critical cases
("...seize/clutch coffee after?") independently rated Unnatural,
matching DistilBERT's 0.0000 score exactly. **One real disagreement**:
R30's own fix ("was belated") — DistilBERT's highest-scoring sentence in
the set — was rated Unnatural by the human. Register/formality mismatch
("belated" almost always appears in fixed collocations), a genuine blind
spot the collocational-fit signal doesn't catch. A second, milder
nuance: "take coffee" rated Acceptable, not fully Natural — an echo of
R29's original genericness concern, not fully resolved.
**Labeled as:** correlation strong enough to justify trigger design —
the strongest validation result across R28-R35 — but the blind spot and
nuance must carry forward into that design explicitly, not be treated as
resolved. Full record: `VALIDATION.md` §28.

### R36. Larger-scale naturalness signal validation — **DONE, 2026-08-19 — evidence supports Option A (reported-only) now**
**Linked finding:** final validation pass requested before an
implementation decision — expand R33-R35's 25-case corpus (38 new
cases) and specifically stress-test the "belated" blind spot, "take
coffee" ambiguity, and the multi-substitution architecture assumption.
**What was done:** built a corpus covering known-bad, known-good,
legitimate rare/formal (6 new), collocation/register mismatch (3 new
stress cases beyond belated), grammatical/inflection (3 new, zero reuse),
sentence-length variants, and 3 constructed multi-substitution sentences.
**Result:** zero false negatives at every threshold tested; false
positives concentrate specifically on "rest" (recurring across 3
sentences), not randomly. Register-mismatch blind spot confirmed
real but *not universal* — 2 of 5 stress cases show it (belated,
likely procure — unconfirmed), the other 2 (consume, terminate) are
caught correctly. Inflection/word-class confirmed as a complementary
catch on entirely new cases — closes that standing R32 open item.
Sentence length: no effect. **Multi-substitution: no cross-
contamination between positions — a good position stays good next to a
bad one, validating the Phase-2 design's core assumption directly.**
**Labeled as:** strong enough for reported-only diagnostics (Option A).
Not yet strong enough for full auto-escalation control (Option B) — the
blind spot's edges aren't fully mapped and the corpus remains
research-scale. Decision reserved for the user. Full record:
`VALIDATION.md` §29.

### R37. Contextual-fit signal wired in as a reported-only diagnostic (Option A) — **DONE, 2026-08-19**
**Linked finding:** the user's Option A decision after R36 — reported
diagnostics first, same rollout as MeaningBERT (R24/R27), not the full
soft-trigger architecture from the Phase-2 design.
**What was done:** `semantic.py` gained `contextual_fit_score()` (the
exact masked-LM mechanism validated R33-R36, `distilbert-base-uncased`).
`reformulate.py` scores every substitution-sourced change's replacement
word against the final assembled sentence, stored in that change's
`verification` dict — never gates anything. Scoped to substitution-
sourced changes only, matching what was actually validated (not phrase-
tier or restructuring). `app.py` surfaces it per-change, labeled
diagnostic-only. 12 new tests (`tests/contextual_fit_test.py`),
including an explicit regression guard on the "belated" blind spot
itself (asserted as present and expected, not a bug) and a direct test
that the signal never flips `final_ok`/`status` even at score 0.0.
**Result:** full suite 131 tests, all pass. `tests/smoke.py`
byte-identical to baseline — zero collateral change, confirmed by diff.
**Labeled as:** done, Option A only. No gate, no escalation trigger, no
threshold. Option B remains a separate, future, explicitly-gated
decision. Full record: `VALIDATION.md` §30.

### R38. Final system-level evaluation against the problem statement — **DONE, 2026-08-19**
**Linked finding:** closes the R17-R37 investigation arc — does the
system, taken as a whole, actually do what the problem statement asks?
Bounded to existing corpora and measurements, plus one retroactive
application of R37's already-validated signal to real (not lab) data.
**What was done:** scored every dimension (difficulty, meaning ×2
signals, naturalness, safety, escalation, over-reformulation,
preference) against existing evidence, explicitly labeling each as
directly-measured, enforced, reported-diagnostic, proxy, or unresolved.
Retroactively ran `contextual_fit_score()` against the real frozen
pilot's 26 actual substitution instances (new computation, existing
tool, existing data).
**Result:** Safety and SBERT-enforced meaning preservation are the
strongest, unqualified claims. Difficulty reduction and over-
reformulation are real but conservative by design. Both secondary
meaning/naturalness signals add real value with specific, named blind
spots. **The retroactive check found 2 new contextual-fit false
positives on real data** ("forgot"→"missed," "happened"→"occurred")
beyond the already-known "rest" quirk — a higher false-positive rate
than the lab corpus alone suggested, disclosed not smoothed over.
Escalation exists only as an unwired capability. **Preference is
unresolved** — the only number on record (73.3%, pilot) reflects
pre-R19-R37 output and cannot be treated as current.
**Labeled as:** the problem statement is answered *partially and
unevenly* — stated as the actual finding, not a hedge. The single
largest remaining gap is a genuine current-state human evaluation (no
valid preference or naturalness measurement exists for today's system).
Full record: `VALIDATION.md` §31.

### R39. Current-state human evaluation, executed — **DONE, 2026-08-20/21**
**Linked finding:** R38's single largest gap — no valid current-state
preference or naturalness measurement existed, only a pre-R19-R37
snapshot.
**What was done:** new script `eval/pilot_select_pairs_v4.py` (mirrors
`pilot_select_pairs.py`'s exact schema) regenerated 20 pairs through
today's live engine with live Datamuse (not `DISABLE_DATAMUSE=1`, per
R31's finding that flag changes the candidate pool). Group A (10) =
historical re-test of the same declared difficulties v3 rated; Group B
(10) = fresh coverage. v3 data archived to `eval/archive_v3/` first,
untouched. `eval/pilot_app.py` ran completely unmodified. Single rater
(n=1), same disclosed limitation as P1/R35.
**Result:** Group A matched-pair delta: 2 confirmed genuine fixes
(R19/R25's idiom-guard case, R27's "push the meeting" case — complaints
fully resolved), 1 confirmed regression ("sleep"→"nap," a live
candidate-pool drift), 1 case where R30's fix is confirmed structurally
working but exposed a separate, still-open candidate-quality problem
("late"→"after-hours"), 3 stable not-yet-fixed defects independently
re-confirmed by fresh blind rating (one with an *identical*,
independently re-typed complaint). Group B: 80% preference, mean
meaning 4.5/5, naturalness 4.3/5. Three items had to be swapped before
generation because they no longer produce a ratable output today —
each itself a real finding (`gs_driving_crazy` is now fully
idiom-protected, confirming R19 by the engine's own refusal, not
inference).
**Labeled as:** preference is no longer entirely unresolved — genuine
current-state numbers exist (~65% blended, n=20, n=1). Not a
replacement for the old 73.3% (different, deliberately edge-case-
weighted sample) — the valid comparison is the matched Group A delta.
Two new findings surfaced only by regenerating through live code, not
previously known. No further investigation started, per explicit
instruction. Full record: `VALIDATION.md` §32.

### R40. Ceiling probe + direct linguistic audit — **DONE, 2026-08-21**
**Linked finding:** direct user question after seeing repeated
`could_not_safely_reformulate` output — has the engine hit a ceiling? —
plus an instruction to judge output quality with general linguistic
capability, not the pipeline's own SBERT/MeaningBERT scores.
**What was done:** new script `eval/ceiling_probe_r40.py` ran 48 real
sentences (fetched live from four Wikipedia articles, register-diverse)
against 4 profiles (light to heavy density) through today's live engine,
live Datamuse — 192 pairs, one live run each, no restructuring-stability
recheck (disclosed limitation). Claude then read all 79 `reformulated`
outputs directly.
**Result:** 21/192 (11%) failed both tiers, concentrated in dense
profiles (`heavy_dense` 31%); T5 restructuring succeeded in only 2/192
runs, both the same sentence — it is not currently functioning as a
fallback. More consequential: direct reading of the 79 "successes" found
real, reproducible defects the pipeline itself scores as passing —
nonsense fragments ("sulfur"→"s", "greenhouse gases"→"gas gases"), a
~50,000-year factual error dressed as a synonym ("pre-industrial"→
"palaeolithic"), substitution-introduced grammar errors (correct "gases
was"→incorrect "gases were," 4x), and a fixed term eroding under
plain substitution ("small talk"→"little talk," 6x) — all scoring SBERT
0.877-0.971, MeaningBERT 56.8-94.5, `final_verification.passed=True`.
Re-running 6 of the worst cases found R37's contextual_fit (reported-only,
never gates) scores ≤0.0007 for 5 of 6, matching direct linguistic
judgment exactly — an existing, unused signal that would catch most of
this.
**Labeled as:** findings only, no fix implemented, per explicit
instruction. Points toward two concrete next steps, neither decided
here: revisit R37's Option A for contextual_fit now that real production
evidence exists, and add per-candidate rejection-reason logging to both
the substitution ranker and `_try_escalation` before any threshold
change, so the next step is measured, not guessed. Full record:
`VALIDATION.md` §33.

**Update, 2026-08-22 — R40 completed:** the entry above rated a curated
~15-example worst-of list; per follow-up instruction, R40 is now
completed with an unselected audit of all 112 individual substitutions
behind the 79 `reformulated` sentences. **Tally: 8/112 CLEAN (7%),
21/112 MINOR (19%), 83/112 SEVERE (74%)** — only 26% of substitutions
in this corpus were free of a real defect, a full-sample proportion,
not a curated list. Two new findings: `sanitize_input()`'s spellchecker
independently corrupts "optimises"→"optimists" (a separate subsystem
bug, not the reformulation engine); and the single worst substitution
found, "slower"→"easier", inverts its own sentence's logic while the
engine's `antonym_check` recorded "pass" (the two words aren't each
other's WordNet antonym). SBERT shows no per-substitution separation
either. Full record: `VALIDATION.md` §33.6.

### R41. Bounded validation of contextual_fit as a candidate substitution-quality gate — **DONE, 2026-08-22**
**Linked finding:** R40's recommendation (§33.5, a 6-example spot
check) that a ~0.01 contextual_fit threshold looked promising for
gating — tested here at full scale against R40's 112 labeled changes.
**What was done:** compared `contextual_fit` score distributions across
R40's CLEAN/MINOR/SEVERE buckets, swept reject thresholds. No
threshold promoted, no production gate, no T5 change, no fine-tuning,
per explicit scope.
**Result:** real signal (CLEAN median 0.0078 vs. SEVERE median 0.00004)
but heavy distribution overlap — no threshold cleanly separates good
from bad. At 0.01, 94% of severe defects are caught but so are **62% of
substitutions that were actually fine**; even 0.001 still misses 19% of
severe cases while rejecting 31% of good ones. Structurally blind to
the corpus's most damaging defects (the factual-era/"palaeolithic" and
"half-century" errors score 0.6-0.999 — they read fluently, which is
exactly what the signal measures).
**Labeled as:** explicitly revises §33.5's smaller-sample optimism, not
a quiet contradiction. contextual_fit remains worth further work as a
signal but is not shown safe as a standalone binary gate — either a
working retry/fallback path (which doesn't currently exist — R40 found
T5 restructuring succeeds in 2/192 runs) or a second signal for the
factual-correctness class is needed first. Neither decided nor
implemented. Full record: `VALIDATION.md` §34.

**Next, per direct instruction, not yet started:** an architecture
reassessment — is the current candidate-generation + verification
design sufficient, or has R40/R41's evidence accumulated enough to
justify investigating a learned, speaker-conditioned generation model
instead? This is the natural next entry, not another signal
investigation.

### R42/R43/R43-A. Architecture reassessment, escalation instrumentation, four bounded fixes — **DONE, 2026-08-22/23**
**Linked finding:** R41's own recommendation above, executed. Full
record was three standalone documents, consolidated 2026-08-26 into one
archival file, not folded into this file's usual R-item length:
`ARCHITECTURE_RESEARCH_R42_R43.md` (Parts 1-3).
**What was done:** R42 reassessed the architecture fresh against the
actual code and prior research. R43 instrumented every T5 candidate in
the 23 escalation-invoked cases from R40's corpus, not just the
final pass/fail. A1-A4 tested four candidate fixes (expanded inflected-
form blocking, a generate-verify-regenerate loop, an NLI logical-
consistency check, a LanguageTool re-test) in isolation; A5 stacked
A1+A3+A4 together.
**Result:** escalation fails 96% of the time from constraint-
satisfaction failure, not poor generation (76% of T5's candidates clear
a strict meaning-similarity floor). 68% of leaks are the blocked word
itself or a morphological variant — not unrelated same-sound words as
R42 first guessed. **The decisive number: even with every validated fix
stacked, only 1/23 dense-profile sentences produces a candidate that
survives a comprehensive check** — more verification lowers the accept
rate further (2%→9%→4%), showing the ceiling is the candidate pool, not
the checks.
**Labeled as:** points at the generation side of the escalation tier as
the actual bottleneck. Neither "patch the current substitution engine"
nor "fine-tune now" is supported; the evidence favors redesigning the
escalation tier's generation mechanism, once a human baseline exists
(R44). No production code, threshold, or model changed throughout.

### R44. Bounded v5 human evaluation — the pre-redesign baseline — **DONE, 2026-08-23**
**Linked finding:** R42/R43's recommendation to redesign the generation
tier, but per direct instruction, establish a human-rated baseline
first. Full record: `VALIDATION.md` §35.
**What was done:** rated the v5 corpus (20 sentences, R40 §33.6 Track C,
stratified against R40's own CLEAN/MINOR/SEVERE audit) through
`eval/pilot_app.py`, unmodified. n=1, same disclosed limitation as every
prior pilot round.
**Result:** strong aggregate agreement — mean meaning/naturalness/ease
and preference all degrade monotonically CLEAN→MINOR→SEVERE, no
reversals. But the 12 SEVERE cases split near-evenly by defect type:
nonsense/wrong-sense/register-confusion defects were reliably rejected
(7/12); grammar corruption, fixed-term erosion, a subtle factual error,
and the project's own worst logical-inversion case ("slower"→"easier")
were tolerated and even preferred (5/12) — in one case despite the
participant's free-text comment correctly naming the exact defect.
Overall preference: 70% (14/20).
**Labeled as:** the baseline the generation-tier redesign is measured
against. Redesign priority should weight nonsense/wrong-sense/register-
confusion classes more heavily than grammar/fixed-term/subtle-factual
ones, per this disclosed (n=1) human signal. No production code, new
signal, or architecture change in this evaluation.

### R45. Two bounded prototypes, and the architecture decision — **DONE, 2026-08-23**
**Linked finding:** R44's baseline, now used to decide between extending
the current hybrid, redesigning the generation tier, or fine-tuning.
Full record: `VALIDATION.md` §36.
**What was done:** Prototype 1 — combined NLI + LanguageTool validator
on all 79 R40 substitution-tier pairs. Prototype 2 — a custom
`LogitsProcessor` that kills a beam mid-generation the instant a word's
onset matches a blocked sound, tested on the same 23 escalation cases as
R43/A1/A2/A5. Both bounded to existing corpora, no production code
touched.
**Result:** Prototype 1: 32% recall on SEVERE (vs. ~20% for either check
alone) — real, partial. **Prototype 2: the largest improvement in the
whole R42-R45 arc** — leak-free 4%→100%, cases with any usable candidate
9%→52% (vs. 13% for A1, 4% for A5's stacked verification). A direct
manual read found ~half of "accepted" outputs still carry a real defect
— but every one is a meaning/logic/grammar defect (including a second
independent instance of the "slower→easier"-class logical inversion),
never a constraint leak — exactly what Prototype 1 targets. Also
disclosed: a narrow tooling gap (a blocked word absorbed into a
hyphenated compound escaped the leak-check) and a real cost when the
flagged word is the sentence's own subject (dropped rather than
replaced).
**Decision:** both prototypes show material, non-overlapping
improvement → **combine them**. Substitution stays primary; the
escalation tier's generation is rebuilt around phoneme-aware decoding;
the combined validator applies to both tiers' final output. **Fine-
tuning explicitly not justified** — its precondition (constraint
handling and validation failing despite being properly implemented) is
the opposite of what was measured. No production code, threshold, or
model changed.

### R46. R45's architecture, built as real, tested, additive code — **DONE, 2026-08-23**
**Linked finding:** R45's decision, implemented without delay per direct
instruction. Full record: `VALIDATION.md` §37.
**What was done:** three new functions, additive only — nothing existing
modified: `rephrase.generate_candidates_phoneme_constrained()` (R45
Prototype 2, promoted from diagnostic script), `semantic.
logical_consistency_check()`/`grammar_issue_count()` (R45 Prototype 1,
same lazy-load pattern as `contextual_fit_score()`), and `reformulate.
reformulate_v2()`/`_try_escalation_v2()` — a separate, parallel entry
point, not a flag on `reformulate()`.
**Result:** the full existing test suite passes unchanged, `smoke.py`
is byte-identical to baseline — `reformulate()` confirmed unaffected.
New `tests/reformulate_v2_test.py` (17 tests, real models) passes. The
real, integrated `reformulate_v2()` reproduces R45's diagnostic-script
number exactly (12/23, 52%) on the same 23 escalation cases — no drift.
The validator, running for real for the first time, caught the exact
"slower→faster" inversion found by manual review, plus independently
flagged the "glucose" restructuring case.
**Labeled as:** tested, verified, additive code — not a shipped
feature. `reformulate_v2()` is not called by `app.py`. Wiring it in,
and whether `validation` becomes a real gate, is a separate decision,
not made here.

**Update, 2026-08-24:** wired into `app.py` behind an opt-in sidebar
toggle, defaulting off — see `VALIDATION.md` §37.3.

### R47/R48. Architecture pushed to its evidenced ceiling, before the final decision — **DONE, 2026-08-24**
**Linked finding:** direct instruction to exhaust the remaining well-
evidenced engineering moves and integrate them, before deciding whether
the current architecture is enough or a custom model is warranted. Full
record: `VALIDATION.md` §38.
**What was done:** R47 — 10 fresh, hand-picked, non-Wikipedia sentences
through both `reformulate()` and `reformulate_v2()` directly. R48 — a
substitution-tier fix hypothesis (genericness + contextual_fit,
targeting R47's "playing"→"acting" case) tested against R31's own
known-good guard cases *before* writing any production code, and
correctly abandoned when it failed. An escalation-tier fix
(`_try_escalation_v3`: phoneme constraint + A2's iterative regeneration,
combined for the first time) built, found via direct tracing to have a
real over-blocking bug (degenerates to gibberish by round 3), fixed
(bounded, rarity-ranked retry), then found to have shipped a genuine
antonym-flip ("rational"→"irrational") that only NLI caught — fixed by
making NLI a real per-candidate gate inside escalation, not just a
report.
**Result:** R47 found a third, independent instance of the
`sanitize_input()` SVA bug, unprompted. R48's substitution hypothesis:
negative, correctly not built (seize/clutch score lower on
contextual_fit than the bad case it was meant to catch). R48's
escalation fix, final and gated: 12/23 (52%, same count as phoneme-
constraint-alone) but a safer, better set — the antonym flip correctly
refused, "starch"→"glucose" (flagged scientifically backwards in R40)
replaced by the correct "starch"→"cornstarch". Manual read of all 12
final successes: 5 CLEAN, 4 MINOR, 3 SEVERE (25%) — down sharply from
R40's 74%, not zero. Two of the three remaining SEVERE cases are defect
classes (wrong-word substitution, factual/physical-claim reversal) that
nothing in this pipeline currently catches by design, not by omission.
**Labeled as:** the honest ceiling of the low-risk architectural moves
available, tested to completion rather than left open. Full existing
suite passes throughout; `reformulate()` confirmed unaffected. Whether
this is "enough" is handed to the user next, not decided here.

### R49. The two remaining cheap levers, both tried, both hit a real wall — **DONE, 2026-08-24**
**Linked finding:** direct instruction to try the two remaining
low-cost, no-training-data escalation levers — wider candidate sampling,
and a prompted local-LLM validator for the two blind-spot defect classes
(wrong-word substitution, factual/physical-claim reversal) — before
treating "build something custom" as the evidenced answer rather than a
hypothesis. Full record: `VALIDATION.md` §39.
**What was done:** (1) Wider candidate sampling — beam width raised to
13-21 (from the production default) plus a second, independent
diversity mechanism (temperature 1.1, top_p 0.92, n=23-24 sampled
candidates), run directly on the 11 cases `_try_escalation_v3` still
refuses. Found and fixed two bugs along the way: a `KeyError` from
comparing sanitized vs. raw `original_text` (removed the unnecessary
lookup), and a literal `float("-inf")` in
`PhonemeConstraintLogitsProcessor` producing NaN under
`torch.multinomial` sampling — safe for beam search, fatal for
sampling; fixed by switching to a large finite `_KILL_SCORE = -1e9`
class constant, with the "already dead" check updated to match. (2) A
prompted local-LLM validator — Qwen2.5-0.5B-Instruct and
Qwen2.5-1.5B-Instruct (both already cached from R23, used here as a
judge rather than a generator), tested on 8 hand-picked cases (3 known
BAD substitutions including the R48 antonym-flip and the R40
pre-industrial/palaeolithic case, 4 known GOOD, one deliberate
cross-check), each model tried with verdict-first and reasoning-first
prompt orderings.
**Result:** Wider sampling rescued 0/11. The LLM judge: 0.5B = 4/8,
1.5B verdict-first = 5/8, 1.5B reasoning-first = 3/8 — no configuration
reliable, and the two prompt orderings fail in different, non-
convergent ways (0.5B and 1.5B-verdict-first both rubber-stamp almost
everything YES; 1.5B-reasoning-first over-flags GOOD cases instead).
Neither lever closes the wrong-word-substitution or factual-reversal
blind spots.
**Labeled as:** per the threshold the user themselves set before this
work started ("if both of those also hit a wall, that's the point
where 'build something custom' stops being a hypothesis and becomes
the evidenced answer"), that threshold is now met — for these two
specific gaps only. This is not a claim that the substitution tier,
the safety gates, or R48's escalation-quality gains are obsolete; they
stand independently and are unaffected by this result.

### R50 (Phase 2/3/7/9). Dataset construction, defect-typed labeling, and baseline report — **DONE, 2026-08-24**
**Linked finding:** direct instruction, following the user's own R50
proposal — before prototyping a custom validator, turn R40–R49's
accumulated evidence into a scientifically usable dataset and answer
whether it's actually enough to train on. Full record: `VALIDATION.md`
§40, `eval/r50_dataset_report.md`.
**What was done:** joined/deduped R40/R44/R47/R48/v5 (and one
reconstructed R48/R49 cross-check negative example) into 135 labeled
records / 88 unique underlying cases, added a structured defect taxonomy
(WRONG_WORD_OR_SENSE / FACTUAL_OR_LOGICAL_REVERSAL / GRAMMAR /
FIXED_TERM_OR_IDIOM / NATURALNESS_OR_REGISTER / OTHER_DEFECT / CLEAN)
alongside the existing severity, repaired R48's under-documented per-case
verdicts (3/12 documented, 9/12 freshly re-read and tagged as such),
benchmarked existing signals against the new taxonomy, and froze a
leakage-safe train/val/test split.
**Result:** at the unique-case level, class sizes are much thinner than
raw N suggests — FACTUAL_OR_LOGICAL_REVERSAL and FIXED_TERM_OR_IDIOM (the
two classes R49 flagged) sit at only 7-8 unique cases each. Two findings
sharper than R40-R49's: fixed-term-idiom erosion is a third, previously
undifferentiated blind spot (NLI+grammar catch 0/5); contextual_fit
scores factual/logical reversals ~40× higher than CLEAN substitutions at
the median — actively counter-indicative for that class, not just weak.
**Labeled as:** sufficiency is (C) leaning (B) — enough for baseline
comparison, not enough to train or trustworthily evaluate a validator on
the two blind-spot classes. A dedicated labeling pass (~40-60 more unique
examples per thin class) is the evidenced next step before Phase 4
(validator prototyping), not training on what exists today.

### R50 Phase 8. Building the missing human-labeled dataset — **DONE, 2026-08-24**
**Linked finding:** direct instruction, following the user's Phase 8
proposal — R50 found a data-scarcity problem, not another signal
question; collect deliberate new evidence rather than re-mining
R40–R50. Full record: `VALIDATION.md` §41, `eval/r50p8_report.md`.
**What was done:** 54 new real sentences (5 Wikipedia topics never used
before: photosynthesis, solar system, exercise, industrial revolution,
internet) run through today's live `reformulate()` across R40's 4
profiles — R40's own methodology, new material — yielding 68 unique
cases, blind-labeled from text alone. Supplemented with 50 disclosed
non-blind constructed examples (20 FACTUAL_OR_LOGICAL_REVERSAL, 20
FIXED_TERM_OR_IDIOM, 10 hard-CLEAN controls). A second, independent
subagent rater checked a 33-case stratified sample blind to the primary
rater's labels; a separate, frozen Phase 8 split was created alongside
R50's own (both untouched).
**Result:** 116 new independent records. Combined unique-case counts:
FACTUAL_OR_LOGICAL_REVERSAL 7→28 (organic yield only 1/68 — this class
is almost entirely constructed evidence), FIXED_TERM_OR_IDIOM 8→41
(organic yield 13/68 — well above the ~8% estimate, these topics are
dense with fixed technical terms the engine keeps breaking). Second-rater
agreement: 88% acceptability, 70% primary defect type overall, but only
25%/33% on GRAMMAR/NATURALNESS_OR_REGISTER — a real taxonomy-boundary
problem, plus a separate labeling-convention confound (per-word-isolation
vs. whole-sentence judgment) identified independently.
**Labeled as:** sufficiency is (B) — a learnable signal clearly exists
(88% acceptability agreement, 100% on two classes), but
FACTUAL_OR_LOGICAL_REVERSAL needs more organic (not constructed)
examples specifically, three classes' boundaries need refinement or a
coarser evaluation axis, and the labeling convention needs reconciling
before validator training can proceed. No training performed.

### R50 Phase 8B. Targeted finalization — final GO/NO-GO decision — **DONE, 2026-08-24**
**Linked finding:** direct instruction to resolve Phase 8's three named
blockers specifically and decide, not run another broad collection
cycle. Full record: `VALIDATION.md` §42, `eval/r50p8b_report.md`.
**What was done:** targeted organic harvest on 4 causal-dense topics
(vaccine, plate tectonics, antimicrobial resistance, supply and demand);
taxonomy reconciliation via a strict 3-step decision procedure tested by
an independent rater; the isolation-vs-whole-sentence labeling
convention resolved and applied retroactively to both R50 and Phase 8;
every record tagged with evidence quality (ORGANIC_OBSERVED/CONSTRUCTED/
HUMAN_REVIEW_OF_EXISTING_CASE).
**Result:** organic FACTUAL_OR_LOGICAL_REVERSAL yield rose ~6× (1/68→
9/58 records) via topic-targeting alone. GRAMMAR/WRONG_WORD_OR_SENSE
agreement improved substantially with the refined procedure (25%→56%,
67%→78%); NATURALNESS_OR_REGISTER did not improve at all (33%→33%) and
was retired as a primary label. 12+6 records corrected under the
resolved convention. Final unique-case counts: FIXED_TERM_OR_IDIOM 53
(62% non-constructed, past target), FACTUAL_OR_LOGICAL_REVERSAL 33
(organic 6, still 61% constructed, short of target).
**Labeled as: GO, scoped per class** — WRONG_WORD_OR_SENSE,
FIXED_TERM_OR_IDIOM, GRAMMAR, and CLEAN/acceptability are sufficient to
proceed to a validator prototype now; FACTUAL_OR_LOGICAL_REVERSAL
proceeds too but any reported performance on it must be labeled
directional/low-confidence pending more organic evidence. A decision,
not a deferral — no further data-collection phase follows automatically.

### Phase 9. Learned validator prototype — training run diverged — **DONE (negative result), 2026-08-25**
**Linked finding:** direct instruction, following the Phase 9 proposal —
build a small cross-encoder ACCEPT/REJECT validator prototype (research
only, not production integration). Full record: `VALIDATION.md` §43,
`eval/r9_report.md`.
**What was done:** assembled the final dataset (313 records, 252 unique
groups) and a unified leakage-safe split respecting R50's/Phase 8's
frozen test assignments; computed existing-signal baselines fresh on the
test set; fine-tuned `microsoft/deberta-v3-xsmall` as a binary
ACCEPT/REJECT cross-encoder with pos_weight≈11 for the 17:188
CLEAN:DEFECTIVE train imbalance; ran the full planned evaluation
(threshold sweep, unseen-word-pair generalization check,
evidence-quality-stratified factual-reversal breakdown).
**Result:** dataset/split/baselines all completed correctly — best
simple combined rule (SBERT<0.95 OR NLI OR grammar) gets 60% DEFECTIVE
recall / 90% precision / 63% CLEAN recall, the real floor to beat. The
fine-tuning run diverged (grad_norm → nan at epoch 3.08, after a
warning-sign spike at epoch 2.69); the saved model is confirmed 100%
NaN weights. The evaluation output numerically matched the
reject-everything baseline only by coincidence of `nan >= threshold`
semantics, not as a real result. None of the three gate questions
(generalize? beat baseline? precision/coverage tradeoff?) were answered.
**Labeled as:** a genuine negative result of this specific
hyperparameter configuration, reported in full rather than re-run or
concealed, per direct instruction not to alter the experiment. A
root-caused fix (lower learning rate, explicit gradient clipping, a
less extreme imbalance correction, early stopping) is recommended for a
future attempt but was not executed — that decision is left to the
user.

### Phase 9B. Training instability fixed, controlled retry succeeded — **DONE, 2026-08-25**
**Linked finding:** direct instruction — diagnose R9's NaN failure
precisely, retrain with a conservative config, sanity-check before the
full run, evaluate against the unchanged baseline/dataset/split. Full
record: `VALIDATION.md` §44, `eval/r9b_report.md`.
**What was done:** confirmed R9's own "missing gradient clipping"
hypothesis was wrong (clipping and fp32 were already active by
default) and revised it to pos_weight~11 + lr=2e-5 + a too-small
adam_epsilon destabilizing DeBERTa within ~3 epochs. Retrained with
lr=3e-6, pos_weight=4.0 (capped), explicit clipping, adam_epsilon=1e-6,
early stopping, and a new abort-on-non-finite safety callback — same
dataset/split as R9, unchanged. A 10-step sanity pass confirmed
stability before the full run.
**Result:** full 8-epoch run completed with zero non-finite events
(confirmed: 0 NaN/0 Inf across 70.8M parameters), best eval_loss 0.676
at epoch 6. Caught and fixed two evaluation bugs before reporting (a
too-coarse threshold grid that missed the model's real narrow output
range, and an initial threshold selected via test-set leakage). On the
frozen, unchanged test set: val-selected threshold gets defect recall
0.77 vs baseline's 0.60, precision 0.92 vs 0.90, clean recall 0.62 vs
0.62 tied; a more conservative threshold beats baseline on all three
simultaneously.
**Labeled as:** justifies further development, directionally, on real
evidence — not a production-ready result. Small test set (51 records, 8
CLEAN), poor score calibration despite real ranking signal, single
run/seed. A second independent training run is the sensible next step,
not performed automatically.

### Phase 9C. Independent replication (seed change only) — **DONE, 2026-08-25**
**Linked finding:** direct instruction — re-run 9B's exact pipeline with
only the seed changed, to test reproducibility. Full record:
`VALIDATION.md` §45.
**Result:** conservative threshold's recall is identical across seeds
(0.65, both beating baseline on all three metrics). The aggressive
threshold-selection method is NOT robust — healthy in 9B, but
clean_recall crashed to 0.38 (below baseline) in 9C, traced to a tiny
6-example validation CLEAN sample. Ranking stability measured directly:
Spearman ρ=0.90, Pearson r=0.92 (p<0.0001) — the underlying signal is
consistent across seeds even where calibration isn't.
**Labeled as:** 9B's core finding replicates at the conservative
threshold; the 77-91% recall headline numbers were partly
threshold-selection luck and should not be quoted as representative.
~65% recall is the honest, reproducible number.

### Phase 10. Broad stratified stress test of the current architecture — **DONE, 2026-08-26**
**Linked finding:** direct instruction (approved plan) — a deliberately
wide, stratified, difficulty-graded evaluation of the current
architecture across ordinary and technical language, disjoint from
every prior corpus, plus a Phase 9B/9C validator generalization test.
Full record: `VALIDATION.md` §46, `eval/r10_report.md`.
**What was done:** froze 133 new sentences (0 contamination against
154 prior sentences), froze 398 (sentence,profile) runs, harvested via
live production `reformulate()`, blind-judged all 238 reformulated
outputs via 5 parallel subagents (no domain/category/difficulty
shown), ran the frozen Phase 9B/9C checkpoints unmodified on the same
new material.
**Result:** 26% CLEAN / 74% DEFECTIVE overall. Domain only a 6-point
gap (general 71% vs technical 77% defective) — content density
(terminology, length) predicts failure far better than subject-matter
label; chemistry/engineering/narrative all 0% CLEAN, math/stats 83%
CLEAN. Difficulty gradient not smooth — moderate (18% CLEAN) scored
worse than hard (30%). Profile constraint density is the cleanest
predictor: multi_word profiles 0% CLEAN (0/13). Escalation ties
substitution on quality (26-27% CLEAN), not a rescue mechanism.
Neither validator checkpoint generalizes cleanly: 9C predicts
DEFECTIVE 99% of the time (non-functional), 9B's CLEAN retention
collapsed 62%→34% on new material despite higher recall.
**Labeled as:** confirms the architecture's real failure predictors
(density/length/constraint-count, not domain label) and directly
answers Phase 9B/9C's own generalization question — partially yes for
9B, no for 9C. Evaluation only, no production changes, no training.

### Phase 10B. Detailed failure analysis — architecture-vs-custom-model evidence — **DONE, 2026-08-26**
**Linked finding:** direct instruction — diagnose exactly what
generation capability is missing across Phase 10's 176 DEFECTIVE
outputs, separated into fixable-now / needs-new-mechanism / needs-
custom-model, to ground the architecture-vs-custom-model decision in
evidence rather than jumping straight to training something huge. Full
record: `VALIDATION.md` §47, `eval/r10b_failure_analysis.md`.
**What was done:** all 176 defects re-examined with full mechanism
context (not blind — a different task from acceptability judging) by 4
independent subagents against the same three-bucket definitions.
**Result: 162/176 (92%) fixable within current architecture, 12/176
(7%) needs a new but still non-learned mechanism, 2/176 (1%) potentially
needs a custom trained model.** GRAMMAR and FIXED_TERM_OR_IDIOM are
100% rule-fixable; FACTUAL_OR_LOGICAL_REVERSAL (the class treated as
most dangerous throughout this project) is 85% rule-fixable. The
needs-new-mechanism bucket is exactly three recurring, still-engineerable
patterns (cross-substitution coherence checking, a pre-ranking WSD
gate, a restructuring content-coverage check). Both custom-model cases
are escalation-tier chemistry-domain causal/state reasoning failures
specifically, not general fluency problems.
**Labeled as:** decisive evidence against building a custom trained
model now. Staged path: rule/blocklist fixes for the 92%, three new
engineered mechanisms for the 7%, and only then reconsider a
custom-trained component for the narrow surviving 1% (escalation-tier
technical-domain causal claims). No fixes implemented — decision left
to the user.

### Phase 11. Implement categories 1-3 of the "92% fixable" batch — **DONE, 2026-08-27**
**Linked finding:** Phase 10B's fixable batch, planned via plan mode
(first draft rejected with load-bearing feedback demanding per-instance
verification, not bulk-copying) then implemented. Full record:
`VALIDATION.md` §48, `eval/r11_targeted_rerun.py`.
**What was done:** (1) expanded `semantic.py`'s fixed-term protection
list and — a gap found during implementation, not in the original plan
— extended its enforcement to escalation-tier T5 output, not just
substitution-tier candidate generation; (2) a duplicate-word-in-sentence
rejection check in `_try_substitution()`; (3) a 52-pair bad-pair
blocklist, each pair individually re-verified against its named Phase
10 `run_id`, catching two real bugs in the process (4 pairs stored in
the wrong grammatical form; the blocklist needed to normalize
Datamuse-sourced candidates that arrive unlemmatized).
**Result:** all tests pass, `smoke.py` byte-identical to both
baselines. Targeted re-run of the 83 specific R10 cases these
categories target: 77/83 (93%) no longer reproduce their original
defect. The remaining 6 are a known, named gap — 4 are duplicate-word
defects introduced by escalation-tier restructuring (out of this pass's
approved scope, which covered substitution-tier only) and 2 are a
number-agreement grammar defect (Category 4).
**Labeled as:** first implementation pass since Phase 10B's diagnosis;
"no longer reproduces the old defect" is a narrower claim than "now
CLEAN" (no re-judging was performed). Categories 4-7 (~87 cases: POS
agreement, antonym/polarity gaps, number/scope preservation, escalation
dictionary validation) remain for a follow-up "Phase 11B", now with the
escalation-tier duplicate-word extension added to that scope as a
concrete, evidenced item rather than a new discovery.

### Phase 11 re-verification. Blind re-judging + a regression found and fixed — **DONE, 2026-08-27**
**Linked finding:** closes Phase 11's own disclosed limitation (no
blind re-judging had been done). Full record: `VALIDATION.md` §49,
`eval/r11_reverify_report.md`.
**What was done:** re-ran the full 398-run Phase 10 corpus through
production `reformulate()`, diffed against the frozen Phase 10 results,
blind-judged every changed run (4 parallel subagents, same discipline
as Phase 10). The first pass found 3 regressions, traced to
`IDIOM_PHRASES` being consumed by a third free-text path
(`_try_phrase_replacement()`) that Phase 11 hadn't gated, plus two
entries ("small intestine"/"large intestine") that were never actually
verified against a real failure. Both fixed and the full 398-run
harvest re-run from the corrected code before any number was finalized.
**Result:** 92/398 runs changed; of 83 still `reformulated`, 15 CLEAN /
68 DEFECTIVE. Against Phase 10's original judgment: 15 genuine fixes, 2
regressions (both a pre-existing, unrelated Category-4 gap surfaced by
known candidate-ranking nondeterminism, not caused by Phase 11). 9
changed runs now safely refuse instead of shipping a defect. **Overall
CLEAN rate among all reformulated runs: 75/230 (32.6%), up from Phase
10's 26.1%.**
**Labeled as:** the actual, blind-judged confirmation that Phase 11
helped, not an inference from "the old defect text is gone." Phase 11B
(Categories 4-7, ~87 cases, still WRONG_WORD_OR_SENSE-dominated per this
pass's own breakdown) remains the next concrete step.

### Phase 11B. Categories 4/6/7 — plus three real bugs caught during verification — **DONE, 2026-08-27**
**Linked finding:** the highest-confidence slice of Phase 10B's
remaining categories, per plan-mode approval. Full record:
`VALIDATION.md` §50, `eval/r11b_reverify_report.md`.
**What was done:** implemented dictionary/real-word validation on
generated output (Category 7), a generalizable number-word
preservation check (Category 6, narrow slice), and five more verified
blocklist pairs (Category 4/5 simple cases). Explicitly deferred:
general POS/subject-verb-agreement checking on T5 output and
antonym/polarity-without-negation-marker detection (both need a new
mechanism, not a rule fix). This phase's own re-harvesting caught and
fixed 3 real bugs before reporting any number: an overly aggressive
dictionary check that regressed 2 previously-CLEAN outputs (fixed by
requiring both pyspellchecker AND exact WordNet membership to fail); a
number-word set that missed digit/hyphenated forms; and a genuine
root-cause bug in `grammar.inflect()`'s pluralization fallback
double-"s"-ing an already-plural candidate ("weekdays" -> "dayss").
Also found, and left as a disclosed limitation rather than chased: two
words ("third", "single") whose candidate pools keep producing a new
bad match every time the previous one is blocked — a concrete ceiling
on the blocklist approach.
**Result:** 111/398 runs changed; of 97 still `reformulated`, 17 CLEAN
/ 80 DEFECTIVE. 17 genuine fixes, 8 apparent regressions all traced to
this project's pre-existing candidate-pool/T5 nondeterminism (none
touch this phase's own code). **Overall CLEAN rate: 71/225 (31.6%)**,
up from Phase 10's 26.1%, flat against Phase 11's 32.6% — within a
newly-confirmed ~1-point noise band from re-running an unchanged
harvest.
**Labeled as:** the still-DEFECTIVE population's shape (WRONG_WORD_OR_
SENSE 42, GRAMMAR 11 dominant) confirms rather than surfaces new scope
— the explicitly-deferred categories (T5-output grammar checking,
polarity-without-negation detection) are the correct next lever, a
candidate "Phase 11C," each needing its own design pass before
implementation (same caution this phase itself applied to Category 4).

### Phase 11C. Research pass, then porting R45/R46's NLI+grammar validator + two new mechanisms — **DONE, 2026-08-27**
**Linked finding:** a research/design-only plan-mode pass (no code, no
evaluation) first, per explicit instruction, re-examining the remaining
Categories 4/5/6/7 evidence and the actual codebase. Full record:
`VALIDATION.md` §51, `eval/r11c_reverify_report.md`.
**Central finding:** two of the four needed mechanisms already existed
— R45/R46 built and validated an NLI entailment gate and a LanguageTool
grammar gate, both already downloaded/cached, gating only in the
experimental `_try_escalation_v3()`/`reformulate_v2()` path (opt-in
toggle, never production). This phase ported both into production, and
built two new mechanisms: an escalation-tier duplicate-word check
(closing a gap named after Phase 11 but dropped before Phase 11B) and a
small curated countability/mass-noun set.
**Self-caught, before any number reported:** the duplicate-word check's
first version would have rejected nearly every legitimate paraphrase
(caught by the existing test suite); a WSD test failure once the new
NLI gate was added turned out to be the gate correctly catching a real
defect the test never actually verified, not a false positive — the
test was rewritten to check the right thing. Also measured (not
assumed) a real tradeoff the plan anticipated: the substitution-tier
NLI check has a genuine precision cost (7/102 previously-CLEAN cases
now refuse) alongside a confirmed true positive (R10-005's reversal
correctly caught).
**Result:** 147/398 runs changed; of 102 still `reformulated`, 21 CLEAN
/ 81 DEFECTIVE. 21 genuine fixes, 10 regressions all individually
traced to pre-existing candidate-pool nondeterminism (none caused by
this phase's gates). **Overall CLEAN rate: 66/194 (34.0%)**, up from
Phase 10's 26.1% and Phase 11B's 31.6% — clears the ~1-point re-harvest
noise band Phase 11B established, a real improvement.
**Labeled as:** still-DEFECTIVE population stays WRONG_WORD_OR_SENSE-
dominated (46/70) — confirms this class needs candidate-pool-level
word-sense disambiguation, a fundamentally different kind of mechanism
than any post-generation gate built across Phases 11/11B/11C. The
substitution-tier NLI check's precision cost is a legitimate open
question for a future refinement pass, not resolved here. `R10-024`'s
same-word-different-replacement pattern is newly named as a distinct
defect shape for a future phase.

### Architecture Go/No-Go, Step 1. Ported R45's phoneme-aware decoding-time constraint — **DONE, 2026-08-27**
**Linked finding:** per an explicit user proposal to stop the open-ended
rule-addition pattern and give the architecture one final opportunity
before a formal Go/No-Go decision (agreed 4-step plan: port the
generation-side fix → diagnose remaining failures → formal architecture
assessment → a genuine 3-way decision, including retiring the
approach). This is Step 1 only — **not itself a verdict**, per explicit
agreement not to judge the architecture question on one number. Full
record: `VALIDATION.md` §52, `eval/arch_gate1_report.md`.
**What was done:** ported the largest measured improvement in this
project's history — R45/R46's phoneme-aware decoding-time constraint,
previously stuck behind an experimental opt-in toggle — into production
`_try_escalation()`, exactly as built, no redesign. Self-caught a real
pre-existing test bug from Phase 11C's own verification gap (never ran
`reformulate_v2_test.py` last phase) before reporting any number.
**Result, deliberately mixed, not spun either way:** 16/42 hardest
previously-stuck cases now produce a candidate (38%, smaller than R45's
original ~52% because of the much stricter validator stack added
since). Full harvest: 14 refused→reformulated (vs. 1 in every prior
phase). CLEAN rate 68/218 (31.2%), DOWN from Phase 11C's 34.0% despite
absolute CLEAN count rising — coverage rose substantially but most
newly-covered cases landed DEFECTIVE, confirming R45's own prediction
that the validation side (now actually installed) still can't catch
WRONG_WORD_OR_SENSE, the dominant remaining defect. Cost measured for
the first time ever in this project: +3% total harvest latency.
**Labeled as:** evidence for Step 2 (is the right word absent from the
candidate pool, or just ranked wrong?) and Step 3 (the formal
architecture assessment) — the natural next step, not decided here.

### Architecture Go/No-Go, Step 2. Is WRONG_WORD_OR_SENSE a generation problem or a ranking problem? — **DONE, 2026-08-27**
**Linked finding:** the exact question the agreed 4-step plan asked
for Step 2. Analysis only, no production code changed. Full record:
`VALIDATION.md` §53, `eval/step2_wrong_sense_report.md`.
**What was done:** all 88 currently-DEFECTIVE WRONG_WORD_OR_SENSE runs
re-instrumented to expose the full candidate pool actually considered
(not just the winner), classified with full context by 4 independent
subagents into absent-from-pool / present-but-misranked / no-good-
option-possible / other. Self-caught and fixed a diagnostic-tooling bug
(19/24 restructuring cases crashed on a dead code line) before any
number was reported.
**Result: 71% of these defects (70/98 classifications) are
PRESENT_BUT_MISRANKED** — a correct or better candidate was already in
the pipeline's own pool, ~57 of those already within production's own
top_k/k window. Only 20% are genuine resource/generation gaps
(ABSENT_FROM_POOL), 5% are genuinely unsolvable (NO_GOOD_OPTION_
POSSIBLE). A specific, mechanistically confirmed cause was traced for
several cases: `combined_score()`'s documented 90%-semantic/10%-
frequency blend measurably favors a more common but less meaning-
preserving word over a less common but more accurate one when their
raw SBERT similarity is close — verified directly against real
combined_score() output, not inferred. Per Practice.md's standing rule,
the weighting itself is flagged as evidence for a future, separate,
explicit decision, not changed here.
**Labeled as:** if Step 3 concludes a learned component is warranted,
this evidence points specifically at a learned reranker/scorer, not a
bigger candidate generator — generation is demonstrably not the
bottleneck for 71% of this defect class. Any such component still
needs to clear the Phase 9B/9C generalization bar before being
trusted.

### Architecture Go/No-Go, Step 3 prep. Generalization check on a fresh corpus — **DONE, 2026-08-27/28**
**Linked finding:** closes a gap flagged while scoping Step 3 — every
evaluation since Phase 10 re-verified the same frozen R10 corpus, none
of it evidence about unseen material. Full record: `VALIDATION.md` §54.
**What was done:** built and harvested an 18-sentence/36-run corpus
genuinely new to this project (10 technical from 5 never-used Wikipedia
topics, 8 hand-authored general sentences) through unchanged production
`reformulate()`; blind-judged the 28 reformulated outputs with the
standard no-metadata rubric.
**Result: CLEAN rate 6/28 (21.4%)** — roughly 10 points below every
R10-corpus figure this architecture has produced across Phases 11
through Architecture Gate Step 1 (26.1%→32.6%→31.6%→34.0%→31.2%), well
outside the ~1-2 point established noise band. Gap concentrates exactly
where prior steps predicted: `dense_mixed` profiles scored **0/10
CLEAN**; WRONG_WORD_OR_SENSE remains the dominant defect (12/22).
Reading (not a verdict): a meaningful share of the R10-corpus gains
looks like fitting to that corpus's specific, well-studied failure
modes rather than a generalizable improvement — direct evidence for
Step 3's "generalization to unseen material" criterion.

### Architecture Go/No-Go, Step 3 (formal assessment) + Step 4 (recommendation) — **DONE, 2026-08-28, recommendation pending user ratification**
**Linked finding:** the culmination of this entire arc. Full record:
`VALIDATION.md` §55, `eval/step3_architecture_assessment.md`, `eval/
step4_recommendation.md`.
**What was done:** synthesized all evidence from Phase 10 through the
Step 3 generalization check against the 8 named criteria. Disclosed
honestly that concrete numeric pass/fail thresholds were never actually
pre-registered as an artifact, only the criteria themselves.
**Result:** CLEAN rate plateaued 31-34% on the tuned R10 corpus across
three phases of real fixes after Phase 11's initial jump; dense/
multi-constraint profiles score 0% CLEAN on both the ORIGINAL frozen
corpus (Phase 10, before any fix) and a completely FRESH corpus (after
every fix) — the identical failure mode, unmoved across the whole arc;
fresh-material CLEAN rate (21.4%) sits ~10-13 points below every
frozen-corpus figure, outside the established noise band; the dominant
defect (WRONG_WORD_OR_SENSE, per Step 2 a ranking problem) is untouched
by every mechanism added across Phases 11 through Architecture Gate 1.
**Recommendation (awaiting ratification): Option C** — freeze the
current architecture as the maintained/shipped state, do not pursue a
learned reranker. Reasoning: Option A isn't supported by the quality
evidence; against Option B, this project's own Phase 9B/9C precedent
(a prior learned component failing 99% of the time on held-out data)
plus this exact fresh-corpus check (the current, simpler, more
inspectable system already failing an equivalent generalization test)
give specific reason to doubt a learned component built the way this
project would build one would fare any better. Not a permanent ban.

---

## Architecture Go/No-Go, Step 4 — RATIFIED: Option C, freeze — **DONE, 2026-08-28**
**Linked finding:** `VALIDATION.md` §56, `DECISION_LOG.md`
2026-08-28-I. The user explicitly ratified the Step 4 recommendation
(`eval/step4_recommendation.md`): freeze the current architecture as
the maintained/shipped baseline, no further optimization. See the
freeze banner at the top of this document for the full terms and
reopening conditions. This closes the Architecture Go/No-Go arc begun
2026-08-27. The Architecture Go/No-Go arc's own remaining "candidate
next steps" (e.g. a learned reranker, narrowing the substitution-tier
NLI check's precision cost, the `"third"`/`"single"` unconverged-pool
gap, `combined_score()`'s weighting) are retained below as historical/
candidate material for a future re-opening under the conditions stated
in the freeze banner — not active roadmap items.

---

## Lower priority / hypotheses proposed by this review (§4-style — explicitly unvalidated)

These are **not** findings. Per Practice.md §4, they are proposed here
with a brief rationale precisely so they're legible as hypotheses, not
smuggled in as decisions:

### H1 (hypothesis). `st.iframe` in `voice.py` may not be a valid Streamlit API call
**Status update (Stage 2, 2026-08-15):** `voice.py` moved to
`out_of_scope/voice.py` — it's no longer part of this repository's live app
(see `out_of_scope/README.md`). This item stays on the record as-is because
the code itself wasn't touched, just relocated; it becomes relevant again
only if/when someone builds the separate Audio Module from this starting
point, not for further work in this repo.
**Rationale:** No documented Streamlit API by that exact name was found
during the original review's reading of `voice.py` against the pinned
`streamlit>=1.58.0` requirement; the conventional call is
`st.components.v1.iframe`/`.html`. This is a plausible bug, not a
confirmed one — that review did not execute the app.
**Cheapest test:** Run the app and exercise the voice-input/voice-output
UI paths; if `st.iframe` raises, this graduates from hypothesis to a
confirmed bug with a one-line fix.

### H2 (hypothesis). README's documentation drift is symptomatic of a missing "docs stay in sync" check
**Rationale:** Two independent drift instances were found in one review
pass (`DECISION_LOG.md` 2026-06-08-C on the semantic-scoring numbers, and
`AUTH_README.md`'s incorrect `.gitignore` claim underlying R0). Finding
two independent instances without looking hard for them is weak but
nonzero evidence that this is a pattern, not a one-off.
**Cheapest test:** Not a technical experiment — a process change (e.g. a
lightweight doc-vs-code consistency check before merging user-facing
changes) would be the test of whether this recurs. Filed as a hypothesis
about process, not about the rewrite pipeline itself, since Practice.md's
methodology is explicit that process failures are exactly as worth
recording as technical ones.

---

## Roadmap-blind reassessment log (§15)

Per §15, this reassessment should be repeated periodically, not only
once. This entry is the first one, performed as part of this review.

**2026-08-08 — first reassessment.** Asked, from the stated research
objective alone (Practice.md §1) and without reference to README's
existing "Roadmap" section: what is the highest-leverage next step?
Answer produced independently: closing the gap named in §12 — confirming
whether *anything* shipped so far has been checked against a real,
non-proxy outcome. That answer matches R2/R3/R4 above, which were derived
the same way, and does **not** match README's own stated near-term
roadmap (Datamuse POS filtering, a revert button, sentence-level
phoneme scoring, multi-sentence input, blocklist/allowlist persistence,
export/copy button) — those items are real and reasonable but are
product-polish items on the "hard" pipeline, not items that would tell
this project whether its core research claim (rewrites get easier to say
*and* stay faithful to meaning) is actually true. Recorded here as the
comparison §15 asks for, not as an argument that README's roadmap is
wrong — product polish and research validation are not mutually
exclusive, and prioritizing between them is a decision this document does
not make on its own.

**2026-08-15 — second reassessment, post-literature-pass.** Asked the same
question again, now with `RESEARCH.md` available: what is the
highest-leverage next step? Answer: **R6** (the A-vs-B ablation, widened
this pass) moved up in practical urgency, because the research pass supplied
a *reason to expect* consolidation is right (§6's complementary-failure-
modes argument) where previously R5 only had "this is duplicated code" as
its justification — evidence-strength changed, not just item count. R10
(the restructuring-escalation path) is new since the last reassessment and
answers the same kind of question R2/R3/R4 were chasing: not "is the
current system polished" but "does the current system actually have the
capability the research objective claims" — and per `RESEARCH.md` §7, the
honest answer today is that it doesn't, for a real subset of cases. Recorded
here as the comparison §15 asks for; this does not reorder R0–R4 (the
credential exposure and the still-unresolved threshold/data/study gaps are
unaffected by the literature pass and remain ahead of R6/R10 in practical
terms).

**2026-08-15 — third reassessment, post-Stage-4A.** Building the profile
foundation surfaced one new structural fact worth recording here rather than
only in R12: the repository now has two independent representations of
"what's difficult for this speaker" (the new, user-declared
`DifficultyProfile` and the old, learned `SpeakerDifficultyProfile`), and
neither R5/R6 (the A-vs-B rewrite-pipeline ablation) nor R2 (fitting the
difficulty formula) can be answered completely without first deciding how
those two profiles relate (R12) — an ablation or a formula fit run against
only one of two now-existing difficulty signals would be answering a
narrower question than it appears to. This doesn't change R0–R4's priority
ordering; it means R12 should be resolved before, or alongside, R5/R6/R2
rather than strictly after them as the numbering alone would suggest.

**2026-08-16 — fourth reassessment, post-Stage-4A-refinement.** R0's
practical urgency dropped for *new* activity (no auth layer left to leak
credentials from) but stays open in the log because historical git
exposure is unchanged — recorded as a status update on R0 itself rather
than a reordering. R12 is now sharper, not new: three difficulty
granularities (learned continuous, declared global, declared word-specific)
exist where the last reassessment counted two. No item moved priority tier
as a result of this pass — the highest-leverage next step remains the same
one two reassessments ago: closing the proxy-metric gap (R2/R3/R4) and
running the pipeline ablation (R6/R12) before any reformulation redesign
decision is made, now with a slightly richer input layer to design that
redesign against.

**2026-08-16 — fifth reassessment, post-Stage-5 (`REFORMULATION_RESEARCH.md`).**
The deep reformulation-engine research pass answers this reassessment's
question directly rather than needing a fresh derivation: it independently
re-arrives at "close the proxy-metric gap and run the ablation first"
(§22's priority order opens with R6, then R11, then R8, then R2's
position/stress terms) via a completely different route (constructing and
walking through ten failure-mode examples, §17) than the earlier
reassessments used. Two items' priority *character* changed, not their
tier: R6 is no longer just "duplication is real," it's "duplication with a
literature-grounded reason to expect a specific outcome" (§12's
complementary-failure-modes test, applied); R10 is no longer just "we
should probably support restructuring," it's "the one constructed failure
mode our architecture cannot solve without it" (§17, the restructuring-vs-
substitution case). R0's status is unchanged from the fourth reassessment.
No item was reordered as a result of this pass — the research confirmed
the existing order rather than revising it, which is itself worth
recording per §15 rather than treated as a null result.

**2026-08-16 — sixth reassessment, post-Stage-5B critical review.** The
implementation-readiness checkpoint (`REFORMULATION_RESEARCH.md` §24–31,
`DECISION_LOG.md` 2026-08-16-D) sharpened R6/R8/R9/R10/R11 into a concrete
MVP/Strong/Future split with an exact order (§27 of that document):
consolidate the two pipelines (R6) → naturalness metric (R11) → tiered
antonym-check-first semantic verification (R8, now staged rather than
flat) → count-threshold escalation trigger and T5 role change (R10) →
position/stress logged as metadata, not scored (a correction to this
review's own earlier framing of R2/R3's update). This is the most
implementation-specific this roadmap has been to date; the next entry here
should be a status update on R6 actually running, not another
reassessment — repeated reassessment without new implementation activity
in between would stop being useful per §15's own intent.
