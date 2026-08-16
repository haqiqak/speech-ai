# 🎙️ Speech AI — Text Reformulation Module

**An accessibility-focused speech assistance system for people who stutter.**

---

## The Speech-AI project

Speech-AI, as a whole, is meant to work as a pipeline:

```
Speaker audio
   → ASR transcription + acoustic/voice disfluency analysis   (Audio Module)
   → identified problematic phonemes / words
   → text reformulation                                        (this repository)
   → an alternative formulation that is easier for that speaker to say,
     with meaning and context preserved
```

**This repository is not the whole system.** It implements only the
**text reformulation ("word") module** — the second half of that pipeline.
Everything upstream of "already-transcribed text plus problem-word
information" (recording audio, running ASR, analyzing acoustic disfluency
signals such as blocks/prolongations/repetitions from the waveform itself)
belongs to a separate **Audio Module** and is out of scope here. See
[`out_of_scope/README.md`](out_of_scope/README.md) for code that used to live
in this repo but belongs to that boundary instead.

## This repository: the text reformulation module

**Input:** transcribed or typed text, plus problematic phoneme/word
information for the speaker (either typed in directly — "the sounds I block
on" — or, in the full system, supplied by the Audio Module's disfluency
detection).

**Output:** an alternative formulation of that text — same meaning, same
context, same speaker intent — chosen to be easier for *that specific
speaker* to say.

**What it does NOT do:** record or process audio, run speech recognition,
extract acoustic features, or detect disfluencies from a waveform. It treats
"what's difficult for this speaker" as an input it consumes, not something it
derives from sound.

You type (or paste in) a sentence or paragraph. Speech AI identifies words
that fall on the speaker's personal trouble sounds, corrects grammar, and
suggests semantically equivalent alternatives that are easier to pronounce —
all in a clean, interactive Streamlit interface.

Built at **NUST SEECS** as independent research into AI-assisted
communication accessibility.

---

## What It Does

Speech AI runs your sentence through a seven-stage pipeline:

1. **Grammar correction** — multi-layer rule-based pipeline (spelling, contractions, tense, subject-verb agreement, auxiliary forms, article agreement, punctuation)
2. **POS tagging** — identifies nouns, verbs, adjectives, adverbs eligible for substitution
3. **Synonym candidates** — fetches alternatives from WordNet, Datamuse, and wordfreq
4. **SBERT semantic filter** — keeps only candidates whose meaning stays close to the original (adjustable threshold, default `0.85`)
5. **Combined ranking** — scores by `0.90 × semantic similarity + 0.10 × log-normalized word frequency` (semantic similarity is the primary gate; frequency only breaks ties among candidates that already passed it — see `semantic.py`)
6. **Phoneme firewall** — drops candidates that start with the same sound you stutter on (ARPAbet onset matching)
7. **Inflection + rebuild** — morphologically inflects the chosen word and reassembles the sentence

A second, parallel implementation adds a **profile-aware soft rewrite layer**
(`rewrite/`): it learns a persistent, multi-factor difficulty profile per
speaker (onset risk, syllable length, word frequency, grammatical class),
seeded from self-report and updated over time, then ranks alternatives by
`similarity − λ·difficulty + μ·frequency` instead of hard-blocking onsets.
The two pipelines are independently implemented and not yet compared against
each other — see `DECISION_LOG.md` / `ROADMAP.md` R5.

An optional third layer (`rephrase.py`) proposes a smoother full-sentence
paraphrase (T5) on top of either pipeline's output.

You see a colour-coded risk map of your sentence, pick synonyms from
dropdowns (or type your own), and get a final easier sentence with a
before/after stutter-difficulty score.

---

## Features

- 🔐 **Multi-user auth** — login/register with per-user phoneme profiles stored in `users/`
- 🧠 **SBERT semantic firewall** — `all-MiniLM-L6-v2` ensures replacements never drift from the original meaning
- 🔊 **Phoneme-aware filtering** — CMU Pronouncing Dictionary (ARPAbet) for onset detection, not spelling
- 🎯 **Speaker Difficulty Profile** — persistent, per-user record of difficult sounds, words, and phrases (each declared and tracked separately — see `PROBLEM_FORMULATION.md`), editable from a dedicated panel or by picking a word straight out of your entered text
- 📊 **Scoring transparency** — collapsible table showing semantic similarity, frequency score, and gate status per candidate
- ✏️ **Custom word input** — override any suggestion with your own word
- 📝 **Grammar correction card** — shows every fix made before synonym analysis
- 📈 **Difficulty meter** — sentence-level stutter difficulty score before and after substitution
- **Multi-factor fluency profile** — onset risk, syllable length, word frequency, and grammatical class with EWMA session updates
- **Profile-aware rewrite card** — per-change accept/reject controls with transparent difficulty and similarity details
- ✨ **Fluency rephrase (beta)** — optional T5 paraphrase pass (`rephrase.py`) that proposes a smoother full-sentence rewrite which avoids your blocked words/onsets while preserving meaning. Loads lazily on first use; degrades to passthrough if the model/stack is unavailable
- **Research harness** — automatic metrics, lambda trade-off sweeps, profile AUC evaluation, and study CSV scaffolding

*(Voice input/output and microphone-based profile updates were part of this
repo in earlier versions; they've moved to [`out_of_scope/`](out_of_scope/)
as audio-module functionality — see below.)*

---

## Project Structure

```
speech-ai/
│
├── app.py              # Streamlit UI — main application (text in, reformulated text out)
├── auth.py             # Login / Register screen
├── user_store.py       # File-based user storage layer
│
├── grammar.py          # Grammar correction + SentenceRewriter (the "hard" onset-gated pipeline)
├── engine.py            # Multi-source synonym engine (WordNet + Datamuse) — v3
├── phonetic.py          # ARPAbet onset extraction + stutter difficulty scoring
├── semantic.py          # SBERT contextual re-ranking (sentence-transformers)
├── freq.py              # Zipf frequency wrapper (wordfreq)
├── paths.py             # Redirects NLTK / SBERT caches into .cache/
├── rephrase.py          # Optional T5 fluency-rephrase layer
├── config.yaml          # Profiling, rewrite, and eval knobs
│
├── profiling/           # Speaker difficulty profile: profile.py, coldstart.py, config.py
├── rewrite/              # Soft-constraint profile-aware rewrite engine (the "soft" pipeline)
├── eval/                # Automatic metrics and user-study harness
│
├── users/               # Per-user JSON files
│   └── default.json     # Auto-migrated from user_prefs.json on first run
│
├── out_of_scope/        # Archived audio/ASR/voice code — see out_of_scope/README.md
│
├── tests/                # Regression + smoke tests for the text-reformulation pipeline
├── scripts/              # Offline dataset-building / fine-tuning scaffolding for rephrase.py
│
├── CLAUDE.md, HANDOFF.md, DOCS.md, DECISION_LOG.md,
├── VALIDATION.md, ROADMAP.md, CHANGELOG.md   # Living documentation set — see below
├── changes.md            # Full narrative version history
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
pip install -r requirements.txt

# 4. Run
streamlit run app.py
```

On first run, NLTK downloads `cmudict`, `averaged_perceptron_tagger_eng`, `punkt_tab`, and `wordnet`. SBERT downloads `all-MiniLM-L6-v2` (~80 MB). Everything is cached under the project-local `.cache/` (NLTK, HuggingFace, torch, and the LanguageTool JAR are all redirected there by `paths.py` — nothing is written to your home/system cache).

**No external API keys required. Runs fully offline after first model download.**

### Optional models (downloaded lazily, only when you use the feature)

| Feature | Model | Size | When it downloads |
|---------|-------|------|-------------------|
| Fluency rephrase (beta) | `Vamsi/T5_Paraphrase_Paws` | ~890 MB | First time you run a rephrase with the toggle on |
| Grammar deep-check | LanguageTool JAR | ~200 MB | First grammar correction (needs Java 8+) |

If a model can't be downloaded or loaded, the app degrades gracefully — rephrase falls back to passthrough. Neither is required for the core synonym pipeline.

### Memory note (important for low-RAM machines)

`accelerate` is in `requirements.txt` and is **required** for loading the transformer model on machines with limited RAM. Without it, `from_pretrained` does a transient double allocation of the weights that can crash (segfault) on tight memory. The rephrase model (~220 M params) loads comfortably with a few GB free.

On a tight-RAM machine, run the app from a **plain terminal** (not inside an IDE) to free ~1 GB. A convenience launcher is included:

```powershell
# Windows — close your IDE first, then from any PowerShell window:
L:\speech-ai\run_app.ps1
```

---

## First Login

A `default` account is automatically created from any existing `user_prefs.json`, or as an empty profile on a fresh install.

| Username | Password |
|----------|----------|
| `default` | `speech` |

Click **Register** on the login screen to create your own account.

---

## User Profile

Each user's data lives in `users/<username>.json`. As of the Stage 4A
foundation, the canonical, structured record of what's difficult for a
speaker is `difficulty_profile` — three independent lists (`sounds`,
`words`, `phrases`), each entry carrying its source, when it was added, and
(for words) a best-effort derived pronunciation. `phoneme_profile` still
exists alongside it as an auto-derived, always-in-sync mirror — it's what
the existing reformulation pipeline (`grammar.py`, `rewrite/`) reads, and
you never edit it directly:

```json
{
  "username": "alice",
  "password_hash": "<sha256 hex>",
  "phoneme_profile": {
    "stutter_patterns": ["str", "pr"],
    "blocked_words":    ["particular"]
  },
  "difficulty_profile": {
    "sounds":  [{"value": "str", "normalized": "S T R", "source": "user_typed", "added_at": "...", "meta": {}}],
    "words":   [{"value": "particular", "normalized": "particular", "source": "user_typed", "pronunciation": ["P","ER","T","IH","K","Y","AH","L","ER"], "added_at": "...", "meta": {}}],
    "phrases": []
  },
  "custom_replacements": {},
  "preferences": {}
}
```

- **`difficulty_profile.sounds`** — starting sounds you block on. Enter
  grapheme clusters like `str`, `pr`, `b`, `sp`; Speech AI converts these to
  ARPAbet onsets automatically (pronunciation, not spelling — `c` and `k`
  dedup as the same sound), so spelling irregularities (`kn` → N, `ph` → F)
  are handled correctly.
- **`difficulty_profile.words`** — specific words difficult for you,
  independent of whether their sounds are separately flagged.
- **`difficulty_profile.phrases`** — multi-word phrases difficult as a
  whole; not yet consumed by the reformulation pipeline (see
  `PROBLEM_FORMULATION.md`).

See `PROBLEM_FORMULATION.md` for the full schema rationale, the ARPAbet-vs-IPA
and JSON-vs-SQLite research behind these choices, and why word difficulty
and sound difficulty are deliberately never conflated.

Changes made in the app are saved back to your profile in real time.

The longitudinal fluency profile is stored separately as `users/<username>.fluency_profile.json` at runtime.

---

## The Phoneme Pipeline

Speech AI uses the **CMU Pronouncing Dictionary** to extract phoneme onsets from pronunciation, not spelling:

| Word | Onset (not spelling) |
|------|----------------------|
| `knight` | N |
| `psychology` | S |
| `school` | S K |

If a word isn't in CMU, a grapheme-to-ARPAbet rule table covers common patterns (digraphs `sh`, `ch`, `th`, `ph`; silent clusters `kn`, `wr`, `ps`; all single consonants).

Word difficulty (`phonetic.word_difficulty()`) is scored as:

```
difficulty = 0.4 × onset_cluster_length
           + 0.3 × syllable_count
           + 0.3 × rarity
           (+ 0.15 plosive/affricate bonus)
```

Displayed in the UI as colour-coded chips: 🔴 high / 🟠 medium / 🟢 low risk.

These coefficients are hand-picked engineering defaults, not fitted against
real speaker data — see `VALIDATION.md` for the honest status of this and the
profile's own (differently-weighted) difficulty formula.

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

`sanitize_input()` runs multiple sequential correction passes before synonym substitution: spelling, contractions, informal words, pronoun case, sentence capitalisation, spacing, article agreement, auxiliary verb forms, tense correction, subject-verb agreement (BE and main verbs), negation agreement, existential-there agreement, punctuation, and an optional LanguageTool deep-check.

### Synonym engine (`engine.py` — v3)

Retrieves candidates from WordNet (POS-filtered) and Datamuse (`rel_syn=` + `ml=` endpoints), then ranks by Zipf frequency. Key fix in v3: WordNet hypernym traversal is gated by POS to prevent cross-POS contamination (e.g. `stress` as a noun no longer pulls in verb hypernyms like `say` or `pronounce`).

### SBERT firewall (`semantic.py`)

For each candidate, builds a candidate sentence, batch-encodes it alongside the original, and computes cosine similarity. Protected phrases (multi-word fixed expressions like `look forward to`, `in order to`, `as well as`) are never substituted. Falls back gracefully to frequency-only ranking if SBERT fails to load.

### Speaker difficulty profile (`profiling/`)

`profiling/profile.py` stores a per-speaker, multi-factor word-difficulty model (onset risk, syllable length, frequency, grammatical class), seeded by self-report and population priors (`profiling/coldstart.py`), then updated with EWMA session events. The profile's `update()` method accepts a list of disfluency events — in the full Speech-AI system, those events come from the Audio Module; in this repo, the profile is currently seeded purely from the user's typed self-report.

### Profile-aware rewrite (`rewrite/`)

`rewrite/rewriter.py` proposes meaning-preserving substitutions using the score `similarity - lambda * difficulty + mu * frequency`. Protected words and the user's always-keep list are never replaced, and the Streamlit card lets each proposed change be accepted or rejected.

### Fluency rephrase (`rephrase.py`)

A standalone, optional layer that proposes a smoother full-sentence rewrite. It generates paraphrase candidates with a T5 model (`Vamsi/T5_Paraphrase_Paws`), blocks the user's trouble words via `bad_words_ids`, then scores each candidate by `w_sim·similarity − w_diff·difficulty − w_viol·violations − w_edit·edit-distance` and keeps the best one that clears a semantic-similarity gate. It is never imported by `grammar.py` or `engine.py`, loads the model lazily on first use (with `low_cpu_mem_usage=True` so it fits on low-RAM machines), and degrades to returning the input sentence unchanged if the stack or weights are unavailable.

### Evaluation harness (`eval/`)

`eval/metrics.py` computes meaning preservation, difficulty-onset reduction, substitution rate, and lambda trade-offs. `eval/profile_eval.py` compares self-report-only, observed-only, and fused profile AUC. `eval/study/` contains CSV helpers for a counterbalanced three-condition **human** study comparing reformulated-text conditions — no audio involved, it's about how readers/listeners judge the *text* output.

### Storage layer (`user_store.py`)

The public API (`register_user`, `verify_user`, `load_profile`, `save_profile`) is intentionally thin. The file-based backend can be swapped for SQLite or PostgreSQL by replacing only the private `_read()` and `_write()` functions — nothing in `auth.py` or `app.py` changes.

To upgrade password hashing from SHA-256 to bcrypt:

```python
import bcrypt
def _hash_password(p):     return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def _check_password(p, h): return bcrypt.checkpw(p.encode(), h.encode())
```

---

## Out of scope for this repository

Audio recording, speech recognition (ASR), acoustic feature extraction, voice
I/O, and audio-based disfluency detection are **not** implemented here — they
belong to the Audio Module, a separate part of the Speech-AI system. Code
that used to live in this repo for those concerns (a CrisperWhisper ASR
wrapper, a rule-based detector over ASR word timings, and a browser
Speech-to-Text/Text-to-Speech UI layer) has been moved to
[`out_of_scope/`](out_of_scope/), preserved as-is for reference rather than
deleted. See [`out_of_scope/README.md`](out_of_scope/README.md) for details
and [`changes.md`](changes.md) / [`DECISION_LOG.md`](DECISION_LOG.md) for the
history of how it got there.

## Known Limitations

*(of the text reformulation module specifically)*

- Grammar correction depends on NLTK POS tagging, which can misfire on very short or broken sentences.
- Datamuse `ml=` results are not guaranteed to match POS; SBERT acts as the final filter for these.
- Protected phrases are hard-coded (~35 total); idiomatic coverage is incomplete.
- UI choices are session-local, while fluency profiles persist per user.
- Subject-verb agreement detection looks left for the nearest subject, which fails in relative clauses.
- Grammar correction runs before synonym substitution; a corrected form may shift the target lemma.
- The two rewrite pipelines (`grammar.py`'s hard onset gate and `rewrite/`'s soft difficulty penalty) duplicate logic and have not been compared against each other.
- The difficulty formulas and semantic threshold are hand-picked, not validated against real speaker data or human judgment — see `VALIDATION.md`.

---

## Documentation set

This README covers the product surface. For methodology, architecture
rationale, decision history, and evaluation status, see the living
documentation set at the repo root:

| File | What it's for |
|---|---|
| `CLAUDE.md` | Orientation — where to start, standing rules |
| `HANDOFF.md` | What's proven vs. hypothesis, how to run things, known pitfalls |
| `DOCS.md` | One line per file — what it's for, drift status |
| `DECISION_LOG.md` | Append-only record of why things are the way they are |
| `VALIDATION.md` | What has actually been measured, and its named limitations |
| `ROADMAP.md` | What's next, and the finding/gap that justifies each item |
| `CHANGELOG.md` | Fast-scan index into the decision log |
| `changes.md` | Full narrative version history (pre-dates the living doc set) |

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
| [transformers](https://github.com/huggingface/transformers) + [torch](https://pytorch.org) + [accelerate](https://github.com/huggingface/accelerate) | T5 fluency rephrase, low-memory model loading |
| [language-tool-python](https://github.com/jxmorris12/language_tool_python) | Optional grammar deep-check (requires Java) |

---

## .gitignore

```
users/*.fluency_profile.json
user_prefs.json
.cache/
venv/
__pycache__/
*.pyc
```

---

## Academic Context

Developed at **NUST SEECS** as an independent research project exploring phoneme-aware synonym substitution for stutter assistance, semantic integrity preservation via SBERT re-ranking, and accessible NLP tooling built on lightweight, offline-capable components.

See `changes.md` for the full development history and `DECISION_LOG.md` for why specific choices were made.
