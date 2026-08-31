# LEARNED_REFORMULATION_RESEARCH.md — Stage LR charter

**Status: charter only. No research has started.** Per Practice.md §0.2 /
`ROADMAP.md`'s own header discipline, a charter names a direction and its
evaluation bar — it does not authorize starting the work. That is a
separate, later decision.

## Name

**Stage LR — Learned Reformulation.** "LR" is short for *Learned
Reformulation* — this stage's whole subject: replacing or supplementing
part of the frozen rule/gate pipeline with a learned component. Named
this way instead of a number by direct instruction (2026-08-30, see
`DECISION_LOG.md` 2026-08-30-C) because the earlier candidate number,
"Stage 8," was accurate but harder to say/remember than what it stood
for. It still sits after this project's existing numbered stages
(Stage 2 scope narrowing, Stage 3 `RESEARCH.md`, Stage 4A the
difficulty profile, Stage 5 `REFORMULATION_RESEARCH.md`, Stage 6 the
`reformulate.py` evaluation, Stage 7 the human pilot — see
`DOCS.md`/`HANDOFF.md`) and does not reuse "Stage 5," which already
names a different, existing document — the letter name just replaces
"8" as the label for that same slot.

## What this is

The reformulation architecture frozen in `VALIDATION.md` §56
(`architecture-freeze-v1`, commit `7451ec4`) plateaued at 31-34% CLEAN
on its own tuning corpus and 21.4% on a fresh one, with the dominant
defect class (WRONG_WORD_OR_SENSE) diagnosed as structurally a
*ranking* problem (§53) — not something any further hand-written gate
touches. Stage LR is the space for exploring a genuinely different,
likely learned, approach to that ranking problem — e.g. the reranker
direction named and set aside in §55's Option B.

`VALIDATION.md` §57 records the external framing this charter is a
direct response to: this project's own arc is a small-scale instance of
the pattern Rich Sutton's "The Bitter Lesson" describes (hand-engineered
rules plateauing on a problem shape general/learned methods are
typically better suited to) — with the caveat, also recorded there, that
the essay's mechanism only applies once the general method actually has
enough data and compute, which is the open question this stage exists
to resolve, not assume.

## Relationship to the frozen baseline — this does not bypass the freeze

`VALIDATION.md` §56 names two, and only two, conditions under which
optimization work may resume:

1. A substantially larger, independently collected labeled dataset —
   not built the same way (same small Claude-judged corpus, same thin
   per-defect-class samples) as the evidence the freeze rests on.
2. A genuinely different modeling approach, evaluated against this
   project's own held-out generalization bar (the Phase 9B/9C
   precedent — a prior learned validator that predicted DEFECTIVE 99%
   of the time on genuinely held-out data) *before* being trusted over
   the frozen baseline.

Stage LR is condition (2)'s work. It is explicitly **not** authorized to
land on `main` or replace the frozen pipeline until it has cleared that
bar on real held-out data — training-set or tuned-corpus numbers alone
do not meet it, per the same Phase 9B/9C precedent. Until then, the
frozen baseline (`architecture-freeze-v1`) remains the shipped
implementation and the reference number any Stage LR result is compared
against: 21.4% fresh-corpus CLEAN, 0% dense-profile CLEAN, ~5-11%
dangerous-reversal rate (`VALIDATION.md` §55).

## Where this lives

All Stage LR work happens on the `stage-lr` branch (opened as
`research/stage8-learned-reformulation` per `DECISION_LOG.md`
2026-08-30-B, renamed to `stage-lr` per 2026-08-30-C), not on `main`.
`main` stays the frozen, shipped implementation partners build against —
see `HANDOFF.md`'s freeze banner. Promotion of any Stage LR result to
`main` is a separate, later, explicitly-ratified decision, following the
same discipline that closed the Architecture Go/No-Go arc — not an
automatic merge once something looks better on a training corpus.

## Matter 1 — phoneme-as-constraint representation audit (2026-08-30)

**Trigger:** before designing any reward function on top of the existing
`DifficultyProfile` schema, a direct question was raised and investigated:
do the phoneme-as-constraint engineering decisions this project already
made (Stage 4A, `PROBLEM_FORMULATION.md` §11) still hold once that
schema becomes training/reward-signal input, not just a rule-engine
input? Investigated directly against source (`phonetic.py`,
`difficulty_profile.py`, `PROBLEM_FORMULATION.md` §11), not evaluated
from prose alone.

**[FACT] Four representational ceilings confirmed, all already disclosed
in `PROBLEM_FORMULATION.md` §11, not new findings:**
1. `sounds` entries are onset-only (`phonetic._onset_from_phones()` stops
   at the first vowel) — §11.1 already names this as inherited, not
   re-derived, and deliberately not extended ("no second value it could
   take yet").
2. `DifficultyEntry` (`difficulty_profile.py`) has no severity, context,
   or time axis — `value`/`normalized`/`category`/`source`/`added_at`/
   `pronunciation`/`problem_phones`/`meta` only. Difficulty is a flat,
   declared, binary fact.
3. Words get a full phone sequence (`phonetic.full_pronunciation()`);
   phrases get none — stored as opaque declared text, matching deferred
   to `ROADMAP.md` R13 (§11.1).
4. `full_pronunciation()` silently uses CMU's first-listed pronunciation
   variant — real, silent label noise for heteronyms, already named in
   §11.3, already partially mitigated (`meta["has_alternate_pronunciations"]`
   exists and is currently unused downstream).

**[INTERPRETATION]** These were sound, disclosed simplifications for a
*rule engine*, where a representational gap just means one candidate
isn't filtered — a locally recoverable miss. For a *learned* component,
the same gap is baked into every training example: whatever the schema
can't represent becomes a hard ceiling on what any model trained against
it can ever learn, regardless of training method. This reframing, not
the four facts themselves, is Matter 1's actual contribution.

**[FINDING] Interim, literature-based sanity check for ceiling (1) — already exists in this repo, not a new task.** `REFORMULATION_RESEARCH.md`
§2.1 (Stage 5) already cites quantified stuttering-loci data: one study
found 97.8% of stuttering events on first syllables of words (76.5% on
the first sound specifically), another found 92–100% word-initial/
syllable-initial occurrence in adults who stutter. This is a real, if
population-level (not this-project's-speakers-level), sanity check that
onset-only is a reasonable *primary* approximation, not a silent miss of
something common. The same section also already names what it does
*not* cover: stress and sentence position (Brown's factor 3) are
real, evidenced loci that neither existing difficulty formula captures —
a distinct, already-tracked gap in `phonetic.word_difficulty()`, not the
profile schema this audit concerns. **This literature check is a cheap
companion to, not a replacement for, a real held-out audit** — it says
onset-only is defensible as a population-level prior, not that it's
correct for any specific Stage LR speaker.

**[LIMITATION, not a new task]** The full version of that audit — "how
often does *this project's* actual declared/observed difficulty fall
outside what the schema can represent" — needs real speaker data.
`ROADMAP.md` R2 already names this exact, standing gap (both difficulty
formulas are validated against nothing but self-declared profiles,
blocked on the separate, not-yet-built Audio Module). Reusing R2 here
rather than opening a duplicate blocker.

**[DECISION] Ceiling (4) gets a one-line fix, not a research task.**
Any Stage LR training-set builder excludes or down-weights entries
carrying `meta["has_alternate_pronunciations"] = True` (already set by
the existing Stage 4A refinement — no new instrumentation needed).

**[DECISION] Ceiling (3) — phrases get a minimal phonetic
representation before any training, not an open tension.** Phrases are
represented as the **concatenation of their words' existing
`full_pronunciation()` phone sequences** (word boundaries preserved,
OOV words contribute no phones rather than a guess, consistent with
`full_pronunciation()`'s own no-guessing policy). This is the smallest
change that closes the actual named risk — a shared feature space
(phone sequences) across sounds/words/phrases, so a reward model can't
learn "this is a phrase" as a shortcut for "I have no real phonetic
signal here." **Explicitly not fixing cross-word coarticulation** —
concatenation captures each word's own phones, not how one word's
ending phone interacts with the next word's starting phone — that stays
a named, separate, still-open limitation, not silently solved by this
decision.

**[DECISION, added 2026-08-30 — closes a scoping gap the first pass of
this decision left unstated] The phrase phone sequence is a fingerprint
of that phrase occurrence, not a set of per-word or per-phone claims.**
"This phrase is difficult" is one declared fact about the phrase as a
sequence — it is **not** the same as "every word in this phrase is
individually difficult," for the identical reason
`PROBLEM_FORMULATION.md` §11.1 already establishes one level down: a
word's `problem_phones` never auto-generalizes into a global `sounds`
entry. `difficulty_profile.py:212-219`'s `add_sound_from_phones()`
states this outright — promotion from a word-specific pattern to a
global sound is *"always an EXPLICIT call — nothing in this module
calls it automatically."* The phrase decomposition above must follow
the identical rule: nothing in Stage LR's feature extraction, training,
or any future consumer may read a phrase's concatenated phone sequence
as "flag these words, or these phones, as difficult everywhere on their
own." That reading is only valid as a separate, deliberate, explicitly-
triggered action — the same kind `add_sound_from_phones()` already
requires for words — never an automatic side effect of decomposing a
phrase into phones. **Not yet implemented as an enforced constraint**
(no training-set builder exists yet to enforce it against) — recorded
here as a binding design requirement for whichever one gets built.

**Alternative considered and rejected:** a separate reward-model
pathway/head for phrases (structurally distinct feature space, matching
their current opaque-string-match reality). Rejected as premature
architecture — it adds a second model pathway before any evidence the
simpler, shared-representation fix is insufficient, and it doesn't
actually give phrases real phonetic content, it just isolates the gap
into its own lane. Same reasoning `PROBLEM_FORMULATION.md` §11.4 already
used to reject adding a speculative `position` field: don't build
structure for a distinction not yet shown to matter.

**Category:** Stage LR design decisions, recorded on `stage-lr`, not
`main` — per direct instruction, this branch's work stays here until
ready to report back. No code written yet; these are representation
requirements for whenever Stage LR's first training-set builder is
implemented. Full record: `DECISION_LOG.md` 2026-08-30-D.

## Scope — Matter 2: proposal reviewed, working plan set (2026-08-30)

A founding proposal (`PROPOSAL_LEARNED_REFORMULATION_ENGINE.md` — a
profile-conditioned DPO reward/reranker, then RL-trained generation)
was submitted and critically reviewed against the live code, current
data, and this machine's actual hardware. Three of its claims did not
hold (a dead-code allowlist precedent, a stale "not wired up" citation,
an unspecified phrase feature); one gap was load-bearing (the claimed
reusable preference data does not exist at the needed scale or shape,
and this project's own Phase 9B/9C precedent already shows what
training on data this small produces on fresh material); hardware was
never costed (CPU-only, no GPU, and R23's own 10-40x slowdown result
for a comparable small-model approach). Full review, corrections, and
reasoning: `STAGE_LR_PROPOSAL_REVIEW.md` — read that first for *why*
the plan below looks like this, not just what it says.

**Current working plan**, superseding the "not yet decided" framing
this section previously had:

1. **Stage LR.1 — data reality check.** Quantify how much real
   pairwise-preference, multi-profile data can actually be produced
   before assuming any exists. Hard prerequisite for LR.3.
2. **Stage LR.2 — feature extractor.** Build the profile-conditioned
   reward features (meaning/naturalness/phoneme-difficulty) from
   already-validated components only (SBERT, MeaningBERT, NLI,
   `contextual_fit_score()`, `phonetic.py` + Matter 1's decisions). Not
   gated on LR.1 — buildable now, low risk.
3. **Stage LR.3 — reranker validation.** Only if LR.1 finds enough real
   data to make a held-out-by-speaker split meaningful. Otherwise,
   named explicitly blocked on data, same as `ROADMAP.md` R2.
4. **LR.4 — generative RL (renamed from "Stage 2," which collided with
   this project's own earlier Stage 2 — see `STAGE_LR_PROPOSAL_REVIEW.md`).
   On hold**, not rejected. **Update 2026-08-30: GPU access can be
   arranged**, so hardware is not the hard stop it looked like — but
   LR.4 still doesn't start until LR.3 has produced a validated reward
   signal. GPU access removes one blocker once LR.1–LR.3 clear; it
   doesn't let LR.4 skip ahead of them.

## LR.1 — data reality check, executed 2026-08-30

**Method:** direct inspection of every labeled/evaluation corpus in this
repo, not an estimate — `eval/r50_dataset/labeled_dataset.json` (the
largest, 135 records), `eval/pilot_responses/P1.csv` (the only real
human data), and the profile-construction code behind `eval/r10_corpus.json`
et al. (`eval/r10_build_corpus.py`, `eval/r10_harvest.py`).

**[FACT] Part A — same-context comparison pairs, checked directly:**
`eval/r50_dataset/labeled_dataset.json`'s 135 records are each a single
(sentence, one substitution tried, one quality rating) triple — not a
choice between candidates. Grouping records by (original sentence,
word being replaced) and checking for two *different* replacement words
rated differently for the same slot: **1 usable pair found out of 135
records** ("search"→"look" vs. "search"→"research," both rated SEVERE
independently). Every other apparent repeat was the identical
substitution re-verified across phases (e.g. "strategy"→"way" logged
three times, same word, same severity, from re-runs) — not a second
option to compare against. **Real, ready-to-use A-vs-B substitution
pairs in this project's entire recorded history: effectively 0.**

**[FACT] Part B — profile diversity, checked directly:** the eval
corpora's test profiles are built from **7-9 fixed templates**
(`single_sound`, `single_word`, `multi_word`, `dense_mixed_generic`,
`multi_sound`, `word_plus_sound`, `sparse_common_sound` —
`eval/r10_build_corpus.py`), authored by this project and reused across
~133-210 sentences. This is template variety, not independently-
collected distinct speakers. The only real human data,
`eval/pilot_responses/P1.csv` (20 rated items, participant P1), is a
genuine preference pair in shape — `pair_id` + `preference:
Reformulated/Original` — but it's "do you prefer the rewrite over the
original," not "which of two candidate words is better," and it's one
person.

**[INTERPRETATION]** The proposal's "reformatting, not fresh
collection" claim doesn't just need softening — the actual count is
close to zero, checked, not assumed. Getting real training data for a
reranker means new work on one of two paths: (1) generate a genuine
second candidate for cases already rated once, run a new A-vs-B
judgment on the pair (buildable — reuses this project's established
Claude-as-judge harvesting pattern from Phase 8/8B/9/10/11 — but it's
new data collection, starting from 1 real pair today, not a
reformatting task); (2) get more than one real declared profile — more
real participants, or explicit, disclosed use of synthetic-template
diversity with the caveat that it doesn't test generalization to an
actual new speaker.

**[DECISION] LR.3 status, per the plan's own conditional design:**
named **explicitly blocked on data**, same treatment `ROADMAP.md` R2
already gives the difficulty-formula weights — not trained on what's
available. Reopens once path (1) or (2) above produces a real, counted
number of pairs from more than one profile, not once "some" data
exists.

**[NOT DONE]** LR.1 quantified what exists; it did not attempt to build
new comparison pairs or recruit new participants — that's the concrete
next action under path (1)/(2) above, a separate, later decision.

## LR.2 — feature extractor, built and tested 2026-08-30

**[FACT] Real code exists now**, not just a spec: `stage_lr/features.py`
(new package, never imported by `app.py`/`reformulate.py`/anything on
`main`) implements `score_candidate(sentence, candidate_sentence,
candidate_text, profile, source, occurrence) -> CandidateScore` —
meaning (SBERT + MeaningBERT), naturalness (`contextual_fit_score()`,
single-word substitutions only, per its own validated scope), and
phoneme difficulty (profile.sounds onset match + exact word/phrase
match). 13 tests in `tests/stage_lr_features_test.py`, all passing.

**[DECISION, implemented not just specified] Every Stage LR guardrail
decided so far is enforced in code, with a regression test per
guardrail:**
- The ARPAbet-key fix (§2.1 of `STAGE_LR_PROPOSAL_REVIEW.md`): `_word_onset_hits()`
  compares `phonetic.onset()` directly against each `sounds` entry's
  stored `.normalized` key — never re-derives it from `.value` via
  `phonetic.normalize_pattern()`'s spelling guess, the exact lossy path
  behind the ZH bug. `test_onset_hit_works_for_sounds_added_via_phones_not_just_spelling`
  checks this against a real `add_sound_from_phones()` entry, not just
  the easy spelling-guess path.
- Matter 1's word-level guardrail: `test_word_specific_pattern_never_leaks_into_a_global_onset_hit`
  checks directly that a word's `problem_phones` never makes an
  unrelated word match a global sound.
- Matter 1's phrase-level guardrail (2026-08-30-E): `test_phrase_match_never_flags_a_lone_word_from_that_phrase`
  checks directly that a declared difficult phrase does not cause its
  own component word, used alone, to register as declared-difficult.
- No allowlist term (per the review's correction) — not implemented,
  not faked.

**[LIMITATION, found while testing, not before]** The end-to-end smoke
test passed, but on loose assertions ("if not None, must be in bounds")
that pass vacuously when a model fails to load. A direct manual check
(not the test suite) found all three models — SBERT, MeaningBERT,
contextual-fit — currently fail to load **in this environment**, from
the same root cause: `protobuf` 5.29.6 installed, but something
requires gencode >= 6.31.1 (a `tensorflow` 2.21.0-side dependency,
`tensorflow` itself not in `requirements.txt` — likely a transitive
install, not a direct one). **This is not a Stage LR bug** — `semantic.py`
is shared with the frozen, live pipeline, so this machine's `main`
branch is *also* silently running on frequency-only ranking right now,
same root cause. Flagged to the user as a separate, real, live-pipeline-
affecting environment issue; not fixed here without a decision on
whether to bump `protobuf` (a dependency-version change, the kind
routine maintenance already permits under the freeze, but touching
installed versions warrants a decision, not a silent fix mid-task).

**[NOT DONE]** LR.2 is not wired into anything — no training-set
builder, no ranking policy, no call from `reformulate.py`. It produces
a scorecard; using it to actually rank or filter candidates is LR.3's
job, still blocked on data per LR.1's finding.

This section is no longer "not yet decided" for the near-term sequence
above; what remains genuinely open is LR.1's actual result and whatever
LR.3/LR.4 look like once it lands.
