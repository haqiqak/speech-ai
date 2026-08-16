"""
tests/persistence_test.py - preference round-trip smoke test.

Rewritten for the Stage 4A refinement (2026-08-16): the original version
tested this via auth.py's login flow (register_user/verify_user/
_load_user_into_session). Both auth.py and user_store.py were removed along
with the multi-user system — see DECISION_LOG.md 2026-08-16 and
PROBLEM_FORMULATION.md. This now tests profile_store.py directly, which is
a more focused test of the same guarantee: preferences saved for a profile
are exactly what's read back.

    python tests/persistence_test.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import profile_store

ROOT = Path(__file__).resolve().parent.parent
TEMP_PROFILE = "codex_persist_tmp"
TEMP_PATH = ROOT / "users" / f"{TEMP_PROFILE}.json"


def _delete_temp():
    if TEMP_PATH.exists():
        TEMP_PATH.unlink()


def main() -> int:
    _delete_temp()
    try:
        prefs = {
            "allowlist_words": ["conference"],
            "rephrase_enabled": True,
            "profile_rewrite_enabled": True,
        }
        profile_store.save_preferences(TEMP_PROFILE, prefs, custom_replacements={})

        loaded = profile_store.load_preferences(TEMP_PROFILE)
        assert loaded["preferences"]["allowlist_words"] == ["conference"]
        assert loaded["preferences"]["rephrase_enabled"] is True

        # A profile with no file yet (never saved) still returns a complete,
        # well-formed preferences dict — the app must never crash on a
        # brand-new default profile.
        never_saved = profile_store.load_preferences("codex_never_saved_profile")
        assert never_saved["preferences"]["allowlist_words"] == []
        assert never_saved["preferences"]["rephrase_enabled"] is False
        assert never_saved["preferences"]["profile_rewrite_enabled"] is True

        # The actual default profile used by the running app must already
        # have a well-formed preferences dict (created across Stage 4A/4A
        # refinement sessions) — this is the one profile.json this test
        # does NOT create/delete itself.
        default_prefs = profile_store.load_preferences(profile_store.DEFAULT_PROFILE)
        assert "allowlist_words" in default_prefs["preferences"]
        assert "rephrase_enabled" in default_prefs["preferences"]

        print("persistence: ok")
        return 0
    finally:
        _delete_temp()


if __name__ == "__main__":
    raise SystemExit(main())
