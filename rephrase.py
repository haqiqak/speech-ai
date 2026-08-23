"""
rephrase.py - optional fluency repair layer for synonym-built sentences.

This module is deliberately standalone. It is not imported by grammar.py or
engine.py, and it degrades to passthrough if transformers/torch or the model
weights are unavailable. Model weights are downloaded on first use into the
project-local ./.cache folder configured by paths.py.
"""

from __future__ import annotations

import paths  # noqa: F401 - keeps HF/torch caches inside ./.cache

import difflib
import os
import re
from pathlib import Path
from typing import Any

import phonetic
import semantic
from semantic import _PROTECTED_SINGLE

try:  # Safe import: app behavior must not depend on these being installed.
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, LogitsProcessor, LogitsProcessorList
    _STACK_OK = True
    _STACK_ERROR = ""
except Exception as exc:  # pragma: no cover - depends on local environment
    torch = None
    AutoModelForSeq2SeqLM = None
    AutoTokenizer = None
    LogitsProcessor = object  # placeholder base so the class body below still parses
    LogitsProcessorList = None
    _STACK_OK = False
    _STACK_ERROR = f"{exc.__class__.__name__}: {exc}"


# Current model is Vamsi/T5, however we can also use this code with humarin/chatgpt_paraphraser_on_T5_base if desired by replacing these 2 lines below.
#REPHRASE_MODEL = os.environ.get("REPHRASE_MODEL", "humarin/chatgpt_paraphraser_on_T5_base")
#REPHRASE_PREFIX = os.environ.get("REPHRASE_PREFIX", "")

REPHRASE_MODEL = os.environ.get("REPHRASE_MODEL", "Vamsi/T5_Paraphrase_Paws")
REPHRASE_PREFIX = os.environ.get("REPHRASE_PREFIX", "paraphrase: ") 

REPHRASE_DEVICE = os.environ.get("REPHRASE_DEVICE", "cpu")
REPHRASE_CACHE = Path(__file__).resolve().parent / ".cache" / "hf" / "rephrase"
REPHRASE_CACHE.mkdir(parents=True, exist_ok=True)

_tokenizer = None
_model = None
_load_tried = False
_rephrase_ok = False
_status = "Rephrase model not loaded."


def _load_model() -> bool:
    """Lazy-load the rephrase model. Returns False on any failure."""
    global _tokenizer, _model, _load_tried, _rephrase_ok, _status
    if _rephrase_ok:
        return True
    if _load_tried:
        return False
    _load_tried = True

    if not _STACK_OK:
        _status = f"Rephrase unavailable ({_STACK_ERROR})."
        return False

    try:
        _tokenizer = AutoTokenizer.from_pretrained(
            REPHRASE_MODEL,
            cache_dir=str(REPHRASE_CACHE),
        )
        _model = AutoModelForSeq2SeqLM.from_pretrained(
            REPHRASE_MODEL,
            cache_dir=str(REPHRASE_CACHE),
            # Incremental, meta-device loading avoids the transient 2x weight
            # allocation (init full model + load state dict) that OOMs / segfaults
            # on low-RAM machines. Requires `accelerate`.
            low_cpu_mem_usage=True,
        )
        device = REPHRASE_DEVICE
        if device != "cpu" and torch is not None and not torch.cuda.is_available():
            device = "cpu"
        _model.to(device)
        _model.eval()
        _rephrase_ok = True
        _status = f"Rephrase model '{REPHRASE_MODEL}' loaded on {device}."
        return True
    except Exception as exc:  # pragma: no cover - network/model dependent
        _tokenizer = None
        _model = None
        _rephrase_ok = False
        _status = f"Rephrase unavailable ({exc.__class__.__name__}: {exc})."
        return False


def rephrase_status(load: bool = False) -> tuple[bool, str]:
    """Return (is_loaded, human-readable status)."""
    if load:
        _load_model()
    return _rephrase_ok, _status


def _bad_words_ids(blocked_words) -> list[list[int]] | None:
    """
    Block each word regardless of case. T5's SentencePiece tokenizer
    assigns different token IDs to "researcher" vs "Researcher" (verified
    directly — VALIDATION.md §6.3 Cause A), so encoding only the form the
    caller happened to pass in left every other-cased occurrence of the
    same word free to generate — confirmed empirically: with only the
    lowercase form blocked, the lowercase token leaked in 0/6 beam
    outputs while the capitalized form of the identical word leaked in
    5/6. Encoding the lowercase and capitalized forms (each with and
    without a leading space, since a leading space frequently changes the
    token boundary for this tokenizer) closes that gap without touching
    anything else about generation.
    """
    if _tokenizer is None or not blocked_words:
        return None
    ids: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    for raw in blocked_words:
        word = str(raw or "").strip()
        if not word:
            continue
        variants = {word, word.lower(), word.capitalize()}
        for variant in variants:
            for form in (variant, " " + variant):
                encoded = _tokenizer.encode(form, add_special_tokens=False)
                if encoded:
                    sig = tuple(encoded)
                    if sig not in seen:
                        seen.add(sig)
                        ids.append(encoded)
    return ids or None


def _clean_generation(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    return text


def generate_candidates(
    sentence: str,
    k: int = 5,
    blocked_words=None,
) -> list[str]:
    """
    Generate up to k distinct rephrase candidates.

    The input sentence is always included. If the model cannot load, returns
    [sentence] without raising.
    """
    base = _clean_generation(sentence)
    candidates: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        cleaned = _clean_generation(text)
        sig = cleaned.lower()
        if cleaned and sig not in seen:
            seen.add(sig)
            candidates.append(cleaned)

    add(base)

    if not base or k <= 1 or not _load_model():
        return candidates[: max(k, 1)]

    try:
        assert _tokenizer is not None and _model is not None
        prompt = REPHRASE_PREFIX + base
        encoded = _tokenizer(prompt, return_tensors="pt", truncation=True)
        device = next(_model.parameters()).device
        encoded = {key: val.to(device) for key, val in encoded.items()}
        in_len = int(encoded["input_ids"].shape[1])
        max_new_tokens = max(16, int(in_len * 1.5) + 8)
        beams = max(4, min(12, k * 2))
        bad_ids = _bad_words_ids(blocked_words)
        kwargs: dict[str, Any] = {
            "num_beams": beams,
            "num_return_sequences": min(beams, max(k * 2, k)),
            "max_new_tokens": max_new_tokens,
            "no_repeat_ngram_size": 3,
            "early_stopping": True,
        }
        if bad_ids:
            kwargs["bad_words_ids"] = bad_ids
        with torch.no_grad():
            outputs = _model.generate(**encoded, **kwargs)
        for output in outputs:
            add(_tokenizer.decode(output, skip_special_tokens=True))
            if len(candidates) >= k:
                break
    except Exception as exc:  # pragma: no cover - model dependent
        global _status
        _status = f"Rephrase generation failed ({exc.__class__.__name__}: {exc})."

    return candidates[: max(k, 1)]


# ── Phoneme-aware decoding-time constraint (VALIDATION.md §36.2, R45) ────────
# generate_candidates() above only blocks NAMED words via bad_words_ids -- it
# has no way to express "avoid this SOUND." R43's instrumentation found that
# was the dominant escalation-tier failure: 96% of candidates leaked the
# flagged sound even when they cleared every other gate. R45 prototyped, and
# measured, a decoding-time fix instead of a post-hoc one: a LogitsProcessor
# that kills a beam the moment any word in its in-progress text -- complete
# or still-forming, as soon as its onset is determinable -- matches the
# profile's blocked sound patterns (phonetic.matches_any, the same check the
# production phoneme veto already uses everywhere else). Measured result:
# leak-free rate 4% -> 100%, cases with any usable candidate 9% -> 52% on
# R43's 23-case corpus (VALIDATION.md §36.2). A direct manual read found the
# remaining defects are meaning/logic/grammar issues, not leaks -- exactly
# what semantic.py's logical_consistency_check()/grammar_issue_count() (also
# added this pass) are for, not this function's job.
#
# Deliberately a SEPARATE function from generate_candidates(), not a new
# parameter on it -- additive, not a replacement, so every existing caller
# (grammar.py's choose_best(), reformulate.py's _try_escalation()) is
# completely unaffected. reformulate.py's NEW _try_escalation_v2() (R45's
# recommended combined architecture) calls this one instead.

class PhonemeConstraintLogitsProcessor(LogitsProcessor):
    """Sets a beam's score to -inf the moment its decoded text-so-far
    contains a word matching `blocked_patterns` -- checked every step,
    against every word including the still-forming last one, so a
    violation is caught as soon as its onset is determinable rather than
    only after the whole candidate is finished.

    `decoder_start_len` is how many leading tokens of `input_ids` are the
    decoder's own start token(s), not generated text -- T5 uses exactly
    one (`decoder_start_token_id`), so the default of 1 is correct for
    this project's model family; passed explicitly rather than hardcoded
    so this class stays reusable if that ever changes.
    """

    def __init__(self, tokenizer, blocked_patterns: list[str], decoder_start_len: int = 1):
        self.tokenizer = tokenizer
        self.blocked_patterns = [p for p in (blocked_patterns or []) if p]
        self.decoder_start_len = decoder_start_len
        self.kill_count = 0

    def __call__(self, input_ids, scores):
        if not self.blocked_patterns:
            return scores
        for i in range(input_ids.shape[0]):
            if torch.isneginf(scores[i]).all():
                continue  # already dead this generation -- skip re-decoding
            gen_ids = input_ids[i, self.decoder_start_len:]
            if gen_ids.numel() == 0:
                continue
            text = self.tokenizer.decode(gen_ids, skip_special_tokens=True)
            for w in re.findall(r"[A-Za-z][A-Za-z'-]*", text):
                if phonetic.matches_any(w, self.blocked_patterns):
                    scores[i, :] = float("-inf")
                    self.kill_count += 1
                    break
        return scores


def generate_candidates_phoneme_constrained(
    sentence: str,
    k: int = 5,
    blocked_words=None,
    blocked_patterns=None,
) -> tuple[list[str], dict]:
    """
    Same contract and defaults as generate_candidates() (base sentence
    always included, degrades to passthrough if the model can't load),
    PLUS a decoding-time phoneme constraint on top of the existing
    bad_words_ids literal-word blocking. `blocked_patterns` is the
    profile's declared sound patterns (DifficultyProfile.sound_values());
    `blocked_words` is unchanged from generate_candidates() -- the
    literal named words, blocked the same way.

    Returns (candidates, stats) where stats['beam_kills'] reports how
    many beam-steps the phoneme processor actually intervened on, for
    diagnostic visibility -- not used by callers, but cheap to keep.
    """
    base = _clean_generation(sentence)
    if not base or k <= 1 or not _load_model():
        return [base] if base else [], {"beam_kills": 0, "model_unavailable": True}

    try:
        prompt = REPHRASE_PREFIX + base
        encoded = _tokenizer(prompt, return_tensors="pt", truncation=True)
        device = next(_model.parameters()).device
        encoded = {key: val.to(device) for key, val in encoded.items()}
        in_len = int(encoded["input_ids"].shape[1])
        max_new_tokens = max(16, int(in_len * 1.5) + 8)
        beams = max(4, min(12, k * 2))
        bad_ids = _bad_words_ids(blocked_words)
        processor = PhonemeConstraintLogitsProcessor(_tokenizer, blocked_patterns)

        kwargs: dict[str, Any] = {
            "num_beams": beams,
            "num_return_sequences": min(beams, max(k * 2, k)),
            "max_new_tokens": max_new_tokens,
            "no_repeat_ngram_size": 3,
            "early_stopping": True,
            "logits_processor": LogitsProcessorList([processor]),
        }
        if bad_ids:
            kwargs["bad_words_ids"] = bad_ids

        with torch.no_grad():
            outputs = _model.generate(**encoded, **kwargs)

        candidates: list[str] = []
        seen: set[str] = set()
        for output in outputs:
            text = _clean_generation(_tokenizer.decode(output, skip_special_tokens=True))
            sig = text.lower()
            if text and sig not in seen:
                seen.add(sig)
                candidates.append(text)
                if len(candidates) >= k:
                    break

        return candidates[:k], {"beam_kills": processor.kill_count}
    except Exception as exc:  # pragma: no cover - model dependent
        global _status
        _status = f"Phoneme-constrained generation failed ({exc.__class__.__name__}: {exc})."
        return [base], {"beam_kills": 0, "error": str(exc)}


def _content_words(sentence: str) -> list[str]:
    out: list[str] = []
    for token in re.findall(r"[A-Za-z][A-Za-z'-]*", sentence or ""):
        low = token.strip("-'").lower()
        if low and low not in _PROTECTED_SINGLE:
            out.append(token)
    return out


def _rough_lemma(word: str) -> str:
    low = re.sub(r"[^a-z]", "", word.lower())
    if len(low) > 5 and low.endswith("ies"):
        return low[:-3] + "y"
    if len(low) > 5 and low.endswith("ing"):
        stem = low[:-3]
        if len(stem) > 2 and stem[-1] == stem[-2]:
            stem = stem[:-1]
        return stem
    if len(low) > 4 and low.endswith("ed"):
        return low[:-2]
    if len(low) > 3 and low.endswith("s"):
        return low[:-1]
    return low


def _violations(sentence: str, patterns, blocked) -> int:
    patterns = [p for p in (patterns or []) if p and str(p).strip()]
    blocked_lows = {str(w).lower() for w in (blocked or set()) if str(w).strip()}
    count = 0
    for word in _content_words(sentence):
        low = word.lower().strip("-'")
        lemma = _rough_lemma(word)
        if low in blocked_lows or lemma in blocked_lows or phonetic.matches_any(word, patterns):
            count += 1
    return count


def _score_candidate(
    original_sentence: str,
    synonym_sentence: str,
    candidate: str,
    patterns,
    blocked,
    weights: dict[str, float],
) -> dict:
    sim = semantic.semantic_similarity(candidate, original_sentence)
    words = _content_words(candidate)
    difficulty = phonetic.sentence_difficulty(words)
    violations = _violations(candidate, patterns, blocked)
    edit = 1.0 - difflib.SequenceMatcher(
        None, synonym_sentence.lower(), candidate.lower()
    ).ratio()
    score = (
        weights["w_sim"] * (sim or 0.0)
        - weights["w_diff"] * difficulty
        - weights["w_viol"] * violations
        - weights["w_edit"] * edit
    )
    return {
        "text": candidate,
        "sim": round(sim, 4) if sim is not None else None,
        "violations": violations,
        "difficulty": difficulty,
        "score": round(score, 4),
    }


def choose_best(
    original_sentence: str,
    synonym_sentence: str,
    patterns,
    blocked,
    sim_gate: float = 0.80,
    weights: dict[str, float] | None = None,
) -> dict:
    """
    Pick the best fluency candidate while preserving meaning and profile safety.

    If the rephrase model is unavailable, returns synonym_sentence unchanged.
    If SBERT is unavailable, the similarity gate is skipped.
    """
    active_weights = {
        "w_sim": 1.0,
        "w_diff": 0.6,
        "w_viol": 1.0,
        "w_edit": 0.4,
    }
    if weights:
        active_weights.update(weights)

    model_ok = _load_model()
    generated = generate_candidates(synonym_sentence, k=5, blocked_words=blocked)
    all_texts: list[str] = []
    seen: set[str] = set()
    for text in [synonym_sentence, *generated]:
        cleaned = _clean_generation(text)
        sig = cleaned.lower()
        if cleaned and sig not in seen:
            seen.add(sig)
            all_texts.append(cleaned)

    scored = [
        _score_candidate(
            original_sentence, synonym_sentence, candidate, patterns, blocked, active_weights
        )
        for candidate in all_texts
    ]

    passing = [
        row for row in scored
        if row["sim"] is None or row["sim"] >= sim_gate
    ]
    if not model_ok or not passing:
        chosen = _score_candidate(
            original_sentence, synonym_sentence, synonym_sentence,
            patterns, blocked, active_weights,
        )
        return {
            "rephrased": synonym_sentence,
            "applied": False,
            "sim": chosen["sim"],
            "violations": chosen["violations"],
            "difficulty": chosen["difficulty"],
            "candidates": scored,
        }

    passing.sort(key=lambda row: (row["violations"] != 0, -row["score"]))
    best = passing[0]
    applied = best["text"].strip().lower() != synonym_sentence.strip().lower()
    return {
        "rephrased": best["text"],
        "applied": applied,
        "sim": best["sim"],
        "violations": best["violations"],
        "difficulty": best["difficulty"],
        "candidates": scored,
    }


if __name__ == "__main__":
    original = "The presenter discussed a strong project plan."
    synonym_sentence = "The speaker discussed a solid project plan."
    profile_patterns = ["pr", "str"]
    profile_blocked = {"present"}
    result = choose_best(
        original,
        synonym_sentence,
        profile_patterns,
        profile_blocked,
    )
    ok, msg = rephrase_status()
    print(msg)
    if not ok:
        print("Passthrough:", result["rephrased"])
    else:
        print("Applied:", result["applied"])
        print("Rephrased:", result["rephrased"])
    print("Candidates:")
    for row in result["candidates"]:
        print(
            f"- {row['text']} | sim={row['sim']} "
            f"viol={row['violations']} diff={row['difficulty']} score={row['score']}"
        )
