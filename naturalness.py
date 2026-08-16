"""
naturalness.py — "naturalness of intervention" scoring (REFORMULATION_RESEARCH.md
§10/§28, ROADMAP.md R11).

Distinguishes "this edit was necessary" from "this edit was correct" — neither
SBERT similarity nor the phoneme veto measures whether a reformulation changed
more of the sentence than it needed to. This module answers only that
narrower question; it says nothing about whether the changes made were the
*right* ones (semantic.py/phonetic.py's gates own that).

Uses difflib.SequenceMatcher — the same edit-distance mechanism already used
elsewhere in this codebase (rephrase.py's `_score_candidate`) — rather than
adding a new dependency (e.g. python-Levenshtein) for what stdlib already
does adequately at this project's scale.
"""

from __future__ import annotations

import difflib
import re


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", (text or "").lower())


def edit_ratio(original: str, reformulated: str) -> float:
    """
    [0, 1] — 0.0 means identical (word-level), 1.0 means completely
    different. Word-level, not character-level: a single word swapped in an
    otherwise-unchanged sentence should score as "one small edit," not be
    penalized for the characters within that one word differing.
    """
    a = _word_tokens(original)
    b = _word_tokens(reformulated)
    if not a and not b:
        return 0.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return round(1.0 - ratio, 4)


def changed_word_count(original: str, reformulated: str) -> int:
    """Count of word positions that differ, via the same alignment
    difflib uses for edit_ratio (not a naive set-difference, which would
    miscount a word that just moved position as two changes)."""
    a = _word_tokens(original)
    b = _word_tokens(reformulated)
    matcher = difflib.SequenceMatcher(None, a, b)
    changed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            changed += max(i2 - i1, j2 - j1)
    return changed
