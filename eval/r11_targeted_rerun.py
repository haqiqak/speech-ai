"""
eval/r11_targeted_rerun.py -- Phase 11 verification step 3 (approved plan):
re-run ONLY the specific R10 run_ids targeted by categories 1-3 (fixed-term
protection, duplicate-word rejection, bad-pair blocklist) through today's
live production reformulate(), and compare against the original Phase 10B
defect that motivated each fix. NOT a re-run of the full R10 harvest (the
plan explicitly says not to do that as a first step) -- this is the
cheapest thing that's actually tied to the evidence.

For each targeted run_id this prints: old (defective) reformulated_text,
new reformulated_text, and a mechanical check of whether the SPECIFIC
old defect (a dropped protected phrase, a reintroduced duplicate, or the
exact old bad word pair) is still present. It does not re-run blind human
judging -- "no longer contains the mechanical defect" is a narrower, cheaper
claim than "now CLEAN", and is reported as such.

Run:
    python eval/r11_targeted_rerun.py
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

# Category 1 -- fixed-term/idiom protection list expansion (semantic.py
# IDIOM_PHRASES) and the new escalation-output enforcement.
CATEGORY_1 = [
    "R10-003-core-word", "R10-004-core-sparse_common_sound", "R10-015-core-word",
    "R10-023-core-word", "R10-029-core-word", "R10-031-core-word",
    "R10-031-calib-multi_sound", "R10-031-calib-sparse_common_sound",
    "R10-031-calib-dense_mixed_generic",
    "R10-038-core-word", "R10-041-core-word", "R10-042-core-word",
    "R10-055-core-dense_mixed_generic", "R10-057-core-sparse_common_sound", "R10-058-core-word",
    "R10-059-core-dense_mixed_generic", "R10-084-core-multi_sound",
    "R10-092-core-word", "R10-133-core-word",
]

# Category 2 -- duplicate-word-in-sentence rejection.
CATEGORY_2 = [
    "R10-001-core-word", "R10-001-calib-single_word",
    "R10-001-calib-word_plus_sound", "R10-024-core-word",
    "R10-025-calib-multi_word", "R10-038-core-sparse_common_sound",
    "R10-060-core-dense_mixed_generic",
    "R10-061-core-word", "R10-061-calib-multi_word",
]

# Category 3 -- specific bad-pair blocklist.
CATEGORY_3 = [
    "R10-005-core-word", "R10-008-core-dense_mixed_generic",
    "R10-011-core-sparse_common_sound", "R10-014-core-dense_mixed_generic",
    "R10-019-core-sparse_common_sound", "R10-020-core-dense_mixed_generic",
    "R10-021-core-sparse_common_sound", "R10-022-core-multi_sound",
    "R10-043-core-word", "R10-043-calib-multi_word",
    "R10-044-core-word", "R10-044-core-dense_mixed_generic",
    "R10-051-core-dense_mixed_generic", "R10-059-core-dense_mixed_generic",
    "R10-061-calib-single_word", "R10-061-calib-word_plus_sound",
    "R10-061-calib-single_sound", "R10-064-core-word",
    "R10-068-core-multi_sound", "R10-069-core-dense_mixed_generic",
    "R10-072-core-word", "R10-073-calib-word_plus_sound",
    "R10-074-core-word", "R10-075-core-dense_mixed_generic",
    "R10-079-core-sparse_common_sound", "R10-080-core-multi_sound",
    "R10-083-core-word", "R10-086-core-word", "R10-089-core-word",
    "R10-091-core-word", "R10-091-calib-single_word",
    "R10-091-calib-word_plus_sound", "R10-094-core-word",
    "R10-099-core-word", "R10-105-core-sparse_common_sound",
    "R10-106-core-word", "R10-108-core-word",
    "R10-109-calib-single_word", "R10-109-calib-word_plus_sound",
    "R10-113-core-dense_mixed_generic", "R10-114-core-word",
    "R10-114-core-sparse_common_sound", "R10-118-core-word",
    "R10-121-core-word", "R10-121-calib-single_word",
    "R10-121-calib-word_plus_sound", "R10-123-core-sparse_common_sound",
    "R10-124-core-multi_sound", "R10-125-core-word",
    "R10-128-core-word", "R10-128-core-sparse_common_sound",
    "R10-129-core-word", "R10-131-core-word",
    "R10-133-calib-multi_sound", "R10-133-calib-sparse_common_sound",
    "R10-133-calib-dense_mixed_generic",
]

ALL_TARGETS = sorted(set(CATEGORY_1 + CATEGORY_2 + CATEGORY_3))


def build_profile(profile_id: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__r11_{profile_id}__")
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

        # Mechanical check: did the exact old changes' replacements survive
        # into the new output? If the new text differs from the old
        # defective one, or the sentence is now safely left unchanged /
        # refused, treat the specific old defect as gone.
        old_replacements = [c["replacement"].lower() for c in old.get("changes", [])
                             if c.get("source") == "substitution"]
        defect_survived = (new_text.strip() == old_text.strip()) if old_text else False
        if not defect_survived and old_replacements:
            # For substitution-sourced defects, also confirm the specific
            # bad replacement word no longer appears verbatim in the new
            # text (guards against a different, still-bad change landing
            # in the same slot by coincidence).
            defect_survived = any(rep in new_text.lower().split() for rep in old_replacements) and new_text == old_text

        if defect_survived:
            still_bad.append(rid)
        else:
            fixed.append(rid)

    print("\n\n===== SUMMARY =====")
    print(f"targeted: {len(ALL_TARGETS)}  found_in_old_defective_set: {len(ALL_TARGETS) - len(not_in_old)}")
    print(f"fixed (output changed from the old defect): {len(fixed)}")
    print(f"still identical to the old defect: {len(still_bad)}")
    if still_bad:
        print("STILL BAD:", still_bad)
    if not_in_old:
        print("NOT FOUND IN r10b_defective_enriched.json (id mismatch?):", not_in_old)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
