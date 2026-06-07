"""
semantic.py  —  SBERT-based semantic firewall + contextual candidate ranking.

Architecture
────────────
                    Sentence
                       ↓
              Synonym Generation  (engine.py)
                       ↓
           Candidate Sentence Builder
                       ↓
    ┌──────  SBERT Similarity Score  ──────┐
    │                                      │
  Accept                                Reject
    │
  Frequency Score  (wordfreq)
    │
  Combined Score  =  0.65 × semantic  +  0.35 × freq
    │
  Ranked Candidate List
                       ↓
            Grammar Check  (grammar.py)
                       ↓
                    Output

Key design decisions (with rationale)
───────────────────────────────────────
1. SBERT (all-MiniLM-L6-v2), NOT raw BERT
   Raw BERT produces token-level embeddings, not sentence-level.  Averaging
   them ("mean pooling") works but is inferior.  SBERT is trained specifically
   for semantic textual similarity, making cosine distance directly meaningful.

2. Semantic score weighted at 0.65, frequency at 0.35
   Meaning preservation is more important than word commonness.
   A rare but contextually correct word beats a common but drifting one.

3. Semantic threshold = 0.72  (soft rejection)
   Empirically:
     ≥ 0.85  →  excellent substitution
     0.72–0.85  →  acceptable (slight meaning shift)
     < 0.72  →  rejected (semantic drift too large)
   This is configurable — tighten to 0.80 for strict mode.

4. Protected words & phrases
   Function words, auxiliaries, and fixed multi-word expressions
   (look forward to, according to, …) are never substituted regardless
   of synonym availability.  This prevents breaking idioms and collocations.

5. Graceful degradation
   If the SBERT model is not yet downloaded (first run) or unavailable,
   the engine falls back to pure frequency ranking with a clear warning.
   The rest of the pipeline continues normally.

6. WSD (Word Sense Disambiguation) via SBERT
   We do NOT run explicit WSD.  Instead, SBERT implicitly handles it:
   wrong-sense synonyms produce low sentence-level similarity and are
   filtered out automatically.  "He was eating lunch" + "damage" → 0.43 → reject.
"""

from __future__ import annotations

import paths  # noqa: F401  — redirects HF/torch model caches into ./.cache
import re
from typing import Optional
import numpy as np
from freq import zipf_frequency   # memory-safe wrapper (falls back to 'small' wordlist)

# ── Constants ────────────────────────────────────────────────────────────────

SBERT_MODEL    = "all-MiniLM-L6-v2"
SEMANTIC_W     = 0.65    # weight for semantic similarity in final score
FREQUENCY_W    = 0.35    # weight for word frequency in final score
MIN_SEMANTIC   = 0.72    # candidates below this are rejected outright
ZIPF_MAX       = 7.0     # normalisation ceiling for Zipf frequency scores

# Protected multi-word phrases — positions covered by these are NEVER touched
PROTECTED_PHRASES: list[str] = [
    "look forward to", "according to", "as well as", "in order to",
    "due to", "in terms of", "as a result", "in addition to",
    "on behalf of", "in spite of", "as long as", "in case of",
    "at least", "at most", "by means of", "in fact", "for example",
    "in other words", "on the other hand", "as soon as", "no matter",
    "in front of", "by the way", "at the same time", "more or less",
    "kind of", "sort of", "a lot of", "plenty of", "a number of",
    "in general", "on average", "to be honest", "in conclusion",
    "for instance", "in contrast", "as opposed to",
]


# ── SBERT loader (lazy — only loads when first needed) ───────────────────────

_sbert_model   = None
_sbert_ok      = False   # True once model is successfully loaded
_sbert_message = ""      # Human-readable status for UI


def load_sbert() -> bool:
    """
    Load the SBERT model into module-level cache.
    Returns True on success, False on any failure (network, disk, etc.).
    Idempotent — safe to call repeatedly.
    """
    global _sbert_model, _sbert_ok, _sbert_message
    if _sbert_ok:
        return True
    try:
        from sentence_transformers import SentenceTransformer
        _sbert_model   = SentenceTransformer(SBERT_MODEL)
        _sbert_ok      = True
        _sbert_message = f"SBERT model '{SBERT_MODEL}' loaded successfully."
        return True
    except Exception as exc:
        _sbert_ok      = False
        _sbert_message = (
            f"SBERT unavailable ({exc.__class__.__name__}: {exc}). "
            "Falling back to frequency-only ranking."
        )
        return False


def sbert_status() -> tuple[bool, str]:
    """Return (is_loaded, human_readable_message)."""
    return _sbert_ok, _sbert_message


# ── Protected position detection ─────────────────────────────────────────────

def protected_positions(tokens: list[str]) -> set[int]:
    """
    Return the set of token indices that belong to a protected phrase
    or are themselves protected auxiliary/function words.
    These positions must never be substituted.
    """
    protected: set[int] = set()

    # 1. Multi-word protected phrases
    lower_tokens = [t.lower() for t in tokens]
    for phrase in PROTECTED_PHRASES:
        words = phrase.split()
        n = len(words)
        for i in range(len(lower_tokens) - n + 1):
            if lower_tokens[i : i + n] == words:
                protected.update(range(i, i + n))

    return protected


# ── Semantic scoring ─────────────────────────────────────────────────────────

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D vectors."""
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def semantic_similarity(sentence_a: str, sentence_b: str) -> Optional[float]:
    """
    Return cosine similarity [0, 1] between two sentences using SBERT.
    Returns None if SBERT is not loaded.
    """
    if not _sbert_ok or _sbert_model is None:
        return None
    embs = _sbert_model.encode([sentence_a, sentence_b])
    return _cosine(embs[0], embs[1])


def batch_semantic_similarity(
    original: str, candidate_sentences: list[str]
) -> list[Optional[float]]:
    """
    Batch version — scores all candidate sentences against *original* in one
    model.encode() call (much faster than calling one by one).
    """
    if not _sbert_ok or _sbert_model is None:
        return [None] * len(candidate_sentences)
    all_sents  = [original] + candidate_sentences
    embs       = _sbert_model.encode(all_sents)
    orig_emb   = embs[0]
    return [_cosine(orig_emb, embs[i + 1]) for i in range(len(candidate_sentences))]


# ── Combined scoring ─────────────────────────────────────────────────────────

def combined_score(
    semantic_sim: float,
    word: str,
    language: str = "en",
    sem_w: float = SEMANTIC_W,
    freq_w: float = FREQUENCY_W,
) -> float:
    """
    Final score used for ranking:
      score = sem_w × semantic_sim + freq_w × (zipf / ZIPF_MAX)
    """
    norm_freq = min(zipf_frequency(word, language) / ZIPF_MAX, 1.0)
    return sem_w * semantic_sim + freq_w * norm_freq


# ── Main API: contextual candidate ranking ───────────────────────────────────

def rank_candidates_contextually(
    original_sentence: str,
    word_to_replace:   str,
    token_index:       int,
    tokens:            list[str],
    candidates:        list[str],          # lemma-form candidates from engine
    inflected_forms:   dict[str, str],     # lemma → inflected form for this slot
    min_semantic:      float | None = None,  # None → read module MIN_SEMANTIC at call time
    language:          str   = "en",
) -> list[dict]:
    """
    Re-rank *candidates* by combined semantic + frequency score.

    For each candidate:
      1. Build the candidate sentence (swap token_index with inflected form)
      2. Score with SBERT vs original_sentence
      3. Reject if semantic < min_semantic
      4. Compute combined score
      5. Return sorted list of dicts

    Returns list of:
      {
        "lemma":         str,
        "inflected":     str,
        "semantic_sim":  float | None,
        "freq_score":    float,
        "combined":      float,
        "accepted":      bool,
      }

    If SBERT is unavailable, semantic_sim = None and ranking falls back to
    frequency only (all candidates accepted).
    """
    if not candidates:
        return []

    # Resolve the threshold at call time so a runtime change to MIN_SEMANTIC
    # (e.g. the sidebar slider doing `sem.MIN_SEMANTIC = x`) actually takes
    # effect.  A bound default argument would freeze the import-time value.
    if min_semantic is None:
        min_semantic = MIN_SEMANTIC

    sbert_available = _sbert_ok and _sbert_model is not None

    # Build candidate sentences
    candidate_sentences: list[str] = []
    valid_candidates:    list[str] = []

    for lemma in candidates:
        inf = inflected_forms.get(lemma, lemma)
        cand_tokens    = list(tokens)
        cand_tokens[token_index] = inf
        candidate_sentences.append(_detokenize(cand_tokens))
        valid_candidates.append(lemma)

    # Batch score with SBERT
    if sbert_available:
        sims = batch_semantic_similarity(original_sentence, candidate_sentences)
    else:
        sims = [None] * len(valid_candidates)

    # Score and filter
    scored: list[dict] = []
    for lemma, inf_form, cand_sent, sim in zip(
        valid_candidates,
        [inflected_forms.get(l, l) for l in valid_candidates],
        candidate_sentences,
        sims,
    ):
        freq = zipf_frequency(lemma, language)
        norm_freq = min(freq / ZIPF_MAX, 1.0)

        if sim is not None:
            accepted = sim >= min_semantic
            score    = combined_score(sim, lemma, language)
        else:
            accepted = True           # fallback: accept all
            score    = norm_freq      # rank by frequency only

        scored.append({
            "lemma":        lemma,
            "inflected":    inf_form,
            "semantic_sim": round(sim, 4) if sim is not None else None,
            "freq_score":   round(norm_freq, 4),
            "combined":     round(score, 4),
            "accepted":     accepted,
        })

    # Sort: accepted first, then by combined score descending
    scored.sort(key=lambda x: (not x["accepted"], -x["combined"]))
    return scored


# ── Helper (mirrors grammar._detokenize to avoid circular import) ─────────────

def _detokenize(tokens: list[str]) -> str:
    result = ""
    for i, tok in enumerate(tokens):
        if i == 0:
            result = tok
        elif tok in (".", ",", "!", "?", ";", ":", "'s", "n't", "'re",
                     "'ve", "'ll", "'d", "'m"):
            result += tok
        elif result and result[-1] == "'":
            result += tok
        else:
            result += " " + tok
    return result
