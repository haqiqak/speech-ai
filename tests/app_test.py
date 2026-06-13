"""
tests/app_test.py — headless UI smoke via Streamlit's AppTest.

Runs app.py end-to-end in a test harness (no browser) and asserts real behavior.
The app now requires login (auth.require_auth -> st.stop until authenticated), so
each scenario seeds an authenticated session before .run().  The query widget is
a text_area ("Your sentence or paragraph"); the run button is "Run speech profile".

    DISABLE_DATAMUSE=1 python tests/app_test.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest

try:
    from user_store import load_profile
except Exception:  # pragma: no cover
    load_profile = None

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
ROOT = os.path.dirname(APP)
QUERY_LABEL = "Your sentence or paragraph"
RUN_LABEL   = "Run speech profile"
REPHRASE_LABEL = "Fluency rephrase (beta)"


def _seed(at):
    """Bypass the login gate and load a sensible profile into session state."""
    at.session_state["authenticated"] = True
    at.session_state["current_user"]  = "default"
    patterns, blocked, allow, prefs, custom = [], [], [], {}, {}
    if load_profile is not None:
        try:
            prof = load_profile("default")
            patterns = list(prof.get("stutter_patterns", []))
            blocked  = list(prof.get("blocked_words", []))
            prefs    = dict(prof.get("preferences", {}))
            custom   = dict(prof.get("custom_replacements", {}))
            allow    = list(prefs.get("allowlist_words", []))
        except Exception:
            pass
    at.session_state["stutter_patterns"] = patterns
    at.session_state["blocked_words"]    = blocked
    at.session_state["allowlist_words"]  = allow
    at.session_state["preferences"]      = prefs
    at.session_state["custom_replacements"] = custom
    at.session_state["rephrase_enabled"] = bool(prefs.get("rephrase_enabled", False))
    at.session_state["profile_rewrite_enabled"] = bool(prefs.get("profile_rewrite_enabled", True))
    return at


def _fresh():
    at = AppTest.from_file(APP, default_timeout=300)
    _seed(at)
    return at


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


def _empty_profile(at):
    at.session_state["stutter_patterns"] = []
    at.session_state["blocked_words"] = []
    at.session_state["allowlist_words"] = []
    at.session_state["rephrase_enabled"] = False
    at.session_state["profile_rewrite_enabled"] = False
    try:
        prefs = dict(at.session_state["preferences"])
    except Exception:
        prefs = {}
    prefs["allowlist_words"] = []
    prefs["rephrase_enabled"] = False
    prefs["profile_rewrite_enabled"] = False
    at.session_state["preferences"] = prefs


def run():
    default_profile = os.path.join(ROOT, "users", "default.json")
    snapshot = None
    if os.path.exists(default_profile):
        with open(default_profile, "rb") as f:
            snapshot = f.read()
    ok = True
    try:

        # 1) Default load reaches the main UI (Phoneme Profile panel visible)
        at = _fresh().run()
        ok &= _check(at, "default load")
        cond = "Phoneme Profile" in _md(at)
        print("     Phoneme Profile panel present:", cond); ok &= cond
        button_labels = [b.label for b in at.button]
        uploader_labels = [getattr(u, "label", "") for u in at.file_uploader]
        cond = "Update profile from microphone" in button_labels
        print("     microphone profile update present:", cond); ok &= cond
        cond = "Upload voice or transcript sample" in uploader_labels
        print("     upload profile update present:", cond); ok &= cond

        # 2) Sentence mode, no patterns → final output contains the grammar fix 'running'
        at = _fresh()
        _empty_profile(at)
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

        # 3) Word mode 'present, happy' with pattern 'pr' → pills, NOT 'No synonyms found'
        at = _fresh()
        _empty_profile(at)
        at.session_state["stutter_patterns"] = ["pr"]
        at.run()
        ok &= _set_text(at, "Stutter sounds", "pr"); at.run()
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
        at = _fresh()
        _empty_profile(at)
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
    finally:
        if snapshot is not None:
            with open(default_profile, "wb") as f:
                f.write(snapshot)

    print("\nRESULT:", "ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
