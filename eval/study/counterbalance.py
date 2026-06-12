"""Generate counterbalanced three-condition passage sets."""

from __future__ import annotations

import csv
from itertools import permutations
from pathlib import Path
from typing import Iterable

CONDITIONS = ("original", "generic", "personal")


def assign_conditions(participant_ids: Iterable[str], passage_ids: Iterable[str]) -> list[dict]:
    orders = list(permutations(CONDITIONS))
    rows: list[dict] = []
    passages = list(passage_ids)
    for p_idx, participant in enumerate(participant_ids):
        order = orders[p_idx % len(orders)]
        for i, passage in enumerate(passages):
            rows.append(
                {
                    "participant_id": participant,
                    "passage_id": passage,
                    "condition": order[i % len(order)],
                    "order": i + 1,
                }
            )
    return rows


def write_schedule(rows: Iterable[dict], path: str | Path) -> None:
    rows = list(rows)
    if not rows:
        return
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
