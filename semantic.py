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
from nltk.corpus import wordnet as wn
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

# Idiomatic/fixed expressions where substituting a single word breaks the
# phrase as a whole, even though each word passes the per-word semantic
# check in isolation (REFORMULATION_PROBLEM_MAP.md SS2.4/SS5 item 1 — found
# directly from VALIDATION.md SS9.7/SS9.9's pilot: "how's it going" and
# "drives me crazy" were both broken this way, and SS9.9's "right now" ->
# "justly"/"properly" word-sense bug is also a fixed adverbial phrase this
# same mechanism protects, ahead of the separate general word-sense-
# disambiguation fix planned for that class of bug). Same exact-match
# mechanism as PROTECTED_PHRASES above -- written as literal, space-
# separated token sequences that must match nltk's own tokenization
# (e.g. "how 's it going", not "how's it going", since word_tokenize
# splits the contraction into its own token).
IDIOM_PHRASES: list[str] = [
    "how 's it going", "how is it going",
    "what 's going on", "what is going on",
    "right now", "right away", "right here",
    # R26/R27 (VALIDATION.md SS17-18): "push [a meeting]" (postpone) has NO
    # WordNet sense at all under "push" -- every literal-force synonym
    # ("force", "press", "drive"...) is a semantically-close but wrong
    # substitution, and no amount of candidate re-ranking can fix a sense
    # that was never in the pool. Added as the literal phrase actually
    # observed, matching item 1's own scoping (a curated list of evidenced
    # phrases, not a general phrasal-verb detector -- REFORMULATION_
    # PROBLEM_MAP.md SS3.1's disclosed [GAP] still stands).
    "push the meeting",
]

# A handful of idioms take an object pronoun in one slot ("drives me
# crazy" / "drives him crazy" / ...) -- spelling out every combination in
# IDIOM_PHRASES would be error-prone and incomplete, so these use a single
# `{pron}` wildcard slot instead, matched against a fixed, small pronoun
# set in _matches_idiom_pattern() below.
_IDIOM_PRONOUNS: frozenset[str] = frozenset({"me", "him", "her", "us", "you", "them", "it"})
IDIOM_PHRASE_PATTERNS: list[str] = [
    "drives {pron} crazy", "driving {pron} crazy",
    "drove {pron} crazy", "drive {pron} crazy",
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


# ── MeaningBERT loader (lazy — optional SECOND meaning-preservation signal) ──
# Validated 2026-08-18, R24 (VALIDATION.md §15): real but partial — catches
# several idiom-adjacent meaning breaks SBERT misses badly (e.g. a causative-
# construction break SBERT scored 0.968/near-perfect, MeaningBERT scored
# 48.0), but completely misses the single worst-rated case on record (SBERT
# and MeaningBERT both score it as fine). NOT a strict improvement over
# SBERT — a different, overlapping-but-not-superset blind spot. Wired in
# 2026-08-19 (R27) strictly as a REPORTED-ALONGSIDE signal: it must never
# gate `final_ok`/`accepted` decisions on its own, and must never silently
# replace the existing SBERT gate (Practice.md §10 — proxy metrics are
# reported, not blended into pass/fail without a separate go-ahead).
_meaningbert_tokenizer = None
_meaningbert_model     = None
_meaningbert_ok        = False   # True once model is successfully loaded
_meaningbert_message   = ""      # Human-readable status for UI

MEANINGBERT_MODEL = "davebulaval/MeaningBERT"


def load_meaningbert() -> bool:
    """
    Load MeaningBERT into module-level cache.
    Returns True on success, False on any failure (network, disk, etc.).
    Idempotent — safe to call repeatedly. Same graceful-degradation shape
    as load_sbert() above; no trust_remote_code, no gating.
    """
    global _meaningbert_tokenizer, _meaningbert_model, _meaningbert_ok, _meaningbert_message
    if _meaningbert_ok:
        return True
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        _meaningbert_tokenizer = AutoTokenizer.from_pretrained(MEANINGBERT_MODEL)
        _meaningbert_model     = AutoModelForSequenceClassification.from_pretrained(MEANINGBERT_MODEL)
        _meaningbert_model.eval()
        _meaningbert_ok        = True
        _meaningbert_message   = f"MeaningBERT model '{MEANINGBERT_MODEL}' loaded successfully."
        return True
    except Exception as exc:
        _meaningbert_ok      = False
        _meaningbert_message = (
            f"MeaningBERT unavailable ({exc.__class__.__name__}: {exc}). "
            "Reporting SBERT similarity only."
        )
        return False


def meaningbert_status() -> tuple[bool, str]:
    """Return (is_loaded, human_readable_message)."""
    return _meaningbert_ok, _meaningbert_message


def meaningbert_score(original_sentence: str, candidate_sentence: str) -> Optional[float]:
    """
    Return MeaningBERT's 0-100 meaning-preservation score for
    (original_sentence, candidate_sentence), or None if the model is
    unavailable. Lazily loads on first call, same pattern as
    semantic_similarity()/SBERT. Deliberately a SEPARATE 0-100 scale (its
    native output, as validated/reported in R24), not normalized to
    SBERT's 0-1 cosine range — the two are different kinds of signal and
    should not be visually conflated.
    """
    if not _meaningbert_ok and not load_meaningbert():
        return None
    try:
        import torch
        with torch.no_grad():
            inputs = _meaningbert_tokenizer(
                original_sentence, candidate_sentence,
                return_tensors="pt", truncation=True,
            )
            logits = _meaningbert_model(**inputs).logits
            return float(logits.squeeze().item())
    except Exception:
        return None


# ── Contextual-fit loader (lazy — optional NATURALNESS/fluency signal) ───────
# Validated 2026-08-19, R33-R36 (VALIDATION.md SS26-29): a masked-LM word-
# probability check — mask the substituted word's position in the FINAL
# reformulated sentence, read the model's probability for the word actually
# used there. Answers a genuinely different question than SBERT/MeaningBERT
# (which check whether MEANING survived): does this specific word choice
# read naturally in this specific slot. Catches a real, confirmed failure
# class SBERT/MeaningBERT/LanguageTool all miss (R28's LanguageTool result
# was 0/7; this signal is 16/16 on the same style of known-bad case across
# R33-R36's combined 61-case corpus, human-confirmed 17/18 in R35). Has a
# real, disclosed, word-specific blind spot (register/formality mismatches
# like "belated" score high despite reading oddly to a human — R35/R36) and
# should not be treated as complete. Named "contextual fit," not
# "naturalness," specifically to avoid confusion with naturalness.py's
# unrelated edit-ratio metric.
#
# Wired in 2026-08-19 (R36 -> Option A) strictly as a REPORTED-ONLY signal,
# same discipline as MeaningBERT (R24/R27): must never gate `final_ok`/
# `accepted`/escalation decisions on its own. That gating decision (Option
# B, REFORMULATION_PROBLEM_MAP.md's Phase-2 design) is explicitly deferred,
# not implemented here.
_contextual_fit_tokenizer = None
_contextual_fit_model     = None
_contextual_fit_ok        = False   # True once model is successfully loaded
_contextual_fit_message   = ""      # Human-readable status for UI

CONTEXTUAL_FIT_MODEL = "distilbert-base-uncased"


def load_contextual_fit_model() -> bool:
    """
    Load the contextual-fit masked-LM into module-level cache.
    Returns True on success, False on any failure (network, disk, etc.).
    Idempotent — safe to call repeatedly. Same graceful-degradation shape
    as load_sbert()/load_meaningbert() above; no trust_remote_code, no
    gating.
    """
    global _contextual_fit_tokenizer, _contextual_fit_model, _contextual_fit_ok, _contextual_fit_message
    if _contextual_fit_ok:
        return True
    try:
        from transformers import AutoTokenizer, AutoModelForMaskedLM
        _contextual_fit_tokenizer = AutoTokenizer.from_pretrained(CONTEXTUAL_FIT_MODEL)
        _contextual_fit_model     = AutoModelForMaskedLM.from_pretrained(CONTEXTUAL_FIT_MODEL)
        _contextual_fit_model.eval()
        _contextual_fit_ok        = True
        _contextual_fit_message   = f"Contextual-fit model '{CONTEXTUAL_FIT_MODEL}' loaded successfully."
        return True
    except Exception as exc:
        _contextual_fit_ok      = False
        _contextual_fit_message = (
            f"Contextual-fit model unavailable ({exc.__class__.__name__}: {exc}). "
            "Reporting SBERT/MeaningBERT only."
        )
        return False


def contextual_fit_status() -> tuple[bool, str]:
    """Return (is_loaded, human_readable_message)."""
    return _contextual_fit_ok, _contextual_fit_message


def contextual_fit_score(sentence: str, word: str, occurrence: int = 0) -> Optional[float]:
    """
    Mask `word`'s position (the `occurrence`-th match, 0-indexed) in
    `sentence` and return the model's probability for the token(s)
    actually there — how well the surrounding context predicts the
    specific word used at that position. Returns None if the model is
    unavailable or `word` can't be located in the sentence's own
    tokenization (rare tokenization mismatches; fails closed to "no
    signal," never raises).

    Deliberately scored against the FINAL, fully-assembled sentence, not
    the original — this checks a property of the output alone (does it
    read naturally), not meaning preservation (SBERT/MeaningBERT's job).
    Multi-word candidates average the probability across their sub-word
    pieces. Validated only for single-word substitutions (source=
    "substitution") — not yet validated for phrase-tier or restructuring
    output, which replace a multi-word span rather than one word; not
    applied to those sources.
    """
    if not _contextual_fit_ok and not load_contextual_fit_model():
        return None
    try:
        import torch
        enc = _contextual_fit_tokenizer(sentence, return_tensors="pt")
        input_ids = enc["input_ids"][0]
        tokens = _contextual_fit_tokenizer.convert_ids_to_tokens(input_ids)
        target_pieces = _contextual_fit_tokenizer.tokenize(word.lower())
        if not target_pieces:
            return None
        n = len(target_pieces)
        matches = [
            i for i in range(len(tokens) - n + 1)
            if tokens[i:i + n] == target_pieces
        ]
        if not matches or occurrence >= len(matches):
            return None
        start = matches[occurrence]
        probs = []
        for pos in range(start, start + n):
            masked = input_ids.clone().unsqueeze(0)
            original_id = masked[0, pos].item()
            masked[0, pos] = _contextual_fit_tokenizer.mask_token_id
            with torch.no_grad():
                logits = _contextual_fit_model(input_ids=masked).logits
            p = torch.softmax(logits[0, pos], dim=-1)[original_id].item()
            probs.append(p)
        return sum(probs) / len(probs)
    except Exception:
        return None


# ── NLI logical-consistency check (R45, VALIDATION.md §36.1/§36.3) ───────────
# SBERT/MeaningBERT/contextual_fit all measure some flavor of embedding
# similarity or local fluency -- none of them check whether the candidate
# still makes the same CLAIM as the original. "pre-industrial"->"palaeolithic"
# and "slower"->"easier" both read fluently and score well on every one of
# those signals, because fluency isn't what's wrong with them. R41 already
# showed contextual_fit can't fill this gap (structurally blind to exactly
# this class); this is the tiered NLI check REFORMULATION_RESEARCH.md §24.A
# designed and deferred, now validated: 32% recall on R40's SEVERE class when
# combined with grammar_issue_count() below (vs. ~20% for either alone,
# VALIDATION.md §36.1) -- real, non-overlapping signal, not a complete fix.
_nli_model = None
_nli_ok = False
_nli_message = ""

NLI_MODEL = "cross-encoder/nli-deberta-v3-xsmall"
# The larger nli-deberta-v3-small failed three separate download attempts on
# this project's network (httpcore.RemoteProtocolError, connection reset
# ~50-60MB in regardless of file size, not a timeout -- VALIDATION.md §36
# footnote). xsmall downloaded successfully via a resumable per-file retry
# loop; kept as the default since it's already proven to load here.


def load_nli_model() -> bool:
    """Load the NLI cross-encoder into module-level cache. Same graceful-
    degradation shape as load_sbert()/load_meaningbert()/
    load_contextual_fit_model() above; idempotent, no gating."""
    global _nli_model, _nli_ok, _nli_message
    if _nli_ok:
        return True
    try:
        from sentence_transformers import CrossEncoder
        _nli_model = CrossEncoder(NLI_MODEL)
        _nli_ok = True
        _nli_message = f"NLI model '{NLI_MODEL}' loaded successfully."
        return True
    except Exception as exc:
        _nli_ok = False
        _nli_message = f"NLI model unavailable ({exc.__class__.__name__}: {exc})."
        return False


def nli_status() -> tuple[bool, str]:
    """Return (is_loaded, human_readable_message)."""
    return _nli_ok, _nli_message


def logical_consistency_check(original_sentence: str, candidate_sentence: str) -> Optional[dict]:
    """
    Bidirectional NLI check (entailment isn't symmetric, so both
    directions are run, same as R45's validation methodology) between
    `original_sentence` and `candidate_sentence`. Returns None if the
    model is unavailable -- fails closed to "no signal," never raises.

    Returns:
      {"fwd_label": "contradiction"|"entailment"|"neutral",
       "rev_label": "contradiction"|"entailment"|"neutral",
       "contradiction": bool}   # True if EITHER direction predicts contradiction

    Reported-only by design, same discipline as contextual_fit_score()
    (Practice.md §10) -- this function does not gate anything on its own;
    callers decide what to do with the result.
    """
    if not _nli_ok and not load_nli_model():
        return None
    try:
        fwd, rev = _nli_model.predict([
            (original_sentence, candidate_sentence),
            (candidate_sentence, original_sentence),
        ])
        id2label = _nli_model.model.config.id2label
        fwd_label = id2label[int(fwd.argmax())]
        rev_label = id2label[int(rev.argmax())]
        return {
            "fwd_label": fwd_label,
            "rev_label": rev_label,
            "contradiction": fwd_label == "contradiction" or rev_label == "contradiction",
        }
    except Exception:
        return None


# ── Grammaticality check, second attempt (R45, VALIDATION.md §36.1) ──────────
# R28 found LanguageTool 0/7 against a DIFFERENT error class ("syntactically
# well-formed sentences built from the wrong word"). R45 re-tested it against
# R40's actual grammar-corruption class (agreement breaks, non-standard
# plurals, a noun used as a verb) and found a real, if partial, positive:
# ~20-25% recall there, non-overlapping with the NLI check above.
#
# Deliberately a SEPARATE LanguageTool instance from grammar.py's
# `_get_lt_tool()` (used by sanitize_input()'s existing, currently-dormant
# Layer 10) -- not shared, on purpose. Loading this one requires prepending
# a portable JRE to PATH (R28's workaround: no system Java is installed in
# this environment); since PATH mutation is process-global, calling this
# loader may ALSO make grammar.py's dormant LanguageTool layer start
# succeeding for the rest of the process. That's a disclosed side effect,
# not a hidden one -- it only happens if something actually calls
# load_grammar_tool(), which nothing in the existing reformulate()/
# sanitize_input() path does.
_grammar_tool = None
_grammar_tool_ok = False
_grammar_tool_message = ""


def load_grammar_tool() -> bool:
    """Load a standalone LanguageTool instance for grammar_issue_count()
    below. Same graceful-degradation shape as this module's other
    loaders. See this section's module comment for the PATH side effect."""
    global _grammar_tool, _grammar_tool_ok, _grammar_tool_message
    if _grammar_tool_ok:
        return True
    try:
        import os
        from pathlib import Path
        from language_tool_python import LanguageTool

        root = Path(__file__).resolve().parent
        jre_bin = root / ".cache" / "jre17" / "bin"
        if jre_bin.exists():
            os.environ.pop("LTP_PATH", None)  # R28: paths.py's redirect reproducibly fails
            os.environ["PATH"] = str(jre_bin) + os.pathsep + os.environ.get("PATH", "")

        _grammar_tool = LanguageTool("en-US")
        _grammar_tool_ok = True
        _grammar_tool_message = "LanguageTool loaded successfully."
        return True
    except Exception as exc:
        _grammar_tool_ok = False
        _grammar_tool_message = f"LanguageTool unavailable ({exc.__class__.__name__}: {exc})."
        return False


def grammar_status() -> tuple[bool, str]:
    """Return (is_loaded, human_readable_message)."""
    return _grammar_tool_ok, _grammar_tool_message


def grammar_issue_count(sentence: str) -> Optional[int]:
    """
    Number of LanguageTool matches against `sentence`, or None if the
    tool is unavailable. Reported-only by design (Practice.md §10) --
    a nonzero count is a signal, not an automatic rejection; callers
    decide what to do with it.
    """
    if not _grammar_tool_ok and not load_grammar_tool():
        return None
    try:
        return len(_grammar_tool.check(sentence))
    except Exception:
        return None


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


def _matches_idiom_pattern(window: list[str], pattern_words: list[str]) -> bool:
    """window and pattern_words are the same length (caller's job). A
    pattern word of `{pron}` matches any word in _IDIOM_PRONOUNS; every
    other pattern word must match literally."""
    for w, p in zip(window, pattern_words):
        if p == "{pron}":
            if w not in _IDIOM_PRONOUNS:
                return False
        elif w != p:
            return False
    return True


def idiom_spans(tokens: list[str]) -> list[tuple[int, int]]:
    """Ordered list of (start, end) [end exclusive] spans matched by
    IDIOM_PHRASES/IDIOM_PHRASE_PATTERNS — the structured form
    idiom_protected_positions() flattens into a position set below.

    reformulate.py's phrase-level replacement tier (REFORMULATION_
    PROBLEM_MAP.md SS3.8/SS5 item 4) needs the actual span boundaries,
    not just which positions are protected, to know exactly what
    contiguous stretch to replace and splice back in."""
    spans: list[tuple[int, int]] = []
    lower_tokens = [t.lower() for t in tokens]

    for phrase in IDIOM_PHRASES:
        words = phrase.split()
        n = len(words)
        for i in range(len(lower_tokens) - n + 1):
            if lower_tokens[i : i + n] == words:
                spans.append((i, i + n))

    for pattern in IDIOM_PHRASE_PATTERNS:
        pattern_words = pattern.split()
        n = len(pattern_words)
        for i in range(len(lower_tokens) - n + 1):
            if _matches_idiom_pattern(lower_tokens[i : i + n], pattern_words):
                spans.append((i, i + n))

    spans.sort()
    return spans


def idiom_protected_positions(tokens: list[str]) -> set[int]:
    """The subset of protected_positions() covering ONLY idiom/fixed-
    expression spans (IDIOM_PHRASES, IDIOM_PHRASE_PATTERNS) — not the
    connector phrases in PROTECTED_PHRASES or the single stop words in
    _PROTECTED_SINGLE.

    reformulate.py needs this distinction, not just the union
    protected_positions() gives: a stop word or connector phrase was
    never a real difficulty candidate, so silently excluding it from
    flagged-word counts is correct. An idiom-locked content word CAN
    genuinely match the speaker's declared difficulty (e.g. "going"
    matching a declared /g/ sound inside "how's it going") — deliberately
    leaving it unsubstituted must stay visible in reporting, not silently
    make the difficulty count as resolved (or as never having existed).
    Found as a follow-up correctness issue while testing the idiom guard
    itself — see REFORMULATION_PROBLEM_MAP.md SS5 item 1's own entry.
    """
    protected: set[int] = set()
    for start, end in idiom_spans(tokens):
        protected.update(range(start, end))
    return protected


def protected_positions(tokens: list[str]) -> set[int]:
    """
    Return the set of token indices that must never be substituted.

    Covers three categories:
      1. Idiom/fixed-expression spans (idiom_protected_positions() above).
      2. Multi-word connector phrases (PROTECTED_PHRASES).
      3. Single-token stop words: auxiliaries, pronouns, determiners,
         prepositions, and discourse particles (_PROTECTED_SINGLE).

    Keeping all three in one function means the grammar layer (_STOP) and
    the semantic/UI layer stay in sync — there is no risk of protected
    single words or idiom spans being left exposed when one check misses
    them but another would have caught them.
    """
    protected: set[int] = set(idiom_protected_positions(tokens))

    lower_tokens = [t.lower() for t in tokens]

    # 2. Multi-word connector phrases (exact match)
    for phrase in PROTECTED_PHRASES:
        words = phrase.split()
        n = len(words)
        for i in range(len(lower_tokens) - n + 1):
            if lower_tokens[i : i + n] == words:
                protected.update(range(i, i + n))

    # 3. Single-token stop words
    for i, lt in enumerate(lower_tokens):
        if lt in _PROTECTED_SINGLE:
            protected.add(i)

    return protected


# ── Word-sense disambiguation (candidate-generation gloss matching) ──────────
#
# engine.py's _wordnet_synonyms() crawls every same-POS synset for a word and
# unions their synonyms — no sense selection. Found directly (REFORMULATION_
# PROBLEM_MAP.md SS2.6, item 2): wn.synsets("right", pos=wn.ADV) has 9 senses
# ("immediately" alongside "properly"/"justly"/"correctly"/"mighty"), and
# without picking the right one first, all 9 senses' synonyms end up in one
# candidate pool ranked by frequency alone — which is exactly how "right" in
# "right now" got replaced with "justly"/"properly" (VALIDATION.md SS9.9).
#
# Fix: before generating candidates for a word, pick the ONE synset whose
# gloss (definition) best matches the sentence it's actually being used in,
# via the same SBERT model already loaded for everything else here — no new
# dependency, no training (REFORMULATION_PROBLEM_MAP.md SS3.2/SS4 ranked this
# the small-effort option over pywsd).

def disambiguate_synset(word: str, wn_pos, sentence: str):
    """Return the single WordNet synset (of `word`, restricted to `wn_pos`)
    whose gloss best matches `sentence`'s context, or None if disambiguation
    isn't possible/needed:
      - `wn_pos` is None (word-mode, no POS to disambiguate within), or
      - the word has 0 or 1 synsets at that POS (nothing to choose between —
        the existing all-senses behavior is already correct), or
      - SBERT is unavailable (graceful fallback to the pre-existing
        all-senses behavior, same pattern as every other SBERT-optional path
        in this module).

    A None return means "don't restrict" — callers should fall back to their
    current behavior, not treat None as an error.
    """
    if wn_pos is None:
        return None
    synsets = wn.synsets(word, pos=wn_pos)
    if len(synsets) <= 1:
        return None
    if not _sbert_ok or _sbert_model is None:
        return None

    glosses = [s.definition() for s in synsets]
    embs = _sbert_model.encode([sentence] + glosses)
    sentence_emb = embs[0]
    best_i, best_score = 0, -1.0
    for i, gloss_emb in enumerate(embs[1:]):
        score = _cosine(sentence_emb, gloss_emb)
        if score > best_score:
            best_i, best_score = i, score
    return synsets[best_i]


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


# ── Antonym check (REFORMULATION_RESEARCH.md §24.A tier 1 — free, zero-model) ──
# The rest of this module's checks (SBERT, and NLI when it's added) are proxies
# that can miss a candidate whose surface form is fine but whose meaning is the
# opposite of the original word — WordNet's own antonym relation catches the
# specific, named case (RESEARCH.md §2.D's negation/antonym finding) at zero
# cost, with no model inference at all. Deliberately narrow: it only rejects a
# *direct*, dictionary-listed antonym relationship, not general "too different"
# meaning drift (that's what the SBERT gate downstream is for).

def is_known_antonym(original_lemma: str, candidate_lemma: str, wn_pos=None) -> bool:
    """
    True if WordNet lists *candidate_lemma* as a direct antonym of any sense
    of *original_lemma* (optionally restricted to a POS). Checked in both
    directions since WordNet's antonym links aren't guaranteed symmetric in
    practice for every sense.
    """
    a = (original_lemma or "").strip().lower()
    b = (candidate_lemma or "").strip().lower()
    if not a or not b or a == b:
        return False
    for synset in wn.synsets(a, pos=wn_pos):
        for lemma in synset.lemmas():
            if lemma.name().replace("_", " ").lower() != a:
                continue
            for ant in lemma.antonyms():
                if ant.name().replace("_", " ").lower() == b:
                    return True
    # Reverse direction — candidate's synsets listing the original as an antonym.
    for synset in wn.synsets(b, pos=wn_pos):
        for lemma in synset.lemmas():
            if lemma.name().replace("_", " ").lower() != b:
                continue
            for ant in lemma.antonyms():
                if ant.name().replace("_", " ").lower() == a:
                    return True
    return False


# ── Sentence-level negation-consistency check (for the T5 escalation path) ────
# bad_words_ids/antonym-lookup both operate at the single-word level and don't
# apply to a freely-generated paraphrase candidate. This is the cheap,
# sentence-level analogue used there instead: a paraphrase that drops or adds
# a negation marker relative to the original is exactly the failure mode
# RESEARCH.md §2.D names (SBERT alone can miss it), so check it directly rather
# than trusting SBERT similarity alone for this one specific pattern.
_NEGATION_MARKERS = frozenset({
    "not", "n't", "never", "no", "none", "nobody", "nothing", "nowhere",
    "neither", "nor", "cannot", "can't", "won't", "isn't", "aren't",
    "wasn't", "weren't", "don't", "doesn't", "didn't", "hasn't", "haven't",
    "hadn't", "shouldn't", "wouldn't", "couldn't",
})


def negation_marker_count(text: str) -> int:
    tokens = re.findall(r"[A-Za-z']+", (text or "").lower())
    return sum(1 for t in tokens if t in _NEGATION_MARKERS)


def negation_consistent(original_text: str, candidate_text: str) -> bool:
    """True if the candidate has the same negation-marker count as the
    original — a cheap, sentence-level proxy for 'this paraphrase didn't
    flip or drop a negation,' the specific failure mode a raw SBERT score
    can miss (RESEARCH.md §2.D)."""
    return negation_marker_count(original_text) == negation_marker_count(candidate_text)


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
