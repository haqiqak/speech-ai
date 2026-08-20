"""
eval/pilot_select_pairs_v4.py — bounded current-state human evaluation,
v4. Built per direct user instruction after R38 (VALIDATION.md §31): the
only preference/naturalness numbers on record predate R19-R37's fixes,
so no valid current-state measurement exists. This regenerates a small,
deliberate corpus through TODAY's live engine and writes it to
eval/pilot_pairs.json for eval/pilot_app.py (unmodified) to serve.

Reuses eval/pilot_select_pairs.py's exact structure and schema — same
_build_profile/_run_item/build_pairs shape, same JSON fields, same
"reformulated"-status requirement, same restructuring-stability
recheck. Two deliberate differences:

  1. LIVE Datamuse, not DISABLE_DATAMUSE=1 — the v3 script pins that
     flag for determinism, but R31 found it changes the candidate pool
     materially (e.g. "grab"->"take" doesn't even appear without live
     Datamuse access). This evaluation is explicitly about current,
     real user-facing behavior, not internal reproducibility, so this
     run does NOT set that flag.
  2. Two groups, not one flat list:
       Group A (10) — the exact same case_id/text/profile as 10 of the
       original v3 items (pair_01, 02, 11, 13, 16, 17, 24, 28, 29, 30 —
       chosen because they have a recorded v3 rating AND are exactly
       the cases R19-R37 touched: idiom guard, WSD, phrase-tier, the
       R30 POS fix, the R33-R37 contextual-fit quirks). Regenerating
       these through today's engine gives a direct before/after delta.
       Group B (10) — fresh (case_id, text, profile) combinations never
       rated before, same category-weighting spirit as v3, to avoid
       anchoring the whole read on already-known edge cases.

The original v3 pilot_pairs.json / pilot_responses/P1.csv were archived
to eval/archive_v3/ (pilot_pairs_v3.json / P1_v3_responses.csv) before
this script ever writes anything — never destroyed, per this project's
own archive_v2 precedent.

Run:
    python eval/pilot_select_pairs_v4.py
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

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "eval" / "pilot_pairs.json"

# (case_id, category, text, profile_spec, group)
ITEMS: list[tuple[str, str, str, dict, str]] = [
    # ── Group A: historical re-test, exact v3 text/profile, regenerated live ──
    ("gs_hows_it_going", "global_sound", "Hey, how's it going today?", {"sounds": ["g"]}, "A"),
    ("gs_sleep_well", "global_sound", "Good morning, did you sleep well?", {"sounds": ["s"]}, "A"),
    # gs_driving_crazy swapped out: R19's idiom guard now fully protects
    # "driving me crazy" (the exact historical defect), so the sentence
    # produces could_not_safely_reformulate today -- itself a real,
    # notable finding (recorded in the v4 report), but not a ratable
    # pair for this study. Swapped for a different historical item per
    # this script's own "swap, don't silently drop" discipline.
    ("gs_cant_believe", "global_sound", "I can't believe this happened again.", {"sounds": ["h"]}, "A"),
    ("gs_bus_late", "global_sound", "The bus was late again this morning.", {"sounds": ["l"]}, "A"),
    ("gs_grab_jacket", "global_sound", "Let me grab my jacket real quick.", {"sounds": ["gr"]}, "A"),
    ("gs_grab_coffee", "global_sound", "Do you want to grab coffee later?", {"sounds": ["gr"]}, "A"),
    ("wp_valuable_lesson", "word_pattern", "This is a valuable lesson for everyone here.",
     {"words": ["valuable"], "patterns": {"valuable": ["V"]}}, "A"),
    ("md_running_traffic", "multi_difficulty", "Sorry, running behind, stuck in traffic right now.",
     {"sounds": ["r"]}, "A"),
    ("md_push_meeting_coffee", "multi_difficulty", "Can we push the meeting and grab coffee after?",
     {"sounds": ["p", "gr"]}, "A"),
    ("md_print_report_coffee", "multi_difficulty", "Can you print the report and grab some coffee?",
     {"sounds": ["pr", "gr"]}, "A"),

    # ── Group B: fresh, never rated before ──────────────────────────────
    ("gs2_forgot_call", "global_sound", "I forgot to call my mother yesterday.", {"sounds": ["f"]}, "B"),
    ("gs2_finished_homework", "global_sound", "She quickly finished her homework before dinner.", {"sounds": ["f"]}, "B"),
    # gs2_nice_weather swapped: "weather"/"week" both /w/-onset, neither
    # had a safe candidate -- could_not_safely_reformulate. Swapped, per
    # this script's own discipline, not silently dropped.
    ("gs2_wonderful_experience", "global_sound", "That was a truly wonderful experience.", {"sounds": ["w"]}, "B"),
    ("gs2_brings_snacks", "global_sound", "He always brings snacks to the office.", {"sounds": ["b"]}, "B"),
    ("gs2_moved_apartment", "global_sound", "They recently moved into a new apartment.", {"sounds": ["m"]}, "B"),
    # dw2_project_deadline swapped: "deadline" had no safe candidate --
    # could_not_safely_reformulate. Swapped, not silently dropped.
    ("dw2_complicated_situation", "declared_word", "The situation became quite complicated.", {"words": ["complicated"]}, "B"),
    ("dw2_movie_hilarious", "declared_word", "I found the movie absolutely hilarious.", {"words": ["hilarious"]}, "B"),
    ("wp2_negotiations_successful", "word_pattern", "The negotiations were surprisingly successful.",
     {"words": ["successful"], "patterns": {"successful": ["S"]}}, "B"),
    ("wp2_thoughtful_gesture", "word_pattern", "That was a genuinely thoughtful gesture.",
     {"words": ["thoughtful"], "patterns": {"thoughtful": ["TH"]}}, "B"),
    ("md2_grab_dinner", "multi_difficulty", "We should probably grab dinner before the movie.",
     {"sounds": ["pr", "gr"]}, "B"),
]


def _build_profile(name: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__pilotv4_{name}__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for word, phones in spec.get("patterns", {}).items():
        p.set_word_pattern(word, phones)
    return p


def _run_item(case_id: str) -> dict:
    by_id = {c[0]: c for c in ITEMS}
    if case_id not in by_id:
        raise KeyError(f"unknown case_id: {case_id}")
    _, category, text, spec, group = by_id[case_id]

    semantic.load_sbert()
    profile = _build_profile(case_id, spec)
    corrected_text, grammar_fixes = sanitize_input(text)
    result = reformulate.reformulate(corrected_text, profile)
    if result["status"] != "reformulated":
        raise RuntimeError(
            f"{case_id} does not produce a 'reformulated' result "
            f"(status={result['status']}) — this item must be swapped, not silently dropped."
        )

    sources = {c["source"] for c in result["changes"]}
    triggers = set()
    for c in result["changes"]:
        triggers.update(c.get("triggered_by", []))

    m = result["metrics"]
    flagged_before = m["flagged_words_before"]
    flagged_after = m["flagged_words_after"]

    return {
        "case_id": case_id,
        "category": category,
        "group": group,
        "profile_spec": spec,
        "triggered_by": sorted(triggers),
        "changes_made": [
            {
                "original": c["original"], "replacement": c["replacement"], "source": c["source"],
                "contextual_fit": c["verification"].get("contextual_fit"),
            }
            for c in result["changes"]
        ],
        "profile_match": {
            "flagged_words_before": flagged_before,
            "flagged_words_after": flagged_after,
            "difficulty_resolved": flagged_after < flagged_before,
            "note": (
                "Whether the declared difficulty was actually avoided in the output — "
                "computed automatically from reformulate.py's own before/after flagged-word "
                "count. NOT part of the participant's rating task; reported here only for "
                "post-hoc, side-by-side analysis (never blended with human scores)."
            ),
        },
        "original_text": result["original_text"],
        "reformulated_text": result["reformulated_text"],
        "status": result["status"],
        "metrics": m,
        "final_verification": result["final_verification"],
        "n_changes": len(result["changes"]),
        "has_restructuring": "restructuring" in sources,
        "grammar_fixes_applied": len(grammar_fixes),
    }


def build_pairs() -> list[dict]:
    """Same fresh-subprocess-per-item + restructuring-stability-recheck
    discipline as v3 (VALIDATION.md SS8.4's T5 non-determinism finding),
    but WITHOUT DISABLE_DATAMUSE=1 -- live Datamuse, matching real
    production behavior, per explicit instruction for this evaluation."""
    import subprocess

    def run_once(case_id: str) -> dict:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--single", case_id],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        if proc.returncode != 0:
            raise RuntimeError(f"subprocess for {case_id} failed:\n{proc.stderr[-2000:]}")
        json_line = None
        for line in proc.stdout.splitlines():
            if line.startswith("PILOT_ITEM_JSON:"):
                json_line = line[len("PILOT_ITEM_JSON:"):]
        if json_line is None:
            raise RuntimeError(f"no JSON output from subprocess for {case_id}")
        return json.loads(json_line)

    pairs = []
    for case_id, _category, _text, _spec, _group in ITEMS:
        first = run_once(case_id)
        if first["has_restructuring"]:
            for trial in range(2):
                again = run_once(case_id)
                if again["status"] != "reformulated":
                    raise RuntimeError(
                        f"{case_id} is unstable across fresh-process trials "
                        f"(trial {trial+2} failed) — must be swapped for a stable item, "
                        f"not shipped as-is."
                    )
        pairs.append(first)
        print(f"  done: {case_id} ({first['group']})" + (" (restructuring, stability-checked x3)" if first["has_restructuring"] else ""))
    return pairs


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--single":
        result = _run_item(sys.argv[2])
        print("PILOT_ITEM_JSON:" + json.dumps(result, ensure_ascii=False))
        return 0

    print(f"Running {len(ITEMS)} items (live Datamuse, no determinism flag)...")
    pairs = build_pairs()
    for i, item in enumerate(pairs):
        item["pair_id"] = f"pair_{i+1:02d}"

    by_cat: dict[str, int] = {}
    by_group: dict[str, int] = {}
    for p in pairs:
        by_cat[p["category"]] = by_cat.get(p["category"], 0) + 1
        by_group[p["group"]] = by_group.get(p["group"], 0) + 1
    print(f"\nBuilt {len(pairs)} pairs: {by_cat} groups={by_group}")
    n_resolved = sum(1 for p in pairs if p["profile_match"]["difficulty_resolved"])
    print(f"Profile-match (automated, NOT part of participant task): "
          f"{n_resolved}/{len(pairs)} pairs actually resolved their declared difficulty")
    for p in pairs:
        print(f"  [{p['group']}][{p['category']:<16}] {p['pair_id']} ({p['case_id']}) "
              f"n_changes={p['n_changes']} restructuring={p['has_restructuring']}")

    out = {
        "_doc": "eval/pilot_pairs.json - v4, bounded current-state human evaluation "
                "(VALIDATION.md R39). Group A (10) = historical re-test of v3 pair_01/02/"
                "11/13/16/17/24/28/29/30, regenerated live. Group B (10) = fresh coverage. "
                "Live Datamuse (no DISABLE_DATAMUSE), unlike v3. The original v3 corpus is "
                "archived at eval/archive_v3/pilot_pairs_v3.json, not overwritten in spirit.",
        "category_counts": by_cat,
        "group_counts": by_group,
        "pairs": pairs,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {len(pairs)} pairs to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
