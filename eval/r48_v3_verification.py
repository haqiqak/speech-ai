"""
eval/r48_v3_verification.py — does _try_escalation_v3 (phoneme constraint
+ iterative regeneration, combined) beat both mechanisms tested alone?
Same 23 escalation-invoked cases as R43/A1/A2/A5/R46's v2 verification,
so this is directly comparable to every number measured so far.

Diagnostic only, read-only against code already written.

Run:
    python eval/r48_v3_verification.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic as sem
from grammar import sanitize_input
import reformulate

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ceiling_probe_r40 import PROFILES, _build_profile  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROBE_PATH = ROOT / "eval" / "ceiling_probe_r40_results.json"
OUT_PATH = ROOT / "eval" / "r48_v3_verification_results.json"


def main() -> int:
    sem.load_sbert()
    data = json.loads(PROBE_PATH.read_text(encoding="utf-8"))["results"]
    targets = [
        r for r in data
        if r["status"] == "could_not_safely_reformulate" or "restructuring" in r["change_sources"]
    ]
    print(f"Re-running {len(targets)} escalation-invoked cases through reformulate_v2() "
          f"(now backed by _try_escalation_v3)...", flush=True)

    results = []
    for i, r in enumerate(targets, 1):
        profile = _build_profile(r["profile"], PROFILES[r["profile"]])
        corrected, _ = sanitize_input(r["original_text"])
        out = reformulate.reformulate_v2(corrected, profile)
        esc_changes = [c for c in out["changes"] if c["source"] == "restructuring_v3"]
        results.append({
            "profile": r["profile"], "source": r["source"],
            "original_text": out["original_text"], "reformulated_text": out["reformulated_text"],
            "status": out["status"],
            "escalated": len(esc_changes) > 0,
            "rounds_used": esc_changes[0]["verification"].get("rounds_used") if esc_changes else None,
            "beam_kills": esc_changes[0]["verification"].get("beam_kills") if esc_changes else None,
            "sbert": esc_changes[0]["verification"].get("sbert_sim") if esc_changes else None,
            "validation": out["validation"],
        })
        print(f"  [{i}/{len(targets)}] status={out['status']:<28} rounds={results[-1]['rounds_used']} "
              f"validation_flagged={out['validation']['flagged']}", flush=True)

    n = len(results)
    n_reformulated = sum(1 for r in results if r["status"] == "reformulated")
    OUT_PATH.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n=== R48 (v3: phoneme constraint + iterative regeneration, combined) ===")
    print(f"reformulated: {n_reformulated}/{n} ({n_reformulated/n:.0%})")
    print("Comparison to every number measured so far on this same 23-case corpus:")
    print("  baseline (post-hoc blocking only):        2/23  (9%)")
    print("  A1 (expanded blocking):                   3/23  (13%)")
    print("  A2 (iterative regeneration alone):         6/23  (26%)")
    print("  A5 (blocking+NLI+grammar stacked):         1/23  (4%)")
    print("  v2 (phoneme constraint, single-round):    12/23  (52%)")
    print(f"  v3 (phoneme constraint + iteration):      {n_reformulated}/23  ({n_reformulated/n:.0%})")

    rounds_dist: dict = {}
    for r in results:
        if r["rounds_used"] is not None:
            rounds_dist[r["rounds_used"]] = rounds_dist.get(r["rounds_used"], 0) + 1
    print(f"\nrounds-used distribution among escalated cases: {rounds_dist}")

    n_flagged = sum(1 for r in results if r["validation"]["flagged"])
    print(f"validator flagged: {n_flagged}/{n_reformulated} of reformulated cases")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
