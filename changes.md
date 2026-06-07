# Changes — Stutter Assistance, Smarter Grammar, UI & Fixes

This document describes everything added/changed in this update, what teammates
need to install, and how to run and test it. It's written so anyone picking up
the repo can get productive quickly.

---

## TL;DR

- **New feature:** phoneme-aware *stutter assistance* — suggest easier words only
  for the sounds a user struggles with, and never replace them with a word that
  starts with the same sound.
- **Smarter grammar** correction (handles "she is run" → "she is running",
  "there is many problems" → "there are…", and avoids breaking valid passives).
- **Cleaner UI** (light theme, discoverable controls, copy button, risk map,
  difficulty meter) and several **bug fixes** (the semantic-threshold slider
  actually works now, predicate adjectives no longer get verb synonyms).
- **No new pip packages.** One extra dataset (`cmudict`) downloads automatically
  on first run.

---

## What teammates need to download / install

1. **Python 3.10+** (tested up to 3.14).
2. Install dependencies (unchanged list):
   ```bash
   pip install -r requirements.txt
   ```
3. **First run needs internet once.** The app auto-downloads, then caches them
   into a local `./.cache/` folder and runs fully offline afterwards:
   - NLTK data: `averaged_perceptron_tagger_eng`, `punkt_tab`, `wordnet`,
     `omw-1.4`, and **`cmudict`** (new — pronunciation dictionary for the
     phoneme feature).
   - SBERT model `all-MiniLM-L6-v2` (~80 MB) for semantic filtering.

No API keys. No Node/Java/GPU. Datamuse (synonym API) is optional and degrades
gracefully if offline.

### Run
```bash
streamlit run app.py
```
Open http://localhost:8501.

---

## New files

| File | Purpose |
|---|---|
| `phonetic.py` | Phoneme/onset engine: word → starting sound (from CMU dict), parse user patterns (`str`, `pr`, `bo`), the matching used by both gates, and a stutter-difficulty score. |
| `freq.py` | Thin wrapper around `wordfreq` that auto-falls back to a smaller wordlist under low memory instead of crashing. |
| `paths.py` | Redirects model/data caches into `./.cache/` and caps math-library threads to keep startup memory low. Imported first by every module. |
| `.streamlit/config.toml` | Pins a consistent light theme so the UI looks the same for everyone. |
| `.gitignore` | Proper ignores (caches, `__pycache__`, `user_prefs.json`, etc.). The repo previously had a misnamed `gitignore` that wasn't active. |
| `tests/smoke.py` | Behaviour baseline: prints grammar + synonym output for a fixed set of sentences. Diff before/after a change to catch regressions. |
| `tests/app_test.py` | Headless UI test (Streamlit AppTest) — verifies the app runs end-to-end with no exceptions. |
| `tests/baseline.txt` | Saved golden output of `smoke.py` for regression diffing. |

---

## Features in depth

### 1. Phoneme-aware stutter assistance (the headline feature)
People who stutter tend to block on specific **starting sounds** (onsets). In the
sidebar/main panel the user enters their trouble sounds (e.g. `str, pr, b`) and,
optionally, specific **words to always avoid**.

Two filters ("gates") then wrap the existing synonym ranker — they do **not**
change the ranking logic, and when no patterns are entered they do nothing
(behaviour is identical to before):

- **Gate A — targeting:** only words that *start* with a trouble sound (or are on
  the avoid list) get suggestions. Everything else is left untouched.
- **Gate B — firewall:** any candidate synonym that starts with the same trouble
  sound is rejected, so we never trade one stutter trigger for another.
  *Example:* with pattern `pr`, **"present"** is **not** replaced by
  **"prestige"** (both `/pr/`); it picks something like **"gift"**.

Onsets come from the **CMU Pronouncing Dictionary**, so it's based on *sound*,
not spelling — `knee` → `/n/`, `school` → `/sk/`, `hour` → vowel (silent h),
`one` → `/w/`. Words not in the dictionary fall back to a spelling-based guess.

Users can edit both lists anytime; they persist between sessions in a local
`user_prefs.json` (auto-created, git-ignored).

### 2. Smarter grammar correction
- **Auxiliary/progressive fix driven by a verb lexicon, not the POS tagger.**
  The tagger mislabels exactly the broken inputs we care about, so we instead
  check whether a word is the base form of a real verb:
  - "she is run right now" → "she is **running** right now"
  - "I am go now" → "I am **going** now"
  - …while leaving real adjectives alone: "she is tired", "the door is broken"
    stay unchanged.
- **Passive-voice guard.** For verbs whose past participle equals the base form
  (read, run, set, cut, put…), "be + verb" is ambiguous. We only convert to
  progressive when there's a clear cue and no agent:
  - "the book is read by many" → **left correct** (not "is reading")
  - "the race is run" → **left correct**
- **Existential "there" agreement:** "there is many problems" → "there **are**
  many problems"; singular "there is a problem" is left alone.

### 3. Predicate adjectives no longer get verb synonyms
Words like *tired/broken/done/gone* after "be" are now treated as adjectives:
- "She is **tired**" → suggestions like *exhausted, worn-out, spent*
  (previously it wrongly suggested verbs like *eaten, bore*).

### 4. Bug fixes
- **Semantic-threshold slider now works.** Previously the slider had no effect
  (the value was frozen at import). Moving it now genuinely tightens/loosens how
  close in meaning a suggestion must be.
- **Deterministic suggestions.** Equal-frequency candidates are now ordered
  consistently, so the same sentence always produces the same auto-pick.
- **Grammar-check notes** are computed by word position, fixing wrong labels when
  a word appears twice in a sentence.

### 5. Performance & robustness
- **Datamuse lookups are cached** (and the timeout lowered), so repeated words
  and repeat searches are much faster.
- **Low-memory fallback:** if the large frequency list or the SBERT model can't
  fit in RAM, the app degrades to a smaller list / frequency-only ranking
  instead of crashing.
- **Offline/deterministic switch:** set `DISABLE_DATAMUSE=1` to skip the network
  source entirely (useful for offline use and reproducible tests).

### 6. UI improvements
- Stutter controls moved to a clear panel under the search box (they were hidden
  in a collapsed sidebar before).
- Consistent **light theme** (fixes low-contrast/invisible text in dark mode).
- **Stutter Risk Map** (each word colour-coded by difficulty), a **before→after
  difficulty score** on the result, a **one-click copy** button, clearer
  "why was this word skipped" messages, and the confusing "Results" slider
  renamed to **"Synonyms / word"**.

---

## Optional configuration (environment variables)

| Variable | Effect |
|---|---|
| `WORDFREQ_LIST` | `best` (default) / `large` / `small`. Force `small` on low-RAM machines. |
| `DISABLE_DATAMUSE` | `1` = WordNet-only (offline / deterministic). |
| `NLTK_DATA`, `HF_HOME`, `SENTENCE_TRANSFORMERS_HOME`, `TORCH_HOME` | Override cache locations (default: `./.cache/`). |

---

## How to test

```bash
# Behaviour baseline (grammar + synonyms). Compare before/after a change:
python tests/smoke.py > tests/after.txt
diff tests/baseline.txt tests/after.txt        # use fc on Windows

# Headless UI smoke (no browser) — should print ALL PASS:
python tests/app_test.py
```

---

## Known limitations (honest notes)

- Grammar correction is rule-based on top of an imperfect POS tagger; complex
  sentences (relative clauses, multi-clause agreement) can still slip through.
- Bare ambiguous passives with no cue and no agent (e.g. "the door is shut") are
  intentionally left untouched rather than risk a wrong edit.
- The pronunciation dictionary is US English, so a few region-specific onsets
  (e.g. "herb") follow US pronunciation.
- Word-mode (single words, no sentence context) can mix parts of speech, since
  there's no surrounding sentence to disambiguate.
