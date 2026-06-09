# Speech AI — Changelog

---

## v5.1.0 — Stability fixes, optional Fluency Rephrase, teammate setup
*2026-06-09*

### Fixes
- **Word mode** "No synonyms found" — `engine.get_synonyms` now strips trailing punctuation/case, so sanitized words like `Happy.` resolve correctly.
- **Allowlist** now *locks* words in place (never substituted) instead of forcing their replacement — `SentenceRewriter.rewrite(..., allowlist=...)`.
- **Paragraph mode** dropdown off-by-one fixed, so per-sentence synonym picks apply on rebuild.
- `requirements.txt` line endings repaired (was a single unusable line).

### New (optional, default OFF)
- **`rephrase.py`** — "Fluency Rephrase" layer: a T5 paraphraser + reranker that smooths the synonym sentence while preserving meaning (SBERT gate) and avoiding your stutter onsets. Wired as **Stage ⑥** behind the **"Fluency rephrase (beta)"** sidebar toggle; it **never auto-replaces** (you click "Use this rephrase").
- Dev/research: `tests/threshold_sweep.py`, `tests/evaluate.py` (+ `eval_corpus.txt`/`eval_results.csv`), and `scripts/` LoRA fine-tuning scaffolding (optional — not required; the stock model + reranker are sufficient).

### Teammate setup (clone → test)
1. `pip install -r requirements.txt` — now includes `sentencepiece` + `tiktoken` (needed by the rephrase tokenizer).
2. `streamlit run app.py` → **log in with `default` / `speech`**.
3. First run auto-downloads NLTK data + the SBERT model into `./.cache/` (one-time; needs internet).
4. **Fluency Rephrase is optional**: turning the toggle on downloads a ~0.9 GB T5 model on first use and needs **~1.8 GB free RAM** (SBERT + model together). If memory is tight it safely shows "No rephrase applied" — the rest of the app is unaffected.
5. Optional: LanguageTool grammar needs Java; if absent it degrades gracefully.

---

## v5.0.0 — Multi-User Authentication System
*2026-06-07*

### New Files
- **`auth.py`** — Login / Register screen rendered before the main app. Uses `st.stop()` to fully block the application until authentication succeeds. Supports username dropdown (populated from existing accounts) and a radio toggle between Login and Register modes. Auto-logs in after successful registration.
- **`user_store.py`** — File-based user storage layer. Each user lives in `users/<username>.json` containing password hash, phoneme profile, custom replacements, and preferences. Public API (`register_user`, `verify_user`, `load_profile`, `save_profile`, `list_users`, `migrate_legacy_prefs`) is intentionally thin so the backend can be swapped to SQLite or PostgreSQL without touching `auth.py` or `app.py`.
- **`users/default.json`** — Auto-generated on first startup by migrating the legacy `user_prefs.json`. Default password: `speech`.

### Changes to `app.py`
- Added `require_auth()` call immediately after `st.set_page_config` — nothing in the app renders until login.
- Removed global `load_prefs()` / `save_prefs()` functions and the `_PREFS_PATH` constant.
- Added `_save_current_user_prefs()` which writes phoneme profile changes back to the logged-in user's JSON file only (not a shared global file).
- Added user badge and Logout button to the sidebar. Logout clears all session state and re-triggers the auth screen.
- Session state now initialises `stutter_patterns` and `blocked_words` from the logged-in user's profile instead of a hardcoded file path.
- One-time migration: `migrate_legacy_prefs()` called at startup to convert `user_prefs.json` → `users/default.json` (no-op if already done).

### Data Model Migration
`user_prefs.json` (global, flat) → `users/<username>.json` (per-user, structured):

```json
{
  "username": "alice",
  "password_hash": "<sha256 hex>",
  "phoneme_profile": {
    "stutter_patterns": ["str", "pr"],
    "blocked_words": ["present"]
  },
  "custom_replacements": {},
  "preferences": {}
}
```

---

## v4.1.0 — Bug Fixes (grammar.py integration)
*2026-06-07*

### Fixed
- **SyntaxError on line 631** — Backslash escapes inside f-string expressions (`\"`) are not valid in Python 3.12+. Fixed by extracting dict lookups into named variables before the f-string in all affected pill/chip render blocks.
- **ImportError: `validate_grammar`** — Function was imported from `grammar.py` but never defined there. Removed from import line.
- **ImportError / NameError: `validate_custom_word`** — Function was called via `grammar.validate_custom_word(...)` but does not exist in `grammar.py`. Replaced with a lightweight inline regex validation (`^[a-zA-Z\-']+$`).
- **ValueError: too many values to unpack** — `rewriter.rebuild_with_choices()` returns a plain `str`, but two call sites were unpacking it as a tuple `(rebuilt, post_issues)`. Fixed both sites; `post_issues` is now produced by a small inline subject-verb agreement check on the rebuilt sentence.
- Removed unused `import json` and `import grammar` module-level imports.

---

## v4.0.0 — Sentence Rewriter + SBERT Semantic Firewall
*prior work*

### Features
- Full sentence mode: tokenise → POS tag → synonym candidates → SBERT contextual re-ranking → phoneme firewall → inflect → rebuild.
- Word mode: bare synonym lookup with pill display.
- Stutter profile panel: `stutter_patterns` and `blocked_words` persisted to `user_prefs.json`.
- Risk chip display (high / medium / low) colour-coded by onset match and difficulty score.
- Per-word synonym dropdowns with custom word input.
- Scoring table (collapsible) showing semantic similarity, frequency score, combined rank, and phoneme gate status per candidate.
- Highlighted diff view (original → replaced words).
- Stutter difficulty before/after meter.
- Grammar correction card showing fix-by-fix breakdown.

### Pipeline
1. Sanitize input grammar (`sanitize_input`)
2. Get synonym candidates (engine + WordNet POS filter)
3. SBERT semantic filter (`sem.rank_candidates_contextually`)
4. Combined score ranking (semantic × frequency)
5. Phoneme firewall — drop candidates sharing the user's stutter onset
6. Inflect surface forms (`pyinflect`)
7. Rebuild sentence with user choices

---

## v3.x — Grammar Correction Pipeline (`grammar.py`)

- `sanitize_input()`: 8-layer correction pipeline — contractions, pronoun case, capitalisation, spacing, tense correction, subject-verb agreement (BE and main verbs), auxiliary form correction, negation agreement, existential *there* agreement, punctuation.
- `SentenceRewriter` class with `rewrite()` and `rebuild_with_choices()`.
- Predicate participle detection (treats "she is tired" adjectively for synonym lookup).
- `_preserve_case()` for case-faithful substitution.

---

## v2.x — Phonetic / Stutter Module (`phonetic.py`)

- CMU Pronouncing Dictionary integration for ARPAbet onset extraction.
- Grapheme → ARPAbet fallback for OOV words.
- `onset()`, `normalize_pattern()`, `matches_any()` public API.
- `word_difficulty()` heuristic: onset cluster size + syllable count + rarity.
- `sentence_difficulty()` aggregate score.

---

## v1.x — Core Synonym Engine

- Multi-source synonym engine: WordNet, Datamuse, wordfreq.
- `freq.py` zipf frequency wrapper with `small` wordlist fallback.
- `paths.py` cache redirection (keeps NLTK/SBERT caches local to project).
- Initial Streamlit UI with basic word lookup and pill display.
