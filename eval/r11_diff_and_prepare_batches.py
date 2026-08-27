"""
eval/r11_diff_and_prepare_batches.py -- Phase 11 re-verification step 2:
diff the full-398-run Phase 11 re-harvest (eval/r11_reverify_raw_results.json)
against the original frozen Phase 10 harvest (eval/r10_raw_results.json),
run_id by run_id. Only runs whose (status, reformulated_text) actually
CHANGED need fresh blind judging -- an unchanged run's prior blind
judgment (CLEAN or DEFECTIVE) still applies by definition, since blind
judgment is a function of the text pair alone.

This is deliberately the FULL 398, not just the 83 run_ids Phase 11's
targeted rerun touched -- it is the actual regression check: it will
surface any unexpected collateral change from the new gates (categories
1-3), not just confirm the cases they were designed for.

Writes:
  eval/r11_diff_summary.json   -- full diff, every run_id classified
  eval/r11_reverify_blind_batch_{1..N}.json -- CHANGED runs only, split
      into batches of ~50 for parallel independent blind judging,
      IDENTICAL schema to eval/r10_blind_batch_N.json (run_id,
      original_text, reformulated_text only -- no domain/category/
      difficulty, same blind discipline as Phase 10).

Run:
    python eval/r11_diff_and_prepare_batches.py
"""
from __future__ import annotations

import json
from pathlib import Path

EVAL = Path(__file__).parent
BATCH_SIZE = 25


def main() -> int:
    old = json.load(open(EVAL / "r10_raw_results.json", encoding="utf-8"))
    new = json.load(open(EVAL / "r11_reverify_raw_results.json", encoding="utf-8"))

    old_by_id = {r["run_id"]: r for r in old["results"]}
    new_by_id = {r["run_id"]: r for r in new["results"]}

    assert set(old_by_id) == set(new_by_id), "run_id sets differ between old and new harvests -- not comparable"

    unchanged = []
    changed = []
    for run_id, old_r in old_by_id.items():
        new_r = new_by_id[run_id]
        same = (old_r["status"] == new_r["status"]) and (old_r["reformulated_text"] == new_r["reformulated_text"])
        entry = {
            "run_id": run_id,
            "old_status": old_r["status"],
            "new_status": new_r["status"],
            "old_text": old_r["reformulated_text"],
            "new_text": new_r["reformulated_text"],
        }
        if same:
            unchanged.append(entry)
        else:
            changed.append(entry)

    print(f"Total runs: {len(old_by_id)}")
    print(f"Unchanged:  {len(unchanged)}")
    print(f"Changed:    {len(changed)}")

    # Status-transition breakdown, for the summary.
    transitions = {}
    for e in changed:
        key = f"{e['old_status']} -> {e['new_status']}"
        transitions[key] = transitions.get(key, 0) + 1
    print("Status transitions among changed runs:")
    for k, v in sorted(transitions.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")

    (EVAL / "r11_diff_summary.json").write_text(
        json.dumps({
            "n_total": len(old_by_id),
            "n_unchanged": len(unchanged),
            "n_changed": len(changed),
            "status_transitions": transitions,
            "changed": changed,
            "unchanged_run_ids": [e["run_id"] for e in unchanged],
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Blind batches: only runs that are actually "reformulated" text worth
    # judging (a changed run whose new status is could_not_safely_reformulate
    # or no_change_needed has no output text to judge for acceptability the
    # same way -- it's a refusal, not a claim of a good rewrite; recorded in
    # the diff summary's status_transitions instead).
    judgeable = [e for e in changed if new_by_id[e["run_id"]]["status"] == "reformulated"]
    print(f"\nChanged AND still 'reformulated' (need blind judging): {len(judgeable)}")

    n_batches = max(1, (len(judgeable) + BATCH_SIZE - 1) // BATCH_SIZE)
    for i in range(n_batches):
        batch = judgeable[i * BATCH_SIZE:(i + 1) * BATCH_SIZE]
        out = [
            {
                "run_id": e["run_id"],
                "original_text": new_by_id[e["run_id"]]["original_text"],
                "reformulated_text": e["new_text"],
            }
            for e in batch
        ]
        path = EVAL / f"r11_reverify_blind_batch_{i + 1}.json"
        path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  wrote {len(out)} rows to {path.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
