"""
eval/reformulation_eval.py — Stage 6 evaluation: reformulate.py (Architecture
D') vs. the two retained legacy pipelines (grammar.py::SentenceRewriter,
rewrite/rewriter.py::DifficultyAwareRewriter), on the shared corpus at
tests/reformulation_eval_corpus.json.

Methodology (REFORMULATION_RESEARCH.md §28):
  - grammar.py::sanitize_input() runs once per case, exactly as app.py does,
    before all three systems — so all three see identical input text.
  - Each case's DifficultyProfile is translated to each legacy system's own
    input shape on a best-effort-equivalent basis (documented per-case
    below, not assumed silently): sounds -> stutter_patterns / onboarding
    self-report; words -> blocked_words / always_replace. Phrases and
    word-specific problem_phones have NO equivalent in either legacy
    system — this is a real, structural capability gap, not an oversight,
    and is reported as such rather than worked around.
  - ALL THREE systems are scored with the SAME metric functions
    (semantic.semantic_similarity, phonetic-based flagged-word recovery,
    naturalness.edit_ratio) computed uniformly over each system's own
    (input, output) pair — not each system's own internal, differently-
    defined metrics — so the comparison is apples-to-apples.
  - Every metric here is an automatable PROXY (REFORMULATION_RESEARCH.md
    §28's table): SBERT similarity is not human-judged meaning
    preservation; the flagged-word recovery count is not a claim that the
    speaker would find the output easier to say. Neither is measured here.
    This script does not claim otherwise anywhere in its output.

Run (DISABLE_DATAMUSE=1 required for determinism):

    DISABLE_DATAMUSE=1 python eval/reformulation_eval.py
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
import phonetic
import naturalness as nat
from grammar import sanitize_input, SentenceRewriter, is_sentence
from engine import SynonymEngine
from difficulty_profile import DifficultyProfile
from profiling.profile import SpeakerDifficultyProfile
from rewrite.rewriter import DifficultyAwareRewriter
import reformulate

ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT / "tests" / "reformulation_eval_corpus.json"
OUT_CSV = ROOT / "eval" / "reformulation_eval_results.csv"


def _load_corpus() -> list[dict]:
    data = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    return data["cases"]


def _build_difficulty_profile(case: dict) -> DifficultyProfile:
    """In-memory only — never .save()'d, never touches users/."""
    p = DifficultyProfile(profile_name="__eval__")
    prof = case["profile"]
    for s in prof.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in prof.get("words", []):
        p.add_word(w, source="user_typed")
    for ph_ in prof.get("phrases", []):
        p.add_phrase(ph_, source="user_typed")
    for word, phones in prof.get("patterns", {}).items():
        p.set_word_pattern(word, phones)
    return p


def _run_new_engine(text: str, profile: DifficultyProfile) -> dict:
    return reformulate.reformulate(text, profile)


def _run_sentence_rewriter(
    text: str, rw: SentenceRewriter, stutter_patterns: list[str], blocked_words: set[str]
) -> tuple[str, dict]:
    """Mirrors app.py v7's actual multi-sentence loop and default candidate
    auto-selection (top accepted+phoneme_ok candidate per flagged word) —
    the same behavior a v7 user would have seen with no manual picks."""
    sentences = reformulate.split_sentences(text)
    rebuilt_parts = []
    all_skipped = []
    total_substitutions = 0
    for sentence in sentences:
        if not is_sentence(sentence):
            rebuilt_parts.append(sentence)
            continue
        result = rw.rewrite(
            sentence, top_k=10,
            stutter_patterns=stutter_patterns, blocked_words=blocked_words,
        )
        choices = {}
        for sub in result["substitutions"]:
            accepted = [s for s in sub.get("scored", []) if s["accepted"] and s.get("phoneme_ok", True)]
            if accepted:
                choices[sub["position"]] = accepted[0]["inflected"]
                total_substitutions += 1
        rebuilt_parts.append(rw.rebuild_with_choices(sentence, result["substitutions"], choices))
        all_skipped.extend(result.get("skipped", []))
    return " ".join(rebuilt_parts), {"skipped": all_skipped, "substitutions": total_substitutions}


def _run_difficulty_aware_rewriter(
    text: str, rewriter: DifficultyAwareRewriter, sp_profile: SpeakerDifficultyProfile, always_replace: set[str]
) -> tuple[str, dict]:
    result = rewriter.rewrite_paragraph(text, sp_profile, always_replace=always_replace)
    return result["rewritten_text"], {"skipped": result.get("skipped", []), "changes": len(result.get("change_log", []))}


def _uniform_metrics(original: str, output: str, profile: DifficultyProfile) -> dict:
    """The SAME metric functions applied to every system's (input, output)
    pair, so differences reflect the systems, not differing metric
    definitions. All are proxies — see module docstring."""
    sim = semantic.semantic_similarity(output, original)
    flagged_before = reformulate._flagged_word_count(original, profile)
    flagged_after = reformulate._flagged_word_count(output, profile)
    return {
        "meaning_preservation": round(sim, 4) if sim is not None else None,
        "flagged_before": flagged_before,
        "flagged_after": flagged_after,
        "difficulty_reduction_pct": (
            round(100.0 * (flagged_before - flagged_after) / flagged_before, 2) if flagged_before else 0.0
        ),
        "naturalness_edit_ratio": nat.edit_ratio(original, output),
        "changed": output.strip() != original.strip(),
    }


def run() -> list[dict]:
    cases = _load_corpus()
    engine = SynonymEngine()
    sentence_rewriter = SentenceRewriter(engine)
    difficulty_aware_rewriter = DifficultyAwareRewriter(engine)

    sbert_ok = semantic.load_sbert()
    print(f"SBERT model={semantic.SBERT_MODEL} loaded={sbert_ok}")
    print(f"MIN_SEMANTIC={semantic.MIN_SEMANTIC}")
    print(f"DISABLE_DATAMUSE={os.environ.get('DISABLE_DATAMUSE')}")
    print(f"corpus={CORPUS_PATH.name} n_cases={len(cases)}")
    print()

    rows: list[dict] = []
    for case in cases:
        profile = _build_difficulty_profile(case)
        corrected_text, grammar_fixes = sanitize_input(case["text"])

        stutter_patterns = profile.sound_values()
        blocked_words = set(profile.word_values())

        sp_profile = SpeakerDifficultyProfile(username="__eval__")
        sp_profile.onboarding(stutter_patterns)

        new_result = _run_new_engine(corrected_text, profile)
        new_output = new_result["reformulated_text"]

        sr_output, sr_meta = _run_sentence_rewriter(corrected_text, sentence_rewriter, stutter_patterns, blocked_words)

        dar_output, dar_meta = _run_difficulty_aware_rewriter(
            corrected_text, difficulty_aware_rewriter, sp_profile, blocked_words
        )

        base_row = {
            "id": case["id"],
            "category": case["category"],
            "grammar_fixes_applied": len(grammar_fixes),
            "input": corrected_text,
        }

        rows.append({
            **base_row, "system": "reformulate.py",
            "output": new_output,
            "status": new_result["status"],
            **_uniform_metrics(corrected_text, new_output, profile),
            "skipped_count": len(new_result["skipped"]),
            "changes_count": len(new_result["changes"]),
        })
        rows.append({
            **base_row, "system": "SentenceRewriter",
            "output": sr_output,
            "status": "changed" if sr_output.strip() != corrected_text.strip() else "no_change",
            **_uniform_metrics(corrected_text, sr_output, profile),
            "skipped_count": len(sr_meta["skipped"]),
            "changes_count": sr_meta["substitutions"],
        })
        rows.append({
            **base_row, "system": "DifficultyAwareRewriter",
            "output": dar_output,
            "status": "changed" if dar_output.strip() != corrected_text.strip() else "no_change",
            **_uniform_metrics(corrected_text, dar_output, profile),
            "skipped_count": len(dar_meta["skipped"]),
            "changes_count": dar_meta["changes"],
        })

    return rows


def _avg(rows: list[dict], key: str) -> float | None:
    vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
    return round(sum(vals) / len(vals), 4) if vals else None


def summarize(rows: list[dict]) -> list[dict]:
    systems = sorted(set(r["system"] for r in rows))
    summaries = []
    for sysname in systems:
        sub = [r for r in rows if r["system"] == sysname]
        n = len(sub)
        n_changed = sum(1 for r in sub if r.get("changed"))
        summaries.append({
            "system": sysname,
            "n_cases": n,
            "reformulation_rate": round(n_changed / n, 4) if n else 0.0,
            "avg_meaning_preservation": _avg(sub, "meaning_preservation"),
            "avg_difficulty_reduction_pct": _avg(sub, "difficulty_reduction_pct"),
            "avg_naturalness_edit_ratio": _avg(sub, "naturalness_edit_ratio"),
            "avg_flagged_after": _avg(sub, "flagged_after"),
        })
    return summaries


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

    summaries = summarize(rows)
    cols = ["system", "n_cases", "reformulation_rate", "avg_meaning_preservation",
            "avg_difficulty_reduction_pct", "avg_naturalness_edit_ratio", "avg_flagged_after"]
    print(" | ".join(f"{c:>26}" for c in cols))
    print("-" * (29 * len(cols)))
    for s in summaries:
        print(" | ".join(f"{str(s[c]):>26}" for c in cols))

    print("\n--- status distribution (reformulate.py only) ---")
    new_rows = [r for r in rows if r["system"] == "reformulate.py"]
    from collections import Counter
    print(dict(Counter(r["status"] for r in new_rows)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
