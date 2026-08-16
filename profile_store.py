"""
profile_store.py — single-default-profile storage for Speech AI.

Stage 4A refinement (2026-08-16): replaces user_store.py's account/auth
layer. No login, no passwords, no registration — the app operates as one
default speaker profile, loaded automatically on startup. See
DECISION_LOG.md 2026-08-16 for why the multi-user system was removed and
PROBLEM_FORMULATION.md for the full reasoning.

The `profile_name` parameter is kept everywhere (never hardcoded away),
defaulting to DEFAULT_PROFILE = "default", specifically so a later stage
could reintroduce multiple named profiles without a storage-layer change —
"single user today" and "extensible data model" are not in tension here.

Storage location: users/<profile_name>.json — the directory is still
called `users/`, not renamed to `profiles/`, because profiling/profile.py
(unmodified, out of scope this stage) hardcodes `users/` for its own
per-speaker EWMA `*.fluency_profile.json` files; renaming it would mean
touching that file, which this stage does not do.

Current on-disk schema (no password_hash, no phoneme_profile — both
obsolete now that there's no auth layer and the legacy mirror is computed
in-memory by app.py instead of persisted):

{
  "profile_name": "default",
  "difficulty_profile": {"sounds": [...], "words": [...], "phrases": [...]},
  "custom_replacements": {},
  "preferences": {"allowlist_words": [...], "rephrase_enabled": bool, "profile_rewrite_enabled": bool}
}

A profile file written by the PREVIOUS stage (Stage 4A, before this
refinement) may still have `password_hash`/`phoneme_profile`/`username`
fields. Those are read once for their still-useful parts (see
load_legacy_phoneme_profile below, consumed by difficulty_profile.py's
one-time migration) and dropped on the next save — no code here writes
them back.

Public API
──────────
  load_difficulty_profile(profile_name)          -> dict
  save_difficulty_profile(profile_name, data)    -> None
  load_legacy_phoneme_profile(profile_name)      -> dict (one-time migration read only)
  load_preferences(profile_name)                 -> dict
  save_preferences(profile_name, preferences, custom_replacements=None) -> None
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEFAULT_PROFILE = "default"

_PROFILES_DIR = Path(__file__).resolve().parent / "users"
_PROFILES_DIR.mkdir(exist_ok=True)


def _safe_name(profile_name: str) -> str:
    safe = re.sub(r"[^a-z0-9_\-]", "", (profile_name or DEFAULT_PROFILE).strip().lower())
    return safe or DEFAULT_PROFILE


def _path(profile_name: str) -> Path:
    return _PROFILES_DIR / f"{_safe_name(profile_name)}.json"


def _read_raw(profile_name: str) -> dict[str, Any]:
    p = _path(profile_name)
    if not p.exists():
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _write_raw(profile_name: str, record: dict[str, Any]) -> None:
    with open(_path(profile_name), "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)


def profile_exists(profile_name: str = DEFAULT_PROFILE) -> bool:
    return _path(profile_name).exists()


def load_difficulty_profile(profile_name: str = DEFAULT_PROFILE) -> dict[str, list]:
    """Return {"sounds": [...], "words": [...], "phrases": [...]} exactly as
    stored — no legacy fallback here (see load_legacy_phoneme_profile for
    that; it's kept as a separate, explicit function so this one stays a
    pure, predictable read)."""
    raw = _read_raw(profile_name)
    dp = raw.get("difficulty_profile") or {}
    return {
        "sounds": list(dp.get("sounds", [])),
        "words": list(dp.get("words", [])),
        "phrases": list(dp.get("phrases", [])),
    }


def save_difficulty_profile(profile_name: str, data: dict[str, list]) -> None:
    """Persist the structured difficulty profile. Rewrites the whole record
    from only the fields this module currently knows about — a Stage-4A-era
    record's now-obsolete password_hash/phoneme_profile/username fields are
    silently dropped on this write, not carried forward."""
    prefs = load_preferences(profile_name)
    record = {
        "profile_name": _safe_name(profile_name),
        "difficulty_profile": {
            "sounds": list(data.get("sounds", [])),
            "words": list(data.get("words", [])),
            "phrases": list(data.get("phrases", [])),
        },
        "custom_replacements": prefs["custom_replacements"],
        "preferences": prefs["preferences"],
    }
    _write_raw(profile_name, record)


def load_legacy_phoneme_profile(profile_name: str = DEFAULT_PROFILE) -> dict[str, list]:
    """Read the OLD phoneme_profile.stutter_patterns/.blocked_words fields,
    if present, for one-time migration only. Used exclusively by
    difficulty_profile.py's DifficultyProfile.load() when the new
    difficulty_profile is empty, so a pre-existing account's data isn't
    lost. Returns empty lists if there's nothing to migrate — this is not
    an error case, most profiles won't have this."""
    raw = _read_raw(profile_name)
    pp = raw.get("phoneme_profile") or {}
    return {
        "stutter_patterns": list(pp.get("stutter_patterns", [])),
        "blocked_words": list(pp.get("blocked_words", [])),
    }


def load_preferences(profile_name: str = DEFAULT_PROFILE) -> dict[str, Any]:
    raw = _read_raw(profile_name)
    prefs = dict(raw.get("preferences", {}))
    prefs.setdefault("allowlist_words", [])
    prefs.setdefault("rephrase_enabled", False)
    prefs.setdefault("profile_rewrite_enabled", True)
    return {
        "preferences": prefs,
        "custom_replacements": dict(raw.get("custom_replacements", {})),
    }


def save_preferences(
    profile_name: str,
    preferences: dict[str, Any],
    custom_replacements: dict[str, Any] | None = None,
) -> None:
    raw = _read_raw(profile_name)
    dp = raw.get("difficulty_profile") or {"sounds": [], "words": [], "phrases": []}
    record = {
        "profile_name": _safe_name(profile_name),
        "difficulty_profile": dp,
        "custom_replacements": (
            dict(custom_replacements) if custom_replacements is not None
            else dict(raw.get("custom_replacements", {}))
        ),
        "preferences": dict(preferences),
    }
    _write_raw(profile_name, record)
