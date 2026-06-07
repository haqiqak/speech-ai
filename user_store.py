"""
user_store.py — file-based user storage for Speech AI.

Each user is stored as  users/<username>.json  with the structure:

{
  "username": "alice",
  "password_hash": "<bcrypt or sha256 hex>",
  "phoneme_profile": {
    "stutter_patterns": ["str", "pr"],
    "blocked_words":    ["particular"]
  },
  "custom_replacements": {},
  "preferences": {}
}

Public API
──────────
  list_users()                          -> list[str]
  user_exists(username)                 -> bool
  register_user(username, password)     -> (ok: bool, msg: str)
  verify_user(username, password)       -> (ok: bool, msg: str)
  load_profile(username)                -> dict   (phoneme_profile sub-dict)
  save_profile(username, patterns, blocked, custom_replacements, preferences)
  migrate_legacy_prefs(path)            -> None   (call once at startup)

The storage layer is intentionally kept behind this thin API so the
implementation can be swapped for SQLite/PostgreSQL with minimal changes.
"""

import hashlib
import json
import re
from pathlib import Path

_USERS_DIR = Path(__file__).resolve().parent / "users"
_USERS_DIR.mkdir(exist_ok=True)

# ── helpers ───────────────────────────────────────────────────────────────────

def _path(username: str) -> Path:
    safe = re.sub(r"[^a-z0-9_\-]", "", username.lower())
    return _USERS_DIR / f"{safe}.json"


def _hash_password(password: str) -> str:
    """SHA-256 hex digest.  Swap this line for bcrypt.hashpw() in production."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _check_password(password: str, stored_hash: str) -> bool:
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == stored_hash


def _default_record(username: str, password: str) -> dict:
    return {
        "username": username,
        "password_hash": _hash_password(password),
        "phoneme_profile": {
            "stutter_patterns": [],
            "blocked_words": [],
        },
        "custom_replacements": {},
        "preferences": {},
    }


def _read(username: str) -> dict | None:
    p = _path(username)
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write(record: dict) -> None:
    p = _path(record["username"])
    with open(p, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)


# ── public API ────────────────────────────────────────────────────────────────

def list_users() -> list[str]:
    """Return sorted list of registered usernames."""
    return sorted(
        p.stem for p in _USERS_DIR.glob("*.json")
        if p.is_file()
    )


def user_exists(username: str) -> bool:
    return _path(username).exists()


def register_user(username: str, password: str) -> tuple[bool, str]:
    """
    Create a new user file.  Returns (True, '') on success or
    (False, reason) on failure.
    """
    username = username.strip().lower()
    if not username:
        return False, "Username cannot be empty."
    if not re.match(r"^[a-z0-9_\-]{2,32}$", username):
        return False, "Username must be 2-32 characters: a-z, 0-9, _ or -."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."
    if user_exists(username):
        return False, f"Username '{username}' is already taken."
    _write(_default_record(username, password))
    return True, ""


def verify_user(username: str, password: str) -> tuple[bool, str]:
    """
    Verify credentials.  Returns (True, '') on success or (False, reason).
    """
    username = username.strip().lower()
    record = _read(username)
    if record is None:
        return False, "User not found."
    if not _check_password(password, record.get("password_hash", "")):
        return False, "Incorrect password."
    return True, ""


def load_profile(username: str) -> dict:
    """
    Return the phoneme_profile sub-dict for a user.
    Keys: stutter_patterns (list), blocked_words (list).
    Falls back to empty lists if the file is corrupt or missing.
    """
    record = _read(username) or {}
    pp = record.get("phoneme_profile", {})
    return {
        "stutter_patterns": list(pp.get("stutter_patterns", [])),
        "blocked_words":    list(pp.get("blocked_words", [])),
        "custom_replacements": dict(record.get("custom_replacements", {})),
        "preferences":         dict(record.get("preferences", {})),
    }


def save_profile(
    username: str,
    patterns: list[str],
    blocked: list[str],
    custom_replacements: dict | None = None,
    preferences: dict | None = None,
) -> None:
    """Persist the current phoneme profile (and optionally other prefs) for a user."""
    record = _read(username)
    if record is None:
        return
    record["phoneme_profile"] = {
        "stutter_patterns": patterns,
        "blocked_words":    blocked,
    }
    if custom_replacements is not None:
        record["custom_replacements"] = custom_replacements
    if preferences is not None:
        record["preferences"] = preferences
    _write(record)


def migrate_legacy_prefs(legacy_path: Path) -> None:
    """
    One-time migration: copy stutter_patterns / blocked_words from the old
    user_prefs.json into a users/default.json account (password "speech").
    Safe to call on every startup — no-op if migration already happened.
    """
    if not legacy_path.exists():
        return
    if user_exists("default"):
        return   # already migrated
    try:
        with open(legacy_path, "r", encoding="utf-8") as f:
            old = json.load(f)
        ok, _ = register_user("default", "speech")
        if ok:
            save_profile(
                "default",
                patterns=list(old.get("stutter_patterns", [])),
                blocked=list(old.get("blocked_words", [])),
            )
    except Exception:
        pass
