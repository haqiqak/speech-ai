"""Candidate generation for profile-aware rewriting."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Iterable

import nltk
from nltk import pos_tag, word_tokenize

import semantic
from engine import SynonymEngine
from grammar import _SUBSTITUTABLE, _STOP, _wn_pos, lemmatize


FALLBACK_SYNONYMS: dict[str, list[str]] = {
    "big": ["large", "major", "great"],
    "begin": ["start", "open", "launch"],
    "begins": ["starts", "opens"],
    "buy": ["purchase", "get"],
    "difficult": ["hard", "tough"],
    "important": ["key", "vital", "main"],
    "project": ["plan", "task", "work"],
    "present": ["show", "share", "offer"],
    "strong": ["solid", "firm"],
    "speak": ["talk", "say"],
    "speech": ["talk", "address"],
}


@dataclass
class CandidateSlot:
    position: int
    word: str
    tag: str
    lemma: str
    candidates: list[str]
    protected: bool = False


def safe_word_tokenize(text: str) -> list[str]:
    try:
        return word_tokenize(text)
    except Exception:
        return re.findall(r"[A-Za-z][A-Za-z'-]*|[.,!?;:]", text or "")


def safe_pos_tag(tokens: list[str]) -> list[tuple[str, str]]:
    try:
        nltk.download("averaged_perceptron_tagger_eng", quiet=True)
        return pos_tag(tokens)
    except Exception:
        return [(tok, "NN") for tok in tokens]


def detect_protected_words(text: str, always_keep: Iterable[str] | None = None) -> set[str]:
    """Return lower-case protected words from NER/proper-noun heuristics."""

    protected = {str(w).strip().lower() for w in (always_keep or []) if str(w).strip()}
    try:
        import spacy  # type: ignore

        nlp = spacy.load(os.environ.get("SPACY_MODEL", "en_core_web_sm"))
        doc = nlp(text)
        for ent in doc.ents:
            for token in ent:
                protected.add(token.text.lower())
    except Exception:
        pass

    tokens = safe_word_tokenize(text)
    for word, tag in safe_pos_tag(tokens):
        if tag in {"NNP", "NNPS"}:
            protected.add(word.lower())
        elif word[:1].isupper() and tokens.index(word) != 0:
            protected.add(word.lower())
    return protected


def _merge_candidates(lemma: str, engine_candidates: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for cand in [*engine_candidates, *FALLBACK_SYNONYMS.get(lemma.lower(), [])]:
        c = re.sub(r"^[^A-Za-z]+|[^A-Za-z]+$", "", str(cand).lower())
        if not c or c == lemma.lower() or " " in c or c in seen:
            continue
        seen.add(c)
        merged.append(c)
    return merged


def gather_candidate_slots(
    text: str,
    top_k: int = 12,
    protected_words: Iterable[str] | None = None,
    engine: SynonymEngine | None = None,
) -> tuple[list[str], list[CandidateSlot]]:
    """Find content-word rewrite slots and gather synonym candidates."""

    tokens = safe_word_tokenize(text)
    tags = safe_pos_tag(tokens)
    protected = {str(w).lower() for w in (protected_words or [])}
    phrase_protected = semantic.protected_positions(tokens)
    engine = engine or SynonymEngine()

    slots: list[CandidateSlot] = []
    for i, (word, tag) in enumerate(tags):
        lower = word.lower()
        if not re.match(r"[a-z]", lower):
            continue
        if lower in protected or i in phrase_protected:
            continue
        if tag not in _SUBSTITUTABLE or lower in _STOP:
            continue
        lemma = lemmatize(word, tag)
        wn_pos = _wn_pos(tag)
        try:
            raw = engine.get_synonyms(lemma, top_k=top_k * 2, wn_pos=wn_pos).get(lemma, [])
        except Exception:
            raw = []
        candidates = _merge_candidates(lemma, raw)[:top_k]
        if candidates:
            slots.append(CandidateSlot(i, word, tag, lemma, candidates))
    return tokens, slots
