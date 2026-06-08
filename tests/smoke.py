"""
tests/smoke.py — behavioural baseline / regression net (not shipped, dev-only).

Run BEFORE and AFTER changes and diff the output.  DISABLE_DATAMUSE=1 is REQUIRED
for deterministic output (it skips the network synonym source):

    DISABLE_DATAMUSE=1 python tests/smoke.py > tests/after_sbert.txt
    diff tests/baseline_sbert.txt tests/after_sbert.txt     # (use fc on Windows)

Committed reference baselines:
  • tests/baseline_sbert.txt  — PRIMARY reference (SBERT-on; DISABLE_DATAMUSE=1)
  • tests/baseline.txt        — frequency-only (DISABLE_DATAMUSE=1 SMOKE_SKIP_SBERT=1)

Set SMOKE_SKIP_SBERT=1 to force frequency-only mode on RAM-constrained machines.
The WORD MODE section mirrors the app (sanitize_input first, then get_synonyms),
so it would catch the trailing-punctuation class of bug.  Optional 2nd arg =
comma/space separated stutter patterns to exercise the phoneme gates.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import semantic as sem
# Load SBERT so scores are real — unless SMOKE_SKIP_SBERT=1 (set this on
# RAM-constrained boxes where the model can't load; output stays deterministic
# in frequency-only mode and parity checks remain valid).
if os.environ.get("SMOKE_SKIP_SBERT") != "1":
    sem.load_sbert()

from engine import SynonymEngine
from grammar import sanitize_input, is_sentence, SentenceRewriter

engine   = SynonymEngine()
rewriter = SentenceRewriter(engine)

# ── Test corpus ───────────────────────────────────────────────────────────────
SENTENCES = [
    # clean control
    "The committee reached an important decision today.",
    # cross-POS cases the v3 POS-filter fix was built for
    "The company is under stress.",
    "He was eating lunch at the restaurant.",
    # idiom / protected phrase
    "I look forward to the meeting.",
    # subject-verb agreement (already works)
    "He go to school every day.",
    # the reported grammar failures
    "she is run right now",
    "I am go now",
    # predicate-adjective guards (MUST stay unchanged by grammar fix)
    "she is tired now",
    "the door is broken",
    "it is done",
    "he is gone",
    "I am well",
    # adjective-after-BE guards (must NOT receive an auxiliary_form/gerund fix)
    "The box is empty",
    "The water is dirty",
    "That movie is boring",
    # tense + informal
    "i dont eat pizza yesterday",
    # general sentence
    "The quick brown fox jumps over the lazy dog.",
]

WORDS = ["happy", "present", "street", "strong"]


def _patterns_from_arg():
    if len(sys.argv) > 1 and sys.argv[1].strip():
        import re
        return [p for p in re.split(r"[\s,]+", sys.argv[1].strip()) if p]
    return []


def main():
    patterns = _patterns_from_arg()
    print("=" * 78)
    print(f"SMOKE BASELINE   sbert={sem._sbert_ok}   patterns={patterns or '(none)'}")
    print("=" * 78)

    for s in SENTENCES:
        print("\n" + "-" * 78)
        print(f"INPUT:     {s!r}")
        if not is_sentence(s):
            res = engine.get_synonyms(s)
            for w, syns in res.items():
                print(f"  WORD {w!r:14} -> {syns}")
            continue

        sanitized, fixes = sanitize_input(s)
        print(f"SANITIZED: {sanitized!r}")
        for f in fixes:
            print(f"  FIX [{f['type']}] {f['original']!r} -> {f['corrected']!r}")

        # rewrite() gains optional phoneme kwargs later; call defensively
        try:
            result = rewriter.rewrite(sanitized, stutter_patterns=patterns)
        except TypeError:
            result = rewriter.rewrite(sanitized)

        for sub in result["substitutions"]:
            acc = sub.get("candidates", [])
            print(f"  SUB {sub['original_word']!r:14} ({sub['tag']}) "
                  f"-> {sub['chosen']!r}   accepted={acc}")
        skipped = result.get("skipped", [])
        # skipped may be list[str] (legacy) or list[dict] (after skip-reason change)
        norm_skip = [
            (x if isinstance(x, str) else f"{x.get('word')}:{x.get('reason')}")
            for x in skipped
        ]
        print(f"  SKIPPED:   {norm_skip}")

    print("\n" + "=" * 78)
    print("WORD MODE  (mirrors the app: sanitize_input first, then get_synonyms)")
    print("=" * 78)
    for w in WORDS:
        sanitized, _ = sanitize_input(w)
        res = engine.get_synonyms(sanitized)
        print(f"  {w!r:12} sanitized={sanitized!r}")
        for k, syns in res.items():
            print(f"    [{k}] -> {syns}")


if __name__ == "__main__":
    main()
