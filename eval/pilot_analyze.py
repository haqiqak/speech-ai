"""
eval/pilot_analyze.py — Stage 7: analyze the human-evaluation pilot's
response CSV (eval/pilot_responses/P1.csv — v3 is single-participant).

Deliberately NOT eval/study/stats.py's condition_summary()/friedman() —
those assume a three-condition ("original"/"generic"/"personal") design
inherited from the pre-reformulate.py study scaffolding (see
VALIDATION.md §7); this pilot is a single-system evaluation with no
condition column at all. stats.read_rows() (plain CSV -> list[dict]) is
still directly reusable and is used below rather than reimplemented.

Two things this script is FOR, kept strictly separate per the user's own
explicit instruction — never blended into one score:
  1. What the human actually rated: meaning preservation, naturalness,
     speaking ease, preference, diagnostic tags, comments.
  2. Whether the reformulation actually resolved its declared difficulty
     — computed automatically from reformulate.py's own before/after
     flagged-word count (eval/pilot_pairs.json's profile_match field),
     never shown to or asked of the participant. Reported in its own
     section, side by side with the human numbers, so a reader can see
     both without either one masquerading as evidence for the other.

Run against real pilot data:

    python eval/pilot_analyze.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "study"))

import stats as study_stats  # eval/study/stats.py — read_rows() reused as-is

ROOT = Path(__file__).resolve().parent.parent
RESPONSES_DIR = ROOT / "eval" / "pilot_responses"
PAIRS_PATH = ROOT / "eval" / "pilot_pairs.json"
PARTICIPANT_IDS = ["P1"]


def load_responses(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for p in paths:
        if p.exists():
            rows.extend(study_stats.read_rows(p))
    return rows


def load_pair_metadata() -> dict[str, dict]:
    data = json.loads(PAIRS_PATH.read_text(encoding="utf-8"))
    return {p["pair_id"]: p for p in data["pairs"]}


def per_pair_summary(rows: list[dict]) -> list[dict]:
    by_pair: dict[str, list[dict]] = {}
    for r in rows:
        by_pair.setdefault(r["pair_id"], []).append(r)

    out = []
    for pair_id, group in by_pair.items():
        meaning = [float(r["meaning_preservation"]) for r in group]
        natural = [float(r["naturalness"]) for r in group]
        ease = [float(r["speaking_ease"]) for r in group]
        prefs = [r["preference"] for r in group]
        tags = [r["diagnostic_tag"] for r in group if r.get("diagnostic_tag")]
        comments = [r["comment"] for r in group if r.get("comment")]
        out.append({
            "pair_id": pair_id,
            "n_ratings": len(group),
            "mean_meaning_preservation": round(mean(meaning), 2),
            "mean_naturalness": round(mean(natural), 2),
            "mean_speaking_ease": round(mean(ease), 2),
            "meaning_disagreement_stdev": round(pstdev(meaning), 2) if len(meaning) > 1 else 0.0,
            "n_prefer_original": prefs.count("Original"),
            "n_prefer_reformulated": prefs.count("Reformulated"),
            "n_no_preference": prefs.count("No preference"),
            "diagnostic_tags": tags,
            "flagged_input_grammar": tags.count("Original sentence itself was confusing or ungrammatical"),
            "comments": comments,
        })
    out.sort(key=lambda r: r["pair_id"])
    return out


def merge_with_metadata(summary: list[dict], metadata: dict[str, dict]) -> list[dict]:
    merged = []
    for row in summary:
        meta = metadata.get(row["pair_id"], {})
        m = meta.get("metrics", {})
        pm = meta.get("profile_match", {})
        merged.append({
            **row,
            "case_id": meta.get("case_id"),
            "category": meta.get("category"),
            "automated_sbert_similarity": m.get("meaning_preservation"),
            "automated_edit_ratio": m.get("naturalness_edit_ratio"),
            "automated_difficulty_reduction_pct": m.get("difficulty_reduction_pct"),
            "source": "restructuring" if meta.get("has_restructuring") else "substitution",
            "n_changes": meta.get("n_changes"),
            # ── profile-match: automated, NOT a human judgment, reported separately ──
            "profile_spec": meta.get("profile_spec"),
            "triggered_by": meta.get("triggered_by"),
            "changes_made": meta.get("changes_made"),
            "difficulty_resolved": pm.get("difficulty_resolved"),
            "flagged_before": pm.get("flagged_words_before"),
            "flagged_after": pm.get("flagged_words_after"),
        })
    return merged


def flag_disagreements(merged: list[dict]) -> list[dict]:
    """Cases where the automated proxy and human judgment point in
    different directions — the specific, actionable output of this
    pilot: high automated similarity but low human meaning-preservation
    rating, or vice versa."""
    flagged = []
    for row in merged:
        sbert = row["automated_sbert_similarity"]
        if sbert is None:
            continue
        human_meaning_normalized = (row["mean_meaning_preservation"] - 1) / 4.0  # 1-5 -> 0-1
        gap = sbert - human_meaning_normalized
        if abs(gap) >= 0.25:
            flagged.append({**row, "proxy_vs_human_gap": round(gap, 3)})
    flagged.sort(key=lambda r: -abs(r["proxy_vs_human_gap"]))
    return flagged


def main() -> int:
    paths = [RESPONSES_DIR / f"{pid}.csv" for pid in PARTICIPANT_IDS]
    rows = load_responses(paths)
    if not rows:
        print("No pilot responses found yet in eval/pilot_responses/. Nothing to analyze.")
        return 0

    print(f"Loaded {len(rows)} responses from {sum(1 for p in paths if p.exists())} participant file(s).")

    summary = per_pair_summary(rows)
    metadata = load_pair_metadata()
    merged = merge_with_metadata(summary, metadata)

    print("\n--- per-pair summary ---")
    for row in merged:
        print(
            f"{row['pair_id']:<10} n={row['n_ratings']} "
            f"meaning={row['mean_meaning_preservation']} natural={row['mean_naturalness']} "
            f"ease={row['mean_speaking_ease']:+.2f} "
            f"pref(orig/reform/none)={row['n_prefer_original']}/{row['n_prefer_reformulated']}/{row['n_no_preference']} "
            f"tags={row['diagnostic_tags']}"
        )

    flagged = flag_disagreements(merged)
    print(f"\n--- proxy-vs-human disagreement (|gap| >= 0.25), {len(flagged)} pairs ---")
    for row in flagged:
        print(
            f"{row['pair_id']:<10} case={row['case_id']:<40} "
            f"sbert={row['automated_sbert_similarity']:.3f} "
            f"human_meaning={row['mean_meaning_preservation']}/5 gap={row['proxy_vs_human_gap']:+.3f}"
        )

    print("\n--- by category (global_sound / declared_word / word_pattern / multi_difficulty) ---")
    categories = sorted({r["category"] for r in merged if r["category"]})
    for cat in categories:
        sub = [r for r in merged if r["category"] == cat]
        print(
            f"{cat:<16} n_pairs={len(sub)} "
            f"mean_meaning={mean(r['mean_meaning_preservation'] for r in sub):.2f} "
            f"mean_naturalness={mean(r['mean_naturalness'] for r in sub):.2f} "
            f"mean_ease={mean(r['mean_speaking_ease'] for r in sub):+.2f}"
        )

    flagged_grammar = [r for r in merged if r["flagged_input_grammar"] > 0]
    if flagged_grammar:
        print(f"\n--- pairs where participants flagged the INPUT sentence itself as unclear ({len(flagged_grammar)}) ---")
        for row in flagged_grammar:
            print(f"{row['pair_id']:<10} case={row['case_id']:<40} flagged_by={row['flagged_input_grammar']} participant(s)")

    all_natural = [r["mean_naturalness"] for r in merged]
    all_ease = [r["mean_speaking_ease"] for r in merged]
    all_meaning = [r["mean_meaning_preservation"] for r in merged]
    print(f"\nOverall human-rated means — meaning: {mean(all_meaning):.2f}/5, "
          f"naturalness: {mean(all_natural):.2f}/5, ease: {mean(all_ease):+.2f} (-2..+2)")

    # ── SEPARATE section: profile-match, automated, never blended with the above ──
    print("\n" + "=" * 78)
    print("PROFILE MATCH — automated, NOT part of the human rating task above.")
    print("This answers a different question: did the reformulation actually avoid")
    print("its declared difficulty? Read alongside the human ratings, not combined")
    print("with them into any single score.")
    print("=" * 78)
    n_resolved = sum(1 for r in merged if r["difficulty_resolved"])
    print(f"\n{n_resolved}/{len(merged)} pairs actually resolved their declared difficulty "
          f"(flagged word count went to 0).")
    for row in merged:
        target = row["profile_spec"] or {}
        changes_desc = "; ".join(
            f"{c['original']}->{c['replacement']} ({c['source']})" for c in (row["changes_made"] or [])
        ) or "(no change recorded)"
        print(
            f"{row['pair_id']:<10} case={row['case_id']:<28} target={target} "
            f"triggered_by={row['triggered_by']} resolved={row['difficulty_resolved']} "
            f"({row['flagged_before']}->{row['flagged_after']} flagged words) | {changes_desc}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
