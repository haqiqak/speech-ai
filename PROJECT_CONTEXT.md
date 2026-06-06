# Speech-AI — Full Project Context

> **Purpose of this document:** This is a living technical narrative. It describes every architectural decision made so far, everything that was considered but rejected, the current state of every file, and a concrete roadmap of what to build next. Keep it updated as the project evolves. When starting a new Claude session, paste this document as context before asking for changes.

---

## 1. What the project is

**Speech-AI** is a synonym-substitution assistant designed for people who stutter or have phonetic difficulty with certain words. The core idea: you type a sentence, the system automatically finds easier-to-say alternatives for the risky words — without changing the meaning, tense, or grammar of the sentence.

It is NOT a speech-to-text transcription tool (that was an earlier phase). The current codebase is entirely about text-in → rewritten-text-out.

---

## 2. Current stack

| Layer | Technology | Why |
|---|---|---|
| UI | Streamlit | Fast to iterate, no JS required, component state via `st.session_state` |
| Synonym retrieval | WordNet (NLTK) + Datamuse API | Complementary: WordNet is structured and POS-aware, Datamuse has broader surface coverage |
| Semantic filter | SBERT `all-MiniLM-L6-v2` | Sentence-level cosine similarity; trained for textual similarity tasks |
| Morphology | pyinflect + NLTK WordNetLemmatizer | Inflect lemmas to correct surface form (ate, eating, eaten, etc.) |
| Frequency ranking | wordfreq (Zipf scores) | Favour common, natural-sounding words over obscure ones |
| Grammar correction | NLTK POS tagger + pyinflect | Rule-based, 8-layer correction pipeline |

**No external API keys required. Runs 100% locally after first model download.**

---

## 3. File-by-file description (current state)

### `engine.py` — SynonymEngine v3

Retrieves synonym candidates from two sources and ranks them by frequency.

**Sources:**
- **WordNet** via `wn.synsets(word, pos=wn_pos)` — direct lemmas, `similar_tos`, `also_sees`, same-POS hypernyms only
- **Datamuse** — `rel_syn=` (exact synonyms) + `ml=` (meaning-like) endpoints, merged

**Key fix applied (v3):** The original engine called `wn.synsets(word)` with no POS filter. This caused cross-POS contamination — `stress` (used as a noun) would also pull in hypernyms from `stress.v.01` (`show`, `evince`) and `stress.v.02` (`say`, `pronounce`). The fix: `_wordnet_synonyms(word, wn_pos=None)` now accepts and passes a POS constant. Hypernym traversal is also gated: `if wn_pos is None or hyper.pos() == wn_pos`. The public `get_synonyms()` method accepts `wn_pos=` and passes it through.

**Quality filters:**
- Zipf frequency ≥ 2.0 (drops archaic/rare words)
- Single-token only (no space-separated phrases)
- Query word itself removed from candidates
- Junk set: `{be, have, do, make, get}` always removed

**Ranking:** By Zipf frequency descending (most common first). This is a pre-SBERT rank — SBERT re-ranks by semantic fit after this.

---

### `semantic.py` — SBERT semantic firewall

**Model:** `all-MiniLM-L6-v2` — 80 MB, runs on CPU, produces 384-dim sentence embeddings. Loaded once via `@st.cache_resource`.

**Core flow:**
1. For each candidate lemma, build a candidate sentence by substituting the inflected form into the token list.
2. Batch-encode `[original_sentence, cand_sent_1, cand_sent_2, ...]` in one `model.encode()` call (amortised cost).
3. Cosine similarity between original and each candidate sentence.
4. Reject if similarity < `MIN_SEMANTIC` (default 0.72).
5. Score accepted candidates: `0.65 × semantic_sim + 0.35 × (zipf / 7.0)`.
6. Sort: accepted first, then by combined score descending.

**Why SBERT over raw BERT:** Raw BERT produces token-level embeddings. Mean-pooling them gives sentence representations, but SBERT is specifically trained with contrastive loss for sentence similarity — cosine distance is directly meaningful.

**Why implicit WSD (not explicit):** Explicit WSD systems (Lesk, supervised neural) add complexity and still make errors. SBERT handles it automatically: a wrong-sense synonym produces a low sentence-level similarity and gets rejected. `eat → damage` in "He was eating lunch" scores ~0.43 and is dropped.

**Protected phrases (33 total):** Positions covered by multi-word fixed expressions are never substituted. Examples: `look forward to`, `according to`, `as well as`, `in order to`, `due to`, `in terms of`, `as a result`, `in addition to`, `on behalf of`, `kind of`, `sort of`, `a lot of`. These are hard-coded in `PROTECTED_PHRASES` list.

**Configurable constants:**
```python
MIN_SEMANTIC = 0.72   # reject threshold
SEMANTIC_W   = 0.65   # weight for semantic score
FREQUENCY_W  = 0.35   # weight for frequency score
ZIPF_MAX     = 7.0    # normalisation ceiling
```

**Graceful degradation:** If SBERT fails to load (first run, no internet, disk issue), all candidates are accepted and ranked by frequency only. A warning banner appears in the sidebar.

---

### `grammar.py` — Sanitizer + SentenceRewriter

**`sanitize_input(text)`** — 8-layer correction pipeline applied BEFORE synonym substitution:

| Layer | What it fixes | Example |
|---|---|---|
| 1a | Contractions | `dont` → `don't` |
| 1b | Informal words | `gonna` → `going to`, `wanna` → `want to` |
| 2 | Pronoun case | `i` → `I` |
| 3 | Sentence capitalisation | `the cat...` → `The cat...` |
| 4 | Extra spaces | `word  word` → `word word` |
| 5 | Auxiliary verb form | `I am go` → `I am going`, `I will went` → `I will go`, `He have eat` → `He have eaten` |
| 6 | Tense correction | `I eat yesterday` → `I ate yesterday` |
| 7 | Subject-verb agreement | `He go` → `He goes`, `They was` → `They were`, `I goes` → `I go` |
| 8 | Punctuation | adds trailing `.` if missing |

**Tense correction logic:** Scans tokens for past-time markers (`yesterday`, `ago`, `last`, `previously`, `earlier`, `back`, `then`, phrases like `last week`, `3 days ago`, `in 1990`). If found and no present-time marker (`now`, `today`, `currently`) exists, converts VBP/VBZ verbs to VBD (past tense) via `pyinflect.getInflection(base, 'VBD')`.

**Subject-verb agreement guard:** Skips SV-agreement correction when the main verb is already preceded by a do/modal/have/be auxiliary (so `She don't like` stays as-is — the auxiliary owns the agreement, not the main verb).

**`SentenceRewriter.rewrite(sentence)`** — full substitution pipeline:
1. Tokenise + POS-tag
2. Identify protected positions (multi-word phrases + stop words)
3. For each substitutable token: lemmatise, fetch POS-filtered candidates from engine, build inflected forms, run SBERT ranking
4. Place best accepted candidate into token list
5. Return full scoring metadata (for UI display)

**`rebuild_with_choices(sentence, substitutions, user_choices)`** — reassembles sentence using user's dropdown selections. Called live on every Streamlit re-render.

**Stop word protection set:** `{be, is, are, was, were, am, been, being, have, has, had, do, does, did, will, would, could, should, may, might, shall, can, must, need, dare, to, of, in, on, at, by, for, with, into, from, about, over, under, it, its, this, that, these, those, i, me, my, we, us, our, you, your, he, him, his, she, her, they, them, their, a, an, the, and, but, or, nor, so, yet, both, not, no, never, just, also, even, still, already, again, always, often, sometimes}`

---

### `app.py` — Streamlit UI

Single-file UI with no external JS. Key structures:

- `@st.cache_resource` on engine, rewriter, and SBERT init — loads once per process
- `st.session_state` tracks: `result`, `sanitized`, `fixes`, `user_choices`, `last_query`, `sentence_mode`
- Renders 5 pipeline cards in sentence mode: ① grammar correction, ② scoring table + dropdowns, ③ grammar check, ④ highlighted diff, ⑤ final output
- Word mode: shows synonym pills per word with top-3 highlighted orange
- Sidebar: SBERT status banner, semantic threshold slider, scoring toggle

---

## 4. Decisions made and why

### Chosen

| Decision | Rationale |
|---|---|
| SBERT over raw BERT | SBERT is trained for sentence similarity; cosine distance is directly usable. Raw BERT requires mean-pooling hacks. |
| Implicit WSD via SBERT | Avoids the complexity of Lesk / supervised WSD. Wrong-sense candidates get rejected naturally by low cosine similarity. |
| Batch SBERT encoding | One `model.encode([orig, c1, c2, ...])` call per word — ~10× faster than one call per candidate. |
| POS-filtered WordNet | Prevents verb synset hypernyms from polluting noun candidate lists. Critical fix for `stress → say`, `company → lot`. |
| Combined score (0.65 semantic + 0.35 freq) | Meaning preservation > popularity. A less common but contextually right word beats a common but drifting one. |
| Protected phrases list (hard-coded) | Prevents breaking idioms. `look forward to`, `as well as`, etc. must never be partially substituted. |
| Rule-based grammar correction | Deterministic, explainable, fast. Each fix is shown to the user with a description. No LLM needed for this layer. |
| pyinflect for inflection | More accurate than hand-rolled suffix rules, handles irregular forms (eat→ate, go→went, etc.). |
| Zipf frequency (wordfreq) | Better than raw corpus counts — Zipf scale compresses the range and is language-normalised. |
| Streamlit for UI | Zero frontend build step, session state built in, fast iteration. Acceptable latency for this use case. |

### Rejected and why

| Option | Rejected because |
|---|---|
| LanguageTool (Java) for grammar | Requires JVM, complex install, adds ~200 MB. Rule-based NLTK approach covers the core errors with zero extra deps. |
| Explicit WSD (Lesk algorithm) | Adds latency and still makes errors. SBERT handles it implicitly and more robustly. |
| OpenAI / Gemini for synonym generation | API cost, latency, rate limits, internet dependency. Local WordNet + Datamuse achieves acceptable quality offline. |
| React + FastAPI split architecture | More complexity than needed for current scope. Streamlit monorepo is easier to run and deploy. *(Note: the repo also has a `speech-backend/` + `speech-app/` React version — that was an earlier architecture, not currently active.)* |
| spaCy for NLP | Heavier install. NLTK covers POS tagging, lemmatisation, and WordNet access in one package already present. |
| Supervised tense correction (seq2seq) | Overkill for the error types seen. Rule-based covers: past-time markers, auxiliary forms, SV agreement — the most common input errors. |
| Storing synonym_map.pkl / phoneme PKL files | The speech-backend folder has these pre-computed pickles for a phoneme-risk pipeline. Not used in the current Streamlit app. May be revived. |

---

## 5. Known limitations (current)

- **Grammar correction is NLTK-POS-dependent.** If the tagger mislabels a word (common in very short or broken sentences), the correction may be wrong or missed. The UI shows every fix explicitly so the user can see what changed.
- **Datamuse may still return wrong-POS words.** These are caught by the secondary `wn.synsets(cand, pos=wn_p)` check in `SentenceRewriter._raw_candidates()`, but Datamuse words with no WordNet entry may pass through. SBERT is the final filter.
- **`damage` can survive for `eat[VERB]`** because Datamuse returns it and some sentences with `damage` score above 0.72 against the original. Raising the threshold or adding a stricter POS check on Datamuse candidates would fix this.
- **No memory between sessions.** The app is stateless; closing the browser loses all choices.
- **Protected phrases are hard-coded.** 33 phrases currently. Idiomatic coverage is incomplete.
- **No handling of passive voice or complex clause structures.** Subject-verb agreement detection looks left for the nearest subject, which fails in relative clauses (`The man who run fast` — `run` would get corrected to `runs` with `man` as subject, which is wrong if the relative clause is intended).
- **Grammar correction runs before synonym substitution.** If the corrected form changes the word's POS, the substitution may operate on a different lemma than the user intended.

---

## 6. Next steps / improvement roadmap

These are ordered roughly by impact vs effort.

### Tier 1 — High impact, moderate effort

**A. Phonetic risk scoring (restore original vision)**
The repo has `cluster_cache.pkl`, `phoneme_index.pkl`, `pos_map.pkl`, `freq_rank.pkl` in `speech-backend/` — pre-computed ARPAbet phoneme data. Add a `phonetic.py` module that:
- Loads these PKL files
- Scores each word by phonetic difficulty (cluster density, consonant clusters, syllable count)
- Tags words in the UI as high/medium/low risk BEFORE the synonym step
- Only runs the synonym pipeline on high-risk words
- This restores the original speech-fluency use case properly

**B. Datamuse POS filtering**
Datamuse's `rel_syn=` endpoint returns same-POS synonyms (usually). Its `ml=` endpoint returns meaning-like words with no POS guarantee. Filter `ml=` results through `wn.synsets(cand, pos=wn_p)` before adding to candidates (already done for WordNet, needs extending to the Datamuse result set explicitly).

**C. Revert correction button**
In card ①, add a button next to each grammar fix that undoes it. Currently, if the grammar corrector makes a mistake on unusual input, there's no way to restore the original word except by retyping.

### Tier 2 — Medium impact, moderate effort

**D. Sentence-level phoneme scoring**
After synonym substitution, score the rewritten sentence for total phonetic difficulty and show a before/after comparison. This gives the user a concrete measure of improvement.

**E. User word list / blocklist**
Let users mark certain words as always-substitute or never-substitute (persistent via `st.session_state` + local file). Useful for recurring proper nouns or personally difficult words.

**F. Multi-sentence input**
Currently the pipeline processes one sentence. Split on `.!?`, process each sentence independently, then rejoin. This requires careful state management (per-sentence substitutions, per-sentence grammar).

**G. Export / copy button**
Add a proper "Copy final sentence" button using the `pyperclip` library or the Streamlit clipboard API. Currently the user has to manually select text.

### Tier 3 — Larger effort, architectural changes

**H. LLM re-ranking layer (optional, gated)**
Add a Gemini / local Ollama call as an optional final re-ranking step after SBERT. The LLM gets: original sentence, top-3 SBERT-accepted candidates, and rates naturalness + fluency. Only fires if the user enables it in settings. Keeps the offline-first promise.

**I. Live speech input (browser mic)**
Use the `streamlit-webrtc` component to capture microphone audio, run Whisper locally (via `faster-whisper`) for transcription, and feed the transcript directly into the synonym pipeline. Closes the loop from speech → text → easier speech.

**J. Fine-tune SBERT on speech-fluency pairs**
Create a dataset of (original sentence, acceptable rewrite, bad rewrite) triplets. Fine-tune `all-MiniLM-L6-v2` using contrastive loss to better judge phonetically-motivated substitutions. Requires ~500–2000 annotated examples.

**K. React + FastAPI architecture revival**
The `speech-backend/` + `speech-app/` directories contain a React/Vite frontend and FastAPI backend from an earlier iteration. These have `GrammarGuard` (5-layer), `HybridEngine`, and `/api/transform-paragraph` endpoints. Reviving this architecture would allow: mobile-friendly UI, multi-user deployment, WebSocket live transcription, and proper API versioning. Would require porting the v3 engine and grammar fixes into the FastAPI backend.

---

## 7. Session history summary

| Session | What was done |
|---|---|
| Session 1 | Initial React + FastAPI architecture. Grammar module with 5-layer GrammarGuard (Gemini, LanguageTool, tense check, SV-agreement, semantic similarity). Phoneme PKL files generated. |
| Session 2 | Pivot to Streamlit monorepo. Built `engine.py` (WordNet + Datamuse), `semantic.py` (SBERT), `grammar.py` (sanitizer + SentenceRewriter), `app.py` (full UI). SBERT integrated with batch encoding, combined scoring, protected phrases. |
| Session 3 | Fixed two root bugs: (1) `engine.py` — added POS-filtering to WordNet synonym extraction, eliminating cross-POS contamination (`stress → say`, `company → lot`). (2) `grammar.py` — expanded `sanitize_input()` from 5 to 8 layers, adding tense correction, subject-verb agreement, and auxiliary verb form correction. |

---

## 8. File versions to use

Always use the **fixed versions** from Session 3:

- `engine.py` — SynonymEngine v3 (POS-filtered WordNet)
- `grammar.py` — sanitize_input 8-layer + SentenceRewriter v2 (POS-aware candidate fetching)
- `semantic.py` — unchanged from Session 2
- `app.py` — unchanged from Session 2

The `speech-backend/` folder's `main.py` and `grammar_module.py` are from the earlier FastAPI architecture and are NOT the files currently being developed. Do not confuse them with the Streamlit files above.

---

## 9. How to continue building with Claude

Paste this document at the start of your prompt, then describe what you want to add. Good prompts follow this pattern:

> "Here is the project context [paste doc]. I want to implement [feature from roadmap section 6]. The relevant files are engine.py and grammar.py. [Describe any specific behaviour you want or edge cases to handle]."

When a session produces new fixed files, update section 7 (session history) and section 8 (file versions) before saving this document.
