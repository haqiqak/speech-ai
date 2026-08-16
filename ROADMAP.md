# ROADMAP.md — Forward-looking priority list

Per Practice.md §15: one list, priority order, each item linked to the
specific finding or gap that justifies it. Proposed-but-unvalidated
directions are labeled as exactly that, not written with the confidence
of an item a completed finding already justifies. Per §0.2 of Practice.md,
**this document does not authorize starting any of these** — it is a
prioritized list produced by §19 steps 1–8; step 9 (actually doing the
work) is a separate, deliberate decision outside the scope of this pass.

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

### R6. Ablation: does the phoneme-onset gate change accepted candidates, and does Pipeline A or B produce better output?
**Linked finding:** Practice.md §11, applied directly — named as a
Speech-AI-shaped candidate ablation once a benchmark exists. Scope widened
slightly during the Stage 3 research pass to explicitly include the A-vs-B
comparison R5 is blocked on, since both are the same class of question
(does this specific gating/scoring choice change what gets accepted).
**Labeled as:** Future work, blocked on R1–R4 producing a usable benchmark
first.

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

### R11. Design a "naturalness of intervention" metric
**Linked finding:** `RESEARCH.md` §4 — none of our current metrics, and
none found in the literature search, cleanly distinguish "this edit was
necessary" from "this edit was correct." `substitution_rate` (already
computed) is the closest existing proxy and conflates the two.
**Labeled as:** Open evaluation-methodology gap, future work — no
literature answer found, flagged as a genuine open question in
`RESEARCH.md` §9 rather than assigned a false solution.

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
