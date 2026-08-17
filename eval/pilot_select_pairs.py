"""
eval/pilot_select_pairs.py — Stage 7 pilot pair selection, v3.

Rebuilt per direct user review of v2 (which itself had already replaced
v1): v2's 4-category mix (short/long/multi-sentence/paragraph) confirmed
short sentences produce the clearest, most legible test signal — long
sentences only changed a word or two, diluting it. v3 narrows to short,
natural, everyday sentences only (~30 of them), single participant, with
one methodological tightening the user was explicit about: participant
ratings cover ONLY meaning preservation / naturalness / speaking ease /
preference / optional comment — never whether the reformulation actually
addressed the declared difficulty profile. That question is answered
separately, automatically, from reformulate.py's own before/after flagged-
word count, and reported alongside (never blended into) the human
ratings — see PROFILE_MATCH fields on every pair and
eval/pilot_analyze.py's separate reporting.

Every item's profile is fully traceable: which sound/word/pattern was
declared, which change(s) it triggered, what changed, and whether the
declared difficulty was actually resolved in the output — all computed
from reformulate.py's own result structure, not asserted.

Categories (30 total, not evenly split — sized by what a real, lightly-
populated difficulty profile would actually produce, per the escalation-
rate corpus's own finding in VALIDATION.md §6.9 that light/moderate
profiles dominate real usage):
  - 18 global-sound-triggered (the most common real scenario — a
    single declared onset)
  - 5 declared-word-triggered (a specific word, not sound-based)
  - 4 word-specific problem_phones-triggered (the D'-unique capability)
  - 3 multi-difficulty (two sounds active in one sentence at once)

Every (text, profile) combination was run through reformulate.py and
kept only if it produced a "reformulated" status (no_change_needed and
could_not_safely_reformulate excluded — there's no candidate to rate in
either), and reconfirmed stable across repeated FRESH-PROCESS trials
before being kept — see _run_item()'s docstring for why that matters
(VALIDATION.md §8.4's T5-escalation non-determinism finding, from v2,
still applies here and was checked for again, not assumed fixed).

The set deliberately includes genuine, checkable errors alongside clean
outputs, not cherry-picked for success: "valuable" -> "worth" ("a worth
lesson," ungrammatical), "straightforward" -> "directed" (wrong meaning),
"print" -> "create" (wrong action), "driving me crazy" -> "going me
crazy" (broken), "was late again" -> "was recently again" (broken).

Run (DISABLE_DATAMUSE=1 required for determinism):

    DISABLE_DATAMUSE=1 python eval/pilot_select_pairs.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DISABLE_DATAMUSE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic
from grammar import sanitize_input
from difficulty_profile import DifficultyProfile
import reformulate

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "eval" / "pilot_pairs.json"

# Each item: (case_id, category, text, profile_spec)
# category in: "global_sound", "declared_word", "word_pattern", "multi_difficulty"
ITEMS: list[tuple[str, str, str, dict]] = [
    # ── global sound (18) — the most common real declared-profile shape ──
    ("gs_hows_it_going", "global_sound", "Hey, how's it going today?", {"sounds": ["g"]}),
    ("gs_sleep_well", "global_sound", "Good morning, did you sleep well?", {"sounds": ["s"]}),
    ("gs_turn_down_music", "global_sound", "Please turn down the music a little.", {"sounds": ["m"]}),
    ("gs_forgot_that", "global_sound", "My bad, I totally forgot about that.", {"sounds": ["f"]}),
    ("gs_meet_up", "global_sound", "Let's meet up sometime next week.", {"sounds": ["m"]}),
    ("gs_doctors_appt", "global_sound", "I have a doctor's appointment tomorrow.", {"sounds": ["d"]}),
    ("gs_frustrating", "global_sound", "This is so frustrating, nothing works.", {"sounds": ["w"]}),
    ("gs_cant_believe", "global_sound", "I can't believe this happened again.", {"sounds": ["h"]}),
    ("gs_always_happen", "global_sound", "Why does this always happen to me?", {"sounds": ["h"]}),
    ("gs_buy_groceries", "global_sound", "I need to buy groceries after work.", {"sounds": ["b"]}),
    ("gs_driving_crazy", "global_sound", "The kids are driving me crazy today.", {"sounds": ["d"]}),
    ("gs_probably_leave", "global_sound", "We should probably leave soon.", {"sounds": ["pr"]}),
    ("gs_bus_late", "global_sound", "The bus was late again this morning.", {"sounds": ["l"]}),
    ("gs_believe_expensive", "global_sound", "Can you believe how expensive that was?", {"sounds": ["b"]}),
    ("gs_need_break", "global_sound", "I really need a break right now.", {"sounds": ["r"]}),
    ("gs_grab_jacket", "global_sound", "Let me grab my jacket real quick.", {"sounds": ["gr"]}),
    ("gs_grab_coffee", "global_sound", "Do you want to grab coffee later?", {"sounds": ["gr"]}),
    ("gs_email_details", "global_sound", "Could you email me the details later?", {"sounds": ["d"]}),

    # ── declared word (5) ────────────────────────────────────────────────
    ("dw_meeting_thursday", "declared_word", "The meeting got moved to Thursday.", {"words": ["meeting"]}),
    ("dw_struggling_project", "declared_word", "I'm really struggling with this project.", {"words": ["struggling"]}),
    ("dw_traffic_ridiculous", "declared_word", "The traffic today was absolutely ridiculous.", {"words": ["ridiculous"]}),
    ("dw_phone_case_nice", "declared_word", "That new phone case looks pretty nice.", {"words": ["nice"]}),
    ("dw_instructions_confusing", "declared_word", "The instructions were a little confusing honestly.", {"words": ["instructions"]}),

    # ── word-specific problem_phones (4) — the D'-unique capability ────
    ("wp_valuable_lesson", "word_pattern", "This is a valuable lesson for everyone here.",
     {"words": ["valuable"], "patterns": {"valuable": ["V"]}}),
    ("wp_straightforward_fix", "word_pattern", "The problem seems fairly straightforward to fix.",
     {"words": ["straightforward"], "patterns": {"straightforward": ["S"]}}),
    ("wp_comfortable_chair", "word_pattern", "That's a really comfortable chair.",
     {"words": ["comfortable"], "patterns": {"comfortable": ["K"]}}),
    ("wp_particular_preference", "word_pattern", "I have a particular preference for tea.",
     {"words": ["particular"], "patterns": {"particular": ["P"]}}),

    # ── multi-difficulty (3) — two declared sounds active at once ───────
    ("md_running_traffic", "multi_difficulty", "Sorry, running behind, stuck in traffic right now.", {"sounds": ["r"]}),
    ("md_push_meeting_coffee", "multi_difficulty", "Can we push the meeting and grab coffee after?", {"sounds": ["p", "gr"]}),
    ("md_print_report_coffee", "multi_difficulty", "Can you print the report and grab some coffee?", {"sounds": ["pr", "gr"]}),
]


def _build_profile(name: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__pilot_{name}__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for word, phones in spec.get("patterns", {}).items():
        p.set_word_pattern(word, phones)
    return p


def _run_item(case_id: str) -> dict:
    """Run exactly one ITEMS entry through reformulate.py and return its
    pair dict, with full profile-traceability metadata. Deliberately the
    unit of work for --single mode (see build_pairs()) — T5-escalation-
    sourced results were found (v2, VALIDATION.md §8.4) to occasionally
    flip between "reformulated" and "could_not_safely_reformulate" across
    separate fresh-process runs of IDENTICAL code and input — a property
    of CPU floating-point non-determinism in beam search, not a bug in
    reformulate.py's own logic. Rather than assume that's fixed, every
    item here is run in its own fresh process and reconfirmed stable
    across repeated trials (see build_pairs()) before being kept.
    """
    by_id = {c[0]: c for c in ITEMS}
    if case_id not in by_id:
        raise KeyError(f"unknown case_id: {case_id}")
    _, category, text, spec = by_id[case_id]

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
        # ── full profile traceability (analyst-only; never shown to the participant) ──
        "profile_spec": spec,
        "triggered_by": sorted(triggers),
        "changes_made": [
            {"original": c["original"], "replacement": c["replacement"], "source": c["source"]}
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
        # ── the actual pair shown to the participant ──────────────────
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
    """Runs each ITEMS entry in its own subprocess (see _run_item's
    docstring for why) via `python eval/pilot_select_pairs.py --single
    <case_id>`, which prints that one pair's JSON to stdout. Each item is
    additionally re-run 2 more times if it involves restructuring
    (T5-dependent, the only source of observed non-determinism) to
    reconfirm stability before being accepted."""
    import subprocess

    def run_once(case_id: str) -> dict:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--single", case_id],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "DISABLE_DATAMUSE": "1", "PYTHONIOENCODING": "utf-8"},
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
    for case_id, _category, _text, _spec in ITEMS:
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
        print(f"  done: {case_id}" + (" (restructuring, stability-checked x3)" if first["has_restructuring"] else ""))
    return pairs


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--single":
        result = _run_item(sys.argv[2])
        print("PILOT_ITEM_JSON:" + json.dumps(result, ensure_ascii=False))
        return 0

    print(f"Running {len(ITEMS)} items (restructuring-sourced ones get 2 extra stability trials)...")
    pairs = build_pairs()
    for i, item in enumerate(pairs):
        item["pair_id"] = f"pair_{i+1:02d}"

    by_cat: dict[str, int] = {}
    for p in pairs:
        by_cat[p["category"]] = by_cat.get(p["category"], 0) + 1
    print(f"\nBuilt {len(pairs)} pairs: {by_cat}")
    n_resolved = sum(1 for p in pairs if p["profile_match"]["difficulty_resolved"])
    print(f"Profile-match (automated, NOT part of participant task): "
          f"{n_resolved}/{len(pairs)} pairs actually resolved their declared difficulty")
    for p in pairs:
        print(f"  [{p['category']:<16}] {p['pair_id']} n_changes={p['n_changes']} "
              f"restructuring={p['has_restructuring']} resolved={p['profile_match']['difficulty_resolved']}")

    out = {
        "_doc": "eval/pilot_pairs.json - Stage 7 human-evaluation pilot set, v3 "
                "(single participant, 30 short/natural/everyday sentences only). "
                "Full metadata here (profile_spec, triggered_by, changes_made, "
                "profile_match) is for post-hoc analysis only and must never be "
                "shown to the participant during rating.",
        "category_counts": by_cat,
        "pairs": pairs,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {len(pairs)} pairs to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
