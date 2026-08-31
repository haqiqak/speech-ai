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

## LR.1, data path (a) — real pairwise preference data generated, 2026-08-30

**[FACT] Method** (`stage_lr/generate_pairs.py`, `stage_lr/data/`):
for each of the 135 records in `eval/r50_dataset/labeled_dataset.json`,
its real profile was reconstructed (not guessed) from the raw harvest
file behind it (`r40_change_audit_data.json` / `r47_fresh_sample_results.json`
/ `r48_v3_verification_results.json` — `labeled_dataset.json` itself
drops the profile field). `reformulate._raw_candidates` was then
wrapped, for one call, to exclude the already-rated replacement's lemma
from the pool handed to the real, unmodified `reformulate.reformulate()`
— every gate (antonym/phoneme/duplicate/blocklist/countability/etc.)
still runs exactly as production. Whatever survives is a genuine,
pipeline-approved runner-up, not hand-picked.

**[FACT, a real bug caught before trusting any result]** The first pass
matched records to profiles by sentence text alone and produced
plausible-looking but silently wrong results (one record showed an
unrelated word changing between the historical and regenerated
sentence). Checked directly, not assumed correct: R40's harvest tests
most sentences under **up to 4 different profiles** — 36 of 41 unique
R40 sentences, confirmed by direct count. A text-only lookup collapses
to whichever profile was read last for that sentence. Fixed by matching
on (sentence, original word, replacement word), verified against each
record's own `changed_word_pair` rather than assumed from lookup order.
The corrected run changed the result meaningfully: 22 candidates found
under the broken matching, 32 under the correct one.

**[FACT] Honest final counts, all 135 records:**
- 21 not substitution-tier (restructuring/other — no word-level
  candidate pool to regenerate against).
- 0 profile-unrecoverable (every substitution-tier record's real profile
  was found and verified).
- 82 attempted, no second candidate survived every gate once the
  original was excluded — the original was the pipeline's only viable
  choice at that position.
- **32 genuine second candidates found.**

**[FACT] Of the 32, 11 are not clean single-variable comparisons.**
Checked by direct token-level diff between the two candidate sentences,
not assumed: when a sentence has 2+ words flagged by the same profile,
ranking is contextual (scored against the sentence as it's being
rebuilt), so excluding one word's top choice can legitimately shift
which candidate ranks best for a *different* flagged word too — the
same interaction this project's own R32 investigation named for the
frozen pipeline's own candidate selection, now observed from the other
side. These 11 are disclosed, not discarded silently, and not forced
into a format that misrepresents what actually varied — see
`stage_lr/data/lr1_preference_pairs.json`'s
`excluded_multi_word_contaminated`.

**[FACT] Of the 21 clean pairs, 4 are exact re-verification duplicates**
(the same sentence/profile/word pair harvested more than once across
different phases) — **17 unique clean comparisons**, all 17 judged
(A/B/tie + reasoning, not a template) and logged in
`stage_lr/data/lr1_preference_pairs.json` in the requested pairwise
format. Preference split: 7 A, 9 B, 1 tie. One real, substantively
interesting finding surfaced by the judging itself: the "sea"→"ocean"
vs. "water" and "restaurants"→"buildings" vs. "eateries" pairs are live
instances of this project's own previously-diagnosed genericness bias
(§53/R26-R29) — a more generic, higher-frequency word beating a more
precise one — caught here in freshly-generated data, not retrieved from
the historical record.

**[INTERPRETATION]** This is a real, if modest, first real dataset —
17 judged pairs from more genuinely-collected comparisons than existed
anywhere in this project before today (LR.1's original count was
effectively 0). It is **not** yet enough to run LR.3's held-out-by-
speaker split meaningfully: all 17 pairs still come from the same small
set of researcher-authored profile templates (`light_single_sound`,
`moderate_mixed`, `heavy_dense`, `single_common_sound`, plus one-off
R47 profiles) — not independently-collected real speakers, the same
limitation LR.1's original pass already named. LR.3 stays blocked on
that broader condition; this data path is a real, disclosed step
toward it, not a resolution of it.

## LR.1, data path (a), batch 2 — grown using the exact same method, 2026-08-30

**[FACT]** Per instruction, batch 2 reused the identical pipeline (`stage_lr/generate_pairs.py`'s `attempt_second_candidate()`, unchanged) against a different, previously-uncovered source: `eval/r10_raw_results.json` (Phase 10's 398-run stress-test harvest — never part of the 135 `labeled_dataset.json` records). No new source material had to be invented; this corpus already existed and already carries each run's exact `profile_spec` directly, so there was no cross-file matching step at all (and therefore no way to repeat batch 1's profile-matching bug — nothing to disambiguate).

**[FACT] Honest counts, same drop-off shape as batch 1, reported plainly:** 239 substitution-sourced changes examined → 154 no second candidate survived exclusion → **85 second candidates found** → 32 excluded as multi-word-contaminated (same diff-based check as batch 1, same underlying cause: contextual ranking, a second flagged word shifting when the first is excluded) → 53 clean → 12 exact re-verification duplicates collapsed → **41 unique pairs, all 41 judged**.

**[FACT] Running total: 58 judged pairs** (17 from batch 1 + 41 from batch 2), appended to the same `stage_lr/data/lr1_preference_pairs.json` — one growing source of truth, not a parallel file. `excluded_multi_word_contaminated.uids` similarly grew to 43 (11 + 32).

## LR.2 sanity check against the 58 pairs — a real finding, not a clean bill of health

**[FACT] A real bug in LR.2 itself, caught by this check, not before it:** `stage_lr/sanity_check_lr2.py`'s first run produced a suspicious, repeating ~0.945 score across dozens of unrelated pairs. Traced directly, not assumed: `semantic.py`'s three load functions are inconsistent — `meaningbert_score()` and `contextual_fit_score()` both auto-load their model on first call, but `semantic_similarity()` (SBERT) does not; it only checks an already-set flag. `stage_lr/features.py`'s `score_candidate()` never called `semantic.load_sbert()`, so SBERT silently returned `None` on every one of the 58 calls, with no error, degrading "meaning" to MeaningBERT alone the entire time. **Fixed in `stage_lr/features.py`** (one line, `semantic.load_sbert()` before use) and locked in with a new regression test (`test_sbert_is_actually_populated_not_silently_none`, `tests/stage_lr_features_test.py`) that fails loudly if the call is ever removed. This is exactly the class of blind spot this sanity check was for.

**[FACT] Result after the fix, all 58 pairs, real numbers:** a naive `meaning + naturalness − phoneme_difficulty` combination (this check's own scoring, not a proposed ranking formula) agreed with the human/Claude judgment on **28/58 (48%)** — barely better than chance for a binary call. Broken down, not smoothed over:
- On the 51 pairs where a human expressed a real preference (not a tie): **26/51 agreed (51%)**, chance level. Of the 25 disagreements, **17 (68%) were LR.2 calling it a tie** — no discriminative power at all, not a wrong-direction error — and only 8 (32%) were LR.2 confidently picking the wrong side.
- On the 7 pairs a human called a genuine tie, LR.2 agreed on only 2 — mostly picking a confident side where a human found none.

**[INTERPRETATION]** This is not noise — it's a coherent, informative result. Both candidates in every pair already survived the frozen pipeline's own SBERT floor before either was offered, so meaning-similarity scores cluster tightly among survivors by construction; LR.2's current signals (SBERT/MeaningBERT/contextual-fit) are the *same class* of signal the frozen `combined_score()` already ranks with, and they show the same low resolution here that `VALIDATION.md` §53 already diagnosed as the frozen pipeline's dominant failure (WRONG_WORD_OR_SENSE as a ranking problem, not a generation problem). Read against the actual judged reasons in `lr1_preference_pairs.json`, a real, recurring pattern in what *did* distinguish A from B is **grammaticality/well-formedness** ("softwares" plural error, "excused for" missing its reflexive object, "manufacturings" invalid pluralization, "a other noise" article mismatch, "It's taken impolite" missing "to be") — a dimension `score_candidate()` currently has **zero signal for**. `semantic.py` already has `grammar_issue_count()`/`logical_consistency_check()` built and validated (Architecture Gate Step 1) that LR.2 doesn't yet call at all.

**[NOT DONE]** Adding a grammar signal to LR.2 is a real, concrete next step this check surfaced — not implemented here, since redesigning the score is a deliberate decision (what weight, what threshold, re-validate against these same 58 pairs) rather than a quick patch alongside a sanity check. Named here so it isn't lost.

## LR.2's 4th term added (grammar), re-checked — still not enough to resume path (a), 2026-08-30

**[FACT] Real code, not a proposal:** `score_candidate()` now calls `semantic.grammar_issue_count()` (LanguageTool, already validated/used live in `reformulate.py`'s own escalation gate) on the full candidate sentence, for every source — no scope restriction, unlike `contextual_fit_score()`. Two new regression tests confirm it catches a real error and is computed for phrase-sourced candidates too (`tests/stage_lr_features_test.py`). **A dependency was missing here as well** — `language_tool_python` was absent from this venv, the exact same class of silent-degradation bug as the SBERT one, except this one was live on `main`'s own shipped gate (`reformulate.py`'s `if (sem.grammar_issue_count(cand) or 0) > 0` was silently always `False`) — fixed on `main` separately (`DECISION_LOG.md` 2026-08-30-E there), verified with real output, and confirmed via direct A/B testing (installed vs. not) that 3 unrelated, pre-existing test failures found along the way are **not** caused by this fix.

**[FACT] Re-ran the sanity check against the same 58 pairs, honest result, not rounded up:**

| | before (3 terms) | after (4 terms) |
|---|---|---|
| Overall agreement | 28/58 (48%) | **30/58 (52%)** |
| Non-tie pairs (51) | 26/51 (51%) | **28/51 (55%)** |
| — LR.2 said tie (no discrimination) | 17 | 16 |
| — LR.2 confidently wrong | 8 | 7 |
| Human-tie pairs (7), LR.2 also tie | 2/7 | 2/7 |

**[INTERPRETATION]** A real, small, honest improvement — not a wash, not a fix. 52% (55% on the non-tie subset) is **not meaningfully above the 50% chance level** for a binary call on n=51 — a 4-5 point shift on this sample size is well within noise, not a result to act on as if the ranking problem is solved. Per the explicit standing instruction, **path (a) stays paused** — growing the pair count further would only produce more data to validate against a reward function still this close to chance.

**[FACT] One specific flip is worth naming, not just the aggregate number.** The "greenhouse"→"gas" vs. "building" pair (R40-014/016): the human judgment preferred "gas" despite an awkward word-duplication ("gas gas emissions") because "building gas emissions" is semantically incoherent, not just awkward. Adding the grammar term flipped LR.2 to prefer "building" — LanguageTool likely flags (or at least doesn't reward) the duplication, but has no way to detect that "building gas" isn't a real, coherent concept in context. This is a concrete illustration of what grammar alone can't fix: `semantic.py` already has `logical_consistency_check()` (NLI, validated in Architecture Gate Step 1) that's a plausible next candidate signal for exactly this gap — surfaced here, not implemented, per the same discipline as the grammar term itself (a deliberate decision, not a reflexive addition to chase one case).

## LR.2's 5th term added (NLI), re-checked — still not meaningfully above chance; time to step back, 2026-08-30

**[FACT] Real code:** `score_candidate()` now also calls `semantic.logical_consistency_check()` (bidirectional NLI, already validated in Architecture Gate Step 1) for every source, surfacing `logical_contradiction: bool | None`. Two new regression tests reuse this project's own already-validated known-contradiction pair (`tests/reformulate_v2_test.py`'s `NLIConsistencyCheckTest`) rather than inventing new ones. 18/18 `stage_lr` tests pass.

**[FACT] Re-ran the sanity check against the same 58 pairs, honest result, not rounded up:**

| | 3 terms | +grammar (4) | +NLI (5) |
|---|---|---|---|
| Overall agreement | 28/58 (48%) | 30/58 (52%) | **32/58 (55%)** |
| Non-tie pairs (51) | 26/51 (51%) | 28/51 (55%) | **30/51 (58.8%)** |

**[FACT, checked, not eyeballed]** Ran the actual significance check the "meaningfully above chance" bar implies: one-sample proportion z-test against p=0.5 on the non-tie subset (n=51, x=30) gives **z=1.26, one-sided p≈0.10** — not significant at any conventional threshold (would need z≥1.645 for p<0.05). Each of the three configurations tested today, including this one, is statistically indistinguishable from chance at this sample size.

**[DECISION, per the explicit standing instruction] This is the signal to stop adding terms one at a time.** Five real, already-validated signals are now wired in (SBERT, MeaningBERT, contextual-fit, grammar, NLI) — the full set this project's frozen pipeline and research arc have actually built and validated. None of the three incremental configurations cleared chance. The honest reading is not "term 6 will probably fix it" — it's that **hand-picking which of these signals matters, and how much, may not be the right approach at all**, the same conclusion this project's own Bitter-Lesson framing (`VALIDATION.md` §57) already anticipated in the abstract. The concrete alternative this check itself points to: a small learned model that weights these same 5 signals (or reads their underlying representations directly) from real preference data, rather than a hand-set linear combination — exactly LR.3's original shape (a reranker), now with 58 real judged examples to actually attempt it on, instead of the ~0 that blocked LR.3 when LR.1 first ran.

**[NOT DONE]** No such model was built here — this is a finding and a fork in the road, not a decision made unilaterally. 58 pairs is almost certainly still too few to train anything reliably (the Phase 9B/9C precedent this project already has on record used a much larger, still-thin dataset and still failed to generalize) — whether to (a) grow the pair count now specifically to attempt a learned reranker, (b) keep manually tuning hand-picked weights despite three consecutive chance-level results, or (c) something else, is a decision for the next turn, not assumed here.

## Fork resolved: hand-tuning closed, a human-agreement ceiling check run, LR.3 gated on two prerequisites — 2026-08-30

**[DECISION] Hand-tuning (option (b) above) is closed, not deprioritized.** Per direct instruction: the evidence from the 3/4/5-term progression — three consecutive statistically-indistinguishable-from-chance results, each increment buying less than the last — closed this door. No further hand-picked LR.2 terms will be added in response to individual gaps found in judged pairs; that pattern is this project's own already-named "Phase 11D/E/F" failure mode (`CLAUDE.md`'s freeze banner), now independently reproduced inside Stage LR itself rather than just inherited as a risk from the frozen pipeline.

**[FACT] Before committing to option (a) (a learned reranker), a human-agreement ceiling check was run, per direct instruction.** 25 of the 58 pairs (`random.seed(42)`, reproducible) were re-judged **blind** by a fresh subagent — a genuinely separate process with zero memory of this conversation or the original verdicts, given only `(sentence, profile, candidate_A, candidate_B)`, the same "blind judging" pattern this project already used in Phase 10. Full data: `stage_lr/data/human_agreement_ceiling_check.json`.

**[LIMITATION, stated prominently, not buried]** This is **not** true human-human inter-rater agreement — both the original judge (this conversation) and the second judge (the fresh subagent) are Claude. It's a genuine blind re-judgment (the second pass could not see or recall the first), but two instances of the same model family plausibly agree with each other more than two genuinely different humans would. Reported with this caveat attached every time the number is cited, not as a substitute for a real second person.

**[FACT] Result:** raw three-way (A/B/tie) agreement **17/25 (68.0%)**. Restricted to the 21 of 25 pairs where *neither* judge hedged with "tie" (all 4 tie-involving pairs were disagreements — one side committing, the other hedging): **17/21 (81.0%)**.

**[INTERPRETATION]** Both ceiling numbers sit clearly above LR.2's 5-term result (55.2% overall / 58.8% non-tie, on the full 58-pair set). Read together: this task has genuine inherent ambiguity — even a blind re-judgment doesn't reach 100% — but the ceiling is well above chance and well above where LR.2 currently sits, at least by this one (imperfect, Claude-only) estimate. That argues LR.2's current shortfall is real headroom, not a task-is-unsolvable ceiling effect — a meaningfully different situation than if the ceiling check had come back near 50-55% itself.

**[DECISION] LR.3 is now gated on two sequential prerequisites, not pursued in parallel with them, per direct instruction:**
1. **Growing data path (a)** — more batches, same method, meaningfully larger and more varied than 58 pairs.
2. **Path (b)** — real, independently-declared profiles from real distinct people, not more researcher-authored templates.

Both must exist before LR.3 training is attempted — not one or the other, and not "start training now, keep collecting in parallel." The reasoning carried over directly from the Phase 9B/9C precedent already on record: a larger-but-still-thin dataset already failed to generalize once in this project's history; attempting LR.3 again on a dataset with the same two structural gaps (small, single-generation-setup) risks reproducing that exact failure rather than learning anything new. This is now the binding sequencing for LR.3, not a preference — recorded here so a future session doesn't reopen it as if undecided.

## Path (b) — still separate, still unstarted, still people-dependent

**[FACT, flagged per direct instruction, not a task for this session]** Growing data path (a) — however many more batches — does not touch path (b)'s actual gap: every profile behind all 58 pairs (and everything path (a) could ever produce from existing corpora) is a researcher-authored template (`light_single_sound`, `moderate_mixed`, `heavy_dense`, `single_common_sound`, `sentence_specific_word`, plus R47's one-offs) or Phase 10's own synthetic density categories — not a real, independently-declared profile from a real distinct person. LR.3's held-out-by-speaker evaluation needs the latter specifically. Path (b) remains separate, unstarted, and dependent on real people (recruiting more participants like the original pilot's P1) — not something more generation or more judging from this pipeline can substitute for.

This section is no longer "not yet decided" for the near-term sequence
above; what remains genuinely open is LR.1's actual result and whatever
LR.3/LR.4 look like once it lands.
