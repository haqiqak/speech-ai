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

Speech AI is built around one linear workflow:

```
enter/paste text → view & edit your difficulty profile → Reformulate →
review proposed changes → keep/revert each one → final text
```

The reformulation engine (`reformulate.py`, Architecture D′ —
`REFORMULATION_RESEARCH.md` §24–31) that runs on "Reformulate":

1. **Tag** — find which words/sounds in your text match your declared difficulty profile (a global sound, a flagged word, or a word-specific sound pattern).
2. **Substitute-and-rank** — for a sentence with a manageable number of flagged spots, try a same-meaning replacement for each: WordNet/Datamuse candidates, ranked by SBERT semantic similarity, filtered through a WordNet antonym guard and the phoneme firewall. All-or-nothing per sentence — if any flagged word can't be safely replaced, the whole sentence escalates rather than shipping a half-fixed patchwork.
3. **Escalate to restructuring** — when a sentence has too many flagged spots to patch word-by-word (or word-by-word substitution couldn't clear every gate), a T5 model (`rephrase.py`) proposes a reworded sentence instead, which is re-checked with the same semantic and phoneme gates plus a negation-consistency check.
4. **Verify** — the actual output is re-scanned against your profile to confirm it improved, not just assumed to have.
5. **Report** — meaning preservation, difficulty reduction, and how much text changed are reported as separate numbers, never blended into one score, alongside anything left unchanged and why.

You review every change in a compact list — each one shows what triggered it and its verification details — and can revert any individual change back to the original wording before copying the final text.

---

## Features

- 🧠 **SBERT semantic firewall** — `all-MiniLM-L6-v2` ensures replacements never drift from the original meaning, plus a WordNet antonym guard and a negation-consistency check for full-sentence rewrites
- 🔊 **Phoneme-aware filtering** — CMU Pronouncing Dictionary (ARPAbet) for onset detection, not spelling
- 🎯 **Speaker Difficulty Profile** — one persistent, default speaker profile (no login) recording difficult sounds, words, and phrases, each declared and tracked separately; editable from a dedicated panel or by picking a word straight out of your entered text — see `PROBLEM_FORMULATION.md`
- 🔍 **Word-specific sound patterns** — optionally narrow a difficult word down to the exact sound(s) that make it hard (e.g. "three" → specifically the TH→R transition) without assuming every occurrence of that sound elsewhere is difficult too
- 🔁 **Restructuring escalation** — when word-level substitution can't safely fix a sentence, a T5 paraphrase pass proposes a reworded sentence instead, generate-then-verify against the same gates
- ✅ **Change review with keep/revert** — every proposed change is shown with why it was made and its verification details; revert any single one back to the original wording
- 📈 **Separate, honest metrics** — meaning preservation, difficulty reduction, and amount of text changed reported as distinct numbers, not combined into one score
- ⚠️ **Explicit "left unchanged" reporting** — if nothing can be safely changed, that's shown, not silently guessed at

*(Voice input/output and microphone-based profile updates were part of this
repo in earlier versions; they've moved to [`out_of_scope/`](out_of_scope/)
as audio-module functionality — see below. The older dual-pipeline UI —
word-picker dropdowns, a profile-rewrite card and a separate rephrase-toggle
card, an allowlist panel, a "learned" onset-risk chart — was replaced by the
workflow above; `grammar.py::SentenceRewriter` and
`rewrite/rewriter.py::DifficultyAwareRewriter` remain in the repo for
comparison but are no longer called from `app.py` — see `DECISION_LOG.md`
2026-08-16-E.)*

---

## Project Structure

```
speech-ai/
│
├── app.py              # Streamlit UI (v8) — text → profile → Reformulate → review workflow
├── reformulate.py       # The live reformulation engine (Architecture D′) — app.py's only entry point
├── naturalness.py       # "Naturalness of intervention" edit-ratio metric, used by reformulate.py
├── difficulty_profile.py  # Speaker Difficulty Profile: sounds/words/phrases + word-specific patterns
├── profile_store.py     # Single default-profile storage (no accounts/login)
│
├── grammar.py          # Grammar correction (still live, called by app.py) + SentenceRewriter
│                        #   (retained for comparison, no longer called by app.py)
├── engine.py            # Multi-source synonym engine (WordNet + Datamuse) — used by reformulate.py
├── phonetic.py          # ARPAbet onset extraction + stutter difficulty scoring + friendly phone labels
├── semantic.py          # SBERT contextual re-ranking + antonym/negation checks (sentence-transformers)
├── freq.py              # Zipf frequency wrapper (wordfreq)
├── paths.py             # Redirects NLTK / SBERT caches into .cache/
├── rephrase.py          # T5 layer — reformulate.py's restructuring-escalation step
├── config.yaml          # Profiling, rewrite, and eval knobs (consumed by the retained rewrite/ path)
│
├── profiling/           # Longitudinal learned difficulty model — retained, only used by rewrite/
├── rewrite/              # Soft-constraint profile-aware rewrite engine — retained for comparison,
│                        #   no longer called by app.py
├── eval/                # Automatic metrics and user-study harness (for the retained rewrite/ path)
│
├── users/               # Per-profile JSON (directory name predates the removed multi-user
│   └── default.json     #   system — see PROBLEM_FORMULATION.md §5.3 for why it wasn't renamed)
│
├── out_of_scope/        # Archived audio/ASR/voice code — see out_of_scope/README.md
│
├── tests/                # Regression + smoke tests for the text-reformulation pipeline
├── scripts/              # Offline dataset-building / fine-tuning scaffolding for rephrase.py
│
├── CLAUDE.md, HANDOFF.md, DOCS.md, DECISION_LOG.md, VALIDATION.md,
├── RESEARCH.md, PROBLEM_FORMULATION.md, REFORMULATION_RESEARCH.md,
├── ROADMAP.md, CHANGELOG.md   # Living documentation set
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
| Restructuring escalation | `Vamsi/T5_Paraphrase_Paws` | ~890 MB | First time `reformulate.py` needs to restructure a sentence |
| Grammar deep-check | LanguageTool JAR | ~200 MB | First grammar correction (needs Java 8+) |

If a model can't be downloaded or loaded, the app degrades gracefully — restructuring escalation is skipped (that sentence is reported as left unchanged, not silently guessed at) and grammar correction still runs its other layers. Neither is required for word-level substitution.

### Memory note (important for low-RAM machines)

`accelerate` is in `requirements.txt` and is **required** for loading the T5 restructuring model (`rephrase.py`, used by `reformulate.py`'s escalation step) on machines with limited RAM. Without it, `from_pretrained` does a transient double allocation of the weights that can crash (segfault) on tight memory. The model (~220 M params) loads comfortably with a few GB free.

On a tight-RAM machine, running the app from a plain terminal (not inside an IDE) frees up some RAM.

---

## No login — one default speaker profile

Speech AI opens directly into a single, persistent default profile — no
account, no password, no registration screen. This is a deliberate
simplification for development/testing (removed 2026-08-16; see
`DECISION_LOG.md` 2026-08-16-A and `PROBLEM_FORMULATION.md` §5), not an
accident: the previous multi-user login layer is gone, but the storage API
underneath (`profile_store.py`) still takes a profile-name parameter
everywhere, so reintroducing multiple named profiles later doesn't require
a data-model change — just UI.

---

## Speaker Difficulty Profile

The default profile's data lives in `users/default.json`. The canonical
record of what's difficult for the speaker is `difficulty_profile` — three
independent lists (`sounds`, `words`, `phrases`), each entry carrying its
source and when it was added. Word entries additionally carry a best-effort
derived pronunciation and, optionally, a **word-specific pattern** —
exactly which sound(s) within that one word are the actual problem,
distinct from a claim that those sounds are difficult everywhere:

```json
{
  "profile_name": "default",
  "difficulty_profile": {
    "sounds":  [{"value": "str", "normalized": "S T R", "source": "user_typed", "added_at": "...", "meta": {}}],
    "words":   [
      {"value": "particular", "normalized": "particular", "source": "user_typed",
       "pronunciation": ["P","ER","T","IH","K","Y","AH","L","ER"], "problem_phones": null, "added_at": "...", "meta": {}},
      {"value": "three", "normalized": "three", "source": "user_selected_from_text",
       "pronunciation": ["TH","R","IY"], "problem_phones": ["TH","R"], "added_at": "...", "meta": {}}
    ],
    "phrases": []
  }
}
```

- **`difficulty_profile.sounds`** — starting sounds you block on, **always
  and everywhere**. Enter grapheme clusters like `str`, `pr`, `b`, `sp`;
  Speech AI converts these to ARPAbet onsets automatically (pronunciation,
  not spelling — `c` and `k` dedup as the same sound).
- **`difficulty_profile.words`** — specific words difficult for you,
  independent of whether their sounds are separately flagged. Click 🔍 next
  to a flagged word to optionally narrow it down to a specific
  `problem_phones` pattern within that word — shown as friendly labels
  (e.g. "TH (as in 'think')"), never raw phonetic notation, and **never
  automatically added to the global `sounds` list** unless you explicitly
  check "Also add ... as a GLOBAL difficulty." `reformulate.py` reads
  `problem_phones` as a trigger reason for that one word.
- **`difficulty_profile.phrases`** — multi-word phrases difficult as a
  whole; declared and editable in the UI, but still not consumed by
  `reformulate.py` — phrase-level matching needs a different detection
  mechanism than the current word-substitution/sentence-restructuring
  model supports (`ROADMAP.md` R13).

See `PROBLEM_FORMULATION.md` for the full schema rationale, the ARPAbet-vs-IPA,
respelling, and JSON-vs-SQLite research behind these choices, and why word
difficulty, word-specific sound patterns, and global sound difficulty are
deliberately never conflated with each other.

Changes made in the app are saved back to the profile in real time.

The longitudinal, learned fluency profile (a separate, older system —
onset risk scored continuously from observed sessions rather than declared
by the user) is stored separately as `users/default.fluency_profile.json`.

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

## Meaning-Preservation Strictness

Under **Advanced** in the sidebar, the **meaning-preservation strictness**
slider (default `0.85`) controls how strictly SBERT gates both word-level
substitutions and full-sentence restructurings. A candidate must score
above this cosine similarity to pass.

| Range | Effect |
|-------|--------|
| 0.90+ | Only near-identical meanings pass. Fewer changes. |
| 0.70–0.80 | Broader rewrites pass. More changes, slightly looser meaning. |

If Reformulate is leaving more unchanged than expected, try lowering this.

---

## Architecture Notes

### The reformulation engine (`reformulate.py`) — app.py's only entry point

Architecture D′ (`REFORMULATION_RESEARCH.md` §24–31): tag flagged words →
per-sentence escalation decision → all-or-nothing substitute-and-rank
(antonym check → SBERT → phoneme veto) → T5 restructuring escalation
(generate-then-verify) → re-verify the actual output → separately-reported
metrics. Built on top of the library modules below rather than
reimplementing candidate generation or scoring — see `DECISION_LOG.md`
2026-08-16-E for the full build record, including two bugs found and fixed
via live testing.

### Grammar correction (`grammar.py`)

`sanitize_input()` — called by `app.py` before every reformulation — runs multiple sequential correction passes: spelling, contractions, informal words, pronoun case, sentence capitalisation, spacing, article agreement, auxiliary verb forms, tense correction, subject-verb agreement (BE and main verbs), negation agreement, existential-there agreement, punctuation, and an optional LanguageTool deep-check.

`grammar.py` also contains `SentenceRewriter`, the original hard onset-gated substitution pipeline. **Retained for comparison, not called by `app.py`** — `reformulate.py` reuses its lower-level helpers (lemmatize/inflect/case-preservation/detokenize) directly rather than the class itself.

### Synonym engine (`engine.py` — v3)

Retrieves candidates from WordNet (POS-filtered) and Datamuse (`rel_syn=` + `ml=` endpoints), then ranks by Zipf frequency. Key fix in v3: WordNet hypernym traversal is gated by POS to prevent cross-POS contamination (e.g. `stress` as a noun no longer pulls in verb hypernyms like `say` or `pronounce`). Used directly by `reformulate.py`.

### SBERT firewall + antonym/negation guards (`semantic.py`)

For each candidate, builds a candidate sentence, batch-encodes it alongside the original, and computes cosine similarity. Protected phrases (multi-word fixed expressions like `look forward to`, `in order to`, `as well as`) are never substituted. Falls back gracefully to frequency-only ranking if SBERT fails to load. Extended for `reformulate.py` with `is_known_antonym()` (WordNet-based, rejects a candidate that's a direct antonym of the original) and `negation_consistent()` (rejects a full-sentence restructuring that changed the number of negation markers).

### Speaker Difficulty Profile — declared (`difficulty_profile.py`)

The user-facing "Speaker Difficulty Profile" panel described above. Three
independent, user-declared lists (sounds/words/phrases) plus optional
word-specific sound patterns, persisted via `profile_store.py`, read
directly by `reformulate.py`. Deliberately kept separate from the
*learned* profile below rather than merged into it — `ROADMAP.md` R12
resolves this for the reformulation engine specifically: it reads only
this declared profile, not the learned one below.

### Longitudinal difficulty model — learned, retained for `rewrite/` only (`profiling/`)

Not the same system as above, despite the similar name. `profiling/profile.py`'s
`SpeakerDifficultyProfile` stores a per-speaker, multi-factor word-difficulty
*model* (onset risk, syllable length, frequency, grammatical class), seeded
by self-report and population priors (`profiling/coldstart.py`), then
updated continuously via EWMA from session events. **Not read by
`reformulate.py` or `app.py`** — its only remaining consumer is the
retained `rewrite/` pipeline below. With no Audio Module in scope, this
profile is only ever seeded from typed self-report, never from real
session data — the UI no longer shows a chart for it, since that chart
would otherwise imply learned data that doesn't exist here.

### Profile-aware rewrite (`rewrite/`) — retained for comparison

`rewrite/rewriter.py`'s `DifficultyAwareRewriter` proposes meaning-preserving substitutions using the score `similarity - lambda * difficulty + mu * frequency`. **Retained for comparison against `reformulate.py`, not called by `app.py`.**

### Restructuring escalation (`rephrase.py`)

`reformulate.py`'s restructuring-escalation step, used when word-level substitution can't safely fix a sentence. Generates paraphrase candidates with a T5 model (`Vamsi/T5_Paraphrase_Paws`), blocks the user's flagged words via `bad_words_ids` (word-level only — phoneme-level constraints are enforced by re-checking each generated candidate, not by constraining generation, since `bad_words_ids` can't block a phoneme class), then `reformulate.py` re-verifies each candidate against the SBERT/antonym-equivalent/phoneme gates and keeps the best one that passes. Never imported by `grammar.py` or `engine.py`, loads the model lazily on first use (with `low_cpu_mem_usage=True` so it fits on low-RAM machines), and degrades to no restructuring available (that sentence is reported as left unchanged) if the stack or weights are unavailable.

### Evaluation harness (`eval/`) — for the retained `rewrite/` path

`eval/metrics.py` computes meaning preservation, difficulty-onset reduction, substitution rate, and lambda trade-offs against `rewrite/`'s `DifficultyAwareRewriter` and the learned `SpeakerDifficultyProfile`. `eval/profile_eval.py` compares self-report-only, observed-only, and fused profile AUC. `eval/study/` contains CSV helpers for a counterbalanced three-condition **human** study comparing reformulated-text conditions — no audio involved, it's about how readers/listeners judge the *text* output. Not yet extended to evaluate `reformulate.py` — that's the next stage.

### Storage layer (`profile_store.py`)

Single-default-profile, file-based storage — replaces the earlier
`user_store.py`/`auth.py` account layer (removed 2026-08-16; see
`DECISION_LOG.md` 2026-08-16-A). The public API
(`load_difficulty_profile`, `save_difficulty_profile`) takes a
`profile_name` parameter everywhere, defaulting to `"default"` — kept
parameterized rather than hardcoded so multi-profile support can be
reintroduced later without a storage-layer rewrite, even though there's no
UI for it today. No passwords are stored anywhere. (The `preferences`/
`custom_replacements` fields from the pre-`reformulate.py` UI — an
allowlist, rephrase/profile-rewrite toggles — were removed in the
2026-08-16 cleanup pass once the UI controls that set them were gone; see
`DECISION_LOG.md`.)

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
and [`DECISION_LOG.md`](DECISION_LOG.md) for the history of how it got there.

## Known Limitations

*(of the text reformulation module specifically)*

- Grammar correction depends on NLTK POS tagging, which can misfire on very short or broken sentences.
- Datamuse `ml=` results are not guaranteed to match POS; SBERT acts as the final filter for these.
- Protected phrases are hard-coded (~35 total); idiomatic coverage is incomplete.
- Subject-verb agreement detection looks left for the nearest subject, which fails in relative clauses.
- Grammar correction runs before synonym substitution; a corrected form may shift the target lemma.
- Declared phrase-level difficulty (`difficulty_profile.phrases`) is editable in the UI but not yet consumed by `reformulate.py` — see `ROADMAP.md` R13.
- Per-change keep/revert in the review panel doesn't yet feed back into the difficulty profile — see `ROADMAP.md` R9.
- The difficulty formulas and semantic threshold are hand-picked, not validated against real speaker data or human judgment — see `VALIDATION.md`.
- `reformulate.py` hasn't yet been measured against the retained `rewrite/`/`grammar.py` pipelines on a shared evaluation corpus — that comparison is the next stage, not yet run.

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
| `RESEARCH.md` | Literature review grounding the reformulation approach (paraphrase generation, lexical substitution, phoneme-aware NLP, evaluation methodology) |
| `PROBLEM_FORMULATION.md` | Design record for the Speaker Difficulty Profile — schema, representation research, the pattern-selection UI, single-profile architecture |
| `VALIDATION.md` | What has actually been measured, and its named limitations |
| `ROADMAP.md` | What's next, and the finding/gap that justifies each item |
| `CHANGELOG.md` | Fast-scan index into the decision log |

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
.cache/
venv/
__pycache__/
*.pyc
```

---

## Academic Context

Developed at **NUST SEECS** as an independent research project exploring phoneme-aware synonym substitution for stutter assistance, semantic integrity preservation via SBERT re-ranking, and accessible NLP tooling built on lightweight, offline-capable components.

See `DECISION_LOG.md` for the full development history and why specific choices were made.
