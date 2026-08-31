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

---

### 2026-08-16-B — Foundation audit: two real ambiguities found and fixed by testing, not just review
**What was done:** Before treating the Stage 4A + refinement profile
schema as a finished foundation, checked it directly against real data
(CMU dict lookups, actual round-trips through `phonetic.normalize_pattern`)
for every question in the user's audit request — unambiguous
interpretation per category, cross-entry ambiguities, missed cases
(multiple pronunciations, same-word-different-context, repeated words,
phrase/word overlap, allowlist overlap, reason-less word flags), and
over-engineering. Two real, previously-undetected issues were confirmed
with actual test data and fixed; the rest were checked and either already
correct (verified, not assumed) or named as genuinely out of scope.

*Fix 1 — heteronym ambiguity.* `phonetic.full_pronunciation()` always uses
CMU dict's first-listed pronunciation variant. Verified directly this is a
real, common case, not a rare one: `cmu["read"]` has 2 variants,
`cmu["the"]` has 3, `cmu["object"]`/`cmu["often"]`/`cmu["route"]` each have
2. New `phonetic.pronunciation_variant_count()` detects this;
`DifficultyProfile._add_raw()` now sets
`meta["has_alternate_pronunciations"] = True` on a word entry when it
applies, surfaced in `app.py` as "⚠️ has multiple pronunciations."

*Fix 2 — a bridge round-trip bug in `add_sound_from_phones()`.* Verified by
direct testing, not assumed: `phonetic.normalize_pattern("th-r".lower())`
correctly returns `('TH','R')`, but `phonetic.normalize_pattern("zh".lower())`
returns `('Z','HH')` — wrong, because ZH has no natural English onset
spelling. This matters because `add_sound_from_phones()`'s output `value`
string is what the *existing, unmodified* legacy bridge
(`sound_values()` → `stutter_patterns` → `grammar.py`'s
`ph.matches_any()`) re-derives an ARPAbet key from, by spelling guess — the
same mechanism that's always been used for user-typed cues, which this
stage cannot change. `add_sound_from_phones()` now checks its own
round-trip fidelity at creation time and sets
`meta["legacy_bridge_unreliable"] = True` when it fails; `app.py` shows
"⚠️ not fully enforced yet" on such an entry instead of silently accepting
it as fully working.
**Alternatives considered:**
  - Fixing the round-trip properly by changing what flows through the
    legacy bridge, or extending `phonetic.py`'s grapheme tables to cover
    every ARPAbet phone. Rejected — the bridge itself is explicitly
    temporary (`ROADMAP.md` R10/R12 already call for replacing it when the
    reformulation engine is redesigned), and not every ARPAbet phone has a
    natural English spelling to add a rule for (ZH essentially never
    starts an English word) — the honest fix is recording the limitation
    where it occurs, not patching around a bridge slated for removal.
  - Adding position-tracking to `problem_phones` (storing *which*
    occurrence of a repeated phone was selected, not just the phone
    value). Rejected after explicit consideration: the reformulation
    engine's actual use of this data (avoid a phone near this word)
    doesn't change based on which occurrence was meant, so tracking
    position would be real added complexity for a distinction that
    wouldn't change downstream behavior. The UI now states this design
    choice explicitly when a word has a repeated phone, so it reads as a
    decision rather than an unexplained quirk.
  - Building a pronunciation-variant picker UI (let the user choose which
    CMU variant they meant). Rejected as too large for an audit
    adjustment — real new UI, real new tests, and arguably needs sentence
    context to resolve automatically rather than ask the user every time;
    named as future work instead (`ROADMAP.md`).
  - Adding a `position: "onset"` field to sound entries to make the
    onset-only scope self-documenting in the schema. Rejected — there is
    currently no second value that field could take, so adding it now
    would be speculative structure ahead of an actual need; documented in
    prose (`difficulty_profile.py`'s docstring, `PROBLEM_FORMULATION.md`
    §11.1) instead.
**Why:** Directly requested — an explicit audit pass before treating the
profile foundation as settled, specifically asking whether the schema is
unambiguous, cleanly consumable, and free of missed cases or
over-engineering, with instructions to fix what's small and name what's
too big rather than silently letting either kind of finding go unrecorded.
**Measured result:** `tests/difficulty_profile_test.py` grew from 38 to 44
tests (6 new: heteronym detection and persistence, clean vs. lossy
round-trip detection for promoted sounds). `tests/app_test.py` grew to 7
scenarios, including one that promotes ZH from a real word ("measure")
through the actual UI widgets and confirms the warning renders, and a
negative control (a clean sound shows no false-positive warning). All
pass. `tests/roadmap_test.py` (3/3) and `tests/smoke.py` (byte-identical to
baseline) confirm — again — that none of this touched the reformulation
engine.
**Category:** Engineering decision, directly requested by the user as an
audit rather than new-feature work. Both fixes are informational (`meta`
flags + UI warnings) — neither changes what the four core categories mean,
how `add_word`/`add_sound`/`add_phrase`/`set_word_pattern` are called, or
any existing entry's `normalized` dedup key.
**Left explicitly out of scope, named as future work — see `ROADMAP.md`:**
  - A pronunciation-variant picker (let the user choose which CMU
    pronunciation they meant for a heteronym) — real new UI/feature, not
    an adjustment.
  - Word-sense-specific difficulty (the same spelling being difficult in
    one grammatical role/sense but not another) — a word-sense
    disambiguation problem, already named in `RESEARCH.md` §2.B/§7 as a
    real, unsolved problem for the reformulation engine generally, not
    something a profile foundation should solve unilaterally.
  - Phrase-matching logic and the phrase/word-overlap computation both
    remain the future reformulation engine's job, confirmed (not just
    assumed) during this audit to be correctly un-precomputed by the
    profile layer.

---

### 2026-08-16-C — Stage 5: reformulation-engine architecture research completed; no implementation changed
**What was done:** A dedicated research pass on the reformulation engine
itself (as opposed to Stage 3's broader literature survey or Stage 4A's
profile-layer focus), recorded in the new `REFORMULATION_RESEARCH.md`.
Covers: Brown's four factors and the stuttering-loci literature (word-
initial dominance, stress, content/function-word, consonant-cluster
effects) as citable grounding for the difficulty formula's known gaps; a
second close prior system, SpeechAgent (2026, arXiv 2510.20113), compared
against Fluent (already covered in `RESEARCH.md`); minimal-edit tagging
architectures (GECToR, FELIX, LaserTagger) researched in implementation
depth and found infeasible to adopt directly — not for a hardware reason,
but because they require paired training data (difficult-input →
easier-output pairs) that doesn't exist for this task; concrete,
CPU-feasible tooling for the two gaps `RESEARCH.md` already named (small
NLI cross-encoders for the negation/antonym blind spot; HF's
`force_words_ids`/`DisjunctiveConstraint` for positive constraints);
student-hardware feasibility findings for small local LLMs (3–7B, Q4 GGUF,
~12 tok/s on a laptop CPU — usable for an occasional fallback call, not a
tight interactive loop); ten constructed failure-mode examples walked
through against the current system and the recommended architecture;
and a ranked comparison of four candidate architectures (direct
generation, candidate-gen+rank, learned minimal-edit tagging, and a hybrid
of the tagging/ranking/escalation/verification stages), with the hybrid
recommended.
**Alternatives considered:** The four candidate architectures themselves
are the alternatives — see `REFORMULATION_RESEARCH.md` §19 for the full
comparison and §20–21 for why the hybrid was selected over the other
three specifically (each of its components independently justified by a
different finding, not a single overarching preference).
**Why:** Explicitly requested as "the most important research stage" —
determine what's technically best before what's convenient, and determine
what's realistically buildable at student/laptop scale before committing
to an architecture, rather than assuming a familiar technology (LLM/T5/
BERT/WordNet/SBERT) by default.
**Measured result:** N/A in the Practice.md §8 sense — this is a research
and design-comparison pass, not an experiment with a reportable numeric
outcome. What it did produce: a reframing with real evidentiary weight —
the existing `grammar.py`/`rewrite/` architecture's overall *shape*
(identify positions needing attention, touch only those, reassemble)
already matches the minimal-edit/tagging pattern the field treats as best
practice (GECToR/FELIX), which is new, citable support for "consolidate
and extend what exists" over "replace it," independent of and additional
to `RESEARCH.md` §8's earlier version of that same conclusion.
**Category:** Research/evidence-gathering, explicitly not an engineering
decision — per the task's own strict boundary, `grammar.py`, `semantic.py`,
`engine.py`, `rewrite/`, and `rephrase.py` all have zero lines changed;
confirmed via `git status`, not just asserted.
**Left explicitly for the next stage, not decided here:**
  - Whether to actually build the recommended architecture, and in what
    order — `REFORMULATION_RESEARCH.md` §22/§23 propose a first-
    implementation priority order (the A-vs-B ablation, the naturalness-
    of-intervention metric, the NLI signal, the difficulty-formula
    position/stress terms, in that order) and explicitly what not to build
    yet (any model training, the escalation stage itself, a local LLM
    integration, any API-based LLM as a default path, the accept/reject
    personalization loop) — but per Practice.md §0.2, this document
    authorizes none of it; that's a separate, deliberate decision.

---

### 2026-08-16-D — Stage 5B: critical architecture review; Stage 5's recommendation revised, not rubber-stamped
**What was done:** A focused critique of `REFORMULATION_RESEARCH.md`'s
Stage 5 architecture recommendation (§24–31 appended to that same file, not
duplicated elsewhere), followed by an exact input/output contract, an
MVP/Strong/Future split, an evaluation plan, explicit failure-handling
states, a final architecture comparison, and an implementation blueprint.
Two concrete technical claims were verified directly against this repo's
own code/libraries rather than assumed: NLTK WordNet's `Lemma.antonyms()`
is a real, zero-cost, zero-model lookup (confirmed by running it live
against `engine.py`); `rephrase.py::_bad_words_ids()` blocks only
specifically-named word strings, with no mechanism for blocking a phoneme
class — confirmed by reading the actual implementation.
**Alternatives considered:** The revised architecture (D′) against three
others — direct generation only (A), candidate-gen+rank with no escalation
(B), and Stage 5's original hybrid (D) — see
`REFORMULATION_RESEARCH.md` §29's comparison table. D′ selected.
**Why:** Explicitly requested as a "break it" critique before implementation,
not a confirmation pass — six specific, evidence-backed revisions to
Stage 5's own recommendation resulted (§31 in `REFORMULATION_RESEARCH.md`
has the full list): tiered semantic verification instead of flat NLI;
MLM candidate generation deferred pending measurement instead of added
outright; position/stress corrected from "score them" to "log them,"
citing this project's own Practice.md §6 discipline that Stage 5's own
§22 had under-weighted; a new count-threshold restructuring trigger Stage
5 didn't have; T5's constraint mechanism limitation, which settles
constrain-vs-filter for phonemes definitively; and two newly-named edge
cases (cross-substitution interference, degenerate/over-restrictive
profiles).
**Measured result:** N/A in the Practice.md §8 sense — a design-review
pass, not an experiment. The two code-level verifications above are the
closest thing to a measured result this entry has, and both are stated
with how they were checked, not asserted from memory.
**Category:** Research/design-decision pass. Per the task's explicit
boundary, no reformulation code was modified — confirmed via `git status`
showing only `REFORMULATION_RESEARCH.md` changed, not just asserted.
**Status:** Architecture declared implementation-ready
(`REFORMULATION_RESEARCH.md` §31). Implementation itself is a separate,
not-yet-taken decision — this entry authorizes planning, not code changes,
per Practice.md §0.2.

---

### 2026-08-16-E — Architecture D′ implemented (`reformulate.py`); UI redesigned around it
**What was done:** Built `reformulate.py`, the consolidated engine
`REFORMULATION_RESEARCH.md` §24–31 declared implementation-ready: tag
(profile-flagged positions) → per-sentence escalation decision
(count-threshold / degenerate-fraction pre-triggers, §24.D/F) →
all-or-nothing substitute-and-rank per sentence (antonym check via the new
`semantic.is_known_antonym()` → SBERT → phoneme veto) → T5 restructuring
escalation via `rephrase.py` unchanged, generate-then-verify (SBERT +
`semantic.negation_consistent()` + phoneme veto on the actual generated
text, since `bad_words_ids` can't block a phoneme class) → final
re-verification by re-running the flagging check on the assembled output
(the "recovery rate" idea, independently landed on, matching SpeechAgent
§2.2) → metrics (meaning preservation, difficulty reduction, naturalness,
substitution rate) reported separately per Practice.md §10, never blended.
`naturalness.py` (word-level `difflib` edit-ratio, R11) built as a shared
dependency. `app.py` rewritten (v7 → v8): the old dual-pipeline UI (word-
picker dropdowns, separate word/sentence/multi-sentence modes, profile-
rewrite card, rephrase card, allowlist panel, the "learned" onset-risk
chart) is gone, replaced by one linear flow — text → difficulty profile →
Reformulate → changes/skipped/verification review with a per-change
Keep/revert toggle. `grammar.py::SentenceRewriter` and
`rewrite/rewriter.py::DifficultyAwareRewriter` are untouched and still
importable, just no longer called from `app.py`, per the migration plan.
**Two real bugs found and fixed during build, not left for later:**
(1) the T5 escalation path rejected every candidate whenever SBERT was
unavailable, contradicting `semantic.rank_candidates_contextually`'s own
documented fallback ("SBERT unavailable → don't gate on it, fall back to
accepting") — found by running the escalation path live with SBERT
offline, not by inspection. (2) escalation's word-block set was the full
declared-word list, which included non-substitutable words (numerals,
etc. — anything `_SUBSTITUTABLE` excludes); since neither substitution nor
T5 restructuring can act on those, this guaranteed escalation always
failed whenever such a word was present in the sentence. Fixed by scoping
the block set to the words actually flagged as substitutable in that
sentence. Both caught by live smoke tests against the real CMU/WordNet/T5
stack, not unit tests with mocked dependencies.
**Scope decisions made, not silently dropped:**
  - The old allowlist ("never substitute this word") feature was cut, not
    ported. The new per-change review UI (Keep/revert per change) serves
    the same protective purpose after the fact, which fits the requested
    workflow ("reviewing changes") better than a pre-emptive block list —
    but this is a real capability change, stated here rather than left for
    someone to notice later.
  - The "learned" `SpeakerDifficultyProfile` onset-risk chart was dropped
    from the UI, not merely deprioritized: with the audio/ASR pipeline out
    of scope (`out_of_scope/`), `onset_observations` never receives real
    session data, so `onboarding()` seeds `onset_risk` purely from the
    same declared sounds the Speaker Difficulty Profile panel already
    shows. The chart was labeled "learned from observed sessions" while
    actually just re-displaying declared input — a mislabeled duplicate,
    not a decorative-but-harmless feature, which is why it was removed
    rather than kept. `profiling/profile.py` itself is untouched.
  - `difficulty_profile.phrases` still has no consumer in the new engine
    (ROADMAP.md R13 stays open for phrases specifically) — `problem_phones`
    now does (via `_trigger_reasons`), but multi-word phrase detection
    needs a different mechanism than the current single-word-substitution /
    whole-sentence-restructuring model supports, and was not built here
    without a separate go-ahead.
**Verification performed:** Every function signature this module calls
(`semantic.rank_candidates_contextually`, `engine.SynonymEngine.get_synonyms`,
`phonetic.matches_any`, `rephrase.generate_candidates`,
`DifficultyProfile.find_word`/`word_values`/`sound_values`, `grammar`'s
lemmatize/inflect/_preserve_case/_detokenize/_wn_pos) was read from the
live code via `inspect.signature`, not assumed from memory, before being
called. `tests/reformulate_test.py` (12 tests, all paths: no-change,
substitution, antonym guard, word-specific-pattern isolation, count-
threshold and all-or-nothing escalation, cannot-safely-reformulate,
multi-sentence pass-through, metrics bounds) and `tests/app_test.py`
(rewritten for the new UI) both pass against the real CMU/WordNet/SBERT/T5
stack, not mocks, except where a test deliberately mocks one dependency to
force a specific edge case. `tests/smoke.py` output is byte-identical to
`tests/baseline_sbert.txt` — the existing pipeline (`grammar.py`/
`engine.py`/`semantic.py`'s pre-existing functions) is unchanged. The app
was run live under `streamlit run` (HTTP 200) in addition to `AppTest`;
no browser-automation tool was available in this environment to capture a
screenshot, which is stated here rather than silently skipped.
**Category:** Engineering decision + implementation. Zero changes to
`grammar.py`, `engine.py`, `rewrite/`; `semantic.py` extended additively
only (two new functions, nothing existing altered).
**Not done here, left open:** the R9 accept/reject → profile feedback
loop (the UI now *has* an accept/reject signal to wire, but it isn't
wired into the profile yet); phrase-level detection (R13, above); Strong-
tier NLI verification (§27); MLM candidate generation (§24.B, deferred
pending measurement per Stage 5B).

---

### 2026-08-16-F — Pre-evaluation cleanup pass: dead surface removed, live-but-old code left alone
**What was done:** A repo-wide audit for code/UI/imports/dependencies/
config/tests/docs made unreachable by the D′/app.py v8 redesign
(2026-08-16-E), scoped to *that* redesign specifically, not a general
decade-old-code sweep of everything `grammar.py`/`rewrite/`/`profiling/`
contain. Every removal below was verified by tracing actual callers
(`Grep` across the live `.py` tree, plus AST-based unused-import checks
on the files this session touched), not by "it looks old."
**Removed, with the verification that justified it:**
  - `run_app.ps1` — hardcoded a nonexistent path (`L:\speech-ai`) and venv
    name (`.venv313`, actual is `venv/`), and its entire premise (close
    your IDE to free RAM for the ASR model) describes a feature
    (`out_of_scope/`'s CrisperWhisper wrapper) this repo hasn't run since
    the Stage 2 narrowing pass. Not referenced by any other file except
    `README.md` (fixed, see below) and `changes.md` (historical, left
    alone).
  - `profile_store.py`'s `load_preferences()`/`save_preferences()` and
    the on-disk `preferences`/`custom_replacements` fields (an allowlist,
    a `rephrase_enabled` toggle, a `profile_rewrite_enabled` toggle) —
    grepped for every caller across the repo: the only ones were
    `profile_store.py`'s own internal round-trip (to avoid clobbering the
    fields on every difficulty-profile save) and
    `tests/persistence_test.py`, which tested exactly that round-trip and
    nothing else. Both existed only because app.py v7's now-removed
    sidebar toggles/allowlist panel wrote to them; v8 never did. Removed
    together: the functions, the schema fields (silently dropped on the
    next `save_difficulty_profile()` call, following the same precedent
    already set for `password_hash`/`phoneme_profile` during the auth
    removal), and `tests/persistence_test.py` (its one remaining
    unique-value assertion — a never-saved profile still loads without
    crashing — is already covered by
    `tests/difficulty_profile_test.py::PersistenceTest`).
  - `freq.py::active_wordlist()` — zero call sites anywhere in the repo;
    existed solely for a sidebar caption ("Frequency wordlist: **X**")
    that app.py v8 doesn't have.
  - `reformulate.py`'s unused `field` (dataclasses) and `Any` (typing)
    imports — caught by an AST pass comparing imported names against
    `ast.Name` usage across the file, run on every file this session
    authored or edited.
  - `torchvision` from `requirements.txt` — re-confirmed zero imports
    anywhere (Stage 2's `DECISION_LOG.md` 2026-08-15-A already found this
    and explicitly deferred it as "unrelated to the audio/text boundary");
    this pass's scope covers it.
  - `.gitignore`'s `user_prefs.json` line — no code anywhere writes that
    filename; a leftover from an even earlier (pre-`user_store.py`)
    architecture.
**Investigated and explicitly kept, not removed:**
  - `grammar.py::SentenceRewriter`, `rewrite/` (`rewriter.py`/`rank.py`/
    `candidates.py`), `profiling/` (`profile.py`/`coldstart.py`/
    `config.py`), `config.yaml`, `eval/` (`metrics.py`/`profile_eval.py`/
    `study/`) — all confirmed, by tracing actual imports, to be a single
    connected dependency chain (`rewrite/rewriter.py` imports
    `profiling.profile.SpeakerDifficultyProfile` and
    `profiling.config.load_config`, which reads `config.yaml`; `eval/`
    imports both `rewrite/` and `profiling/`) that stays alive as a whole
    specifically because 2026-08-16-E's migration plan keeps
    `SentenceRewriter`/`DifficultyAwareRewriter` for the upcoming
    evaluation-stage comparison against `reformulate.py`. Confirmed
    genuinely exercised, not just present: `tests/smoke.py`,
    `tests/threshold_sweep.py`, `tests/evaluate.py` run `SentenceRewriter`
    directly; `tests/roadmap_test.py` and `eval/metrics.py` run
    `DifficultyAwareRewriter` directly.
  - `scripts/` (T5 fine-tuning scaffolding) — standalone, not imported by
    the live app, but not orphaned either: it targets the same
    `Vamsi/T5_Paraphrase_Paws` model `rephrase.py` still serves as
    `reformulate.py`'s live restructuring-escalation step.
  - `changes.md` — pre-dates this doc set and describes several
    now-removed features (mic profiling, the old rewrite toggles) as
    current, but it's a labeled, append-only historical record
    (`DOCS.md` already flags it as "not a source of truth for current
    behavior"), not a cleanup target — Practice.md's own discipline is to
    append corrections, not rewrite history.
**`app.py`/`reformulate.py` audit result:** no dead code found beyond the
two unused imports above — both were rewritten as complete, self-
contained passes in 2026-08-16-E rather than accreted onto, so there was
little inherited cruft to find.
**Docs updated to match:** `README.md` (the "What It Does"/"Features"
sections were still describing the v7 dropdown UI as current; "Architecture
Notes" now states which modules are live vs. retained-for-comparison;
fixed the `run_app.ps1` and `preferences`-schema references), `DOCS.md`
(`profile_store.py`/`users/` rows, `persistence_test.py` row removed).
**Category:** Cleanup/removal, explicitly not a redesign — no scoring
formula, threshold, gate, or reformulation behavior changed. Verified via
`tests/smoke.py` staying byte-identical to `tests/baseline_sbert.txt`.
**Verification performed:** `tests/reformulate_test.py` (12),
`tests/difficulty_profile_test.py` (44), `tests/app_test.py`, and
`tests/roadmap_test.py` (3) all pass after every removal above: 56
unittest cases plus two script-style suites, all green. A live
`save_difficulty_profile()` round-trip was run and its on-disk output
inspected directly to confirm the schema simplification behaves as
described, not just as intended.
**Left for the user to decide, not removed:** whether to eventually
delete (not just stop calling) `grammar.py::SentenceRewriter`/`rewrite/`/
`profiling/`/`eval/` once the evaluation stage actually measures
`reformulate.py` against them — that decision explicitly belongs to the
evaluation stage's outcome, per 2026-08-16-E's migration plan, not to
this cleanup pass.

---

### 2026-08-16-G — Stage 6: `reformulate.py` evaluated against both retained legacy pipelines (executed, not inferred)
**What was done:** Built `tests/reformulation_eval_corpus.json` (18 cases —
`REFORMULATION_RESEARCH.md` §17's eight constructed failure modes,
phonetic claims verified against live `phonetic.onset()` output before
writing them, plus ten control cases spanning ordinary text, multi-
sentence input, a degenerate/dense profile, a phrase-only profile, a
word-specific-`problem_phones`-only profile, and a direct antonym-guard
probe) and `eval/reformulation_eval.py` (runs `reformulate.py`,
`grammar.py::SentenceRewriter`, and `rewrite/rewriter.py::DifficultyAwareRewriter`
on identical `sanitize_input()`-corrected text, scored with the same
metric functions applied uniformly to all three). Ran it and wrote the
actual results into `VALIDATION.md` §6 with Practice.md's evidence
labels, not into a new document.
**Measured result:** `reformulate.py` — meaning preservation 0.979,
edit-ratio 0.068, reformulation rate 0.556; `SentenceRewriter` — 0.938 /
0.147 / 0.889; `DifficultyAwareRewriter` — 0.929 / 0.143 / 0.833. The
gap is fully explained by one mechanism: `reformulate.py`'s T5
restructuring-escalation path succeeded 0/4 times on this corpus — every
substitution-only case succeeded. Root-caused into two distinct causes by
direct debugging (manual `_model.generate()` calls with the exact
`bad_words_ids` computed, token IDs inspected directly), not left as one
vague "escalation is weak" statement: (A) `rephrase.py::_bad_words_ids()`
is case-sensitive but is given lowercased words, so a blocked word's
capitalized form leaks through untouched — confirmed directly (lowercase
token: 0/6 beams leaked; capitalized form of the same word: 5/6 leaked);
(B) even where blocking worked correctly, T5 reintroduced the flagged
phoneme via unblocked, semantically-related synonyms/inflections
(`struggling`→`struggled`, `stressful`→`stress`) — confirming, with
evidence for the first time, the limitation `REFORMULATION_RESEARCH.md`
§24.E only theorized.
**Additional findings, not hypothesized in advance:** a pre-existing
inflection bug in `SentenceRewriter`'s own candidate path (produced
"constructionss," double-s) surfaced by running it side-by-side with
`reformulate.py` for the first time; the context-dependent-substitution
failure mode (§17 row 5) confirmed to persist in all three systems with a
concrete example; a null result honestly reported (the antonym-guard
probe case never actually forced an antonym to the top of any system's
ranking, so it demonstrates nothing about the guard either way); and one
directly-observed case where SBERT scored a redundant, arguably-worse
rewrite ("The gift was a wonderful gift.") at 0.965 — the highest
similarity band in the corpus — offered as concrete evidence for the
proxy-metric warning already on record in `VALIDATION.md` §2, not just a
restatement of it.
**Category:** Measurement only, per this stage's explicit instruction.
No scoring formula, threshold, gate, or reformulation algorithm was
changed. Both root-caused issues (R17/R18 in `ROADMAP.md`) are documented
as findings with a proposed fix/research direction, not applied.
**Verification performed:** The harness was run twice and its output CSV
diffed byte-for-byte to confirm determinism under `DISABLE_DATAMUSE=1`
before this entry was written. No `DifficultyProfile`/
`SpeakerDifficultyProfile` instance created for this evaluation was ever
saved to disk — confirmed via `git status` on `users/` showing no diff.
**Explicitly not established:** speaker suitability (whether a real
speaker would find any output easier to say) — stated in `VALIDATION.md`
§6.5 as categorically outside what this or any automated evaluation can
measure, not as a gap this corpus could have closed with more cases.
Also not established: a realistic escalation-trigger/success rate for
ordinary (non-adversarially-constructed) text — this corpus was built
failure-mode-dense by design, so 0/4 should not be read as a general
escalation failure rate.

---

### 2026-08-16-H — R17 fixed: `rephrase.py::_bad_words_ids()` case-insensitivity, measured, did not recover any escalation cases
**What was done:** `_bad_words_ids()` (`rephrase.py`) now encodes each
blocked word's lowercase and capitalized forms (each with and without a
leading space), not just the exact form the caller passed in — the fix
for `VALIDATION.md` §6.3's Cause A, confirmed there via direct
tokenization and a controlled `_model.generate()` repro. Nothing else in
`rephrase.py` changed: same model, same generation parameters, same
number of candidates, same public signature.
**Tests added:** `tests/rephrase_test.py`, 8 new tests, all pass —
`BadWordsIdsUnitTest` (4 fast, deterministic checks directly on
`_bad_words_ids()`: both case forms present for a word verified to
tokenize differently by case; leading-space variants of both forms still
present, a regression check against the pre-fix behavior; an
already-mixed-case input like `"TensorFlow"` still has its exact form
blocked; empty/None input still returns `None`; no duplicate token
sequences) and `GenerationCaseLeakTest` (3 integration-level checks
actually calling `generate_candidates()`: a sentence-initial
capitalization case, a mid-sentence-vs-sentence-initial pair for the same
word, and a regression check that unblocked generation is unaffected).
**Measured result:** Re-ran the identical `eval/reformulation_eval.py` /
`tests/reformulation_eval_corpus.json` corpus from Stage 6
(`VALIDATION.md` §6) after the fix. The fix works exactly as intended at
the unit and single-sentence level (the original "manager" repro's 5/6
capitalized leak is now 0/6, confirmed live, not just via the new tests).
**It recovered zero of the four `could_not_safely_reformulate` cases** —
every aggregate number in the before/after comparison is unchanged
(reformulation rate 0.556 both times; identical status distribution;
byte-identical final output for all four previously-failing cases).
Traced why directly: post-fix candidates for these cases no longer leak
the literal blocked word in any case, but they either (a) still contain a
different word sharing the same flagged phoneme class (Cause B,
unaffected by this fix, exactly as predicted), or (b) a newly-observed
effect — blocking more token forms pushes T5's beam search toward
substantially lower-similarity paraphrases (0.49–0.61 post-fix vs.
0.81–0.91 pre-fix on the same case), which then fail the SBERT gate
instead of, or in addition to, the phoneme gate.
**Category:** Bug fix + measurement, exactly as scoped — no reformulation
scoring, gate, or trigger logic touched; `ROADMAP.md` R17 explicitly
excluded any T5 redesign or Cause B work, and none was done.
**Verification performed:** Full existing test suite (67 cases across
`reformulate_test`/`difficulty_profile_test`/`roadmap_test`/
`rephrase_test`) passes. The Stage 6 corpus was re-run against the fixed
code, not re-inferred from the fix's description. No profile touched
disk during any of this (`git status` on `users/` clean throughout).
**Left open, unresolved:** `ROADMAP.md` R18 (Cause B / escalation-model
mismatch) — this entry's result strengthens the case that R18, not R17,
is the actual blocker on this corpus's escalation success rate, and adds
one new consideration for whoever picks up R18: naively blocking *more*
terms as a fix risks trading a phoneme-veto rejection for a
semantic-gate rejection rather than producing an actual pass.

---

### 2026-08-16-I — Escalation-trigger/success rate measured on ordinary text: Stage 6's 0/4 does not generalize
**What was done:** Built `tests/reformulation_ordinary_corpus.json` (36
already-committed `tests/eval_corpus.txt` sentences, unmodified, + 6
ordinary multi-sentence paragraphs written for this corpus without regard
to any profile) crossed against 5 realistic, non-adversarial difficulty
profiles (light single-sound, moderate two-plosive, consonant-cluster,
words-only, and one modeled directly on this repo's own real
`users/default.json`) — 210 cases. Ran `eval/reformulation_escalation_rate.py`
(`reformulate.py` only — the retained legacy pipelines have no escalation
concept) and classified each sentence's outcome directly from
`reformulate.py`'s own result structure (a `"restructuring"`-sourced
change = escalation triggered and succeeded; a `skipped` entry = escalation
triggered and failed — verified these are the only two ways a sentence
reaches either list, not assumed).
**Measured result:** 72/210 cases (34.3%) had at least one flagged word
under a realistic profile; 44 of those (61%) resolved by substitution
alone. Escalation triggered for 28 of 270 total sentences (10.4%) and
**succeeded for 12 of those 28 (42.9%)** — not the 0% Stage 6's corpus
showed. Per-profile: `moderate_two_plosive` 13 triggered/5 succeeded,
`light_single_sound` 8/2, `consonant_clusters` 4/2, `words_only` 3/3,
and the real-profile-shaped `typical_mixed` **0 triggered across all 42
texts**.
**Category:** Measurement only, directly answering a limitation
`VALIDATION.md` §6.7 explicitly flagged as unresolved rather than leaving
it as a caveat indefinitely. No code changed.
**Verification performed:** Concrete examples pulled and manually
inspected (not just aggregate counts) — two clean escalation successes
("The manager confirmed the schedule this morning." → "...confirmed the
time this morning."; "cooked pasta" → "cooked spaghetti") and two
genuine failures, confirming the aggregate numbers reflect real,
readable outcomes, not an artifact of the counting method.
**Category — what this changes:** Re-prioritizes, does not close, R18 —
Cause B is real and reproducible on Stage 6's own cases, but this result
shows it's not representative of ordinary usage, specifically because it
requires several instances of one onset to be semantically load-bearing
in a single sentence, a real but non-typical condition. R9 (wire the
review UI's keep/revert into the profile) and the never-run human-
judgment study are, by this result, no longer obviously lower priority
than R18 — left for the next planning step to decide.
**Not established:** speaker suitability, still, for the same reason as
2026-08-16-G. Also not established: whether these 5 specific profiles are
representative of real speaker profiles generally — they were built to be
*plausible*, not sourced from real users, since this repo has none beyond
its own single default profile.

---

### 2026-08-17-A — R9 implemented: Keep/Revert wired into the profile as a recorded feedback signal (prototype scope, not yet acted on)
**What was done:** `reformulate.py` gained one new, read-only, additive
function — `feedback_targets(change, profile)` — that maps a
substitution-sourced change back to the specific declared word/sound
entry responsible for it, using only information already in the change
dict (`triggered_by`, `original`); restructuring-sourced changes
deliberately return `[]` rather than guess an attribution for a whole-
sentence rewrite. `difficulty_profile.py` gained `record_feedback(entry,
kept)` / `undo_feedback(entry, kept)`, storing plain kept/reverted
counters in the entry's existing, reserved `meta` field (in place since
Stage 4A specifically for this kind of forward-compatible extension).
`app.py`'s existing Keep/Revert checkbox handler now calls both on every
genuine toggle (not on re-renders) — undoing any prior vote for that same
change first, so re-toggling reflects the user's current choice rather
than accumulating raw clicks — and persists via the existing
`profile.save()` path. A small `(✓k ↺r)` badge in the difficulty-profile
panel surfaces the counts rather than leaving them invisible.
**Explicit scope boundary, honored:** this records the reward signal the
field's contextual-bandit framing (`ROADMAP.md` R9, `REFORMULATION_RESEARCH.md`
§11) calls for — it does not act on it. Nothing in `reformulate.py`'s
candidate ranking, scoring, or gating reads this field. Using it to
influence future substitution choices is separate work, not started here,
consistent with this project's own just-reaffirmed discipline (don't
change ranking without evaluation evidence, `VALIDATION.md` §6.9).
**Tests added:** 11 new — `tests/difficulty_profile_test.py::FeedbackTest`
(6: increment, undo, undo-floors-at-zero, per-entry isolation, persists
across reload, and — the one that matters most — recording feedback
never mutates the declared sounds/words/phrases lists themselves, only
annotates); `tests/reformulate_test.py::FeedbackTargetsTest` (5: word
attribution, sound attribution, restructuring returns `[]`, no-match
returns `[]`, and confirms `feedback_targets` mutates neither the profile
nor the change dict it's given). `tests/app_test.py` extended with a
real end-to-end scenario through the actual UI: reformulate → revert a
change → confirm the vote persisted to the real `users/default.json` →
confirm the badge renders → toggle back to Keep → confirm the vote flips
net (1 kept, 0 reverted) rather than accumulating.
**Verification performed:** full existing suite (78 tests total, up from
67) passes; `tests/smoke.py` is byte-identical to `baseline_sbert.txt`,
confirming zero effect on the underlying `grammar.py`/`engine.py`/
`semantic.py` pipeline; `git status` on `users/` clean after the new
`app_test.py` scenario (snapshot/restore held).
**Category:** Feature implementation, additive only — no existing
function's control flow, signature, or return shape was changed; three
new functions added (`reformulate.feedback_targets`,
`difficulty_profile.record_feedback`/`undo_feedback`), one existing UI
event handler extended by two lines to call them.
**Left open, unresolved:** whether recorded feedback should ever
influence ranking, and if so how (naive down-weighting? the bandit
framing? something else) — an explicit, separate, evaluation-gated
decision, not decided or hinted at by this entry.

---

### 2026-08-17-B — `eval/study/` infrastructure verified by actually running it; no bugs found, real blockers identified instead
**What was done:** Ran `eval/study/counterbalance.py`,
`eval/study/collect.py`, and `eval/study/stats.py` against synthetic data
— not read for plausibility, actually executed. `assign_conditions()`
against 7 synthetic participants × 3 passages produced a correctly
balanced 21-row, 7/7/7 condition schedule. `init_collection_csv()`
produced the documented 10-column schema. `stats.friedman()` was run
against synthetic per-condition data with scipy available and returned a
real statistic/p-value.
**Measured result:** No bugs. Per this task's own instruction ("fix only
infrastructure problems if necessary"), nothing was changed, because
nothing was broken. Three real, non-code gaps were found instead: (1)
`collect.py` defines a CSV schema, not a collection instrument — nothing
in the repo presents a stimulus to a participant or records a response;
(2) the condition labels (`original`/`generic`/`personal`) are specific
to the pre-`reformulate.py` `rewrite/`-era study design and don't map
onto the current three-pipeline comparison; (3) the schema's own
headline metric, `disfluency_count`, requires spoken-performance data —
a participant reading aloud, disfluencies counted from audio — which
this text-only module cannot capture itself, since audio was moved to
`out_of_scope/` in this module's own Stage 2 narrowing. The two other
recorded fields (`ease_likert_1_7`, `forced_choice_preference`) do not
require audio and remain usable for a text-only pilot.
**Category:** Verification only. Zero lines of `eval/study/` changed —
confirmed via `git status` showing no diff on that directory.
**Left for the next step, not decided here:** what a realistic pilot
actually looks like (participants, sample size, which systems/condition
labels to compare) — that depends on who can realistically read and rate
outputs, which this pass has no way to determine on its own.

---

### 2026-08-17-C — Stage 7: human-evaluation pilot built, verified end-to-end with synthetic data; real 4x20 collection not yet run
**What was done:** Built the full Stage 7 pilot per the user's detailed
brief. `eval/pilot_select_pairs.py` re-ran `reformulate.py` (with
`sanitize_input()` first — matching `app.py`'s real pipeline; the earlier
escalation-rate corpus run had NOT applied `sanitize_input`, a real
inconsistency found and fixed here for this new script, not retroactively
fixed in the old one) over both existing evaluation corpora (18 + 210 =
228 combinations), found 69 eligible (`status == "reformulated"`; the two
non-reformulated statuses excluded since there's no candidate to rate),
and selected 20 by deliberate criteria (documented in
`VALIDATION.md` §8.2) rather than randomly — including two Stage-6 cases
already known to be qualitatively weak despite passing every automated
gate, and, on inspection of the freshly-regenerated ordinary-text pool,
two previously-undiscovered genuine errors ("stored... in the **farm**"
for "barn"; "...to **education**" for "school") that also passed every
automated gate. `eval/pilot_app.py` (a separate, minimal Streamlit
instrument, not part of `app.py`) presents one pair at a time, asks the
four required questions plus an optional diagnostic tag, with
per-participant order and display-position counterbalancing, and never
shows any internal score. `eval/pilot_analyze.py` computes per-pair
summaries and specifically flags pairs where the automated SBERT
proxy and the (eventual) human meaning-preservation rating disagree by a
material margin — the concrete, actionable output this pilot exists to
produce, not just "did people like it."
**Verification performed, per the brief's explicit requirement to test
before real participants:** `tests/pilot_app_test.py` drove the actual
app twice (participant IDs P1 and P2 — the app's selectbox only accepts
its 4 fixed IDs, so a synthetic-only ID couldn't be used) through all 20
pairs each via Streamlit's `AppTest`, then verified: exactly 20 rows
saved per participant; zero cross-contamination between participant
files; presentation order and display position both genuinely varied
between participants (not just coded to); all response values round-trip
through the CSV correctly; and `eval/pilot_analyze.py` correctly loads
and summarizes the resulting 40 synthetic rows. The test snapshots and
restores `P1.csv`/`P2.csv` around its run (same pattern
`tests/app_test.py` uses for `users/default.json`), confirmed via
`git status` showing no diff on `eval/pilot_responses/` afterward.
**Category:** Infrastructure + design, explicitly not implementation of
any reformulation change. Zero lines of `reformulate.py` changed —
confirmed via the full existing suite (78 tests) plus `tests/smoke.py`
byte-identical to baseline, both re-run after this stage's work.
**Not yet done:** the actual 4x20 data collection with real participants,
and therefore any results, conclusions, or improvement recommendations
drawn from it — `VALIDATION.md` §8 records the design and verified
infrastructure only; results will be appended there, not substituted for
this entry, once real participants complete the pilot.

---

### 2026-08-17-D — Pilot redesigned (v2) per direct user review; found and worked around genuine T5 escalation non-determinism
**What was done:** The v1 pilot set (2026-08-17-C) was reviewed directly
by the user before any real participant used it — informally, via the
live app at localhost:8502, which produced a real 4-row `P1.csv` (cleared
before this v2 set replaced it, since its `pair_id`s no longer correspond
to the same sentences — flagged to the user rather than silently
deleted). Feedback: v1's 20 pairs were too uniform in length/register.
Redesigned to `eval/pilot_select_pairs.py` v2: 10 short single sentences
(quickly-typed, natural register), 3 long/complex single sentences, 6
multi-sentence passages, and 1 real public-domain speech paragraph
(Lincoln's Gettysburg Address, 1863 — sourced via `WebSearch`/`WebFetch`
against archival transcripts on 2026-08-17, cross-checked against two
independent sources rather than quoted from training-data memory alone,
confirmed public domain both by age and as a historical/government-
adjacent work) with a profile chosen to produce many substitutions across
its ten sentences in one item. `eval/pilot_app.py` gained a new
diagnostic-tag option ("Original sentence itself was confusing or
ungrammatical" — so a broken input isn't misattributed to
`reformulate.py`) and an optional free-text comment field.
**Unplanned finding, significant:** while verifying each new candidate
item's stability, 4 of 24 initially-chosen (text, profile) pairs were
found to be genuinely non-deterministic — `reformulate.reformulate()`
called with identical code and identical input produced "reformulated"
once and then `could_not_safely_reformulate` on 2-3 immediately-following
fresh-process trials (repro case: `long_printer_broken`, "Because the
printer had been broken..." — succeeded once, then failed 3/3 times in
separate `python -c` launches with no code change in between). All
affected items involved T5 restructuring escalation; plain
substitution-only items showed no instability across repeated trials.
This points to CPU floating-point non-associativity in T5's beam search
across process/thread scheduling — not a bug in `reformulate.py`'s own
logic — and is **not fixed here** (would mean touching `rephrase.py`,
out of scope for a pilot-design task). Practical response: `_run_item()`
runs in an isolated subprocess per item (`--single <case_id>` mode), and
every final item was reconfirmed stable across 2-3 fresh-process trials
before being kept; the 4 unstable items were swapped for equally
illustrative, verified-stable replacements (mostly substitution-only,
still containing genuine, checkable errors — "snacks" → "eatings",
"exam season" → "exam period" with "Students" → "Pupils", etc.).
**Category:** Design revision + a new, disclosed limitation finding. Zero
changes to `reformulate.py`/`rephrase.py` — this finding is about their
existing behavior, observed, not introduced or fixed.
**Verification performed:** `tests/pilot_app_test.py` re-run against the
v2 pair set end-to-end (P1/P2 through all 20 pairs via `AppTest`) — all
checks pass, including two new ones (comment field round-trips; the new
"input grammar" diagnostic tag is recorded correctly). Full existing
suite (78 tests) and `tests/smoke.py` re-confirmed unaffected.
**Left open, disclosed as a limitation:** this non-determinism means a
different machine, or even a different run on this machine, could
plausibly see 1-2 of these 20 pairs resolve differently than recorded in
`eval/pilot_pairs.json` if regenerated — the pairs actually used for data
collection are the ones frozen in that committed file, not whatever a
fresh regeneration might produce. `eval/pilot_select_pairs.py` should not
be re-run to "refresh" the pairs once real data collection begins.

---

### 2026-08-17-E — v2 pilot actually run (P1, real data); a real UI labeling bug found from using it; methodology narrowed and pilot rebuilt as v3
**What was done:** The user ran the live v2 pilot app themselves as P1 and
completed all 20 pairs with real ratings and several free-text comments —
the first genuine human-judgment data this project has collected (every
prior evaluation stage was automated/proxy-based). Headline: meaning
preservation 4.65/5, naturalness 4.70/5, speaking ease +1.75 (of +2 max),
preference for the reformulated sentence on 19/20 pairs.
**Bug found from that real use, not from re-reading the code
speculatively:** several of P1's free-text comments described a wording
flaw as being in "the input," quoting text that was actually in the
*reformulated* output (e.g. pair_12: "stopped 'using' is rather not so
correct" as an input complaint — "stopped using" was `reformulate.py`'s
own output; the input said "stopped working"). Traced to
`eval/pilot_app.py`: the two text boxes were labeled generically
"Sentence 1"/"Sentence 2," with a separate caption below stating which
was Original vs. Reformulated — since display order is randomized per
pair, "Sentence 1" meant Original for some pairs and Reformulated for
others, and P1 evidently anchored on "Sentence 1 = input" as a shortcut
rather than re-reading the caption on all 20 pairs. Confirmed via the
actual `shown_first` value recorded for pair_12
(`shown_first=reformulated`, i.e. Sentence 1 *was* the reformulated
text). The numeric ratings are less likely affected (answered directly
below the caption, not narrated afterward) but this can't be fully
ruled out either.
**User's review, direct instructions, acted on in full:**
1. Short sentences tested far better than long ones — long sentences
   only changed a word or two, diluting the signal. Long/multi-sentence/
   paragraph categories dropped entirely for the next round.
2. **Methodology narrowed, explicitly, going forward**: human ratings
   cover meaning preservation / naturalness / speaking ease / preference
   / optional comment ONLY. Whether a reformulation actually resolved
   its declared difficulty profile is a separate, automated question,
   analyzed alongside the human results afterward, never asked of the
   participant and never blended into their ratings.
3. Profile traceability was missing — nothing surfaced, per item, what
   difficulty was actually being targeted. Must be fixed.
4. New design: single participant (not four), ~30 short/natural/
   everyday sentences only, selected to cover different difficulty types
   and reformulation behaviors including flawed/weak outputs, not only
   clean successes.
**Category:** Real human-judgment data collected and recorded; a real UI
bug found and fixed; a methodology decision locked in by explicit user
instruction. No `reformulate.py` changes — this entire entry is about
the evaluation instrument, not the engine.
**Verification performed:** the `shown_first=reformulated` claim for
pair_12 was checked directly against the v2 response CSV (archived at
`eval/archive_v2/P1_v2_responses.csv`), not asserted from memory.
**Left for the next entry:** the actual v3 rebuild (pilot set, app,
analysis script, tests) — recorded separately, 2026-08-17-F, so this
entry stays focused on what was *found*, not what was *built* in
response.

---

### 2026-08-17-F — Pilot rebuilt as v3: single participant, 30 short/natural sentences, full profile traceability, labeling bug fixed
**What was done:** `eval/pilot_select_pairs.py` rebuilt from scratch: 30
short, natural, everyday sentences (requests, apologies, scheduling,
small talk, complaints — the register people actually stutter on in
real use, authored directly rather than scraped, for the same copyright-
safety reasoning as v2's public-domain-only sourcing decision), split
18 global-sound-triggered / 5 declared-word-triggered / 4 word-specific-
pattern-triggered / 3 multi-difficulty, sized by category to match what
a real, lightly-populated profile actually produces (`VALIDATION.md`
§6.9's own finding: light/moderate profiles dominate real usage).
`eval/pilot_app.py` rebuilt: single fixed participant, no selection
screen; **Original/Reformulated labeled directly on each box** (the
v2 bug's actual fix — no more "Sentence 1/2" + separate caption).
`eval/pilot_analyze.py` extended with a profile-match section, computed
from `reformulate.py`'s own before/after flagged-word count, printed in
its own clearly-separated block — never merged into the human-rating
numbers above it. Every item carries full traceability metadata
(declared profile, trigger reason, exact word(s) changed, whether the
difficulty was actually resolved) for post-hoc analysis, never shown to
the participant.
**Reused as-is, not rebuilt:** `reformulate.py` (zero changes — this
stage is evaluation-only, per the user's own explicit instruction), the
subprocess-isolation + multi-trial stability verification approach from
v2 (`VALIDATION.md` §8.4's non-determinism finding still applies and was
checked for again here, not assumed fixed), `eval/study/stats.read_rows()`.
**Removed, not archived-in-place:** v2's 4-category composition, the
4-participant selection screen, the "Sentence 1/2" labeling scheme. The
real v2 P1 data and the v2 pilot_pairs.json were moved to
`eval/archive_v2/` (not deleted — real collected human-subject data and
a fully-documented, working design are not thrown away, even when
superseded) before v3 overwrote the live files.
**Verification performed:** every item run through the live
`reformulate.py` engine and kept only on a `"reformulated"` status;
restructuring-sourced items (8 of 30) reconfirmed stable across 2
additional fresh-process trials before being kept (the same discipline
v2's non-determinism finding required) — all 8 passed. `tests/pilot_app_test.py`
rebuilt for the single-participant/30-pair flow, including a dedicated
check that "Original"/"Reformulated" appear directly in the UI and
"Sentence 1/2" does not — the specific v2 bug, checked for directly, not
just assumed fixed by the code change.
**A second, unrelated bug found and fixed while building this
verification, not in `reformulate.py` or the pilot content:** the first
version of `tests/pilot_app_test.py` reused one long-lived `AppTest`
instance across all 30 submit-and-rerun cycles (the same pattern that
worked for v2's 20-pair runs) and reliably crashed partway through with a
`KeyError` against a stale widget ID — traced to AppTest's internal
widget tracking accumulating corrupted state after enough sequential
`st.form` submit → `st.rerun()` cycles (first observed to leak a stale
form's radios into the next pair's widget list, then crash on a later
`.run()`). Not a bug in `eval/pilot_app.py` itself — confirmed by
checking that a fresh `AppTest` instance created for *each* pair
(relying on the app's own disk-based resume logic, `_load_completed()`)
completes all 30 pairs cleanly and repeatably. `tests/pilot_app_test.py`
rebuilt on that pattern. v2's 20-pair/2-participant runs apparently
stayed under whatever threshold triggers this; v3's 30 pairs in one
continuous session crossed it.
**Category:** Evaluation-infrastructure rebuild. Zero changes to
`reformulate.py` — confirmed via the full existing suite (78 tests) and
`tests/smoke.py`, both re-run after this stage's work.
**Not yet done:** the actual 30-item single-participant data collection
under v3 — this entry records the design and verified infrastructure
only.

### 2026-08-17-G — v3 pilot actually run and analyzed (P1, real 30-item data); no changes made, analysis only

**What was done:** P1 completed all 30 v3 pilot items. Analyzed per the
user's explicit request, keeping human ratings, automated profile-match
metadata, and automated proxy metrics as three separate evidence
streams throughout — never blended, per Practice.md §10. Full record:
`VALIDATION.md` §9.6-9.11. No code changed; this is an analysis-only
entry.

**Headline findings:** Overall meaning=4.13/5, naturalness=4.07/5,
ease=+1.10, preferred-reformulated=73.3% (22/30). Sharp category split:
plain content-word targets (`declared_word`/`word_pattern`) scored
near-perfect; sound-based targets (`global_sound`) scored notably
lower; `multi_difficulty` (n=3) was worst (meaning=2.00). Automated
profile-match was 30/30 resolved, but this is a selection artifact
(only `"reformulated"`-status items were eligible), not a general-use
resolution rate — §6.9 already measured that separately, lower.

**The single most load-bearing finding:** all 9 material SBERT-vs-human
disagreements ran the same direction (SBERT more optimistic, never the
reverse), and 6 of the 9 largest gaps involved breaking a fixed
idiom/grammatical construction ("how's it going," "drives me crazy,"
adjective→adverb POS mismatch) that the phonetic-onset flagging
mechanism has no way to detect before substituting into it. This
replicates §6.5's single earlier example as a repeatable pattern
across two independent corpora, and is judged the best-evidenced next
engineering target — not because it's the only issue found, but
because two independent analyses (proxy-gap direction, category-score
gap) converge on the same mechanism.

**Also found:** a reproducible "right now" → wrong-WordNet-sense bug
(twice, independently); a frequency-bias pattern in candidate ranking
(generic high-frequency words like "take"/"going" over-selected
regardless of fit); two cases where the human rated a real error
(pair_19's meaning-changing singular→plural, missed by both SBERT and
the rater) or accepted an error they explicitly named in a comment
(pair_04, pair_24, pair_29) — evidence that a small human pilot
undercounts real defects, not just catches proxy blind spots; and an
unanticipated reversal — restructuring-escalation items (n=8)
outperformed plain substitution (n=22) on every human axis, complicating
§6.9's framing of escalation as the lower-priority path (its success
*rate* is still the bottleneck, but its output quality when it
succeeds now looks better than substitution's).

**Category:** Evaluation results / analysis. Explicitly did not
implement any of the five ranked recommendations in `VALIDATION.md`
§9.11 — user instruction was analysis first, decisions afterward.
`reformulate.py` and the pilot test setup were not touched.

### 2026-08-17-H — REFORMULATION_PROBLEM_MAP.md created; focused research pass; interface audit of app.py

**What was done, per direct user instruction:** three separate pieces of
work, none committed yet (user explicitly held off approval pending
review).

1. **`REFORMULATION_PROBLEM_MAP.md` created** — a new, explicitly *living*
   document (unlike every other dated research file in this repo) defining
   the reformulation engine as a nine-factor problem (input-intent
   inference, in-context meaning preservation, grammaticality, naturalness/
   idiomaticity, profile-difficulty resolution, word sense, cross-
   substitution interaction, restructuring vs. substitution, change-amount
   trade-off), each checked against real pilot evidence (`VALIDATION.md`
   §9.6-9.11) and, for §2.7 specifically, against the actual
   `reformulate.py`/`semantic.py` source (confirmed the per-substitution
   SBERT check does see prior substitutions in the same sentence via the
   candidate string, but always compares against the pristine original
   sentence, and the whole-text final-verification gate shares the same
   SBERT idiom-blindness as the per-substitution checks — not assumed, read
   directly). Restated the product's ultimate objective (best, most natural
   way for a specific speaker to get their own message and sentiment
   across) as the standard every factor is subordinate to, per the user's
   explicit framing.
2. **Research pass executed** (WebSearch/WebFetch, real sources) targeting
   the four areas the pilot evidenced most strongly — idiom/MWE
   preservation, word-sense disambiguation, multi-difficulty interaction,
   T5 constrained-generation/escalation — plus a survey of adjacent fields
   (GEC/clarification precedent, stuttering/AAC-specific systems,
   controllable text simplification, semantic-preservation metrics beyond
   SBERT). Findings tagged `[SOURCED]`/`[GENERAL KNOWLEDGE]`/`[GAP]`,
   crossed with feasibility for this laptop/student-scale project. Most
   actionable finds: HuggingFace `transformers` already supports
   constrained beam search with disjunctive constraints (`force_words_ids`)
   — a small-effort upgrade over manual `bad_words_ids`; `pywsd` or an
   SBERT-gloss lookup for word-sense disambiguation before candidate
   generation (small effort, fixes the "right now" bug in principle);
   spaCy `PhraseMatcher` + a curated idiom list as an idiom-preservation
   guard (small effort). One unexpected, non-technical finding: mainstream
   stuttering-therapy literature (ARTS) treats word-avoidance/substitution
   itself as a behavior therapy works to *reduce*, in tension with this
   project automating that behavior — recorded as an open framing question
   in `REFORMULATION_PROBLEM_MAP.md` §2.9, not resolved here.
3. **Interface audit of `app.py`** — removed one genuinely dead CSS rule
   (`.pipe-card`, confirmed via a script counting every class selector's
   usage count across the file — it was the only one appearing just once,
   i.e. only in its own definition; every other class is actually applied
   somewhere). Softened three places where the UI implied SBERT/automated
   checks are a stronger guarantee than the now-twice-confirmed evidence
   supports: the sidebar "Meaning check active" banner (now "Meaning
   screen active," explicitly notes it can miss idiom breaks and wrong
   word senses), the sidebar "How it works" blurb (added a "Known limits"
   paragraph naming the same two failure modes in user-facing language),
   and the results-page metric label ("Meaning kept" → "Meaning
   similarity," plus a new caption stating these are automated estimates,
   not a human judgment). No layout change, no feature removed, no engine
   change — `sanitize_input()`/`reformulate()`/`grammar.py` untouched.
   Verified via `tests/app_test.py` (all scenarios pass, run with the
   project's `venv/Scripts/python.exe`) and `tests/smoke.py` (unchanged
   output) that nothing broke.

**Category:** Research / documentation / UI copy. No reformulation-engine
behavior changed. Nothing committed — per direct user instruction, changes
are staged locally for review, not pushed.

### 2026-08-17-I — R19 implemented: idiom/fixed-expression guard, verified against real pilot data

**What was done, per the user's explicit approval and sequencing**
("commit the research/interface work once checked, then idiom guard is
the next actual implementation"): `REFORMULATION_PROBLEM_MAP.md` §5 item
1, the highest-evidence item in that document.

`semantic.py` gained `IDIOM_PHRASES` (exact multi-word matches: "how 's
it going", "what 's going on", "right now/away/here") and
`IDIOM_PHRASE_PATTERNS` (a pronoun-wildcard mechanism for "drives/
driving/drove/drive {pron} crazy" — spelling out every pronoun by hand
would've been error-prone/incomplete). Both feed the existing
`protected_positions()` mechanism `reformulate.py` already used to block
substitution at a position (same code path `PROTECTED_PHRASES`/stop
words already used — not new machinery).

**A follow-up correctness issue found and fixed in the same pass, not
shipped with a known gap:** the first version silently excluded
idiom-protected words from `flagged_words_before`/`after` entirely, the
same as stop words always have been. Correct for stop words (never real
difficulty candidates); wrong for an idiom-locked *content* word that
genuinely matches a declared sound — it made "difficulty resolved: true"
misleading for a sentence where the difficulty is still there,
unaddressed, just no longer counted. Fixed via a new
`_idiom_protected_matches()` in `reformulate.py`: still excluded from
substitution (unchanged, correct), but now counted in
`flagged_words_before`/`after` and reported in `skipped` with reason
"part of a fixed expression — left unchanged to avoid breaking it";
sentence status becomes `could_not_safely_reformulate` instead of the
misleading `no_change_needed` when that's the only match.

**Verification, per the user's explicit "test it properly... see whether
the human-proxy failures actually decrease" instruction:** new script
`eval/idiom_guard_recheck.py` re-runs the FROZEN v3 pilot corpus
(`eval/pilot_pairs.json`, never overwritten — same discipline as
§8.4/§9.4) through the current engine and diffs against what P1 actually
rated. Result: the exact broken outputs P1 rated poorly ("how's it
**taking**", "going me crazy") no longer occur; "right now" survives in
both cases that used to break it; 26/30 pairs are byte-identical (zero
collateral change); pair_29/pair_30 (also on the high-disagreement list
but NOT idiom breaks) correctly came back untouched, confirmed rather
than assumed out of scope. Full regression suite re-run twice (before
and after the metrics follow-up fix): `tests/reformulate_test.py`
(20/20, 3 new idiom-guard tests using the real pilot sentences),
`tests/semantic_test.py` (new file, 12/12), `tests/app_test.py`,
`tests/difficulty_profile_test.py` (50/50), `tests/roadmap_test.py`
(3/3) all pass. `tests/smoke.py` diffed against both committed
baselines — exactly one intended, isolated change in each (a "right
now" test sentence no longer gets wrongly substituted), nothing else
shifted; both baselines regenerated and committed.
`eval/reformulation_eval.py` (Stage 6, 18 cases) and
`eval/reformulation_escalation_rate.py` (210 cases) both re-run and
produced **byte-identical** output to the pre-change committed CSVs —
confirmed via direct grep that neither corpus contains any of the new
guard's trigger phrases before assuming zero overlap, not inferred.

**The honest trade-off, not glossed over:** when the *only* word
matching a declared difficulty sits inside a protected idiom
("how's it **going**", "driving me **crazy**"), the engine now correctly
leaves the sentence alone and reports the difficulty as unresolved,
rather than shipping a broken substitution and reporting it as resolved.
Same "never ship a bad guess" philosophy §6.3's Cause B already
established for escalation, now shown to extend to substitution once an
idiom guard exists.

**Category:** Reformulation-engine implementation (R19/`REFORMULATION_
PROBLEM_MAP.md` §5 item 1). Full record: `VALIDATION.md` §10;
`REFORMULATION_PROBLEM_MAP.md` §2.4/§2.5/§5 (updated, living document);
`ROADMAP.md` R19 (new, done) and R18 (cross-referenced). Not yet
committed — pending the same review/approval flow as the rest of this
session's work.

### 2026-08-17-J — R20 implemented: word-sense disambiguation, corrected against two real regressions found by re-running the eval corpus

**What was done, per the user's explicit sequencing** ("Implement #2:
word-sense disambiguation... Re-run the evaluation corpus + targeted
tests"): `REFORMULATION_PROBLEM_MAP.md` §5 item 2, the fix for the
reproducible "right"→"justly"/"properly" bug (`VALIDATION.md` §9.9).

`semantic.py::disambiguate_synset(word, wn_pos, sentence)` picks the one
WordNet synset whose gloss best matches the given context (SBERT, the
model already loaded for everything else — the small-effort option per
`REFORMULATION_PROBLEM_MAP.md` §3.2/§4, not `pywsd`). `engine.py` gained
a `restrict_synsets` parameter so candidate generation pulls from only
that sense instead of unioning every same-POS sense. Verified this
fixes the *general* problem, not just "right now": "He'll be right over
to help." (not covered by R19's idiom list) correctly resolves to the
"immediately" sense.

**This did not ship on the first pass — re-running Stage 6's corpus
(exactly as instructed, not skipped) found two real regressions,**
diffed at the raw-CSV level, not just read from the aggregate:
`avg_flagged_after` 0.9444→1.0, `avg_meaning_preservation` 0.9785→0.9703.
Root-caused as two distinct mechanisms: (1) `fm_multiple_difficult_words`
— a profile declaring both "reviewed" and "examined" difficult produced
"reviewed"→"examined" as a substitution, since nothing checked a
candidate against the profile's *other* declared words, only the
global-sound phoneme veto; making candidate ranking more precise (this
same fix) made this collision more likely, not less. (2)
`fm_context_dependent_substitution` ("He runs the company... before he
runs three miles.") — both occurrences of "runs" were disambiguated
against the identical whole-sentence context, so both got the identical
sense and the identical (wrong-for-at-least-one) replacement,
measurably worsening an already-known-hard, already-disclosed failure
mode (SBERT similarity 0.9475→0.8739).

**Both fixed in the same pass, verified independently before
re-measuring:** (1) `_try_substitution`'s acceptance loop now also
rejects a candidate matching `profile.find_word()`. (2)
`disambiguate_synset` is now called with a small local token window
(`_local_context_window()`, ±6 tokens) instead of the whole sentence —
the two "runs" occurrences now resolve independently. Re-measured:
`avg_flagged_after` and `avg_difficulty_reduction_pct` both back to
full parity with the pre-WSD baseline; `avg_meaning_preservation`
settled at 0.9652 (a real, disclosed, NOT-engineered-around residual
cost — single-sense candidate pools are sometimes smaller/lower-scoring
than the old sense-mixed ones even when the sense picked is correct).

**Confirmed at scale, not just on Stage 6's 18 cases:** the 210-case
ordinary-text corpus (`eval/reformulation_escalation_rate.py`) was
re-run and shows the same cost generalizes — escalation-trigger rate
rose 10.4%→14.1% at an unchanged ~42% escalation success rate, meaning
a real, quantified fraction of previously-successful substitutions now
correctly escalate instead (some succeed differently, some correctly
refuse). This directly raises R18's priority (updated separately).

**Re-checked against the real, frozen pilot corpus**
(`eval/idiom_guard_recheck.py`, still never overwritten): 13/30 pairs
now differ from the frozen record. Two of P1's own explicitly-
articulated grammar complaints are directly fixed — pair_24 "valuable"→
"worth" (P1: "Must be worthy not worth") now produces "worthy"; pair_04
"forgot"→"missed about that" (P1: "missed that would be better") is now
left completely unchanged rather than shipping the ungrammatical guess.
Two different-class bugs confirmed still open, named rather than
implied fixed: pair_13's adjective-for-adverb POS mismatch (unaffected
by word sense, a different bug class) and pair_29's phrasal-verb idiom
("push the meeting" meaning "postpone," not on R19's curated idiom
list).

**Test coverage:** `tests/reformulate_test.py` grew from 20 to 23 tests
(general-context "right" sense outside the idiom list, candidate-
collision, repeated-word-different-senses — using the exact sentences
that found each regression, not synthetic restatements); one
pre-existing test updated to use a sentence that reliably still
produces a substitution rather than the now-correctly-escalating
"strong decision" case. Full regression suite (`tests/semantic_test.py`,
`tests/app_test.py`, `tests/difficulty_profile_test.py`,
`tests/roadmap_test.py`, `tests/rephrase_test.py`) all pass.
`tests/smoke.py` byte-identical against both committed baselines — no
update needed this time (none of that corpus's sentences are
sense-ambiguous in a way that changes the final chosen candidate).

**Category:** Reformulation-engine implementation (R20/`REFORMULATION_
PROBLEM_MAP.md` §5 item 2). Full record: `VALIDATION.md` §11;
`REFORMULATION_PROBLEM_MAP.md` §2.6/§2.7/§5 (updated, living document);
`ROADMAP.md` R20 (new, done) and R18 (cross-referenced, raised
priority). Not yet committed — pending the same review/approval flow.

### 2026-08-17-K — Two research passes: phrase-level replacement tier; fine-tuning/specializing a model for this task

**What was done, prompted directly by two user questions, not
self-initiated:** (1) whether the idiom guard (R19) could go further —
replace a whole flagged phrase with an equivalent easier phrase instead
of only protecting-and-leaving-alone or escalating the whole sentence;
(2) whether T5 should be fine-tuned/specialized for this task
specifically, given the project's longer-term "profile-to-profile" full
speech reformulation goal. Two research passes run in parallel
(WebSearch/WebFetch, real sources), synthesized into
`REFORMULATION_PROBLEM_MAP.md` §3.8/§3.9. No code changed.

**Phrase-level tier (§3.8):** confirmed as a real, currently-studied
task, not a stretch — PARSEME 2.0's MWE-2026 shared task (co-located
with EACL 2026) has a subtask literally defined as "paraphrase a
sentence containing an MWE to remove idiomaticity." PIE (ACL MWE 2021)
and a AAAI 2022 follow-up give a working task framing and a
sub-sentence-aware metric (SARI). MAGPIE's core insight — idiomaticity
is usage-dependent, not phrase-dependent — is a real limitation of
R19's static curated-list approach, not yet acted on. Most actionable
near-term path found: reuse the *existing* T5 restructuring call but
scope its input to a local window around the idiom instead of the whole
sentence, splice back in — no new model, no training. Evaluation must
score the resulting full sentence, not the isolated phrase swap (a
directly relevant paper found isolated-span metrics correlate poorly
with human judgment, ρ 0–0.3, vs. context-aware scoring, ρ 0.7–0.9) —
this project already does exactly that for the sentence-restructuring
tier, so no new evaluation design is needed, just reuse.

**Fine-tuning/specialization (§3.9):** the closest real precedent
(ParaDetox, ACL 2022 — BART-base fine-tuned on ~10K toxic→non-toxic
pairs) operates at word/topic/style level, not phoneme level. No
published work fine-tunes for phoneme-level avoidance specifically —
a genuine, first-of-kind gap, not a template to copy. PEFT (LoRA)
fine-tuning of T5-base is realistic on a single consumer GPU, not
CPU-only (no sourced benchmark for realistic CPU-only training at this
scale) — this project's current CPU-only setup would need a real
infrastructure decision (a GPU) before fine-tuning is even possible.
**The load-bearing finding:** prompting a capable instruction-tuned
model, with the constraint spelled out in-context, is a documented,
evaluated, *competing* alternative to fine-tuning in the closest
analogous literature (ReadCtrl/MedReadCtrl, 2024-2025) — not a lesser
fallback. Document/speech-level profile-conditioned reformulation
(the project's own longer-term goal) is confirmed real and harder in
the literature (naive sentence-by-sentence looping is not adequate for
document-level coherence), with no direct speaker-facing precedent —
genuinely future work, not something to start now.

**The convergence:** both research passes, run independently and blind
to each other's findings, arrived at the same practical near-term
recommendation — try a stronger, promptable model for the restructuring
step, with the constraint's *reason* (not just a blocklist) spelled out
in-context, before building an idiom classifier or fine-tuning anything.
Zero training cost; directly tests whether Cause B (§2.8, the T5
escalation failure mode) is a knowledge problem or a mechanism problem.

**Category:** Research only — `REFORMULATION_PROBLEM_MAP.md` §3.8/§3.9/
§4/§5/§6/§7 updated (living document), `reformulate.py`/`semantic.py`/
`rephrase.py` untouched. Not committed — pending user review, per the
established pattern this session.

### 2026-08-17-L — R21: diagnostic experiment (promptable model + reason vs. blocklist), negative result, phrase-tier correctly not started

**What was done, per direct user instruction:** run the diagnostic
experiment §5 item 3 named, measuring success/meaning preservation/
naturalness/difficulty-avoidance/runtime/failure-modes against the
current production baseline, without replacing the current engine, and
only proceed to the phrase-level tier if the result showed a meaningful
improvement.

New script `eval/escalation_model_comparison.py`. Failing-case set: all
22 real (profile, sentence) pairs from the committed 210-case
ordinary-text corpus where production escalation currently triggers and
fails — re-derived directly from `reformulate.reformulate()`, not
hand-picked. Baseline: `rephrase.generate_candidates` (current
production path, `bad_words_ids` only). Candidate: `google/flan-t5-base`
(247.6M params, chosen to be comparable in size to the current model's
222.9M so any gap isn't just "bigger model wins"), prompted with the
flagged words **and** a natural-language reason derived from the
profile (e.g. "The speaker stutters on words that start with the
sound(s) s..."), with no `bad_words_ids` — isolating explanation from
hard blocking. A third, hybrid condition (reason prompt **and**
`bad_words_ids` together) was added after the first result. Every
candidate from every condition was scored with the **exact same three
checks** `_try_escalation` already applies (SBERT similarity, negation
consistency, a post-hoc phoneme/blocked-word scan) — no new or looser
verification logic for the new model.

**Result:** baseline 0/22 passed (avg. sim 0.865); reason-only 1/22
(avg. sim **0.950**); hybrid 2/22 (avg. sim 0.812, worse than baseline
despite more passes). Failure-reason breakdown showed the mechanism
precisely: baseline fails roughly evenly on leaks (14) and low
similarity (8); reason-only fails almost entirely on leaks (20) — high
meaning preservation, but the model doesn't reliably obey the
phonological instruction; hybrid partially recovers leak-avoidance (10)
at a real fluency cost (10 low-similarity failures, plus one genuinely
new failure mode: the model echoed a fragment of its own instruction
prompt back as the "rewritten" sentence for the densest-profile case).

**Robustness check, not skipped:** before concluding, the same
reason-only and hybrid conditions were re-run with `google/flan-t5-large`
(783.2M params, 3.5×) on a stratified 8-case sample. Same picture,
stronger on the meaning-preservation axis (avg. sim 0.982 reason-only)
and unchanged on the pass-rate axis (0/8 reason-only, 1/8 hybrid) —
rules out "the model was just too small to understand the instruction"
specifically, rather than leaving that as an unexamined possibility.

**Verdict, stated plainly rather than softened:** does not clear the
bar for "meaningful improvement" the user set. Pass rate stayed far
below anything usable at every tested configuration and model size.
Per the plan's own explicit condition, the phrase-level replacement
tier (`REFORMULATION_PROBLEM_MAP.md` §5 item 4) was **not** started as
a result — this is reported as a negative result, not reframed as a
partial success. The one real, positive, twice-replicated finding
(reason-based prompting substantially improves meaning preservation) is
preserved and folded into how the *next* item (constrained beam search,
R18/§5 item 5) should be tested — combined with reason-prompting, not
assumed to be made redundant by it.

**Category:** Reformulation-engine diagnostic experiment (R21). No
change to `reformulate.py`/`rephrase.py`/`semantic.py` — the current
engine was not touched or replaced, per direct instruction. Full
record: `VALIDATION.md` §12; `REFORMULATION_PROBLEM_MAP.md` §2.8/§5
(updated, living document); `ROADMAP.md` R21 (new) and R18
(cross-referenced). Not yet committed — pending the same review/
approval flow as the rest of this session's work.

### 2026-08-17-M — R22: constrained beam search (`force_words_ids`) found blocked, not evaluated

**What was done:** per the plan's next step after R21, attempted to
evaluate HuggingFace constrained beam search (`force_words_ids`) on the
current production model, as `REFORMULATION_PROBLEM_MAP.md` §3.3's
research pass had described it — small effort, built into `transformers`,
no new dependency.

**What was found, before any actual evaluation could run:** a minimal
smoke test (`model.generate(..., force_words_ids=[[...]])`) against
`transformers==5.10.2` (this project's installed version) raised
`ValueError: Constrained Beam Search requires trust_remote_code=True...
it loads https://hf.co/transformers-community/constrained-beam-search`
— the feature has been moved out of core `transformers` into a
community-maintained `custom_generate` repo, fetched from the Hub at
call time. Retrying with `trust_remote_code=True` (accepting a category
of risk — Hub-fetched code executed at runtime — this project has not
taken on anywhere else, for SBERT or either T5 checkpoint) failed
differently: `OSError: transformers-community/constrained-beam-search
does not contain a custom_generate subdirectory with a generate.py
file` — the replacement repo does not currently provide a loadable
implementation. Checked for a lower-level fallback:
`DisjunctiveConstraint`/`PhrasalConstraint` are no longer importable
from `transformers.generation` in this version either.

**Why this matters beyond "one API call didn't work":** the earlier
research pass's claim that this technique is small-effort and dependency-
free was based on published documentation, not tested against this
project's actual installed environment — and turned out not to hold.
This is exactly the kind of gap this project's own discipline (verify
before recommending, memory guidance included) exists to catch, applied
here to a research finding rather than a remembered fact.

**Not decided here, surfaced instead:** three real paths forward exist
— pin an older `transformers` version (affects every model call in this
project, a real compatibility-risk decision, not evaluated for side
effects here), accept `trust_remote_code=True` and wait for/contribute
to the community repo, or hand-implement disjunctive constrained
decoding (materially larger than "small," closer to the NeuroLogic
Decoding route §3.3 already flagged as medium-effort with no maintained
package). None of these was chosen unilaterally — this is a dependency-
footprint decision affecting the whole project, not a pure research
step, so it's reported to the user rather than decided mid-diagnostic.

**Category:** Reformulation-engine diagnostic — blocked before
execution, not a completed evaluation. No change to `reformulate.py`/
`rephrase.py`/`semantic.py`, no dependency version changed. Full record:
`VALIDATION.md` §13; `REFORMULATION_PROBLEM_MAP.md` §4/§5 (updated,
living document); `ROADMAP.md` R22 (new, blocked). Not committed —
pending the same review/approval flow as the rest of this session's
work.

### 2026-08-18-A — R23: decoder-only model tested against T5 baseline, closed negative

**What was done, per direct instruction:** after R21 (prompting) and
R22 (blocked), test whether a genuinely different architecture family
— a small, decoder-only, instruction-tuned model — beats the current
T5 escalation path, without touching the installed `transformers`
version, without `trust_remote_code`, and without any new heavy
dependency.

**Candidate selection, verified against this environment first:**
Qwen2.5-0.5B-Instruct (494.0M params) and Qwen2.5-1.5B-Instruct
(1543.7M params) — both confirmed to load via `AutoModelForCausalLM`
with no `trust_remote_code` and no authentication before any
benchmarking began. Gemma and Llama were excluded on sight — both
gated on Hugging Face, and this project makes unauthenticated requests
only. SmolLM2 was not tested (a secondary source suggested it needs
`trust_remote_code`, not independently re-verified, since the two Qwen
sizes already gave a clear enough signal).

**Method:** `eval/escalation_model_comparison_decoder.py`, reusing
R21's case-finding and verification functions directly — same 22 real
currently-failing cases, same checks. A calibration pass found beam
search/sampling (num_beams=2-4) took 60-106s per call for negligible
diversity benefit (candidates clustered on the same output regardless
of strategy), so greedy decoding became the default generation
strategy — a disclosed methodology difference from R21's beam search,
not an oversight. **A real bug was found and fixed before trusting any
result:** the first greedy pass produced degenerate, repeated-prompt-
fragment output, traced to a dropped `no_repeat_ngram_size` parameter
when switching away from beam search; fixed
(`no_repeat_ngram_size=3` + `repetition_penalty=1.3`), reconfirmed, and
only then were results recorded.

**Result:** Qwen2.5-0.5B (n=8, complete run): 0/8 passed, avg. sim
0.663 (reason-only) / 0.571 (hybrid) — worse than the T5 baseline
(0.861) and far worse than R21's flan-t5-base (0.950). Failure-mode
breakdown inverted from R21's pattern: flan-t5 mostly leaked the
constraint while staying faithful; Qwen2.5-0.5B mostly failed on basic
faithfulness (7-8 of 8 cases below the similarity threshold, only 0-1
leaked) — the model frequently didn't perform the rewrite task at all,
producing hallucinated unrelated content or confused meta-commentary
about the instruction itself in some cases. Qwen2.5-1.5B (n=2, pilot
only — the user stopped the session before this reached n=8): better
task-following (genuine rewrites, not hallucination) but stilted
phrasing and one outright factual error (a "fresh pastry" rewritten as
an "unbaked treat" — a meaning change, not a style issue). Runtime:
~31s/case (0.5B) and ~97s/case (1.5B), a 10-40x slowdown versus the T5
family's ~2.6-8s/case at comparable or larger parameter counts.

**Verdict:** decoder-only, at this family and these sizes, is not
better suited to this task within this project's actual constraints —
it loses on meaning preservation, loses on task-reliability at the
smaller size, and loses badly on runtime at both sizes. Read as a
likely structural cost of decoder-only autoregressive generation via
plain `transformers` CPU inference (no quantization/optimized runtime),
not a "wrong checkpoint" problem — a bigger model in this family would
plausibly narrow the quality gap further but predictably widen the
runtime gap, so there's no obviously-better size left to try inside
these constraints. This closes `REFORMULATION_PROBLEM_MAP.md` §5 item
3's investigation on a third independent angle (prompting, constrained
decoding, model-family swap) — none cleared the bar. The one remaining
lever that could change this (an optimized/quantized local-inference
runtime) is a new-dependency decision, surfaced separately, not
decided here — same category as R22's open question.

**Category:** Reformulation-engine diagnostic experiment (R23). No
change to `reformulate.py`/`rephrase.py`/`semantic.py`, no dependency
added or changed — the current engine was not touched. Full record:
`VALIDATION.md` §14; `REFORMULATION_PROBLEM_MAP.md` §4/§5 (updated,
living document); `ROADMAP.md` R23 (new).

### 2026-08-18-B — R24: MeaningBERT validated as a second semantic-preservation signal, real but partial

**What was done, per the user's approved sequence and explicit scope
limit:** after R21-R23 closed the model/decoding-swap avenue, the user
approved C (validate a second semantic signal) → A (phrase-level tier)
→ E (re-examine multi-difficulty) → reassess, and specifically asked
for Option C to run first "with strict limits so it doesn't disappear
into another four-hour experiment." Honored directly: one small model
(MeaningBERT, 109.5M params, no `trust_remote_code`, no gating), 14
sentence pairs pulled from data already recorded in the repo (9 known
SBERT-vs-human disagreement cases from `VALIDATION.md` §9.7, plus 5
control pairs), single forward passes only — no new corpus, no
generation, no long-running sweep. Total wall-clock: one model download
plus seconds of scoring, not hours.

**Result:** genuinely mixed, reported as found rather than smoothed
into a clean verdict either direction. MeaningBERT catches several
idiom-adjacent breaks SBERT missed badly — most clearly pair_11
("drives me crazy" → "going me crazy," a causative-construction break):
SBERT scored it 0.968 (near-perfect, wrong), MeaningBERT scores it 48.0,
correctly flagging the break with a wide margin below every control
pair (81.5-94.5). Same directional pattern, smaller margin, on three
other disagreement pairs. **But MeaningBERT completely misses pair_28 —
the single worst human-rated case in the entire dataset** (meaning=1/5,
the floor of the scale): it scores 94.5, indistinguishable from the
clean control pairs, the same mistake SBERT made (0.912). Two other
disagreement pairs (pair_06, pair_02 — register/formality shifts, not
true idiom breaks) scored high on MeaningBERT too, plausibly the more
accurate read of those two cases rather than a miss.

**Interpretation:** not a strict improvement over SBERT — a different,
overlapping-but-not-superset set of blind spots. This is concrete
evidence, not just an architectural argument, that a better similarity
metric alone does not substitute for the phrase-level tier's structural
approach (item 4): pair_28 is exactly the class of case that item
targets by detecting the fixed expression before substitution, and no
similarity metric tested so far — old or new — caught it after the
fact.

**Decision:** proceed with wiring MeaningBERT into `reformulate.py`/
`app.py` as a genuine second, reported-alongside signal — never
replacing SBERT, never silently blended into one score (Practice.md
§10) — exactly the scope already planned for this item, not upgraded
to "the fix" on the strength of this result. Its demonstrated value is
flagging disagreement between the two signals, not serving as a
stronger standalone gate. **This validation step is complete; the
actual engine wiring has not been built yet** — a separate step,
expected to be confirmed before it's made, consistent with this
session's established checkpoint pattern.

**Category:** Evaluation-infrastructure validation (R24). No change to
`reformulate.py`/`app.py`/`semantic.py` — validation only, per the
user's explicit scope limit. Full record: `VALIDATION.md` §15;
`REFORMULATION_PROBLEM_MAP.md` §3.7/§4/§5 (updated, living document);
`ROADMAP.md` R24 (new).

### 2026-08-18-C — R25: phrase-level replacement tier implemented and verified

**What was done, per direct instruction (Option A of the approved C →
A → E → reassess sequence, requested directly rather than waiting on
item 3's original gate):** first laid out the exact implementation plan
(trigger/detection, local T5 generation, splicing, full-sentence
verification, fallback behavior, affected files, regression tests) for
review, then built it.

`semantic.py` gained `idiom_spans()` — the actual (start, end) span
boundaries R19's curated `IDIOM_PHRASES`/`IDIOM_PHRASE_PATTERNS` match,
not just the flattened position set `idiom_protected_positions()`
already returned; that function was refactored to derive from the new
one (confirmed behavior-preserving against the full pre-existing
`tests/semantic_test.py` suite before writing anything new).
`reformulate.py` gained `_try_phrase_replacement()`: fires only in the
"idiom-only" case (a sentence's *sole* difficulty is idiom-locked —
word-level substitution is trivially impossible since nothing is
substitutable); reuses `rephrase.generate_candidates()` completely
unchanged, scoped to a local window (span ± 5 tokens, new
`ReformulateSettings.phrase_window_radius`) rather than the whole
sentence, per the design `REFORMULATION_PROBLEM_MAP.md` §3.8 already
laid out; splices the result into the full sentence and verifies THAT —
never the window in isolation — with the exact same three checks
`_try_escalation` already uses (SBERT similarity vs. the original
sentence, negation consistency, a full-sentence phoneme/blocked-word
leak scan) plus the R20 candidate-collision check (a phrase candidate
must not reintroduce another declared word). Falls back to R19's exact
prior behavior (leave the span alone, report the difficulty honestly as
unresolved) when nothing clears every gate. Deliberately scoped to one
span per sentence and the "idiom-only" case only — the "mixed" case
(idiom span + a separately-substitutable word, e.g. pilot pair_15/
pair_28) is untouched, since every real observed pilot case is one of
these two shapes and substitution already handles the mixed case
correctly; chaining multiple spans against shifting token indices was
judged not worth the complexity for a shape with zero observed
real-world examples. `app.py` got two small, consistent changes:
`_apply_change_choices` treats the new `source: "phrase"` as sentence-
scoped for keep/revert (same as `"restructuring"`, since both changes'
`original`/`replacement` are full sentences), and a distinct CSS tag.
`reformulate.feedback_targets()` was extended to attribute phrase
changes to their declared entries — needed a new `matched_words` field
on the change dict, since `original` for this source is the whole
sentence, not one word, so the existing single-word lookup couldn't be
reused directly. No new dependency; no change to `rephrase.py`,
`engine.py`, or `grammar.py`.

**Regression tests:** `tests/semantic_test.py` gained `IdiomSpansTest`
(4 tests). `tests/reformulate_test.py` gained `PhraseTierTest` (4
tests, using the same `mock.patch.object(rf.rephrase,
"generate_candidates", ...)` determinism discipline `EscalationTest`
already established, since live T5 is documented elsewhere in this
project as non-deterministic across process launches): a mocked-good
candidate resolves the difficulty as `source="phrase"`; a mocked
candidate that changes the window but still literally contains the
flagged word is correctly rejected by the full-sentence leak scan (not
just accepted because something changed); `feedback_targets()`
attributes correctly; and one test using live T5 on a longer sentence
(local window a true subset of the sentence) confirming splicing
preserves text outside the window verbatim, written to pass whichever
way the live, non-deterministic call goes. The two pre-existing R19
tests that previously never reached a live T5 call were updated to mock
`generate_candidates` explicitly, so they stay deterministic now that
they do; the third (the mixed-case "right now" test) needed no change
and still passes unmodified — direct confirmation the mixed-case path
is genuinely untouched, not just asserted to be.

**Collateral-change check, isolated precisely rather than assumed
clean:** `tests/smoke.py` byte-identical against both baselines
(expected — it never imports `reformulate.py`, only confirms the
`semantic.py` refactor didn't disturb `SentenceRewriter`/`engine.py`).
Stage 6's 18-case corpus and the 210-case ordinary-text corpus both
byte-identical to their pre-phrase-tier committed CSVs. Re-running
`eval/idiom_guard_recheck.py` against the frozen pilot corpus initially
showed 13/30 pairs differing — but investigation found 11 of those were
already-known R20 changes (documented in `VALIDATION.md` §11.5), and
the diagnostic script's own target list, written for R19, had simply
never been updated to know about them — not a new regression. Used
`git stash` to get a true pre-phrase-tier baseline (all of R19-R24's
code, none of this session's changes) and diffed directly against the
post-phrase-tier run: **the phrase tier changed exactly one pair** —
pair_01 (`gs_hows_it_going`), from `could_not_safely_reformulate`
(idiom left alone, difficulty honestly unresolved) to `reformulated`
("Hey, how's it today?", SBERT 0.9522, difficulty resolved). Every
other pair, including pair_11 (`gs_driving_crazy`, the other genuine
idiom-only target — the phrase tier attempted it and correctly found no
usable candidate on this run, falling back safely rather than shipping
something worse), was byte-identical between the two runs.

**One honest limitation surfaced, not smoothed over:** pair_01's actual
recovered output, "Hey, how's it today?", is grammatically a little
thin — passed SBERT similarity, negation consistency, and the leak scan
cleanly, and still reads as missing a word ("going"/"doing"). Nothing
in the pipeline checks grammaticality at the phrase or sentence level;
this is the third independent instance of exactly this proxy-metric
blind spot (after pair_04/pair_24 on substitution, §9.8, and R24's
MeaningBERT miss on pair_28) — folded into `REFORMULATION_PROBLEM_MAP.md`
§2.3's running record, not treated as a clean win.

**Category:** Reformulation-engine implementation (R25/
`REFORMULATION_PROBLEM_MAP.md` §5 item 4). Full record: `VALIDATION.md`
§16; `REFORMULATION_PROBLEM_MAP.md` §2.3/§2.4/§5 (updated, living
document); `ROADMAP.md` R25 (new, done). Not yet committed — pending
the same review/approval flow as the rest of this session's work.

### 2026-08-18-D — R26: Option E re-examined, §2.7's own hypothesis corrected rather than confirmed

**What was done, per direct instruction:** Option E of the approved
C → A → E → reassess sequence — re-run the existing multi-difficulty
evaluation against the phrase-tier implementation and compare with the
pre-phrase-tier baseline. No new code, no new investigation, exactly as
instructed.

The comparison itself was already available from R25's own `git stash`
before/after (§16.3) — all three of the pilot's `multi_difficulty`
pairs (pair_28, pair_29, pair_30) are byte-identical pre- and post-
phrase-tier. To understand *why*, each pair's exact flagged
(substitutable) and idiom-protected positions were traced directly
against `reformulate.py`'s own functions with its real profile spec,
not inferred from the output text: pair_28 has one substitutable word
(`running`) and one idiom-protected word (`right`, inside "right
now") — a mixed case R25 excludes from the phrase tier by design.
pair_29 (`push`/`grab`) and pair_30 (`print`/`grab`) have **no idiom
span at all** — two ordinary, unrelated substitutable words with
nothing fixed connecting them.

**Result:** zero regressions (nothing changed, as expected — none of
the three were ever eligible for the phrase tier). But also zero
recovery, and more importantly, a specific, evidenced correction to
`REFORMULATION_PROBLEM_MAP.md` §2.7's own standing hypothesis that
multi-difficulty compounding "may already be explained by [idiom-
blindness] rather than needing its own separate fix." That hypothesis
does not hold in this sample: 2 of the 3 cases have nothing to do with
idioms. Their poor pilot scores trace to a different, already-separately
-documented mechanism (`VALIDATION.md` §9.9's "generic overused
replacement" pattern — `push`→`force`/`urge`, `grab`→`catch`/`take`/
`get`): two independent substitution slots each carry their own risk of
a weak, loosely-fitting word choice, and two chances compound that risk
in a way that has nothing to do with idiom detection.

**Category:** Evaluation/analysis only (R26/`REFORMULATION_PROBLEM_MAP.md`
§5 item 7). No code changed, no new corpus, no new experiment — pure
re-analysis of data already gathered verifying R25, per explicit scope.
Full record: `VALIDATION.md` §17; `REFORMULATION_PROBLEM_MAP.md` §2.7/§5
(updated, living document); `ROADMAP.md` R26 (new, done).

### 2026-08-19-A — R27: bounded investigation of R26's ranking mechanism and grammaticality, orchestration principle recorded

**What was done, per direct instruction:** a bounded, non-implementing
investigation of two things before proceeding with any of the previously
proposed order (MeaningBERT wiring, grammaticality wiring, idiom-guard
extension) — no ranking retuning, no dependency installs, no long
experiment.

For R26's "generic overused replacement" pattern: called the actual
production candidate-ranking path directly (`engine.get_synonyms` →
`reformulate._raw_candidates` → `semantic.rank_candidates_contextually`,
unmodified) on the real pilot sentences, with SBERT loaded, and printed
the full scored candidate table rather than just the winner. Found two
distinct mechanisms, not one: "push"→"force" is a missing-sense problem
(WordNet has no synset for "push [a meeting]" meaning postpone — no
amount of re-ranking could have found a correct candidate that was never
in the pool); "grab"→"take"/"catch" is a genuine sentence-embedding bias
toward generic, semantically-bleached words (a maximally generic word
perturbs the sentence embedding least, so it scores highest on *both*
the 0.90-weighted semantic term and the 0.10-weighted frequency term
independently — they are correlated, not competing, so the formula's
declared 90/10 split does not protect against this the way it looks like
it should). This corrects `VALIDATION.md` §9.9's framing ("a ranking
formula that rewards high corpus frequency") — direct inspection shows
the semantic term, not the frequency term, is the dominant driver in
both cases.

For grammaticality: inspected `rephrase._score_candidate`,
`reformulate._try_substitution`'s acceptance loop, `_try_escalation`,
and `_try_phrase_replacement` directly — confirmed no grammaticality
check exists anywhere in the reformulation-output verification path.
Found `grammar._correct_with_languagetool()` already exists but is wired
only into input-side `sanitize_input()`, never applied to reformulation
output. Checked the LanguageTool situation directly rather than trusting
the prior record: `language_tool_python` (v3.4.0) is pip-installed and
Java is present (`1.8.0_461`) — contradicting R23's speculative "most
likely Java isn't installed" note — but attempting to actually
instantiate `LanguageTool("en-US")` raised `SystemError: Detected java
1.8. LanguageTool requires Java >= 17 for version 6.8`. No download was
triggered (no local cache existed beforehand; the failure happens before
any download step) — the real, now-confirmed blocker is a **Java version
mismatch**, not absence. Three options surfaced, none decided
unilaterally: install a JDK 17+, pin an older `language_tool_python`/
LanguageTool-server combination compatible with Java 8, or leave blocked.

Per direct instruction, also recorded (not implemented) an orchestration
principle in `REFORMULATION_PROBLEM_MAP.md` §2.8: local substitution
stays the preferred default path (smallest change, preserves structure);
full-sentence restructuring is a first-class *alternative*, not a
replacement, meant to be triggered by a future quality-based escalation
decision — distinct from today's only trigger (hard gate failure, i.e.
"every candidate was rejected"). The `push`/`grab` cases are exactly the
gap: the winning candidate clears every existing gate and substitution
reports success, with no mechanism today to instead try a full-sentence
rewrite. Recorded as `REFORMULATION_PROBLEM_MAP.md` §5 item 11, explicitly
deferred — not scoped or implemented.

**What proceeded after the investigation, per the evidence:**
grammaticality wiring did **not** proceed (blocked, not unevaluated —
`REFORMULATION_PROBLEM_MAP.md` §5 item 12 marked BLOCKED, same category
as item 5's constrained-beam-search block). MeaningBERT (item 6,
independently validated in R24, unrelated to the LanguageTool block) was
wired into `semantic.py` (`load_meaningbert()`/`meaningbert_score()`,
same lazy-load/graceful-degradation shape as SBERT) and `reformulate.py`
(`meaning_preservation_meaningbert` in the final metrics, read-only,
never blended into `final_ok`) and `app.py` (a second, separately-labeled
metric box). Verified against R24's own recorded scores before trusting
it (48.04 vs. 48.0, 94.52 vs. 94.5, a clean control at 85.83 within the
81.5-94.5 control range) — confirms the implementation reproduces R24's
methodology, not a divergent reimplementation. The idiom guard (item 13)
was extended with the literal phrase "push the meeting" in `semantic.py`'s
`IDIOM_PHRASES`, verified with the same `git stash` isolation technique
R25/R26 established (stash only the session's code changes, run the
30-pair recheck against the true pre-change baseline, pop, run again,
diff the two runs against each other — not against the pilot corpus's
long-stale original snapshot, which reflects R19-R26's cumulative effect,
not just this change). Result: exactly one pair changed (pair_29), zero
collateral elsewhere. The fix is disclosed as partial: "push" is now
left honestly unresolved rather than mis-substituted, but pair_29's
separate "grab" problem (the still-open generic-word-ranking pattern)
is untouched by design, since this only ever targeted the missing-sense
half of that pair.

**Regression check:** two new targeted tests added
(`tests/semantic_test.py::IdiomPhraseGuardTest` — `test_push_the_meeting_
protects_push`, `test_push_alone_not_protected_outside_the_idiom`;
`tests/reformulate_test.py::IdiomGuardTest.test_push_the_meeting_
survives_while_grab_is_still_substituted`). Full suite: 107 tests
(46 in `reformulate_test.py`/`semantic_test.py`, 61 across
`app_test.py`/`rephrase_test.py`/`difficulty_profile_test.py`/
`roadmap_test.py`/`pilot_app_test.py`) — all pass. Stage 6's 18-case
corpus (`eval/reformulation_eval.py`) re-run: `reformulation_rate`
0.5556, status distribution `{reformulated: 10,
could_not_safely_reformulate: 4, no_change_needed: 4}`,
`avg_meaning_preservation` 0.9652 — byte-identical to the committed
`eval/reformulation_eval_results.csv` (`git status` confirms zero diff).
`eval/idiom_guard_recheck.py`'s `TARGET_PAIR_IDS` updated to include
`pair_29`, its stale "not an idiom break" comment corrected.

**Category:** Investigation (candidate-ranking mechanism, grammaticality
gap, LanguageTool feasibility) + two scoped implementations gated on that
investigation's evidence (MeaningBERT wiring, idiom-guard extension) +
one architecture note recorded per direct instruction, not implemented
(the orchestration escalation-trigger principle). Grammaticality wiring
explicitly did not proceed — blocked, surfaced for a future decision, not
worked around. Full record: `VALIDATION.md` §18-20;
`REFORMULATION_PROBLEM_MAP.md` §2.8, §5 items 6/11/12/13 (updated, living
document); `ROADMAP.md` R27 (new, done/partial).

### 2026-08-19-B — repo cleanup pass: `changes.md` removed; `HANDOFF.md`/`DOCS.md`/`README.md` refreshed for R17-R27

**What was done, per direct instruction:** a full-repo sweep for unused/
redundant files, followed by a content refresh of the three onboarding/
product-facing docs found to be stale.

**File audit.** Checked actual usage (imports, live call graph), not just
commit recency, for every file the user named plus a general sweep:
`paths.py`, `grammar.py`, `config.yaml`, `rewrite/`, `profiling/`, and
`eval/study/` all confirmed still load-bearing or actively used as
comparison-baseline evidence (`eval/reformulation_eval.py`/`tests/
roadmap_test.py` still exercise `SentenceRewriter`/`DifficultyAwareRewriter`
against `reformulate.py` on every Stage-6-corpus check, most recently in
R27) — none of these are unused despite having no recent commits;
stability and staleness are not the same thing. `scripts/` (fine-tuning
prep) is idle but not broken or stale — correctly gated on a GPU-access
decision (`ROADMAP.md` R9/item 9) that has never been made. Two genuine
removal candidates found: `changes.md` (a pre-`CHANGELOG.md` release-notes
log, last touched 2026-06-13, describing features since removed —
microphone profiling, a `run_app.ps1` launcher already gone from the repo)
and `tests/baseline_current.txt` (referenced by zero files in the repo).
User approved removing `changes.md` only; `tests/baseline_current.txt` was
left as-is.

**`changes.md` removed**, `git rm`. Its four current-state pointers in
`README.md` (project-structure listing, doc-set table, two prose
references) updated to point at `DECISION_LOG.md`/`CHANGELOG.md` instead.
Historical references to it in `DECISION_LOG.md` (this file, prior
entries), `RESEARCH.md`, `REFORMULATION_RESEARCH.md`, and `CHANGELOG.md`'s
own commit-log entry were left untouched — those are append-only records
of what was true at the time, not current-state pointers, and editing them
would falsify history. `DOCS.md`'s file table gained a `~~changes.md~~
Removed` row, matching its existing convention for `AUTH_README.md`'s
earlier removal.

**Documentation drift, found and fixed.** A prior full-status pass
(2026-08-19, same day) had already flagged `HANDOFF.md`, `DOCS.md`, and
`README.md` as frozen at the pre-R19 (2026-08-16 Architecture D′) state —
materially incomplete for a fresh reader, since none of R17-R27's real
engine capability (idiom guard, WSD, the phrase-level tier, MeaningBERT,
three closed model-swap attempts, the characterized-but-unfixed generic-
word-ranking bias, the grammaticality gap and its Java-version blocker) was
reflected anywhere in them. Per direct instruction, refreshed rather than
rewritten — new dated scope notes and corrected specific stale claims,
preserving the files' own established pattern of layering dated updates
rather than discarding history:
- **`HANDOFF.md`**: new 2026-08-19 scope note summarizing R17-R27 and
  pointing to `REFORMULATION_PROBLEM_MAP.md` as the current source of
  truth; the "proven vs. hypothesis" section's stale SBERT-idiom-blindness
  claim ("plausible, argued by example... not measured") corrected to
  reflect it's now been measured with real, disclosed limitations (n=1
  pilot); the R5/R6 rewrite-vs-SentenceRewriter comparison claim ("no
  comparison exists") corrected to point at the comparison that already
  ran (`VALIDATION.md` §6) and still runs on every regression check; the
  curated reading order updated to include `reformulate.py` explicitly (it,
  not `app.py`, is the actual orchestrator) and `REFORMULATION_PROBLEM_MAP.md`;
  two new pitfalls added (T5 non-determinism across process launches and
  the mocking discipline it requires; the `git stash`-isolation technique
  for verifying one change's true effect against a corpus that's drifted);
  the "documentation drift happened twice" pitfall updated to "three times"
  — this refresh itself is the third instance, named plainly rather than
  quietly fixed and left unremarked.
- **`DOCS.md`**: `reformulate.py`, `semantic.py`, `rephrase.py`, `tests/
  semantic_test.py`, and `eval/idiom_guard_recheck.py` rows updated to
  describe current capability instead of the 2026-08-16/17 snapshot;
  `idiom_guard_recheck.py`'s row corrected from "built for this one fix" to
  reflect it's been reused across five fixes since (R19/R20/R25/R26/R27).
- **`README.md`**: the "What It Does" pipeline (5 steps → 7, adding the
  idiom guard and phrase-level tier), the Features list (idiom guard, WSD,
  phrase-level replacement, MeaningBERT added), "Architecture Notes"
  (the reformulation-engine, SBERT-firewall, rephrase.py, and eval/
  sections all updated — including correcting a now-false claim that
  `reformulate.py` "hasn't yet been measured" against the retained
  pipelines, which it has, repeatedly, since Stage 6), "Known Limitations"
  (two resolved items removed/corrected — the R9 keep/revert feedback loop
  is wired, `problem_phones` now has a consumer — and the real, current
  limitations from R21-R27 added: no grammaticality signal, the generic-
  word ranking bias, no quality-based escalation trigger, no clarification
  flow, the single-participant pilot's own disclosed undercounting), and
  the documentation-set table gained a `REFORMULATION_PROBLEM_MAP.md` row.

**`CLAUDE.md` deliberately not reordered.** The user's original concern was
that `CLAUDE.md`'s reading order (`HANDOFF.md` step 2, `DOCS.md` step 3,
`REFORMULATION_PROBLEM_MAP.md` step 9) front-loads a stale picture before
reaching the current one. With `HANDOFF.md`/`DOCS.md`'s *content* now
accurate and each pointing forward to `REFORMULATION_PROBLEM_MAP.md`
itself, reading them first is no longer harmful — the root cause was
staleness, not sequencing, so fixing the content resolves the concern
without needing to restructure `CLAUDE.md`'s otherwise-reasonable
broad-to-specific order.

**Category:** Repo hygiene + documentation-drift correction, no code or
engine behavior changed. Full record: this entry; `CHANGELOG.md`.

### 2026-08-19-C — R28: grammaticality resolved-and-measured (negative); MeaningBERT test coverage added

**What was done:** per the user-approved reordering of the next-steps
plan (grammaticality investigation + MeaningBERT tests before designing
the generic-word signal or the quality-based escalation trigger, so
neither gets designed around an unvalidated signal), resolved the R27
Java-version blocker and actually measured LanguageTool's hit rate, and
closed the MeaningBERT test-coverage gap the prior audit found.

**Grammaticality.** The blocker (`SystemError: Detected java 1.8.
LanguageTool requires Java >= 17`) was resolved without a system-wide
install: downloaded a portable Temurin JRE 17.0.20 into this project's
own `.cache/jre17/`, added to `PATH` for the diagnostic subprocess only.
Ran `language_tool_python.LanguageTool("en-US")` directly against R27's
own known-broken (7 cases) and clean-control (3 cases) corpus. **Result:
0/7 caught, 0/3 false positives** — confirmed as a genuine negative, not
a broken check, via a direct sanity probe showing the tool correctly
catches classic SVA/tense errors it was never given the chance to fail
on here ("She go to the store." → `HE_VERB_AGR`; "I enjoys algorithms" →
`BASE_FORM`). This project's own failures ("a worth lesson," "data
knowledges," "going me crazy," "was recently again") are syntactically
well-formed sentences built from the wrong word — outside what a
rule-based grammar checker is built to catch. **LanguageTool itself is
now closed for this use case**, not blocked; `REFORMULATION_PROBLEM_MAP.md`
§5 item 12 updated from BLOCKED to TESTED/negative.

Two secondary findings surfaced during this investigation, both left
unfixed per explicit scope (measurement only, no production changes):
(a) the project-local cache path `paths.py` redirects `LTP_PATH` to
reproducibly fails — the bundle downloads to completion but the target
directory ends up empty and the server then fails to start; root cause
not isolated (ruled out a space-in-path theory directly — the working
default cache path has the identical space and works fine); worked
around for this diagnostic by pointing `LTP_PATH` at the default,
already-proven-working location instead. (b) `grammar.py::
_correct_with_languagetool()` has a latent bug: it uses `m.ruleId`/
`m.errorLength`, which don't exist on the installed `language_tool_python`
version's `Match` object (`rule_id`/`error_length` are correct,
confirmed directly via `AttributeError`) — sitting outside that
function's own exception handling, this would have crashed
`sanitize_input()` (and so the Reformulate button) the first time
LanguageTool ever successfully loaded *and* found an actionable match in
production. Never triggered before now, since LanguageTool has never
successfully loaded in this project until this investigation — a
concrete pre-requisite for any future work in this area, not a
theoretical risk.

**MeaningBERT test coverage.** New file `tests/meaningbert_test.py`, 9
tests — closes exactly the gap the prior ground-truth audit named
(model loads, scores stay in the valid 0-100 range, a real R24 finding
is reproduced as a regression guard, graceful degradation on model
unavailability, and — the specific gap — `reformulate()`'s real,
unmocked metrics dict is checked to actually carry the signal correctly
and never let it gate `final_verification`). All 9 pass. Full suite now
116 tests.

**Category:** Investigation (grammaticality) + test coverage (MeaningBERT).
No production code changed; no ranking weights touched. Full record:
`VALIDATION.md` §21; `ROADMAP.md` R28; `REFORMULATION_PROBLEM_MAP.md` §5
item 12.

### 2026-08-19-D — R29: candidate specificity/genericness signal designed and validated (not implemented)

**What was done:** per the approved plan (design/validate this before
the quality-based escalation trigger, so the trigger isn't built around
an unvalidated signal), read `engine.py::_wordnet_synonyms()` directly
to find the actual mechanism behind R26/R27's "grab"→"take" pattern: a
candidate pool is the union of a disambiguated synset's direct lemmas
(same specificity) and that synset's hypernym lemmas (structurally
broader, by WordNet's hierarchy) — meaning a candidate's WordNet
hypernym-depth relative to the original word's disambiguated sense is a
real, zero-new-dependency, already-available proxy for "is this a
generalization."

**Validated, not assumed:** computed depth-delta and Zipf-frequency-delta
for the real production candidate pool across 3 independent "grab"
sentences (pair_16, pair_17, pair_29) and "push" (pair_29). Depth-delta
alone flags "take" consistently (−1 to −2 hypernym levels shallower than
"grab" in every context) but also flags legitimate rarer synonyms
("seize," "clutch") as false positives. **Requiring both depth-delta
(structurally broader) and a positive Zipf-delta (anomalously more
common) cleanly separates "take" from the legitimate alternatives in
every case tested** — "seize"/"clutch" fire on depth alone since they
are *less* common than "grab," not more.

**Explicitly not implemented.** No ranking weights changed in
`semantic.py`; no new gate added to `reformulate.py`. The exact
threshold (how many hypernym-hops, how large a Zipf gap) is not settled
by 4 cases — recorded as directionally validated, not tuned, and a
future implementation decision if picked up. If implemented, the
evidence points toward an additional hard gate (same shape as the
existing antonym/phoneme/profile-collision checks), not a change to the
weighted combined-score formula.

**Category:** Signal design + validation. No production code changed;
no ranking weights touched. Full record: `VALIDATION.md` §22;
`ROADMAP.md` R29; `REFORMULATION_PROBLEM_MAP.md` §5 item 14.

### 2026-08-19-E — R30: predicate-adjective POS-tagging bug fixed (pair_13)

**What was done:** a small, independent fix, approved separately from
CONAN's escalation-trigger design work. Traced directly (not assumed)
during the R30 design investigation: `pos_tag()` tags "late" as RB in
"The bus was late again this morning." — it's actually a predicate
adjective after the copula "was," part of English's small "flat adverb"
class (identical adjective/adverb surface form: late, fast, early,
hard, ...). Because `_wn_pos("RB")` then restricts candidate generation
to adverb-sense synonyms only, this produced the long-standing
`pair_13` bug ("was late again" → "was recently again").

**Fix:** `reformulate.py::_correct_predicate_adjective_tags()`, applied
at both `pos_tag()` call sites — reclassifies RB to JJ only for a
curated `_FLAT_ADVERBS` list directly adjacent to a BE-form token. A
broader "does WordNet list any adjective sense" check was tried first
and rejected after empirical testing found it over-fires: WordNet lists
a rare satellite-adjective sense for "here" (`here.s.01`), which would
have mis-tagged "He was here." Switched to a curated list — the same
precision-over-recall tradeoff already used for `semantic.IDIOM_PHRASES`.

**Verified:** target case fixed (produces "was belated again," a
grammatically correct predicate-adjective substitution); 8 adversarial
controls confirm no false positives (genuinely adverbial "here"/"now"/
"there"/"still"/"already"/"arrived late" all correctly untouched); 3 new
regression tests added; full suite 119 tests pass; `tests/smoke.py`
byte-identical to the committed baseline (zero collateral change,
confirmed by diff).

**Category:** Bug fix, small and targeted. No ranking weights touched;
no new dependency. Full record: `VALIDATION.md` §23; `ROADMAP.md` R30.

### 2026-08-19-F — R31: evaluation corpus built, R29's genericness signal not promoted

**What was done:** Tier 2 of the approved plan — tested R29's signal
against a broader, explicitly-labeled corpus (real pilot cases with
human ratings pulled directly from `eval/pilot_responses/P1.csv`, plus
new constructed cases) rather than trusting the original 4-case
validation. Found and corrected a methodological error mid-run:
`DISABLE_DATAMUSE=1` produced a non-representative, smaller candidate
pool than actual pilot/production conditions.

**Result:** R29's combined signal flags "grab"→"take" in pair_16 and
pair_17 — two real cases the human rated 5/5/5 and preferred. A direct,
confirmed contradiction on the signal's own target pattern, not a
hypothetical risk. 7/7 correct on unrelated cases (legitimate rare
synonyms, other known-good substitutions) — the signal isn't broadly
broken, just wrong about the specific pattern it was built for.
Separately checked SBERT/MeaningBERT disagreement magnitude against
R24's own 14-pair table: no clean relationship to human-judged severity
(the single worst case has the *smallest* disagreement). Multi-
substitution interaction identified as the strongest remaining lead.

**Decision: R29 is not promoted to even a reported diagnostic signal.**
Stays research-only pending a reconciliation of why the structural
mechanism doesn't predict human judgment. Full record: `VALIDATION.md`
§24; `ROADMAP.md` R31.

### 2026-08-19-G — R32: multi-substitution interaction ruled out as a distinct mechanism

**What was done:** traced `_try_substitution()`/`reformulate()` directly
— sequential per-position processing, each candidate scored against the
pristine original sentence, no explicit cross-substitution check
anywhere in the code. Analyzed `pair_28`/`pair_29`/`pair_30` in full
(real `changes_made`, `profile_spec`, and P1's actual free-text
comments), then ran all three through **today's live engine** — not
just the frozen v3 capture — to see what's changed since. Built 2 new
cases pairing words each independently confirmed good in R31.

**Result: 5 of 5 cases (3 real + 2 new), zero exceptions — every
multi-substitution failure traces to exactly one bad substitution, never
to interaction between two.** Concretely: two of the three original
pilot defects are already fixed by unrelated prior work (R19's and
R27's idiom-guard entries) — not by anything about multiple
substitutions. A new failure class surfaced and named for future work:
inflection/word-class mismatch (e.g. "sleep"→"asleep" used as a noun;
"start"→"starting" in a finite-verb slot) — same general shape as R30's
bug, distinct instances.

**Decision: do not design a multi-substitution-specific signal.**
The category's real rating gap (§9.6) reflects doubled exposure to
already-known per-word failure classes, not a new mechanism. Redirects
the next investigation toward a general per-word grammaticality/fluency
signal (R33) rather than anything interaction-specific. Two small,
separately-fixable items named but not implemented: "running behind"
missing from the idiom guard; the inflection/word-class class needs its
own future investigation.

**Category:** Both investigations. No production code changed in either;
no ranking weights touched. Full record: `VALIDATION.md` §24-25;
`ROADMAP.md` R31-R32.

### 2026-08-19-H — R33+R34: a fluency/naturalness signal found, and its main ambiguity resolved

**R33 — what was done:** tested two candidates for detecting a
substitution that passes every gate but reads unnaturally, both via the
already-installed `transformers` package (new checkpoints only, no new
pip dependency): GPT-2 sentence-level perplexity, and DistilBERT
masked-LM word-probability at the substituted word's specific position.

**R33 result:** GPT-2 rejected outright — it rated R30's own confirmed
fix ("was belated") as *less* fluent than the exact bug it replaced
("was recently"), a direct inversion on the clearest possible test.
DistilBERT showed strong, clean separation on matched contrast pairs
(same sentence, only the flagged word differs) — e.g. "start" 0.2578 vs.
"starting" 0.0001 — and correctly rated R30's fix far above its bug. One
real ambiguity was left open: R29's own false-positive class (seize/
clutch, legitimate but uncommon grab-synonyms) scored 0.0000 when
substituted, indistinguishable from confirmed-bad cases.

**R34 — what was done:** tested the same words (plus grasp, snatch) in
two contexts each — a natural, idiomatic sentence and the same forced
"grab coffee"-style substitution context — to determine whether the low
score reflects rarity bias or genuine mismatch detection.

**R34 result:** uniform and decisive across all 4 words — each scores
high (0.05-0.44) in its natural context and collapses to 0.0000 only
when forced into the mismatched context, by ratios of 2,259× to
468,789×. **Not a rarity artifact.** The model is correctly detecting
real collocation/register mismatch. Zero confirmed false positives, zero
false negatives across R33+R34 combined.

**Decision: DistilBERT masked-LM word-probability is the strongest
candidate signal found across R28-R34** — the only one to survive every
test, including a direct, targeted attempt to falsify it. **Not yet
promoted to implementation.** This remains strong model-judgment
evidence at n=25 labeled points, not human-validated — the explicit next
step (agreed with the user) is a small blind human-rating pass on a
controlled good/bad corpus before any design or implementation work
proceeds, so a promising research result doesn't get promoted into
production on model-internal consistency alone.

**Category:** Signal investigation, two-part. No production code
changed; no ranking weights touched; no thresholds set. Full record:
`VALIDATION.md` §26-27; `ROADMAP.md` R33-R34.

### 2026-08-19-I — R35: human validation of the DistilBERT signal — 17/18 agreement, one real blind spot found

**What was done:** the explicit next step R34 called for — direct human
confirmation, not just model self-consistency. 18 sentences (known-bad
plus known-good/legitimate-rare, per R33/R34's own labeling) presented
blind and shuffled to the user, rated Natural/Acceptable/Unnatural.
Single rater — same disclosed n=1 limitation as the original P1 pilot,
named plainly rather than treated as a large study.

**Result:** 17 of 18 ratings agree with the pre-assigned label. Both
cases R34 was specifically built to resolve ("...push the meeting and
seize/clutch coffee after?") were independently rated Unnatural by the
human, exactly matching DistilBERT's 0.0000 score — direct human
confirmation of R34's inference, not just internal model consistency.

**One real, informative disagreement, reported plainly, not smoothed
over:** the human rated R30's own fix ("The bus was belated again this
morning") **Unnatural** — the single highest-scoring sentence in the
entire set by DistilBERT (0.2176). "Belated" is correct but almost
always appears in fixed collocations ("belated birthday wishes");
applying it plainly to a bus is a register/formality mismatch a native
speaker notices that the signal's collocational-fit measure did not
catch. **A genuine, disclosed blind spot, not a footnote.** A second,
milder nuance: "take coffee" was rated Acceptable, not fully Natural —
echoes R29's original genericness concern; the signal should not be
oversold as having fully resolved that question either.

**Decision: proceed to Phase 2 (fresh escalation-trigger design) — the
correlation (17-18/18) is the strongest validation result across
R28-R35** and clears the bar the user set before any design work. Both
the "belated" blind spot and the "take coffee" nuance are carried
forward as explicit, binding constraints on that design, not treated as
resolved or smoothed over.

**Category:** Human validation. No production code changed; no ranking
weights touched; no thresholds set. Full record: `VALIDATION.md` §28;
`ROADMAP.md` R35.

### 2026-08-19-J — R36: larger-scale naturalness signal validation — evidence supports Option A now

**What was done:** the final validation pass before an implementation
decision, per direct instruction — a 38-case corpus (up from R33-R35's
25), covering every category requested: known-bad, known-good,
legitimate rare/formal, collocation/register mismatch (specifically
expanded to stress-test the "belated" blind spot beyond one sentence),
grammatical/inflection (entirely new cases, closing the standing R32
open item), sentence-length variation, and constructed multi-
substitution sentences testing whether per-position independent
checking on the final sentence remains valid when multiple substitutions
co-occur.

**Result:** zero false negatives at every candidate cutoff tested. False
positives are not random — all concentrate on the word "rest," recurring
across three separate sentences, a specific and now-characterized quirk.
The register-mismatch blind spot is real but **not universal**: 2 of 5
stress cases (belated, and likely — unconfirmed — procure) show it; the
other 2 (consume, terminate) are caught correctly, meaning the blind
spot is word-specific, not a blanket failure of the approach.
Inflection/word-class mismatch, tested on entirely new sentences with no
overlap with prior corpora, is cleanly caught — confirmed as a
complementary signal, closing R32's standing open item. Sentence length
has no measurable effect. **Multi-substitution: no cross-contamination
found between positions** — a good substitution's score stays consistent
with its solo-sentence value even when a bad substitution sits nearby in
the same sentence, directly validating the Phase-2 design's central
architectural assumption (check each position independently on the
final, fully-assembled sentence).

**Decision, reserved for the user per explicit instruction, not made
here:** the evidence is strong enough to justify Option A (reported-only
diagnostics, the same rollout pattern MeaningBERT used) now. It is not
yet strong enough for Option B (full auto-escalation control) — the
register-mismatch blind spot's edges are better scoped than before but
not fully mapped, and the combined corpus (61 cases across R33-R36) is
still research-scale, not production-scale.

**Category:** Final pre-implementation validation. No production code
changed; no ranking weights touched; no threshold selected for
deployment. Full record: `VALIDATION.md` §29; `ROADMAP.md` R36.

### 2026-08-19-K — R37: contextual-fit signal wired in as a reported-only diagnostic (Option A)

**What was done:** the user chose Option A after reviewing R36 —
reported-only diagnostics first, the same rollout MeaningBERT used
(R24/R27), not the full soft-trigger → escalation architecture from the
Phase-2 design. This is the first production code change in the entire
R28-R36 investigation arc; everything before it was read-only.

`semantic.py` gained `load_contextual_fit_model()`/`contextual_fit_
status()`/`contextual_fit_score()` — the exact masked-LM word-
probability mechanism validated across R33-R36 (`distilbert-base-
uncased`), same lazy-load/graceful-degradation shape as
`load_meaningbert()`. Named "contextual fit" specifically to avoid
confusion with `naturalness.py`'s unrelated edit-ratio metric.
`reformulate.py`: every `source == "substitution"` change gets its
replacement word scored against the **final, fully-assembled sentence**
(never the original, never mid-loop) immediately after `_try_
substitution()` succeeds — matching the Phase-2 design's validated
placement exactly. Deliberately scoped to substitution-sourced changes
only — phrase-tier and restructuring output were never validated for
this signal, so they don't receive it. `app.py` surfaces the score
per-change, explicitly labeled diagnostic-only.

`tests/contextual_fit_test.py` (new, 12 tests): load/status,
known-bad/known-good regression guards reproducing R33/R36's own cases,
an explicit assertion that the "belated" blind spot **is present and
expected** (a documented characteristic, not a bug — if it ever flips,
that's a real change worth noticing, not silent drift), graceful
degradation, and — the actual behavioral contract, not just
documentation — a direct test that forcing the score to 0.0 does not
flip `final_ok` or `status`, plus a test confirming restructuring-
sourced changes never receive the field at all.

**Verified:** full suite 131 tests, all pass. `tests/smoke.py` output
byte-identical to `tests/baseline_sbert.txt` — zero collateral change on
the existing regression corpus, confirmed by diff.

**Category:** Implementation, Option A only. No gate, no escalation
trigger, no threshold selected. Option B (the full soft-trigger
architecture) remains a separate, future, explicitly-gated decision —
not started here. Full record: `VALIDATION.md` §30; `ROADMAP.md` R37.

### 2026-08-19-L — R38: final system-level evaluation against the problem statement

**What was done:** closes the R17-R37 investigation arc with a bounded
evaluation against the project's own governing question (does the
system reformulate difficult speech text into easier-to-say text while
preserving meaning, context, safety, and linguistic quality) — reusing
existing frozen corpora and existing measurements only, per explicit
instruction, plus one retroactive application of R37's already-
implemented signal to real (not lab-constructed) data: every recorded
substitution in the frozen pilot corpus was re-scored with `contextual_
fit_score()`.

**Result, by dimension, each explicitly labeled by evidence class:**
Safety (hard gates, zero known failures reaching production) and
SBERT-enforced meaning preservation (the only meaning signal that
actually gates behavior, 0.9785 average, highest of three systems
compared) are the strongest, unqualified claims available. Difficulty
reduction and over-reformulation are real, conservative-by-design
properties, both directly measured. MeaningBERT and the contextual-fit
signal both add real value with specific, named blind spots — the
retroactive real-data check found **2 new contextual-fit false
positives** ("forgot"→"missed," "happened"→"occurred") beyond the
already-known "rest" quirk, a higher false-positive rate than R33-R36's
lab corpus alone suggested, reported here rather than smoothed over.
Escalation exists only as an unwired diagnostic capability — no
auto-escalation runs anywhere in the current system, and this report is
explicit that capability and behavior are not the same claim.
**Preference is unresolved**: the only number on record (73.3%,
pilot) reflects a single participant's judgment of pre-R19-R37 output,
already disclosed at collection time as a likely upper bound, and
cannot be treated as a current measurement.

**Decision: the problem statement is answered partially and unevenly
across dimensions** — stated as the actual finding of this evaluation,
not a hedge on an otherwise complete answer. **The single largest
remaining evidentiary gap is a genuine current-state human evaluation**
— no valid preference or naturalness measurement exists for the system
as it actually stands today, only for eras that predate most of R17-R37's
fixes. Designing that evaluation, not another signal investigation, is
the justified next step.

**Category:** Final evaluation, closing the R17-R38 arc. No production
code changed; no new corpus or human study conducted; no new metrics
introduced. Full record: `VALIDATION.md` §31; `ROADMAP.md` R38.

### 2026-08-20/21-A — R39: current-state human evaluation executed, closing R38's largest gap

**What was done:** the human evaluation R38 recommended, actually run.
New `eval/pilot_select_pairs_v4.py` (mirrors `pilot_select_pairs.py`'s
schema exactly) regenerated 20 pairs through today's live engine, with
live Datamuse — deliberately not `DISABLE_DATAMUSE=1`, since R31 found
that flag changes the candidate pool materially and this evaluation is
about real, current behavior, not internal reproducibility. Group A
(10) reused the exact case_id/text/profile of 10 original v3 items for
a direct before/after delta; Group B (10) is fresh coverage. The
original v3 `pilot_pairs.json`/`pilot_responses/P1.csv` were archived
to `eval/archive_v3/` first, untouched, mirroring the existing
`archive_v2/` precedent — never overwritten without a backup.
`eval/pilot_app.py` itself ran completely unmodified. Single rater
(n=1), same disclosed limitation as every prior pass.

**Three items required swapping before generation succeeded** — each a
real finding, not friction to route around: `gs_driving_crazy` ("The
kids are driving me crazy today.") now produces `could_not_safely_
reformulate` — R19's idiom guard fully protects this phrase today, so
the exact v3 defect cannot be produced anymore, confirmed by the
engine's own refusal rather than inferred. Two Group B candidates also
had no safe candidate and were swapped, per this project's standing
practice of swapping rather than silently dropping.

**Group A result (matched pairs, same declared difficulty, re-rated
fresh):** 2 confirmed genuine fixes — R19/R25's "how's it going" case
(2/2/0/Original→5/5/1/Reformulated) and R27's "push the meeting" case
(the exact complaint, "push and force might mean different," fully
disappeared). 1 confirmed regression — "sleep"→"nap" (was "rest" in
v3), the rater independently naming the exact issue ("nap is different
to sleep, it is short"). 1 case demonstrating a fix working exactly as
designed while exposing a different, still-open problem — "late"→
"after-hours" (R30 correctly stopped the wrong-POS "recently" output,
but the replacement candidate itself is a poor semantic fit for a bus).
3 stable, still-open defects independently reconfirmed — most notably
`md_running_traffic`, where the rater produced the *identical* free-text
complaint ("going behind might mean going back") on a blind, independent
re-rating, a real reliability signal on both the system and the rater.

**Group B result:** 80% preference, mean meaning 4.5/5, naturalness
4.3/5, no pattern connecting its two rejections to any previously-known
issue.

**Decision:** preference is no longer entirely unresolved — genuine
current-state numbers now exist. This does not replace the old 73.3%
(different, deliberately edge-case-weighted sample) — the valid,
disclosed comparison is the matched Group A delta, not a new headline
number. Two of this pass's findings (the "nap" regression, the
"after-hours" candidate-quality gap) were not previously known and
could only have been found by regenerating through live code rather
than reasoning from old data. **No further investigation started**, per
explicit instruction — this closes the evaluation, pending the user's
review.

**Category:** Human evaluation, executed. No production code changed;
no ranking weights touched; no new signal or model introduced. Full
record: `VALIDATION.md` §32; `ROADMAP.md` R39.

### 2026-08-21-A — R40: ceiling probe + direct linguistic audit, on user request

**What was done:** user asked directly whether the engine has hit a
ceiling, after seeing repeated `could_not_safely_reformulate` output, and
asked for large-scale real-sentence testing plus a genuine linguistic
read of the output, not just the pipeline's own scores. New script
`eval/ceiling_probe_r40.py` ran 48 real sentences (fetched live from four
Wikipedia articles spanning technical/scientific/procedural/conversational
register) against 4 profiles (light to heavy density) through today's
live engine — 192 pairs, one live run each. Claude then read all 79
`reformulated` outputs directly, without relying on SBERT/MeaningBERT, per
explicit instruction to apply general linguistic judgment as the check,
not the app's own proxy metrics.

**Quantitative result:** 21/192 (11%) failed both tiers, concentrated in
dense profiles (`heavy_dense` 31%). T5 restructuring — the tier meant to
back up substitution — succeeded in 2/192 runs, both the same sentence.
Substitution is carrying essentially all observed success.

**Qualitative result — the more consequential finding:** direct reading
found real, reproducible defects inside outputs the pipeline itself
labels successful: nonsense fragments ("sulfur"→"s", "greenhouse
gases"→"gas gases"), fluent-but-wrong word sense including a ~50,000-year
factual error ("pre-industrial"→"palaeolithic"), grammar errors
introduced by substitution itself (correct "gases was" → incorrect "gases
were," 4x), and a fixed term eroding under plain substitution ("small
talk"→"little talk," 6x). Spot-checked SBERT (0.877-0.971) and MeaningBERT
(56.8-94.5) scores, and the engine's own `final_verification.passed`,
were all green for these — confirmed, at scale and on real text, the
limitation the UI already discloses in the abstract.

**Connecting finding:** re-running 6 of the worst cases and reading
`contextual_fit` (R37, wired in but reported-only) directly — 5 of 6
scored ≤0.0007 (one at 0.0000000053), matching direct linguistic
judgment exactly. The one miss ("palaeolithic," scoring 0.9994) is a
factual-correctness error, a different problem class contextual_fit
isn't built to catch (it measures fluency, not world knowledge).

**Decision:** findings only, no fix implemented, no config changed —
recorded per explicit instruction, with the user to decide direction
next. The evidence points toward revisiting R37's Option A
(reported-only) decision for contextual_fit now that real production
evidence exists, and toward adding per-candidate rejection-reason
logging to both the substitution ranker and `_try_escalation` before any
threshold or gating change, so the next step is measured rather than
guessed.

**Category:** Diagnostic investigation, on direct user request. No
production code changed; no ranking weights touched; no fix implemented.
Full record: `VALIDATION.md` §33; `ROADMAP.md` R40.

### 2026-08-22-A — R40 completed: systematic audit of all 112 substitutions

**What was done:** the prior R40 entry rated a curated ~15-example
worst-of list. Per explicit follow-up instruction, R40 is completed
here with an unselected audit of all 112 individual substitution
changes behind the 79 `reformulated` sentences — new
`eval/r40_change_audit.py` re-captured full change-level detail
(reproduced the original 79/112 split exactly), `eval/
r40_change_audit_verdicts.py` records a CLEAN/MINOR/SEVERE verdict and
reason for every one, index-matched and reproducible.

**Result:** 8/112 CLEAN (7%), 21/112 MINOR (19%), 83/112 SEVERE (74%) —
a full-sample proportion, not a curated list. Two findings beyond the
tally: (1) a second, independent bug source — `sanitize_input()`'s
spellchecker turns valid "optimises" into the noun "optimists" via
edit-distance correction, on a code path separate from the
reformulation engine entirely; (2) the single worst substitution found,
"slower"→"easier", inverts its own sentence's logic ("insufficient...
because... become exponentially easier") while the engine's own
`antonym_check` recorded "pass" — "slower"/"easier" are not each
other's WordNet antonym, so the check cannot see this class of error.
SBERT similarity shows no separation at the per-substitution level
either (SEVERE median 0.9696, actually higher than MINOR's 0.9682).

**Decision:** findings only, no fix implemented. Full record:
`VALIDATION.md` §33.6.

### 2026-08-22-B — R41: bounded contextual_fit gate validation

**What was done:** per direct instruction — validate contextual_fit as
a candidate substitution-quality gate using the R40 audit's 112 labeled
changes as ground truth, no threshold promoted, no production gate, no
T5 change, no fine-tuning. Compared `contextual_fit` score distributions
across the CLEAN/MINOR/SEVERE buckets and swept reject thresholds.

**Result:** real signal exists (CLEAN median 0.0078 vs. SEVERE median
0.00004, ~200x apart) but the distributions overlap heavily — no single
threshold cleanly separates them. At threshold 0.01 (the level §33.5's
earlier 6-example spot check had suggested), 94% of severe defects
would be caught, but so would **62% of substitutions that were actually
fine**. Even the most permissive threshold tested (0.001) still misses
19% of severe cases while already rejecting 31% of good ones. The
signal is also structurally blind to the corpus's most damaging defect
class: the "palaeolithic"/"pre-industrial" and "half-century" factual-era
errors all score 0.6-0.999 — they read fluently, which is exactly what
contextual_fit measures, so it cannot see that they're factually wrong.

**Decision:** this explicitly revises §33.5's earlier recommendation
rather than quietly superseding it — the small-sample optimism doesn't
survive at scale. contextual_fit remains worth further investigation as
a signal, but is not shown safe to wire in as a standalone binary gate.
Any production use would need either a working retry/fallback path
(which R40 §33.2 already found doesn't currently exist — T5
restructuring succeeds in 2/192 runs) or a second signal for the
factual-correctness class this one can't see. Neither is decided or
implemented here. Per explicit instruction, architecture reassessment
(candidate-generation + verification vs. a learned, speaker-conditioned
generation model) is the next step, not started in this pass.

**Category:** Bounded signal validation, on direct user request. No
production code changed; no ranking weights touched; no threshold
promoted; no fix implemented. Full record: `VALIDATION.md` §34;
`ROADMAP.md` R41.

### 2026-08-23-A — R42/R43/R43-A: architecture reassessment, escalation instrumentation, four bounded fixes tested and stacked

**What was done:** on direct instruction, a full architecture
reassessment reading the actual implementation and prior research
fresh, followed by R43: instrumenting the T5 escalation path on the 23
(sentence, profile) pairs from R40's corpus that actually invoke it.
Then four candidate fixes tested in isolation and stacked (A1-A5). Full
original text consolidated 2026-08-26 into
`ARCHITECTURE_RESEARCH_R42_R43.md` (Parts 1-3).

**Key results:** T5 escalation fails 96% of the time not from poor
generation (76% of candidates clear a strict SBERT floor) but from
constraint-satisfaction failure — 68% of leaks are the blocked word
itself or a morphological variant, correcting R42's own hypothesis that
it was mostly unrelated same-sound words. A1 (expanded inflected-form
blocking) recovered part of that gap; A2 (generate-verify-regenerate)
recovered more but at 6x latency and with real defects still present in
several "accepted" outputs; A3 (NLI) and A4 (LanguageTool) each caught a
narrow, non-overlapping defect class with real but low recall. **A5
(all three filters stacked) produced the decisive number: only 1/23
dense-profile sentences produces any candidate surviving a genuinely
comprehensive check** — verification stacking lowers the accept rate
further (2%→9%→4%), confirming the ceiling is the candidate pool, not
the checks. Also found a third independent spellchecker-corruption
instance ("chatbots"→"chariots").

**Decision:** no production code, threshold, or model changed throughout.
Findings point toward the generation side of the escalation tier as the
actual bottleneck, not verification — directly informing the next step
(R44's human evaluation, then the generation-tier redesign).

**Category:** Architecture investigation + bounded diagnostic
experiments, on direct user request. Full record: the three standalone
architecture documents named above.

### 2026-08-23-B — R44: bounded v5 human evaluation, the pre-redesign baseline

**What was done:** per direct instruction, before starting the
generation-tier redesign, rated the v5 corpus (20 sentences, R40 §33.6
Track C) through `eval/pilot_app.py`, unmodified. n=1, single session,
same disclosed limitation as every prior pilot round.

**Result:** strong aggregate agreement with R40's own CLEAN/MINOR/SEVERE
audit — mean meaning/naturalness/ease and preference rate all degrade
monotonically across the three tiers, no reversals. But the 12 SEVERE
cases split near-evenly by defect *type*: nonsense, wrong-sense, and
register-confusion defects were reliably rejected (7/12); grammar
corruption, fixed-term erosion, a subtle factual error, and the
project's own worst logical-inversion case were tolerated and even
preferred (5/12) — including one case where the participant's free-text
comment correctly named the exact defect ("slower easier are not fine")
while still preferring the reformulated version overall. Overall
preference across the stratified corpus: 70% (14/20).

**Decision:** this is the human-rated baseline the generation-tier
redesign will be measured against. A redesign's priority should weight
the nonsense/wrong-sense/register-confusion classes more heavily than
the grammar/fixed-term/subtle-factual classes, per this round's
disclosed, human-sourced (if n=1) signal — not treat all of R40's SEVERE
cases as equally costly.

**Category:** Human evaluation, executed on direct instruction. No
production code changed; no new signal added; no architecture changed.
Full record: `VALIDATION.md` §35; `ROADMAP.md` R44.

### 2026-08-23-C — R45: two bounded prototypes, and the architecture decision

**What was done:** per direct instruction, two prototypes against
existing corpora only. Prototype 1: combined NLI + LanguageTool
validator run on all 79 R40 substitution-tier pairs (previously only
NLI had covered all 79; grammar had only covered 11). Prototype 2: a
custom `LogitsProcessor` intervening during T5 generation itself —
killing any beam the moment a word's onset (even mid-formation) matches
a blocked sound — tested on the same 23 escalation cases as R43/A1/A2/A5.

**Prototype 1 result:** combining beats either check alone — 32% recall
on SEVERE (21/65) vs. ~20% for NLI or grammar individually, confirming
the two checks are genuinely non-overlapping. Real but partial: 68% of
SEVERE cases still pass both checks undetected.

**Prototype 2 result — the largest improvement measured in this entire
arc:** leak-free rate 4%→100%; cases producing any usable candidate
9%→52% (vs. 13% for A1 and 4% for A5's fully-stacked verification). A
direct manual read of a 12-case sample (not trusting the gate-pass count
alone) found roughly half still carry a real defect — but every one is
a meaning/logic/grammar defect, not a constraint leak, including a
second independent instance of the exact logical-inversion class R40
found worst ("exponentially slower"→"exponentially faster", passing
every existing gate). Also found and disclosed a narrow tooling gap (a
blocked word absorbed into a larger hyphenated compound escaped the
leak-check, confirmed to 4 occurrences from one sentence) and a genuine
cost when the flagged word is itself the sentence's subject (the model
drops it rather than replacing it).

**Decision, per the branching logic given directly:** both prototypes
show material, independent improvement, targeting different problems —
Prototype 2 fixes constraint satisfaction, Prototype 1 catches what
survives it. **Combine them**: substitution stays primary and unchanged;
the escalation tier's generation is rebuilt around phoneme-aware
decoding; the combined validator applies to both tiers' final output,
not just escalation's. **Fine-tuning is explicitly not justified** —
the precondition for it (appropriate constraint handling and validation
failing to reach required quality) is the opposite of what was just
measured.

**Category:** Bounded prototypes + architecture decision, on direct
instruction. No production code, threshold, or model changed. Full
record: `VALIDATION.md` §36; `ROADMAP.md` R45.

### 2026-08-23-D — R46: R45's decision built as real, tested, additive code

**What was done:** per direct instruction to proceed without delay, R45's
combined architecture (phoneme-aware escalation + NLI/grammar validator)
built as production-quality code, not another diagnostic script — three
new functions only, nothing existing modified:
`rephrase.generate_candidates_phoneme_constrained()`,
`semantic.logical_consistency_check()`/`grammar_issue_count()`, and
`reformulate.reformulate_v2()`/`_try_escalation_v2()` as a separate,
parallel entry point.

**Verification:** the full existing test suite (`reformulate_test.py`
31 tests, `rephrase_test.py`, `semantic_test.py`, `contextual_fit_test.py`,
`app_test.py`) passes unchanged; `smoke.py`'s output is byte-identical to
the committed baseline — `reformulate()` is confirmed unaffected. New
`tests/reformulate_v2_test.py` (17 tests, real models) passes. The real
`reformulate_v2()`, re-run against the same 23 escalation cases R45
used, reproduces the diagnostic prototype's number exactly (12/23, 52%)
— no drift between prototype and production-quality implementation. The
new validator, running for real for the first time, caught the exact
"slower→faster" logical inversion found by manual review in R45, plus
independently flagged the "starch"→"glucose" restructuring case R40
had raised only as a manual concern.

**Decision:** this is tested, verified, additive code — not a shipped
feature. `reformulate_v2()` is not called anywhere in `app.py`; wiring
it in, and whether `validation` stays reported-only or becomes a real
gate, remains a separate, explicit decision, not made here.

**Category:** Implementation of a prior architecture decision, on direct
instruction. No existing production code path changed. Full record:
`VALIDATION.md` §37; `ROADMAP.md` R46.

### 2026-08-24-A — R46 wired into app.py behind an opt-in toggle

**What was done:** per direct instruction, a sidebar checkbox ("🧪 Try
next-gen escalation (experimental)"), defaulting to unchecked, routes
the Reformulate button to `reformulate_v2()` instead of `reformulate()`
when checked. Off (default) is byte-identical to before — confirmed by
the full `app_test.py` suite passing unchanged. On, the Output tab
shows a diagnostic banner if the new validator flags something (never
blocking the result) and the Verification tab shows the raw NLI/grammar
detail.

**Verification:** a new one-time headless AppTest check
(`eval/r46_toggle_smoke.py`) confirmed the toggle actually reaches
`reformulate_v2()` and both new UI elements render without exception;
the app was also launched live and confirmed responding.

**Decision:** this makes R46's architecture reachable by an actual user
for the first time, strictly opt-in. Whether to flip the default or
promote the validator into a real gate remains undecided.

**Category:** UI change, on direct instruction. Full record:
`VALIDATION.md` §37.3.

### 2026-08-24-B — R47/R48: architecture pushed to its evidenced ceiling before the final decision

**What was done:** per direct instruction, exhaust the remaining well-
evidenced engineering moves and integrate them before deciding whether
the current architecture is enough. R47: 10 fresh, non-Wikipedia
sentences run through both pipelines directly. R48: one substitution-
tier fix hypothesis tested and correctly abandoned; one escalation-tier
fix (combine the phoneme constraint with A2's iterative regeneration)
built, found to have a real over-blocking bug, fixed, then found to
have shipped a dangerous antonym-flip case, fixed by making the NLI
check a real per-candidate gate inside escalation specifically.

**Key results:** R47 surfaced a third, independent, unprompted instance
of the `sanitize_input()` subject-verb-agreement bug (`was`→`were`),
present even in a fully-refused (zero-change) output. R48's substitution
hypothesis (genericness + contextual_fit) failed against R31's own
known-good guard cases (seize/clutch score lower than the bad case it
was meant to catch) — correctly not implemented. R48's escalation fix,
after both bugs were caught and fixed: final gated result 12/23 (52%,
matching phoneme-constraint-alone), but a materially safer and better
set — the "rational"→"irrational" antonym flip correctly refused, the
"starch"→"glucose" scientifically-backwards case replaced by the
correct "starch"→"cornstarch". Direct manual read of all 12 final
successes: 5 CLEAN, 4 MINOR, 3 SEVERE (25%) — down sharply from R40's
original 74% severe rate, not zero.

**Decision:** this is the honest ceiling of the low-risk moves available
within the current architecture, tested to completion. Full existing
suite passes throughout; `reformulate()` confirmed unaffected at every
step. Whether this is "enough" is handed to the user, not decided here.

**Category:** Architecture completion + comprehensive re-test, on direct
instruction. Full record: `VALIDATION.md` §38.

### 2026-08-24-C — R49: the two remaining cheap levers, both tried, both hit a real wall

**What was done:** per direct instruction, the two remaining no-
training-data moves named after R48 — wider candidate sampling for
escalation, and a prompted (not fine-tuned) local LLM as a validator
for the two defect classes nothing in the pipeline catches.

**Wider sampling:** tested 24 candidates via wider beam search (vs. the
production cap of 12) and 24 via genuinely different sampling-based
decoding, on all 11 still-refusing cases. Found and fixed a real bug
first — `PhonemeConstraintLogitsProcessor` used literal `-inf`, which
crashes `torch.multinomial` under sampling (safe for beam search, not
softmax); fixed to a large finite kill-score, re-verified the
production beam-search path unaffected. Result: **0/11 rescued** at
~4× the search budget — the 52% escalation ceiling is now directly
confirmed, not just repeated across strategies.

**LLM judge:** reused the exact Qwen2.5-0.5B/1.5B-Instruct models R14/
R23 already proved load locally, as a judge rather than a generator.
0.5B: 4/8, a rubber stamp (said "preserved" to the direct antonym flip
and the ~50,000-year factual error alike). 1.5B verdict-first: 5/8 —
better but internally inconsistent (correct written reasoning on the
palaeolithic case, wrong final verdict, because the verdict was
requested before the reasoning). 1.5B reasoning-first: 3/8, worse —
caught all 3 bad cases but flagged 4/5 good ones on trivial phrasing,
trading one failure mode for another, plus one unparseable verdict.

**Decision:** both levers were tried in good faith, with real
engineering, and both show a direct, tested wall rather than an
inferred one. Per the standard agreed before this pass: this is the
point where a custom, learned component becomes the evidenced next step
for these two specific gaps — not a claim the whole architecture is
obsolete, since the substitution tier, safety gates, and R48's quality
gains all stand independent of this finding.

**Category:** Bounded follow-up experiments, on direct instruction. One
disclosed correctness fix to already-shipped, opt-in-only code (the
`-inf`/NaN bug); no new production capability, no threshold, no model
change. Full record: `VALIDATION.md` §39.

### 2026-08-24-D — R50 Phase 2/3/7/9: dataset construction, defect-typed labeling, and baseline report

**What was done:** per direct instruction, following the user's own R50
proposal — before any custom-validator prototyping, join and dedupe the
labeled evidence across R40/R44/R47/R48/R49/v5 into one provenance-
tracked dataset, add a structured defect taxonomy (CLEAN /
WRONG_WORD_OR_SENSE / FACTUAL_OR_LOGICAL_REVERSAL / GRAMMAR /
FIXED_TERM_OR_IDIOM / NATURALNESS_OR_REGISTER / OTHER_DEFECT / UNCERTAIN)
alongside the existing CLEAN/MINOR/SEVERE severity, benchmark existing
signals against it, and produce a frozen leakage-safe test split.
**Research/dataset-construction only — no model trained, no production
code touched.**

**Repair:** R48's 12 escalation successes only had 3/12 documented at
per-case granularity in `VALIDATION.md` §38.3 (an aggregate "5 CLEAN, 4
MINOR, 3 SEVERE" tally, not attached to specific sentences). Rather than
infer, the 3 documented cases kept their documented verdict; the other 9
got a fresh, distinctly-tagged read of the actual stored text.

**Result:** 135 labeled records, 88 unique underlying cases after
deduplication. Class sizes at the unique-case level are much thinner than
raw counts suggest — WRONG_WORD_OR_SENSE 33, down to
**FACTUAL_OR_LOGICAL_REVERSAL 7** and FIXED_TERM_OR_IDIOM 8, the two
classes this work exists to address. Two new findings sharper than
anything in R40–R49: fixed-term-idiom erosion is caught by NLI+grammar
0/5 (0%), a third complete blind spot; and contextual_fit scores
factual/logical reversals ~40× *higher* than CLEAN substitutions at the
median (0.305 vs 0.0078) — actively counter-indicative for this class by
construction, not just weak.

**Decision:** sufficiency assessment is (C) leaning (B) — enough for
baseline comparison and a directional WRONG_WORD_OR_SENSE experiment, not
enough to train or trustworthily evaluate a validator for
FACTUAL_OR_LOGICAL_REVERSAL or FIXED_TERM_OR_IDIOM. A dedicated labeling
pass (~40-60 more unique examples per thin class) is needed before Phase
4 (validator prototyping) can proceed on the two classes that motivated
R49's "build something custom" conclusion.

**Category:** Dataset construction and analysis, on direct instruction.
No model trained, no threshold changed, no production code touched. Full
record: `VALIDATION.md` §40, `eval/r50_dataset_report.md`.

### 2026-08-24-E — R50 Phase 8: building the missing human-labeled dataset

**What was done:** per direct instruction, following the user's Phase 8
proposal — collect deliberate new evidence for the two data-scarce
classes R50 identified, rather than re-mining R40-R50. **Data collection
only.** 54 new real sentences (5 Wikipedia topics never used before) run
through today's live `reformulate()` across R40's 4 profiles (R40's own
methodology, new material) — 68 unique cases, blind-labeled. Supplemented
with 50 disclosed-non-blind constructed examples (20
FACTUAL_OR_LOGICAL_REVERSAL, 20 FIXED_TERM_OR_IDIOM, 10 hard-CLEAN
controls). A second, independent subagent rater checked a 33-case
stratified sample blind to the primary rater's labels.

**Result:** 116 new independent records (2 excluded as R50-duplicate
lexical phenomena). Combined unique-case counts:
FACTUAL_OR_LOGICAL_REVERSAL 7->28 (21 new, 95% constructed - organic
yield was 1/68), FIXED_TERM_OR_IDIOM 8->41 (33 new, 13 organic/20
constructed - well above R50's ~8% base-rate estimate, these topics are
dense with fixed technical terminology). Second-rater agreement:
acceptability 88%, severity 64%, primary defect type 70% overall; 100%
on FACTUAL_OR_LOGICAL_REVERSAL and OTHER_DEFECT, but only 25% on GRAMMAR
and 33% on NATURALNESS_OR_REGISTER - a real taxonomy-boundary problem,
plus a separate labeling-convention confound (per-word-isolation vs.
whole-sentence judgment) identified as a distinct source of
disagreement.

**Decision:** sufficiency is (B), not (A) or (C) - a learnable signal
clearly exists, but FACTUAL_OR_LOGICAL_REVERSAL needs more organic (not
constructed) examples, the GRAMMAR/WRONG_WORD_OR_SENSE/NATURALNESS_OR_
REGISTER boundary needs refinement or a coarser evaluation axis, and the
labeling-convention needs reconciling before training. No training
proceeds from this phase.

**Category:** Data collection, on direct instruction. No model trained,
no threshold changed, no production code touched. Full record:
`VALIDATION.md` §41, `eval/r50p8_report.md`.

### 2026-08-24-F — R50 Phase 8B: targeted finalization, final GO/NO-GO decision

**What was done:** per direct instruction, resolve Phase 8's three named
blockers and decide, rather than run another broad collection cycle.
(1) Targeted organic harvest: 42 new sentences from 4 causal-dense topics
(Vaccine, Plate Tectonics, Antimicrobial Resistance, Supply and Demand);
organic FACTUAL_OR_LOGICAL_REVERSAL yield rose 1/68->9/58 records (~6x).
(2) Taxonomy reconciliation: a strict 3-step decision procedure, tested
by an independent rater, raised GRAMMAR agreement 25%->56% and WRONG_
WORD_OR_SENSE 67%->78%, but NATURALNESS_OR_REGISTER stayed at 33%
unchanged. (3) Labeling convention resolved (judge the complete
delivered sentence, not an isolated word) and applied retroactively - 12
R50 + 6 Phase 8 records corrected, original rationale preserved
alongside. (4)/(5) Evidence-quality tagging (ORGANIC_OBSERVED/
CONSTRUCTED/HUMAN_REVIEW_OF_EXISTING_CASE) and full recount.

**Result:** FIXED_TERM_OR_IDIOM 53 unique (62% non-constructed, past
target). FACTUAL_OR_LOGICAL_REVERSAL 33 unique (organic count 1->6,
still 61% constructed, short of the 40-60 target). NATURALNESS_OR_
REGISTER retired as a primary label (kept as secondary only) since two
independent tests found it unreliable regardless of definitional
clarity - a data-driven partial coarsening, not a blanket merge.

**Decision: GO, scoped per class.** WRONG_WORD_OR_SENSE,
FIXED_TERM_OR_IDIOM, GRAMMAR, and CLEAN/acceptability are sufficient to
proceed to a validator prototype. FACTUAL_OR_LOGICAL_REVERSAL proceeds
too, but any reported performance on it must be labeled directional/
low-confidence and evaluated separately, given its evidence is still
majority-constructed. This is a decision, not a deferral - no further
data-collection phase follows automatically.

**Category:** Data/analysis phase, on direct instruction. No model
trained, no threshold changed, no production code touched. Full record:
`VALIDATION.md` §42, `eval/r50p8b_report.md`.

### 2026-08-25-A — Phase 9: learned validator prototype, training run diverged

**What was done:** per direct instruction, following the Phase 9
proposal - assemble the final labeled dataset, build a unified
leakage-safe split (respecting R50's and Phase 8's frozen test
assignments), compute existing-signal baselines fresh, fine-tune a small
cross-encoder (microsoft/deberta-v3-xsmall, binary ACCEPT/REJECT,
pos_weight~11 for the 17:188 CLEAN:DEFECTIVE train imbalance), and
evaluate on the frozen test set with unseen-word-pair and
evidence-quality-stratified breakdowns.

**Result:** dataset/split/baselines completed correctly - the best
simple combined rule (SBERT<0.95 OR NLI OR grammar) gets 60% DEFECTIVE
recall / 90% precision / 63% CLEAN recall, the real floor to beat. The
fine-tuning run diverged: grad_norm went nan at epoch 3.08 (after a
warning-sign spike to 24.5 at epoch 2.69) and stayed nan for the
remaining 5 epochs. Direct inspection confirmed 100% of the saved
model's 70.8M parameters are NaN. The evaluation script's output
numerically matched the reject-everything baseline, but only because
Python's `nan >= threshold` always evaluates False - not a real result.
None of Phase 9's three gate questions (generalize? beat baseline?
precision/coverage tradeoff?) were answered.

**Decision:** reported exactly as it happened, per instruction not to
alter or re-run the experiment. Root-cause hypothesis (pos_weight
~11x + lr=2e-5 on n=205 -> gradient explosion) documented with a
recommended fix for a future attempt, but no retraining performed
automatically - that decision is left to the user. The broken checkpoint
is not committed (already gitignored, and not worth preserving given
it's confirmed non-functional); the training log fully documents the
divergence.

**Category:** Prototype/research, on direct instruction. No production
code touched, no model integrated. Full record: `VALIDATION.md` §43,
`eval/r9_report.md`.

### 2026-08-25-B — Phase 9B: training instability fixed, controlled retry succeeded

**What was done:** per direct instruction - diagnose R9's NaN failure
precisely, retrain with a conservative config, sanity-check before the
full run, evaluate against the unchanged baseline/dataset/split.

**Diagnosis correction:** R9's report guessed missing gradient clipping
as the cause. Checked against actual library defaults -
max_grad_norm=1.0 and fp32 were already active throughout the failed
run; that guess was wrong and is corrected here rather than left
standing. Revised hypothesis: pos_weight~11 + lr=2e-5 +
adam_epsilon=1e-8 (smaller than DeBERTa's commonly-recommended 1e-6)
destabilized the model within ~3 epochs despite clipping.

**Conservative config:** lr=3e-6, pos_weight=4.0 (capped),
max_grad_norm=1.0 (explicit), adam_epsilon=1e-6, early stopping on
eval_loss, plus a new abort-on-non-finite safety callback. Same
dataset/split as R9, unchanged. 10-step sanity pass passed; full
8-epoch run completed with zero non-finite events (confirmed: 0 NaN/0
Inf across 70.8M parameters). Best eval_loss 0.676 at epoch 6.

**Two evaluation bugs caught and fixed before reporting:** (1) an
initial coarse threshold grid missed the model's narrow real output
range (0.528-0.625), producing a false "no signal" read - a fine sweep
found real separation. (2) an initial "best threshold" was read
directly off test-set performance (leakage) - fixed to select on val
only, applied to test exactly once.

**Result:** on the frozen, unchanged test set (100% out-of-distribution
word-pairs), the val-selected threshold gets defect recall 0.77 vs
baseline's 0.60, defect precision 0.92 vs 0.90, clean recall 0.62 vs
0.62 (tied). A second, more conservative threshold beats baseline on
all three simultaneously (0.65/0.93/0.75). Real, not favorable
after-the-fact threshold-picking.

**Decision:** justifies further development, directionally, on real
evidence - not a production-ready result. Test set is small (51
records, 8 CLEAN), confidence is poorly calibrated despite real ranking
signal, single run/seed not repeated for variance. A second independent
training run is the sensible next step, not performed here.

**Category:** Prototype/research, on direct instruction. No production
code touched, no model integrated. Full record: `VALIDATION.md` §44,
`eval/r9b_report.md`.

### 2026-08-25-C — Phase 9C: independent replication (seed change only)

**What was done:** exact re-run of 9B's pipeline with only the random
seed changed (42->123) - same dataset, split, architecture,
hyperparameters, threshold-selection procedure, evaluation metrics.
Paused mid-run at user's request (checkpoint saved after epoch 1) and
resumed cleanly later via resume_from_checkpoint.

**Result:** full run completed stably (0 NaN/0 Inf, confirmed by
inspection). Conservative threshold result nearly identical across
seeds - defect recall 0.65 in BOTH 9B and 9C, both beating baseline on
all three metrics. But the "aggressive" threshold-selection procedure
(max recall among val-thresholds beating baseline on val) is NOT
robust: it gave a healthy result in 9B (0.77/0.92/0.62) but in 9C
produced clean_recall=0.38, BELOW baseline's 0.62 - a real regression
traced to the validation set's tiny CLEAN sample (6 examples) making
that selection criterion noisy. Ranking stability measured directly:
Spearman rho=0.901, Pearson r=0.916 (n=51, p<0.0001) between the two
models' scores on the same test set - the underlying learned judgment
is highly consistent even though calibration differs.

**Decision:** Phase 9B's core finding replicates at the conservative
threshold (~65% recall, reproducible). The 77-91% recall numbers from
aggressive threshold selection are NOT reliable and should not be
quoted as representative - a small-CLEAN-sample threshold-selection
fragility, not model instability (rankings stay correlated). Still
justifies further development, with somewhat more confidence than 9B
alone (two seeds, correlated rankings), but the honest headline is ~65%
recall.

**Category:** Prototype/research, on direct instruction. No production
code touched, no model integrated. Full record: `VALIDATION.md` §45.

### 2026-08-26-A — Phase 10: broad stratified stress test of the current architecture

**What was done:** per the approved plan (EnterPlanMode/ExitPlanMode
cycle), a deliberately wide, stratified, difficulty-graded evaluation:
133 new sentences (11 technical + 11 general domains), 0 contamination
with any prior corpus, 398 (sentence,profile) runs frozen before
execution, harvested via today's live reformulate() (238 reformulated/
98 no-change/62 refused), blind-judged by 5 parallel subagents (no
domain/category/difficulty shown), plus the frozen Phase 9B/9C
validator checkpoints run unmodified on the same new material.

**Result:** 26% CLEAN / 74% DEFECTIVE overall (harder corpus than any
prior phase by design). Domain (general vs technical) only a 6-point
gap - content density (terminology, length) predicts failure far
better than subject-matter label; chemistry/engineering/narrative all
0% CLEAN while math/stats hit 83% CLEAN. Difficulty gradient not
smooth - moderate (18% CLEAN) scored worse than hard (30%). Profile
constraint density is the cleanest predictor in the dataset:
multi_word profiles 0% CLEAN (0/13). Escalation ties substitution on
quality (26% vs 27% CLEAN), not a safety net. Most consequential:
neither validator checkpoint generalizes cleanly - 9C predicts
DEFECTIVE 99% of the time (non-functional, the same instability its
own report flagged), 9B's CLEAN retention collapsed 62%->34% on new
material despite higher recall.

**Decision:** confirms the architecture's real, specific failure
predictors (density/length/profile-constraint-count, not domain
label), and directly answers Phase 9B/9C's open generalization
question - partially yes for 9B, no for 9C. Evaluation only, no
production changes, no training.

**Category:** Evaluation, on direct instruction and approved plan. No
production code touched, no model trained. Full record:
`VALIDATION.md` §46, `eval/r10_report.md`.

### 2026-08-26-B — Documentation hygiene: consolidated the orphaned R42/R43/R43-A architecture documents

**What was done:** per direct instruction ("declutter documentation...
there are a few new ones you made, make sure they're organized in a
singular place... or remove if not needed"). Three standalone documents
(`ARCHITECTURE_REASSESSMENT_R42.md`, `ARCHITECTURE_TRANSITION_R43.md`,
`ARCHITECTURE_TRANSITION_R43A_RESULTS.md`) existed in the repo root
since 2026-08-22/23 but were never added to `CLAUDE.md`'s reading order
or `DOCS.md`'s file table - genuinely orphaned, exactly the confusion
raised. Consolidated all three, in full and in original chronological
order, into one archival file: `ARCHITECTURE_RESEARCH_R42_R43.md`.
Updated every cross-reference in `VALIDATION.md`, `DECISION_LOG.md`
(the 2026-08-23-A entry above), and `ROADMAP.md` to point at the new
file instead of the three old filenames. Added a `DOCS.md` row for the
new file, explicit that it is archival/frozen and not part of the
standard reading chain - every recommendation in it was already carried
out and is documented with results starting at `VALIDATION.md` §35.
Removed the three original files (recoverable from git history).

**Why now:** these three documents' entire purpose was to justify a
decision (R45's "two bounded prototypes") that has since been fully
implemented, tested, and independently replicated (R46 through Phase
10) - their standalone existence outside the documented chain had
become pure clutter, not a live reference.

**Category:** Documentation hygiene, on direct instruction. No code,
data, or evaluation content touched - text-only reorganization.

### 2026-08-26-C — Phase 10B: detailed failure analysis, architecture-vs-custom-model evidence

**What was done:** per direct instruction - "a detailed R10 failure
analysis... identify exactly what kind of generation capability is
missing and separate: fixable within current architecture -> needs a
new generation mechanism -> potentially requires a custom trained
model... rather than jumping straight into training something huge."
All 176 Phase 10 DEFECTIVE outputs re-examined with full mechanism
context (not blind this time, since diagnosing mechanism is a
different task from judging acceptability) by 4 independent subagents,
each given the same three-bucket definitions and told not to default
to the safe middle category.

**Result:** 162/176 (92%) fixable within current architecture, 12/176
(7%) needs a new but still non-learned/engineerable mechanism, 2/176
(1%) potentially requires a custom trained model. GRAMMAR and
FIXED_TERM_OR_IDIOM defects are 100% rule-fixable. FACTUAL_OR_LOGICAL_
REVERSAL - the class treated as most dangerous throughout this project
- is 85% rule-fixable. The needs-new-mechanism bucket clusters into
exactly three patterns (joint cross-substitution coherence checking, a
pre-ranking WSD gate, a restructuring content-coverage check), none
requiring a trained model. Both custom-model cases are escalation-tier
(T5) chemistry-domain state/causal reasoning failures specifically, not
general fluency problems.

**Decision:** decisive evidence against jumping to a custom trained
model. Staged path supported: (1) rule/blocklist/check additions for
the 92%, each grounded in a named instance; (2) three specific new
engineered mechanisms for the 7%; (3) only then, reconsider a
custom-trained component for the narrow surviving 1% (escalation-tier
technical-domain causal claims specifically). No fixes implemented in
this phase - analysis only, decision left to the user.

**Category:** Evaluation/analysis, on direct instruction. No production
code touched, no fixes implemented, no training. Full record:
`VALIDATION.md` §47, `eval/r10b_failure_analysis.md`.

### 2026-08-27-A — Phase 11: implemented categories 1-3 of the "92% fixable" batch

**What was done:** planned via plan mode, then implemented, the
highest-value/lowest-risk slice of Phase 10B's fixable batch: (1)
expanded `semantic.py`'s `IDIOM_PHRASES` fixed-term list and extended
enforcement to escalation-tier (T5 restructuring) output via a new
`dropped_protected_phrases()` gate in `_try_escalation()` - the actual
`reformulate()` v1 function, not the experimental v2/v3 path the first
plan draft mistakenly named; (2) a duplicate-word-in-sentence rejection
check (`_duplicates_sentence_word()`) wired into `_try_substitution()`;
(3) a specific bad-pair blocklist (`BLOCKED_SUBSTITUTION_PAIRS`/
`blocked_pair()`) of 52 verified `(original, replacement)` pairs.

**User feedback that shaped this (verbatim, load-bearing):** the first
plan draft was rejected with: *"verify every proposed protected entry
against its actual failure instances and make protection
context-sensitive where necessary, rather than blindly dumping all ~30
into PROTECTED_PHRASES."* Every phrase and every blocklist pair was
re-verified against its named Phase 10 `run_id`'s actual
original/reformulated text before being added; several originally-
proposed entries were rejected or moved to a different category on this
pass (momentum, straight line, held together by, of hydrogen into
helium, and others - see `VALIDATION.md` §48 for the full list).

**Result:** all existing tests pass (`reformulate_test.py` 40/40 with
10 new tests, plus `semantic_test.py`/`rephrase_test.py`/
`contextual_fit_test.py`/`app_test.py`), `tests/smoke.py` byte-identical
to both committed baselines. `eval/r11_targeted_rerun.py` re-ran the 83
specific R10 `run_id`s these categories target through live production
`reformulate()`: 77/83 (93%) no longer reproduce their original
defective output. The same verification process caught two real bugs
before they shipped: 4 blocklist pairs stored in the wrong grammatical
form (the actual POS tag in context differed from the intuitive guess),
and `blocked_pair()` needed to normalize the candidate side because
Datamuse-sourced candidates aren't guaranteed to already be a WordNet
lemma (R10-129's "studies" vs the stored "study"). Both were found by
re-running the targeted evidence, not assumed fixed after writing the
code - direct vindication of the plan-rejection feedback's verification
discipline.

**Known, named gap (not scope creep):** 6 of the 83 targeted cases
remain unfixed - `R10-024`/`R10-025`/`R10-061` (x2) are duplicate-word
defects introduced by escalation-tier restructuring, which the approved
plan scoped the duplicate check to substitution-tier only; `R10-043`
(x2) is a number-agreement grammar defect, Category 4, correctly
deferred. Recorded as future work, not silently dropped.

**Category:** Implementation, on direct plan-mode approval following
Phase 10B's analysis. Production code touched: `semantic.py`,
`reformulate.py`. Full record: `VALIDATION.md` §48,
`eval/r11_targeted_rerun.py`.

### 2026-08-27-B — Phase 11 re-verification: blind re-judging, a regression found and fixed

**What was done:** per direct instruction to close §48's own disclosed
limitation (no blind re-judging had been performed on Phase 11's
fixes), re-ran the FULL frozen Phase 10 corpus (398 runs, not just the
83 originally targeted) through production `reformulate()`, diffed
against the frozen Phase 10 results, and blind-judged every changed run
via 4 independent parallel subagents, same no-metadata discipline as
Phase 10.

**Self-caught regression, fixed before this entry was written:** the
first re-harvest found 3 CLEAN->DEFECTIVE regressions. Root cause:
`IDIOM_PHRASES` is consumed by three free-text-generating paths, not
the two Phase 11 covered - `_try_phrase_replacement()` (the phrase
tier) had no post-generation preservation check, and for phrases whose
internal word IS the user's declared difficulty ("golden brown", "with
distinction", "money supply"), that function's own `blocked_words` set
makes it structurally incapable of ever preserving the phrase - every
one of these was silently shipping a broken phrase. Separately,
"small intestine"/"large intestine" were found to have never actually
been verified against a real failure (misattributed to unrelated
defects) - exactly the failure mode the original plan-rejection
feedback warned against, which slipped through on 2 of 15 entries
despite the discipline being applied. Fixed: removed the two
unevidenced entries, added the same preservation gate to
`_try_phrase_replacement()` (correctly converts these cases into an
honest refusal rather than a shipped defect). Full test suite +
smoke.py re-verified clean; the 398-run harvest and diff were re-run
completely from the corrected code before any numbers below were
finalized.

**Result:** 92/398 runs changed. Of 83 still `reformulated`: 15 CLEAN,
68 DEFECTIVE (52 SEVERE, 16 MINOR). Against Phase 10's original
judgment: 15 DEFECTIVE->CLEAN (genuine fixes), 65 DEFECTIVE->DEFECTIVE,
2 CLEAN->DEFECTIVE (a pre-existing, Phase-11-unrelated Category-4
POS-agreement gap surfaced by known Datamuse nondeterminism), 1
N/A->DEFECTIVE (same nondeterminism). 9 changed runs now safely refuse
instead of reformulating (8 of 9 were previously DEFECTIVE, 7 SEVERE) -
a real improvement even without a CLEAN verdict. **Overall CLEAN rate
among all currently-`reformulated` runs: 75/230 (32.6%), up from Phase
10's 62/238 (26.1%)** - the actual, blind-judged answer to "did Phase
11 help."

**Category:** Verification/regression-fix, on direct instruction
following Phase 11. Production code touched: `semantic.py`,
`reformulate.py` (both already-modified-in-Phase-11 files, corrected
further). Full record: `VALIDATION.md` §49,
`eval/r11_reverify_report.md`.

### 2026-08-27-C — Phase 11B: categories 4/6/7, three real bugs caught during verification

**What was done:** planned via plan mode (approved), then implemented
the highest-confidence slice of Phase 10B's remaining categories 4-7:
(A) `grammar.has_unknown_tokens()` -- dictionary/real-word validation on
escalation-tier, phrase-tier, AND (after a mid-phase finding)
substitution-tier output; (B) `semantic.is_number_word_mismatch()` -- a
generalizable number-word preservation check; (C) five more
individually-verified `BLOCKED_SUBSTITUTION_PAIRS` entries. General
POS/subject-verb-agreement checking on T5 output and antonym/polarity-
without-negation-marker detection were explicitly deferred (need a new
mechanism, not a rule fix), per the approved plan.

**Three real bugs found and fixed during this phase's own
verification, not shipped and disclosed after the fact:** (1)
`has_unknown_tokens()`'s first version rejected legitimate technical
vocabulary this project's own corpus uses ("nucleosynthesis",
"overnutrition"), regressing two previously-CLEAN Phase 10 outputs to a
refusal -- fixed by requiring BOTH pyspellchecker AND exact WordNet-
word-list membership to fail (plain `wn.synsets()` was separately found
too permissive, via morphy inflection-stripping false positives); (2)
the number-word check's spelled-out-word-only set missed digit forms
("2nd") and hyphenated compounds ("twenty-third"), both found via this
same word's actual candidate pool; (3) a previously-unknown root-cause
bug in `grammar.inflect()`'s NNS fallback double-pluralizing an
already-plural candidate lemma ("weekdays" -> "dayss"), fixed at the
source, which also meant `has_unknown_tokens()` needed wiring into
`_try_substitution()` too, not just escalation/phrase-tier as originally
scoped.

**A genuine limit found, not chased further:** two words ("third",
"single") each produced a new distinct bad candidate every time the
previous one was blocked -- the blocklist mechanism's known convergence
limit made concrete. Recorded as an evidenced limitation needing real
WSD, not continued one-off patching.

**Result:** full 398-run harvest re-run three times (once per bug fix)
before trusting any number. Final diff: 111 runs changed. 97 still-
reformulated runs blind-judged: 17 CLEAN, 80 DEFECTIVE. Against Phase
10's original judgment: 17 genuine fixes, 72 still-defective, 8
apparent regressions -- every one traced to this project's already-
documented candidate-pool/T5 nondeterminism, confirmed by checking none
touch any word or mechanism this phase's code changed. Overall CLEAN
rate: 71/225 (31.6%), up from Phase 10's 26.1%, flat against Phase 11's
32.6% (within the noise band the next finding establishes).

**New methodological finding:** re-running the identical 398-run
harvest with NO code change between runs can itself change a small
number of individual outcomes (confirmed directly, e.g. `R10-030`) --
comparing raw CLEAN-rate percentages between two separate harvest runs
carries genuine noise of at least ~1 point; single-run deltas below
that need the underlying cases checked directly, not treated as a
verdict alone.

**Category:** Implementation + self-caught verification bugs, on direct
plan-mode approval. Production code touched: `grammar.py`,
`semantic.py`, `reformulate.py`. Full record: `VALIDATION.md` §50,
`eval/r11b_reverify_report.md`.

### 2026-08-27-D — Phase 11C: research pass, then porting the R45/R46 validator + two new mechanisms

**What was done:** per explicit instruction, a research/design-only
plan-mode pass first (no code changes, no evaluation run) re-examining
the remaining Phase 10B/11B evidence and the actual codebase for
Categories 4/5/6/7's deferred defects. Its central finding: two of the
four needed mechanisms already existed, built and validated by R45/R46
but never promoted from the experimental `_try_escalation_v3()`/
`reformulate_v2()` path (opt-in `app.py` toggle only) into production.
The approved plan was to port those two (NLI entailment gate, grammar
gate) and build two new ones (escalation-tier duplicate-word check,
countability/mass-noun set), each individually verified against its own
cited evidence before wiring in, MIN_SEMANTIC left untouched (no
entanglement found).

**Implementation, in the plan's stated order:** NLI gate ported into
`_try_escalation()`/`_try_phrase_replacement()`, plus added once to
`_try_substitution()`'s final assembled output per R45's own
recommendation. New `reformulate.introduces_new_duplicate()` (stem/
prefix-key counting against an original-sentence baseline, not a
blanket no-repeats rule) wired into escalation/phrase-tier. Grammar gate
(`semantic.grammar_issue_count()`, LanguageTool) ported into the same
two functions, after confirming (Step 0 of the plan) it actually loads
in this environment. New `semantic.is_mass_noun_substitution()` (a
small curated set) wired into substitution.

**Two real bugs caught during this phase's own verification, fixed
before any number was reported:** the duplicate-word check's first
version flagged any brand-new candidate word as a "duplicate" (would
have rejected nearly every legitimate paraphrase) - caught immediately
by the existing test suite; a pre-existing WSD test failed once the new
substitution-tier NLI gate was added, which turned out to be the gate
correctly catching a real defect the test had never actually verified
the quality of - the test was rewritten to check the disambiguation
mechanism directly rather than end-to-end output.

**A measured, not assumed, tradeoff:** the substitution-tier NLI check
has a real precision cost (7/102 previously-CLEAN cases now refuse,
e.g. a fine "remove"->"take" swap flagged as a contradiction) - the
exact risk the approved plan named before implementation. Directly
confirmed the same mechanism also delivers a true positive (R10-005's
"reabsorbed"->"eliminated" reversal correctly rejected while
->"absorbed" passes) rather than assuming the tradeoff nets positive.

**Result:** full 398-run harvest, 147 changed, 102 blind-judged: 21
CLEAN, 81 DEFECTIVE. Against Phase 10's original judgment: 21 genuine
fixes, 70 still-defective, 10 regressions - every one individually
checked and traced to pre-existing candidate-pool nondeterminism, none
caused by this phase's new gates. **Overall CLEAN rate: 66/194 (34.0%),
up from Phase 10's 26.1% and Phase 11B's 31.6%** - clearing the
~1-point re-harvest noise band Phase 11B itself established, so a real
improvement. Still-DEFECTIVE population remains WRONG_WORD_OR_SENSE-
dominated (46/70), confirming that class needs candidate-pool-level
word-sense disambiguation, not another post-generation gate.

**Category:** Research/design (plan-mode, approved) then implementation
+ self-caught verification bugs, on explicit follow-up approval.
Production code touched: `semantic.py`, `reformulate.py`,
`tests/reformulate_test.py`. Full record: `VALIDATION.md` §51,
`eval/r11c_reverify_report.md`.

### 2026-08-27-E — Architecture Go/No-Go Step 1: ported R45's phoneme-aware decoding-time constraint

**What was done:** per an explicit user proposal to stop the open-ended
"Phase 11D/E/F" pattern and instead give the architecture one final,
serious opportunity before a formal Go/No-Go decision (agreed 4-step
plan: port the generation-side fix, diagnose remaining failures,
formal architecture assessment against pre-registered criteria, then a
genuine three-way decision including "retire this approach"), plan-mode
approved Step 1: port R45/R46's phoneme-aware decoding-time constraint
("Prototype 2") -- the largest measured improvement in this project's
history, never before promoted from the experimental `reformulate_v2()`
path -- into production `_try_escalation()`. Ported exactly as built,
no redesign: same call `_try_escalation_v2()` already made, all 9 of
v1's existing gates (accumulated across Phase 11/11B/11C) left
unchanged. `_try_phrase_replacement()` deliberately not touched
(untested there even experimentally).

**Self-caught, before any number reported:** running `tests/
reformulate_v2_test.py` (a gap in Phase 11C's own verification --
acknowledged, not hidden) surfaced a real pre-existing test failure
caused by Phase 11C's own NLI gate on the shared `_try_substitution()`
colliding with an older test's global mock. Fixed by mocking a
different, non-colliding signal (`grammar_issue_count`) that correctly
isolates the test's actual target.

**Result, deliberately reported as mixed evidence, not a verdict:**
targeted verification on the 42 hardest previously-stuck dense-profile
cases: 16/42 (38%) now produce a candidate at all (smaller than R45's
original ~52%, explained by the much stricter validator stack Phase
11/11B/11C added since that measurement). Full harvest: 162/398 changed,
14 refused->reformulated (vs. 1 in every prior phase, itself
nondeterminism). 128 blind-judged: 23 CLEAN, 105 DEFECTIVE. Overall
CLEAN rate 68/218 (31.2%), DOWN from Phase 11C's 34.0% despite absolute
CLEAN count rising (66->68) -- because coverage rose substantially
(refused count 106->82) while most newly-covered cases landed
DEFECTIVE, not CLEAN, exactly matching R45's own anticipated finding
that roughly half of newly-accepted candidates still carry the defects
the *validation* side targets -- except that validation side is now
actually installed and still isn't enough, since the dominant remaining
defect (WRONG_WORD_OR_SENSE) is invisible to both NLI and grammar
checking. Cost measured directly for the first time in this project:
+3% total harvest latency, concentrated on the hardest cases (+28% on
the targeted set).

**Labeled as:** evidence for Steps 2 (diagnose whether the missing
piece for WRONG_WORD_OR_SENSE is candidate generation or ranking) and 3
(the formal architecture assessment) -- explicitly not a decision on
its own, per the agreement not to judge the architecture question on
one number.

**Category:** Implementation + self-caught verification bug, on
plan-mode approval. Production code touched: `reformulate.py`,
`tests/reformulate_test.py`, `tests/reformulate_v2_test.py`. Full
record: `VALIDATION.md` §52, `eval/arch_gate1_report.md`.

### 2026-08-27-F — Architecture Go/No-Go Step 2: is WRONG_WORD_OR_SENSE a generation problem or a ranking problem?

**What was done:** per the agreed 4-step plan's exact Step 2 question
("determine whether the correct reformulation is absent from the
candidate pool or merely ranked incorrectly"), all 88 currently-
DEFECTIVE, WRONG_WORD_OR_SENSE runs were re-instrumented to expose the
FULL candidate pool the pipeline actually considered (production
top_k/k plus an extended, much larger pool), then classified with full
context (not blind -- root-cause diagnosis, same distinction Phase 10B
drew) by 4 independent subagents. Analysis only, no production code
changed.

**Self-caught, before any number reported:** the instrumentation
crashed on 19/24 restructuring-tier cases due to a dead line of code
in the diagnostic script itself (not production code). Fixed and all
19 re-diagnosed from real data before merging into the final counts --
the earlier, data-free classifications were discarded, not blended in.

**Result: 98 classifications across 88 cases -- PRESENT_BUT_MISRANKED
70 (71%), ABSENT_FROM_POOL 20 (20%), NO_GOOD_OPTION_POSSIBLE 5 (5%),
OTHER 3 (3%).** The dominant, unambiguous answer: for 71% of these
defects, a correct or better candidate was already in the pipeline's
own pool -- this is primarily a selection problem, not a generation-
coverage gap. ~57 of the 70 had the better candidate already in
production's own top_k/k window (a pure ranking-function problem, not
fixable by raising a cutoff); ~13 only appeared at an extended, larger
pool.

**A specific, mechanistically confirmed sub-finding, not just an
impression:** several ranking failures (e.g. "biochemical and
physiological" -> "chemical and physical") trace directly to
semantic.combined_score()'s documented 90%-semantic/10%-frequency
blend: "biological" has HIGHER raw SBERT similarity than the shipped
"chemical"/"physical" in these cases, but LOWER combined score, because
the shipped words are simply more common English words (verified
directly against the actual combined_score() output, not inferred).
This is the formula working exactly as designed, not broken code -- but
demonstrated to be a real, load-bearing contributor to the dominant
remaining defect class. Per Practice.md's standing rule, the 0.90/0.10
weighting is flagged as evidence for a future, SEPARATE, explicit
decision -- NOT changed here, exactly like the MIN_SEMANTIC threshold
question has been handled throughout this project.

**Labeled as:** if Step 3 concludes a learned component is warranted,
this evidence points specifically at a learned reranker/scorer
replacing or augmenting combined_score()'s fixed linear blend, not a
bigger candidate generator -- generation is demonstrably not the
bottleneck for 71% of this defect class. Any such component still
needs to clear the Phase 9B/9C generalization bar before being
trusted, per the criteria already agreed before this step began.

**Category:** Evaluation/analysis, on direct instruction following the
agreed 4-step plan. No production code touched, self-caught bug was in
the diagnostic tooling only. Full record: `VALIDATION.md` §53,
`eval/step2_wrong_sense_report.md`.

### 2026-08-27/28-G — Architecture Go/No-Go, Step 3 prep: generalization check on a genuinely fresh corpus

User selected "run a small fresh-corpus check first" to close a gap
identified while scoping Step 3: every evaluation since Phase 10 (11,
11B, 11C, Architecture Gate Step 1, Step 2) re-verified the SAME frozen
R10 corpus, so none of it answers how the architecture performs on
material it hasn't been iteratively patched against.

Built an 18-sentence / 36-run fresh corpus (10 technical, from 5
Wikipedia topics never used before in this project; 8 hand-authored
general sentences), harvested through today's unchanged production
`reformulate()`, blind-judged the 28 reformulated outputs with the same
no-metadata rubric used every prior phase.

**Result: CLEAN rate 6/28 (21.4%)** — roughly 10 points below every
R10-corpus figure this exact architecture has produced (26.1% -> 32.6%
-> 31.6% -> 34.0% -> 31.2%), well outside the ~1-2 point noise band this
project independently established across three prior re-harvests. The
gap concentrates exactly where Steps 1-2 already pointed: `dense_mixed`
profiles scored **0/10 CLEAN** on fresh material (vs. 6/18 for
`core_word`), and WRONG_WORD_OR_SENSE remains the dominant defect (12 of
22 DEFECTIVE cases), consistent with, not a new mechanism versus, Step
2's finding.

**Reading, not yet a decision:** a meaningful fraction of the R10-corpus
improvement measured across Phases 11/11B/11C and Architecture Gate
Step 1 looks like it was fitting to that corpus's specific, by-now
well-studied failure modes rather than a generalizable architectural
gain — this is the first direct evidence for that reading, not a final
verdict. This result is load-bearing input to Step 3's formal
assessment, specifically the "generalization to unseen material"
criterion.

**Also disclosed:** the corpus file's docstring originally overclaimed
"verbatim Wikipedia" for all 10 technical sentences; 4 of the 10 (G2,
G3, G5, G7) actually had a parenthetical example/abbreviation trimmed
for brevity when the corpus was first built. Corrected in the corpus
file itself before any results were reported on it, per Practice.md's
evidence-tagging discipline.

**Category:** Evaluation/analysis, on direct instruction (user's
AskUserQuestion selection). No production code touched. Full record:
`VALIDATION.md` §54, `eval/step3_gencheck_corpus.py`,
`eval/step3_gencheck_harvest.py`, `eval/step3_gencheck_raw_results.json`,
`eval/step3_gencheck_blind_results.json`.

### 2026-08-28-H — Architecture Go/No-Go Step 3 (formal assessment) and Step 4 (RECOMMENDATION, pending ratification)

**What was done:** synthesized all evidence gathered across this arc
(Phase 10's stress test, Phase 10B, Phases 11/11B/11C, Architecture
Gate Step 1, Step 2, and the just-completed fresh-corpus check) against
the 8 criteria named in the agreed plan (CLEAN rate, defective-output
rate, dangerous semantic reversals, refusal/escalation rate,
dense-profile performance, generalization to unseen material,
consistency/reproducibility, computational cost). Full record: `eval/
step3_architecture_assessment.md`, `eval/step4_recommendation.md`,
`VALIDATION.md` §55.

**Disclosed process gap:** the agreed plan called for pre-registered
numeric thresholds per criterion; only the 8 criteria themselves were
ever actually written down in advance, not concrete pass/fail numbers.
Named honestly rather than silently worked around; the mitigation is
that every cited number was recorded before this synthesis was
written, and the fresh-corpus check was interpreted independently
before this document existed.

**Key synthesis finding:** CLEAN rate plateaued at 31-34% on the
R10 corpus across three full phases of work after Phase 11's initial
jump from 26.1%; dense/multi-constraint profiles score 0% CLEAN on
BOTH the original frozen corpus (before any fix, Phase 10) and a
completely fresh corpus (after every fix) -- an unmoved failure mode
across the entire optimization arc; fresh-corpus CLEAN rate (21.4%) is
~10-13 points below every frozen-corpus figure, outside the established
~1-2 point noise band; the dominant defect (WRONG_WORD_OR_SENSE) is a
ranking problem (per Step 2) that no mechanism added across
Phases 11/11B/11C/Architecture-Gate-1 actually touches.

**RECOMMENDATION (not yet ratified): Option C** -- freeze the current
architecture as the maintained/shipped state, do not pursue a learned
reranker. Option A is not supported by the evidence (21.4% fresh CLEAN,
0% on dense profiles is not "good enough"). Against Option B: Step 2's
reranker diagnosis is well-motivated on its own, but this project's own
evidence -- Phase 9B/9C's prior learned validator failing 99% of the
time on held-out data (the mandatory bar the user required), plus this
exact fresh-corpus check just showing the CURRENT, simpler,
human-inspectable system fail an equivalent generalization test using
the same limited Claude-judged evaluation infrastructure a reranker
would also depend on -- gives specific, not hypothetical, reason to
doubt a learned component built the way this project would have to
build one would generalize any better. Not a permanent ban; reopenable
if independently-collected, larger labeled data becomes available.

**Category:** Evaluation/synthesis + recommendation, on direct
instruction following the agreed 4-step plan. No production code
touched. Awaiting user ratification before Step 4 is treated as closed.

### 2026-08-28-I — Architecture Go/No-Go Step 4 RATIFIED: architecture frozen

**What was done:** the user explicitly ratified the Step 4
recommendation (2026-08-28-H, Option C) in full, instructing: "Freeze
the current architecture now. We have completed the planned
optimization arc and formally reached the practical ceiling of the
current rule/gate-based architecture based on the evidence gathered.
Do not implement any further optimization, rules, gates, ranking
tweaks, threshold changes, or learned components ... The freeze is not
abandonment of the project. It means this architecture is now the
reference baseline for any future, fundamentally different approach."
This closes the Architecture Go/No-Go arc opened 2026-08-27.

**Effect:** the reformulation pipeline as it stands at commit `7451ec4`
(Architecture Gate Step 1 -- the last commit touching `reformulate.py`/
`rephrase.py`/`semantic.py`; confirmed via `git log` that every commit
since is documentation/evaluation only) is frozen as the maintained/
shipped baseline. No further rule, gate, threshold, ranking-weight,
blocklist, or learned-component work is authorized on the current
evidence base. Routine maintenance (dependency updates, non-behavioral
bug fixes) continues normally -- this is a scope freeze on optimization
work, not a moratorium on keeping the codebase running.

**Explicit reopening conditions (per the user's own instruction, not
left implicit):** optimization may resume only given (1) a
substantially larger, independently collected labeled dataset -- not
built the same way as the small, Claude-judged, thin-per-class-sample
corpus this freeze's evidence rests on -- or (2) a genuinely different
modeling approach, which must itself clear this project's own held-out
generalization bar (the Phase 9B/9C precedent) before being trusted
over the frozen baseline.

**Category:** Direct user instruction, ratifying a recommendation this
project's own evidence produced. No production code touched --
documentation/versioning only (`VALIDATION.md` §56, `ROADMAP.md`,
`CHANGELOG.md`, and git tag `architecture-freeze-v1`). Full record:
`VALIDATION.md` §56.

---

### 2026-08-30-A — External literature connection recorded: the Bitter Lesson (Sutton)

**What was done:** the user surfaced Rich Sutton's essay "The Bitter
Lesson" and observed that this project's own Architecture Go/No-Go arc
(2026-08-27-E through 2026-08-28-I above) independently rediscovered
its core pattern in miniature -- a hand-engineered rule/gate stack
plateauing while the dominant remaining defect was diagnosed as a
ranking problem, the kind general/learned methods are typically better
suited to. Recorded as durable context, per direct instruction to add
it to documentation.

**Alternatives considered:** N/A -- documentation/context addition, not
an implementation decision; no code or config changed.

**Why:** Practice.md's evidence-classification discipline (§5) calls
for situating findings against relevant outside literature where it
exists. This connection is genuine but was recorded with its own
caveat rather than taken at face value: Sutton's argument requires the
general/learned method to actually have sufficient data and compute
available, not merely be tried instead of hand engineering. This
project's own Phase 9B/9C precedent -- a prior learned validator
failing 99% of the time on held-out data -- is a case of exactly that
precondition being unmet, and it lost, which the essay's own logic
predicts rather than contradicts. Read this way, the essay corroborates
the freeze's two existing reopening conditions (`VALIDATION.md` §56)
rather than arguing to loosen them.

**Measured result:** N/A -- no experiment; a literature/interpretation
note, tagged [OBSERVATION]/[INTERPRETATION] per Practice.md §5's
vocabulary, not [FACT] or [FINDING].

**Category:** Documentation only. No production code touched. Does
**not** change the freeze's scope, status, or reopening conditions --
those stand exactly as ratified in 2026-08-28-I / `VALIDATION.md` §56.
Full record: `VALIDATION.md` §57.

---

### 2026-08-30-B — Stage 8 opened: charter + branch for a learned-reformulation research direction, kept off `main`

**What was done:** per direct user instruction, opened a named
container for exploring reopening condition (2) from the freeze
(`VALIDATION.md` §56) -- a genuinely different, likely learned,
modeling approach to the ranking problem Step 2 diagnosed. Created
`LEARNED_REFORMULATION_RESEARCH.md` (charter only, no research
performed) and the branch `research/stage8-learned-reformulation`,
opened from `main` at this commit. `main` is untouched by this entry
beyond the doc-trail updates listed below.

**Alternatives considered:** The user's own prior-session draft proposed
naming this "Stage 5 -- Learned Reformulation." Rejected on a direct
check against `DOCS.md`/`HANDOFF.md`: "Stage 5" already names
`REFORMULATION_RESEARCH.md` (Stage 6 and Stage 7 are also already
taken, by the `reformulate.py` evaluation and the human pilot
respectively). "Stage 8" is the next unused number in the existing
sequence -- kept the existing convention's intent (discoverability
inside the project's own numbering) while fixing the collision, rather
than inventing an unrelated codename.

**Why:** The user asked how to package the frozen implementation for
partners while continuing new research in the same repo, and for a name
for that new direction. Per this project's own freeze terms, new
optimization work is only authorized as an explicit instance of
condition (1) or (2) -- this is condition (2)'s work, so it gets a
named, evidence-gated container rather than starting as loose commits
on `main`, which the freeze already forbids for architecture changes.

**Measured result:** N/A -- setup only, no research performed yet.

**Category:** Engineering/process decision (branching, naming,
charter). No production code touched; `main`'s frozen implementation is
unaffected. The branch is explicitly not authorized to merge into
`main` until a Stage 8 result clears the freeze's held-out
generalization bar (Phase 9B/9C precedent) -- see the charter file's
own "Relationship to the frozen baseline" section. Full record:
`LEARNED_REFORMULATION_RESEARCH.md`.

---

### 2026-08-30-C — Stage 8 renamed to Stage LR; branch renamed to `stage-lr`

**What was done:** per direct user instruction, renamed "Stage 8" to
**"Stage LR"** everywhere it's referenced (`LEARNED_REFORMULATION_
RESEARCH.md`, `DOCS.md`, `CLAUDE.md`, `ROADMAP.md`) and renamed the
branch from `research/stage8-learned-reformulation` to `stage-lr`
(deleted the old branch on `origin`, pushed the new one). "LR" stands
for **Learned Reformulation** -- the stage's actual subject, spelled
out in full at the top of the charter file so the abbreviation is never
opaque on its own. No scope, content, or authorization changed: Stage
LR is exactly the same charter as 2026-08-30-B, still off `main`, still
not authorized to merge until it clears the freeze's held-out
generalization bar.

**Alternatives considered:** Keeping "Stage 8" (rejected -- the user's
own stated reason: accurate but "a tough long name," harder to say/
remember day to day than what it stands for). A number-free name
unrelated to the existing stage sequence was not chosen either, to keep
this discoverable inside the project's own numbering the way every
other stage document is (per 2026-08-30-B's own reasoning for picking
a stage slot in the first place) -- "LR" replaces "8" as this slot's
label, it doesn't remove the slot.

**Why:** Direct, practical: a name used constantly in conversation and
commands should be short and self-explanatory. "Stage LR" reads as
what it is (Learned Reformulation) without needing the numbering
history looked up first, while still slotting into that history for
anyone who does look it up.

**Measured result:** N/A -- naming/branch-mechanics change only. No
code touched, no research performed.

**Category:** Engineering/process decision (renaming). Per this
project's own append-only discipline (see this file's header), the
2026-08-30-B entry above is left as originally written rather than
edited -- this entry is the correction on record. Full record:
`LEARNED_REFORMULATION_RESEARCH.md`, `CHANGELOG.md`.

---

### 2026-08-30-D — Fixed: SBERT/MeaningBERT/contextual-fit were silently failing to load on this machine (environment fix, affects the frozen baseline)

**What was done:** found (while testing unrelated Stage LR code, on the
`stage-lr` branch) that all three semantic-preservation/naturalness
signals in `semantic.py` -- SBERT, MeaningBERT, and the contextual-fit
model -- were failing to load on this machine, silently falling back to
frequency-only ranking. Root cause: `protobuf` 5.29.6 installed, but
`tensorflow` 2.21.0 (present in this venv, imported transitively when
`transformers`/`sentence-transformers` probe for available backends)
requires protobuf gencode >= 6.31.1. Fixed by removing the actual root
cause rather than bumping a shared dependency: `tensorflow` and `keras`
were uninstalled -- confirmed first, by direct grep, that no file in
this repo imports `tensorflow`, and that neither `sentence-transformers`
nor `transformers` declares it as a requirement (both run on `torch`
alone, already a direct requirement). `protobuf` was left at 5.29.6,
since two *other* unrelated packages present in this same venv
(`google-ai-generativelanguage`, `grpcio-status` -- neither used by this
project, not in `requirements.txt`) require protobuf `<6.0`; bumping
protobuf instead of removing `tensorflow` would have fixed this
project's models while breaking those two. Separately found and fixed:
`pyinflect` (a direct `requirements.txt` dependency) was missing
entirely from this venv, pre-existing and unrelated to the protobuf
issue -- installed, since `tests/contextual_fit_test.py` and
`tests/meaningbert_test.py` both import `reformulate.py` -> `grammar.py`
-> `pyinflect` and could not even be collected without it.

**Alternatives considered:** Upgrade `protobuf` to `>=6.31.1` instead.
Tried first, then reverted -- confirmed via `pip install` output that
it breaks `google-ai-generativelanguage`'s and `grpcio-status`'s own
declared constraints. Removing the unused `tensorflow`/`keras` instead
fixes the same problem with a smaller blast radius, since nothing in
this project needs them.

**Why:** Direct instruction, after this was found to affect not just
Stage LR's new code but `semantic.py` itself -- shared with the live,
frozen pipeline `main` ships. Verified as real, not just "tests pass,"
per the same standard applied when the silent failure was first caught:
loading status flags alone were insufficient evidence last time (they
reported failure clearly, so that wasn't the issue here), but real
numeric output was still checked directly rather than trusted from
status alone.

**Measured result:** All three models load and produce real, correctly-
directioned numbers, checked directly, not just via status flags:
SBERT similarity 0.829 (paraphrase-shaped pair) vs. 0.038 (unrelated
pair); MeaningBERT 94.32 vs. 0.02 (same pairs, native 0-100 scale);
contextual-fit produces small positive probabilities in the expected
range for both a known-natural and a known-natural-adjacent word
(0.0003-0.0068 -- consistent with this signal's own documented
low-magnitude-but-real-signal behavior, R33-R37). This project's own
test suites confirm it with real assertions, not just imports
succeeding: `tests/semantic_test.py` 18/18 pass; `tests/
contextual_fit_test.py` + `tests/meaningbert_test.py` 21/21 pass
together, including `test_known_bad_case_scores_low`/
`test_known_good_case_scores_higher`-style real-number checks, not just
`test_status_reports_loaded`. `tests/smoke.py` (SBERT on) vs. `tests/
baseline_sbert.txt`: **one line differs** -- `'dont' -> "don't"` is
labeled `[spelling]` in the committed baseline, `[contraction]` in
today's run; the actual corrected output text is byte-identical, only
the internal layer-attribution label differs. This is in the
`pyspellchecker`-based grammar-correction layer, a different subsystem
from the three models this fix touched -- flagged as likely pre-
existing drift (this environment could not run `tests/smoke.py` at all
before `pyinflect` was restored, so there was no way to have observed
this diff earlier), not investigated further and not fixed here since
it's non-behavioral and out of this fix's scope. Baseline file left
untouched -- regenerating it is a separate, deliberate decision, not
made silently alongside an unrelated fix.

**Category:** Routine maintenance / dependency fix, explicitly permitted
under the freeze (`VALIDATION.md` §56 -- "routine maintenance...
continues normally"). Affects `main` directly, recorded here because it
affects the frozen baseline partners are relying on, per direct
instruction. No reformulation algorithm, weight, threshold, or gate
changed. Installed versions after this fix: `protobuf==5.29.6`,
`pyinflect==0.5.1`, `tensorflow`/`keras` removed (were not in
`requirements.txt`).

---

### 2026-08-30-E — Fixed: `language_tool_python` was missing, silently disabling a live grammar gate in `reformulate.py`

**What was done:** found (while wiring a grammar signal into Stage LR's
LR.2 feature extractor, on the `stage-lr` branch) that
`language_tool_python` -- a direct `requirements.txt` dependency
(`language-tool-python>=3.4.0`) -- was not installed in this venv.
`semantic.grammar_issue_count()` returns `None` when the tool can't
load; `reformulate.py` uses it as a live gate in two places
(`_try_escalation`/phrase-tier: `if (sem.grammar_issue_count(cand) or
0) > 0: reject`) -- with the tool missing, `None or 0` is `0`, so `0 >
0` is `False`, meaning the gate has been **silently never firing**,
the same class of bug as 2026-08-30-D's SBERT/MeaningBERT finding, but
this one is a hard accept/reject gate on the live pipeline, not just a
reported metric. Installed the missing package (already pinned in
`requirements.txt`, nothing new added).

**Verified with real output, not just status flags:** `grammar_issue_count("She go to the store.")` → 1 (catches the real error);
`grammar_issue_count("She goes to the store.")` → 0; the specific
"softwares" pluralization case found during Stage LR's LR.2 sanity
check → 1. `tests/smoke.py` (SBERT on) vs. `tests/baseline_sbert.txt`:
**no new diff** beyond the single, already-disclosed, non-behavioral
line from 2026-08-30-D (the 'dont'→"don't" spelling/contraction
label) -- this fix did not change the frozen substitution-tier
corpus's output.

**A real, pre-existing problem found and NOT caused by this fix,
verified directly, not assumed:** `tests/reformulate_test.py`'s
`EscalationTest.test_count_threshold_triggers_restructuring`/
`UnknownTokenRejectionTest.test_garbled_token_detected` and
`tests/reformulate_v2_test.py`'s
`PhonemeConstrainedGenerationTest.test_output_never_contains_blocked_sound`
fail. Before assuming this fix caused it, tested both ways directly:
uninstalled `language_tool_python` again and re-ran the same 3 tests --
**they fail identically without the fix too.** Confirmed pre-existing,
unrelated to this change. Not investigated or fixed here -- out of
scope for a dependency fix, flagged for separate attention rather than
silently left for someone to rediscover.

**Category:** Routine maintenance / dependency fix, explicitly
permitted under the freeze. Affects `main` directly -- a real,
previously-silent hard gate on the shipped pipeline is now live, not
just a diagnostic. No reformulation algorithm, weight, or threshold
changed; the gate itself is unchanged code, only its dependency is
restored. Installed: `language-tool-python==3.4.0`. Known, pre-existing,
separate issue flagged: the 3 named test failures above, confirmed
independent of this fix.
