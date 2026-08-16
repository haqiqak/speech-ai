"""
difficulty_profile.py — the persistent, user-declared speaker difficulty
profile (Stage 4A foundation).

Design summary (full rationale in PROBLEM_FORMULATION.md)
───────────────────────────────────────────────────────────
Three explicitly separate categories — a word-specific difficulty is NOT
the same claim as a phoneme-level difficulty, and neither implies the other:

    sounds   — phoneme-level: "I have trouble with this starting sound."
    words    — lexical: "This specific word is difficult for me."
    phrases  — multi-word: "This specific phrase is difficult for me."

Every entry carries `source` (user_typed / user_selected_from_text /
system_observed — the last one reserved, unused, for a future Audio Module
per Stage 4A's requirement #17) and `added_at`, plus an empty, forward-
compatible `meta` dict so future fields (severity, confidence, context)
don't require a schema migration.

Word entries additionally carry a best-effort, CMU-dict-only `pronunciation`
(see `phonetic.full_pronunciation()`) — purely informational, shown to the
user so they can see WHY a word might be hard, never auto-promoted into a
`sounds` entry. Marking a word difficult never implies its phonemes are
individually difficult; that would conflate the two categories the whole
point of this module is to keep separate.

This module owns validation/normalization/dedup logic. `user_store.py` owns
file I/O and the legacy `phoneme_profile` mirror (kept in sync automatically
so the existing, UNCHANGED reformulation pipeline — grammar.py, rewrite/ —
keeps working without modification; see that module's docstring).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Iterable, Literal

import phonetic
import user_store

Category = Literal["sound", "word", "phrase"]
Source = Literal["user_typed", "user_selected_from_text", "system_observed"]

_VALID_SOURCES = {"user_typed", "user_selected_from_text", "system_observed"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_word(text: str) -> str:
    """Strip leading/trailing punctuation, collapse internal whitespace,
    lowercase. Keeps internal apostrophes/hyphens (contractions, compounds)."""
    t = re.sub(r"\s+", " ", (text or "").strip())
    t = re.sub(r"^[^\w']+|[^\w']+$", "", t)
    return t.lower()


def _clean_phrase(text: str) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    t = t.strip(".,!?;:\"'()[]")
    return t.lower()


def _sound_key(text: str) -> str:
    """Normalize a raw sound cue to its ARPAbet onset key, e.g. 'str' -> 'S T R'.

    Dedup and matching happen on this key, not on the raw spelling — 'c' and
    'k' both normalize to 'K', which is correct (CMU/ARPAbet reflects
    pronunciation, not spelling; see RESEARCH.md §2.F on why spelling isn't
    the right basis for this).
    """
    onset = phonetic.normalize_pattern((text or "").strip().lower())
    return " ".join(onset)


@dataclass
class DifficultyEntry:
    value: str                       # what the user typed/selected, as-is (case preserved for display)
    normalized: str                  # dedup/matching key: ARPAbet key for sounds, lowercased text for words/phrases
    category: Category
    source: Source = "user_typed"
    added_at: str = field(default_factory=_now)
    pronunciation: tuple[str, ...] | None = None   # words only; informational
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "normalized": self.normalized,
            "category": self.category,
            "source": self.source,
            "added_at": self.added_at,
            "pronunciation": list(self.pronunciation) if self.pronunciation else None,
            "meta": dict(self.meta),
        }

    @classmethod
    def from_dict(cls, category: Category, data: dict[str, Any]) -> "DifficultyEntry":
        pron = data.get("pronunciation")
        return cls(
            value=str(data.get("value", "")),
            normalized=str(data.get("normalized", "")),
            category=category,
            source=data.get("source") if data.get("source") in _VALID_SOURCES else "user_typed",
            added_at=str(data.get("added_at") or _now()),
            pronunciation=tuple(pron) if pron else None,
            meta=dict(data.get("meta") or {}),
        )


class DifficultyProfile:
    """The persistent, user-declared difficulty profile for one speaker.

    Loaded from (and always reflects) whatever the speaker already had —
    never starts "empty" for a returning user. New entries are additive;
    nothing here is reset by entering new text.
    """

    def __init__(self, username: str):
        self.username = username
        self.sounds: list[DifficultyEntry] = []
        self.words: list[DifficultyEntry] = []
        self.phrases: list[DifficultyEntry] = []

    # ── persistence ─────────────────────────────────────────────────────────
    @classmethod
    def load(cls, username: str) -> "DifficultyProfile":
        profile = cls(username)
        data = user_store.load_difficulty_profile(username)
        if not (data["sounds"] or data["words"] or data["phrases"]):
            # No difficulty_profile yet for this user — seed from whatever
            # legacy phoneme_profile already has, so a returning user's
            # existing data isn't lost or presented as empty. One-time,
            # transparent: the very next save() writes difficulty_profile,
            # after which this branch never fires again for this user.
            legacy = user_store.load_profile(username)
            for pattern in legacy.get("stutter_patterns", []):
                profile._add_raw("sound", pattern, source="user_typed", skip_dup=True)
            for word in legacy.get("blocked_words", []):
                profile._add_raw("word", word, source="user_typed", skip_dup=True)
        else:
            profile.sounds = [DifficultyEntry.from_dict("sound", d) for d in data["sounds"]]
            profile.words = [DifficultyEntry.from_dict("word", d) for d in data["words"]]
            profile.phrases = [DifficultyEntry.from_dict("phrase", d) for d in data["phrases"]]
        return profile

    def save(self) -> None:
        user_store.save_difficulty_profile(
            self.username,
            {
                "sounds": [e.to_dict() for e in self.sounds],
                "words": [e.to_dict() for e in self.words],
                "phrases": [e.to_dict() for e in self.phrases],
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sounds": [e.to_dict() for e in self.sounds],
            "words": [e.to_dict() for e in self.words],
            "phrases": [e.to_dict() for e in self.phrases],
        }

    # ── add ─────────────────────────────────────────────────────────────────
    def add_sound(self, raw_text: str, source: Source = "user_typed") -> tuple[DifficultyEntry | None, str]:
        """Returns (entry_or_None, status) where status is 'added' / 'duplicate' / 'empty'."""
        return self._add_raw("sound", raw_text, source=source)

    def add_word(self, raw_text: str, source: Source = "user_typed") -> tuple[DifficultyEntry | None, str]:
        return self._add_raw("word", raw_text, source=source)

    def add_phrase(self, raw_text: str, source: Source = "user_typed") -> tuple[DifficultyEntry | None, str]:
        return self._add_raw("phrase", raw_text, source=source)

    def _add_raw(
        self, category: Category, raw_text: str, source: Source, skip_dup: bool = False
    ) -> tuple[DifficultyEntry | None, str]:
        raw_text = (raw_text or "").strip()
        if not raw_text:
            return None, "empty"

        if category == "sound":
            normalized = _sound_key(raw_text)
            if not normalized:
                return None, "empty"
            bucket = self.sounds
            pronunciation = None
        elif category == "word":
            normalized = _clean_word(raw_text)
            if not normalized:
                return None, "empty"
            bucket = self.words
            pronunciation = phonetic.full_pronunciation(normalized)
        else:  # phrase
            normalized = _clean_phrase(raw_text)
            if not normalized:
                return None, "empty"
            bucket = self.phrases
            pronunciation = None

        if not skip_dup:
            for existing in bucket:
                if existing.normalized == normalized:
                    return existing, "duplicate"

        entry = DifficultyEntry(
            value=raw_text.strip(),
            normalized=normalized,
            category=category,
            source=source,
            pronunciation=pronunciation,
        )
        bucket.append(entry)
        return entry, "added"

    # ── remove ──────────────────────────────────────────────────────────────
    def remove(self, category: Category, normalized: str) -> bool:
        bucket = {"sound": self.sounds, "word": self.words, "phrase": self.phrases}[category]
        for i, entry in enumerate(bucket):
            if entry.normalized == normalized:
                del bucket[i]
                return True
        return False

    # ── convenience views for the current reformulation pipeline / UI ────────
    def sound_values(self) -> list[str]:
        return [e.value for e in self.sounds]

    def word_values(self) -> list[str]:
        return [e.value for e in self.words]

    def phrase_values(self) -> list[str]:
        return [e.value for e in self.phrases]

    def is_empty(self) -> bool:
        return not (self.sounds or self.words or self.phrases)


def extract_candidate_words(text: str) -> list[str]:
    """Unique, lowercased single-word tokens from *text*, for the UI's
    'pick a word from your current text' convenience control. Order
    preserves first appearance. Not a tokenizer used anywhere in scoring —
    display/UX helper only.
    """
    seen: set[str] = set()
    out: list[str] = []
    for match in re.finditer(r"[A-Za-z][A-Za-z'-]*", text or ""):
        w = match.group().lower().strip("-'")
        if w and w not in seen:
            seen.add(w)
            out.append(w)
    return out
