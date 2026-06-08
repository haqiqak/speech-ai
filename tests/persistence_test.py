"""
tests/persistence_test.py - preference round-trip smoke for Task I.

    python tests/persistence_test.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from auth import _load_user_into_session
from user_store import load_profile, register_user, save_profile

ROOT = Path(__file__).resolve().parent.parent
TEMP_USER = "codex_persist_tmp"
TEMP_PATH = ROOT / "users" / f"{TEMP_USER}.json"


def _delete_temp():
    if TEMP_PATH.exists():
        TEMP_PATH.unlink()


def main() -> int:
    _delete_temp()
    try:
        ok, msg = register_user(TEMP_USER, "speech")
        assert ok, msg
        prefs = {
            "allowlist_words": ["conference"],
            "rephrase_enabled": True,
        }
        save_profile(
            TEMP_USER,
            patterns=["pr"],
            blocked=["present"],
            custom_replacements={},
            preferences=prefs,
        )

        prof = load_profile(TEMP_USER)
        assert prof["preferences"]["allowlist_words"] == ["conference"]
        assert prof["preferences"]["rephrase_enabled"] is True

        try:
            st.session_state.clear()
        except Exception:
            pass
        _load_user_into_session(TEMP_USER)
        assert st.session_state.allowlist_words == ["conference"]
        assert st.session_state.rephrase_enabled is True

        for username in ("default", "bobcat"):
            loaded = load_profile(username)
            assert "allowlist_words" in loaded["preferences"]
            assert "rephrase_enabled" in loaded["preferences"]

        print("persistence: ok")
        return 0
    finally:
        _delete_temp()


if __name__ == "__main__":
    raise SystemExit(main())
