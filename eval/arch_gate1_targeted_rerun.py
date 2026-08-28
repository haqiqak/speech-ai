"""
eval/arch_gate1_targeted_rerun.py -- Architecture Go/No-Go Step 1
targeted verification: re-run the R10 corpus's dense/multi-sound-profile
run_ids that were REFUSED (could_not_safely_reformulate) as of the
post-Phase-11C harvest (eval/r11_reverify_raw_results.json) through
today's live production reformulate() -- now using the phoneme-aware
decoding-time constraint for escalation. These are exactly the cases
R45's Prototype 2 was built to help: dense-sound-pattern sentences where
the OLD post-hoc-rejection generator could rarely produce ANY usable
candidate at all.

Reports, per case: old status (always could_not_safely_reformulate by
construction), new status, and whether a candidate was now produced.

Run:
    python eval/arch_gate1_targeted_rerun.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic
from grammar import sanitize_input
from difficulty_profile import DifficultyProfile
import reformulate

EVAL = Path(__file__).parent
DENSE_TYPES = {"dense_mixed_generic", "multi_sound", "word_plus_sound"}


def build_profile(profile_id: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__archgate1_{profile_id}__")
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
    prior = json.load(open(EVAL / "r11_reverify_raw_results.json", encoding="utf-8"))

    by_sentence = {r["sentence_id"]: r for r in corpus["records"]}
    by_run_id = {r["profile_id"]: r for r in run_plan["runs"]}
    prior_by_id = {r["run_id"]: r for r in prior["results"]}

    targets = [
        r["run_id"] for r in prior["results"]
        if r["status"] == "could_not_safely_reformulate"
        and by_run_id.get(r["run_id"], {}).get("profile_type") in DENSE_TYPES
    ]

    semantic.load_sbert()
    semantic.load_nli_model()
    semantic.load_grammar_tool()

    now_reformulated = 0
    still_refused = 0
    latencies = []

    for rid in targets:
        run = by_run_id[rid]
        sent = by_sentence[run["sentence_id"]]
        profile = build_profile(run["profile_id"], run["spec"])
        corrected_text, _ = sanitize_input(sent["sentence_text"])

        import time
        t0 = time.perf_counter()
        result = reformulate.reformulate(corrected_text, profile)
        latencies.append(time.perf_counter() - t0)

        print(f"\n=== {rid} ({run['profile_type']}) ===")
        print(f"  OLD status: could_not_safely_reformulate")
        print(f"  NEW status: {result['status']}")
        print(f"  NEW text:   {result['reformulated_text'][:150]}")
        for c in result["changes"]:
            if c["source"] == "restructuring":
                print(f"  beam_kills: {c['verification'].get('beam_kills')}")

        if result["status"] == "reformulated":
            now_reformulated += 1
        else:
            still_refused += 1

    print("\n\n===== SUMMARY =====")
    print(f"targeted (dense-profile, previously refused): {len(targets)}")
    print(f"now produce a candidate: {now_reformulated}")
    print(f"still refused: {still_refused}")
    if latencies:
        latencies.sort()
        n = len(latencies)
        print(f"latency (this targeted set): mean={sum(latencies)/n:.2f}s median={latencies[n//2]:.2f}s max={latencies[-1]:.2f}s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
