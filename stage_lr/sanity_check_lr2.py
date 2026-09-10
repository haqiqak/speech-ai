"""
stage_lr/sanity_check_lr2.py — uses the 58 judged pairs in
lr1_preference_pairs.json to sanity-check stage_lr/features.py: run
each pair's two candidates through score_candidate() and see whether
the resulting meaning+naturalness comparison agrees with the human/
Claude judgment. Cheap, immediate, done while the pair count is small
enough to inspect every disagreement by eye.

    DISABLE_DATAMUSE=1 python stage_lr/sanity_check_lr2.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DISABLE_DATAMUSE", "1")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import paths  # noqa: F401,E402
from difficulty_profile import DifficultyProfile  # noqa: E402
from stage_lr.features import score_candidate  # noqa: E402

PAIRS_PATH = ROOT / "stage_lr" / "data" / "lr1_preference_pairs.json"
LOG1_PATH = ROOT / "stage_lr" / "data" / "lr1_candidate_generation_log.json"
LOG2_PATH = ROOT / "stage_lr" / "data" / "lr1_candidate_generation_log_r10.json"
OUT_PATH = ROOT / "stage_lr" / "data" / "lr2_sanity_check_results.json"


def build_profile(spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name="__lr2_sanity__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for ph in spec.get("phrases", []):
        p.add_phrase(ph, source="user_typed")
    return p


def load_sentence_lookup() -> dict[str, dict]:
    lookup = {}
    for path in (LOG1_PATH, LOG2_PATH):
        d = json.loads(path.read_text(encoding="utf-8"))
        for r in d["results"]:
            if r.get("outcome") == "second_candidate_found":
                lookup[r["uid"]] = r
    return lookup


GRAMMAR_PENALTY_PER_ISSUE = 0.2  # provisional, inspectable — not a tuned/validated weight
CONTRADICTION_PENALTY = 0.3  # provisional, inspectable — not a tuned/validated weight


def combined_score(s) -> float | None:
    """Simple, inspectable combination for this sanity check only — NOT
    a proposed ranking formula. meaning = average of available signals
    (SBERT 0-1 scaled to match MeaningBERT's 0-100 by *100, or vice
    versa -- here both rescaled to 0-1); naturalness added directly
    (already 0-1); phoneme_difficulty subtracted as a large penalty
    (should be ~0 for both sides here, since both candidates already
    passed the live pipeline's own phoneme gate by construction);
    grammar_issue_count subtracted at GRAMMAR_PENALTY_PER_ISSUE per
    issue (4th term, 2026-08-30); logical_contradiction subtracted at
    a flat CONTRADICTION_PENALTY when True (5th term, 2026-08-30).
    Both new penalties are provisional weights sized to be noticeable
    against the typical meaning-score gap between two candidates that
    already cleared the SBERT floor (often 0.02-0.1) — not fitted or
    validated against this data."""
    parts = []
    if s.meaning_sbert is not None:
        parts.append(s.meaning_sbert)
    if s.meaning_meaningbert is not None:
        parts.append(s.meaning_meaningbert / 100.0)
    if not parts:
        return None
    meaning = sum(parts) / len(parts)
    naturalness = s.naturalness_contextual_fit if s.naturalness_contextual_fit is not None else 0.0
    grammar_penalty = (s.grammar_issue_count or 0) * GRAMMAR_PENALTY_PER_ISSUE
    contradiction_penalty = CONTRADICTION_PENALTY if s.logical_contradiction else 0.0
    return meaning + naturalness - (s.phoneme_difficulty * 10.0) - grammar_penalty - contradiction_penalty


def main() -> None:
    pairs = json.loads(PAIRS_PATH.read_text(encoding="utf-8"))["pairs"]
    sentence_lookup = load_sentence_lookup()

    rows = []
    agree = disagree = no_signal = 0

    for pair in pairs:
        uid = pair["source_uids"][0]
        rec = sentence_lookup.get(uid)
        if rec is None:
            no_signal += 1
            rows.append({**pair, "lr2_outcome": "source_record_not_found"})
            continue

        profile = build_profile(pair["difficulty_profile"])
        score_a = score_candidate(
            pair["original_sentence"], rec["candidate_a_sentence"], pair["candidate_A"],
            profile, source="substitution",
        )
        score_b = score_candidate(
            pair["original_sentence"], rec["candidate_b_sentence"], pair["candidate_B"],
            profile, source="substitution",
        )

        ca, cb = combined_score(score_a), combined_score(score_b)
        if ca is None or cb is None:
            no_signal += 1
            rows.append({**pair, "lr2_outcome": "no_model_signal",
                         "score_A": ca, "score_B": cb})
            continue

        diff = ca - cb
        # Small threshold so near-equal scores map to "tie" rather than
        # noise deciding a fake winner.
        if abs(diff) < 0.01:
            lr2_pref = "tie"
        else:
            lr2_pref = "A" if diff > 0 else "B"

        matches = (lr2_pref == pair["preferred"])
        if matches:
            agree += 1
        else:
            disagree += 1

        rows.append({
            **pair,
            "score_A": round(ca, 4), "score_B": round(cb, 4),
            "lr2_preferred": lr2_pref, "agrees_with_judgment": matches,
        })
        print(f"{'AGREE ' if matches else 'DISAGREE'} human={pair['preferred']:<4} "
              f"lr2={lr2_pref:<4} A={ca:.3f} B={cb:.3f}  {pair['candidate_A']} vs {pair['candidate_B']}", flush=True)

    OUT_PATH.write_text(json.dumps({
        "counts": {"agree": agree, "disagree": disagree, "no_signal": no_signal, "total": len(pairs)},
        "rows": rows,
    }, indent=2), encoding="utf-8")

    print()
    print(f"=== agree: {agree}  disagree: {disagree}  no_signal: {no_signal}  total: {len(pairs)} ===")


if __name__ == "__main__":
    main()
