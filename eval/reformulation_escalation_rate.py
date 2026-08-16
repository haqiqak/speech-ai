"""
eval/reformulation_escalation_rate.py — how often does reformulate.py's T5
restructuring-escalation path actually trigger, and how often does it
succeed, on ORDINARY text?

Stage 6 (VALIDATION.md §6) measured a 0/4 escalation success rate, but
explicitly flagged that its corpus was built failure-mode-dense
(REFORMULATION_RESEARCH.md §17) and could not answer how often escalation
is even reached in typical usage. This script answers that question
directly: tests/reformulation_ordinary_corpus.json crosses 42 ordinary,
non-adversarial texts (36 already-committed eval_corpus.txt sentences +
6 ordinary paragraphs) against 5 realistic (not sentence-tailored)
difficulty profiles — 210 cases, reformulate.py only (this question is
specific to the escalation path, which the retained legacy pipelines
don't have, so this run doesn't need the three-way comparison).

A sentence's outcome is classified from reformulate.py's own result
structure, not re-derived: a "restructuring"-sourced entry in
result["changes"] means escalation was triggered and succeeded for that
sentence; an entry in result["skipped"] means escalation was triggered
(either pre-triggered by the count/degenerate-fraction check, or
triggered by a failed substitution attempt) and failed — reformulate.py
never adds a sentence to result["skipped"] for any other reason (word-
level substitution failures that lead to escalation are absorbed into
the sentence-level outcome, not surfaced separately — see
reformulate.py's own module docstring for the pipeline shape).

Run (DISABLE_DATAMUSE=1 required for determinism):

    DISABLE_DATAMUSE=1 python eval/reformulation_escalation_rate.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DISABLE_DATAMUSE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic
from difficulty_profile import DifficultyProfile
import reformulate

ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT / "tests" / "reformulation_ordinary_corpus.json"
OUT_CSV = ROOT / "eval" / "reformulation_escalation_rate_results.csv"

_SENTENCE_LEVEL_SKIP_REASONS = {
    "could not safely reformulate this sentence",
    "profile too restrictive for this sentence",
}


def _build_profile(name: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__ordinary_{name}__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for ph_ in spec.get("phrases", []):
        p.add_phrase(ph_, source="user_typed")
    return p


def run() -> list[dict]:
    data = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    profiles = data["profiles"]
    texts = data["texts"]

    sbert_ok = semantic.load_sbert()
    print(f"SBERT loaded={sbert_ok}  profiles={len(profiles)}  texts={len(texts)}  total_cases={len(profiles) * len(texts)}")

    rows: list[dict] = []
    for prof_spec in profiles:
        profile = _build_profile(prof_spec["name"], prof_spec)
        for text in texts:
            result = reformulate.reformulate(text, profile)
            n_sentences = len(reformulate.split_sentences(text))

            n_restructuring = sum(1 for c in result["changes"] if c["source"] == "restructuring")
            n_substitution = sum(1 for c in result["changes"] if c["source"] == "substitution")
            n_escalation_failed = sum(
                1 for s in result["skipped"] if s["reason"] in _SENTENCE_LEVEL_SKIP_REASONS
            )
            n_escalation_triggered = n_restructuring + n_escalation_failed

            rows.append({
                "profile": prof_spec["name"],
                "text_preview": text[:60],
                "n_sentences": n_sentences,
                "status": result["status"],
                "flagged_before": result["metrics"]["flagged_words_before"],
                "n_substitution_changes": n_substitution,
                "n_escalation_triggered": n_escalation_triggered,
                "n_escalation_succeeded": n_restructuring,
                "n_escalation_failed": n_escalation_failed,
            })

    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    import csv
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    rows = run()
    write_csv(rows, OUT_CSV)
    print(f"\nwrote {len(rows)} rows to {OUT_CSV}\n")

    n_cases = len(rows)
    n_flagged = sum(1 for r in rows if r["flagged_before"] > 0)
    n_escalation_triggered = sum(r["n_escalation_triggered"] for r in rows)
    n_escalation_succeeded = sum(r["n_escalation_succeeded"] for r in rows)
    n_escalation_failed = sum(r["n_escalation_failed"] for r in rows)
    n_sentences_total = sum(r["n_sentences"] for r in rows)

    print(f"Total (text, profile) cases:            {n_cases}")
    print(f"Cases with >=1 flagged word:             {n_flagged} ({n_flagged/n_cases:.1%})")
    print(f"Total sentences processed:               {n_sentences_total}")
    print(f"Sentences where escalation triggered:    {n_escalation_triggered} ({n_escalation_triggered/n_sentences_total:.2%} of all sentences)")
    print(f"  -> escalation succeeded:                {n_escalation_succeeded}")
    print(f"  -> escalation failed:                   {n_escalation_failed}")
    if n_escalation_triggered:
        print(f"  -> escalation success rate when triggered: {n_escalation_succeeded/n_escalation_triggered:.1%}")

    print("\n--- by profile ---")
    profile_names = sorted(set(r["profile"] for r in rows))
    for name in profile_names:
        sub = [r for r in rows if r["profile"] == name]
        trig = sum(r["n_escalation_triggered"] for r in sub)
        succ = sum(r["n_escalation_succeeded"] for r in sub)
        print(f"  {name:<24} triggered={trig:<4} succeeded={succ:<4}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
