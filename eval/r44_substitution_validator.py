"""
eval/r44_substitution_validator.py — R44 Prototype 1: does NLI + grammar,
run TOGETHER, materially improve validation on the full substitution-tier
corpus (all 79 R40 sentence-level pairs, not the 11-case A4 sample or the
79-but-NLI-only A3 run)?

Diagnostic only. Reuses eval/r43a3_nli_validation_results.json's
already-computed NLI labels for all 79 pairs (no re-run needed — same
model, same data) and adds a full LanguageTool pass over all 79
(previously only 11 were checked, in A4). No production code touched.

Run:
    python eval/r44_substitution_validator.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
JRE_BIN = ROOT / ".cache" / "jre17" / "bin"
os.environ.pop("LTP_PATH", None)
os.environ["PATH"] = str(JRE_BIN) + os.pathsep + os.environ.get("PATH", "")

NLI_PATH = ROOT / "eval" / "r43a3_nli_validation_results.json"
OUT_PATH = ROOT / "eval" / "r44_substitution_validator_results.json"


def main() -> int:
    from language_tool_python import LanguageTool

    nli_rows = json.loads(NLI_PATH.read_text(encoding="utf-8"))["results"]
    print(f"Loaded {len(nli_rows)} NLI-scored pairs from A3.", flush=True)

    print("Loading LanguageTool...", flush=True)
    tool = LanguageTool("en-US")
    print("Loaded. Checking all 79 reformulated sentences...", flush=True)

    rows = []
    for i, r in enumerate(nli_rows, 1):
        matches = tool.check(r["reformulated_text"])
        grammar_flag = len(matches) > 0
        nli_flag = r["either_contradiction"]
        combined_flag = nli_flag or grammar_flag
        rows.append({
            "profile": r["profile"],
            "verdict": r["verdict"],
            "original_text": r["original_text"],
            "reformulated_text": r["reformulated_text"],
            "nli_flag": nli_flag,
            "grammar_flag": grammar_flag,
            "grammar_matches": [m.ruleId if hasattr(m, "ruleId") else getattr(m, "rule_id", None) for m in matches],
            "combined_flag": combined_flag,
        })
        print(f"  [{i}/{len(nli_rows)}] [{r['verdict']:<7}] nli={nli_flag} grammar={grammar_flag} "
              f"combined={combined_flag}  {r['original_text'][:50]}", flush=True)

    tool.close()
    OUT_PATH.write_text(json.dumps({"results": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {len(rows)} rows to {OUT_PATH}")

    # ── Aggregate ──
    from collections import defaultdict
    by_v = defaultdict(list)
    for r in rows:
        by_v[r["verdict"]].append(r)

    print("\n=== Recall/false-positive rate by verdict, per check and combined ===")
    print(f"{'verdict':<8}{'n':<5}{'NLI only':<12}{'Grammar only':<14}{'Combined (OR)':<15}")
    for v in ["CLEAN", "MINOR", "SEVERE"]:
        subset = by_v.get(v, [])
        n = len(subset)
        if n == 0:
            continue
        nli_r = sum(1 for r in subset if r["nli_flag"])
        gram_r = sum(1 for r in subset if r["grammar_flag"])
        comb_r = sum(1 for r in subset if r["combined_flag"])
        print(f"{v:<8}{n:<5}{f'{nli_r}/{n} ({nli_r/n:.0%})':<12}"
              f"{f'{gram_r}/{n} ({gram_r/n:.0%})':<14}{f'{comb_r}/{n} ({comb_r/n:.0%})':<15}")

    severe = by_v.get("SEVERE", [])
    good = by_v.get("CLEAN", []) + by_v.get("MINOR", [])
    n_severe, n_good = len(severe), len(good)
    comb_recall = sum(1 for r in severe if r["combined_flag"])
    comb_fp = sum(1 for r in good if r["combined_flag"])
    print(f"\nCombined validator: recall on SEVERE = {comb_recall}/{n_severe} ({comb_recall/n_severe:.0%}), "
          f"false-positive rate on CLEAN+MINOR = {comb_fp}/{n_good} ({comb_fp/n_good:.0%})")

    # Which SEVERE cases neither check catches (the residual gap)
    print("\n=== SEVERE cases neither NLI nor grammar catches ===")
    for r in severe:
        if not r["combined_flag"]:
            print(f"  {r['original_text'][:55]} -> {r['reformulated_text'][:55]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
