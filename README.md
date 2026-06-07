# 🎙️ Speech AI

**An accessibility-focused speech assistance system for people who stutter.**

Speech AI takes a sentence you struggle to say, corrects its grammar, identifies words that fall on your personal trouble sounds, and suggests semantically equivalent alternatives that are easier to pronounce — all in a clean, interactive Streamlit interface.

Built at **NUST SEECS** as part of independent research into AI-assisted communication accessibility.

---

## What it does

You type a sentence. Speech AI runs it through a seven-stage pipeline:

1. **Grammar correction** — fixes contractions, tense, subject-verb agreement, auxiliary forms, negation, punctuation (8 distinct layers)
2. **POS tagging** — identifies nouns, verbs, adjectives, adverbs that can be substituted
3. **Synonym candidates** — fetches alternatives from WordNet, Datamuse, and wordfreq
4. **SBERT semantic filter** — keeps only candidates whose meaning is close enough to the original (adjustable threshold)
5. **Combined ranking** — scores by semantic similarity × word frequency
6. **Phoneme firewall** — drops any candidate that starts with the same sound you stutter on
7. **Inflection + rebuild** — morphologically inflects the chosen word and reassembles the sentence

You see a colour-coded risk map of your sentence, pick synonyms from dropdowns (or type your own), and get the final easier sentence with a before/after stutter-difficulty score.

---

## Features

- 🔐 **Multi-user auth** — Login / Register screen with per-user phoneme profiles stored in `users/`
- 🧠 **SBERT semantic firewall** — `all-MiniLM-L6-v2` ensures replacements never drift from the original meaning
- 🔊 **Phoneme-aware filtering** — uses the CMU Pronouncing Dictionary (ARPAbet) for onset detection, not spelling
- 🎯 **Stutter profile** — enter the sounds you block on (`str`, `pr`, `b`) and words to always avoid
- 📊 **Scoring transparency** — collapsible table showing semantic sim, frequency score, and gate status per candidate
- ✏️ **Custom word input** — override any suggestion with your own word
- 📝 **Grammar correction card** — shows every fix made to your input before synonym analysis
- 📈 **Difficulty meter** — sentence-level stutter difficulty score before and after substitution

---

## Project Structure

```
speech-ai/
│
├── app.py              # Streamlit UI — main application
├── auth.py             # Login / Register screen (guards the app)
├── user_store.py       # File-based user storage layer
│
├── grammar.py          # 8-layer grammar correction + SentenceRewriter
├── engine.py           # Multi-source synonym engine (WordNet + Datamuse)
├── phonetic.py         # ARPAbet onset extraction + stutter difficulty
├── semantic.py         # SBERT contextual re-ranking (sentence-transformers)
├── freq.py             # Zipf frequency wrapper (wordfreq)
├── paths.py            # Redirects NLTK / SBERT caches into .cache/
│
├── users/              # Per-user JSON files (gitignored)
│   └── default.json    # Auto-migrated from user_prefs.json on first run
│
├── CHANGES.md          # Full version history
└── README.md
```

---

## Setup

**Requirements:** Python 3.10+

```bash
# 1. Clone and enter the project
git clone https://github.com/your-username/speech-ai.git
cd speech-ai

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install streamlit nltk sentence-transformers pyinflect wordfreq requests

# 4. Run
streamlit run app.py
```

On first run, NLTK will download its required corpora (`cmudict`, `averaged_perceptron_tagger_eng`, `punkt_tab`, `wordnet`) and SBERT will download the `all-MiniLM-L6-v2` model (~80 MB). Both are cached locally in `.cache/` after that.

---

## First Login

A `default` account is automatically created from any existing `user_prefs.json`, or as an empty profile if this is a fresh install.

| Username | Password |
|----------|----------|
| `default` | `speech` |

To create your own account, click **Register** on the login screen.

---

## User Profile

Each user's data lives in `users/<username>.json`:

```json
{
  "username": "alice",
  "password_hash": "<sha256 hex>",
  "phoneme_profile": {
    "stutter_patterns": ["str", "pr", "b"],
    "blocked_words":    ["present", "statistics"]
  },
  "custom_replacements": {},
  "preferences": {}
}
```

**`stutter_patterns`** — the starting sounds you block on. Enter grapheme clusters like `str`, `pr`, `b`, `sp`. Speech AI converts these to ARPAbet onsets automatically, so spelling irregularities (`kn` → N, `ph` → F) are handled correctly.

**`blocked_words`** — specific words you always want replaced, regardless of their onset.

Changes made in the app are saved back to your profile in real time.

---

## The Phoneme Pipeline

Speech AI uses the **CMU Pronouncing Dictionary** to extract phoneme onsets, not spelling. This matters because:

- `"knight"` → onset `N` (not `K`)
- `"psychology"` → onset `S` (not `P`)
- `"school"` → onset `S K` (not `S C`)

If a word isn't in CMU, a grapheme-to-ARPAbet rule table covers common patterns (digraphs `sh`, `ch`, `th`, `ph`; silent clusters `kn`, `wr`, `ps`; and all single consonants).

Word difficulty is scored as:

```
difficulty = 0.4 × onset_cluster_length
           + 0.3 × syllable_count
           + 0.3 × rarity
```

Displayed in the UI as colour-coded chips: 🔴 high / 🟠 medium / 🟢 low risk.

---

## Semantic Threshold

The **Semantic threshold** slider (sidebar, default `0.85`) controls how strictly SBERT gates synonym candidates. A candidate must score above this cosine similarity to be accepted.

- **Higher (0.90+)** — only near-identical meanings pass. Fewer replacements offered.
- **Lower (0.70–0.80)** — broader synonyms pass. More options, slightly looser meaning.

If you're not seeing suggestions for some words, try lowering the threshold.

---

## Architecture Notes

### Storage layer (`user_store.py`)
The public API (`register_user`, `verify_user`, `load_profile`, `save_profile`) is intentionally thin. The file-based backend can be swapped for SQLite or PostgreSQL by replacing only the private `_read()` and `_write()` functions — nothing in `auth.py` or `app.py` changes.

Password hashing currently uses SHA-256. To upgrade to bcrypt:

```python
import bcrypt
def _hash_password(p):    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def _check_password(p, h): return bcrypt.checkpw(p.encode(), h.encode())
```

### Grammar correction layers (`grammar.py`)
`sanitize_input()` runs 8 sequential correction passes:
1. Contractions (`dont` → `don't`)
2. Informal words (`gonna` → `going to`)
3. Pronoun case (`i` → `I`)
4. Capitalisation
5. Spacing and punctuation normalisation
6. Tense correction (present verb + past time marker → past tense)
7. Subject-verb agreement (BE verbs, main verbs, negation, existential *there*)
8. Auxiliary form correction (`I am go` → `I am going`)

---

## .gitignore

```
users/
user_prefs.json
.cache/
venv/
__pycache__/
*.pyc
```

---

## Built With

| Library | Role |
|---------|------|
| [Streamlit](https://streamlit.io) | UI framework |
| [sentence-transformers](https://www.sbert.net) | SBERT semantic similarity (`all-MiniLM-L6-v2`) |
| [NLTK](https://www.nltk.org) | Tokenisation, POS tagging, WordNet, CMU dict |
| [pyinflect](https://github.com/bjascob/pyInflect) | Morphological inflection |
| [wordfreq](https://github.com/rspeer/wordfreq) | Zipf word frequency scores |
| [Datamuse API](https://www.datamuse.com/api/) | Additional synonym candidates |

---

## Academic Context

This project was developed at **NUST SEECS** (BS Data Science, cohort BSDS-02) as an independent research and software development project exploring:

- Phoneme-aware synonym substitution for stutter assistance
- Semantic integrity preservation via contextual SBERT re-ranking
- Accessible NLP tooling built on lightweight, offline-capable components

See `CHANGES.md` for the full development history.
