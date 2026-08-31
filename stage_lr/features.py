"""
stage_lr/features.py — Stage LR's profile-conditioned feature extractor (LR.2).

Turns (sentence, candidate, DifficultyProfile) into an inspectable
scorecard, reusing only already-validated signals from the frozen
pipeline as libraries (semantic.py, phonetic.py, difficulty_profile.py)
— no duplicated scoring logic, no changes to any frozen file. Not
imported by app.py or reformulate.py; not wired into any live path.
Read-only consumer, produces a scorecard, does not rank/reject/gate
anything — ranking policy is LR.3's job, a separate, later decision.

Design constraints carried over from Stage LR's own prior decisions —
each one exists to prevent a specific, already-identified failure mode,
not by convention:

  - Reads `sounds`/`words`/`phrases` directly from `DifficultyProfile`,
    never through the `stutter_patterns`/`blocked_words` legacy bridge
    (`STAGE_LR_PROPOSAL_REVIEW.md` §2.1). Concretely: a `sounds` entry's
    already-correct ARPAbet key (`entry.normalized`) is compared
    directly against `phonetic.onset()`'s output — never re-derived
    from the entry's display spelling via `phonetic.normalize_pattern()`,
    which is the exact lossy round-trip behind the ZH bug
    (`PROBLEM_FORMULATION.md` §11.2).
  - A word's `problem_phones` is never generalized into a rule about
    other words sharing that phone — only an exact profile.words /
    profile.phrases match counts as "this candidate collides with the
    profile." Promotion to a general phone rule is `add_sound_from_phones()`,
    always an explicit user action, never automatic
    (`LEARNED_REFORMULATION_RESEARCH.md`, Matter 1, 2026-08-30-D/E).
  - A phrase's phone sequence is a fingerprint of that phrase, compared
    fingerprint-to-fingerprint against declared phrases only — never
    unpacked into per-word claims (same Matter 1 decision).
  - No allowlist term. The proposal's hard-gate term assumed a live
    `allowlist_words` field that does not exist in the current schema
    (`STAGE_LR_PROPOSAL_REVIEW.md` §2.1) — dropped from this v1 rather
    than faked.
  - `contextual_fit_score()` is only computed for single-word
    substitution candidates, per its own validated scope
    (`semantic.py`'s docstring) — not called for phrase-tier or
    restructuring candidates.
"""
import paths  # noqa: F401

from dataclasses import dataclass, field
from typing import Optional

import difficulty_profile as dp
import phonetic
import semantic


@dataclass
class CandidateScore:
    candidate: str
    source: str
    meaning_sbert: Optional[float] = None
    meaning_meaningbert: Optional[float] = None
    naturalness_contextual_fit: Optional[float] = None
    phoneme_difficulty: float = 0.0
    phoneme_difficulty_reasons: list[str] = field(default_factory=list)
    pronunciation_ambiguous: bool = False


def _word_onset_hits(word: str, profile: dp.DifficultyProfile) -> list[str]:
    """Which of the profile's global `sounds` entries this word's real
    onset matches, using each entry's stored ARPAbet key directly."""
    onset = phonetic.onset(word)
    if not onset:
        return []
    hits = []
    for entry in profile.sounds:
        pattern = tuple(p for p in entry.normalized.split() if p)
        if pattern and onset[: len(pattern)] == pattern:
            hits.append(entry.value)
    return hits


def _is_declared_difficult_word(word: str, profile: dp.DifficultyProfile) -> bool:
    """Exact match only. Does not read a word's own `problem_phones` as a
    rule about any other word — that generalization is never automatic
    (Matter 1)."""
    w = (word or "").strip().lower()
    return any(e.normalized == w for e in profile.words)


def _phrase_phone_fingerprint(phrase_words: list[str]) -> Optional[tuple[str, ...]]:
    """Matter 1's phrase representation: concatenate each word's real
    `full_pronunciation()`; OOV words contribute no phones (no guessing,
    matching `full_pronunciation()`'s own no-fabrication policy). None
    if every word was OOV — "no signal," not a fabricated one."""
    phones: list[str] = []
    any_known = False
    for w in phrase_words:
        p = phonetic.full_pronunciation(w)
        if p:
            any_known = True
            phones.extend(p)
    return tuple(phones) if any_known else None


def _is_declared_difficult_phrase(phrase_words: list[str], profile: dp.DifficultyProfile) -> bool:
    """Fingerprint-to-fingerprint only — never unpacks a phrase match into
    per-word claims about the words inside it (Matter 1's scoping
    guardrail, 2026-08-30-E)."""
    candidate_fp = _phrase_phone_fingerprint(phrase_words)
    if candidate_fp is None:
        return False
    for entry in profile.phrases:
        declared_fp = _phrase_phone_fingerprint(entry.normalized.split())
        if declared_fp is not None and declared_fp == candidate_fp:
            return True
    return False


def score_candidate(
    original_sentence: str,
    candidate_sentence: str,
    candidate_text: str,
    profile: dp.DifficultyProfile,
    *,
    source: str = "substitution",
    occurrence: int = 0,
) -> CandidateScore:
    """
    Score one reformulation candidate against a speaker's declared
    profile. `candidate_text` is the changed span only — the
    replacement word (source="substitution") or replacement phrase
    (source="phrase") — not the whole sentence.
    """
    score = CandidateScore(candidate=candidate_text, source=source)

    # -- meaning: the two independently-trained signals already
    # validated in the frozen pipeline, called as-is. semantic.py's own
    # load functions are inconsistent about auto-loading on first call --
    # meaningbert_score()/contextual_fit_score() both do
    # ("if not X_ok and not load_X(): return None"), but
    # semantic_similarity() does NOT (it only checks the already-set
    # flag). Found by direct comparison against real output, not
    # assumed: without this explicit call, SBERT silently returns None
    # on every invocation in a fresh process, degrading "meaning" to
    # MeaningBERT alone with no visible error. Idempotent, per
    # reformulate.py's own use of the same call.
    semantic.load_sbert()
    score.meaning_sbert = semantic.semantic_similarity(original_sentence, candidate_sentence)
    score.meaning_meaningbert = semantic.meaningbert_score(original_sentence, candidate_sentence)

    words = candidate_text.strip().split()

    # -- naturalness: only single-word substitutions, per
    # contextual_fit_score()'s own validated scope ---------------------
    if source == "substitution" and len(words) == 1:
        score.naturalness_contextual_fit = semantic.contextual_fit_score(
            candidate_sentence, candidate_text, occurrence=occurrence
        )

    # -- phoneme difficulty: profile.sounds (global onset) + exact
    # word/phrase matches only. problem_phones is deliberately not
    # read here -- it identifies why the ORIGINAL word was flagged for
    # substitution (reformulate.py's job), not a rule about candidates.
    if source == "phrase" or len(words) > 1:
        if _is_declared_difficult_phrase(words, profile):
            score.phoneme_difficulty = 1.0
            score.phoneme_difficulty_reasons.append("matches a declared difficult phrase (fingerprint)")
    else:
        onset_hits = _word_onset_hits(candidate_text, profile)
        if onset_hits:
            score.phoneme_difficulty = 1.0
            score.phoneme_difficulty_reasons.append(f"onset matches declared sound(s): {onset_hits}")
        if _is_declared_difficult_word(candidate_text, profile):
            score.phoneme_difficulty = 1.0
            score.phoneme_difficulty_reasons.append("candidate itself is a declared difficult word")

    # -- ceiling (4) fix (Matter 1, 2026-08-30-D): flag pronunciation
    # ambiguity on the candidate word itself, using the existing
    # detector -- no new instrumentation. Caller's job to exclude/
    # down-weight; this only surfaces the flag. ------------------------
    if len(words) == 1:
        score.pronunciation_ambiguous = phonetic.pronunciation_variant_count(candidate_text) > 1

    return score
