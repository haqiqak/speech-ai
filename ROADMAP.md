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
**Status:** Documented, not remediated (per §19's scope for this pass).

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

### R3. Run the literature pass called for in §7
**Linked finding:** `VALIDATION.md` §5 — this review did not perform it.
**What this roadmap item actually is:** A dedicated literature review
(speech-language pathology, lexical-substitution/paraphrase NLP,
stutter-therapy/AAC research, readability/simplification literature),
written as its own document per §7's format, addressing specifically
whether fixed onset-matching is the right primary signal.
**Labeled as:** Directly named by Practice.md itself as a concrete,
overdue gap — not a hypothesis this review is proposing, but a
prerequisite the methodology already flags.

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
The actual next step is R11 below (an ablation comparing the two paths on
the same objective), and only once that comparison exists does a
consolidation decision have evidence behind it. Filed here as the
maintenance-risk observation that motivates running that comparison sooner
rather than later, not as a pre-decided outcome.
**Labeled as:** Observation (duplication is real and confirmed by reading
both code paths) driving a **future** evidence-gathering step, not an
implementation decision.

### R6. Ablation: does the phoneme-onset gate change accepted candidates?
**Linked finding:** Practice.md §11, applied directly — named as a
Speech-AI-shaped candidate ablation once a benchmark exists.
**Labeled as:** Future work, blocked on R1–R4 producing a usable benchmark
first.

### R7. Ablation: is the frequency term in the ranking formula doing real work?
**Linked finding:** Practice.md §11, same source as R6.
**Labeled as:** Future work, same blocking condition as R6.

---

## Lower priority / hypotheses proposed by this review (§4-style — explicitly unvalidated)

These are **not** findings. Per Practice.md §4, they are proposed here
with a brief rationale precisely so they're legible as hypotheses, not
smuggled in as decisions:

### H1 (hypothesis). `st.iframe` in `voice.py` may not be a valid Streamlit API call
**Rationale:** No documented Streamlit API by that exact name was found
during this review's reading of `voice.py` against the pinned
`streamlit>=1.58.0` requirement; the conventional call is
`st.components.v1.iframe`/`.html`. This is a plausible bug, not a
confirmed one — this review did not execute the app.
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
