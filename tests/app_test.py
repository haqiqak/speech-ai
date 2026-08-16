"""
tests/app_test.py — headless UI smoke via Streamlit's AppTest.

Runs app.py end-to-end in a test harness (no browser) and asserts real
behavior. Rewritten for the Stage 4A refinement (2026-08-16): the app no
longer has a login gate (auth.py/user_store.py were removed — see
DECISION_LOG.md 2026-08-16), so there's nothing to bypass anymore. Each
scenario that needs a specific starting profile now writes it to the real,
snapshot-protected users/default.json via DifficultyProfile/profile_store
directly, then lets app.py's own startup code
(_load_default_profile_into_session / _difficulty_profile) load it exactly
as it would for a real user — this is more faithful than pre-poking
session_state, and it exercises the actual load path.

    DISABLE_DATAMUSE=1 python tests/app_test.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest

import profile_store
from difficulty_profile import DifficultyProfile

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
ROOT = os.path.dirname(APP)
QUERY_LABEL = "Your sentence or paragraph"
RUN_LABEL   = "Run speech profile"
REPHRASE_LABEL = "Fluency rephrase (beta)"
PROFILE = profile_store.DEFAULT_PROFILE


def _reset_default_profile(sounds=(), words=(), phrases=(), rephrase_enabled=False,
                            profile_rewrite_enabled=True, allowlist_words=()):
    """Write a known, from-scratch profile + preferences state to the real
    users/default.json before creating a fresh AppTest instance. The
    caller's run() wrapper snapshots/restores this file, so mutating it
    here is safe."""
    p = DifficultyProfile(PROFILE)
    for s in sounds:
        p.add_sound(s)
    for w in words:
        p.add_word(w)
    for ph in phrases:
        p.add_phrase(ph)
    p.save()
    profile_store.save_preferences(
        PROFILE,
        {
            "allowlist_words": list(allowlist_words),
            "rephrase_enabled": rephrase_enabled,
            "profile_rewrite_enabled": profile_rewrite_enabled,
        },
        custom_replacements={},
    )


def _fresh():
    return AppTest.from_file(APP, default_timeout=300)


def _check(at, label):
    if at.exception:
        print(f"  [FAIL] {label}")
        for e in at.exception:
            print("     ", repr(e)[:400])
        return False
    print(f"  [ok]   {label}")
    return True


def _set_text(at, label, value):
    for ta in at.text_area:
        if ta.label == label:
            ta.set_value(value)
            return True
    for ti in at.text_input:
        if ti.label == label:
            ti.set_value(value)
            return True
    print(f"     [warn] widget not found: {label!r}")
    return False


def _click_run(at):
    for b in at.button:
        if b.label == RUN_LABEL:
            b.click()
            return True
    print(f"     [warn] button not found: {RUN_LABEL!r}")
    return False


def _set_toggle(at, label, value):
    for tg in at.toggle:
        if tg.label == label:
            tg.set_value(value)
            return True
    print(f"     [warn] toggle not found: {label!r}")
    return False


def _md(at):
    return " ".join(m.value for m in at.markdown)


def _fill(at, widget_key, value):
    for ti in at.text_input:
        if ti.key == widget_key:
            ti.set_value(value)
            return True
    return False


def _click(at, widget_key):
    for b in at.button:
        if b.key == widget_key:
            b.click()
            return True
    return False


def run():
    default_profile = os.path.join(ROOT, "users", "default.json")
    snapshot = None
    if os.path.exists(default_profile):
        with open(default_profile, "rb") as f:
            snapshot = f.read()
    ok = True
    try:
        # 1) No login gate: app reaches the main UI directly.
        _reset_default_profile()
        at = _fresh().run()
        ok &= _check(at, "default load, no login required")
        cond = "Speaker Difficulty Profile" in _md(at)
        print("     Speaker Difficulty Profile panel present:", cond); ok &= cond
        cond = "Login" not in _md(at) and "Register" not in _md(at)
        print("     no login/register UI present:", cond); ok &= cond

        # 2) Sentence mode, no patterns → final output contains the grammar fix 'running'
        _reset_default_profile()
        at = _fresh()
        at.run()
        ok &= _set_text(at, QUERY_LABEL, "she is run right now"); at.run()
        ok &= _click_run(at); at.run()
        ok &= _check(at, "sentence mode, no patterns")
        md = _md(at)
        cond = "running" in md.lower()
        print("     final contains 'running':", cond); ok &= cond
        cond = "Word Risk Analysis" in md
        print("     Word Risk Analysis panel present:", cond); ok &= cond
        cond = "Fluency Rephrase" not in md
        print("     rephrase card absent when toggle off:", cond); ok &= cond

        # 3) Word mode 'present, happy' with sound 'pr' already in the profile
        # (written to disk, then loaded through the real startup path) → pills,
        # NOT 'No synonyms found'.
        _reset_default_profile(sounds=["pr"])
        at = _fresh()
        at.run()
        cond = at.session_state["stutter_patterns"] == ["pr"]
        print("     pre-existing profile loaded on startup:", cond); ok &= cond
        ok &= _set_text(at, QUERY_LABEL, "present, happy"); at.run()
        ok &= _click_run(at); at.run()
        ok &= _check(at, "word mode, pattern pr")
        md = _md(at)
        pill_count = md.count('class="pill ')
        cond = pill_count >= 2
        print("     synonym pills rendered:", pill_count); ok &= cond
        cond = "No synonyms found" not in md
        print("     no 'No synonyms found' for present/happy:", cond); ok &= cond

        # 4) Toggle-on rephrase path renders the optional card or graceful no-op
        _reset_default_profile()
        at = _fresh()
        at.run()
        ok &= _set_toggle(at, REPHRASE_LABEL, True); at.run()
        ok &= _set_text(at, QUERY_LABEL, "she is run right now"); at.run()
        ok &= _click_run(at); at.run()
        ok &= _check(at, "rephrase toggle on")
        md = _md(at)
        cond = "Fluency Rephrase" in md
        print("     rephrase card present:", cond); ok &= cond
        cond = ("No rephrase applied" in md) or ("Similarity:" in md)
        print("     rephrase status rendered:", cond); ok &= cond

        # 5) Speaker Difficulty Profile panel: add a word, a sound, a phrase;
        # verify each shows up; remove the word; verify it's gone. Exercises
        # the actual Streamlit widgets (by key, since "Add" is ambiguous by
        # label across the three add buttons), not just the profile module
        # directly (that's covered in tests/difficulty_profile_test.py).
        _reset_default_profile()
        at = _fresh()
        at.run()

        ok &= _fill(at, "dp_word_add_input", "particular"); at.run()
        ok &= _click(at, "dp_word_add_btn"); at.run()
        ok &= _check(at, "difficulty profile: add word")
        md = _md(at)
        cond = "particular" in md.lower()
        print("     added word visible:", cond); ok &= cond
        cond = "dp_pattern_target" in at.session_state and at.session_state["dp_pattern_target"] == "particular"
        print("     pattern editor auto-opens after adding a word:", cond); ok &= cond

        ok &= _fill(at, "dp_sound_add_input", "str"); at.run()
        ok &= _click(at, "dp_sound_add_btn"); at.run()
        md = _md(at)
        cond = "str" in md.lower()
        print("     added sound visible:", cond); ok &= cond

        ok &= _fill(at, "dp_phrase_add_input", "through the research"); at.run()
        ok &= _click(at, "dp_phrase_add_btn"); at.run()
        md = _md(at)
        cond = "through the research" in md.lower()
        print("     added phrase visible:", cond); ok &= cond

        cond = at.session_state["blocked_words"] == ["particular"]
        print("     legacy blocked_words mirror updated:", cond); ok &= cond
        cond = at.session_state["stutter_patterns"] == ["str"]
        print("     legacy stutter_patterns mirror updated:", cond); ok &= cond

        removed = _click(at, "dp_word_rm_particular")
        print("     remove button found and clicked:", removed); ok &= removed
        at.run()
        md = _md(at)
        cond = "particular" not in md.lower()
        print("     removed word no longer visible:", cond); ok &= cond
        cond = at.session_state["blocked_words"] == []
        print("     legacy mirror updated after removal:", cond); ok &= cond

        # 6) Word-specific sound pattern: flag 'three', open the pattern
        # editor, select TH + R, save WITHOUT promoting to global — 'three'
        # shows the specific pattern, but no global sound entry is created.
        _reset_default_profile()
        at = _fresh()
        at.run()
        ok &= _fill(at, "dp_word_add_input", "three"); at.run()
        ok &= _click(at, "dp_word_add_btn"); at.run()
        ok &= _check(at, "flag 'three' and open pattern editor")
        md = _md(at)
        cond = 'What\'s difficult about "three"?' in md
        print("     pattern editor visible after flagging 'three':", cond); ok &= cond

        # Checkboxes are keyed dp_pattern_phone_three_<index>; 'three' -> TH R IY.
        found_th = found_r = False
        for cb in at.checkbox:
            if cb.key == "dp_pattern_phone_three_0":
                cb.set_value(True)  # TH
                found_th = True
            elif cb.key == "dp_pattern_phone_three_1":
                cb.set_value(True)  # R
                found_r = True
        print("     TH/R checkboxes found:", found_th and found_r); ok &= (found_th and found_r)
        at.run()

        ok &= _click(at, "dp_pattern_save_three"); at.run()
        ok &= _check(at, "save word-specific pattern without promoting")
        md = _md(at)
        cond = "specifically:" in md and "TH" in md and "R" in md
        print("     word-specific pattern shown on the word entry:", cond); ok &= cond
        cond = at.session_state["stutter_patterns"] == []
        print("     NO global sound created from the word pattern:", cond); ok &= cond
    finally:
        if snapshot is not None:
            with open(default_profile, "wb") as f:
                f.write(snapshot)
        elif os.path.exists(default_profile):
            os.remove(default_profile)

    print("\nRESULT:", "ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
