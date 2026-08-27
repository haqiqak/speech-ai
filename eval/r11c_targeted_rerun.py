"""
eval/r11c_targeted_rerun.py -- Phase 11C verification: re-run ONLY the
specific R10 run_ids this phase's four mechanisms (NLI gate, escalation-
tier duplicate-word check, grammar gate, mass-noun check) were evidenced
against, through today's live production reformulate(), and compare
against the original Phase 10B defect that motivated each fix. NOT a
full re-run of the R10 corpus -- that's the next, separate step.

Run:
    python eval/r11c_targeted_rerun.py
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

# (a) grammar/agreement on T5 escalation output
CATEGORY_A = [
    "R10-002-core-word", "R10-013-calib-multi_word", "R10-029-core-word",
    "R10-037-calib-multi_word", "R10-061-core-word", "R10-061-calib-multi_word",
    "R10-105-core-word", "R10-108-core-word",
]

# (b) polarity/meaning reversal without an explicit negation marker
CATEGORY_B = [
    "R10-005-core-word", "R10-088-core-word", "R10-101-core-word",
    "R10-025-calib-multi_word", "R10-059-core-word", "R10-059-core-dense_mixed_generic",
]

# (c) countability / mass-noun / category preservation
CATEGORY_C = [
    "R10-073-calib-word_plus_sound", "R10-091-core-multi_sound",
    "R10-091-calib-dense_mixed_generic", "R10-122-core-word", "R10-011-core-word",
]

# (d) escalation-tier duplicate-word introduction
CATEGORY_D = [
    "R10-061-core-word", "R10-061-calib-multi_word",
    "R10-024-core-word", "R10-025-calib-multi_word",
]

ALL_TARGETS = sorted(set(CATEGORY_A + CATEGORY_B + CATEGORY_C + CATEGORY_D))


def build_profile(profile_id: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__r11c_{profile_id}__")
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
    old_results = json.load(open(EVAL / "r10b_defective_enriched.json", encoding="utf-8"))
    old_by_id = {d["run_id"]: d for d in old_results}

    by_sentence = {r["sentence_id"]: r for r in corpus["records"]}
    by_run_id = {r["profile_id"]: r for r in run_plan["runs"]}
    semantic.load_sbert()
    semantic.load_nli_model()
    semantic.load_grammar_tool()

    missing = [rid for rid in ALL_TARGETS if rid not in by_run_id]
    if missing:
        print("MISSING FROM RUN PLAN (skipped):", missing)

    still_bad = []
    fixed = []
    not_in_old = []

    for rid in ALL_TARGETS:
        run = by_run_id.get(rid)
        if run is None:
            continue
        sent = by_sentence[run["sentence_id"]]
        profile = build_profile(run["profile_id"], run["spec"])
        corrected_text, _ = sanitize_input(sent["sentence_text"])
        result = reformulate.reformulate(corrected_text, profile)

        old = old_by_id.get(rid)
        old_text = old["reformulated_text"] if old else None
        new_text = result["reformulated_text"]

        print(f"\n=== {rid} ===")
        print(f"  status:  {result['status']}")
        print(f"  OLD(bad): {old_text}")
        print(f"  NEW:      {new_text}")

        if old is None:
            not_in_old.append(rid)
            continue

        defect_survived = (new_text.strip() == old_text.strip()) if old_text else False
        if defect_survived:
            still_bad.append(rid)
        else:
            fixed.append(rid)

    print("\n\n===== SUMMARY =====")
    print(f"targeted: {len(ALL_TARGETS)}  found_in_old_defective_set: {len(ALL_TARGETS) - len(not_in_old)}")
    print(f"changed from the old defect: {len(fixed)}")
    print(f"still identical to the old defect: {len(still_bad)}")
    if still_bad:
        print("STILL BAD:", still_bad)
    if not_in_old:
        print("NOT FOUND IN r10b_defective_enriched.json (id mismatch?):", not_in_old)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
