# PROBLEM_FORMULATION.md — The Text-Only Problem and Its Foundation

Covers Stage 4A (2026-08-15: the initial sounds/words/phrases profile
foundation), its refinement (2026-08-16: word-specific sound patterns,
single-default-profile architecture), and a foundation audit (2026-08-16,
same day: checking the result for ambiguity before treating it as settled —
see §11). This is a living design document, not an append-only log — where
a later pass changed an earlier decision, this file states the **current**
design and reasoning; it does not preserve the superseded version as if it
were still accurate. The append-only record of *that something changed and
why* lives in `DECISION_LOG.md`.

Every claim is labeled per the legend: `[FINDING]` (literature/documented,
cited) / `[INTERPRETATION]` (our reasoning from a finding) / `[HYPOTHESIS]`
(untested claim) / `[LIMITATION]` (a stated gap) / `[FUTURE WORK]`
(deferred, not started) / `[RECOMMENDATION]` (a forward-looking proposal,
not a decision) / `[Decision]` (what was actually built and why).

---

## 1. Problem formulation

> Given text and a **speaker difficulty profile**, produce an alternative
> formulation that preserves meaning while reducing the presence of
> whatever is difficult for that speaker.

The profile is not one homogeneous thing. It is **four explicitly separate
concepts**, none implying any other:

```
GLOBAL SOUND DIFFICULTY      "I have trouble with /r/, generally."
WORD DIFFICULTY              "This word is difficult," no claim about why.
PHRASE DIFFICULTY            "This phrase is difficult as a sequence."
WORD-SPECIFIC SOUND PATTERN  "Within THIS word specifically, these sounds
                               are the problem" — scoped to one word entry,
                               never a global claim by itself.
```

**[FINDING, RESEARCH.md §1.2/§2.F]** Lexical access (word-finding) and
articulatory/motor execution (sound production) are different
psycholinguistic mechanisms; stuttering is understood as primarily a
motor-execution phenomenon. Conflating "this word is hard" with "every
sound in this word is hard" is a category error a reformulation engine
would act on incorrectly — e.g. substituting an unrelated word purely
because it shares a syllable with a word the user actually just finds
unfamiliar, not phonetically hard.

**[INTERPRETATION, this refinement's central case]** The same logic applies
one level deeper: a speaker may be "perfectly comfortable saying /th/ in
general" and "perfectly comfortable saying /r/ in general" while still
finding the word "three" difficult specifically because of how /th/ flows
into /r/ *in that word*. Promoting that observation into "I->/th/ is always
difficult" and "/r/ is always difficult" would overgeneralize from one data
point. This is why word-specific patterns are stored as an attribute of the
word they were observed in, never auto-copied into the global `sounds`
list — see §2 and §3.4.

**Other research questions from the task, answered:**
- *Can a speaker have difficulty with a word without difficulty with its
  constituent phonemes?* **[INTERPRETATION]** Yes — unfamiliarity, length,
  or stress pattern can make a word hard independent of any single phoneme.
- *Should phrases be treated separately from words?* **[FINDING, RESEARCH.md
  §2.F]** Yes — a phrase can be difficult as a sequence even when no
  individual word/sound in it is independently flagged.
- *Should the profile represent only explicit user declarations initially?*
  **[Decision, per the task]** Yes — see `source` in §2.

---

## 2. The profile schema

```
DifficultyProfile (per speaker)
 ├── sounds:  [DifficultyEntry, ...]      GLOBAL sound difficulty
 ├── words:   [DifficultyEntry, ...]      word difficulty (+ optional pattern)
 └── phrases: [DifficultyEntry, ...]      phrase difficulty

DifficultyEntry
 ├── value            display text, case preserved
 ├── normalized       dedup/matching key (§3)
 ├── category         "sound" | "word" | "phrase"
 ├── source           "user_typed" | "user_selected_from_text" | "system_observed" (reserved, §8)
 ├── added_at         ISO-8601 timestamp
 ├── pronunciation    words only; full ARPAbet phone sequence or null (§3.2)
 ├── problem_phones   words only; a user-selected SUBSET of `pronunciation` —
 │                     the word-specific pattern, or null if not specified
 └── meta             {} — empty, reserved for future fields, no migration needed
```

**[Decision]** `problem_phones` lives on the word entry it describes, not
as a fifth top-level list — it's meaningless without the word it's scoped
to, and a top-level list would need a foreign key back to the word anyway,
which is more machinery for the same information.

**[Decision]** Promoting a word's `problem_phones` into a **global**
`sounds` entry is a separate, explicit method call
(`add_sound_from_phones()`) — nothing sets `problem_phones` and
automatically touches `sounds`. Tested directly:
`tests/difficulty_profile_test.py::test_setting_pattern_does_not_create_global_sound`.

---

## 3. Representation research

### 3.1 ARPAbet internally, never raw ARPAbet/IPA as the primary user-facing label

**[FINDING]** ARPAbet is ASCII, English-specific, and what CMU dict natively
uses; IPA is the universal standard but unicode and no more familiar to a
general audience — "the ARPAbet (and to a much larger extent, the IPA
alphabet) uses a specific notation ... not widely known" to end users.
**[Decision]** ARPAbet stays internal (zero conversion cost, already
integrated); the user never has to type or read a raw phone code to use the
feature.

### 3.2 Word → pronunciation → pattern, and why it's display-only until the user acts

**[Decision]** `phonetic.full_pronunciation(word)` (new, additive, CMU-dict
only, no grapheme-guess fallback — returns `None` rather than a fabricated
pronunciation for OOV words) is used purely to populate the checkbox list
in the pattern editor. Nothing in this module ever reads `pronunciation`
and writes to `sounds` on its own.

### 3.3 Showing phones to non-technical users — respelling, not raw codes

**[FINDING, this refinement's new research]** Dictionaries written for
general readers use **pronunciation respelling** — a familiar reference
word per sound (e.g. "dye-REE-a" for diarrhea) — specifically because most
readers know neither IPA nor ARPAbet notation; "most people are normally
more comfortable with pronunciation spellings commonly found in newspapers
... which make use of well-known words." Webster's New World Dictionary,
Chambers, Collins, and Cassell's all use a respelling system rather than
raw IPA for exactly this audience reason.

**[Decision]** `phonetic.friendly_phone_label()` implements the same idea
in miniature: a fixed table (`ARPABET_EXAMPLE_WORD`, all 39 CMU phones)
mapping each phone to one common English word that contains it — "TH (as
in "think")" rather than bare "TH". This is the label shown for every
checkbox in the pattern editor. **[FUTURE WORK]** A full non-phonemic
respelling of the *whole word* (e.g. "th-REE") was considered and not built
— the per-phone table achieves the same accessibility goal with far less
work, and covers the actual UI need (labeling individual selectable
phones), not a general-purpose respelling engine.

### 3.4 Should sounds dedup by spelling or pronunciation?

**[Decision, tested]** By pronunciation — "c" and "k" both normalize to
`/K/` and dedup as one entry. Also holds for phones-based sounds: a sound
typed as "thr" and one promoted from a word's TH+R pattern normalize to the
same key and dedup correctly
(`test_promoted_sound_dedups_against_typed_sound`).

### 3.5 Phrase representation

**[Decision, unchanged from Stage 4A]** Plain, whitespace-normalized,
lowercased text. **[FUTURE WORK]** How a stored phrase gets matched against
new input text is deferred to the reformulation-engine stage.

---

## 4. The pattern-selection interaction — design and research

### 4.1 What was asked for, and what Streamlit actually supports

The task's example shows a "contextual popup/dialog" appearing after a word
is flagged, offering pronunciation phones as selectable items.

**[FINDING]** Streamlit has a native modal primitive, `st.dialog`
(decorator-based). **[FINDING, this refinement]** It also has a **documented,
open bug**: "Using AppTest, st.dialog does not execute code within
st.buttons" (streamlit/streamlit#9786) — button clicks inside a dialog are
never triggered when driven by the automated test harness this project
relies on for verification.

**[Decision]** `st.dialog` was **not used**, specifically because of that
bug — this project's established testing standard (set in Stage 4A, when
an equivalent custom-JS-selection idea was rejected for being unverifiable)
is not to ship an interaction that can't actually be exercised by the test
suite. Instead: a plain, session-state-toggled inline panel
(`_render_pattern_editor()` in `app.py`), which is exactly as testable as
every other widget in the app — and was, in fact, tested
(`tests/app_test.py` scenario 6, checkbox clicks and all).

### 4.2 What was built

1. A 🔍 button next to each word entry (disabled, with an explanatory
   tooltip, when the word has no derivable pronunciation) opens/closes an
   inline panel below the three-column layout.
2. The panel lists the word's phones **in order**, each as an individually
   keyed `st.checkbox` labeled with its friendly gloss (§3.3) — not a
   `st.multiselect`, specifically to avoid ambiguity when the same phone
   occurs twice in one word (checkbox keys are `{word}_{position-index}`,
   so duplicates never collide).
3. **Selecting nothing and closing is a fully valid, non-error outcome** —
   the word stays a plain word-level difficulty. This directly satisfies
   the task's "do not assume the user always knows or needs to specify a
   phoneme."
4. A separate "Also add ... as a GLOBAL difficulty" checkbox, **default
   unchecked**, is the only path from a word-specific pattern to a global
   `sounds` entry.
5. The panel **auto-opens right after a word is successfully added** (via
   the Add button or the quick-pick-from-text control) — matching the
   task's example flow (flag → immediately asked what's difficult about
   it) — but is also reachable any time later via the 🔍 button, covering
   the "manage the profile without entering text first" requirement too.

### 4.3 What remains deferred

**[RECOMMENDATION — not built]** A true inline "select text in place, a
floating button appears at the selection" interaction (for flagging
arbitrary spans directly from the text, not just whole words via the
dropdown) — researched in Stage 4A, still unbuilt, technical approach fully
specified in that pass's record (superseded text kept only in
`DECISION_LOG.md`/`CHANGELOG.md` history, not repeated here since nothing
changed about that specific finding this refinement).

---

## 5. Single-default-profile architecture

### 5.1 What was removed, and why

**[Decision, directly per the task]** `auth.py` and `user_store.py` were
deleted (`git rm` — recoverable from history, not archived in-repo,
per the task's explicit "do not create unnecessary compatibility layers
just to preserve obsolete behavior"). Removed with them: the login/register
screens, SHA-256 password hashing, multi-account management UI, the
sidebar user badge and logout button.

**Why now, not just "because the task said so":** the login layer was
already flagged in this project's own evidence trail as a liability, not
just unneeded complexity — `DECISION_LOG.md` 2026-06-13-A/2026-06-07-A
record that `users/default.json` and `users/bobcat.json` carried committed,
weakly-hashed password material, and `ROADMAP.md` R0 named remediating it
the single highest-priority item in the whole project (ahead of any
research question). Removing the auth layer doesn't purge that material
from git *history* (a separate, harder problem, not attempted here without
explicit authorization to rewrite published history), but it does mean **no
new password hashes are ever written again**, and the current
`users/default.json` and the now-deleted `users/bobcat.json` were rewritten
to a clean schema with no `password_hash` field at all
(`tests/difficulty_profile_test.py::test_no_account_fields_survive_a_save`
verifies a save() always drops any password_hash a loaded record might
still carry).

### 5.2 What stayed extensible, and how

**[Decision, directly per the task's "do not make future multi-user
support impossible" instruction]** `profile_store.py`'s entire public API
takes a `profile_name` parameter, defaulting to `DEFAULT_PROFILE = "default"`
— it is never hardcoded away. `DifficultyProfile` and `SpeakerDifficultyProfile`
(unchanged) both already took a name/username parameter before this
refinement; nothing about *that* changed. What's gone is the **UI and
auth layer** around choosing/switching/creating profiles, not the storage
layer's ability to key by name. Reintroducing multiple profiles later is a
UI change (add a profile picker back) plus a decision about how a picker
authenticates (or doesn't) — not a data-model change.

### 5.3 Where the data lives, and a deliberate naming inconsistency

**[Decision, explained rather than hidden]** Profiles still live at
`users/<profile_name>.json` — the directory is **not** renamed to
`profiles/`, even though "users" now reads oddly for a single-profile app
with no accounts. Reason: `profiling/profile.py` (unmodified, out of scope
both this stage and its refinement) hardcodes `ROOT / "users"` for its own
per-speaker `*.fluency_profile.json` files. Renaming the directory would
require touching that file, which neither this stage nor its refinement
does. This is recorded explicitly so the naming mismatch reads as a stated
constraint, not an oversight.

### 5.4 Schema simplification

**[Decision]** The on-disk record dropped two fields that existed in the
Stage-4A-era schema: `password_hash` (no auth = meaningless) and
`phoneme_profile` (the mirror described in Stage 4A's original version of
this document — see §6 below for why it's gone, not just renamed).
Current schema:

```json
{
  "profile_name": "default",
  "difficulty_profile": {"sounds": [...], "words": [...], "phrases": [...]},
  "custom_replacements": {},
  "preferences": {"allowlist_words": [...], "rephrase_enabled": true, "profile_rewrite_enabled": true}
}
```

---

## 6. How the profile reaches the (still unchanged) reformulation engine

**This is the one part of the design that changed shape in the
refinement, not just in scope.** Stage 4A's original approach persisted a
`phoneme_profile` mirror to disk on every save, specifically so
`auth.py::_load_user_into_session()` could read it at login time.
**[Decision, this refinement]** With `auth.py` gone, there is no login-time
read to serve — `app.py` now derives `stutter_patterns`/`blocked_words`
**purely in memory**, once per session, directly from the loaded
`DifficultyProfile`:

```
app.py startup
        │
        ▼
_difficulty_profile()  — DifficultyProfile.load("default")
        │
        ▼
_sync_legacy_session_from_profile()
   st.session_state.stutter_patterns = profile.sound_values()
   st.session_state.blocked_words    = profile.word_values()
        │
        ▼
grammar.py::SentenceRewriter.rewrite(stutter_patterns=..., blocked_words=...)
rewrite/rewriter.py::DifficultyAwareRewriter    ← UNCHANGED call sites, UNCHANGED logic
```

Any add/remove re-runs this same sync immediately
(`_save_difficulty_profile()`), so the current session always reflects the
latest profile with no re-login step to trigger it (there's no login at
all anymore). **[Simplification over Stage 4A]** This removes an entire
persisted, must-stay-in-sync field (`phoneme_profile`) that existed only to
serve a login step that no longer exists — one fewer piece of state that
could drift.

**[FACT, verified by test]** `grammar.py`, `engine.py`, `semantic.py`,
`rewrite/*.py`, `rephrase.py`, and `profiling/profile.py` still have
**zero** lines changed. `tests/smoke.py`'s output remains byte-identical to
the committed baseline after this refinement.

`phrases` and word-specific `problem_phones` both still have **no
consumer** in the reformulation pipeline — declared and persisted, not yet
acted on. Correct and expected: neither this stage nor its refinement
touches the reformulation engine.

---

## 7. Testing

### 7.1 What's covered, and how

`tests/difficulty_profile_test.py` — 38 tests: the original 26 (dedup, text
edge cases, OOV pronunciation, persistence, legacy migration) plus 12 new
ones for this refinement — setting/clearing a word-specific pattern,
**that doing so never creates a global sound entry**, pattern validation
against the word's real pronunciation (rejects a phone the word doesn't
actually contain), behavior for a word with no derivable pronunciation,
explicit promotion to a global sound and its dedup behavior, persistence of
`problem_phones` across a reload, and that a save() always drops obsolete
account fields.

`tests/app_test.py` — extended with two new scenarios exercising the actual
Streamlit widgets: scenario 5 (add/remove word/sound/phrase, unchanged from
Stage 4A but re-verified against the new storage layer) and **scenario 6**
(flag "three", confirm the pattern editor auto-opens, click the TH and R
checkboxes by their real widget keys, save without checking "promote",
confirm the word shows "specifically: TH, R" in rendered markdown, **and
confirm `st.session_state.stutter_patterns` stays empty** — i.e. no global
sound was created). Also newly verified: no login/register text appears
anywhere in the rendered app, and a profile pre-written directly to disk
loads correctly through the real startup path (not just via session-state
pre-seeding, which no longer works the same way once `_difficulty_profile()`
syncs from disk on every fresh session — see the comment at the top of
`tests/app_test.py` for why the test-seeding approach changed).

`tests/persistence_test.py` — rewritten (it previously depended entirely on
the now-deleted `auth.py`) to test `profile_store.py`'s preference
round-trip directly: a never-saved profile still returns a complete,
well-formed preferences dict (the app must never crash on a brand-new
default profile), and the real running app's default profile has one.

Also re-ran unmodified: `tests/roadmap_test.py` (3/3 pass), `tests/smoke.py`
(byte-identical to baseline).

```
$ DISABLE_DATAMUSE=1 python tests/difficulty_profile_test.py   → 38/38 OK
$ python tests/persistence_test.py                              → ok
$ DISABLE_DATAMUSE=1 python tests/roadmap_test.py                → 3/3 OK
$ DISABLE_DATAMUSE=1 python tests/app_test.py                    → ALL PASS (6 scenarios)
$ diff tests/baseline_sbert.txt <(python tests/smoke.py)         → no diff
```

### 7.2 Explicitly not tested

**[LIMITATION, unchanged from Stage 4A]** No real-browser JS interaction
exists in this implementation (§4.3), so there's nothing of that kind to
verify — `AppTest` covers the Python-side widget tree and session state,
which is the entirety of what was actually built.

---

## 8. Future audio-module integration (still not implemented)

**[Decision, unchanged]** `source="system_observed"` and the empty `meta`
dict remain reserved, unused by anything in this repo, specifically so a
future Audio Module's `{"word":..., "phoneme":..., "confidence":...,
"context":...}` output maps onto a `DifficultyEntry` without a schema
migration. Nothing here imports or depends on `out_of_scope/`.

---

## 9. Rejected alternatives (this refinement)

| Alternative | Rejected because |
|---|---|
| `st.dialog` for the "what's difficult about this word?" popup | Documented AppTest bug — button clicks inside it don't execute under test (streamlit/streamlit#9786); would ship an unverifiable interaction |
| Auto-creating a global `sounds` entry when `problem_phones` is set | Exactly the word-vs-phoneme conflation the whole refinement exists to prevent |
| `st.multiselect` for phone selection | Ambiguous/colliding options when a word repeats a phone; per-position checkboxes have no such ambiguity |
| Hardcoding a single profile name with no parameter | Would make reintroducing multi-user later a data-model change, not just a UI one — violates the task's explicit extensibility instruction |
| Renaming `users/` → `profiles/` | Would require touching `profiling/profile.py` (hardcodes `users/`), which is out of scope; documented as a deliberate naming mismatch instead |
| Archiving `auth.py`/`user_store.py` in an `out_of_scope/`-style folder | Not an audio/ASR concern (the only category that folder represents, per Stage 2) and git history already preserves them; keeping a copy in-tree is exactly the "unnecessary compatibility layer" the task says to avoid |
| A full non-phonemic word respelling (e.g. "th-REE") | The per-phone friendly-label table achieves the same accessibility goal for the actual UI need (labeling individually selectable phones) with far less engineering |

---

## 10. What this stage and its refinement deliberately do not attempt

Unchanged from Stage 4A: no synonym generation, contextual lexical
substitution, paraphrase generation, sentence restructuring, semantic
scoring, NLI verification, candidate ranking, or LLM/T5 generation change.
No phrase-matching logic. No consumption of `problem_phones` by any
scoring/gating code. The reformulation engine's behavior, verified by
`tests/smoke.py`, is unchanged by either pass.

---

## 11. Foundation audit (2026-08-16, same day as the refinement)

Before treating the schema above as settled, it was checked directly
against real data (CMU dict lookups, actual round-trips through
`phonetic.normalize_pattern`), not just reasoned about abstractly. Two real
issues were found and fixed; several other questions were checked and found
already handled correctly; a few are named as genuinely out of scope for a
foundation pass.

### 11.1 Can every entry be unambiguously interpreted? — checked per category

- **Global sound.** Unambiguous *given* one fact that wasn't previously
  stated explicitly anywhere: a `sounds` entry is always an **onset**
  pattern (matches word-initial phones only), because that's the only kind
  of phoneme matching the existing, unmodified reformulation engine
  (`phonetic.matches_any`) does. This was always true — it's inherited from
  Stage 1 — but the new profile schema doesn't self-document it (no
  `sounds` entry says "onset-only" anywhere in its fields). **Resolved by
  documentation, not a schema field**: adding a `position` field with only
  one possible value (`"onset"`) would be speculative — there's no second
  value it could take yet, and Practice.md §3/§6's evidence-constrained
  principle argues against adding structure for a distinction that doesn't
  exist in the code yet. Recorded here and in `difficulty_profile.py`'s
  docstring instead.
- **Difficult word.** Unambiguous as "this spelling, case/punctuation-
  normalized, is difficult" — *except* for the CMU heteronym case, §11.3.
- **Difficult phrase.** Unambiguous as declared text. Matching it against
  future input text is explicitly deferred (§3.5, `ROADMAP.md` R13) — not
  an ambiguity in the *storage*, a gap in the (not-yet-built) consumer.
- **Word-specific pattern.** Unambiguous once one deliberate simplification
  is stated explicitly (it wasn't, until this audit): `problem_phones`
  identifies **phone classes within the word, not specific occurrences**.
  A word with a repeated phone (`"level"` → `L EH V AH L`, `L` at positions
  0 and 4) cannot represent "only the second L is the problem" — checking
  either checkbox marks that phone as difficult everywhere it occurs in
  that word. **Kept as-is, not changed to position-tracking**: for the
  reformulation engine's actual purpose (avoid this phone when picking a
  substitute near this word), *which* occurrence was intended doesn't
  change what the engine should do with the information — tracking
  position would be real added complexity for a distinction that doesn't
  change downstream behavior. The UI now says so explicitly when a word
  has a repeated phone, so this reads as a decision, not an unexplained
  quirk when someone reopens the editor and sees a sibling checkbox
  pre-checked.

### 11.2 Can the future reformulation engine consume this cleanly?

**What it will actually receive today** (via the one bridge that exists,
§6): two flat lists of strings, `stutter_patterns` and `blocked_words`,
exactly as before this stage — `problem_phones` and `phrases` are not
wired to anything yet (§10, unchanged). **What it would receive if/when a
later stage consumes `difficulty_profile` directly** (not built yet): the
schema in §2, which is self-contained per entry — no entry requires
resolving a reference to another entry to be interpreted, except the
already-acknowledged word ↔ its own `problem_phones` (which is intrinsic,
not cross-entry).

**A concrete, previously-undetected bridge bug, found by testing (not
assumed) and fixed this pass:** `add_sound_from_phones()` (used when a
word-specific pattern is promoted to a global sound) builds a display
`value` like `"TH-R"`. The *existing* bridge re-derives an ARPAbet key from
that string by **spelling guess** (`phonetic.normalize_pattern`), the same
mechanism used for user-typed cues like `"str"` — because that mechanism
is what the unmodified `grammar.py`/`phonetic.py` contract expects, and
touching that contract is out of scope this stage. Verified directly:
`normalize_pattern("th-r".lower())` → `('TH','R')` (correct, most phones
round-trip fine), but `normalize_pattern("zh".lower())` → `('Z','HH')`
(**wrong** — ZH has no English onset spelling that decodes back to ZH,
because ZH essentially never starts an English word). **Fixed**:
`add_sound_from_phones()` now checks its own round-trip fidelity at
creation time and records `meta["legacy_bridge_unreliable"] = True` when
it fails, and the UI shows "⚠️ not fully enforced yet" on that entry rather
than silently accepting it as if it worked. Not fixed at the root, because
the root (the spelling-based bridge) is explicitly temporary — `ROADMAP.md`
R10/R12 already call for replacing it when the reformulation engine is
redesigned; patching around it further would be effort spent on code
that's slated for removal. Tested:
`test_promoted_sound_with_lossy_roundtrip_is_flagged` plus an end-to-end
`tests/app_test.py` scenario that promotes ZH from a real word ("measure")
through the actual UI and confirms the warning renders.

### 11.3 Missed cases, checked one at a time

- **Multiple pronunciations.** Real and common — checked against live CMU
  data: `"read"` has 2 variants (present/past tense), `"the"` has 3,
  `"object"`, `"often"`, `"route"` each have 2. `full_pronunciation()`
  silently uses CMU's first-listed variant, which is not guaranteed to be
  the sense the user meant. **Fixed, minimally**: a new
  `phonetic.pronunciation_variant_count()` detects this, and adding a word
  with more than one variant now sets `meta["has_alternate_pronunciations"]
  = True`, shown in the UI as "⚠️ has multiple pronunciations." **Not
  fixed further** — letting the user pick *which* variant they meant needs
  a variant-picker UI (more widgets, more tests) and arguably needs
  sentence context to resolve automatically; that's a real feature, not a
  one-line adjustment, and is named as future work rather than built here.
- **Same word, different contexts** (e.g. "read" present vs. past is
  actually the multi-pronunciation case above; a subtler version is a word
  that's spelled and pronounced identically but has different *difficulty*
  in different grammatical roles). **Not addressed, named as genuinely out
  of scope**: distinguishing *which occurrence* of a word in a sentence a
  difficulty applies to would require capturing sentence context at
  flag-time and matching it later — full word-sense disambiguation, which
  `RESEARCH.md` §2.B/§7 already identifies as a real, unsolved problem for
  the *reformulation engine*, not something a profile foundation should
  attempt to solve on its own.
- **Repeated words** (the same word appears twice in one input). No new
  issue: `extract_candidate_words()` already dedups for the quick-pick
  list, and word difficulty is intentionally a type-level declaration (one
  entry covers every occurrence) — this is the same underlying question as
  "same word, different contexts," not a separate gap.
- **Phrases containing difficult words** (e.g. "research" is a difficult
  word and also appears inside the difficult phrase "through the
  research"). Checked: the two facts are stored independently and neither
  entry references the other. **This is intentional, not a gap** — the
  profile records independent facts; checking for overlap between a phrase
  and the words it contains is a computation the *consumer* (the future
  reformulation engine) does over the whole profile, not something the
  storage layer should pre-compute or cross-link. Documented here so a
  future engine implementer doesn't assume the profile already did this.
- **Overlapping difficulties in general** (a word's `problem_phones`
  happens to match a separately-declared global sound; a word is both
  difficulty-flagged and separately allowlisted). Checked: redundant-but-
  consistent overlap (word pattern + matching global sound) is harmless —
  both signals just reinforce each other, no conflict to resolve.
  Word-vs-allowlist overlap is a real potential tension between two
  *different, both-untouched* features, but it's already resolved
  correctly by existing, unmodified code: `grammar.py`'s allowlist check is
  a hard lock that's checked before any substitution logic runs
  (`DECISION_LOG.md` 2026-06-08-D) — a word that's both difficulty-flagged
  and allowlisted is never substituted, consistent with "allowlist always
  wins," which is the sensible precedent (a hard-to-say word the user
  explicitly never wants changed — e.g. their own name — is a legitimate
  combination, not a contradiction to reject).
- **A word flagged difficult with no stated reason.** Already correctly
  supported and already covered by an existing test
  (`test_leaving_word_as_plain_difficulty_without_a_pattern`) — confirmed
  again during this audit, not a gap.

### 11.4 Is anything over-engineered?

Checked deliberately, not just assumed absent. `meta: {}` and the reserved
`system_observed` source value were re-examined given they're unused right
now — kept, because they're zero-cost reservations (an empty dict, one
unused enum value) against an explicitly planned future integration (the
Audio Module), not speculative building-ahead of an undefined need.
`add_sound_from_phones()` as a method separate from `add_sound()` was
re-examined too — keeping them separate turned out to be load-bearing, not
redundant: collapsing them would mean routing known-correct ARPAbet phones
back through the same spelling-guess path that causes the ZH bug in
§11.2. The one genuine (very minor) redundancy found: `_add_raw()` and
`add_sound_from_phones()` each implement their own short dedup-scan loop;
left as-is (a four-line duplication, not worth the indirection a shared
helper would add for this little repetition).

### 11.5 Verdict: does the data model need a final adjustment?

Two small, targeted, tested additions (§11.2, §11.3's fixed items) — not a
schema redesign. Both are informational (`meta` flags surfaced in the UI),
neither changes what the four core categories mean or how they're stored.
Everything else in this section was either confirmed already correct
(word-without-a-reason, phrase/word independence, allowlist precedence) or
named explicitly as future work too large for a foundation adjustment
(variant-picker UI, phrase-matching logic, word-sense disambiguation) —
listed again, with links, in `ROADMAP.md`.
