"""CSV schema helpers for blinded coding and self-report collection."""

from __future__ import annotations

import csv
from pathlib import Path

FIELDS = [
    "participant_id",
    "passage_id",
    "condition",
    "reader_order",
    "coder_id",
    "disfluency_count",
    "ease_likert_1_7",
    "confidence_likert_1_7",
    "forced_choice_preference",
    "notes",
]


def init_collection_csv(path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=FIELDS).writeheader()
