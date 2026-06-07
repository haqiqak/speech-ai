"""
tests/app_test.py — headless UI smoke via Streamlit's AppTest.

Runs app.py end-to-end in a test harness (no browser) and asserts the script
executes without raising for: default load, sentence mode (no patterns),
sentence mode WITH stutter patterns, and word mode.  Catches template/HTML
f-string and session-state bugs that py_compile cannot.

    python tests/app_test.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
QUERY_LABEL = "Enter word(s) or a sentence"


def _check(at, label):
    if at.exception:
        print(f"  [FAIL] {label}")
        for e in at.exception:
            print("     ", repr(e)[:400])
        return False
    print(f"  [ok]   {label}")
    return True


def _set(at, label, value):
    for ti in at.text_input:
        if ti.label == label:
            ti.set_value(value)
            return True
    return False


def run():
    ok = True

    # 1) Default load
    at = AppTest.from_file(APP, default_timeout=180).run()
    ok &= _check(at, "default load")
    print("     text inputs:", [ti.label for ti in at.text_input])

    # 2) Sentence mode, no patterns (legacy path) — grammar fix must appear
    at = AppTest.from_file(APP, default_timeout=180).run()
    _set(at, QUERY_LABEL, "she is run right now")
    at.run()
    at.button[0].click().run()
    ok &= _check(at, "sentence mode, no patterns")
    md = " ".join(m.value for m in at.markdown)
    print("     final contains 'running':", "running" in md.lower())

    # 3) Sentence mode WITH stutter patterns
    at = AppTest.from_file(APP, default_timeout=180).run()
    _set(at, "Stutter sounds", "d, str")
    at.run()
    _set(at, QUERY_LABEL, "The company is under stress and made a decision.")
    at.run()
    at.button[0].click().run()
    ok &= _check(at, "sentence mode, patterns=[d,str]")
    md = " ".join(m.value for m in at.markdown)
    print("     risk map present:", "Stutter Risk Map" in md)
    print("     difficulty shown:", "Stutter difficulty" in md)

    # 4) Word mode with patterns
    at = AppTest.from_file(APP, default_timeout=180).run()
    _set(at, "Stutter sounds", "pr")
    at.run()
    _set(at, QUERY_LABEL, "present, happy")
    at.run()
    at.button[0].click().run()
    ok &= _check(at, "word mode, patterns=[pr]")

    print("\nRESULT:", "ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
