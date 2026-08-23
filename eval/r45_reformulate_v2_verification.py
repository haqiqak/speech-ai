"""
eval/r45_reformulate_v2_verification.py — does the REAL, integrated
reformulate_v2() reproduce what the throwaway diagnostic prototypes
measured (VALIDATION.md §36), not just the standalone scripts?

Runs reformulate_v2() directly (the actual production-quality function
in reformulate.py, not a copy) against:
  1. The same 23 escalation-invoked (sentence, profile) pairs from R40 —
     confirms the phoneme-aware escalation path (_try_escalation_v2)
     behaves the way Prototype 2 measured.
  2. The 48x4=192 full R40 corpus — confirms reformulate_v2() as a whole
     (substitution unchanged + new escalation + new validation) doesn't
     regress anything, and reports the validation block's flag rate
     end-to-end for the first time (previously only tested as separate
     NLI-only / grammar-only passes on the substitution tier alone).

Does not modify reformulate.py, rephrase.py, or semantic.py. Read-only
verification of code already written.

Run:
    python eval/r45_reformulate_v2_verification.py
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
from ceiling_probe_r40 import SENTENCES, PROFILES, _build_profile  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROBE_PATH = ROOT / "eval" / "ceiling_probe_r40_results.json"
OUT_PATH = ROOT / "eval" / "r45_reformulate_v2_verification_results.json"


def main() -> int:
    sem.load_sbert()
    data = json.loads(PROBE_PATH.read_text(encoding="utf-8"))["results"]
    escalation_targets = [
        r for r in data
        if r["status"] == "could_not_safely_reformulate" or "restructuring" in r["change_sources"]
    ]

    print(f"Part 1: re-running the {len(escalation_targets)} escalation-invoked cases "
          f"through the REAL reformulate_v2()...", flush=True)
    results = []
    for i, r in enumerate(escalation_targets, 1):
        profile = _build_profile(r["profile"], PROFILES[r["profile"]])
        corrected, _ = sanitize_input(r["original_text"])
        out = reformulate.reformulate_v2(corrected, profile)
        restructuring_changes = [c for c in out["changes"] if c["source"] == "restructuring_v2"]
        results.append({
            "profile": r["profile"], "source": r["source"],
            "original_text": out["original_text"], "reformulated_text": out["reformulated_text"],
            "status": out["status"],
            "used_phoneme_escalation": len(restructuring_changes) > 0,
            "beam_kills": restructuring_changes[0]["verification"].get("beam_kills") if restructuring_changes else None,
            "validation": out["validation"],
        })
        print(f"  [{i}/{len(escalation_targets)}] status={out['status']:<28} "
              f"escalated_v2={len(restructuring_changes) > 0} "
              f"validation_flagged={out['validation']['flagged']}", flush=True)

    n = len(results)
    n_reformulated = sum(1 for r in results if r["status"] == "reformulated")
    n_escalated_v2 = sum(1 for r in results if r["used_phoneme_escalation"])
    print(f"\nPart 1 summary: {n_reformulated}/{n} ({n_reformulated/n:.0%}) reformulated "
          f"(vs. 2/23 = 9% for reformulate()'s original escalation on this same corpus, "
          f"VALIDATION.md §36.2's baseline)")
    print(f"  of those, {n_escalated_v2} actually went through phoneme-aware escalation")

    OUT_PATH.write_text(json.dumps({"escalation_corpus_results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote results to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
