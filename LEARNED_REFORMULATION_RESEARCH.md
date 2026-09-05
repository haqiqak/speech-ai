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

**[DECISION, confirmed 2026-08-30]** The human-agreement ceiling check (`stage_lr/data/human_agreement_ceiling_check.json`, 68%/81%, n=1 Claude rater) is accepted as-is, with its caveat (Claude-consistency, not a true human ceiling) logged exactly as stated — no revision needed.

## Claude-as-judge established as the standard judging method — 2026-08-30

**[DECISION]** Per direct instruction, a general-purpose Claude call (via the Agent tool in this environment — there is no direct Anthropic API tool available to a script here) is now the **standard method** for judging candidate pairs in data path (a), and for any future evaluation work in Stage LR — replacing the ad hoc, manually-reasoned judging used in batches 1-2 (and, before that, the original 17-pair pass), which was the real bottleneck. Formalized as real, reusable code: `stage_lr/judge_pairs.py` (prompt-building + response-parsing, 7 tests, `tests/stage_lr_judge_pairs_test.py`), following the exact blind-judging discipline already established for the human-agreement ceiling check and, before that, this project's own Phase 10 precedent (5 parallel blind subagents).

**[FACT, a hard invariant, not a convention — checked and enforced]** Claude judges **meaning, naturalness, and grammaticality only**. Phoneme-avoidance is never a Claude judgment call — `stage_lr/judge_pairs.py`'s prompt has no phonetic-judgment language at all, by design (`test_prompt_never_mentions_phoneme_judgment` asserts this directly), because it doesn't need to: every candidate `generate_pairs.py` ever hands to a judge has already survived the real, unmodified `reformulate()` pipeline's own phoneme gate (matching against `profile.sounds` via `phonetic.py`'s ARPAbet/onset logic, the same mechanism behind Matter 1's guardrails) before this module ever sees it. Phoneme-avoidance is a computable fact, checked deterministically upstream; Claude is never asked to decide it, and structurally cannot override it even if it tried.

**[FACT] First real use: batch 3.** With no more unused existing corpus of the right shape available (checked directly: R11's reverify data covers the exact same 398 R10 runs batch 2 already used — same sentences, same profiles, just a later harvest snapshot, not genuinely new; R43a/R44/R49's result files don't carry substitution-tier `changes` lists), batch 3 used the pre-approved fallback: 30 fresh, previously-unused sentences (`stage_lr/harvest_batch3.py`, new domains — gardening, travel, cars, sports, home repair, finance, pets, art, health, shopping — not reused from R40/R47/R10's topics) run through the real `reformulate()` pipeline for the first time, against the same 4 existing profile templates, then the identical generate-second-candidate method as batches 1-2.

**[FACT] Honest counts, real, not padded:** 30 sentences × 4 profiles = 120 attempted → **97 produced no substitution-tier change at all** (most sentence/profile combinations simply don't trigger a flagged word — expected and different in shape from batches 1-2, which only ever attempted combinations already *known* to have triggered one) → 23 actually attempted a second candidate → 10 no second candidate → **13 second candidates found** → 0 excluded as contaminated (checked, same diff method) → 3 exact duplicates collapsed → **10 unique pairs, all 10 judged via the new standard method** (one Claude call, `stage_lr/data/batch3_pairs_full.json`/generation log). **Running total: 68 judged pairs** (58 + 10), appended to the same `lr1_preference_pairs.json`.

**[LIMITATION, disclosed]** Batch 3's much lower found-rate (13/120 = 10.8%, vs. batches 1-2's ~24-36% found-rate on pre-filtered records) is a real, expected consequence of trying *every* sentence/profile combination blind rather than only ones already known to trigger a change — not a sign anything is broken. Reported as the actual denominator, not hidden by only counting attempts that succeeded.

## Claude-as-judge does not substitute for path (b) — clarified explicitly, 2026-08-30

**[DECISION, per direct instruction]** Claude-as-judge resolves the **judging-bottleneck** half of path (a) — it makes producing judgments faster and cheaper, nothing more. It does **not** touch path (b)'s actual gap, which is a **data-diversity question, not a judging-mechanism question**: path (b) needs real, independently-declared difficulty profiles from real distinct people, to test whether a reward model generalizes across speakers — no amount of faster or cheaper judging produces that. Both LR.3 prerequisites named above (path (a) grown meaningfully larger; path (b) real people) remain exactly as gated — this update changes *how* path (a)'s judgments get made, not *what* is required before LR.3 training is attempted.

## Path (a) declared at a practical ceiling for the current generation setup — no batch 4, 2026-08-30

**[FACT, checked before deciding, not a gut call]** Two things measured across all 68 pairs before deciding whether to run batch 4:
- **Profile-shape diversity is capped at ~4-6 fundamentally distinct sound/word constraint patterns**, however many label variants they appear under (`sentence_specific_word` 20, `heavy_dense` 12, `moderate_mixed` 11, `dense_mixed_generic` 7, `multi_sound` 7, `sparse_common_sound` 4, plus five 1-2-count one-offs) — a direct consequence of only 4 profile templates existing at all. No number of additional sentences moves this.
- **Vocabulary diversity is still genuinely healthy**: 62 distinct flagged words out of 68 pairs — only 6 repeats, mostly legitimate re-verification duplicates (the same sentence tested under two profile variants), not signs of running out of material.

**[DECISION]** No batch 4. Not because sentences ran out — vocabulary diversity says they haven't — but because batch 3's found-rate already dropped to 10.8% (vs. batches 1-2's 24-36% on pre-filtered records), a genuinely fresh batch 4 would cost real sentence-writing effort for a similarly small yield, and would almost certainly recur the same failure-mode categories already well-represented (countability/pluralization errors, wrong-sense substitutions, register mismatches, missing-object grammar errors — batch 3 surfaced no qualitatively new category), while adding zero profile-shape diversity regardless. Path (a) is at a practical ceiling **for this generation setup specifically** (fixed profile templates) — not a claim that no more sentences exist, a claim that the marginal batch buys recurrence, not new signal, on the dimension that actually matters for LR.3.

## Path (a), batch 4 — new profile shapes, not new sentences, 2026-08-30

**[FACT] This is not the batch declined above — it targets the exact dimension that decision named as capped.** After the first real path (b) participant's profile turned out messier than any of the 4 original synthetic templates (a common sound mixed with several unrelated, personally-anticipated words, not one tidy pattern), 3 new profile shapes were designed to mirror that structure — deliberately not clean single-pattern templates — and run against **batch 3's existing 30 sentences, unchanged**, isolating template diversity as the actual variable, not sentence novelty (`stage_lr/harvest_batch4_new_templates.py`).

**[FACT] Honest counts:** 30 sentences × 3 new templates = 90 attempted → 71 no substitution change → 8 found → 1 excluded as contaminated → **7 unique, all 7 judged**. Running total: **75 judged pairs** (68 + 7).

**[FACT, disclosed not hidden]** One of the 3 new templates (`word_heavy_sparse_sound` — words like "comfortable," "vegetable," "library," plus the rare onset "gl") produced **zero hits across all 30 sentences** — none of its declared words happened to appear in this sentence pool at all. Not a bug: a real, concrete illustration of something relevant to the actual problem — an idiosyncratic real profile won't always intersect with whatever text exists, which is exactly why path (b)'s real participants (with their own real, unpredictable word choices) can't be substituted for by researcher-guessed templates no matter how many are invented.

## Path (b) — a concrete, minimal ask, ready to send — 2026-08-30

**[FACT, flagged per direct instruction, not a task for this session]** Growing data path (a) — however many more batches — does not touch path (b)'s actual gap: every profile behind all 68 pairs (and everything path (a) could ever produce from existing corpora or fresh sentences) is a researcher-authored template or Phase 10's own synthetic density categories — not a real, independently-declared profile from a real distinct person. LR.3's held-out-by-speaker evaluation needs the latter specifically.

**[RECOMMENDATION] The minimal, concrete ask per friend — two short steps, ~20 minutes total:**

1. **Declare a real difficulty profile (~5 min).** Answer, in plain language, no jargon: (a) any sounds you often stumble on or avoid, especially at the *start* of a word (e.g. "the 'str' in street," "the 'th' in think," "hard 'r' sounds") — however they'd describe it themselves, not ARPAbet notation; (b) any specific words that are personally hard for you, for any reason, even idiosyncratic ones; (c) optionally, any whole phrases that are hard as a unit even if the individual words aren't.
2. **Judge a short batch of real pairs generated from their own profile (~15 min).** Once (1) is in hand, generating the pairs is a zero-new-engineering step — reuse `generate_pairs.py`/`judge_pairs.py` exactly as built, just with a real `DifficultyProfile` instead of a template. Show the friend ~10-15 short items: a sentence, one word in it, two ways to reword it — "which would you actually rather say out loud? A / B / doesn't matter" — no explanation required from them, just a pick, to keep it fast.

**[INTERPRETATION] Why both steps, not just the profile.** Step 1 alone would still leave the *judging* done by Claude (better than a synthetic profile, but not the actual gold-standard signal). Step 2 is what makes this genuinely different from everything path (a) has produced: a real human preference tied to a real declared difficulty — directly comparable against Claude's own judgment on the same pairs, closing part of the "Claude-consistency, not a true human ceiling" caveat the agreement-ceiling check (`DECISION_LOG.md` 2026-08-30-N) already disclosed. This is the same shape of contribution the original pilot's single participant (P1) gave — path (b) is asking for more of exactly that, not something new in kind.

**[NOT DONE]** No profile has been collected yet — this is the ask itself, not a result. Once any real answers come back, ingesting them requires no new code: `DifficultyProfile.add_sound()`/`add_word()`/`add_phrase()` and the existing `generate_pairs.py`/`judge_pairs.py` pipeline handle it as-is.

**[DECISION] Ingestion mechanism built ahead of any real data, per direct instruction, to close off a specific risk before it can happen.** `stage_lr/ingest_real_human_pair.py` is now the only sanctioned way to record a friend's verdict. Two hard rules, enforced structurally, not just documented:

1. **A human verdict is never logged without a Claude verdict on the exact same pair, obtained in the same session.** `record_real_human_pair()`'s `human_preferred`, `claude_preferred`, and `claude_reason` are required keyword arguments with no default — there is no code path that writes a record carrying only one verdict. This closes off, by construction, the two-pass drift risk this project already has concrete precedent for (Phase 9B/9C's own instability across separate runs; R28's test-set leakage, only caught by re-checking) — a changed prompt, pipeline state, or model version between a "log the human answer now" pass and a "run Claude on it later" pass could silently desynchronize two verdicts meant to be directly comparable.
2. **Real-human pairs live in a separate file**, `stage_lr/data/real_human_pairs.json`, not merged into `lr1_preference_pairs.json`'s 68 pairs (which are now retroactively tagged `source: "synthetic_profile_template"` for schema consistency, not just new entries going forward). Every real-human record also carries `source: "real_human"` as a second, redundant safeguard. Structural separation, not just a filterable tag, was chosen specifically because the instruction was that these "shouldn't get silently merged... when computing agreement rates later" — a different file makes that require a deliberate action, not an accidental one.

9 tests (`tests/stage_lr_ingest_real_human_pair_test.py`) prove both rules directly — including calling the function without `claude_preferred` and confirming it raises `TypeError`, not just asserting the intent in a docstring. Exercised with synthetic stand-in verdicts only; no real human data exists yet, and none was fabricated to test this — the mechanism is proven correct, not "tested" against invented results.

This section is no longer "not yet decided" for the near-term sequence
above; what remains genuinely open is LR.1's actual result and whatever
LR.3/LR.4 look like once it lands.

## Path (b), real participants — in progress; participant content kept local by design (2026-08-30)

**[FACT] The ask worked — a real answer came back**, and has been processed as far as generating and judging candidates. Per direct instruction, participants' actual declared profiles, sentences, and generated pairs are **not reproduced in this shared document or committed to the repository** — they live only under `stage_lr/data/private/` (gitignored) on the machine handling this. This section records aggregate, non-identifying facts and one system-level finding, nothing participant-specific.

**[FACT] The mechanism is generic and reusable**, corrected early from an initial version that mistakenly hardcoded a participant's actual words directly in a committed `.py` file — caught before that file was pushed, not after. `stage_lr/harvest_real_profile.py` takes a per-participant input file from `stage_lr/data/private/` and is itself content-free; only `stage_lr/data/private/` and `stage_lr/data/real_human_pairs.json` are gitignored, not the mechanism.

**[FACT, a genuinely new finding, disclosed not fixed — about the system, found from constructed sentences, not participant content]** During candidate generation, a real, previously-undocumented defect in `main`'s frozen `sanitize_input()` was found and independently reproduced across two separate generation runs: it incorrectly applies third-person-singular agreement to an infinitive after "to" (e.g. "wants to conduct" → "wants to conducts"; "tried to predict" → "tried to predicts") — a generic English construction, not specific to any participant's own words. Confirmed directly both times by checking each affected sentence's own `sanitize_input()` output; any candidate pair built from an affected sentence was excluded from what gets shown to a participant, since it wouldn't bias the underlying A-vs-B comparison but would show an unrelated, unexplained error. Not fixed here, per `CLAUDE.md`'s standing instruction for a newly observed failure against the frozen architecture — logged in `DECISION_LOG.md` 2026-08-30-R.

**[FACT] Real human-vs-Claude comparison data: n=15, 8/15 agree (53.3%)**, computed directly from `stage_lr/ingest_real_human_pair.summarize()`, not by hand — every record carries both a real participant's verdict and a same-session Claude verdict on the identical pair, per `ingest_real_human_pair.py`'s hard rule. Now spans **four** distinct real participants (friend_1: 6; friend_2: 1; friend_3: 1; a fifth participant judging their own declared profile: 7, 2026-09-01), not three.

**[FACT] The 7-pair batch from the fifth participant dropped the aggregate rate from 87.5% to 53.3%, and the specific shape of the disagreement matters.** On 6 of those 7 pairs Claude's verdict was `"tie"` (explicitly: both candidates equally good), while the human made a definite A/B pick every time (all "A", across all 7). Only 1 of 7 was a same-direction match. `ingest_real_human_pair.py`'s `agree` field is strict equality (`human_preferred == claude_preferred`), so a Claude "tie" against a human "A" scores as disagreement — correct and intended by this module's own design (a tie genuinely isn't the same verdict as a definite pick), but worth stating plainly: this is not the same failure shape as an earlier batch where Claude picked the *other* letter than the human. Here Claude repeatedly saw two near-synonymous candidates as interchangeable on meaning/naturalness/grammar (its stated reasoning), while the human had a consistent, definite preference anyway.

**[INTERPRETATION, heavily qualified — n=15 across four participants is not a result to act on, and isn't treated as one]** Cannot statistically distinguish anything on this scale, and the new data now has more spread than before, not less. Two live, undistinguished explanations for the tie-vs-definite-pick pattern: (a) Claude's "tie" judgments are genuinely too conservative for pairs that are close but not truly indistinguishable — humans reliably notice a difference Claude's rubric averages away — or (b) the human's picks reflect a mild, consistent response bias (e.g. always favoring the first-listed option, or a stylistic preference not tied to meaning/naturalness/grammar at all) rather than a real quality judgment the rubric should be expected to reproduce. Nothing in this data distinguishes these — both remain live. Four participants, one of them contributing a disproportionate share of the pair count, still can't confirm or rule out either explanation.

**[NOT DONE]** No conclusion drawn, no LR.2 weights touched, no change to LR.3's gating, no change to `judge_pairs.py`'s instructions (e.g. discouraging "tie") in response to this. n=15 across four participants is still well within the scale this project's own discipline says not to generalize from — if anything, this batch is a concrete illustration of *why* that discipline exists: a single batch just swung the headline number by 34 points.

**[INTERPRETATION, resolving the two explanations above in explanation (a)'s favor, from the user's own contemporaneous account]** Asked what they judged the pairs on, the user volunteered — unprompted, before being told Claude's verdicts — that the 7 pairs "were all close and not really different." That matches Claude's own stated reasoning on 6 of the 7 ("near-synonyms," "interchangeable," "equally idiomatic") almost exactly. This favors explanation (a): the tie-vs-definite-pick pattern looks like an artifact of *this batch's pair selection*, not a real gap between Claude's and human judgment. These 7 words were chosen (2026-09-01) specifically for their unusually rich WordNet synonym sets, to get past this profile's earlier zero-yield problem (`DECISION_LOG.md` 2026-09-01-A/C/E) — that same richness produced candidates too close together to carry a real preference signal, so a forced A/B choice measured something other than quality judgment on most of them. **Methodological update for future batches, not a fix to any gate:** favor pairs with a demonstrable quality gap (checked before relay, same as the broken/awkward-pair screening already practiced) over whichever candidates are easiest to generate — a near-tie pair tests the forced-choice format's noise floor, not the question path (b) exists to answer.

**[DECISION, 2026-09-01, same day] A recognized-bad-test batch is kept in the record but separated from conclusion-drawing figures — never silently discarded.** Per direct instruction, `ingest_real_human_pair.py` gained an optional `pair_distinguishability` field (`"distinguishable"` default / `"near_synonym"`) and `summarize(exclude_near_synonym=True)`. The 7-pair batch above was tagged `"near_synonym"` retroactively (it was logged, and the problem diagnosed, before this mechanism existed); nothing was deleted. Two figures now exist side by side, and both should be reported together going forward, not just one:

- **All recorded pairs: n=15, 8/15 agree (53.3%).**
- **Conclusion-eligible pairs (excludes the recognized near-synonym batch): n=8, 7/8 agree (87.5%)** — identical to the figure standing before this batch, since the 7 near-synonym pairs are the only ones tagged out.

**[NOT DONE]** The near-synonym tag does not retroactively relabel or reinterpret the 6 "tie" verdicts as correct or incorrect — it only marks the batch as low-information for the specific question path (b) asks. Future batches get tagged at collection time (screened before relay, same discipline as the broken/awkward-pair exclusions), not after the fact from a disappointing aggregate number — the criterion is "does this pair have a real quality gap," decided before either verdict is known, never "did Claude and the human agree."

**[CORRECTION, 2026-09-01, same day]** Per direct, explicit follow-up instruction, the 7 near-synonym-tagged records described immediately above were removed from `real_human_pairs.json` outright (not just excluded via `exclude_near_synonym`) — a recognized-bad test, once recognized, is not kept mixed into the dataset conclusions get drawn from. The `pair_distinguishability`/`exclude_near_synonym` mechanism (2026-09-01-H) stays in the codebase for any future batch where filtering rather than deletion is preferred, but for this batch specifically, deletion is what happened. **Real human-vs-Claude comparison data, current and going forward: n=8, 7/8 agree (87.5%)** — the two-figure ("all recorded" vs "conclusion-eligible") framing immediately above is superseded by this correction, per this document's own append-only rule (the original entries are left as written, not edited, matching the precedent set when the first participant's data was dropped on 2026-08-30 — see `DECISION_LOG.md` 2026-08-30-W).

**[UPDATE, 2026-09-01, same day — final round across the three existing "friend" profiles, per direct instruction]** More natural sentences were added to each of friend_1's, friend_2's, and friend_3's existing profiles, using only words/sounds/phrases each had already declared (no new content invented on a friend's behalf, unlike the fifth participant's own, self-authorized expansion). friend_1 yielded 13 raw pairs, manually screened down to **7 clean, distinguishable pairs** (6 excluded: 1 grammar-broken, 5 wrong-meaning via the same declared word's several distinct verb senses — both already-documented failure classes, §2.3 and §2.6 respectively, no new mechanism). friend_2 and friend_3 yielded **zero new pairs** — every "found" outcome re-derived a pair already in hand from an earlier round; both profiles' remaining words continue to fail via mechanisms already on record and are treated as effectively exhausted for this architecture. Full record: `DECISION_LOG.md` 2026-09-01-J. The 7 friend_1 pairs are queued for relay, not yet judged as of this entry.

**[FACT, 2026-09-01, same day]** friend_1's 7 pairs were judged: 6/7 agree. Unlike 2026-09-01-G's since-removed batch, this disagreement is a genuine directional split (Claude picked A, the participant picked B), not a Claude-"tie"-vs-human-definite-pick artifact — consistent with these being real, distinguishable pairs, screened for a quality gap before relay. **Real human-vs-Claude comparison data: n=15, 13/15 agree (86.7%)**, spanning four distinct real participants (friend_1: 13; friend_2: 1; friend_3: 1). Still not a result to act on at this scale — no conclusion drawn, no LR.2/LR.3 change.

**[UPDATE, 2026-09-01, same day — the fifth participant (self) declared a second, distinct sound-class]** Per direct instruction, extended the same participant's profile with a new declared sound, word, and phrase (not a new person — still counted toward this participant's existing share, not added participant diversity). Harvest found 16 raw pairs; most re-derived the already-removed near-synonym batch (2026-09-01-G/I) or hit the already-known `sanitize_input()` grammar bug again (no new documentation needed for either). **2 new clean pairs** survived screening, both judged same-session: human and Claude agreed on both (2/2). One is a genuine, useful counter-example to the R13 phrase-gap pattern — full note: `ROADMAP.md` R13. **n=17, 15/17 agree (88.2%)**, spanning the same four participants (self's share: 2 of 17, the first survived data from this participant since 2026-09-01-I's removal). Still not a result to act on at this scale.

**[UPDATE, 2026-09-01, same day — new candidate words proposed for friend_2 and friend_3, chosen by the researcher (not self-reported by either participant), per direct instruction]** friend_2 and friend_3 were previously treated as exhausted at their own declared words. Per direct instruction, additional same-sound-class words were chosen and added to each profile — a different provenance than the self participant's own-authorized additions or a friend's own relayed answer, disclosed here for traceability. Selection basis: words matching the participant's already-declared sound(s), with a non-trivial WordNet synonym pool, favoring a single dominant sense over heavy polysemy (this session's own repeated WSD-wrong-sense finding argues against picking highly ambiguous words). friend_2 yielded 3 new clean pairs (3 excluded: 1 repeat of already-logged data, 1 grammar-broken via the recurring `sanitize_input()` bug, 1 unnatural/wrong-register). friend_3 yielded 1 new clean pair (5 excluded: 2 repeats, 2 wrong-sense meaning changes, 1 article-agreement-broken — all already-documented failure classes, no new mechanism). All 4 judged same-session: **2/4 agree** — a real, mixed batch, not a near-synonym artifact (Claude gave different verdicts on the identical candidate pair depending on sentence context, i.e. genuine context-sensitive judgment, not blanket indifference). **n=21, 17/21 agree (81.0%)**, spanning the same four participants (friend_1: 13, friend_2: 4, friend_3: 2, self: 2 — friend_1's share now 62% of the data, down from 76%, still dominant). Still not a result to act on at this scale.

**[UPDATE, 2026-09-01, same day — a large, deliberate push across all four existing profiles at once, per direct instruction to grow n substantially]** 5 more pairs each were generated against friend_1, friend_3, and self; friend_2 fell short at 3 despite adding another candidate word and more sentences (genuine diminishing returns, reported as measured — not padded to 5). All 18 pairs relayed and judged same-session: **11/18 agree**. Not a near-synonym artifact — this was a substantive batch with a real, legible pattern in the disagreements: on one declared word repeated across several sentences, Claude consistently favored one of its two candidates for sentences describing a publicly-admired figure and the other candidate for sentences describing a personal relation, while the human's picks favored one candidate almost uniformly with one exception — a real, substantive semantic disagreement about register, not noise. Full record (aggregate only, no participant content): `DECISION_LOG.md` 2026-09-01-P. **n=39, 28/39 agree (71.8%)**, spanning the same four participants — but participant concentration improved substantially: friend_1: 18, friend_2: 7, friend_3: 7, self: 7 (friend_1's share now 46%, down from 62%, no longer anywhere near dominant). The rate itself moved down with this batch, which is the expected, honest behavior of a growing sample surfacing real disagreement, not a problem to correct. Still not a result to act on at this scale — no conclusion drawn, no LR.2/LR.3 change.

**[DECISION, 2026-09-01, same day — a new system built, per direct instruction that the one-pair-at-a-time chat relay was wasting time]** Three additive pieces: `stage_lr/human_test_tool.html` (a static, offline, local-only page — never to be hosted — that lets a real participant click through a whole batch of pairs in one sitting instead of chat transcription), `stage_lr/merge_human_test_results.py` (joins that tool's output back with the original pairs and the Claude judgment step, then logs via `record_real_human_pair()` exactly as before), and `stage_lr/claude_only_pairs.py` — a genuinely separate track for pairs that don't need a real human verdict to be useful dataset volume, judged by Claude alone, structurally kept apart from the human-comparison figures so it can never be silently pooled into them. Demonstrated end-to-end with a first small batch (n=4, a separate, additional dataset from the n=39 figure above). Full record: `DECISION_LOG.md` 2026-09-01-Q.

**[FACT, a second genuinely new finding, disclosed not fixed — 2026-09-01, third real participant / counted "friend 2" per the 2026-08-30 renumbering]** First harvest attempt (12 sentences, a real declared profile of 3 words + 1 sound-class set + 1 phrase) yielded **0** clean pairs. Root-caused against the real pipeline, not guessed: two of the three declared words are polysemous in WordNet; `semantic.disambiguate_synset()` (word-sense disambiguation, added per `REFORMULATION_PROBLEM_MAP.md` §5 item 2) narrows candidate generation to a single sense before scoring, and for this participant's specific words that single sense happened to have only one viable synonym, which then failed the live 0.85 `MIN_SEMANTIC` threshold — while a different, equally valid sense of the same word had several synonyms that plausibly would have passed. `REFORMULATION_PROBLEM_MAP.md` §2.6 already named this exact cost in the abstract on 2026-08-17 ("single-sense candidate pools are sometimes smaller and score lower... even when correct"); this is the first concrete, measured instance of it. Full trace: `REFORMULATION_PROBLEM_MAP.md` §2.6, 2026-09-01 update; `DECISION_LOG.md` 2026-09-01-A.

**[DECISION] Not fixed, per the architecture freeze.** `MIN_SEMANTIC` and `disambiguate_synset()` were left untouched. The only change made was adding 13 more natural sentences (same declared words, not written to dodge the threshold) to the same participant's input file — matching path (a)'s own batch-3/4 precedent of adding sentence material, not changing the engine. Re-run on 25 sentences total yielded **1** clean pair.

**[LIMITATION]** 1/25 is a real, low yield, reported as measured rather than padded by retrying until a better number appears. It suggests real, naturally-declared (as opposed to synthetic-template) profiles with common polysemous words may be structurally harder for this architecture to harvest usable pairs from than path (a)'s templates have been — consistent with, and now adding a second concrete data point to, this section's standing finding that path (a) cannot substitute for path (b). The single found pair was judged same-session (both verdicts agreed, folded into the n=7 figure above).

**[FACT, a third and fourth genuinely new finding, disclosed not fixed — 2026-09-01, fourth real participant / counted "friend 3"]** Harvest against a real declared profile (1 sound-class, 1 word, 1 phrase; 20 natural sentences) produced **zero usable pairs**. Two independent mechanisms, both root-caused against the real pipeline: (1) the declared word's most common senses have no single-word WordNet synonym at all — a more fundamental gap than "friend 2"'s WSD-narrows-to-a-weak-candidate case just above, though the same `disambiguate_synset()` mechanism was involved; (2) the declared phrase produced exactly one candidate pair, and it was broken — a word inside the phrase also independently matched the declared sound-class, so it was flagged and substituted as an ordinary single word (declared phrases have no consumer anywhere in `reformulate.py` at all — `ROADMAP.md` R13, an already-open item, not a new discovery), destroying the fixed expression. Full trace: `ROADMAP.md` R13, 2026-09-01 update; `DECISION_LOG.md` 2026-09-01-C.

**[DECISION] The broken phrase pair was not shown to the participant.** Excluded before relay, same "never ship a bad guess" discipline `REFORMULATION_PROBLEM_MAP.md` §2.4 already established for hardcoded idiom spans — this case just wasn't caught by that guard, since it only covers a fixed list, not a speaker's own declared phrases. No gate, threshold, or WSD/phrase-matching logic was changed on `main` or `stage-lr`, per the architecture freeze.

**[UPDATE, 2026-09-01, same day]** Per direct instruction, the participant's declared-word list was expanded (still the same sound-class and phrase) and the harvest re-run on a larger, still-natural sentence set. This produced one more instance of the same broken phrase pair (excluded again, no new information) and one new, legitimate-but-awkward pair from a different declared word (an idiomatic/informal sense of a common noun, literally pluralized by the substitution — a naturalness cost, not a nonsense one, distinct from both mechanisms above; flagged to the user before relaying rather than silently sent or silently withheld). The user chose to send it; the participant and a same-session blind Claude verdict agreed on the same candidate. Folded into the n=8 figure above.

**[FACT, a fifth genuinely new finding, disclosed not fixed — 2026-09-01, fifth real participant]** Harvest against a real declared profile (1 sound-class, 2 words, 1 phrase; 25 natural sentences) produced **zero usable pairs**, for three distinct, non-overlapping reasons — the most mechanisms found for any single profile so far:

1. One declared word had a clean, correct, single-word synonym that passed similarity, antonym, and every other check — and was then rejected every single time by `semantic.logical_consistency_check()` (the frozen pipeline's own Phase 11C NLI gate), which judged the substitution a "contradiction." Re-tested across 4 independent sentences: the same word pair was rejected in all of them (2 by NLI, 2 by the similarity score dropping just under threshold in that particular context) — never once accepted. This is a **new mechanism**, distinct from both the WSD-narrowing and no-synonym-exists shapes found earlier, and the first concrete instance of a literature-flagged NLI risk this project's own §3.7 research pass had marked untested. Full trace: `REFORMULATION_PROBLEM_MAP.md` §3.7, 2026-09-01 update.
2. The other declared word has exactly one usable synonym in WordNet (via hypernym expansion, since it has no direct lemma of its own) — first-stage substitution succeeds every time, but path (b)'s methodology needs a *second*, different candidate to form a pair, and none exists. Same no-true-synonym shape already found twice before (friend_2, friend_3), not a new mechanism.
3. The declared phrase was never engaged at all — the word inside it that carries the declared sound is a function word/stopword, which `reformulate.py` never flags as substitutable by design. Unlike friend_3's phrase case, this doesn't produce a broken output — it produces silence: the participant's declared phrase difficulty is simply never addressed, anywhere, in any sentence. A different-flavored consequence of the same already-known `ROADMAP.md` R13 gap (phrases have no consumer), not a new item.

**[DECISION]** Nothing shown to the participant this round — no candidate cleared every gate. No gate, threshold, or NLI/WSD/phrase-matching logic was changed on `main` or `stage-lr`, per the architecture freeze. `real_human_pairs.json` and the n=8 figure above are unchanged by this entry.

**[UPDATE, 2026-09-01, same day]** Per direct instruction, 5 more everyday same-sound words were chosen and added to this participant's profile (not asked of the participant again), and 20 more natural sentences written. This produced 11 candidate pairs — the highest single-profile yield this session — and, on manual quality review before any relay (per this session's own practice), two more new findings:

**[FACT, sixth genuinely new finding]** Indefinite-article agreement ("a" vs "an") is not adjusted anywhere in the substitution pipeline when a replacement changes the following word's leading sound — confirmed via a direct, real `reformulate()` call, not inferred. `REFORMULATION_PROBLEM_MAP.md` §2.3 updated.

**[FACT, seventh genuinely new finding]** WSD can pick an outright *wrong* sense for a short, common, locally-ambiguous adjective — not just a narrow-but-correct one, as found earlier for friend_2's profile. A literal/physical sense was replaced using candidates from an unrelated figurative/emotional sense, changing the sentence's actual claim; confirmed directly via `disambiguate_synset()` on the exact sentence, reproduced on 2 sentences. `REFORMULATION_PROBLEM_MAP.md` §2.6 updated as a sharper variant of the already-known cost.

Also reproduced (third instance, no new documentation needed): `sanitize_input()`'s infinitive-after-"to" conjugation bug (`DECISION_LOG.md` 2026-08-30-R), this time surfacing in `sanitize_input()`'s own pre-substitution correction pass.

**[DECISION]** Of the 11 pairs found, 4 carried a defect (1 grammar-broken via the `sanitize_input()` bug, 2 meaning-changed via the wrong-sense WSD finding, 1 article-agreement-broken) and were excluded before relay — same discipline as every prior broken/borderline pair this session. **7 clean pairs remain queued for the participant's judgment**, not yet relayed as of this entry. No gate, threshold, WSD, or inflection logic was changed on `main` or `stage-lr`.
