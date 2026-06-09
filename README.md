# 🎙️ Speech AI

**An accessibility-focused speech assistance system for people who stutter.**

You type a sentence. Speech AI identifies words that fall on your personal trouble sounds, corrects grammar, and suggests semantically equivalent alternatives that are easier to pronounce — all in a clean, interactive Streamlit interface.

Built at **NUST SEECS** as independent research into AI-assisted communication accessibility.

---

## What It Does

Speech AI runs your sentence through a seven-stage pipeline:

1. **Grammar correction** — 8-layer rule-based pipeline (contractions, tense, subject-verb agreement, auxiliary forms, punctuation)
2. **POS tagging** — identifies nouns, verbs, adjectives, adverbs eligible for substitution
3. **Synonym candidates** — fetches alternatives from WordNet, Datamuse, and wordfreq
4. **SBERT semantic filter** — keeps only candidates whose meaning stays close to the original (adjustable threshold)
5. **Combined ranking** — scores by `0.65 × semantic similarity + 0.35 × word frequency`
6. **Phoneme firewall** — drops candidates that start with the same sound you stutter on (ARPAbet onset matching)
7. **Inflection + rebuild** — morphologically inflects the chosen word and reassembles the sentence

It also allows **Speech-to-text transcription** — converts spoken input into editable text.

You see a colour-coded risk map of your sentence, pick synonyms from dropdowns (or type your own), and get a final easier sentence with a before/after 
stutter-difficulty score.

---

## Features

- 🎤 **Voice Input (Speech-to-Text)** — dictate sentences directly instead of typing
- 🔊 **Voice Output (Text-to-Speech)** — listen to the final sentence with a single click
- 🔐 **Multi-user auth** — login/register with per-user phoneme profiles stored in `users/`
- 🧠 **SBERT semantic firewall** — `all-MiniLM-L6-v2` ensures replacements never drift from the original meaning
- 🔊 **Phoneme-aware filtering** — CMU Pronouncing Dictionary (ARPAbet) for onset detection, not spelling
- 🎯 **Stutter profile** — enter the sounds you block on (`str`, `pr`, `b`) and words to always avoid
- 📊 **Scoring transparency** — collapsible table showing semantic similarity, frequency score, and gate status per candidate
- ✏️ **Custom word input** — override any suggestion with your own word
- 📝 **Grammar correction card** — shows every fix made before synonym analysis
- 📈 **Difficulty meter** — sentence-level stutter difficulty score before and after substitution


---

## Project Structure

```
speech-ai/
│
├── app.py              # Streamlit UI — main application
├── auth.py             # Login / Register screen
├── user_store.py       # File-based user storage layer
│
├── grammar.py          # 8-layer grammar correction + SentenceRewriter
├── engine.py           # Multi-source synonym engine (WordNet + Datamuse) — v3
├── phonetic.py         # ARPAbet onset extraction + stutter difficulty scoring
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
git clone https://github.com/haqiqak/speech-ai.git
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

On first run, NLTK downloads `cmudict`, `averaged_perceptron_tagger_eng`, `punkt_tab`, and `wordnet`. SBERT downloads `all-MiniLM-L6-v2` (~80 MB). Both are cached in `.cache/` after that.

**No external API keys required. Runs fully offline after first model download.**

---

## First Login

A `default` account is automatically created from any existing `user_prefs.json`, or as an empty profile on a fresh install.

| Username | Password |
|----------|----------|
| `default` | `speech` |

Click **Register** on the login screen to create your own account.

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

- **`stutter_patterns`** — starting sounds you block on. Enter grapheme clusters like `str`, `pr`, `b`, `sp`. Speech AI converts these to ARPAbet onsets automatically, so spelling irregularities (`kn` → N, `ph` → F) are handled correctly.
- **`blocked_words`** — specific words to always replace, regardless of their onset.

Changes made in the app are saved back to your profile in real time.

---

## The Phoneme Pipeline

Speech AI uses the **CMU Pronouncing Dictionary** to extract phoneme onsets from pronunciation, not spelling:

| Word | Onset (not spelling) |
|------|----------------------|
| `knight` | N |
| `psychology` | S |
| `school` | S K |

If a word isn't in CMU, a grapheme-to-ARPAbet rule table covers common patterns (digraphs `sh`, `ch`, `th`, `ph`; silent clusters `kn`, `wr`, `ps`; all single consonants).

Word difficulty is scored as:

```
difficulty = 0.4 × onset_cluster_length
           + 0.3 × syllable_count
           + 0.3 × rarity
```

Displayed in the UI as colour-coded chips: 🔴 high / 🟠 medium / 🟢 low risk.

---

## Semantic Threshold

The **Semantic threshold** slider (sidebar, default `0.85`) controls how strictly SBERT gates synonym candidates. A candidate must score above this cosine similarity to pass.

| Range | Effect |
|-------|--------|
| 0.90+ | Only near-identical meanings pass. Fewer replacements. |
| 0.70–0.80 | Broader synonyms pass. More options, slightly looser meaning. |

If you're not seeing suggestions for some words, try lowering the threshold.

---

## Architecture Notes

### Grammar correction (`grammar.py`)

`sanitize_input()` runs 8 sequential correction passes before synonym substitution:

| Layer | What it fixes | Example |
|-------|---------------|---------|
| 1a | Contractions | `dont` → `don't` |
| 1b | Informal words | `gonna` → `going to` |
| 2 | Pronoun case | `i` → `I` |
| 3 | Sentence capitalisation | `the cat...` → `The cat...` |
| 4 | Extra spaces | `word  word` → `word word` |
| 5 | Auxiliary verb form | `I am go` → `I am going` |
| 6 | Tense correction | `I eat yesterday` → `I ate yesterday` |
| 7 | Subject-verb agreement | `He go` → `He goes` |
| 8 | Punctuation | adds trailing `.` if missing |

### Synonym engine (`engine.py` — v3)

Retrieves candidates from WordNet (POS-filtered) and Datamuse (`rel_syn=` + `ml=` endpoints), then ranks by Zipf frequency. Key fix in v3: WordNet hypernym traversal is gated by POS to prevent cross-POS contamination (e.g. `stress` as a noun no longer pulls in verb hypernyms like `say` or `pronounce`).

### SBERT firewall (`semantic.py`)

For each candidate, builds a candidate sentence, batch-encodes it alongside the original, and computes cosine similarity. Protected phrases (33 multi-word fixed expressions like `look forward to`, `in order to`, `as well as`) are never substituted. Falls back gracefully to frequency-only ranking if SBERT fails to load.

### Storage layer (`user_store.py`)

The public API (`register_user`, `verify_user`, `load_profile`, `save_profile`) is intentionally thin. The file-based backend can be swapped for SQLite or PostgreSQL by replacing only the private `_read()` and `_write()` functions — nothing in `auth.py` or `app.py` changes.

To upgrade password hashing from SHA-256 to bcrypt:

```python
import bcrypt
def _hash_password(p):     return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def _check_password(p, h): return bcrypt.checkpw(p.encode(), h.encode())
```

---

## Voice Accessibility

Speech AI supports both directions of spoken communication.

### Speech-to-Text

Users can click **Start Speaking** and dictate their sentence directly into the application. The transcribed text appears in the editor for review and further processing.

### Text-to-Speech

After grammar correction and synonym substitution, users can optionally click **Speak Output** to hear the final sentence read aloud.

This makes the system useful for users who:

- Prefer speaking over typing
- Want to verify pronunciation before speaking
- Need audio feedback while practicing communication
- Benefit from multimodal accessibility support

## Known Limitations

- Grammar correction depends on NLTK POS tagging, which can misfire on very short or broken sentences.
- Datamuse `ml=` results are not guaranteed to match POS; SBERT acts as the final filter for these.
- Protected phrases are hard-coded (33 total); idiomatic coverage is incomplete.
- No memory between sessions — closing the browser loses all choices.
- Subject-verb agreement detection looks left for the nearest subject, which fails in relative clauses.
- Grammar correction runs before synonym substitution; a corrected form may shift the target lemma.

---

## Roadmap

**Near-term (high impact)**
- Datamuse POS filtering — explicitly gate `ml=` results through WordNet POS check
- Revert button — undo individual grammar fixes from the correction card
- Sentence-level phoneme scoring — before/after comparison of full sentence difficulty

**Medium-term**
- Multi-sentence input — split, process, and rejoin on `.!?`
- User blocklist/allowlist — persistent per-user word overrides
- Export / copy button — one-click copy of the final sentence

**Longer-term**
- Optional LLM re-ranking layer (Gemini / local Ollama) for naturalness scoring
- Live speech input via `streamlit-webrtc` + Whisper transcription
- Fine-tune SBERT on speech-fluency sentence pairs

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

## Academic Context

Developed at **NUST SEECS** as an independent research project exploring phoneme-aware synonym substitution for stutter assistance, semantic integrity preservation via SBERT re-ranking, and accessible NLP tooling built on lightweight, offline-capable components.

See `CHANGES.md` for the full development history.
