# DECISION_LOG.md — Full decision history

**Format note (read before trusting anything below).** Practice.md §14
requires this log to be written continuously, at the time each decision
is made, with four parts: what was done, alternatives considered, why,
and measured result. The entries below were **not** written at decision
time — they are reconstructed retroactively, in a single pass, from git
commit messages, code comments, and README/AUTH_README/changes.md. That
reconstruction is itself a limitation (§5): "alternatives considered" and
"measured result" are frequently unavailable because the original author
never recorded them, and this is noted per entry rather than invented.
From this point forward, new entries should be written live, not
backfilled.

Entries are ordered chronologically and dated from `git log` where a
commit maps cleanly to the decision. Append-only: later entries correct
earlier ones explicitly; nothing below is edited after being added.

---

### 2026-06-05 — Project bootstrap
**What was done:** Initial commit; README, `.gitignore`, `requirements.txt` added.
**Alternatives considered:** Not recorded.
**Why:** Not recorded.
**Measured result:** N/A.
**Category:** Engineering decision (unrecorded rationale).

---

### 2026-06-07-A — Password hashing chosen: SHA-256, not bcrypt
**What was done:** `user_store.py` hashes passwords with unsalted SHA-256
(`_hash_password`), documented in-line as "swap this line for
`bcrypt.hashpw()` in production," with the exact 2-line replacement given
in both `AUTH_README.md` and `README.md`.
**Alternatives considered:** bcrypt (explicitly named and deferred, not
rejected).
**Why:** Not stated beyond "simplicity" (README's own word). Plausibly a
reasonable choice for a research prototype's storage layer, but not
argued for on the record beyond that.
**Measured result:** N/A — no security review performed.
**Category:** Engineering decision, explicitly labeled a placeholder by
its own authors — treat as a **named limitation**, not a settled choice:
the storage layer is designed to be swappable, but has not yet been
swapped, and the current state should not be assumed safe for real
credentials.
**Note added by this review (2026-08-08):** the risk this defers against
is not hypothetical here — see entry 2026-06-13-A below. A deferred
constraint that "the infra to fix this doesn't exist yet" no longer
applies once real user JSON is sitting in the repo; Practice.md §3's
"old constraint outliving its evidence" pattern is directly relevant and
should be re-checked, not re-assumed.

---

### 2026-06-07-B — Multi-source synonym retrieval: WordNet + Datamuse, not WordNet alone
**What was done:** `engine.py`'s `SynonymEngine` combines NLTK WordNet
with the Datamuse API (`rel_syn=` + `ml=`), ranked by Zipf frequency.
**Alternatives considered:** WordNet alone (implied baseline).
**Why:** Comment in `engine.py`'s module docstring and this review's
earlier repo-review pass both note WordNet-only coverage gaps for some
query words, but no specific measured rate is cited in the code or
README for *this* decision (a related, later measurement — "~15% of test
nouns" — appears in a different commit's message; see entry
2026-06-08-B, which is about a different, later change and should not be
conflated with this one).
**Measured result:** Not recorded at the time of this specific decision.
**Category:** Engineering decision with an informally-stated rationale,
not yet a pre-registered (§8) comparison of single-source vs.
multi-source candidate quality.

---

### 2026-06-08-A — MIN_SEMANTIC threshold sweep produces an unactioned finding
**What was done:** `tests/threshold_sweep.py` added specifically to sweep
the SBERT `MIN_SEMANTIC` gate. Per the commit message itself: *"recommends
MIN_SEMANTIC~0.80 vs current 0.85; per-POS would help. Default
unchanged."*
**Alternatives considered:** N/A (this is itself the alternative-testing step).
**Why:** To check whether the hand-picked `0.85` gate value was well
calibrated.
**Measured result:** **Observation** (per Practice.md §5) — the sweep's
own output suggested `~0.80` might be a better default, and separately
suggested per-POS thresholds could help, but the code's default was
deliberately left at `0.85`.
**Category:** This is exactly the kind of finding Practice.md §6 asks to
be recorded as evidence *without* being auto-applied — and it was, in
fact, handled correctly at the time: the finding was recorded (in the
commit message, if not in a durable eval doc) and the threshold was
**not** silently retuned. What's missing, per this review, is that the
finding never made it into a durable, discoverable record (no
`VALIDATION.md` existed) — so a future contributor has no way to find
this except by reading `git log` line by line, which is precisely the
failure mode a living `VALIDATION.md`/`DECISION_LOG.md` is meant to
prevent. See `VALIDATION.md` and `ROADMAP.md` for how this is carried
forward.

---

### 2026-06-08-B — Semantic scoring re-weighted: 0.65/0.35 → 0.90/0.10, threshold 0.72 → 0.85
**What was done:** `semantic.py`'s module docstring documents this
explicitly as an "UPDATED SCORING STRATEGY (v2)": semantic weight raised
from 0.65 to 0.90, frequency weight lowered from 0.35 to 0.10, and the
minimum-semantic gate raised from 0.72 to 0.85, with frequency
additionally changed from raw Zipf to log-normalized.
**Alternatives considered:** The prior 0.65/0.35 scheme (the change is
framed explicitly as a correction to it).
**Why (as stated in the code):** The old weighting let "contextually weak
words like 'container', 'side', or 'trust' ... survive due to popularity
rather than meaning" — an example is given (`"stress"` pulling in
verb-hypernym contamination) but no dataset-level measurement is cited.
**Measured result:** Not recorded as a dataset-level number — the
rationale is example-driven ("empirically: ≥0.85 → excellent... 0.72–0.85
→ likely drift"), which is closer to an informally-observed pattern than
a reported metric with a stated n. This is a real change to a
consequential threshold made on example-based reasoning, not a
pre-registered comparison (§8).
**Category:** Engineering decision, reasonably argued, but its evidentiary
basis is weaker than the confident wording ("empirically") in the code
comment implies. Flagged as a place where Practice.md §5's "don't mix
hypothesis-confidence with fact-confidence" applies directly: the comment
reads as more settled than the evidence behind it.
**Important downstream note:** this change directly **contradicts** the
still-unactioned finding in entry 2026-06-08-A (the threshold sweep
recommending ~0.80, run the same day) — the sweep ran against a threshold
that had already been raised to 0.85 by this same day's other commits,
and its own recommendation to lower it back toward 0.80 was not applied.
This tension between two same-day decisions is exactly the sort of thing
a live decision log would have surfaced immediately; it only became
visible in this backfilled pass. **This is not resolved here** — see
`ROADMAP.md`.

---

### 2026-06-08-C — README's ranking description not updated to match 2026-06-08-B
**What was done:** N/A — this is an absence, not an action: `README.md`'s
"Architecture Notes" section and "What It Does" pipeline description
still describe the pre-2026-06-08-B scheme (`0.65 × semantic + 0.35 ×
frequency`) as of this review.
**Category:** Not a decision — a **limitation** (documentation drift,
§5), noted here so it's discoverable from the decision log rather than
only from `DOCS.md`'s file-map notes.

---

### 2026-06-08-D — Allowlist implemented as a hard lock, not a soft preference
**What was done:** Per commit `b04a4a6` ("Task B"), `rewrite()` gained an
`allowlist` parameter; the app was changed to pass allowlisted words as
`allowlist=` rather than folding them into `blocked_words`.
**Alternatives considered:** Treating allowlisted words the same as
blocked words (the pre-existing behavior this commit replaced).
**Why:** Not elaborated beyond the commit message; the distinction (never
substitute vs. never substitute-*because-of-stutter-risk*) is a real
semantic difference reflected consistently in `grammar.py`'s
`SentenceRewriter.rewrite()`.
**Measured result:** Not recorded.
**Category:** Engineering decision, informally justified, functionally
verified by this review to be implemented consistently in the current
code.

---

### 2026-06-08-E — Low-RAM survivability: `low_cpu_mem_usage`, thread capping, wordlist downgrade
**What was done:** Across several commits culminating in `d292cfb`
("low-RAM model loading"), the repo added: `accelerate` +
`low_cpu_mem_usage=True` for transformer loading (`rephrase.py`), BLAS/
OpenMP thread capping before any heavy import (`paths.py`), and an
automatic, irreversible downgrade from the "best" to the "small"
`wordfreq` wordlist on `MemoryError` (`freq.py`).
**Alternatives considered:** Not explicitly enumerated, but the
README's "Memory note" section explains the failure mode being avoided
(a transient double allocation during `from_pretrained`, and OpenBLAS
pre-allocating per-core buffers).
**Why:** Documented concretely and specifically in code comments and the
README (unusually well-justified relative to other decisions in this
log) — e.g. "OpenBLAS otherwise pre-allocates per-thread buffers sized
for every CPU core... a large upfront allocation that fails on
RAM-constrained machines."
**Measured result:** Not a formal benchmark, but the reasoning is
mechanistic and specific enough to be a credible engineering decision
rather than a guess. This is the one area of the codebase where the
"why" is unusually well recorded already.
**Category:** Engineering decision, well-justified relative to the rest
of this log.

---

### 2026-06-13-A — User account JSON files committed to the repository
**What was done:** `users/default.json` and `users/bobcat.json` — each
containing a SHA-256 password hash and a phoneme profile — are present in
git history and the current working tree.
**Alternatives considered:** N/A — this appears to be an oversight, not a
deliberate choice; both `README.md` and `AUTH_README.md` state `users/`
is gitignored, but the actual `.gitignore` only excludes
`users/*.fluency_profile.json`, not the account files themselves.
**Why:** No rationale exists for this being intentional; the documentation
contradicts the actual `.gitignore` contents, which is itself evidence
this was not a deliberate decision.
**Measured result:** Confirmed present via `git log --oneline -- users/`
and direct inspection during this review (2026-08-08).
**Category:** **Limitation** (§5) with real severity — this is committed,
weakly-hashed credential material in what is presented as a public
GitHub repository. Practice.md doesn't have a "security incident"
category, but this is closest to a limitation with immediate,
non-research-priority urgency: it is not a "which architecture is
better" question, it's a "credential material is exposed right now"
question. Recorded here per §14's discipline (record it, don't fix it
silently) — remediation itself belongs to whoever owns repository
access, and is out of scope for a documentation pass under §19's protocol
(step 9, "implementation," is explicitly deferred by that protocol).

---

### 2026-08-15-A — Repository narrowed to the text reformulation module; audio/ASR/voice code moved to `out_of_scope/`
**What was done:** Per an explicit user-directed scoping pass (not a
research decision — a repository-organization one), everything specific to
audio capture, ASR, and audio-timing-based disfluency detection was moved
out of the live import graph:
  - `voice.py` (browser STT/TTS UI) → `out_of_scope/voice.py`
  - `profiling/asr.py` (`CrisperWhisperASR`) → `out_of_scope/profiling/asr.py`
  - `profiling/detect.py` (rule-based ASR-timing disfluency detector) →
    `out_of_scope/profiling/detect.py`
  - `sample_stutter.json` (a test fixture for the above) →
    `out_of_scope/sample_stutter.json`

  `app.py` had its voice-input widget, TTS "speak" buttons, live-STT
  autorefresh polling, and the "Voice / transcript profile update"
  microphone/upload expander removed, along with the four helper functions
  that backed that expander (`_process_profile_upload`,
  `_render_profile_update_result`, `_safe_upload_name`,
  `_profile_safe_events`). `profiling/__init__.py` no longer re-exports
  `CrisperWhisperASR`/`VerbatimToken`/`detect_disfluencies`.
  `tests/roadmap_test.py` was split: its three ASR/detector tests moved to
  `out_of_scope/tests/roadmap_test_audio.py` (re-pointed at the archived
  package via `sys.path`, confirmed still runnable); its three
  `SpeakerDifficultyProfile`/`DifficultyAwareRewriter` tests stayed.
  `tests/app_test.py` had its two assertions for the now-removed
  microphone/upload UI elements dropped. `streamlit-mic-recorder` was
  removed from `requirements.txt` (its only caller was `voice.py`).
  `README.md` and `DOCS.md` were rewritten to describe the narrowed scope,
  state Speech-AI-the-project vs. this-repo-the-module explicitly, and fix
  the pre-existing `0.65/0.35` vs. actual `0.90/0.10` semantic-weight drift
  (`DECISION_LOG.md` 2026-06-08-C) while already touching that section.
**Alternatives considered:** Deleting the audio-facing files outright
instead of archiving them. Rejected per the user's explicit instruction not
to destroy historical implementation work — `out_of_scope/` preserves both
the code and its test coverage, with a README explaining why it's there and
that it's the natural starting point for a separate Audio Module repo.
**Why:** This repository's stated scope (per `CLAUDE.md`/`HANDOFF.md`) is the
text reformulation module of a two-repository system; the audio-facing code
had accreted here anyway during earlier feature work (see 2026-06-13's
`profiling`/mic-related commits in `CHANGELOG.md`). Narrowing the repo to its
actual scope is an organizational decision, explicitly **not** a technical
redesign: no rewrite algorithm, semantic threshold, difficulty formula, or
scoring weight was changed as part of this entry — the drift fix above
corrects a *documentation* number to match code that was already there,
not a code change.
**Measured result:** `tests/roadmap_test.py` (narrowed) — 3/3 pass.
`out_of_scope/tests/roadmap_test_audio.py` (extracted) — runnable standalone
against the archived package (not re-verified line-for-line against its
pre-move behavior, but unmodified other than the sys.path adjustment).
`tests/app_test.py` — all scenarios pass. `tests/smoke.py` output is
byte-identical to the committed `tests/baseline_sbert.txt` — confirms the
core rewrite pipeline's behavior is unchanged by this pass.
**Category:** Engineering/organizational decision, directly instructed and
scoped by the user, with before/after test parity as the measured check
rather than a quality claim (this pass makes no claim about rewrite quality
either way — see `VALIDATION.md`, still unchanged by this entry).
**Left deliberately untouched, flagged as ambiguous — see next session:**
  - `users/default.json` / `users/bobcat.json` remaining committed
    credential material (2026-06-13-A / `ROADMAP.md` R0) — a security
    remediation, not a scoping question; out of this entry's scope.
  - `auth.py` / `user_store.py` / `users/` — multi-user account
    infrastructure. Not audio-related, so not moved, but also not obviously
    "text reformulation" either; it's cross-cutting infra this module
    happens to depend on for per-speaker profiles. Left in place; whether it
    belongs in this repo long-term is a question for the user, not decided
    here.
  - `config.yaml`'s `profiling.detection` sub-block (repetition/prolongation/
    block/filler thresholds) is now dead weight in the live config — it's
    only consumed by the archived detector. Left in place rather than
    pruning `config.yaml`'s structure, to avoid touching a shared config
    file beyond the scope of a pure move.
  - `torchvision` in `requirements.txt` appears unused by any `.py` file in
    the repo (grepped, zero hits) — but this predates and is unrelated to
    the audio/text boundary, so it was left alone rather than pruned as
    part of this pass.

---

### 2026-08-15-B — Stage 3 literature/research pass completed; `RESEARCH.md` added
**What was done:** Per an explicit user-directed research stage, conducted a
literature/technical-approach review across paraphrase generation, lexical
substitution, sentence simplification, semantic-preservation evaluation,
controlled/constrained generation, phoneme-aware NLP and speech
accessibility, and personalized generation — then used those findings to
critically re-assess this repository's own implementation, component by
component, including the two-pipeline duplication question (`ROADMAP.md`
R5) and the fundamental-weakness questions the user posed directly. Recorded
as `RESEARCH.md`. This closes `ROADMAP.md` R3 ("run the literature pass
called for in §7") — see that file's updated status.
**Alternatives considered:** N/A — this is itself an evidence-gathering step,
per Practice.md §19 steps 1–8, not a decision between alternatives.
**Why:** The repository's own `VALIDATION.md` (§5, "explicit non-findings")
already named this literature pass as the single most overdue gap in the
project's evidence base — several load-bearing constants (`MIN_SEMANTIC`,
the difficulty formula's weights) had been defended by in-code argument
rather than either measurement or literature grounding. This pass supplies
the literature grounding half of that gap (measurement against real speaker
data remains blocked on the Audio Module, per `ROADMAP.md` R2 — unchanged by
this entry).
**Measured result:** N/A in the Practice.md §8 sense — this is a literature
review, not an experiment with a reportable outcome. What it *did* produce:
one directly-comparable prior system (`Fluent`, ASSETS 2021) whose problem
framing matches this project's closely enough to be a genuine, checkable
reference point (see `RESEARCH.md` §2.F), and several literature-grounded
reasons — not just code-elegance ones — to treat specific existing components
as sound (the phoneme filter's position in the pipeline, POS-gated WordNet
retrieval, the profile's interpretable-score design) versus genuinely
under-evidenced (the SBERT threshold, the difficulty formula's weights and
functional form, the assumption that substitution-in-place is always
sufficient).
**Category:** Research/evidence-gathering, explicitly **not** an
engineering decision — no threshold, weight, model, or algorithm changed as
a result of this entry, per the user's explicit Stage 3 restriction. Per
§19, this authorizes nothing; Stage 4 (or a future session) is where any of
`RESEARCH.md`'s recommendations would become an actual decision, against
this evidence, with the user.
**Note:** `RESEARCH.md` distinguishes established literature findings from
this project's own interpretation of them, from untested hypotheses, from
forward-looking architecture recommendations — see that file's legend. Cite
individual claims from it with that distinction intact rather than flattening
"the research says X" when the honest label is "we interpreted the research
to suggest X for our specific case."

---

### 2026-08-15-C — Stage 4A: new user-declared speaker difficulty profile foundation added, kept separate from the reformulation engine
**What was done:** Added a new persistent, structured "speaker difficulty
profile" — three explicitly independent lists (`sounds`, `words`,
`phrases`), each entry carrying `source`/`added_at`/an empty forward-
compatible `meta` dict, words additionally carrying a best-effort CMU-dict
pronunciation for display only. New files: `difficulty_profile.py` (schema,
validation, normalization, dedup logic), `tests/difficulty_profile_test.py`
(26 tests). Extended (not replaced): `phonetic.py` gained one new, purely
additive function, `full_pronunciation()` (informational only, no
scoring/gating use); `user_store.py` gained `load_difficulty_profile()` /
`save_difficulty_profile()`, the latter also refreshing the legacy
`phoneme_profile.stutter_patterns`/`.blocked_words` mirror in the same
write. `app.py`'s old "Phoneme Profile — Stuttering Patterns" panel and the
"Blocklist" half of the Blocklist/Allowlist expander (which were, on
inspection, two separate UI surfaces independently editing the same
`blocked_words` list — a pre-existing redundancy resolved by this change,
not introduced by it) were replaced by one consolidated "Speaker Difficulty
Profile" panel: three columns (Sounds/Words/Phrases), each with the
already-working add-input-plus-button / per-entry-remove-button pattern
reused from the old Blocklist column rather than reinvented, plus a
"pick a word from your current text" convenience dropdown for the Words
column. The Allowlist (a genuinely different, untouched concept — words
that must never be substituted) stays in its own expander.
**Alternatives considered:**
  - A hand-rolled, JS-based inline "select text in place, a floating
    button appears" component — the task's own suggested interaction.
    Rejected for this pass: Streamlit has no native support for reading
    browser text selection (a documented open feature request on
    Streamlit's own forum), and building a custom bidirectional component
    would mean shipping unverified browser JS with no way to test it in
    this environment — the exact pitfall already on record for `voice.py`'s
    `st.iframe` usage. The technical approach is fully specified as a
    deferred future item in `PROBLEM_FORMULATION.md` §7.2 rather than
    built untested.
  - Auto-deriving `sounds` entries from a flagged word's phonemes.
    Rejected — directly conflates word-level and phoneme-level difficulty,
    which the task's own instructions (§6/§13) explicitly require staying
    separate; a psycholinguistic basis for keeping them separate is also in
    `RESEARCH.md` §1.2/§2.F.
  - SQLite for profile persistence. Rejected — no query pattern this data
    volume justifies; would add a second persistence mechanism alongside
    `user_store.py`'s existing, working JSON pattern for no offsetting
    benefit. Full comparison table in `PROBLEM_FORMULATION.md` §4.
  - Keeping `phoneme_profile` as an independently-user-edited list
    alongside the new `difficulty_profile`. Rejected — real drift risk,
    the same class of problem `RESEARCH.md` §6 already flagged for this
    repo's two rewrite pipelines. Made a derived, auto-refreshed mirror
    instead, written in the same file operation as the new profile so the
    two can never observably disagree.
**Why:** Per the task's explicit framing: the profile is one of the most
important inputs to the eventual reformulation architecture, and needed a
clean, correctly-scoped foundation before any reformulation logic changes.
Full reasoning for every representation choice (ARPAbet-vs-IPA, word-vs-
phoneme independence, phrase representation, JSON-vs-SQLite) is in
`PROBLEM_FORMULATION.md`, not repeated here.
**Measured result:** `tests/difficulty_profile_test.py` — 26/26 pass
(add/remove/dedup per category, text edge cases, pronunciation derivation
including the OOV case, persistence across a simulated restart, legacy-
profile migration firing exactly once). `tests/app_test.py` — extended with
a new scenario exercising the actual Streamlit widgets end to end (add
word/sound/phrase, confirm rendered, confirm legacy session-state mirror
updates without re-login, remove, confirm removal rendered); all scenarios
pass. `tests/roadmap_test.py` (3/3), `tests/persistence_test.py` — both
still pass unmodified in behavior. `tests/smoke.py` — **byte-identical**
output to the committed `tests/baseline_sbert.txt`, i.e. direct, checkable
evidence the reformulation pipeline's actual behavior is unchanged by this
stage, not merely an assertion that it should be.
**Category:** Engineering decision, directly scoped and instructed by the
user, with a research pass (documented in `PROBLEM_FORMULATION.md`)
preceding implementation per the task's own required workflow order.
**Left deliberately unresolved, flagged for the next stage — see
`ROADMAP.md`:**
  - The new, user-declared `DifficultyProfile` and the old, learned/EWMA
    `SpeakerDifficultyProfile` (`profiling/profile.py`, unchanged, still
    driving `rewrite/`) are now two different "difficulty" representations
    that don't talk to each other. This is the direct, correct consequence
    of not touching the reformulation engine this stage, not an oversight —
    but it needs reconciling before (or as part of) the actual
    reformulation redesign.
  - `phrases` has no consumer anywhere in the current pipeline — declared
    and persisted, not yet matched against or acted on by anything.
  - The inline text-selection interaction remains unbuilt, specified only.

---

### 2026-08-16-A — Stage 4A refinement: word-specific sound patterns; multi-user system removed
**What was done:** Two changes, requested together, both to the profile
foundation only (reformulation engine untouched).

*(1) Word-specific sound patterns.* `DifficultyEntry` gained a
`problem_phones` field (words only) — a user-selected subset of the word's
own `pronunciation`, representing "within THIS word specifically, these
sounds are the problem," distinct from both word-level difficulty (no claim
about why) and global sound difficulty (applies everywhere). New
`DifficultyProfile` methods: `set_word_pattern()` (validates the phones are
actually a subset of the word's real pronunciation — never trusts the
caller), `clear_word_pattern()`, `add_sound_from_phones()` (the *only* path
from a word pattern to a global `sounds` entry, always an explicit,
separate call). New `app.py` UI: a 🔍 toggle per word entry opens an inline
panel (`_render_pattern_editor`) listing the word's phones as individually
keyed checkboxes, each labeled with a friendly gloss via a new
`phonetic.friendly_phone_label()` / `ARPABET_EXAMPLE_WORD` table (all 39 CMU
phones) — researched against real dictionary "pronunciation respelling"
practice, not invented. `st.dialog` was considered for this panel and
rejected: AppTest has a documented, open bug (streamlit/streamlit#9786)
where button clicks inside a dialog don't execute during automated testing,
which would have meant shipping an unverifiable interaction — this
project's standing rule since Stage 4A's original text-selection decision.

*(2) Multi-user system removed.* `auth.py` and `user_store.py` deleted
(`git rm`). The app now loads one persistent default profile automatically
— no login screen, no registration, no account switching, no sidebar user
badge/logout. New `profile_store.py` replaces `user_store.py`'s storage
role, keeping a `profile_name` parameter (defaulting to `DEFAULT_PROFILE =
"default"`) everywhere rather than hardcoding single-user-ness away, per
the task's explicit instruction that future multi-profile support must stay
possible. The on-disk schema dropped `password_hash` (no auth = meaningless)
and `phoneme_profile` (see below) — `users/default.json` and the now-removed
`users/bobcat.json` were rewritten to the clean schema as part of this
change (bobcat, a second test account with no purpose under a single-profile
design, was deleted outright, `git rm`).

*(3) A consequence of (2) that changed (1)'s original design, not just
removed code around it:* Stage 4A's `phoneme_profile` mirror existed
specifically to be read by `auth.py::_load_user_into_session()` at login
time. With no login step, that mirror has no reader left to serve, so it
was removed entirely (not renamed, not kept "just in case") —
`stutter_patterns`/`blocked_words` are now derived **purely in memory**,
once per session, directly from the loaded `DifficultyProfile`, by
`app.py`'s own `_sync_legacy_session_from_profile()` (unchanged from Stage
4A) — one fewer persisted field that could drift from the profile it
mirrors.
**Alternatives considered:**
  - Archiving `auth.py`/`user_store.py` into an `out_of_scope/`-style
    folder instead of deleting. Rejected — that folder represents
    audio/ASR/voice concerns specifically (Stage 2's own definition); an
    auth layer doesn't belong there, and git history already preserves the
    files without needing an in-tree copy — keeping one would be exactly
    the "unnecessary compatibility layer" the task instructs against.
  - `st.multiselect` for phone selection instead of per-position
    checkboxes. Rejected — a word with a repeated phone (same ARPAbet code
    at two positions) produces colliding/ambiguous multiselect options;
    checkboxes keyed by position have no such collision.
  - Auto-creating a global sound entry whenever `problem_phones` is set.
    Rejected outright — this is precisely the conflation the task's central
    new requirement exists to prevent.
  - Hardcoding `DEFAULT_PROFILE` with no parameter anywhere (simpler code,
    fewer function arguments). Rejected — the task is explicit that
    removing the *auth UI* must not make reintroducing multi-profile
    support later a data-model change.
**Why:** Per the task's own framing: a word being flagged difficult does
not tell the system *what* about it is difficult, and the previous design
had no way to capture that distinction — a genuine, named gap in Stage 4A's
own foundation, not a hypothetical one. The multi-user removal was
independently requested (development/testing did not need it) but the task
was explicit that removing it must not foreclose reintroducing it later,
which shaped `profile_store.py`'s API design directly.
**Measured result:** `tests/difficulty_profile_test.py` — 38/38 pass (26
carried over + 12 new, covering pattern set/clear/validate/promote/persist
and that no global sound is ever created implicitly). `tests/app_test.py` —
extended to 6 scenarios, including one that clicks the actual phone
checkboxes by widget key, saves, and asserts
`st.session_state.stutter_patterns` is still empty afterward (i.e., no
global sound leaked from a word-specific selection) — all pass.
`tests/persistence_test.py` — rewritten (its only path depended on the
deleted `auth.py`) to test `profile_store.py` directly; passes.
`tests/roadmap_test.py` (3/3, unmodified) and `tests/smoke.py`
(byte-identical to `tests/baseline_sbert.txt`) confirm the reformulation
pipeline's behavior is still completely unaffected.
**Category:** Engineering decision, directly scoped and instructed by the
user. Supersedes the parts of `DECISION_LOG.md` 2026-08-15-C describing the
`phoneme_profile` mirror as persisted/kept-in-sync-on-disk — as of this
entry, it no longer exists on disk at all; that entry is not edited (this
log is append-only) but should be read with this correction in mind.
**Left deliberately unresolved, flagged for the next stage — see
`ROADMAP.md`:**
  - Reconciling the new `DifficultyProfile` with the old, learned
    `SpeakerDifficultyProfile` remains open (unchanged from 2026-08-15-C) —
    if anything, slightly more consequential now that word-specific
    patterns add a third kind of difficulty signal alongside the two
    profiles' existing ones.
  - `problem_phones`, like `phrases` before it, has no consumer in the
    reformulation pipeline — declared and persisted, not yet acted on.
  - Committed credential material from *before* this change (old git
    history containing `users/default.json`/`users/bobcat.json` with
    password hashes, `DECISION_LOG.md` 2026-06-13-A) is **not** remediated
    by this entry — rewriting published git history is a separate,
    deliberate action this entry does not take without explicit
    authorization; only new writes are affected.
