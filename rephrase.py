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
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    _STACK_OK = True
    _STACK_ERROR = ""
except Exception as exc:  # pragma: no cover - depends on local environment
    torch = None
    AutoModelForSeq2SeqLM = None
    AutoTokenizer = None
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
    if _tokenizer is None or not blocked_words:
        return None
    ids: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    for raw in blocked_words:
        word = str(raw or "").strip()
        if not word:
            continue
        for form in (word, " " + word):
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
