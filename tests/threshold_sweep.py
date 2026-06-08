"""
tests/threshold_sweep.py — DIAGNOSTIC ONLY (dev tool; NOT imported by the app).

Sweeps semantic.MIN_SEMANTIC over a range and reports, on the smoke corpus, how
many candidates / words survive the SBERT gate at each threshold, with a per-POS
breakdown and the chosen substitution for two representative sentences.  Use it
to pick a sensible default — it does NOT modify the committed default.

Run (DISABLE_DATAMUSE=1 is required for determinism; SBERT must be available):

    DISABLE_DATAMUSE=1 python tests/threshold_sweep.py

──────────────────────────────────────────────────────────────────────────────
RECOMMENDATION (from a real run on the smoke corpus; SBERT all-MiniLM-L6-v2,
semantic/freq weights 0.9/0.1):

    Recommended MIN_SEMANTIC ≈ 0.80   (current committed default is 0.85).

    • At 0.85 word-coverage is only ~40% and clearly-valid swaps disappear
      (stress→tension and decision→choice are both dropped).
    • 0.78–0.82 is the stable "knee": the representative picks settle on
      reached→came, important→key, decision→choice, stress→tension and stop
      drifting, at ~50–52% coverage.
    • Below ~0.74 low-similarity drift creeps in (e.g. reached→gave,
      company→organization).

    Per-POS thresholds WOULD help: verbs (VB) stay acceptable even at 0.85, but
    nouns (NN) collapse at high thresholds (NN ~40/102 @0.70 → ~4/28 @0.85). A
    slightly lower gate for NN (~0.78) with VB/JJ/RB (~0.82) would keep noun
    coverage without admitting verb drift.

    This script does NOT change the default — the maintainer chooses.
──────────────────────────────────────────────────────────────────────────────
"""
import os
import sys

os.environ.setdefault("DISABLE_DATAMUSE", "1")
# Prevent the smoke import from loading SBERT at import time; we load it ourselves.
os.environ.setdefault("SMOKE_SKIP_SBERT", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic as sem
from engine import SynonymEngine
from grammar import sanitize_input, is_sentence, SentenceRewriter

try:
    from smoke import SENTENCES
except Exception:  # pragma: no cover
    from tests.smoke import SENTENCES

THRESHOLDS = [0.70, 0.74, 0.78, 0.80, 0.82, 0.85]
REPRESENTATIVE = [
    "The company is under stress.",
    "The committee reached an important decision today.",
]


def _pos_bucket(tag: str) -> str:
    for p in ("NN", "VB", "JJ", "RB"):
        if tag.startswith(p):
            return p
    return "OT"


def main() -> int:
    if not sem.load_sbert():
        print("SBERT unavailable — threshold sweep requires SBERT. Skipping cleanly.")
        return 0

    engine = SynonymEngine()
    rw = SentenceRewriter(engine)

    corpus = [sanitize_input(s)[0] for s in SENTENCES if is_sentence(s)]
    rep = [sanitize_input(s)[0] for s in REPRESENTATIVE]

    print(f"corpus={len(corpus)} sentences  DISABLE_DATAMUSE={os.environ.get('DISABLE_DATAMUSE')}")
    print(f"SBERT model={sem.SBERT_MODEL}  committed default MIN_SEMANTIC={sem.MIN_SEMANTIC}")
    print(f"scoring weights: semantic={sem.SEMANTIC_W}  frequency={sem.FREQUENCY_W}\n")
    print(f"{'thr':>5} | {'cand_acc/tot':>13} {'rate':>6} | {'word_cov':>9} | per-POS accepted/total")
    print("-" * 96)

    orig_default = sem.MIN_SEMANTIC
    rows = []
    try:
        for thr in THRESHOLDS:
            sem.MIN_SEMANTIC = thr
            tot = acc = 0
            words_sub = words_rejected = 0
            pos = {p: [0, 0] for p in ("NN", "VB", "JJ", "RB", "OT")}
            rep_choice = {}
            for s in corpus:
                res = rw.rewrite(s)
                for sub in res["substitutions"]:
                    words_sub += 1
                    b = _pos_bucket(sub["tag"])
                    for sc in sub.get("scored", []):
                        tot += 1
                        pos[b][1] += 1
                        if sc["accepted"]:
                            acc += 1
                            pos[b][0] += 1
                for sk in res.get("skipped", []):
                    if isinstance(sk, dict) and sk.get("reason") == "no valid synonym":
                        words_rejected += 1
                if s in rep:
                    rep_choice[s] = [(x["original_word"], x["chosen"]) for x in res["substitutions"]]
            rate = (acc / tot) if tot else 0.0
            cov_den = words_sub + words_rejected
            cov = (words_sub / cov_den) if cov_den else 0.0
            pos_str = "  ".join(f"{p} {pos[p][0]}/{pos[p][1]}" for p in ("NN", "VB", "JJ", "RB"))
            print(f"{thr:5.2f} | {acc:5d}/{tot:<7d} {rate:6.1%} | {cov:9.1%} | {pos_str}")
            rows.append((thr, rep_choice))
    finally:
        sem.MIN_SEMANTIC = orig_default  # never leak a mutated default

    print("\n── chosen substitutions for representative sentences ──")
    for thr, rep_choice in rows:
        print(f"\n[thr={thr:.2f}]")
        for s, picks in rep_choice.items():
            print(f"  {s!r}")
            print(f"     {picks}")

    print("\n(Interpretation: higher threshold = fewer, safer substitutions. Look for the "
          "knee where acceptance drops sharply and the representative picks stop drifting.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
