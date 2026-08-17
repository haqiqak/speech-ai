"""
eval/idiom_guard_recheck.py — re-run the FROZEN v3 pilot corpus
(eval/pilot_pairs.json) through the current reformulate.py, after the
idiom/fixed-expression guard (REFORMULATION_PROBLEM_MAP.md SS5 item 1,
semantic.py's IDIOM_PHRASES/IDIOM_PHRASE_PATTERNS), and compare each
pair's NEW output against what P1 actually rated (VALIDATION.md
SS9.6-9.9), for the pairs that finding identified as idiom/fixed-
expression failures or the "right now" word-sense bug.

This does NOT overwrite eval/pilot_pairs.json or eval/pilot_responses/ —
those stay frozen exactly as VALIDATION.md SS8.4/SS9.4 require (the
record of what a real participant actually rated must never be silently
regenerated). This is a read-only diagnostic re-run, same spirit as the
R17 follow-up in VALIDATION.md SS6.8.

    DISABLE_DATAMUSE=1 python eval/idiom_guard_recheck.py
"""
import json
import os
import sys

os.environ.setdefault("DISABLE_DATAMUSE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic
import reformulate
from difficulty_profile import DifficultyProfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAIRS_PATH = os.path.join(ROOT, "eval", "pilot_pairs.json")

# The pairs VALIDATION.md SS9.7/SS9.9 identified as an idiom break or the
# "right now" word-sense bug specifically — the guard's actual targets.
# pair_29 ("push"->"force"/"grab"->"catch", a word-choice/frequency-bias
# issue) and pair_30 ("print"->"create", a wrong-action substitution) were
# also on SS9.7's high-SBERT-vs-human-gap list but are NOT idiom breaks —
# confirmed by this script itself on first run (they came back unchanged,
# correctly: this guard was never going to touch them, and it doesn't).
# Left out of the target set now that that's confirmed, not assumed.
TARGET_PAIR_IDS = {"pair_01", "pair_11", "pair_15", "pair_28"}


def _build_profile(pair_id: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__recheck_{pair_id}__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for word, phones in spec.get("patterns", {}).items():
        p.set_word_pattern(word, phones)
    return p


def main() -> None:
    semantic.load_sbert()
    pairs = json.loads(open(PAIRS_PATH, encoding="utf-8").read())["pairs"]

    changed = []
    unchanged = 0
    for pair in pairs:
        profile = _build_profile(pair["pair_id"], pair["profile_spec"])
        result = reformulate.reformulate(pair["original_text"], profile)
        new_text = result["reformulated_text"]
        old_text = pair["reformulated_text"]
        if new_text != old_text or result["status"] != pair["status"]:
            changed.append((pair, result))
        else:
            unchanged += 1

    print(f"{len(pairs)} pairs re-run. {len(changed)} changed output, {unchanged} identical to the frozen pilot record.\n")

    for pair, result in changed:
        pid = pair["pair_id"]
        tag = " <- idiom-guard target" if pid in TARGET_PAIR_IDS else " <- UNEXPECTED, not a guard target"
        print(f"[{pid}] {pair['case_id']}{tag}")
        print(f"  original text:      {pair['original_text']}")
        print(f"  OLD reformulated:    {pair['reformulated_text']}  (status={pair['status']}, sbert={pair['metrics']['meaning_preservation']})")
        print(f"  NEW reformulated:    {result['reformulated_text']}  (status={result['status']}, sbert={result['metrics']['meaning_preservation']})")
        print(f"  NEW flagged_before/after: {result['metrics']['flagged_words_before']}/{result['metrics']['flagged_words_after']}"
              f"  (difficulty still resolved: {result['metrics']['flagged_words_after'] < result['metrics']['flagged_words_before'] or result['metrics']['flagged_words_before'] == 0})")
        print()

    missed_targets = TARGET_PAIR_IDS - {p["pair_id"] for p, _ in changed}
    if missed_targets:
        print(f"NOTE: {sorted(missed_targets)} were expected guard targets but produced IDENTICAL output to the frozen pilot record — investigate.")


if __name__ == "__main__":
    main()
