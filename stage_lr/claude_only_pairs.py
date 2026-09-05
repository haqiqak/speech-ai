"""
stage_lr/claude_only_pairs.py -- added 2026-09-01, per direct instruction
to scale dataset growth: "a good system for using human as a test just
if that is the best way, and some by claude if too."

Not every candidate pair needs a real human's verdict to be useful data.
This module records pairs judged by Claude ALONE, generated from real
participants' declared profiles (not synthetic templates -- that's
lr1_preference_pairs.json's job, source="synthetic_profile_template").
Kept in a separate file and a separate schema from
stage_lr/ingest_real_human_pair.py's real_human_pairs.json on purpose:
that module's whole reason for existing is a hard rule that a human
verdict is NEVER logged without a same-session Claude verdict on the
same pair -- this module is the opposite case, a Claude verdict with
deliberately NO human verdict, and must never be confused with or
silently pooled into the human-comparison figures ingest_real_human_pair
computes. `source: "real_profile_claude_only"` on every record is a
second, redundant safeguard, same pattern as real_human_pairs.json's
own "source": "real_human" tag.

When to use which track (the "just if that is the best way" judgment
call, made explicit rather than left implicit):
  - A pair specifically meant to validate whether Claude tracks real
    human preference -> stage_lr/ingest_real_human_pair.py (needs a
    real participant, needs the human_test_tool.html + this session's
    quality-screening discipline before relay).
  - A pair meant just to grow the labeled dataset's volume, where the
    question isn't "does Claude match this specific person" but "is
    this a better/worse rewrite" in general -> this module. Faster,
    scales without needing a real participant's time, but never
    counts toward the human-agreement figures.

Usage:
    from stage_lr.claude_only_pairs import record_claude_only_pair, summarize
    record_claude_only_pair(
        original_sentence=..., difficulty_profile=..., flagged_word=...,
        candidate_A=..., candidate_B=..., claude_preferred=..., claude_reason=...,
        participant_label="friend_1",  # whose declared profile this came from
    )
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent.parent
CLAUDE_ONLY_PAIRS_PATH = ROOT / "stage_lr" / "data" / "claude_only_pairs.json"

Verdict = Literal["A", "B", "tie"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    if CLAUDE_ONLY_PAIRS_PATH.exists():
        return json.loads(CLAUDE_ONLY_PAIRS_PATH.read_text(encoding="utf-8"))
    return {
        "_meta": {
            "description": "Pairs generated from real participants' declared profiles, "
                            "judged by Claude alone -- no human verdict. Separate from "
                            "stage_lr/data/real_human_pairs.json (which requires both a "
                            "human and a same-session Claude verdict on every record) and "
                            "from stage_lr/data/lr1_preference_pairs.json (synthetic "
                            "profile templates, not real declared words). Never pooled "
                            "with either when computing agreement rates.",
        },
        "pairs": [],
    }


def record_claude_only_pair(
    *,
    participant_label: str,
    original_sentence: str,
    difficulty_profile: dict,
    flagged_word: str,
    candidate_A: str,
    candidate_B: str,
    claude_preferred: Verdict,
    claude_reason: str,
) -> dict:
    """Records one Claude-only-judged pair. `participant_label` marks
    whose declared profile the words came from (e.g. "friend_1") --
    never a real name, same standing rule as ingest_real_human_pair.py."""
    record = {
        "source": "real_profile_claude_only",
        "participant_label": participant_label,
        "original_sentence": original_sentence,
        "difficulty_profile": difficulty_profile,
        "flagged_word": flagged_word,
        "candidate_A": candidate_A,
        "candidate_B": candidate_B,
        "claude_preferred": claude_preferred,
        "claude_reason": claude_reason,
        "judged_at": _now(),
    }
    data = _load()
    data["pairs"].append(record)
    CLAUDE_ONLY_PAIRS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_ONLY_PAIRS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return record


def summarize() -> dict:
    """Counts only -- there is no "agreement rate" here, since there is
    no second verdict to compare against. Use
    stage_lr.ingest_real_human_pair.summarize() for the human-agreement
    figure; this is purely a dataset-size report."""
    data = _load()
    pairs = data["pairs"]
    by_participant: dict[str, int] = {}
    for p in pairs:
        by_participant[p["participant_label"]] = by_participant.get(p["participant_label"], 0) + 1
    return {"n": len(pairs), "by_participant": by_participant}
