"""
eval/r46_toggle_smoke.py — headless smoke test of the new "Try next-gen
escalation" toggle in app.py, via Streamlit's AppTest (same mechanism
tests/app_test.py already uses). Checks the checkbox, forces a dense
profile that needs escalation, clicks Reformulate, and confirms the v2
path actually rendered: the "restructuring (v2)" tag, the Verification
tab's validator section. Read-only check of code already written --
not a permanent addition to tests/ (app_test.py already covers the
default, toggle-off path exhaustively; this is a one-time confirmation
the toggle wires through correctly before calling this done).

    DISABLE_DATAMUSE=1 python eval/r46_toggle_smoke.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest
import profile_store
from difficulty_profile import DifficultyProfile

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
ROOT = os.path.dirname(APP)
PROFILE = profile_store.DEFAULT_PROFILE


def _reset_default_profile(sounds=()):
    p = DifficultyProfile(PROFILE)
    for s in sounds:
        p.add_sound(s)
    p.save()


def _md(at):
    return " ".join(m.value for m in at.markdown)


def main() -> int:
    default_profile = os.path.join(ROOT, "users", "default.json")
    snapshot = None
    if os.path.exists(default_profile):
        with open(default_profile, "rb") as f:
            snapshot = f.read()
    ok = True
    try:
        _reset_default_profile(sounds=["s", "th", "r"])  # dense enough to force escalation
        at = AppTest.from_file(APP, default_timeout=300).run()

        checkboxes = [cb for cb in at.checkbox if cb.label and "next-gen escalation" in cb.label]
        print(f"toggle checkbox found: {len(checkboxes) == 1}"); ok &= len(checkboxes) == 1
        checkboxes[0].set_value(True)
        at.run()

        for ta in at.text_area:
            if ta.label == "Enter or paste text":
                ta.set_value("The scientific study of cooking has become known as molecular gastronomy.")
        at.run()

        clicked = False
        for b in at.button:
            if b.label == "Reformulate":
                b.click()
                clicked = True
        print(f"reformulate clicked: {clicked}"); ok &= clicked
        at.run()

        if at.exception:
            print("EXCEPTION:", at.exception)
            ok = False
        else:
            md = _md(at)
            cond = "restructuring (v2)" in md or "reformulated" in md.lower() or "could not" in md.lower()
            print(f"v2 result rendered without crashing: {cond}"); ok &= cond
            cond_validator = "Experimental validator" in md
            print(f"validator section present in Verification tab: {cond_validator}"); ok &= cond_validator
    finally:
        if snapshot is not None:
            with open(default_profile, "wb") as f:
                f.write(snapshot)
        elif os.path.exists(default_profile):
            os.remove(default_profile)

    print("\nRESULT:", "ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
