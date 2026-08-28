"""
eval/step3_gencheck_harvest.py -- Architecture Go/No-Go Step 3
generalization check: run eval/step3_gencheck_corpus.py's 36
(sentence, profile) pairs through today's live production reformulate(),
freezing raw output before any judging, matching every prior phase's
harvest discipline.

Run:
    python eval/step3_gencheck_harvest.py
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
from step3_gencheck_corpus import CORPUS, RUN_PLAN

EVAL = Path(__file__).parent


def build_profile(run_id: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__step3_gencheck_{run_id}__")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    return p


def main() -> int:
    by_id = {c["id"]: c for c in CORPUS}
    semantic.load_sbert()
    semantic.load_nli_model()
    semantic.load_grammar_tool()

    results = []
    total = len(RUN_PLAN)
    for i, run in enumerate(RUN_PLAN, 1):
        sent = by_id[run["id"]]
        run_id = f"{run['id']}-{run['profile_type']}"
        profile = build_profile(run_id, run)
        corrected_text, grammar_fixes = sanitize_input(sent["text"])

        t0 = time.perf_counter()
        result = reformulate.reformulate(corrected_text, profile)
        latency_s = time.perf_counter() - t0

        results.append({
            "run_id": run_id,
            "sentence_id": run["id"],
            "domain": sent["domain"],
            "topic": sent["topic"],
            "profile_type": run["profile_type"],
            "profile_spec": run,
            "original_text": result["original_text"],
            "reformulated_text": result["reformulated_text"],
            "status": result["status"],
            "changes": result["changes"],
            "skipped": result["skipped"],
            "metrics": result["metrics"],
            "latency_seconds": round(latency_s, 4),
        })
        print(f"  [{i}/{total}] {run_id:<30} status={result['status']:<28} latency={latency_s:.2f}s", flush=True)

    OUT = EVAL / "step3_gencheck_raw_results.json"
    OUT.write_text(json.dumps({"n_runs": len(results), "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {len(results)} results to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
