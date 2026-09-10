"""
stage_lr/generate_pairs_r10.py — Stage LR data path (a), batch 2: same
method as generate_pairs.py, applied to eval/r10_raw_results.json (Phase
10's 398-run stress-test harvest — not part of the 135 labeled_dataset.json
records, never covered by batch 1). Reuses attempt_second_candidate()
unchanged; the only real difference from batch 1 is that R10's raw
results already carry each run's exact profile_spec directly, so there
is no cross-file profile-matching step (and no version of the batch-1
matching bug possible here — nothing to disambiguate).

    DISABLE_DATAMUSE=1 python stage_lr/generate_pairs_r10.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DISABLE_DATAMUSE", "1")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import paths  # noqa: F401,E402
from difficulty_profile import DifficultyProfile  # noqa: E402
from stage_lr.generate_pairs import attempt_second_candidate  # noqa: E402

R10_RAW = ROOT / "eval" / "r10_raw_results.json"
OUT_PATH = ROOT / "stage_lr" / "data" / "lr1_candidate_generation_log_r10.json"


def _build_profile(run_id: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__lr1_r10_{run_id}__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for ph in spec.get("phrases", []):
        p.add_phrase(ph, source="user_typed")
    return p


def main() -> None:
    data = json.loads(R10_RAW.read_text(encoding="utf-8"))
    runs = data["results"]

    # Build the flat list of (run, change) targets up front so the
    # running count matches what's actually attempted.
    targets = []
    for run in runs:
        for change in run.get("changes", []):
            if change.get("source") != "substitution":
                continue
            targets.append((run, change))

    results = []
    counts = {"total_substitution_changes": len(targets), "attempt_error": 0,
              "no_second_candidate": 0, "second_candidate_found": 0}

    for i, (run, change) in enumerate(targets, 1):
        uid = f"{run['run_id']}::pos{change['position']}"
        pseudo_record = {
            "uid": uid,
            "original_text": run["original_text"],
            "reformulated_text": run["reformulated_text"],
            "changed_word_pair": [change["original"], change["replacement"]],
        }
        profile_entry = {
            "profile": _build_profile(run["run_id"], run["profile_spec"]),
            "profile_spec": {"name": f"{run['run_id']}:{run['profile_type']}", **run["profile_spec"]},
            "source": "r10_raw_results.json",
        }

        try:
            res = attempt_second_candidate(pseudo_record, profile_entry)
        except Exception as e:
            counts["attempt_error"] += 1
            results.append({"uid": uid, "outcome": "attempt_error", "reason": f"{type(e).__name__}: {e}"})
            print(f"[{i}/{len(targets)}] {uid:<40} attempt_error: {e}", flush=True)
            continue

        counts[res["outcome"]] = counts.get(res["outcome"], 0) + 1
        results.append(res)
        print(f"[{i}/{len(targets)}] {uid:<40} {res['outcome']}", flush=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({"counts": counts, "results": results}, indent=2), encoding="utf-8")

    print()
    print("=== FINAL COUNTS (R10 batch) ===")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
