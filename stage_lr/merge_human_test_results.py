"""
stage_lr/merge_human_test_results.py -- completes the loop opened by
human_test_tool.html. Added 2026-09-01 to replace one-pair-at-a-time
chat relay (the actual bottleneck) with: harvest -> tool (participant
judges a whole batch in one sitting) -> this script -> one batched
Claude judgment call -> record_real_human_pair() for every pair.

Usage:
    from stage_lr.merge_human_test_results import load_merged, to_judge_payload

    merged = load_merged(
        "stage_lr/data/private/real_profile_2_pairs_for_review.json",
        "stage_lr/data/private/real_profile_2_human_test_results.json",
    )
    # merged: list of dicts, one per pair, each with the pair's own
    # fields (review_id, sentence_with_A/B, changed_word, candidate_A/B)
    # PLUS original_sentence (reconstructed) and human_preferred.

    payload = to_judge_payload(merged, difficulty_profile={...})
    # -> exact input shape for stage_lr.judge_pairs.build_judge_prompt();
    # send that prompt via the Agent tool in the same session, same as
    # every prior round -- this module does not call any model itself.

    # After the judge response comes back:
    from stage_lr.merge_human_test_results import log_all
    log_all(merged, judge_pairs.parse_judge_response(response_text),
             participant_label="friend_1", difficulty_profile={...})
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from stage_lr.ingest_real_human_pair import record_real_human_pair


def _reconstruct_original_sentence(pair: dict) -> str:
    """sentence_with_A has candidate_A in place of the original word;
    swapping it back for candidate_A's own text recovers the
    pre-substitution sentence -- same reconstruction done by hand every
    prior round this session. Falls back to sentence_with_A unchanged
    if candidate_A's exact surface form isn't found (e.g. it was
    inflected), which only affects the cosmetic "original_sentence"
    field shown to the judge, not the actual candidates being compared.
    """
    sentence = pair["sentence_with_A"]
    candidate = pair["candidate_A"]
    pattern = re.compile(re.escape(candidate), re.IGNORECASE)
    match = pattern.search(sentence)
    if not match:
        return sentence
    return sentence[:match.start()] + pair["changed_word"] + sentence[match.end():]


def load_merged(pairs_for_review_path: str | Path, human_results_path: str | Path) -> list[dict]:
    """Loads a *_pairs_for_review.json (harvest_real_profile.py's
    output) and a human_test_tool.html results export, joins them on
    review_id. Raises if any pair has no matching human answer or an
    unrecognized value -- never silently drops a pair."""
    pairs = json.loads(Path(pairs_for_review_path).read_text(encoding="utf-8"))
    results_raw = json.loads(Path(human_results_path).read_text(encoding="utf-8"))
    results = results_raw["results"] if isinstance(results_raw, dict) else results_raw
    by_id = {r["review_id"]: r["human_preferred"] for r in results}

    merged = []
    for p in pairs:
        rid = p["review_id"]
        if rid not in by_id:
            raise ValueError(f"review_id {rid} has no human answer in {human_results_path}")
        human_preferred = by_id[rid]
        if human_preferred not in ("A", "B", "tie"):
            raise ValueError(f"review_id {rid} has an invalid human_preferred: {human_preferred!r}")
        row = dict(p)
        row["human_preferred"] = human_preferred
        row["original_sentence"] = _reconstruct_original_sentence(p)
        merged.append(row)
    return merged


def to_judge_payload(merged: list[dict], difficulty_profile: dict) -> list[dict]:
    """Builds the exact input shape stage_lr.judge_pairs.build_judge_prompt()
    expects -- send the resulting prompt via a fresh, blind Agent call,
    same discipline as every prior round (never told the human's answer)."""
    return [
        {
            "id": row["review_id"],
            "original_sentence": row["original_sentence"],
            "difficulty_profile": difficulty_profile,
            "flagged_word": row["changed_word"],
            "candidate_A": row["candidate_A"],
            "candidate_B": row["candidate_B"],
        }
        for row in merged
    ]


def log_all(merged: list[dict], claude_verdicts: dict[int, dict], *,
            participant_label: str, difficulty_profile: dict) -> dict:
    """Calls record_real_human_pair() once per pair using the merged
    human answers and the corresponding Claude verdicts (id -> {preferred, reason}
    from judge_pairs.parse_judge_response()). Returns
    ingest_real_human_pair.summarize()'s result after logging everything.
    Raises if a pair has no matching Claude verdict -- never logs a
    human-only record, per ingest_real_human_pair.py's own hard rule."""
    for row in merged:
        rid = row["review_id"]
        if rid not in claude_verdicts:
            raise ValueError(f"review_id {rid} has no Claude verdict -- refusing to log a human-only record")
        verdict = claude_verdicts[rid]
        record_real_human_pair(
            participant_label=participant_label,
            original_sentence=row["original_sentence"],
            difficulty_profile=difficulty_profile,
            flagged_word=row["changed_word"],
            candidate_A=row["candidate_A"],
            candidate_B=row["candidate_B"],
            human_preferred=row["human_preferred"],
            claude_preferred=verdict["preferred"],
            claude_reason=verdict["reason"],
        )
    from stage_lr.ingest_real_human_pair import summarize
    return summarize()
