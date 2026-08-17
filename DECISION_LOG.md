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
