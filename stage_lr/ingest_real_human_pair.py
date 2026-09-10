"""
stage_lr/ingest_real_human_pair.py — the ONLY sanctioned way to record a
real friend's judgment on a Stage LR candidate pair (path (b)). Exists
to enforce one hard rule, structurally, not just by convention:

  A real-human verdict is NEVER logged without a Claude verdict on the
  EXACT SAME pair, obtained in the SAME session. Never "log the human
  answer now, run judge_pairs.py on it later." This project has
  concrete precedent for what goes wrong with two-pass data that turns
  out not to line up (e.g. Phase 9B/9C's own instability, R28's
  test-set leakage caught only by re-checking) — different pipeline
  state, a changed prompt, a changed model version between passes can
  silently desynchronize two verdicts that were supposed to be
  directly comparable. `record_real_human_pair()` below makes the
  desynchronized path impossible to reach: both `human_preferred` and
  `claude_preferred` are required, non-optional arguments with no
  default — there is no code path in this module that writes a record
  with only one of them.

Real-human pairs are stored SEPARATELY from the 68
`source=synthetic_profile_template` pairs in `lr1_preference_pairs.json`
— a different file (`real_human_pairs.json`), not just a different
field — per direct instruction: they answer a different question (do
real people, not just Claude, agree with a candidate ranking) and must
not be silently pooled with the template-based pairs when computing
agreement rates later. Every record here still also carries
`source: "real_human"` as a second, redundant safeguard.

Usage, once a friend's profile and their raw pick on a pair are in
hand:
  1. Build the SAME judge prompt for that pair via
     `stage_lr.judge_pairs.build_judge_prompt([pair])` and get the
     Claude verdict for it via a general-purpose Claude call, in the
     same session as receiving the human's answer — not deferred.
  2. Call `record_real_human_pair(...)` with both verdicts. It appends
     to `stage_lr/data/real_human_pairs.json` and returns the combined
     record.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent.parent
REAL_HUMAN_PAIRS_PATH = ROOT / "stage_lr" / "data" / "real_human_pairs.json"

Verdict = Literal["A", "B", "tie"]
Distinguishability = Literal["distinguishable", "near_synonym"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    if REAL_HUMAN_PAIRS_PATH.exists():
        return json.loads(REAL_HUMAN_PAIRS_PATH.read_text(encoding="utf-8"))
    return {
        "_meta": {
            "description": "Real-human-judged Stage LR candidate pairs (data path (b)). "
                            "Kept SEPARATE from stage_lr/data/lr1_preference_pairs.json's "
                            "68 source=synthetic_profile_template pairs — different question, "
                            "must not be silently pooled when computing agreement rates.",
            "invariant": "Every record here has BOTH a human_preferred and a claude_preferred "
                          "verdict, obtained on the exact same pair in the same ingestion "
                          "session — never a human verdict logged alone. Enforced by "
                          "record_real_human_pair()'s required arguments, not just documented.",
        },
        "pairs": [],
    }


def record_real_human_pair(
    *,
    participant_label: str,
    original_sentence: str,
    difficulty_profile: dict,
    flagged_word: str,
    candidate_A: str,
    candidate_B: str,
    human_preferred: Verdict,
    claude_preferred: Verdict,
    claude_reason: str,
    human_reason: str | None = None,
    pair_distinguishability: Distinguishability = "distinguishable",
) -> dict:
    """Records one real-human-judged pair. `human_preferred` and
    `claude_preferred` are BOTH required — there is no way to call this
    function with only one verdict. `human_reason` is optional (the
    friend-facing ask deliberately doesn't require an explanation, per
    LEARNED_REFORMULATION_RESEARCH.md's "concrete, minimal ask" — a bare
    pick is enough); `claude_reason` is not optional, since Claude is
    always asked for one.

    `pair_distinguishability` defaults to "distinguishable" (ordinary
    case: the two candidates have some real, checkable quality gap).
    Pass "near_synonym" for a pair chosen mainly for ease of generation
    where both candidates are close enough that a tie is a defensible
    verdict (`DECISION_LOG.md` 2026-09-01-G) — kept in the record
    (never deleted; real, honestly-collected data isn't discarded
    because an aggregate number moved) but excludable from
    conclusion-drawing figures via `summarize(exclude_near_synonym=True)`.

    `participant_label` is whatever non-identifying label the user
    wants for this friend (e.g. "friend_1") — never a real name, per
    this project's own standing caution about committing real personal
    data (`ROADMAP.md` R0)."""
    record = {
        "source": "real_human",
        "participant_label": participant_label,
        "original_sentence": original_sentence,
        "difficulty_profile": difficulty_profile,
        "flagged_word": flagged_word,
        "candidate_A": candidate_A,
        "candidate_B": candidate_B,
        "human_preferred": human_preferred,
        "human_reason": human_reason,
        "claude_preferred": claude_preferred,
        "claude_reason": claude_reason,
        "agree": human_preferred == claude_preferred,
        "pair_distinguishability": pair_distinguishability,
        "judged_together_at": _now(),
    }

    data = _load()
    data["pairs"].append(record)
    REAL_HUMAN_PAIRS_PATH.parent.mkdir(parents=True, exist_ok=True)
    REAL_HUMAN_PAIRS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return record


def summarize(*, exclude_near_synonym: bool = False) -> dict:
    """Real, human-vs-Claude agreement rate on whatever's been
    collected so far — separate from, never combined with, the 68
    synthetic-template pairs' own agreement figures.

    `exclude_near_synonym=True` drops any pair recorded with
    `pair_distinguishability="near_synonym"` (2026-09-01-G) before
    computing the rate — for conclusion-drawing reads. The default
    (False) reports every recorded pair, near-synonym batches included;
    nothing is ever deleted from the underlying file either way. A
    record with no `pair_distinguishability` field (pre-2026-09-01-G)
    is treated as "distinguishable", its implicit prior meaning."""
    data = _load()
    pairs = data["pairs"]
    if exclude_near_synonym:
        pairs = [p for p in pairs if p.get("pair_distinguishability", "distinguishable") != "near_synonym"]
    if not pairs:
        return {"n": 0, "agree": 0, "rate": None}
    agree = sum(1 for p in pairs if p["agree"])
    return {"n": len(pairs), "agree": agree, "rate": agree / len(pairs)}
