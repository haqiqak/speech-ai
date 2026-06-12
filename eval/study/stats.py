"""Within-subject stats for the three-condition study."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Iterable


def read_rows(path: str | Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def condition_summary(rows: Iterable[dict], metric: str = "disfluency_count") -> dict[str, dict]:
    vals: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        try:
            vals[row["condition"]].append(float(row[metric]))
        except Exception:
            continue
    out = {}
    for condition, numbers in vals.items():
        out[condition] = {
            "n": len(numbers),
            "mean": sum(numbers) / len(numbers) if numbers else None,
            "values": numbers,
        }
    return out


def friedman(rows: Iterable[dict], metric: str = "disfluency_count") -> dict:
    """Run Friedman test when scipy is available; otherwise return summaries."""

    rows = list(rows)
    summary = condition_summary(rows, metric)
    try:
        from scipy.stats import friedmanchisquare  # type: ignore
    except Exception:
        return {"test": "friedman", "available": False, "summary": summary}

    by_participant: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        try:
            by_participant[row["participant_id"]][row["condition"]] = float(row[metric])
        except Exception:
            pass
    original, generic, personal = [], [], []
    for vals in by_participant.values():
        if {"original", "generic", "personal"} <= set(vals):
            original.append(vals["original"])
            generic.append(vals["generic"])
            personal.append(vals["personal"])
    if not original:
        return {"test": "friedman", "available": True, "n": 0, "summary": summary}
    stat, p_value = friedmanchisquare(original, generic, personal)
    return {
        "test": "friedman",
        "available": True,
        "n": len(original),
        "statistic": float(stat),
        "p_value": float(p_value),
        "summary": summary,
    }
