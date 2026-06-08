"""
Build a small controlled rephrase fine-tuning dataset.

Offline best-of-N self-distillation:
  1. sample a synthetic stutter profile
  2. run the existing synonym pipeline to get the awkward intermediate sentence
  3. generate N rephrase candidates
  4. score with rephrase.choose_best's reward surface
  5. write JSONL rows:
       {"input": "avoid: ... | blocked: ... | repair: ...", "target": "..."}

Smoke run:
    python scripts/build_rephrase_dataset.py --smoke --output scripts/toy_rephrase_dataset.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DISABLE_DATAMUSE", "1")

from engine import SynonymEngine
from grammar import SentenceRewriter, is_sentence, sanitize_input
import rephrase


PROFILES = [
    {"patterns": ["pr", "str"], "blocked": {"present"}},
    {"patterns": ["b", "tr"], "blocked": {"breakfast"}},
    {"patterns": ["m", "f", "l"], "blocked": {"meeting"}},
    {"patterns": ["sp", "k"], "blocked": {"contract"}},
]

SMOKE_SENTENCES = [
    "The company prepared a practical project plan.",
    "The student practiced the speech before class.",
    "The manager confirmed the schedule this morning.",
    "The baker prepared a fresh pastry for lunch.",
    "The assistant printed the final contract.",
]


def _read_sentences(path: Path | None, smoke: bool) -> list[str]:
    if smoke or path is None:
        return SMOKE_SENTENCES
    return [
        line.strip() for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def _profile_text(profile: dict) -> tuple[str, str]:
    avoid = ",".join(profile["patterns"])
    blocked = ",".join(sorted(profile["blocked"]))
    return avoid, blocked


def _best_candidate(original: str, intermediate: str, profile: dict, n: int, weights) -> dict:
    generated = rephrase.generate_candidates(
        intermediate,
        k=max(n, 1),
        blocked_words=profile["blocked"],
    )
    # choose_best includes the unchanged intermediate and uses the same scoring
    # surface as production. The generated list above warms/records candidates.
    result = rephrase.choose_best(
        original,
        intermediate,
        profile["patterns"],
        profile["blocked"],
        weights=weights,
    )
    result["generated"] = generated
    return result


def build_rows(sentences: list[str], n: int, seed: int, weights=None) -> list[dict]:
    rng = random.Random(seed)
    engine = SynonymEngine()
    rw = SentenceRewriter(engine)
    rows = []
    for sentence in sentences:
        profile = rng.choice(PROFILES)
        sanitized, _ = sanitize_input(sentence)
        if is_sentence(sanitized):
            result = rw.rewrite(
                sanitized,
                top_k=6,
                stutter_patterns=profile["patterns"],
                blocked_words=set(profile["blocked"]),
            )
            intermediate = result["rewritten"]
        else:
            intermediate = sanitized
        best = _best_candidate(sanitized, intermediate, profile, n, weights)
        avoid, blocked = _profile_text(profile)
        rows.append({
            "input": f"avoid: {avoid} | blocked: {blocked} | repair: {intermediate}",
            "target": best["rephrased"],
            "original": sanitized,
            "intermediate": intermediate,
            "profile": {"patterns": profile["patterns"], "blocked": sorted(profile["blocked"])},
            "score": {
                "applied": best["applied"],
                "sim": best["sim"],
                "violations": best["violations"],
                "difficulty": best["difficulty"],
            },
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "tests" / "eval_corpus.txt")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "rephrase_dataset.jsonl")
    parser.add_argument("--n", type=int, default=5, help="best-of-N candidate count")
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--smoke", action="store_true", help="use the built-in five-row toy input")
    parser.add_argument("--w-sim", type=float, default=1.0)
    parser.add_argument("--w-diff", type=float, default=0.6)
    parser.add_argument("--w-viol", type=float, default=1.0)
    parser.add_argument("--w-edit", type=float, default=0.4)
    args = parser.parse_args()

    weights = {
        "w_sim": args.w_sim,
        "w_diff": args.w_diff,
        "w_viol": args.w_viol,
        "w_edit": args.w_edit,
    }
    sentences = _read_sentences(args.input, args.smoke)
    rows = build_rows(sentences, args.n, args.seed, weights)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows to {args.output}")
    for row in rows[:5]:
        print(f"- {row['input']} -> {row['target']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
