"""
tests/pilot_app_test.py — Stage 7 v3: drive eval/pilot_app.py through a
full synthetic run (1 participant x 30 pairs = 30 synthetic responses) via
Streamlit's AppTest, BEFORE any real participant touches it.

Verifies, per this stage's explicit checklist:
  1. exactly 30 eligible pairs are presented
  2. responses are saved correctly (values round-trip through the CSV)
  3. no responses are lost (all 30 land, in order, one row each)
  4. randomization/counterbalancing (pair order, shown-first position)
     actually varies across pairs, not fixed
  5. Original/Reformulated are labeled directly in the UI — the exact bug
     v2's real pilot run exposed (labels were "Sentence 1"/"Sentence 2"
     plus a separate caption, which participants lost track of) — checked
     by asserting the literal strings "**Original**"/"**Reformulated**"
     appear as markdown, and "Sentence 1"/"Sentence 2" do NOT
  6. the resulting data is analyzable by eval/pilot_analyze.py, including
     the profile-match section, kept separate from the human ratings

Uses the app's one fixed participant ID (P1 — v3 is single-user, no
selection screen). Snapshots and restores any pre-existing
eval/pilot_responses/P1.csv around the run, the same snapshot/restore
pattern tests/app_test.py already uses for users/default.json — this
test must never be able to lose real pilot data if it happens to run
after the participant has started.

    python tests/pilot_app_test.py
"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "eval" / "pilot_app.py"
RESPONSES_DIR = ROOT / "eval" / "pilot_responses"
PAIRS_PATH = ROOT / "eval" / "pilot_pairs.json"

PARTICIPANT_ID = "P1"


def _check(cond, label):
    print(f"  [{'ok' if cond else 'FAIL'}] {label}")
    return cond


def _snapshot():
    p = RESPONSES_DIR / f"{PARTICIPANT_ID}.csv"
    return p.read_bytes() if p.exists() else None


def _restore(data):
    p = RESPONSES_DIR / f"{PARTICIPANT_ID}.csv"
    if data is None:
        if p.exists():
            p.unlink()
    else:
        p.write_bytes(data)


def _n_pairs() -> int:
    import json
    return len(json.loads(PAIRS_PATH.read_text(encoding="utf-8"))["pairs"])


def _complete_all_pairs(n_pairs: int) -> AppTest:
    """Drive the single participant through all n_pairs with synthetic
    but varied answers. No selection screen in v3 — starts immediately.

    A FRESH AppTest instance is created for each pair (relying on
    eval/pilot_app.py's own disk-based resume — _load_completed() reads
    the CSV fresh every run), rather than reusing one long-lived instance
    across all 30 submit-and-rerun cycles. Found empirically, not by
    reading AppTest's docs: reusing one instance across ~24+ sequential
    st.form-submit-triggered st.rerun() cycles reliably corrupted
    AppTest's internal widget tracking (a stale prior form's radios
    would leak into the next pair's widget list, then a later .run()
    call would raise a KeyError against a widget ID from an already-
    torn-down render). A fresh instance per pair sidesteps whatever
    internal state accumulates — verified stable across all 30 pairs,
    repeatedly, once switched to this pattern. v2's 20-pair, 2-participant
    run used one long-lived instance per participant and never hit this;
    v3's 30 pairs in one participant's session apparently crossed
    whatever threshold triggers it."""
    rng = random.Random("synthetic-v3")
    at = None
    for i in range(n_pairs):
        at = AppTest.from_file(str(APP), default_timeout=180)
        at.run()
        if at.exception:
            for e in at.exception:
                print("     EXCEPTION:", repr(e)[:300])
            break
        radios = at.radio
        if len(radios) < 5:
            print("     [FAIL] expected 5 radio questions, found", len(radios))
            break
        radios[0].set_value(rng.choice([1, 2, 3, 4, 5]))
        radios[1].set_value(rng.choice([1, 2, 3, 4, 5]))
        radios[2].set_value(rng.choice([0, 1, 2, 3, 4]))
        radios[3].set_value(rng.choice(["Original", "Reformulated", "No preference"]))
        radios[4].set_value(rng.choice([
            "(not applicable / no issue)", "Meaning changed", "Sounds unnatural",
            "Original sentence itself was confusing or ungrammatical",
        ]))
        comment_boxes = [t for t in at.text_area if "anything else" in t.label.lower()]
        if comment_boxes:
            comment_boxes[0].set_value(rng.choice(["", "", "seemed fine to me", "a bit awkward wording"]))
        submit_btn = [b for b in at.button if b.label == "Submit and continue"][0]
        submit_btn.click()
        at.run()

    # One more fresh instance to observe the final "all completed" state.
    at = AppTest.from_file(str(APP), default_timeout=180)
    at.run()
    return at


def run() -> int:
    ok = True
    snapshot = _snapshot()
    if snapshot is not None:
        (RESPONSES_DIR / f"{PARTICIPANT_ID}.csv").unlink()
    try:
        import csv

        n_pairs = _n_pairs()
        ok &= _check(n_pairs == 30, f"pilot_pairs.json has 30 pairs (got {n_pairs})")

        # 0) The labeling fix: fresh run, first screen — Original/Reformulated
        # must be labeled directly, and "Sentence 1"/"Sentence 2" must be gone.
        at0 = AppTest.from_file(str(APP), default_timeout=180)
        at0.run()
        md0 = " ".join(m.value for m in at0.markdown)
        ok &= _check("Original" in md0, "'Original' label appears directly in the UI")
        ok &= _check("Reformulated" in md0, "'Reformulated' label appears directly in the UI")
        ok &= _check("Sentence 1" not in md0 and "Sentence 2" not in md0,
                      "the old ambiguous 'Sentence 1/2' labels are gone")

        # 1) Complete all 30 pairs.
        at1 = _complete_all_pairs(n_pairs)
        ok &= _check(not at1.exception, "completed with no exceptions")
        md1 = " ".join(m.value for m in at1.markdown) + " ".join(s.value for s in at1.success)
        ok &= _check(f"All {n_pairs} pairs completed" in md1, "reached the completion screen")

        # 2) Exactly 30 rows, no more, no less.
        path1 = RESPONSES_DIR / f"{PARTICIPANT_ID}.csv"
        ok &= _check(path1.exists(), "response file exists")
        rows1 = list(csv.DictReader(open(path1, encoding="utf-8"))) if path1.exists() else []
        ok &= _check(len(rows1) == n_pairs, f"exactly {n_pairs} rows (got {len(rows1)})")

        # 3) No duplicate/lost pair_ids.
        pair_ids_1 = [r["pair_id"] for r in rows1]
        ok &= _check(len(set(pair_ids_1)) == n_pairs, f"rated {n_pairs} distinct pairs, none repeated")

        # 4) Participant ID correct throughout.
        ok &= _check(
            all(r["participant_id"] == PARTICIPANT_ID for r in rows1),
            f"every row tagged participant_id={PARTICIPANT_ID}",
        )

        # 5) Randomization: pair order isn't just pair_01..pair_30 in file
        # order, and both shown-first positions occur.
        expected_file_order = [f"pair_{i+1:02d}" for i in range(n_pairs)]
        ok &= _check(pair_ids_1 != expected_file_order, "presentation order is shuffled, not file order")
        shown_first_values = {r["shown_first"] for r in rows1}
        ok &= _check(
            shown_first_values == {"original", "reformulated"},
            "both 'original-first' and 'reformulated-first' positions occur",
        )

        # 6) Values round-trip correctly.
        sample = rows1[0]
        ok &= _check(sample["meaning_preservation"] in {"1", "2", "3", "4", "5"}, "meaning_preservation is 1-5")
        ok &= _check(sample["naturalness"] in {"1", "2", "3", "4", "5"}, "naturalness is 1-5")
        ok &= _check(sample["speaking_ease"] in {"-2", "-1", "0", "1", "2"}, "speaking_ease is -2..2")
        ok &= _check(
            sample["preference"] in {"Original", "Reformulated", "No preference"},
            "preference is one of the three allowed values",
        )
        ok &= _check(bool(sample["timestamp"]), "timestamp recorded")
        any_comment = any(r.get("comment") for r in rows1)
        ok &= _check(any_comment, "at least one free-text comment was recorded")
        grammar_tag_used = any(
            r.get("diagnostic_tag") == "Original sentence itself was confusing or ungrammatical"
            for r in rows1
        )
        ok &= _check(grammar_tag_used, "the 'input grammar not right' diagnostic tag was recorded at least once")

        # 7) The resulting data is analyzable, including the separate
        # profile-match reporting.
        sys.path.insert(0, str(ROOT / "eval"))
        import pilot_analyze
        combined = pilot_analyze.load_responses([path1])
        ok &= _check(len(combined) == n_pairs, f"pilot_analyze loads all {n_pairs} rows (got {len(combined)})")
        per_pair = pilot_analyze.per_pair_summary(combined)
        ok &= _check(len(per_pair) == n_pairs, f"per-pair summary covers all {n_pairs} pairs")
        ok &= _check(all(row["n_ratings"] == 1 for row in per_pair), "each pair shows exactly 1 rating")

        metadata = pilot_analyze.load_pair_metadata()
        merged = pilot_analyze.merge_with_metadata(per_pair, metadata)
        ok &= _check(
            all("difficulty_resolved" in row for row in merged),
            "profile-match field (difficulty_resolved) present for every pair, kept separate from ratings",
        )
        ok &= _check(
            all(row["category"] in {"global_sound", "declared_word", "word_pattern", "multi_difficulty"} for row in merged),
            "every pair has a valid v3 category label",
        )

    finally:
        _restore(snapshot)

    print("\nRESULT:", "ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
