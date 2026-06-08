"""
tests/evaluate.py - deterministic measurement script for the Speech AI pipeline.

Run with SBERT on and Datamuse disabled:

    DISABLE_DATAMUSE=1 python tests/evaluate.py

Metrics:
  A = sanitized original sentence.
  B = synonym-substituted output from SentenceRewriter.
  C = B plus optional rephrase.choose_best output.

  sbert_B_A / sbert_C_A:
      semantic.semantic_similarity(B, A) and semantic.semantic_similarity(C, A)
      using semantic.SBERT_MODEL. None if SBERT cannot load.
  difficulty_A/B/C:
      phonetic.sentence_difficulty(content words).
  reduction_B / reduction_C:
      difficulty_A - difficulty_B/C.
  violation_rate_A/B/C:
      number of content words whose onset matches the synthetic profile or whose
      lowercase word is blocked, divided by content-word count.
  edit_B_A / edit_C_B:
      1 - difflib.SequenceMatcher ratio.
  coverage:
      accepted substitutions divided by risky words in A.

Datamuse is forced off for determinism. BERTScore is included only when the
bert_score package is installed; otherwise it is reported as skipped.
"""

from __future__ import annotations

import csv
import difflib
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("DISABLE_DATAMUSE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import phonetic
import semantic
from engine import SynonymEngine
from grammar import SentenceRewriter, is_sentence, sanitize_input

try:
    import rephrase
except Exception:  # pragma: no cover
    rephrase = None


ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "eval_corpus.txt"
OUT_CSV = ROOT / "eval_results.csv"

PROFILES = [
    {"name": "default_like", "patterns": ["str", "pr", "b", "tr"], "blocked": {"present"}},
    {"name": "soft_onsets", "patterns": ["m", "f", "l", "sp"], "blocked": {"meeting"}},
]


def _content_words(sentence: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'-]*", sentence or "")


def _violations(sentence: str, patterns, blocked) -> int:
    blocked = {str(w).lower() for w in (blocked or set())}
    count = 0
    for word in _content_words(sentence):
        low = word.lower()
        if low in blocked or phonetic.matches_any(word, patterns):
            count += 1
    return count


def _rate(sentence: str, patterns, blocked) -> float:
    words = _content_words(sentence)
    if not words:
        return 0.0
    return _violations(sentence, patterns, blocked) / len(words)


def _difficulty(sentence: str) -> float:
    return phonetic.sentence_difficulty(_content_words(sentence))


def _edit(a: str, b: str) -> float:
    return round(1.0 - difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio(), 4)


def _sim(a: str, b: str):
    val = semantic.semantic_similarity(a, b)
    return round(val, 4) if val is not None else None


def _fmt(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _load_sentences() -> list[str]:
    lines = []
    for line in CORPUS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def _bertscore_status() -> str:
    try:
        import bert_score  # noqa: F401
        return "available (not run by default to keep this deterministic smoke lightweight)"
    except Exception:
        return "skipped (bert_score not installed)"


def _row(engine: SynonymEngine, rw: SentenceRewriter, sentence: str, profile: dict) -> dict:
    patterns = profile["patterns"]
    blocked = set(profile["blocked"])
    sanitized, _ = sanitize_input(sentence)
    if not is_sentence(sanitized):
        rewritten = sanitized
        result = {"substitutions": []}
    else:
        result = rw.rewrite(
            sanitized,
            top_k=6,
            stutter_patterns=patterns,
            blocked_words=blocked,
        )
        rewritten = result["rewritten"]

    if rephrase is not None:
        c_result = rephrase.choose_best(sanitized, rewritten, patterns, blocked)
        rephrased = c_result["rephrased"]
        rephrase_applied = c_result["applied"]
    else:
        rephrased = rewritten
        rephrase_applied = False

    risky = _violations(sanitized, patterns, blocked)
    accepted = len(result.get("substitutions", []))
    coverage = (accepted / risky) if risky else 0.0

    diff_a = _difficulty(sanitized)
    diff_b = _difficulty(rewritten)
    diff_c = _difficulty(rephrased)

    return {
        "profile": profile["name"],
        "sentence": sentence,
        "A": sanitized,
        "B": rewritten,
        "C": rephrased,
        "sbert_B_A": _sim(rewritten, sanitized),
        "sbert_C_A": _sim(rephrased, sanitized),
        "difficulty_A": diff_a,
        "difficulty_B": diff_b,
        "difficulty_C": diff_c,
        "reduction_B": round(diff_a - diff_b, 4),
        "reduction_C": round(diff_a - diff_c, 4),
        "violation_rate_A": round(_rate(sanitized, patterns, blocked), 4),
        "violation_rate_B": round(_rate(rewritten, patterns, blocked), 4),
        "violation_rate_C": round(_rate(rephrased, patterns, blocked), 4),
        "edit_B_A": _edit(rewritten, sanitized),
        "edit_C_B": _edit(rephrased, rewritten),
        "risky_words": risky,
        "accepted_substitutions": accepted,
        "coverage": round(coverage, 4),
        "rephrase_applied": rephrase_applied,
    }


def _avg(rows: list[dict], key: str) -> float:
    vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
    return sum(vals) / len(vals) if vals else 0.0


def _summary(rows: list[dict], name: str) -> dict:
    return {
        "profile": name,
        "n": len(rows),
        "sbert_B_A": _avg(rows, "sbert_B_A"),
        "sbert_C_A": _avg(rows, "sbert_C_A"),
        "difficulty_A": _avg(rows, "difficulty_A"),
        "difficulty_B": _avg(rows, "difficulty_B"),
        "difficulty_C": _avg(rows, "difficulty_C"),
        "reduction_B": _avg(rows, "reduction_B"),
        "reduction_C": _avg(rows, "reduction_C"),
        "violation_A": _avg(rows, "violation_rate_A"),
        "violation_B": _avg(rows, "violation_rate_B"),
        "violation_C": _avg(rows, "violation_rate_C"),
        "coverage": _avg(rows, "coverage"),
    }


def _print_table(summaries: list[dict]) -> None:
    cols = [
        "profile", "n", "sbert_B_A", "sbert_C_A", "difficulty_A",
        "difficulty_B", "difficulty_C", "reduction_B", "reduction_C",
        "violation_A", "violation_B", "violation_C", "coverage",
    ]
    print(" | ".join(f"{c:>13}" for c in cols))
    print("-" * (16 * len(cols)))
    for row in summaries:
        print(" | ".join(f"{_fmt(row[c]):>13}" for c in cols))


def main() -> int:
    if os.environ.get("DISABLE_DATAMUSE") != "1":
        print("Set DISABLE_DATAMUSE=1 for deterministic evaluation.")
        return 2
    sbert_ok = semantic.load_sbert()
    print(f"SBERT model={semantic.SBERT_MODEL} loaded={sbert_ok}")
    print(f"semantic threshold={semantic.MIN_SEMANTIC}")
    print(f"Datamuse disabled={os.environ.get('DISABLE_DATAMUSE') == '1'}")
    print(f"BERTScore: {_bertscore_status()}")

    engine = SynonymEngine()
    rw = SentenceRewriter(engine)
    sentences = _load_sentences()
    rows = []
    for profile in PROFILES:
        for sentence in sentences:
            rows.append(_row(engine, rw, sentence, profile))

    fields = list(rows[0].keys()) if rows else []
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    summaries = []
    for profile in PROFILES:
        subset = [r for r in rows if r["profile"] == profile["name"]]
        summaries.append(_summary(subset, profile["name"]))
    summaries.append(_summary(rows, "overall"))

    print(f"\nwrote {OUT_CSV} ({len(rows)} rows)")
    _print_table(summaries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
