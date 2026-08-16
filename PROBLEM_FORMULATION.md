# PROBLEM_FORMULATION.md — Stage 4A: The Text-Only Problem and Its Foundation

Per Practice.md §19 and this stage's own instructions: this document covers
research (steps 1–3), design (step 3), and a real implementation + test pass
(steps 4–5) — but explicitly **not** the reformulation engine itself. Every
claim is labeled per `RESEARCH.md`'s legend (`[FINDING]` / `[INTERPRETATION]`
/ `[HYPOTHESIS]` / `[LIMITATION]` / `[FUTURE WORK]` / `[RECOMMENDATION]`),
reused here for continuity with that document.

---

## 1. Problem formulation — text-only, restated and critiqued

### 1.1 As given

> Given a piece of user-provided text and a persistent representation of the
> linguistic patterns a particular speaker finds difficult to produce,
> generate an alternative formulation that preserves the original meaning,
> intent, and relevant context while reducing the presence of those
> problematic patterns and remaining natural, grammatical, and appropriate.

```
TEXT + SPEAKER DIFFICULTY PROFILE  →  TEXT REFORMULATION  →  ALTERNATIVE TEXT
```

### 1.2 Critique

This formulation is sound as a *description of the eventual system's I/O
contract*. It is incomplete as a description of what "the profile" is,
because it silently assumes the profile is a single, homogeneous thing. It
isn't — and conflating its parts is exactly the mistake this stage's own
instructions warn against (§6/§13 of the task: a word being difficult does
not imply its phonemes are difficult). The refined formulation:

> Given text and a **speaker difficulty profile with three explicitly
> separate parts** (difficult sounds, difficult words, difficult phrases —
> each independently declarable, none implying the others), plus, in the
> future, a fourth source (structured signals from an Audio Module), produce
> an alternative formulation.

This document's job is to build the profile side of that contract — the
`+ SPEAKER DIFFICULTY PROFILE` term — correctly, before anything touches the
`TEXT REFORMULATION` box.

### 1.3 Research questions from the task, answered

- **Should phoneme difficulty and lexical difficulty be separate concepts?**
  **[FINDING, RESEARCH.md §1.2/§2.F]** Yes — psycholinguistically, lexical
  access (word-finding) and articulatory/motor execution (sound production)
  are different mechanisms; stuttering is understood as primarily a
  motor-execution phenomenon, distinct from a word-retrieval disorder.
  Conflating "this word is hard" with "every sound in this word is hard"
  would be a category error the moment a future reformulation engine tries
  to use the data, e.g., substituting a word that shares an unrelated syllable
  with a flagged word for no real reason. **Decision: kept fully separate**
  (§2 below).
- **Can a speaker have difficulty with a word without difficulty with its
  constituent phonemes?** **[INTERPRETATION]** Yes, plausibly often — a word
  can be hard because it's unfamiliar, long, or has an unusual stress
  pattern, none of which is captured by "this speaker blocks on /θ/."
  Word-level and sound-level difficulty are correlated in general but not
  identical for any specific instance, which is exactly why they're stored
  as separate declarations rather than one implying the other.
- **Can a speaker have difficulty with a phoneme only in certain positions
  or contexts?** **[LIMITATION, acknowledged not solved]** Almost certainly
  yes (onset vs. coda, stressed vs. unstressed syllable, word-initial vs.
  mid-sentence) — the *existing* onset-matching mechanism this repo already
  has (`phonetic.py`, kept unchanged this stage) only models word-initial
  onset position. This stage does not extend that model — it's flagged as
  future work (§8) precisely because doing so is a reformulation-engine-side
  change, out of scope here.
- **Should phrases be treated separately from words?** **[FINDING, RESEARCH.md
  §2.F clinical literature]** Yes — a phrase can be difficult as a
  *sequence* even when no individual word or sound in it is independently
  flagged (prosody, rhythm, or a specific word-to-word transition can be the
  actual source of difficulty). Stored as a third, independent category (§2).
- **Should the profile represent only explicit user declarations initially?**
  **[Decision, per the task's own explicit instruction]** Yes. `source` is
  recorded per entry (`user_typed` / `user_selected_from_text` /
  `system_observed`), with `system_observed` reserved, unused, for §9's
  future Audio Module integration.

---

## 2. The profile schema

```
DifficultyProfile (per speaker)
 ├── sounds:  [DifficultyEntry, ...]
 ├── words:   [DifficultyEntry, ...]
 └── phrases: [DifficultyEntry, ...]

DifficultyEntry
 ├── value          the user's text, display form, case preserved
 ├── normalized      the dedup/matching key (see §3)
 ├── category        "sound" | "word" | "phrase"
 ├── source          "user_typed" | "user_selected_from_text" | "system_observed" (unused, reserved)
 ├── added_at         ISO-8601 timestamp
 ├── pronunciation    words only; ARPAbet phones or null (see §4)
 └── meta             {} — empty, reserved for future fields (severity, confidence,
                       context) without a schema migration when they're added
```

**[Decision]** No severity/confidence/frequency/position fields are
populated in this stage, per the task's explicit "do not over-engineer"
instruction. `meta: {}` exists so adding them later is additive (new key in
an existing dict), not a migration.

**[Decision, explicitly per the task]** `source` cleanly separates
user-declared data (`user_typed`, `user_selected_from_text` — both populated
today) from future system-observed data (`system_observed` — reserved,
never written by anything in this stage). See §9.

---

## 3. Representation research: sounds, words, phrases

### 3.1 ARPAbet vs. IPA — researched, not assumed

**[FINDING]** ARPAbet is ASCII-only, English-specific, and is what CMU
Pronouncing Dictionary natively uses; IPA is the universal linguistic
standard, unicode-based, more expressive, and more recognized by trained
linguists/SLPs, but not by a general audience — "the ARPAbet (and to a much
larger extent, the IPA alphabet) uses a specific notation to encode phonemes
that is not widely known" to end users generally.

**[Decision, evidence-based]** Keep ARPAbet as the **internal**
representation (zero conversion cost — this repo's `phonetic.py` and CMU
dict integration already speak it fluently and are being reused unmodified;
see §7), and **never surface raw ARPAbet/IPA as the primary user-facing
label**. The user always types an ordinary spelling-like cue ("str", "th",
"r") — exactly as before this stage — and the system does the conversion.
Where a technical detail is shown at all (an onset preview, a word's
pronunciation), it's small, secondary, and clearly optional information, not
something the user must understand to use the feature. **[FUTURE WORK]**
IPA as an *additional*, opt-in display format was considered and rejected
for this stage — no clear benefit for this project's non-linguist user base
was found in the research, and it adds unicode-rendering risk for no
demonstrated gain; revisit only if a specific user population (e.g., SLP
clinicians) is identified as needing it.

### 3.2 Should words map to phonemes automatically?

**[Decision, directly answering the task's §6]** A word's pronunciation is
derived **for display only**, via a new, purely additive function,
`phonetic.full_pronunciation(word)` — CMU-dict lookup, stress digits
stripped, returning `None` (not a guess) for out-of-vocabulary words. It is
**never** used to create or influence a `sounds` entry. Marking "three"
difficult does not add `/TH/` to `sounds` — that would be exactly the
conflation §1.3 argues against. The pronunciation is shown next to the word
entry in the UI purely so the user can see *why* a word might be hard, as
an aid to understanding, not as a hidden side effect that changes what gets
stored.

**[Decision — deliberately conservative]** `full_pronunciation()` does *not*
fall back to a guessed pronunciation for OOV words the way `phonetic.onset()`
already does for the *onset* (a documented, accepted approximation for
gating). The reasoning: a wrong onset guess only weakens a filter (cheap
failure mode, already accepted risk in the existing pipeline); a fabricated
*full* pronunciation would be presented to the user as if it were a
verified fact about their own word (expensive failure mode — false
confidence). `None` displayed as "pronunciation unknown" is honest;
a fabricated one is not.

### 3.3 Should sounds dedup by spelling or by pronunciation?

**[Decision, tested — `tests/difficulty_profile_test.py::test_duplicate_sound_by_arpabet_not_spelling`]**
By pronunciation. "c" and "k" are different letters but the same ARPAbet
phoneme (`/K/`) — normalizing through `phonetic.normalize_pattern()` (an
existing, unmodified function) means they correctly dedup as *one* declared
sound difficulty, not two. This is a direct, tested application of
`RESEARCH.md` §2.F's finding that pronunciation, not spelling, is what
determines articulatory difficulty.

### 3.4 Phrase representation

**[Decision, per the task's "don't overcomplicate" instruction]** Phrases
are stored as plain, whitespace-normalized, lowercased text — no attempt at
structured tokenization, n-gram indexing, or position tracking in this
stage. **[FUTURE WORK]** How a stored phrase gets *matched* against new
input text (exact substring? fuzzy/reordered? partial overlap?) is
explicitly deferred to the reformulation-engine stage — this stage only
establishes that phrases are captured as a first-class, independent
category, not how they'll later be detected in arbitrary new text. The
representation chosen (plain text) doesn't foreclose any future matching
strategy.

---

## 4. Persistence: JSON vs. SQLite — researched, not assumed

| Criterion | JSON (per-user file, existing pattern) | SQLite |
|---|---|---|
| Inspectable | Yes — human-readable, diffable in git-style review | Requires a DB browser/query |
| Easy to modify | Yes — a text editor suffices | Requires SQL or a client |
| Data volume | Tiny — tens to low hundreds of entries per user | Designed for volumes this project doesn't have |
| Query needs | None — always "load the whole profile for this user" | Would matter only for cross-user queries (e.g. "find all users struggling with /str/"), which nothing in this stage or the near-term roadmap needs |
| New dependency | None — matches `user_store.py`'s existing, working pattern | New dependency (`sqlite3` is stdlib, but still a new persistence *pattern* alongside the existing JSON one) |
| Migration risk | Additive key in an existing file (see §5) | Would require migrating existing `users/*.json` accounts into a new store, real risk for no offsetting benefit at this data volume |

**[Decision]** JSON, as an **additive key** (`difficulty_profile`) inside
the *existing* per-user `users/<username>.json` file that `user_store.py`
already manages — not preserved merely because it existed, but because it's
the objectively right choice at this data volume and this project's stated
"avoid unnecessary infrastructure" value, per the criteria above.
**[FUTURE WORK]** If a later stage needs to query *across* users (e.g. for
research/eval on population difficulty patterns), that's the point at which
SQLite (or even just concatenating JSON files) becomes worth reconsidering
— not before.

---

## 5. Reusing vs. changing the existing implementation

Per the task's explicit instruction to determine this before implementing,
not to preserve things merely because they exist:

| Existing piece | Kept as-is? | Why |
|---|---|---|
| `phonetic.onset()`, `matches_any()`, `normalize_pattern()`, `word_difficulty()` | **Unchanged** | Already correct for this stage's needs; RESEARCH.md found no reason to touch them, and this stage explicitly must not redesign scoring/gating logic |
| `user_store.py`'s `phoneme_profile` (`stutter_patterns`/`blocked_words`) | **Kept, now an auto-derived mirror** | It's exactly "difficult sounds" + "difficult words" already, just as flat, unstructured lists with no phrase support and no metadata. Rather than maintaining it as an independent, separately-edited list (real drift risk — the same class of problem `RESEARCH.md` §6 flagged for the two rewrite pipelines), it's now *derived* from the new `difficulty_profile` on every save. This is the **only** point of contact between the new foundation and the existing reformulation pipeline — see §6. |
| The old "Blocklist" UI column | **Absorbed, not duplicated** | It was already, semantically, "difficult words" (Gate A in `grammar.py` treats `blocked_words` as words to always flag) — editable from *two* separate UI surfaces before this stage (the free-text patterns/blocked panel, and the Blocklist expander). That pre-existing redundancy is resolved by making the new Words column the single place to manage it, reusing its already-working add/remove-button pattern rather than inventing a new one. |
| The "Allowlist" UI | **Unchanged, kept separate** | A genuinely different concept — words that must *never* be touched, unrelated to difficulty — not in scope for this stage. |
| `profiling/profile.py`'s `SpeakerDifficultyProfile` (EWMA onset-risk model) | **Unchanged, kept separate from the new profile** | A different kind of thing: a *learned, continuous* scoring model consumed by `rewrite/`, not a flat user-declared list. Conflating the two would mean redesigning `rewrite/`'s input contract, which is a reformulation-engine change explicitly out of scope this stage. The relationship between them is future work — see §9. |

**[LIMITATION, stated explicitly]** This means the repository now has *two*
different "difficulty" representations that don't talk to each other yet:
the new, structured, user-declared `DifficultyProfile` (this stage), and the
old, learned, continuous `SpeakerDifficultyProfile` (unchanged, still
running, still feeding `rewrite/`). This is not an oversight — it's the
direct, correct consequence of the task's explicit instruction not to touch
the reformulation engine this stage. Reconciling them is named as the
natural next step in §9/`ROADMAP.md`.

---

## 6. How the foundation reaches the (unchanged) reformulation engine today

```
DifficultyProfile.save()
        │
        ▼
user_store.save_difficulty_profile()
   writes difficulty_profile{}  (new, structured)
   AND derives+writes phoneme_profile.stutter_patterns/.blocked_words
        │
        ▼
st.session_state.stutter_patterns / .blocked_words
   (refreshed immediately in the current session — no re-login needed)
        │
        ▼
grammar.py::SentenceRewriter.rewrite(stutter_patterns=..., blocked_words=...)
rewrite/rewriter.py::DifficultyAwareRewriter    ← UNCHANGED call sites, UNCHANGED logic
```

**[FACT, verified by test]** `grammar.py`, `engine.py`, `semantic.py`,
`rewrite/*.py`, `rephrase.py`, and `profiling/profile.py` have **zero**
lines changed in this stage. `tests/smoke.py`'s output is byte-identical to
the committed baseline after this stage's changes (verified below, §7) —
direct, checkable evidence the reformulation pipeline's behavior is
unaffected, not just an assertion.

`phrases` has **no consumer yet** — nothing in the current reformulation
pipeline accepts a phrase-level constraint. This is honest and correct: the
task explicitly does not ask this stage to make phrases *do* anything yet,
only to let the user *declare* them.

---

## 7. Text-entry and flagging interaction — design and research

### 7.1 What the task asks for, and the real constraint it runs into

The requested interaction: select text inline (not necessarily double-click,
per the task's own explicit permission to choose a different mechanism),
see a small contextual action, flag it, get clear confirmation, be able to
undo.

**[FINDING]** Native, JS-level "receive the browser's text selection as
Streamlit input" is a **documented, open gap** in Streamlit itself — there
is an active community feature request for exactly this
("Feature request: receive selected text as user input," Streamlit forum),
and the only existing solutions are third-party custom components
(`streamlit-text-annotation`, `st-tex-annotation`, `text-highlighter`) built
with separate React/JS frontend toolchains.

**[INTERPRETATION]** Building an equivalent custom component from scratch in
this pass would mean hand-rolling the `postMessage`-based Streamlit
component protocol and verifying it in a real browser — something this tool
environment cannot do. Shipping that as if it were a tested, working
foundation would repeat exactly the mistake this repository's own
`HANDOFF.md` already flags as a pitfall for `voice.py`'s `st.iframe` usage
(unverified browser JS, never confirmed to actually work). Given this
stage's own framing — *"The most important outcome is not a fancy
interface. It is a correct, well-researched, persistent representation"* —
building something unverifiable would work against the stage's actual goal.

### 7.2 What was actually built

A two-path interaction, both using **only native Streamlit widgets** (fully
testable, verified below):

1. **Free-text flagging** (primary, general-purpose): a text input + "Add"
   button per category (Sounds / Words / Phrases). The user can type a word
   directly, or use the browser's own native text selection (a capability
   every browser already has, requiring no custom code) to select-and-copy
   text from the entry box above and paste it in. This genuinely uses text
   selection — the browser's native one — without any custom JS.
2. **Quick-pick from current text** (convenience, words only): a dropdown
   auto-populated with the unique words already present in whatever the
   user has typed into the main text area (`extract_candidate_words()`),
   plus a "Flag" button. This directly satisfies "select something in your
   current text and mark it as difficult" for the single-word case — the
   task's own example (`thoroughly`) — as one compact widget, not "every
   word as a separate box/button" (the task's explicit anti-pattern).
   Phrases aren't offered through this path (a dropdown of individual
   tokens can't represent a multi-word span); the free-text path (paste a
   selection) covers that case.

**Confirmation and undo:** `st.success`/`st.info` messages after add
("clear indication after flagged"); every entry renders with its own ✕
remove button ("ability to undo/remove the flag").

**[RECOMMENDATION — not built, explicitly deferred]** A true inline
"select text, a small floating button appears next to the selection" JS
component remains the better long-term UX and was genuinely researched, not
dismissed out of hand. The concrete technical path, for a future session
with real-browser access to verify it: `st.components.v1.html()` rendering
the text as flowing HTML, a `mouseup` listener reading `window.getSelection()`,
a small absolutely-positioned button near the selection's bounding rect, and
a hand-rolled `postMessage`-based Streamlit component value channel (the
`streamlit-component-lib.js` helper would need to be vendored locally,
not loaded from a CDN, to preserve this project's offline-only guarantee).
This is recorded as a specified, ready-to-build future item, not implemented
now, precisely so it doesn't get shipped as verified when it isn't.

### 7.3 What was explicitly NOT done

Per the task's explicit prohibition: no token-per-word chip UI. The main
text area still renders as one normal, continuously-flowing text box —
nothing about entering or viewing the text changed from before this stage.

---

## 8. Fundamental design questions, answered directly

- **How should multiple simultaneous difficulties be represented?** As
  independent entries across the three lists — no attempt to represent
  *interaction* between them (e.g., "this word is only hard when preceded by
  a difficult sound") in this stage. **[LIMITATION]** Interaction modeling
  is unaddressed, consistent with `RESEARCH.md` §7's finding that this is
  underexplored in the literature generally, not just in this repo.
- **What information should eventually be learned from user feedback?**
  **[FUTURE WORK, directly named in RESEARCH.md §5.5/R9]** Whether a
  suggested reformulation (once the engine exists) was accepted or rejected
  — the `Fluent` system's active-learning loop is the concrete precedent.
  `meta: {}` on each entry, and the reserved `system_observed` source value,
  are the two places this would attach without a schema change.
- **How should this interface with a future automatic speech-analysis
  module?** See §9.

---

## 9. Future audio-module integration (not implemented)

**[Decision, per the task's explicit instruction]** The schema already
supports it without modification: an external module producing
`{"word": ..., "phoneme": ..., "confidence": ..., "context": ...}` per the
task's own example maps directly onto a `DifficultyEntry` with
`source="system_observed"` and the extra fields (`confidence`, `context`)
placed in `meta` — no migration needed when that integration is built,
because `meta` was designed empty-but-present for exactly this. **Nothing
imports, calls, or depends on any audio/ASR code to do this** — the
`difficulty_profile.py` module has zero dependency on `out_of_scope/`, and
the whole feature works end-to-end from manual input alone, verified by the
tests in §10.

---

## 10. Testing — what was run, and what wasn't

### 10.1 Fully automated, run, passing

`tests/difficulty_profile_test.py` (26 tests) — add/remove/dedup for all
three categories; text edge cases (punctuation-adjacent, capitalization,
contractions, numbers, proper nouns, leading/trailing whitespace,
multi-word phrase capture); pronunciation derivation including the OOV case
(`full_pronunciation()` returns `None`, not a guess); persistence across a
fresh `DifficultyProfile.load()` (simulating an app restart); the legacy
`phoneme_profile` mirror staying in sync on both add and remove; migration
of a pre-existing legacy-only profile into the new structure without data
loss; migration firing exactly once, not resurrecting a removed entry on
a later reload.

`tests/app_test.py` (extended, scenario 5) — the actual Streamlit widgets,
through `AppTest`: panel renders; add word/sound/phrase via the real text
input + button widgets; entries appear in rendered markdown; the legacy
session-state mirror (`stutter_patterns`/`blocked_words`) updates
immediately, in the same session, with no re-login; remove button works;
removed entry disappears from rendered output.

```
$ DISABLE_DATAMUSE=1 python tests/difficulty_profile_test.py
Ran 26 tests in 0.85s — OK

$ DISABLE_DATAMUSE=1 python tests/app_test.py
[ok] default load / sentence mode / word mode / rephrase toggle / difficulty profile add+remove
RESULT: ALL PASS
```

Also re-ran, unmodified, to confirm zero regression in the untouched
reformulation pipeline: `tests/roadmap_test.py` (3/3 pass),
`tests/persistence_test.py` (pass), `tests/smoke.py` (**byte-identical**
to `tests/baseline_sbert.txt`).

### 10.2 Explicitly not tested — stated honestly, not glossed over

**[LIMITATION]** No real-browser, JS-driven interaction exists in this
implementation, so there is nothing of that kind to test — this is a
consequence of the §7.1 decision, not a gap in an otherwise-JS-based
feature. `AppTest` does not execute a real browser or real JS; it verifies
Streamlit's Python-side widget tree and session state, which is what this
implementation is actually built from, so the coverage above is a genuine
test of the shipped feature, not a partial one.

---

## 11. Rejected alternatives, summarized

| Alternative | Rejected because |
|---|---|
| Custom bidirectional Streamlit component (hand-rolled `postMessage` protocol) for inline text selection | Unverifiable in this environment; would ship untested browser JS as if proven, repeating a known pitfall already on record for `voice.py` |
| Third-party Streamlit annotation components (`streamlit-text-annotation`, etc.) | New external dependency requiring a separate JS/React toolchain, conflicting with this project's offline-first, minimal-infrastructure values; unverifiable here either |
| Storing difficulty as a single flat list (no sound/word/phrase separation) | Directly contradicts the task's central requirement (§1.3) and `RESEARCH.md`'s psycholinguistic finding that these are different mechanisms |
| Auto-deriving `sounds` entries from a flagged word's phonemes | Exactly the conflation §1.3/§6 of the task explicitly warns against |
| SQLite for profile storage | No query need this data volume/access pattern justifies; would add a new persistence pattern for no offsetting benefit (§4) |
| Maintaining `phoneme_profile` as an independently-edited list alongside the new `difficulty_profile` | Real, demonstrated drift risk — the exact failure mode `RESEARCH.md` §6 already flagged for this repo's two rewrite pipelines; resolved by making it a derived mirror instead |
| IPA as the primary user-facing phoneme notation | No evidence found that it serves this project's non-linguist users better than the existing spelling-cue-in, ARPAbet-internal approach; adds unicode risk |

---

## 12. What this stage deliberately does not attempt

Per the task's explicit scope restriction, and worth restating plainly:
no synonym generation, no contextual lexical substitution, no paraphrase
generation, no sentence restructuring, no semantic scoring of candidate
reformulations, no NLI verification, no candidate ranking, no LLM/T5
generation call added, and no phrase-matching logic (detecting a stored
phrase inside new input text). The output of this stage is **structured
profile data**, not a rewritten sentence — verified by the fact that
`tests/smoke.py`'s reformulation output is unchanged.
