"""
difficulty_profile.py — the persistent, user-declared speaker difficulty
profile (Stage 4A foundation; word-specific patterns + single-profile
storage added in the Stage 4A refinement, 2026-08-16).

Design summary (full rationale in PROBLEM_FORMULATION.md)
───────────────────────────────────────────────────────────
Four explicitly separate concepts — none of these implies any other:

    sounds          — GLOBAL phoneme-level: "I have trouble with this sound,
                       generally, wherever it occurs." Specifically an
                       ONSET pattern (word-initial phones only) — inherited
                       from phonetic.matches_any(), the only phoneme
                       matching the existing reformulation engine does.
                       Not a schema field because there is currently no
                       second value it could take; recorded here because
                       nothing else in the schema states it (audit,
                       PROBLEM_FORMULATION.md §11.1).
    words           — lexical: "This specific word is difficult for me,"
                       with no claim about *why*.
    phrases         — multi-word: "This specific phrase is difficult for me
                       as a sequence."
    word.problem_phones — WORD-SPECIFIC sound-level: "Within THIS word
                       specifically, these particular sounds are the
                       difficult part." Stored as an attribute of the word
                       entry it belongs to, not as its own top-level list —
                       it's meaningless without the word it's scoped to.
                       Identifies phone CLASSES within the word, not
                       specific occurrences — a word with a repeated phone
                       (e.g. "level" -> L EH V AH L) can't represent "only
                       the second L," by design (PROBLEM_FORMULATION.md
                       §11.1): the reformulation engine's use of this
                       (avoid the phone near this word) doesn't change
                       based on which occurrence was meant.

Flagging "three" as difficult NEVER creates a global "TH" or "R" sounds
entry by itself — that would silently convert "this one word is hard" into
"every word with this sound is hard," which is a different, much stronger
claim the user didn't make. A word's `problem_phones` (if the user chooses
to specify them) stays scoped to that word. Promoting a word-specific
pattern into a *global* sound difficulty is a separate, explicit action
(`add_sound_from_phones()`), never an automatic side effect of setting
`problem_phones`.

Every entry carries `source` (user_typed / user_selected_from_text /
system_observed — the last one reserved, unused, for a future Audio Module)
and `added_at`, plus an empty, forward-compatible `meta` dict.

Word entries additionally carry a best-effort, CMU-dict-only `pronunciation`
(see `phonetic.full_pronunciation()`) — informational, shown to the user so
they can see (and pick from) the word's actual sound sequence.
`problem_phones`, when set, is always a subset of `pronunciation` — it is
never fabricated for a word with no derivable pronunciation.

Storage: this module owns validation/normalization/dedup logic;
`profile_store.py` owns file I/O for a single default profile (see that
module for why the multi-account layer was removed and why `profile_name`
is nonetheless still a parameter, not hardcoded away).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Iterable, Literal

import phonetic
import profile_store

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


def _phones_key(phones: Iterable[str]) -> str:
    """Same key format as _sound_key(), built directly from ARPAbet phones
    rather than a grapheme guess — used when the phones are already known
    (selected from a word's real CMU pronunciation), so a sound added by
    typing 'thr' and one promoted from a word's TH+R selection dedup
    against each other correctly."""
    return " ".join(p.strip().upper() for p in phones if p and p.strip())


@dataclass
class DifficultyEntry:
    value: str                       # what the user typed/selected, as-is (case preserved for display)
    normalized: str                  # dedup/matching key: ARPAbet key for sounds, lowercased text for words/phrases
    category: Category
    source: Source = "user_typed"
    added_at: str = field(default_factory=_now)
    pronunciation: tuple[str, ...] | None = None     # words only; informational, full CMU phone sequence
    problem_phones: tuple[str, ...] | None = None    # words only; user-selected SUBSET of `pronunciation`
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "normalized": self.normalized,
            "category": self.category,
            "source": self.source,
            "added_at": self.added_at,
            "pronunciation": list(self.pronunciation) if self.pronunciation else None,
            "problem_phones": list(self.problem_phones) if self.problem_phones else None,
            "meta": dict(self.meta),
        }

    @classmethod
    def from_dict(cls, category: Category, data: dict[str, Any]) -> "DifficultyEntry":
        pron = data.get("pronunciation")
        pattern = data.get("problem_phones")
        return cls(
            value=str(data.get("value", "")),
            normalized=str(data.get("normalized", "")),
            category=category,
            source=data.get("source") if data.get("source") in _VALID_SOURCES else "user_typed",
            added_at=str(data.get("added_at") or _now()),
            pronunciation=tuple(pron) if pron else None,
            problem_phones=tuple(pattern) if pattern else None,
            meta=dict(data.get("meta") or {}),
        )


class DifficultyProfile:
    """The persistent, user-declared difficulty profile for one speaker.

    Loaded from (and always reflects) whatever the speaker already had —
    never starts "empty" for a returning user. New entries are additive;
    nothing here is reset by entering new text.
    """

    def __init__(self, profile_name: str = profile_store.DEFAULT_PROFILE):
        self.profile_name = profile_name
        self.sounds: list[DifficultyEntry] = []
        self.words: list[DifficultyEntry] = []
        self.phrases: list[DifficultyEntry] = []

    # ── persistence ─────────────────────────────────────────────────────────
    @classmethod
    def load(cls, profile_name: str = profile_store.DEFAULT_PROFILE) -> "DifficultyProfile":
        profile = cls(profile_name)
        data = profile_store.load_difficulty_profile(profile_name)
        if not (data["sounds"] or data["words"] or data["phrases"]):
            # No difficulty_profile yet for this profile — seed from whatever
            # a pre-existing account's legacy phoneme_profile already had, so
            # returning data isn't lost or presented as empty. One-time,
            # transparent: the very next save() writes difficulty_profile,
            # after which this branch never fires again for this profile.
            legacy = profile_store.load_legacy_phoneme_profile(profile_name)
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
        profile_store.save_difficulty_profile(self.profile_name, self.to_dict())

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

    def add_sound_from_phones(
        self, phones: Iterable[str], source: Source = "user_typed"
    ) -> tuple[DifficultyEntry | None, str]:
        """Add a GLOBAL sound difficulty built directly from known ARPAbet
        phones (e.g. a pattern promoted from a word's problem_phones),
        rather than from a typed grapheme cue. This is always an EXPLICIT
        call — nothing in this module calls it automatically when a word's
        problem_phones is set; see set_word_pattern()."""
        phones = list(phones or [])
        if not phones:
            return None, "empty"
        normalized = _phones_key(phones)
        if not normalized:
            return None, "empty"
        for existing in self.sounds:
            if existing.normalized == normalized:
                return existing, "duplicate"

        value = "-".join(p.strip().upper() for p in phones)
        meta: dict[str, Any] = {}
        # `sound_values()` -> `.value` is what actually reaches the existing
        # reformulation pipeline today (via the legacy stutter_patterns
        # mirror), which re-derives an ARPAbet key from `.value` by GUESSING
        # from spelling (phonetic.normalize_pattern), not by reading
        # `.normalized` directly — that's how it already worked for
        # user-typed cues like "str", and touching that contract is out of
        # scope here. For most promoted phone combos the guess round-trips
        # correctly (e.g. "TH-R" -> TH, R), but not all ARPAbet phones have
        # a spelling that decodes correctly (e.g. "ZH" decodes as Z + HH).
        # Detect that mismatch here so it's a recorded fact, not a silent
        # failure discovered later.
        if phonetic.normalize_pattern(value.lower()) != tuple(p.strip().upper() for p in phones):
            meta["legacy_bridge_unreliable"] = True

        entry = DifficultyEntry(
            value=value,
            normalized=normalized,
            category="sound",
            source=source,
            meta=meta,
        )
        self.sounds.append(entry)
        return entry, "added"

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

        meta: dict[str, Any] = {}
        if category == "word" and phonetic.pronunciation_variant_count(normalized) > 1:
            # A real, silent ambiguity otherwise: full_pronunciation() always
            # picks CMU's first-listed variant (e.g. "read" -> present tense),
            # which may not be the sense the user meant. We can't resolve
            # *which* variant without sentence context this module doesn't
            # have (see PROBLEM_FORMULATION.md's audit) — recording that the
            # ambiguity exists is the honest, minimal thing to do here.
            meta["has_alternate_pronunciations"] = True

        entry = DifficultyEntry(
            value=raw_text.strip(),
            normalized=normalized,
            category=category,
            source=source,
            pronunciation=pronunciation,
            meta=meta,
        )
        bucket.append(entry)
        return entry, "added"

    # ── word-specific problem pattern ──────────────────────────────────────
    def find_word(self, normalized_word: str) -> DifficultyEntry | None:
        for entry in self.words:
            if entry.normalized == normalized_word:
                return entry
        return None

    def set_word_pattern(self, normalized_word: str, phones: Iterable[str]) -> bool:
        """Mark specific sounds within an ALREADY-FLAGGED word as the
        particular problem — e.g. 'three' is difficult, and specifically
        the TH-R transition, not necessarily every sound in the word.

        `phones` must be a subset of the word's own derived pronunciation
        (validated here, not just trusted from the caller) — this method
        never invents a pronunciation, and it never touches `self.sounds`.
        Returns False (no-op) if the word isn't flagged yet, has no
        derivable pronunciation, or `phones` isn't actually a subset of it.
        """
        entry = self.find_word(normalized_word)
        if entry is None or not entry.pronunciation:
            return False
        phones = [p.strip().upper() for p in (phones or []) if p and p.strip()]
        if not phones or not set(phones).issubset(set(entry.pronunciation)):
            return False
        # de-dup while preserving selection order
        entry.problem_phones = tuple(dict.fromkeys(phones))
        return True

    def clear_word_pattern(self, normalized_word: str) -> bool:
        entry = self.find_word(normalized_word)
        if entry is None or entry.problem_phones is None:
            return False
        entry.problem_phones = None
        return True

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
