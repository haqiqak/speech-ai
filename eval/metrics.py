"""Automatic metrics for original/generic/personal rewrite triples."""

from __future__ import annotations

import csv
from pathlib import Path
import re
from typing import Iterable

import semantic
from profiling.profile import SpeakerDifficultyProfile
from rewrite.rewriter import DifficultyAwareRewriter


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'-]*", text or "")


def meaning_preservation(original: str, rewritten: str) -> float | None:
    return semantic.semantic_similarity(rewritten, original)


def substitution_rate(original: str, rewritten: str) -> float:
    before = _words(original)
    after = _words(rewritten)
    if not before:
        return 0.0
    changed = sum(1 for a, b in zip(before, after) if a.lower() != b.lower())
    changed += abs(len(before) - len(after))
    return round(changed / len(before), 4)


def difficulty_reduction(original: str, rewritten: str, profile: SpeakerDifficultyProfile) -> float:
    before = profile.risk_count(original)
    after = profile.risk_count(rewritten)
    if before == 0:
        return 0.0
    return round(100.0 * (before - after) / before, 2)


def evaluate_triples(
    triples: Iterable[dict],
    profile: SpeakerDifficultyProfile,
) -> list[dict]:
    rows: list[dict] = []
    for idx, row in enumerate(triples):
        original = row["original"]
        for condition in ("generic_rewrite", "personal_rewrite"):
            rewritten = row.get(condition, "")
            rows.append(
                {
                    "item_id": row.get("item_id", idx),
                    "condition": condition,
                    "meaning_preservation": meaning_preservation(original, rewritten),
                    "difficulty_reduction_pct": difficulty_reduction(original, rewritten, profile),
                    "substitution_rate": substitution_rate(original, rewritten),
                }
            )
    return rows


def lambda_tradeoff(
    text: str,
    profile: SpeakerDifficultyProfile,
    lambdas: Iterable[float],
    rewriter: DifficultyAwareRewriter | None = None,
) -> list[dict]:
    return (rewriter or DifficultyAwareRewriter()).sweep_lambda(text, profile, lambdas)


def write_csv(rows: Iterable[dict], path: str | Path) -> None:
    rows = list(rows)
    if not rows:
        return
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_tradeoff(rows: Iterable[dict], path: str | Path) -> bool:
    """Write a matplotlib trade-off figure if matplotlib is available."""

    rows = list(rows)
    if not rows:
        return False
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return False
    xs = [row["lambda"] for row in rows]
    ys = [row.get("difficulty_onset_reduction_pct", 0.0) for row in rows]
    subs = [row.get("substitution_rate", 0.0) for row in rows]
    plt.figure(figsize=(6, 4))
    plt.plot(xs, ys, marker="o", label="Difficulty reduction %")
    plt.plot(xs, subs, marker="s", label="Substitution rate")
    plt.xlabel("lambda")
    plt.legend()
    plt.tight_layout()
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out)
    plt.close()
    return True
