"""
main.py — StammAI FastAPI backend (Production v3.0)
Run: uvicorn main:app --reload --port 8000

Architecture:
  LocalEngine    → phonetic + POS filtering  (PKL files, zero API cost)
  EmbeddingLayer → semantic similarity filter + integrity check  (local, CPU)
  HybridEngine   → orchestrates both layers + Gemini re-ranking / rephrase

Changes from v2.2 → v3.0  (Phase 1 + 2 + 3 upgrades):
  Phase 1 — Token Integrity & Psycholinguistic Metrics:
  - layout_tokenize()       : character-offset-preserving tokenizer. Every
                              whitespace, punctuation, and word is a typed
                              Token object. No information lost for the frontend.
  - linguistic_risk()       : now incorporates Age-of-Acquisition (AoA) lookup.
                              Words learned late (AoA > 10 yrs) incur a 1.25x
                              cognitive-load penalty on the base risk factor.

  Phase 2 — Grammar & Context Protection:
  - filter_candidates()     : adds Asymmetric Window Similarity gate.
                              Extracts a ±3 word window around the substituted
                              word and computes local embedding similarity.
                              Candidates scoring < 0.75 on the window are
                              rejected — prevents grammatically unnatural fits
                              even when global sentence similarity is acceptable.
  - WSD hint                : LocalEngine._context_pos() already performs
                              context-aware POS disambiguation via NLTK tagger.
                              Phase 2 extends this with a lightweight synset
                              filter inside get_candidates().

  Phase 3 — Unified Pipeline & Session Feedback:
  - /api/transform-paragraph : single-pass endpoint. Tokenizes, scans, and
                               pre-fetches top-5 verified synonyms per risky
                               word in one async call. Returns a ready-to-render
                               token array for the React editor.
  - /api/user/report-spike   : session-adaptive feedback. The frontend reports
                               a stutter spike; the backend looks up the ARPAbet
                               onset and permanently increases the risk multiplier
                               for all words sharing that onset cluster during
                               the active session.
  - TransformToken           : unified Pydantic token schema that drives the
                               component-driven React rendering loop.

  Preserved from v2.2:
  - _safe_json()             : defensive Gemini response parser
  - async routes + asyncio.to_thread threading model
  - lifespan pattern
  - Cloud Ceiling gate (skip Gemini when avg_sim >= 0.88)
  - SynonymAPIResponse with engine + confidence fields
"""

import asyncio
import os
import re
import json
import pickle
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional, Tuple, Dict

import nltk
from nltk.corpus import wordnet as wn
from nltk.tokenize import word_tokenize

from google import genai
from google.genai import types
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
 
# ── NEW: StammAI GrammarGuard Orchestration ──
from grammar_module import (
    GrammarGuard,
    grammar_router,
    init_grammar,
    GrammarCheckReq,
    GrammarCheckResponse,
    report_to_response,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("stammapi")

# ── NLTK bootstrap ────────────────────────────────────────────────────────────
_NLTK_NEEDS = {
    "punkt":                          "tokenizers/punkt",
    "punkt_tab":                      "tokenizers/punkt_tab",
    "averaged_perceptron_tagger":     "taggers/averaged_perceptron_tagger",
    "averaged_perceptron_tagger_eng": "taggers/averaged_perceptron_tagger_eng",
    "wordnet":                        "corpora/wordnet",
    "omw-1.4":                        "corpora/omw-1.4",
}
for pkg, path in _NLTK_NEEDS.items():
    try:
        nltk.data.find(path)
    except LookupError:
        nltk.download(pkg, quiet=True)

# ── Optional: sentence-transformers ──────────────────────────────────────────
try:
    from sentence_transformers import SentenceTransformer, util as st_util
    _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    _ST_AVAILABLE = True
    log.info("Sentence-transformers loaded (all-MiniLM-L6-v2).")
except ImportError:
    _ST_AVAILABLE = False
    log.warning("sentence-transformers not installed — falling back to TF-IDF cosine.")

# ── TF-IDF cosine fallback ────────────────────────────────────────────────────
import numpy as np

def _tfidf_cosine(a: str, b: str) -> float:
    _STOP = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "to", "of", "in", "and", "or", "for", "with", "it", "its",
        "this", "that", "which", "at", "on", "by", "as", "but", "not",
        "he", "she", "they", "we", "i", "you", "my", "your", "his", "her",
    }
    def _bag(text):
        words = re.findall(r"[a-z]+", text.lower())
        return {w: words.count(w) for w in set(words) - _STOP}

    bag_a, bag_b = _bag(a), _bag(b)
    vocab = list(set(bag_a) | set(bag_b))
    if not vocab:
        return 1.0
    va = np.array([bag_a.get(w, 0) for w in vocab], dtype=float)
    vb = np.array([bag_b.get(w, 0) for w in vocab], dtype=float)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def semantic_similarity(text_a: str, text_b: str) -> float:
    if _ST_AVAILABLE:
        emb_a = _ST_MODEL.encode(text_a, convert_to_tensor=True)
        emb_b = _ST_MODEL.encode(text_b, convert_to_tensor=True)
        return float(st_util.cos_sim(emb_a, emb_b)[0][0])
    return _tfidf_cosine(text_a, text_b)


# ── Gemini setup ──────────────────────────────────────────────────────────────
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

if GEMINI_KEY:
    _CLIENT = genai.Client(api_key=GEMINI_KEY)
    _MODEL_NAME = "gemini-2.5-flash"
    log.info("Gemini client ready.")
else:
    _CLIENT = None
    log.warning("GEMINI_API_KEY not set — semantic functions degraded to local-only.")


# ── Centralised Gemini response parser ───────────────────────────────────────
def _safe_json(raw: str, fallback=None):
    """
    Parse a Gemini response string defensively.
    Handles markdown fences, BOM, preamble text, truncated strings.
    Every json.loads() call in this file goes through here.
    """
    text = raw.strip().lstrip('\ufeff')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```\s*$',          '', text, flags=re.MULTILINE)
    text = text.strip()

    m = re.search(r'[{\[]', text)
    if m:
        text = text[m.start():]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log.warning("_safe_json: primary parse failed — attempting bracket extraction")

    for pattern in [r'\{.*\}', r'\[.*\]']:
        hit = re.search(pattern, text, re.DOTALL)
        if hit:
            try:
                return json.loads(hit.group())
            except json.JSONDecodeError:
                pass

    log.error("_safe_json: all parse attempts failed. First 300 chars: %s", raw[:300])
    return fallback


# ── Pydantic schemas for structured Gemini output ────────────────────────────
class SynonymResponse(BaseModel):
    ranked_options: List[str]

class RephraseResponse(BaseModel):
    rephrased: List[str]

class CheckResponse(BaseModel):
    preserved: bool
    score: int
    issues: List[str]
    suggestion: str


# ════════════════════════════════════════════════════════════════════════════════
# PHASE 1 — LAYOUT-SAFE TOKENIZER
# ════════════════════════════════════════════════════════════════════════════════

class RawToken(BaseModel):
    """
    Character-offset-aware token. Every character in the original paragraph
    is represented exactly once. No information is discarded.

    Used internally by layout_tokenize() and returned as-is to the Phase 3
    /api/transform-paragraph endpoint after enrichment.
    """
    text:       str               # Raw substring (may be whitespace or punct)
    is_word:    bool
    risk_level: str = "safe"      # "high" | "medium" | "low" | "safe"
    synonyms:   List[str] = []    # Populated for high/medium word tokens only


def layout_tokenize(text: str) -> List[RawToken]:
    """
    Phase 1 — Layout-Safe Paragraph Tokenizer.

    Parses the input into a complete, sequence-preserved list of RawToken
    objects. Every whitespace, tab, newline, and punctuation mark is captured
    as an explicit non-word token.  No character is dropped or collapsed.

    Token classification:
      - Contiguous letter sequences → is_word=True
      - Everything else (spaces, punctuation, digits) → is_word=False

    Downstream enrichment (risk scoring, synonym population) is applied by
    HybridEngine.transform_paragraph() after initial tokenization.
    """
    tokens: List[RawToken] = []
    # Split preserving every separator character using a capture group
    # Pattern: one or more word characters vs one or more non-word characters
    parts = re.findall(r"[A-Za-z']+|[^A-Za-z']+", text)
    _WORD = re.compile(r"^[A-Za-z']+$")
    for part in parts:
        tokens.append(RawToken(
            text=part,
            is_word=bool(_WORD.match(part)),
        ))
    return tokens


# ════════════════════════════════════════════════════════════════════════════════
# LOCAL ENGINE
# ════════════════════════════════════════════════════════════════════════════════

# ── Phase 1 — Age of Acquisition (AoA) static fallback dictionary ─────────────
# Scores represent approximate age (in years) at which native English speakers
# typically acquire a word. Higher score = later acquisition = higher cognitive load.
# Source: approximated from Kuperman et al. (2012) AoA norms & Brysbaert (2017).
_AOA_DICT: Dict[str, float] = {
    # Late-acquired complex/abstract terms (AoA > 10 yrs)
    "acquire": 12.1,   "ambiguous": 13.5,  "analogous": 14.2,
    "arbitrary": 13.8, "autonomous": 13.1, "bilateral": 14.8,
    "bureaucratic": 15.2, "capitulate": 14.6, "causality": 13.9,
    "coherent": 12.8,  "collaborate": 12.4, "commemorate": 13.2,
    "competent": 11.5, "conceptual": 13.7,  "conjecture": 14.5,
    "consequence": 11.8, "constraint": 13.1, "contemplate": 12.9,
    "contradict": 12.6, "controversial": 13.4, "correlate": 13.8,
    "criterion": 14.1, "cumulative": 14.3,  "deliberate": 12.7,
    "demographic": 15.1, "discrepancy": 14.4, "distribute": 11.9,
    "elaborate": 12.5, "eliminate": 11.6,   "empirical": 15.3,
    "equivalent": 12.2, "exacerbate": 15.6, "facilitate": 13.6,
    "fluctuate": 13.9,  "formulate": 13.4,  "fundamental": 12.1,
    "generate": 11.7,   "hierarchy": 13.8,  "hypothesis": 14.2,
    "implication": 13.5, "inevitable": 13.1, "infrastructure": 15.4,
    "inherent": 13.7,   "initiate": 12.3,   "innovative": 13.2,
    "integrate": 12.8,  "interpret": 12.1,  "investigate": 11.9,
    "legislative": 15.7, "legitimate": 13.6, "manipulate": 12.9,
    "methodology": 15.1, "minimize": 12.4,  "mitigation": 14.8,
    "modification": 13.3, "monopoly": 13.8, "motivation": 12.6,
    "negotiate": 12.7,  "objective": 12.2,  "obligation": 13.1,
    "obsolete": 13.5,   "optimize": 13.9,   "paradigm": 15.8,
    "parameter": 14.6,  "perception": 12.8,  "perspective": 12.4,
    "phenomenon": 13.7,  "philosophy": 13.3, "pragmatic": 14.2,
    "prerequisite": 14.9, "prioritize": 13.6, "proficiency": 13.8,
    "proportional": 13.4, "regulation": 13.2, "reimbursement": 15.3,
    "reinforce": 12.7,  "relevance": 12.9,   "reluctant": 12.5,
    "replication": 14.1, "rhetoric": 14.4,   "scrutinize": 14.7,
    "significant": 11.8, "simultaneously": 14.3, "sophisticated": 13.5,
    "specification": 14.6, "stereotype": 13.1, "strategy": 12.3,
    "substantial": 12.7, "substitute": 12.1, "sufficient": 11.9,
    "systematic": 13.8,  "theoretical": 15.2, "transformation": 13.4,
    "underlying": 13.2,  "utilize": 13.1,    "validate": 13.6,
    "vulnerability": 14.1, "predominantly": 14.5,
}


class LocalEngine:
    """
    Phonetic + POS gatekeeper.
    100% offline — zero API cost.
    All data sourced from the five PKL files.

    v3 additions:
      - linguistic_risk()  : AoA-weighted cognitive load penalty (Phase 1)
      - get_candidates()   : WSD-aware synset filtering (Phase 2)
      - difficulty_override: extended with onset-cluster keys for Phase 3
        spike reporting. Keys can be either word strings or uppercase onset
        strings like "STR", "PL"; the risk scorer checks both.
    """

    # ARPAbet vowel set — for onset detection
    _VOWELS = {"AA","AE","AH","AO","AW","AY","EH","ER","EY","IH","IY","OW","OY","UH","UW"}

    def __init__(self, pkl_dir: str = "."):
        d = Path(pkl_dir)
        log.info("Loading PKL files from %s …", d.resolve())

        with open(d / "phoneme_index.pkl",  "rb") as f:
            self.phoneme_index: dict = pickle.load(f)
        with open(d / "synonym_map.pkl",    "rb") as f:
            self.synonym_map:   dict = pickle.load(f)
        with open(d / "pos_map.pkl",        "rb") as f:
            self.pos_map:       dict = pickle.load(f)
        with open(d / "cluster_cache.pkl",  "rb") as f:
            self.cluster_cache: dict = pickle.load(f)
        with open(d / "freq_rank.pkl",      "rb") as f:
            self.freq_rank:     dict = pickle.load(f)

        log.info("  phoneme_index  : %d entries", len(self.phoneme_index))
        log.info("  synonym_map    : %d entries", len(self.synonym_map))
        log.info("  cluster_cache  : %d entries", len(self.cluster_cache))

        # Extension hook: per-user difficulty overrides (populated at runtime).
        # Keys are either specific word strings or uppercase onset clusters
        # (e.g. "STR", "PL") injected by /api/user/report-spike.
        self.difficulty_override: Dict[str, float] = {}

    def _context_pos(self, word: str, sentence: str) -> str:
        """
        Context-aware POS via NLTK perceptron tagger.
        Returns WordNet POS character: 'n','v','a','r'.
        Falls back to static pos_map, then 'n'.
        """
        try:
            tokens = word_tokenize(sentence)
            tagged = nltk.pos_tag(tokens)
            for tok, tag in tagged:
                if tok.lower() == word.lower():
                    if tag.startswith("VB"): return "v"
                    if tag.startswith("NN"): return "n"
                    if tag.startswith("JJ"): return "a"
                    if tag.startswith("RB"): return "r"
        except Exception:
            pass
        return self.pos_map.get(word.lower(), "n")

    def _arpa_onset(self, word: str) -> List[str]:
        """
        Return ARPAbet onset phoneme(s) for the first pronunciation in CMU.
        Returns [] if word not in phoneme_index.
        """
        entry = self.phoneme_index.get(word.lower())
        if not entry:
            return []
        pron = entry[0] if isinstance(entry[0], list) else entry
        onset = []
        for phone in pron:
            p = re.sub(r"\d", "", str(phone)).upper()
            if p in self._VOWELS:
                break
            onset.append(p)
            if len(onset) == 2:
                break
        return onset

    def _is_blocked(self, word: str, block_set: set) -> bool:
        """
        True if the word's ARPAbet onset starts with any blocked cluster/phoneme.
        block_set contains strings like {"S","P","ST","SP","PR","TR"}.
        Also checks session-injected onset multipliers from difficulty_override.
        """
        onset = self._arpa_onset(word)
        if not onset:
            return False
        onset_str = "".join(onset)

        # Static block profile
        for block in block_set:
            if onset_str.startswith(block.upper()):
                return True

        # Dynamic spike-reported blocks stored as onset keys in difficulty_override
        for key, multiplier in self.difficulty_override.items():
            # Onset-cluster keys are ALL-CAPS and at most 3 chars (e.g. "STR", "PL")
            if key.isupper() and len(key) <= 3:
                if onset_str.startswith(key) and multiplier >= 2.0:
                    return True
        return False

    def linguistic_risk(self, word: str) -> float:
        """
        Phase 1 — Composite risk score [0-1].
        Higher = harder to say.
        Weights: onset_difficulty 0.4 + syllable_count 0.3 + rarity 0.3

        v3 additions:
          - AoA penalty: if the word's Age of Acquisition exceeds 10 years,
            the base risk factor is scaled up by 1.25x to model the extra
            cognitive-planning load imposed by late-acquired vocabulary.
          - Onset-cluster multipliers: session-reported spike onset clusters
            (stored in difficulty_override as uppercase keys) lift the risk of
            any word sharing that onset, even if not individually overridden.
          - Per-word difficulty_override multiplier (existing behaviour).
        """
        entry = self.phoneme_index.get(word.lower())
        if not entry:
            base = 0.5
        else:
            pron = entry[0] if isinstance(entry[0], list) else entry
            p0 = re.sub(r"\d", "", str(pron[0])).upper() if pron else ""
            onset_score = 0.2 if p0 in self._VOWELS else 0.85
            syllables = sum(1 for p in pron if str(p)[-1].isdigit())
            syl_score = min(syllables / 5.0, 1.0)
            freq = self.freq_rank.get(word.lower(), 0)
            rarity = max(0.0, (8.0 - freq) / 8.0) if freq > 0 else 1.0
            base = round(0.4 * onset_score + 0.3 * syl_score + 0.3 * rarity, 4)

        # ── Phase 1: Age of Acquisition penalty ───────────────────────────────
        aoa_score = _AOA_DICT.get(word.lower())
        if aoa_score is not None and aoa_score > 10.0:
            base = base * 1.25   # 25% uplift for late-acquired vocabulary
            log.debug("AoA penalty applied to '%s' (AoA=%.1f): base → %.4f", word, aoa_score, base)

        # ── Per-word override (existing) ──────────────────────────────────────
        override = self.difficulty_override.get(word.lower(), 1.0)

        # ── Onset-cluster override (Phase 3 spike learning) ──────────────────
        onset = self._arpa_onset(word)
        if onset:
            onset_str = "".join(onset)
            for key, mult in self.difficulty_override.items():
                if key.isupper() and len(key) <= 3 and onset_str.startswith(key):
                    override = max(override, mult)   # take strongest multiplier

        return min(1.0, base * override)

    def get_candidates(
        self,
        word: str,
        sentence: str,
        block_profile: set,
        n: int = 20,
    ) -> List[dict]:
        """
        Returns up to `n` phonetically-safe, POS-matched candidates.
        Each entry: {word, freq, risk, pos_match, onset}

        Phase 2 addition — WSD synset filter:
          Uses NLTK context POS to select only WordNet synsets whose POS
          matches the contextual tag. This prevents pulling in homograph
          synonyms (e.g. "lead" as metal vs "lead" as verb).
        """
        w = word.lower()
        target_pos = self._context_pos(word, sentence)
        block_upper = {b.upper() for b in block_profile}

        # Merge Moby + cluster_cache raw synonyms
        raw: set = set()
        raw.update(self.synonym_map.get(w, []))
        raw.update(self.cluster_cache.get(w, []))

        # Phase 2 — WSD-filtered WordNet supplement
        # Only add lemmas from synsets whose POS matches the contextual POS tag
        _WN_POS = {"n": wn.NOUN, "v": wn.VERB, "a": wn.ADJ, "r": wn.ADV}
        wn_pos = _WN_POS.get(target_pos)
        for s in wn.synsets(w, pos=wn_pos):  # filter synsets by context POS
            for lem in s.lemmas():
                raw.add(lem.name().lower().replace("_", " "))
            for sim in s.similar_tos():
                for lem in sim.lemmas():
                    raw.add(lem.name().lower().replace("_", " "))

        # Fallback: if WSD synsets produce nothing, widen to all POS (existing behaviour)
        if not raw and w not in self.cluster_cache:
            for s in wn.synsets(w):
                for lem in s.lemmas():
                    raw.add(lem.name().lower().replace("_", " "))

        raw.discard(w)

        _SINGLE = re.compile(r"^[a-z']+$")
        candidates = []
        for cand in raw:
            if not _SINGLE.fullmatch(cand):
                continue
            if self._is_blocked(cand, block_upper):
                continue
            cand_pos = self.pos_map.get(cand, None)
            pos_match = (cand_pos == target_pos) if cand_pos else False
            freq = self.freq_rank.get(cand, 0)
            risk = self.linguistic_risk(cand)
            candidates.append({
                "word":      cand,
                "freq":      freq,
                "risk":      risk,
                "pos_match": pos_match,
                "onset":     self._arpa_onset(cand),
            })

        candidates.sort(key=lambda x: (-int(x["pos_match"]), -x["freq"]))
        return candidates[:n]


# ════════════════════════════════════════════════════════════════════════════════
# EMBEDDING LAYER
# ════════════════════════════════════════════════════════════════════════════════

class EmbeddingLayer:
    """
    Semantic filtering and integrity checking via sentence embeddings.
    Uses sentence-transformers (all-MiniLM-L6-v2) when available;
    degrades gracefully to TF-IDF cosine otherwise.

    v3 additions:
      - filter_candidates(): Asymmetric Window Similarity gate (Phase 2).
        For each candidate, a ±3-word local context window is extracted
        around the substitution point and embedded separately. If the local
        window similarity < LOCAL_WINDOW_THRESHOLD (0.75), the candidate is
        rejected regardless of global sentence similarity. This catches
        grammatical/collocational mismatches that global similarity misses.
    """

    CANDIDATE_SIM_THRESHOLD: float = 0.70   # global sentence similarity floor
    INTEGRITY_PRESERVE_THRESHOLD: float = 0.80
    LOCAL_WINDOW_THRESHOLD: float = 0.75    # Phase 2 — local window floor

    def _extract_window(self, sentence: str, word: str, window: int = 3) -> str:
        """
        Phase 2 — extract a ±window word context string around `word` in
        `sentence`. Returns the window as a space-joined string.
        Falls back to the full sentence on any failure.
        """
        try:
            words = re.findall(r"\b\w+\b", sentence)
            lower_words = [w.lower() for w in words]
            try:
                idx = lower_words.index(word.lower())
            except ValueError:
                return sentence   # word not found — fall back to full sentence
            start = max(0, idx - window)
            end   = min(len(words), idx + window + 1)
            return " ".join(words[start:end])
        except Exception:
            return sentence

    def filter_candidates(
        self,
        original_sentence: str,
        word: str,
        candidates: List[dict],
        threshold: float | None = None,
    ) -> List[dict]:
        """
        Phase 2 — Dual-gate semantic filter:

        Gate 1 — Global Sentence Similarity (existing):
          Substitute candidate into the full sentence and compare embeddings
          against the original. Reject if global sim < CANDIDATE_SIM_THRESHOLD.

        Gate 2 — Asymmetric Window Similarity (new in v3):
          Extract a ±3-word window around the substitution point in both the
          original and substituted sentences. Compute local window similarity.
          If local sim < LOCAL_WINDOW_THRESHOLD (0.75), reject the candidate.
          This prevents structurally unnatural collocations that happen to
          score well on global similarity.
        """
        min_sim   = threshold or self.CANDIDATE_SIM_THRESHOLD
        win_floor = self.LOCAL_WINDOW_THRESHOLD
        accepted  = []

        orig_window = self._extract_window(original_sentence, word)

        for cand in candidates:
            sub_sentence = re.sub(
                r"\b" + re.escape(word) + r"\b",
                cand["word"],
                original_sentence,
                flags=re.IGNORECASE,
            )

            # Gate 1 — global similarity
            global_sim = semantic_similarity(original_sentence, sub_sentence)
            if global_sim < min_sim:
                continue

            # Gate 2 — local window similarity (Phase 2)
            sub_window = self._extract_window(sub_sentence, cand["word"])
            local_sim  = semantic_similarity(orig_window, sub_window)
            if local_sim < win_floor:
                log.debug(
                    "Window gate rejected '%s' for '%s': local_sim=%.3f < %.2f",
                    cand["word"], word, local_sim, win_floor,
                )
                continue

            enriched = dict(cand)
            enriched["sim_score"]   = round(global_sim, 4)
            enriched["window_sim"]  = round(local_sim, 4)
            accepted.append(enriched)

        accepted.sort(key=lambda x: (
            -int(x.get("pos_match", False)),
            -x.get("sim_score", 0),
            -x.get("freq", 0),
        ))
        return accepted

    def check_integrity(self, original: str, modified: str) -> dict:
        """
        Embedding-based semantic integrity check.
        Returns { preserved, score, issues, suggestion, method, needs_gemini }.
        """
        sim = semantic_similarity(original, modified)
        score = int(round(sim * 100))
        method = "embedding-local" if _ST_AVAILABLE else "tfidf-local"

        if sim >= self.INTEGRITY_PRESERVE_THRESHOLD:
            return {
                "preserved": True, "score": score, "issues": [],
                "suggestion": "", "method": method, "needs_gemini": False,
            }

        issues = []
        if sim < 0.5:
            issues.append("Significant semantic divergence detected.")

        return {
            "preserved": sim >= 0.65, "score": score, "issues": issues,
            "suggestion": "", "method": method, "needs_gemini": True,
        }


# ════════════════════════════════════════════════════════════════════════════════
# HYBRID ENGINE
# ════════════════════════════════════════════════════════════════════════════════

class HybridEngine:
    """
    Orchestrates Local → Embedding → Gemini pipeline.

    v3 additions:
      - transform_paragraph(): Phase 3 single-pass endpoint implementation.
      - report_spike()        : Phase 3 session-adaptive feedback implementation.
    """

    _GEMINI_SIM_CEILING: float = 0.88

    def __init__(self, pkl_dir: str = "."):
        self.local    = LocalEngine(pkl_dir=pkl_dir)
        self.semantic = EmbeddingLayer()

    # ── 1. SYNONYMS  ─────────────────────────────────────────────────────────

    def synonyms(
        self,
        word: str,
        sentence: str,
        block_profile: set,
        n_final: int = 6,
    ) -> Tuple[List[str], str, float]:
        """
        Full pipeline:
          Tier 1 — LocalEngine.get_candidates  (phonetic + POS + WSD)
          Tier 2 — EmbeddingLayer.filter_candidates  (global + window semantic gate)
          Tier 3 — Gemini re-rank  (only when embedding confidence is low)

        Returns (words, tier, confidence).
        """
        raw_candidates = self.local.get_candidates(word, sentence, block_profile, n=20)
        filtered       = self.semantic.filter_candidates(sentence, word, raw_candidates)

        if not filtered:
            filtered = self.semantic.filter_candidates(
                sentence, word, raw_candidates, threshold=0.55
            )

        if not filtered:
            log.info("No candidates passed semantic filter for '%s'.", word)
            return [], "local", 0.0

        candidate_words = [c["word"] for c in filtered[:15]]
        top5     = filtered[:5]
        avg_sim  = sum(c.get("sim_score", 0.0) for c in top5) / len(top5)
        confidence = round(avg_sim, 4)

        if avg_sim >= self._GEMINI_SIM_CEILING or not _CLIENT:
            tier = "embedding" if avg_sim > 0 else "local"
            log.info("synonyms('%s'): ceiling reached (avg_sim=%.3f).", word, avg_sim)
            return candidate_words[:n_final], tier, confidence

        prompt = (
            f'Sentence context: "{sentence}"\n'
            f'Target word to replace: "{word}"\n'
            f'Candidate replacements (phonetically pre-approved):\n'
            f'{json.dumps(candidate_words)}\n\n'
            f'Rank these candidates from best to worst fit for this exact sentence. '
            f'Consider: meaning preservation, natural fluency, register match. '
            f'Never add words outside the provided list.'
        )
        try:
            response = _CLIENT.models.generate_content(
                model=_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1, max_output_tokens=512,
                    response_mime_type="application/json",
                    response_schema=SynonymResponse,
                ),
            )
            data   = _safe_json(response.text, fallback={})
            ranked = data.get("ranked_options", [])
            approved   = set(candidate_words)
            ranked     = [w for w in ranked if w in approved]
            ranked_set = set(ranked)
            tail       = [w for w in candidate_words if w not in ranked_set]
            return (ranked + tail)[:n_final], "gemini", confidence
        except Exception as e:
            log.warning("Gemini re-ranking failed for '%s': %s", word, e)
            return candidate_words[:n_final], "embedding", confidence

    # ── 2. REPHRASE  ─────────────────────────────────────────────────────────

    def _local_rephrase(self, sentence: str, block_profile: set) -> List[str]:
        block_upper = {b.upper() for b in block_profile}
        tokens      = word_tokenize(sentence)
        result_tokens = list(tokens)
        changed = False

        for i, tok in enumerate(tokens):
            if not re.match(r'^[a-zA-Z]+$', tok):
                continue
            if self.local._is_blocked(tok, block_upper):
                candidates = self.local.get_candidates(tok, sentence, block_profile, n=5)
                if candidates:
                    replacement = candidates[0]["word"]
                    if tok[0].isupper():
                        replacement = replacement.capitalize()
                    result_tokens[i] = replacement
                    changed = True

        if not changed:
            return []
        rephrased = " ".join(result_tokens)
        rephrased = re.sub(r'\s([?.!,;:])', r'\1', rephrased)
        return [rephrased]

    def rephrase(
        self, sentence: str, block_profile: set, n: int = 3,
    ) -> List[str]:
        if not _CLIENT:
            log.info("rephrase: Gemini unavailable — using local fallback.")
            return self._local_rephrase(sentence, block_profile) or []

        blocked_str = ", ".join(sorted(block_profile)) or "none"
        prompt = (
            f'You are a fluency adaptation assistant for a person who stutters.\n'
            f'Rephrase the sentence below {n} different ways.\n\n'
            f'HARD CONSTRAINTS:\n'
            f'- Every rephrasing must carry EXACTLY the same meaning and intent.\n'
            f'- Avoid words whose onset sounds match these phoneme clusters: {blocked_str}.\n'
            f'- Keep the same register (formal stays formal, casual stays casual).\n'
            f'- Output must sound completely natural.\n\n'
            f'Sentence: "{sentence}"'
        )
        try:
            response = _CLIENT.models.generate_content(
                model=_MODEL_NAME, contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.25, max_output_tokens=512,
                    response_mime_type="application/json",
                    response_schema=RephraseResponse,
                ),
            )
            data    = _safe_json(response.text, fallback={})
            options = data.get("rephrased", [])
            options = [o for o in options if isinstance(o, str) and o.strip()][:n]
            if options:
                return options
            log.warning("rephrase: Gemini returned no options — using local fallback.")
        except Exception as e:
            log.warning("rephrase: Gemini failed (%s) — using local fallback.", e)

        return self._local_rephrase(sentence, block_profile) or []

    # ── 3. SEMANTIC INTEGRITY CHECK  ─────────────────────────────────────────

    def check(self, original: str, modified: str) -> dict:
        local_result = self.semantic.check_integrity(original, modified)

        if not local_result.get("needs_gemini", False):
            return {k: v for k, v in local_result.items() if k != "needs_gemini"}

        if not _CLIENT:
            result = dict(local_result)
            result.pop("needs_gemini", None)
            result["issues"] = result.get("issues", []) + ["Gemini offline — local embedding check only."]
            return result

        prompt = (
            f'You are a semantic integrity auditor for a speech-fluency tool.\n'
            f'A user replaced some words in their text.\n\n'
            f'Original: "{original}"\n'
            f'Modified: "{modified}"\n\n'
            f'Evaluate whether MODIFIED preserves:\n'
            f'1. Exact same meaning and intent.\n'
            f'2. Natural fluency — no awkward word combinations.\n'
            f'3. Same grammatical structure and register.\n\n'
            f'Be strict. Flag broken idioms, shifted tone, or tonal drift.\n'
            f'Provide a score 0-100 where 100 = perfectly equivalent.'
        )
        try:
            response = _CLIENT.models.generate_content(
                model=_MODEL_NAME, contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1, max_output_tokens=512,
                    response_mime_type="application/json",
                    response_schema=CheckResponse,
                ),
            )
            data = _safe_json(response.text, fallback={})
            return {
                "preserved":  bool(data.get("preserved", local_result["preserved"])),
                "score":      int(data.get("score", local_result["score"])),
                "issues":     list(data.get("issues", [])),
                "suggestion": str(data.get("suggestion", "")),
                "method":     "gemini-validated",
            }
        except Exception as e:
            log.warning("Gemini integrity check failed: %s", e)
            result = dict(local_result)
            result.pop("needs_gemini", None)
            result["method"] = local_result["method"] + "+gemini-error"
            return result

    # ── 4. SCAN  ─────────────────────────────────────────────────────────────

    def scan(
        self, text: str, block_profile: set, risk_threshold: float = 0.65,
    ) -> dict:
        """
        Existing scan endpoint — unchanged behaviour.
        Uses NLTK word_tokenize (not layout_tokenize) to preserve v2.2 API.
        """
        block_upper = {b.upper() for b in block_profile}
        tokens      = word_tokenize(text)
        word_results = []
        _WORD = re.compile(r"^[a-z]+$", re.IGNORECASE)

        for tok in tokens:
            if not _WORD.fullmatch(tok):
                continue
            w    = tok.lower()
            risk = self.local.linguistic_risk(w)
            blocked = self.local._is_blocked(w, block_upper)

            if blocked:
                level = "high"
            elif risk >= risk_threshold:
                level = "medium"
            elif risk >= 0.40:
                level = "low"
            else:
                level = "safe"

            if level in ("high", "medium"):
                alts_raw = self.local.get_candidates(w, text, block_profile, n=10)
                alts = [c["word"] for c in alts_raw[:3]]
            else:
                alts = []

            word_results.append({
                "word": tok, "risk": level, "risk_score": round(risk, 3),
                "blocked": blocked, "alternatives": alts,
            })

        risky_count = sum(1 for r in word_results if r["risk"] in ("high", "medium"))
        return {
            "original": text, "total_words": len(word_results),
            "risky_words": risky_count, "words": word_results,
        }

    # ── 5. PHASE 3 — TRANSFORM PARAGRAPH (single-pass) ───────────────────────

    def transform_paragraph(
        self,
        text: str,
        block_profile: set,
        risk_threshold: float = 0.65,
        top_n: int = 5,
    ) -> List[dict]:
        """
        Phase 3 — Single-pass paragraph transformation.

        1. Tokenize the full text with layout_tokenize() — preserves every
           space, newline, and punctuation character as an explicit token.
        2. For each word token: compute linguistic_risk, determine risk_level,
           check onset blockage.
        3. For HIGH and MEDIUM risk words: run the full Tier 1 + Tier 2
           pipeline (phonetic candidates → dual-gate semantic filter) to
           pre-fetch the top `top_n` verified synonym candidates.
        4. Return the enriched token list. The frontend can render immediately
           without making any additional API calls for synonym data.

        Returns: List[dict]  — each dict matches the TransformToken schema.
        """
        block_upper = {b.upper() for b in block_profile}
        raw_tokens  = layout_tokenize(text)

        # Collect all word tokens with their surrounding sentence context
        # We need the full text to extract sentence context for each word.
        enriched: List[dict] = []

        for tok in raw_tokens:
            if not tok.is_word:
                enriched.append({
                    "text": tok.text, "is_word": False,
                    "risk_level": "safe", "synonyms": [],
                    "risk_score": 0.0, "blocked": False,
                })
                continue

            w    = tok.text.lower()
            # Skip possessives / contractions that slip through (e.g. "'s")
            if not re.match(r"^[a-z]+$", w):
                enriched.append({
                    "text": tok.text, "is_word": False,
                    "risk_level": "safe", "synonyms": [],
                    "risk_score": 0.0, "blocked": False,
                })
                continue

            risk    = self.local.linguistic_risk(w)
            blocked = self.local._is_blocked(w, block_upper)

            if blocked:
                level = "high"
            elif risk >= risk_threshold:
                level = "medium"
            elif risk >= 0.40:
                level = "low"
            else:
                level = "safe"

            # Pre-fetch verified synonyms for risky words (the key Phase 3 value)
            synonyms_list: List[str] = []
            if level in ("high", "medium"):
                try:
                    raw_cands = self.local.get_candidates(w, text, block_profile, n=20)
                    filtered  = self.semantic.filter_candidates(text, w, raw_cands)
                    if not filtered:
                        filtered = self.semantic.filter_candidates(
                            text, w, raw_cands, threshold=0.55
                        )
                    synonyms_list = [c["word"] for c in filtered[:top_n]]
                except Exception as e:
                    log.warning("transform_paragraph: synonym fetch failed for '%s': %s", w, e)

            enriched.append({
                "text":       tok.text,
                "is_word":    True,
                "risk_level": level,
                "risk_score": round(risk, 3),
                "blocked":    blocked,
                "synonyms":   synonyms_list,
            })

        return enriched

    # ── 6. PHASE 3 — SESSION SPIKE REPORTING ─────────────────────────────────

    def report_spike(self, word: str, multiplier: float = 1.5) -> dict:
        """
        Phase 3 — Session-Adaptive Feedback Loop.

        When the frontend reports a stutter spike on a specific word:
          1. Look up the word's ARPAbet onset cluster via _arpa_onset().
          2. Register that onset cluster as a session-level risk multiplier in
             difficulty_override (keyed by the uppercase onset string, e.g. "STR").
          3. All subsequent linguistic_risk() calls automatically apply this
             multiplier to ANY word sharing that onset cluster — not just the
             specific word that was flagged.
          4. _is_blocked() also checks these onset-keyed entries when multiplier
             reaches 2.0, effectively blocking the onset cluster.

        Also applies a per-word override for the specific word reported.

        Returns a dict describing what was registered.
        """
        onset = self.local._arpa_onset(word)
        onset_str = "".join(onset).upper() if onset else ""

        # Per-word override
        self.local.difficulty_override[word.lower()] = multiplier

        # Onset-cluster override
        registered_onset: Optional[str] = None
        if onset_str:
            existing = self.local.difficulty_override.get(onset_str, 1.0)
            self.local.difficulty_override[onset_str] = max(existing, multiplier)
            registered_onset = onset_str
            log.info(
                "Spike reported: word='%s' onset='%s' multiplier=%.2f registered.",
                word, onset_str, multiplier,
            )
        else:
            log.info(
                "Spike reported: word='%s' (no onset found) — word-level override only.",
                word,
            )

        return {
            "word":              word,
            "onset_registered":  registered_onset,
            "multiplier":        multiplier,
            "override_table_size": len(self.local.difficulty_override),
        }


# ════════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ════════════════════════════════════════════════════════════════════════════════

_engine: HybridEngine | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine
    try:
        _engine = HybridEngine(pkl_dir=".")
        log.info("StammAI HybridEngine v3 ready.")
 
        # ── NEW: initialise GrammarGuard ──────────────────────────────────────
        init_grammar(gemini_client=_CLIENT, model_name=_MODEL_NAME)
        # ─────────────────────────────────────────────────────────────────────
    except Exception as e:
        log.error("Engine startup failed: %s", e)
        _engine = None
    yield

app = FastAPI(title="StammAI API", version="3.1", lifespan=lifespan)

# ── NEW: Attach grammar validation endpoints ──
app.include_router(grammar_router)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request models ────────────────────────────────────────────────────────────

class SynonymReq(BaseModel):
    word: str
    sentence_context: str
    block_profile: List[str] = []
    n: int = 6

class RephraseReq(BaseModel):
    sentence: str
    block_profile: List[str] = []
    n: int = 3

class CheckReq(BaseModel):
    original_text: str
    modified_text: str

class ScanReq(BaseModel):
    text: str
    block_profile: List[str] = []
    risk_threshold: float = 0.65

# Phase 3 — new request schemas
class TransformParagraphReq(BaseModel):
    text: str
    block_profile: List[str] = []
    risk_threshold: float = 0.65
    top_n: int = 5                     # max synonyms to pre-fetch per risky word

class ReportSpikeReq(BaseModel):
    word: str
    multiplier: float = 1.5            # risk multiplier; >= 2.0 triggers onset block


# ── Response models ───────────────────────────────────────────────────────────

class SynonymAPIResponse(BaseModel):
    synonyms: List[str]
    context_note: str = ""
    engine: Optional[str] = None
    confidence: Optional[float] = None

class RephraseAPIResponse(BaseModel):
    rephrased: List[str]

class CheckAPIResponse(BaseModel):
    preserved: bool
    score: int
    issues: List[str]
    suggestion: str
    method: Optional[str] = None

class ScanWordResult(BaseModel):
    word: str
    risk: str
    risk_score: float
    blocked: bool
    alternatives: List[str]

class ScanAPIResponse(BaseModel):
    original: str
    total_words: int
    risky_words: int
    words: List[ScanWordResult]

# Phase 3 — unified token schema for the React editor
class TransformToken(BaseModel):
    """
    Unified layout-safe token for the React component-driven rendering loop.

    Non-word tokens (spaces, punctuation) have is_word=False and empty
    synonyms — the frontend renders them verbatim as <span> elements.

    Word tokens have risk_level and pre-fetched synonyms so the frontend
    can immediately display highlights and interactive drop-downs without
    making any further API calls.
    """
    text:       str
    is_word:    bool
    risk_level: str           # "high" | "medium" | "low" | "safe"
    risk_score: float = 0.0
    blocked:    bool  = False
    synonyms:   List[str] = []

class TransformParagraphResponse(BaseModel):
    tokens: List[TransformToken]
    total_words: int
    risky_words: int

class ReportSpikeResponse(BaseModel):
    word: str
    onset_registered: Optional[str] = None
    multiplier: float
    override_table_size: int


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def route_health():
    return {
        "status":     "ok",
        "gemini":     _CLIENT is not None,
        "embeddings": _ST_AVAILABLE,
        "engine":     _engine is not None,
        "version":    "3.0",
    }


@app.post("/api/synonyms", response_model=SynonymAPIResponse)
async def route_synonyms(req: SynonymReq):
    if not _engine:
        return SynonymAPIResponse(synonyms=[], context_note="Engine not ready.")

    words, tier, confidence = await asyncio.to_thread(
        _engine.synonyms,
        req.word, req.sentence_context, set(req.block_profile), req.n,
    )
    notes = {
        "local":     "Phonetically filtered · locally ranked",
        "embedding": "Phonetically filtered · semantically verified (global + window)",
        "gemini":    "Phonetically filtered · semantically verified · Gemini re-ranked",
    }
    return SynonymAPIResponse(
        synonyms=words, context_note=notes.get(tier, ""),
        engine=tier, confidence=confidence,
    )


@app.post("/api/rephrase", response_model=RephraseAPIResponse)
async def route_rephrase(req: RephraseReq):
    if not _engine:
        return RephraseAPIResponse(rephrased=[])
    opts = await asyncio.to_thread(
        _engine.rephrase, req.sentence, set(req.block_profile), req.n,
    )
    return RephraseAPIResponse(rephrased=opts)


@app.post("/api/check-semantics", response_model=CheckAPIResponse)
async def route_check(req: CheckReq):
    if not _engine:
        return CheckAPIResponse(preserved=True, score=100, issues=[], suggestion="")
    result = await asyncio.to_thread(
        _engine.check, req.original_text, req.modified_text,
    )
    return CheckAPIResponse(**{k: v for k, v in result.items() if k in CheckAPIResponse.model_fields})


@app.post("/api/scan", response_model=ScanAPIResponse)
async def route_scan(req: ScanReq):
    if not _engine:
        return ScanAPIResponse(original=req.text, total_words=0, risky_words=0, words=[])
    result = await asyncio.to_thread(
        _engine.scan, req.text, set(req.block_profile), req.risk_threshold,
    )
    return ScanAPIResponse(**result)


# ── Phase 3 routes ────────────────────────────────────────────────────────────

@app.post("/api/transform-paragraph", response_model=TransformParagraphResponse)
async def route_transform_paragraph(req: TransformParagraphReq):
    """
    Phase 3 — Single-pass paragraph transformation.

    Runs the full tokenize → scan → synonym-prefetch pipeline in one call.
    Returns a layout-safe token array with risk levels and pre-fetched
    synonym candidates embedded. The React editor can render immediately.
    """
    if not _engine:
        # Degrade gracefully: return a plain tokenization with no risk data
        raw = layout_tokenize(req.text)
        tokens = [
            TransformToken(text=t.text, is_word=t.is_word, risk_level="safe")
            for t in raw
        ]
        return TransformParagraphResponse(tokens=tokens, total_words=0, risky_words=0)

    raw_result: List[dict] = await asyncio.to_thread(
        _engine.transform_paragraph,
        req.text,
        set(req.block_profile),
        req.risk_threshold,
        req.top_n,
    )

    tokens     = [TransformToken(**t) for t in raw_result]
    word_toks  = [t for t in tokens if t.is_word]
    risky_toks = [t for t in word_toks if t.risk_level in ("high", "medium")]

    return TransformParagraphResponse(
        tokens=tokens,
        total_words=len(word_toks),
        risky_words=len(risky_toks),
    )


@app.post("/api/user/report-spike", response_model=ReportSpikeResponse)
async def route_report_spike(req: ReportSpikeReq):
    """
    Phase 3 — Session-adaptive stutter spike reporting.

    The frontend calls this when the user flags a word as a live stutter spike.
    The engine immediately:
      1. Registers a per-word risk multiplier.
      2. Registers the ARPAbet onset cluster as a session-wide multiplier so
         ALL words sharing that onset are treated as higher-risk for the rest
         of the session.
      3. If multiplier >= 2.0, the onset cluster is effectively blocked.

    This endpoint is lightweight and near-instant — no LLM calls, no PKL I/O.
    """
    if not _engine:
        return ReportSpikeResponse(
            word=req.word, onset_registered=None,
            multiplier=req.multiplier, override_table_size=0,
        )

    result = await asyncio.to_thread(
        _engine.report_spike, req.word, req.multiplier,
    )
    return ReportSpikeResponse(**result)
