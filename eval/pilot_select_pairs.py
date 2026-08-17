"""
eval/pilot_select_pairs.py — Stage 7: select a curated, diverse 20-pair
pilot set for the human-evaluation pilot, from reformulate.py's ACTUAL
output on the existing corpora, not a random sample.

Pools from:
  - tests/reformulation_eval_corpus.json (Stage 6, 18 hand-built cases,
    each with its own profile)
  - tests/reformulation_ordinary_corpus.json (the escalation-rate corpus,
    42 ordinary texts x 5 realistic profiles = 210 combinations)

Both are re-run through reformulate.py fresh here — the escalation-rate
corpus's own CSV never stored full output text (only a 60-char preview),
and re-running is deterministic (verified in VALIDATION.md §6.6/§6.9) so
this recovers complete, accurate (input, output, metadata) pairs rather
than requiring either corpus script to be modified.

Excludes any case whose status is "no_change_needed" or
"could_not_safely_reformulate" — there is no reformulated candidate to
show a participant in either case. Reports the eligible-pool size before
selection, per Stage 7's brief.

Selection is deliberately diverse, not random, spanning: straightforward
single-word substitutions; different trigger types (declared word, global
sound, word-specific pattern); short and multi-sentence input; multiple-
change cases; conservative (small-edit) reformulations; and a
"challenging" bucket that includes every available restructuring-sourced
case (there were none in Stage 6's own successful cases — the escalation
path never succeeded there — so genuine restructuring examples can only
come from the ordinary-text pool) plus specific Stage 6 cases already
flagged in VALIDATION.md §6.4/§6.5 as qualitatively weak despite passing
every automated gate (the "gift...gift" redundancy case, the context-
dependent-substitution case) — included on purpose, to test whether human
raters notice what the proxy metrics missed.

Output: eval/pilot_pairs.json — the 20 selected pairs with full metadata
(never shown to participants; kept for post-hoc analysis) plus a
selection report (pool size, per-bucket counts, why each pair was picked).

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
STAGE6_CORPUS = ROOT / "tests" / "reformulation_eval_corpus.json"
ORDINARY_CORPUS = ROOT / "tests" / "reformulation_ordinary_corpus.json"
OUT_PATH = ROOT / "eval" / "pilot_pairs.json"

N_PAIRS = 20

# Stage 6 cases with documented analytical value (VALIDATION.md §6.3-6.5) —
# included whenever eligible, ahead of generic pool sampling.
PRIORITY_STAGE6_IDS = [
    "fm_ambiguous_word_noun_sense",       # known redundancy artifact ("gift...gift"), sim 0.965
    "fm_context_dependent_substitution",  # known sense-ambiguity not resolved by context
    "fm_multiple_difficult_words",        # multi-change, no interaction modeling
    "fm_ambiguous_word_verb_sense",       # companion to the noun-sense case
    "ctl_word_specific_pattern_only",     # D'-unique capability (problem_phones)
    "ctl_antonym_guard",                  # safety mechanism (null result in Stage 6 — worth a second look)
    "fm_multi_sentence_transcript",       # multi-sentence, cross-sentence context not modeled
    "ctl_multi_sentence_mixed",           # multi-sentence, mixed flagged/unflagged
    "ctl_single_clean_substitution",      # simplest possible positive case
    "ctl_informal_grammar_interaction",   # grammar-correction + reformulation interaction
]


def _build_profile(name: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__pilot_{name}__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for ph_ in spec.get("phrases", []):
        p.add_phrase(ph_, source="user_typed")
    for word, phones in spec.get("patterns", {}).items():
        p.set_word_pattern(word, phones)
    return p


def _tag(case_id: str, text: str, profile_name: str, result: dict) -> dict:
    changes = result["changes"]
    sources = {c["source"] for c in changes}
    triggers = set()
    for c in changes:
        triggers.update(c.get("triggered_by", []))
    n_sentences = len(reformulate.split_sentences(text))
    m = result["metrics"]
    return {
        "case_id": case_id,
        "profile_name": profile_name,
        "original_text": result["original_text"],
        "reformulated_text": result["reformulated_text"],
        "status": result["status"],
        "changes": changes,
        "skipped": result["skipped"],
        "metrics": m,
        "final_verification": result["final_verification"],
        "n_changes": len(changes),
        "n_sentences": n_sentences,
        "has_restructuring": "restructuring" in sources,
        "has_substitution": "substitution" in sources,
        "triggers": sorted(triggers),
        "is_priority_stage6": case_id in PRIORITY_STAGE6_IDS,
    }


def build_eligible_pool() -> list[dict]:
    pool: list[dict] = []

    stage6 = json.loads(STAGE6_CORPUS.read_text(encoding="utf-8"))
    for case in stage6["cases"]:
        profile = _build_profile(case["id"], case["profile"])
        corrected_text, _ = sanitize_input(case["text"])
        result = reformulate.reformulate(corrected_text, profile)
        if result["status"] != "reformulated":
            continue
        pool.append(_tag(case["id"], corrected_text, "stage6:" + case["id"], result))

    ordinary = json.loads(ORDINARY_CORPUS.read_text(encoding="utf-8"))
    for prof_spec in ordinary["profiles"]:
        profile = _build_profile(prof_spec["name"], prof_spec)
        for idx, text in enumerate(ordinary["texts"]):
            corrected_text, _ = sanitize_input(text)
            result = reformulate.reformulate(corrected_text, profile)
            if result["status"] != "reformulated":
                continue
            case_id = f"ordinary:{prof_spec['name']}:{idx}"
            pool.append(_tag(case_id, corrected_text, prof_spec["name"], result))

    return pool


def select_pairs(pool: list[dict], n: int = N_PAIRS) -> tuple[list[dict], dict]:
    selected: list[dict] = []
    selected_ids: set[str] = set()

    def take(item: dict) -> None:
        if item["case_id"] not in selected_ids and len(selected) < n:
            selected.append(item)
            selected_ids.add(item["case_id"])

    report = {"buckets": {}}

    # 1) Priority Stage 6 cases — documented analytical value, taken first.
    priority = [p for p in pool if p["is_priority_stage6"]]
    priority.sort(key=lambda p: PRIORITY_STAGE6_IDS.index(p["case_id"]))
    for item in priority:
        take(item)
    report["buckets"]["priority_stage6"] = len([p for p in selected if p["is_priority_stage6"]])

    # 2) Every available restructuring-sourced case — Stage 6 itself has
    # zero successful ones, so this bucket can only be filled from the
    # ordinary-text pool. These are the "challenging" edits.
    restructuring = [p for p in pool if p["has_restructuring"]]
    restructuring.sort(key=lambda p: -(p["metrics"]["meaning_preservation"] or 0))
    before = len(selected)
    for item in restructuring:
        if len(selected) - before >= 4:
            break
        take(item)
    report["buckets"]["restructuring_examples"] = len(selected) - before

    # 3) Multi-change substitution cases not already selected.
    multi_change = [p for p in pool if p["n_changes"] >= 2 and not p["has_restructuring"]]
    multi_change.sort(key=lambda p: -p["n_changes"])
    before = len(selected)
    for item in multi_change:
        if len(selected) - before >= 3:
            break
        take(item)
    report["buckets"]["multi_change"] = len(selected) - before

    # 4) Multi-sentence inputs not already selected.
    multi_sentence = [p for p in pool if p["n_sentences"] >= 2]
    before = len(selected)
    for item in multi_sentence:
        if len(selected) - before >= 2:
            break
        take(item)
    report["buckets"]["multi_sentence"] = len(selected) - before

    # 5) Coverage across trigger types (declared_word / global_sound /
    # word_specific_pattern) for whichever aren't yet represented.
    covered_triggers = set()
    for item in selected:
        covered_triggers.update(item["triggers"])
    for trigger in ("declared_word", "global_sound", "word_specific_pattern"):
        if trigger in covered_triggers or len(selected) >= n:
            continue
        candidates = [p for p in pool if trigger in p["triggers"] and p["n_changes"] == 1]
        candidates.sort(key=lambda p: p["metrics"]["naturalness_edit_ratio"])
        for item in candidates:
            if item["case_id"] not in selected_ids:
                take(item)
                break
    report["buckets"]["trigger_coverage_fill"] = "see triggers_covered"

    # 6) Fill remaining slots with straightforward, conservative, single-
    # substitution cases — the ordinary/common case a pilot must include
    # plenty of, not just edge cases.
    straightforward = [
        p for p in pool
        if p["n_changes"] == 1 and p["has_substitution"] and not p["has_restructuring"]
    ]
    straightforward.sort(key=lambda p: p["metrics"]["naturalness_edit_ratio"])
    before = len(selected)
    for item in straightforward:
        if len(selected) >= n:
            break
        take(item)
    report["buckets"]["straightforward_fill"] = len(selected) - before

    # 7) If still short, take anything eligible left.
    before = len(selected)
    if len(selected) < n:
        remaining = [p for p in pool if p["case_id"] not in selected_ids]
        for item in remaining:
            if len(selected) >= n:
                break
            take(item)
    report["buckets"]["generic_fill"] = len(selected) - before

    report["triggers_covered"] = sorted(covered_triggers | {t for it in selected for t in it["triggers"]})
    report["restructuring_count"] = sum(1 for p in selected if p["has_restructuring"])
    report["multi_change_count"] = sum(1 for p in selected if p["n_changes"] >= 2)
    report["multi_sentence_count"] = sum(1 for p in selected if p["n_sentences"] >= 2)
    report["priority_stage6_count"] = sum(1 for p in selected if p["is_priority_stage6"])
    return selected, report


def main() -> int:
    sbert_ok = semantic.load_sbert()
    print(f"SBERT loaded={sbert_ok}")

    pool = build_eligible_pool()
    print(f"Eligible pool (status == 'reformulated'): {len(pool)} pairs")

    selected, report = select_pairs(pool, N_PAIRS)
    print(f"Selected: {len(selected)} pairs")
    print("Bucket report:", json.dumps(report, indent=2))

    for i, item in enumerate(selected):
        item["pair_id"] = f"pair_{i+1:02d}"

    out = {
        "_doc": "eval/pilot_pairs.json - Stage 7 human-evaluation pilot set. "
                "Full metadata here is for post-hoc analysis only and must "
                "never be shown to participants.",
        "n_eligible_pool": len(pool),
        "selection_report": report,
        "pairs": selected,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {len(selected)} pairs to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
