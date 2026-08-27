"""
eval/r11_reverify_harvest.py -- Phase 11 re-verification step 1: re-run
the SAME frozen Phase 10 corpus + run plan (398 runs) through TODAY's
live production reformulate() (v1, the same path app.py calls by
default), after Phase 11's categories 1-3 fixes. This is the full
harvest, not just the 83 cases Phase 11's targeted rerun touched --
diffing the full 398 against eval/r10_raw_results.json is what actually
proves (a) the 92%-fixable-batch cases changed as claimed and (b)
nothing else regressed. No modification of reformulate.py/app.py; no
experimental validators invoked here.

Records, per run: status, full changes list (source, triggered_by,
verification), metrics, final_verification, plus wall-clock latency
measured by this harness (not added to reformulate.py itself).

RESEARCH ONLY. Read-only w.r.t. production.

Run:
    python eval/r11_reverify_harvest.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic
from grammar import sanitize_input
from difficulty_profile import DifficultyProfile
import reformulate

EVAL = Path(__file__).parent
OUT_PATH = EVAL / "r11_reverify_raw_results.json"


def build_profile(profile_id: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__r11v_{profile_id}__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for ph in spec.get("phrases", []):
        p.add_phrase(ph, source="user_typed")
    return p


def main() -> int:
    corpus = json.load(open(EVAL / "r10_corpus.json", encoding="utf-8"))
    run_plan = json.load(open(EVAL / "r10_run_plan.json", encoding="utf-8"))
    assert corpus["corpus_version_hash"] == run_plan["corpus_version_hash"], "corpus/run_plan hash mismatch -- frozen files inconsistent"

    by_id = {r["sentence_id"]: r for r in corpus["records"]}
    semantic.load_sbert()

    results = []
    total = len(run_plan["runs"])
    for i, run in enumerate(run_plan["runs"], start=1):
        sent = by_id[run["sentence_id"]]
        profile = build_profile(run["profile_id"], run["spec"])
        corrected_text, grammar_fixes = sanitize_input(sent["sentence_text"])

        t0 = time.perf_counter()
        result = reformulate.reformulate(corrected_text, profile)
        latency_s = time.perf_counter() - t0

        results.append({
            "run_id": run["profile_id"],
            "sentence_id": run["sentence_id"],
            "profile_type": run["profile_type"],
            "profile_spec": run["spec"],
            "domain": sent["domain"],
            "subcategory": sent["subcategory"],
            "expected_opportunity": sent["expected_opportunity"],
            "linguistic_tags": sent["linguistic_tags"],
            "original_text": result["original_text"],
            "reformulated_text": result["reformulated_text"],
            "status": result["status"],
            "changes": result["changes"],
            "skipped": result["skipped"],
            "metrics": result["metrics"],
            "final_verification": result["final_verification"],
            "grammar_fixes_applied": grammar_fixes,
            "latency_seconds": round(latency_s, 4),
        })
        n_changes = len(result["changes"])
        escalated = any(c["source"] != "substitution" for c in result["changes"])
        print(f"  [{i}/{total}] {run['profile_id']:<40} status={result['status']:<28} "
              f"n_changes={n_changes} escalated={escalated} latency={latency_s:.2f}s", flush=True)

    OUT_PATH.write_text(
        json.dumps({
            "corpus_version_hash": corpus["corpus_version_hash"],
            "n_runs": len(results),
            "results": results,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nwrote {len(results)} re-verify results to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
