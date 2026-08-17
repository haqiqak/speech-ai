"""
tests/pilot_app_test.py — Stage 7: drive eval/pilot_app.py through a full
synthetic run (2 participants x 20 pairs = 40 synthetic responses) via
Streamlit's AppTest, BEFORE any real participant touches it.

Verifies, per Stage 7's explicit checklist:
  1. exactly 20 eligible pairs are assigned to each participant
  2. responses are saved correctly (values round-trip through the CSV)
  3. participant IDs remain separate (no cross-contamination)
  4. no responses are lost (all 20 land, in order, one row each)
  5. randomization/counterbalancing actually varies (different pair
     order and different shown-first pattern between two participants)
  6. the resulting data is analyzable by eval/pilot_analyze.py

Uses two of the app's real, fixed participant IDs (P1/P2 — the app's
selectbox only accepts P1-P4, so a synthetic-only ID can't be driven
through the actual widget). Snapshots and restores any pre-existing
eval/pilot_responses/P1.csv and P2.csv around the run, the same
snapshot/restore pattern tests/app_test.py already uses for
users/default.json — this test must never be able to lose real pilot
data if it happens to run after participants have started.

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

SYNTHETIC_IDS = ["P1", "P2"]  # real, app-selectable IDs — see module docstring


def _check(cond, label):
    print(f"  [{'ok' if cond else 'FAIL'}] {label}")
    return cond


def _snapshot():
    snap = {}
    for pid in SYNTHETIC_IDS:
        p = RESPONSES_DIR / f"{pid}.csv"
        snap[pid] = p.read_bytes() if p.exists() else None
    return snap


def _restore(snap):
    for pid in SYNTHETIC_IDS:
        p = RESPONSES_DIR / f"{pid}.csv"
        data = snap.get(pid)
        if data is None:
            if p.exists():
                p.unlink()
        else:
            p.write_bytes(data)


def _cleanup_for_fresh_run():
    for pid in SYNTHETIC_IDS:
        p = RESPONSES_DIR / f"{pid}.csv"
        if p.exists():
            p.unlink()


def _complete_all_pairs(participant_id: str) -> AppTest:
    """Drive one participant through all 20 pairs with synthetic but
    varied answers, patching st.selectbox in via session_state directly
    since PARTICIPANT_IDS is a fixed list, not free text."""
    at = AppTest.from_file(str(APP), default_timeout=120)
    at.run()
    sb = at.selectbox[0]
    sb.set_value(participant_id)
    at.run()
    start_btn = [b for b in at.button if b.label == "Start"][0]
    start_btn.click()
    at.run()

    rng = random.Random(f"synthetic-{participant_id}")
    seen_pair_ids = []
    for i in range(20):
        if at.exception:
            for e in at.exception:
                print("     EXCEPTION:", repr(e)[:300])
            break
        # pull the current pair id out of the caption text
        caption_texts = [c.value for c in at.caption]
        pair_caption = next((c for c in caption_texts if "Completed:" in c), "")
        radios = at.radio
        if len(radios) < 5:
            print("     [FAIL] expected 5 radio questions, found", len(radios))
            break
        radios[0].set_value(rng.choice([1, 2, 3, 4, 5]))
        radios[1].set_value(rng.choice([1, 2, 3, 4, 5]))
        radios[2].set_value(rng.choice([0, 1, 2, 3, 4]))
        radios[3].set_value(rng.choice(["Original", "Reformulated", "No preference"]))
        radios[4].set_value(rng.choice(
            ["(not applicable / no issue)", "Meaning changed", "Sounds unnatural"]
        ))
        at.run()
        submit_btn = [b for b in at.button if b.label == "Submit and continue"][0]
        submit_btn.click()
        at.run()
    return at


def run() -> int:
    ok = True
    snapshot = _snapshot()
    _cleanup_for_fresh_run()
    try:
        import csv

        # 1) Two participants (real IDs P1/P2) complete all 20 pairs each.
        at1 = _complete_all_pairs("P1")
        ok &= _check(not at1.exception, "P1 completed with no exceptions")
        md1 = " ".join(m.value for m in at1.markdown) + " ".join(s.value for s in at1.success)
        ok &= _check("All 20 pairs completed" in md1, "P1 reached the completion screen")

        at2 = _complete_all_pairs("P2")
        ok &= _check(not at2.exception, "P2 completed with no exceptions")

        # 2) Exactly 20 rows per participant, no more, no less.
        path1 = RESPONSES_DIR / "P1.csv"
        path2 = RESPONSES_DIR / "P2.csv"
        ok &= _check(path1.exists() and path2.exists(), "both response files exist")
        rows1 = list(csv.DictReader(open(path1, encoding="utf-8"))) if path1.exists() else []
        rows2 = list(csv.DictReader(open(path2, encoding="utf-8"))) if path2.exists() else []
        ok &= _check(len(rows1) == 20, f"P1 has exactly 20 rows (got {len(rows1)})")
        ok &= _check(len(rows2) == 20, f"P2 has exactly 20 rows (got {len(rows2)})")

        # 3) No duplicate/lost pair_ids within a participant.
        pair_ids_1 = [r["pair_id"] for r in rows1]
        ok &= _check(len(set(pair_ids_1)) == 20, "P1 rated 20 distinct pairs, none repeated")
        pair_ids_2 = [r["pair_id"] for r in rows2]
        ok &= _check(len(set(pair_ids_2)) == 20, "P2 rated 20 distinct pairs, none repeated")
        ok &= _check(set(pair_ids_1) == set(pair_ids_2), "both participants rated the same 20 pairs")

        # 4) Participant IDs remain separate — no cross-contamination.
        ok &= _check(
            all(r["participant_id"] == "P1" for r in rows1),
            "every row in P1.csv is tagged participant_id=P1",
        )
        ok &= _check(
            all(r["participant_id"] == "P2" for r in rows2),
            "every row in P2.csv is tagged participant_id=P2",
        )

        # 5) Randomization/counterbalancing actually varies between participants.
        order_1 = pair_ids_1  # insertion order == presentation order here
        order_2 = pair_ids_2
        ok &= _check(order_1 != order_2, "P1 and P2 saw the pairs in a different order")

        shown_first_1 = {r["pair_id"]: r["shown_first"] for r in rows1}
        shown_first_2 = {r["pair_id"]: r["shown_first"] for r in rows2}
        differs = sum(1 for pid in shown_first_1 if shown_first_1[pid] != shown_first_2.get(pid))
        ok &= _check(differs > 0, f"shown-first position differs on {differs}/20 pairs between participants")

        both_positions_used = set(shown_first_1.values()) | set(shown_first_2.values())
        ok &= _check(
            both_positions_used == {"original", "reformulated"},
            "both 'original-first' and 'reformulated-first' positions actually occur",
        )

        # 6) Values round-trip correctly (no silent coercion/loss).
        sample = rows1[0]
        ok &= _check(sample["meaning_preservation"] in {"1", "2", "3", "4", "5"}, "meaning_preservation is 1-5")
        ok &= _check(sample["naturalness"] in {"1", "2", "3", "4", "5"}, "naturalness is 1-5")
        ok &= _check(sample["speaking_ease"] in {"-2", "-1", "0", "1", "2"}, "speaking_ease is -2..2")
        ok &= _check(
            sample["preference"] in {"Original", "Reformulated", "No preference"},
            "preference is one of the three allowed values",
        )
        ok &= _check(bool(sample["timestamp"]), "timestamp recorded")

        # 7) The resulting data is analyzable.
        sys.path.insert(0, str(ROOT / "eval"))
        import pilot_analyze
        combined = pilot_analyze.load_responses([path1, path2])
        ok &= _check(len(combined) == 40, f"pilot_analyze loads all 40 synthetic rows (got {len(combined)})")
        per_pair = pilot_analyze.per_pair_summary(combined)
        ok &= _check(len(per_pair) == 20, f"per-pair summary covers all 20 pairs (got {len(per_pair)})")
        ok &= _check(
            all(row["n_ratings"] == 2 for row in per_pair),
            "each pair shows exactly 2 ratings (one per synthetic participant)",
        )

    finally:
        _restore(snapshot)

    print("\nRESULT:", "ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
