"""
semantic.py  —  SBERT-based semantic firewall + contextual candidate ranking.

UPDATED SCORING STRATEGY: STRICT SEMANTIC GATING (v2)
───────────────────────────────────────────────────────
The original 0.65 semantic / 0.35 frequency split allowed contextually weak
words like "container", "side", or "trust" to survive due to popularity rather
than meaning.  This update makes semantic similarity the PRIMARY GATEKEEPER,
reducing frequency to only a weak naturalness signal.

NEW THRESHOLDS & WEIGHTS:
  • MIN_SEMANTIC threshold:     0.72 → 0.85   (strict gate)
  • Semantic weight:             0.65 → 0.90   (primary signal)
  • Frequency weight:            0.35 → 0.10   (weak naturalness only)
  • Frequency normalisation:  raw zipf/7.0  →  log(1+z)/log(1+7)  (flattened)

Architecture
────────────
                    Sentence
                       ↓
              Synonym Generation  (engine.py)
                       ↓
           Candidate Sentence Builder
                       ↓
    ┌──────  SBERT Similarity Score  ──────┐
    │        (0.85 threshold — strict!)     │
  Accept                                Reject
    │
  Log-Normalized Frequency Score (weak tiebreaker: 10% influence)
    │
  Combined Score  =  0.90 × semantic  +  0.10 × log_freq
    │
  Ranked Candidate List  (semantic first, then naturalness)
                       ↓
            Grammar Check  (grammar.py)
                       ↓
                    Output

Key design decisions (with rationale)
───────────────────────────────────────────────────────
1. SBERT (all-MiniLM-L6-v2), NOT raw BERT
   Raw BERT produces token-level embeddings, not sentence-level.  Averaging
   them ("mean pooling") works but is inferior.  SBERT is trained specifically
   for semantic textual similarity, making cosine distance directly meaningful.

2. Strict semantic threshold (0.85) as PRIMARY GATEKEEPER
   Empirically:
     ≥ 0.85  →  excellent, safe substitution (THIS is the bar now)
     0.72–0.85  →  likely semantic drift (REJECTED)
     < 0.72  →  clear semantic drift (REJECTED)
   This prevents popularity-bias from overriding meaning preservation.

3. Frequency score is now WEAK NATURALNESS SIGNAL only (10% weight)
   After semantic filtering, only among SEMANTICALLY EQUIVALENT candidates
   do we prefer common, natural-sounding words over rare ones.  This eliminates
   the scenario where "container" (high freq) beats "pot" (lower freq) even
   though "container" shifts the meaning.

4. Log-normalized frequency (not raw linear)
   Raw Zipf leads to diminishing returns: going from freq=1 to freq=3 is huge,
   but freq=6 to freq=8 barely moves the score.  Log-norm flattens this:
   log(1+1)=0.69, log(1+3)=1.39, log(1+6)=1.95, log(1+8)=2.20.
   Result: among semantically filtered candidates, frequency is a fair tiebreaker.

5. Protected words & phrases
   Function words, auxiliaries, and fixed multi-word expressions
   (look forward to, according to, …) are never substituted regardless
   of synonym availability.  This prevents breaking idioms and collocations.

6. Graceful degradation
   If the SBERT model is not yet downloaded (first run) or unavailable,
   the engine falls back to pure frequency ranking with a clear warning.
   The rest of the pipeline continues normally.

7. WSD (Word Sense Disambiguation) via SBERT
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
SEMANTIC_W     = 0.90    # weight for semantic similarity in final score (stricter: 0.65→0.90)
FREQUENCY_W    = 0.10    # weight for word frequency in final score (reduced: 0.35→0.10)
MIN_SEMANTIC   = 0.85    # candidates below this are rejected outright (stricter: 0.72→0.85)
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

# Single-token protected words — mirrors grammar._STOP exactly so that
# protected_positions() is the single source of truth for the UI/semantic layer.
# These are auxiliaries, pronouns, determiners, prepositions, and discourse
# particles that must never be substituted.
_PROTECTED_SINGLE: frozenset[str] = frozenset({
    "be", "is", "are", "was", "were", "am", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "shall", "can", "must", "need", "dare",
    "to", "of", "in", "on", "at", "by", "for", "with", "into", "from", "about", "over", "under",
    "it", "its", "this", "that", "these", "those",
    "i", "me", "my", "we", "us", "our", "you", "your", "he", "him", "his", "she", "her", "they", "them", "their",
    "a", "an", "the",
    "and", "but", "or", "nor", "so", "yet", "both",
    "not", "no", "never",
    "just", "also", "even", "still", "already", "again", "always", "often", "sometimes",
})


def protected_positions(tokens: list[str]) -> set[int]:
    """
    Return the set of token indices that must never be substituted.

    Covers two categories:
      1. Multi-word protected phrases (PROTECTED_PHRASES list above).
      2. Single-token stop words: auxiliaries, pronouns, determiners,
         prepositions, and discourse particles (_PROTECTED_SINGLE).

    Keeping both in one function means the grammar layer (_STOP) and the
    semantic/UI layer stay in sync — there is no longer a risk of protected
    single words being left exposed when phrase matching misses them.
    """
    protected: set[int] = set()

    lower_tokens = [t.lower() for t in tokens]

    # 1. Multi-word protected phrases
    for phrase in PROTECTED_PHRASES:
        words = phrase.split()
        n = len(words)
        for i in range(len(lower_tokens) - n + 1):
            if lower_tokens[i : i + n] == words:
                protected.update(range(i, i + n))

    # 2. Single-token stop words
    for i, lt in enumerate(lower_tokens):
        if lt in _PROTECTED_SINGLE:
            protected.add(i)

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
      score = sem_w × semantic_sim + freq_w × log_norm_freq(zipf)
    
    SEMANTIC SIMILARITY is now the PRIMARY GATEKEEPER (0.90 weight).
    Frequency is only a weak naturalness signal (0.10 weight) to prefer
    common, natural-sounding words among semantically equivalent candidates.
    
    Log-normalization prevents ultra-common words (e.g. "the", "thing")
    from dominating the ranking once they clear semantic filtering.
    """
    import math
    raw_zipf = zipf_frequency(word, language)
    # Log-normalize: log(1 + z) / log(1 + ZIPF_MAX)
    log_norm = math.log(1.0 + raw_zipf) / math.log(1.0 + ZIPF_MAX)
    norm_freq = min(log_norm, 1.0)
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
        import math
        raw_zipf = zipf_frequency(lemma, language)
        # Log-normalize frequency: log(1 + z) / log(1 + ZIPF_MAX)
        log_norm = math.log(1.0 + raw_zipf) / math.log(1.0 + ZIPF_MAX)
        norm_freq = min(log_norm, 1.0)

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
