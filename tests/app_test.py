"""
tests/app_test.py — headless UI smoke via Streamlit's AppTest.

Runs app.py end-to-end in a test harness (no browser) and asserts real
behavior. Rewritten for the UI redesign around reformulate.py (2026-08-16):
the old dual-pipeline UI (word pickers, "Run speech profile" button,
profile-rewrite/rephrase cards, allowlist panel) is gone, replaced by a
single Reformulate button and a changes/skipped/verification review panel.
Each scenario that needs a specific starting profile writes it to the
real, snapshot-protected users/default.json via DifficultyProfile/
profile_store directly, then lets app.py's own startup code
(_difficulty_profile) load it exactly as a real user would.

    DISABLE_DATAMUSE=1 python tests/app_test.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest

import profile_store
from difficulty_profile import DifficultyProfile

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
ROOT = os.path.dirname(APP)
QUERY_LABEL = "Enter or paste text"
RUN_LABEL   = "Reformulate"
PROFILE = profile_store.DEFAULT_PROFILE


def _reset_default_profile(sounds=(), words=(), phrases=()):
    """Write a known, from-scratch profile to the real users/default.json
    before creating a fresh AppTest instance. run()'s wrapper snapshots/
    restores this file, so mutating it here is safe."""
    p = DifficultyProfile(PROFILE)
    for s in sounds:
        p.add_sound(s)
    for w in words:
        p.add_word(w)
    for ph in phrases:
        p.add_phrase(ph)
    p.save()


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
        # 1) App reaches the main UI directly, no login gate.
        _reset_default_profile()
        at = _fresh().run()
        ok &= _check(at, "default load, no login required")
        cond = "Your difficulty profile" in _md(at)
        print("     difficulty-profile step present:", cond); ok &= cond
        cond = "Login" not in _md(at) and "Register" not in _md(at)
        print("     no login/register UI present:", cond); ok &= cond

        # 2) No flagged content -> "no change needed" status, text untouched.
        _reset_default_profile()
        at = _fresh()
        at.run()
        ok &= _set_text(at, QUERY_LABEL, "The sky is blue today."); at.run()
        ok &= _click_run(at); at.run()
        ok &= _check(at, "no flagged content")
        md = _md(at)
        cond = "no changes needed" in md.lower()
        print("     'no change needed' status shown:", cond); ok &= cond

        # 3) Global sound flagged -> a substitution change + verification
        # metrics + output box containing the replacement, not the original.
        _reset_default_profile(sounds=["str"])
        at = _fresh()
        at.run()
        ok &= _set_text(
            at, QUERY_LABEL,
            "I need to review three reports before the strong deadline."
        ); at.run()
        ok &= _click_run(at); at.run()
        ok &= _check(at, "global sound flagged -> substitution")
        md = _md(at)
        cond = "Reformulated" in md or "reformulated" in md.lower()
        print("     'reformulated' status shown:", cond); ok &= cond
        import re as _re
        output_match = _re.search(r'class="output-box">(.*?)</div>', md)
        cond = output_match is not None
        print("     output box rendered:", cond); ok &= cond
        cond = bool(output_match) and "strong" not in output_match.group(1).lower()
        print("     'strong' no longer in the output text:", cond); ok &= cond
        cond = "Changes" in md
        print("     changes section rendered:", cond); ok &= cond
        cond = "Verification" in md
        print("     verification section rendered:", cond); ok &= cond

        # 4) Keep-toggle: unchecking a change's "Keep" box reverts that word
        # in the displayed output.
        keep_boxes = [cb for cb in at.checkbox if cb.key and cb.key.startswith("change_keep_")]
        cond = len(keep_boxes) >= 1
        print("     at least one change keep-toggle present:", cond); ok &= cond
        if keep_boxes:
            keep_boxes[0].set_value(False)
            at.run()
            ok &= _check(at, "revert a change via Keep toggle")
            md = _md(at)
            cond = 'class="output-box"' in md and "strong deadline" in md
            print("     reverted change restores original word in output:", cond); ok &= cond

        # 5) Speaker Difficulty Profile panel: add a word, a sound, a phrase;
        # verify each shows up; remove the word; verify it's gone.
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

        removed = _click(at, "dp_word_rm_particular")
        print("     remove button found and clicked:", removed); ok &= removed
        at.run()
        md = _md(at)
        cond = "particular" not in md.lower()
        print("     removed word no longer visible:", cond); ok &= cond

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
        _p = DifficultyProfile.load(PROFILE)
        cond = _p.sounds == []
        print("     NO global sound created from the word pattern:", cond); ok &= cond

        # 7) Audit-driven warnings: a heteronym word shows the "multiple
        # pronunciations" caveat; a promoted lossy-round-trip sound (ZH)
        # shows the "not fully enforced" one.
        _reset_default_profile()
        at = _fresh()
        at.run()
        ok &= _fill(at, "dp_word_add_input", "read"); at.run()
        ok &= _click(at, "dp_word_add_btn"); at.run()
        ok &= _check(at, "flag heteronym 'read'")
        md = _md(at)
        cond = "has multiple pronunciations" in md
        print("     heteronym warning shown:", cond); ok &= cond

        _reset_default_profile()
        at = _fresh()
        at.run()
        ok &= _fill(at, "dp_sound_add_input", "sh"); at.run()
        ok &= _click(at, "dp_sound_add_btn"); at.run()
        md = _md(at)
        cond = "not fully enforced yet" not in md
        print("     clean sound shows no false-positive warning:", cond); ok &= cond

        _reset_default_profile()
        at = _fresh()
        at.run()
        ok &= _fill(at, "dp_word_add_input", "measure"); at.run()
        ok &= _click(at, "dp_word_add_btn"); at.run()
        zh_found = False
        for cb in at.checkbox:
            if cb.key == "dp_pattern_phone_measure_2":  # M(0) EH(1) ZH(2) ER(3)
                cb.set_value(True)
                zh_found = True
        print("     ZH checkbox found on 'measure':", zh_found); ok &= zh_found
        at.run()
        for cb in at.checkbox:
            if cb.key == "dp_pattern_promote_measure":
                cb.set_value(True)
        at.run()
        ok &= _click(at, "dp_pattern_save_measure"); at.run()
        ok &= _check(at, "promote ZH to global sound")
        md = _md(at)
        cond = "not fully enforced yet" in md
        print("     lossy round-trip warning shown for promoted ZH:", cond); ok &= cond
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
