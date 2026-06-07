# Speech-AI 🔤

A **speech-fluency assistant** that reads text, identifies phonetically risky or hard-to-pronounce words, and replaces them with easier alternatives — while preserving meaning, tense, and grammatical correctness.

Built with **Python + Streamlit** (monorepo, single-process). No frontend framework required.

---

## What it does

1. You paste or type a sentence.
2. The system corrects grammar automatically (tense, subject-verb agreement, auxiliary forms, contractions, capitalisation).
3. It identifies substitutable content words (nouns, verbs, adjectives, adverbs).
4. It fetches synonym candidates from WordNet and Datamuse — filtered by the word's actual POS so verb synonyms never pollute noun lookups.
5. SBERT (`all-MiniLM-L6-v2`) scores every candidate sentence against the original and rejects anything that shifts meaning.
6. The best candidates are ranked by a combined score (65% semantic similarity + 35% word frequency).
7. **Phoneme firewall (stutter assistance):** enter the starting sounds you stutter on (e.g. `str, pr, b`). The app then only suggests replacements for words that *start* with those sounds, and never offers a synonym that starts with the same sound (replacing *present* with *prestige* is useless — both start /pr/). Onsets come from the CMU Pronouncing Dictionary, so spelling traps are handled correctly (`knee`→/n/, `school`→/sk/).
8. You pick your preferred synonym from a dropdown. The sentence rebuilds live with correct inflection, and a **before→after stutter-difficulty score** shows how much easier the sentence got.

---

## Project structure

```
speech-ai/
├── app.py          # Streamlit UI — rendering, session state, sidebar, stutter prefs
├── engine.py       # SynonymEngine — WordNet + Datamuse retrieval, POS-filtered
├── grammar.py      # sanitize_input() — grammar correction (base-form aux gate)
│                   # SentenceRewriter — POS-tag, protect phrases, Gate A/B, rewrite
├── semantic.py     # SBERT loader, protected phrases, batch cosine, combined score
├── phonetic.py     # CMU-onset extraction, pattern parsing, phoneme gates, difficulty
├── freq.py         # memory-safe wordfreq wrapper (auto-falls back to 'small' list)
├── paths.py        # keeps ALL caches (NLTK / SBERT / torch) off C:, on the app dir
├── tests/          # smoke.py (behaviour baseline) + app_test.py (headless UI smoke)
└── requirements.txt
```

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10 or higher |
| pip | any recent version |

No Node.js, no Java, no GPU. Runs entirely on CPU.

---

## Setup

### 1. Clone

```bash
git clone https://github.com/haqiqak/speech-ai.git
cd speech-ai
```

### 2. Create a virtual environment (recommended)

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (Command Prompt)
python -m venv .venv
.venv\Scripts\activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download NLTK data (one-time, runs automatically on first launch)

The app downloads these NLTK packages on first run: `averaged_perceptron_tagger_eng`, `punkt_tab`, `wordnet`, `omw-1.4`, `cmudict`. You need internet access for this step only.

### 5. Run

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

On first run, SBERT (`all-MiniLM-L6-v2`, ~80 MB) downloads automatically and is cached locally. Subsequent runs are fully offline.

> **Cache location:** `paths.py` automatically redirects NLTK data and the SBERT/torch
> model caches into a project-local `./.cache/` folder (kept out of git), and caps BLAS
> threads to keep startup memory low. Override any location with the standard env vars
> (`NLTK_DATA`, `HF_HOME`, `SENTENCE_TRANSFORMERS_HOME`, `TORCH_HOME`).

**Low-memory machines:** if `large` wordfreq or SBERT can't fit in RAM, the app degrades
gracefully — `freq.py` falls back to the small wordlist and the pipeline drops to
frequency-only ranking. Force low-memory mode up front with `WORDFREQ_LIST=small`.

---

## Usage

**Word mode** — type one or more comma-separated words (e.g. `happy, angry, stress`) to get a raw ranked synonym list.

**Sentence mode** — type or paste a full sentence. The pipeline runs automatically:

1. Grammar corrections are shown in card ①, with each fix explained.
2. Synonym candidates appear in card ②. The auto-selected best match is highlighted. Use the dropdowns to pick a different synonym for any word.
3. Card ③ shows a grammar check on the rewritten sentence.
4. Card ④ shows a highlighted diff (original → new words marked in orange).
5. Card ⑤ shows the final sentence ready to copy.

**Sidebar controls**

- **Stutter sounds** — comma/space separated starting sounds you stutter on (e.g. `str, pr, b`). Activates the phoneme firewall (Gate A targets only these words; Gate B keeps same-onset synonyms out). Saved to `user_prefs.json` so they persist between sessions.
- **Words to always avoid** — specific words you struggle with; always flagged risky and never suggested.
- Semantic threshold slider (0.60–0.95) — lower = more permissive substitutions, higher = stricter meaning preservation.
- Show scoring details toggle — reveals the full score table per word, including which candidates were rejected for sharing your stutter onset (`✗ onset`).

With stutter sounds active you also get a **Stutter Risk Map** (each word colour-coded by onset risk) and a **before→after difficulty score** on the final sentence.

---

## Configuration

No API keys required. Everything runs locally. A few optional environment variables:

| Variable | Effect |
|---|---|
| `WORDFREQ_LIST` | `best` (default) / `large` / `small`. Force `small` on low-RAM machines. |
| `DISABLE_DATAMUSE` | `1` = WordNet-only (offline / deterministic, skips the network source). |
| `NLTK_DATA`, `HF_HOME`, `SENTENCE_TRANSFORMERS_HOME`, `TORCH_HOME` | Override cache locations (default: `./.cache/`). |

The semantic threshold can also be changed in `semantic.py`:

```python
MIN_SEMANTIC = 0.72   # default — raise to 0.80 for strict mode
```

The score weighting can be changed in `semantic.py`:

```python
SEMANTIC_W = 0.65   # weight for SBERT cosine similarity
FREQUENCY_W = 0.35  # weight for word frequency (Zipf)
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'sentence_transformers'`**
```bash
pip install sentence-transformers
```

**SBERT shown as offline in the sidebar**
The model hasn't been downloaded yet, or the download failed. Connect to the internet and restart. The app works without SBERT (frequency-only fallback) but synonym quality is lower.

**Datamuse synonyms missing / slow**
Datamuse is a free public API. If it times out, WordNet candidates are still used. The timeout is 4 seconds per request.

**Wrong grammar corrections on valid text**
The grammar layer uses NLTK POS tagging, which can misparse unusual sentence structures. If a correction is wrong, it shows in card ① — you can see exactly what changed and why. Future versions will add a "revert correction" button.

---

## Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web UI |
| `nltk` | Tokenisation, POS tagging, WordNet access, lemmatisation |
| `sentence-transformers` | SBERT semantic similarity scoring |
| `wordfreq` | Zipf frequency scores for ranking |
| `pyinflect` | Morphological inflection (past tense, plurals, etc.) |
| `requests` | Datamuse API calls |
| `numpy` | Cosine similarity computation |
| `scikit-learn` | (available for future use) |

---


