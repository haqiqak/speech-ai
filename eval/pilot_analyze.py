"""
eval/pilot_analyze.py — Stage 7: analyze the human-evaluation pilot's
response CSVs (eval/pilot_responses/P1.csv .. P4.csv).

Deliberately NOT eval/study/stats.py's condition_summary()/friedman() —
those assume a three-condition ("original"/"generic"/"personal") design
inherited from the pre-reformulate.py study scaffolding (see
VALIDATION.md §7); this pilot is a single-system evaluation with no
condition column at all. stats.read_rows() (plain CSV -> list[dict]) is
still directly reusable and is used below rather than reimplemented.

The one thing this script is FOR, beyond simple descriptive summaries:
merging each pair's human ratings against the automated metrics already
computed for it in eval/pilot_pairs.json (SBERT similarity, naturalness
edit-ratio, trigger type, restructuring vs. substitution) — this is what
turns "people liked pair 14 less" into "the proxy metrics didn't flag
pair 14 as risky, but a real reader did," which is the actual point of
running this pilot at all.

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
PARTICIPANT_IDS = ["P1", "P2", "P3", "P4"]


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
        })
    out.sort(key=lambda r: r["pair_id"])
    return out


def merge_with_metadata(summary: list[dict], metadata: dict[str, dict]) -> list[dict]:
    merged = []
    for row in summary:
        meta = metadata.get(row["pair_id"], {})
        m = meta.get("metrics", {})
        merged.append({
            **row,
            "case_id": meta.get("case_id"),
            "automated_sbert_similarity": m.get("meaning_preservation"),
            "automated_edit_ratio": m.get("naturalness_edit_ratio"),
            "automated_difficulty_reduction_pct": m.get("difficulty_reduction_pct"),
            "source": "restructuring" if meta.get("has_restructuring") else "substitution",
            "n_changes": meta.get("n_changes"),
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

    all_natural = [r["mean_naturalness"] for r in merged]
    all_ease = [r["mean_speaking_ease"] for r in merged]
    all_meaning = [r["mean_meaning_preservation"] for r in merged]
    print(f"\nOverall means — meaning: {mean(all_meaning):.2f}/5, "
          f"naturalness: {mean(all_natural):.2f}/5, ease: {mean(all_ease):+.2f} (-2..+2)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
