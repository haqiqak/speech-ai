"""
eval/r43_escalation_instrumentation.py — R43: instrument the T5 escalation
path on the exact 23 (sentence, profile) pairs from R40's existing
192-case corpus that actually invoked `reformulate._try_escalation`
(21 ended `could_not_safely_reformulate`, 2 succeeded — both the same
sentence). No new corpus, per explicit instruction to reuse R40's data.

This does NOT modify reformulate.py or rephrase.py. It calls the exact
same library functions production code calls
(`rephrase.generate_candidates`, `semantic.semantic_similarity`,
`semantic.negation_consistent`, `phonetic.matches_any`) from this
diagnostic script, and additionally logs every individual T5 candidate's
fate — something `reformulate._try_escalation` itself discards (it only
keeps the single best-scoring accepted candidate, or None). Same
"diagnostic script reuses production functions, doesn't change them"
pattern already used throughout R21/R23/R29/R31/R40.

For each candidate, records:
  - whether it's a duplicate of the input (T5/model unavailable signal)
  - SBERT similarity vs. the sentence, and whether it clears threshold
  - negation-marker-count parity (negation_consistent)
  - which content words (if any) leak a flagged sound or blocked word
  - whether it would be ACCEPTED (all three gates clear)

Run:
    python eval/r43_escalation_instrumentation.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic as sem
import phonetic as ph
import rephrase
from grammar import sanitize_input
from difficulty_profile import DifficultyProfile
import reformulate

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ceiling_probe_r40 import SENTENCES, PROFILES, _build_profile  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "eval" / "ceiling_probe_r40_results.json"
OUT_PATH = ROOT / "eval" / "r43_escalation_instrumentation.json"

MIN_SEMANTIC = sem.MIN_SEMANTIC  # production default, unchanged
T5_CANDIDATES = reformulate.ReformulateSettings().t5_candidates  # unchanged, =5


def _target_pairs() -> list[dict]:
    """Exactly the 23 (source, profile) pairs from R40's 192-case run
    whose status shows escalation was invoked — could_not_safely_
    reformulate (both tiers tried and failed) or reformulated via
    source=restructuring (escalation tried and succeeded)."""
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))["results"]
    return [
        r for r in data
        if r["status"] == "could_not_safely_reformulate" or "restructuring" in r["change_sources"]
    ]


def _flagged_for(sentence: str, profile: DifficultyProfile) -> list[dict]:
    """Reproduce reformulate.reformulate()'s own tagging step for one
    sentence, exactly as it runs in production — needed to rebuild the
    same `blocked` set _try_escalation uses, and to confirm whether this
    sentence was pre-escalated (density trigger) or substitution-failed."""
    from nltk import pos_tag, word_tokenize
    try:
        tokens = word_tokenize(sentence)
    except Exception:
        tokens = re.findall(r"[A-Za-z][A-Za-z'-]*|[.,!?;:]", sentence)
    tags = reformulate._correct_predicate_adjective_tags(tokens, pos_tag(tokens))
    return tokens, tags, reformulate._flagged_positions(tokens, tags, profile)


def instrument_one(source: str, text: str, profile_name: str, spec: dict) -> dict:
    profile = _build_profile(profile_name, spec)
    corrected_text, _ = sanitize_input(text)
    tokens, tags, flagged = _flagged_for(corrected_text, profile)
    blocked = {item["word"].lower() for item in flagged}

    phrase_protected = sem.protected_positions(tokens)
    content_count = reformulate._substitutable_content_word_count(tags, phrase_protected)
    flagged_fraction = len(flagged) / content_count
    settings = reformulate.ReformulateSettings()
    pre_escalated = (
        len(flagged) > settings.escalation_word_count
        or flagged_fraction > settings.degenerate_fraction
    )

    raw_candidates = rephrase.generate_candidates(
        corrected_text, k=T5_CANDIDATES, blocked_words=blocked
    )

    candidates_out = []
    any_accepted = False
    for cand in raw_candidates:
        is_dup = cand.strip().lower() == corrected_text.strip().lower()
        sim = sem.semantic_similarity(cand, corrected_text) if not is_dup else None
        sim_pass = (sim is not None and sim >= MIN_SEMANTIC) if not is_dup else False
        neg_ok = sem.negation_consistent(corrected_text, cand) if not is_dup else False
        content_words = re.findall(r"[A-Za-z][A-Za-z'-]*", cand)
        leaked = [
            w for w in content_words
            if ph.matches_any(w, profile.sound_values()) or w.lower() in blocked
        ]
        accepted = (not is_dup) and sim_pass and neg_ok and not leaked
        any_accepted = any_accepted or accepted
        candidates_out.append({
            "text": cand,
            "is_duplicate_of_input": is_dup,
            "sbert_sim": round(sim, 4) if sim is not None else None,
            "sbert_pass": sim_pass,
            "negation_consistent": neg_ok,
            "leaked_words": leaked,
            "leak_free": not leaked,
            "accepted": accepted,
        })

    return {
        "source": source,
        "profile": profile_name,
        "sentence": corrected_text,
        "pre_escalated": pre_escalated,
        "n_flagged": len(flagged),
        "flagged_fraction": round(flagged_fraction, 3),
        "blocked_words": sorted(blocked),
        "n_raw_candidates_from_t5": len(raw_candidates),
        "n_unique_non_duplicate": sum(1 for c in candidates_out if not c["is_duplicate_of_input"]),
        "n_sbert_pass": sum(1 for c in candidates_out if c["sbert_pass"]),
        "n_negation_ok": sum(1 for c in candidates_out if c["negation_consistent"]),
        "n_leak_free": sum(1 for c in candidates_out if c["leak_free"]),
        "n_accepted": sum(1 for c in candidates_out if c["accepted"]),
        "any_accepted": any_accepted,
        "candidates": candidates_out,
    }


def main() -> int:
    sem.load_sbert()
    targets = _target_pairs()
    print(f"Instrumenting {len(targets)} escalation-invoked (sentence, profile) pairs...", flush=True)

    results = []
    for i, r in enumerate(targets, 1):
        out = instrument_one(r["source"], r["original_text"], r["profile"], PROFILES[r["profile"]])
        results.append(out)
        print(f"  [{i}/{len(targets)}] {r['profile']:<22} {r['source']:<10} "
              f"pre_escalated={out['pre_escalated']} n_flagged={out['n_flagged']} "
              f"t5_candidates={out['n_raw_candidates_from_t5']} "
              f"sbert_pass={out['n_sbert_pass']} leak_free={out['n_leak_free']} "
              f"accepted={out['n_accepted']}", flush=True)

    OUT_PATH.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {len(results)} instrumented cases to {OUT_PATH}")

    # ── Aggregate summary ────────────────────────────────────────────
    n = len(results)
    n_pre_escalated = sum(1 for r in results if r["pre_escalated"])
    total_candidates = sum(r["n_raw_candidates_from_t5"] for r in results)
    total_non_dup = sum(r["n_unique_non_duplicate"] for r in results)
    total_sbert_pass = sum(r["n_sbert_pass"] for r in results)
    total_negation_ok = sum(r["n_negation_ok"] for r in results)
    total_leak_free = sum(r["n_leak_free"] for r in results)
    total_accepted = sum(r["n_accepted"] for r in results)
    n_any_accepted = sum(1 for r in results if r["any_accepted"])
    n_zero_nondup_candidates = sum(1 for r in results if r["n_unique_non_duplicate"] == 0)

    print("\n=== R43 AGGREGATE ===")
    print(f"cases (sentence,profile) with escalation invoked: {n} ({n_pre_escalated} pre-escalated by density)")
    print(f"total T5 candidates generated: {total_candidates} (avg {total_candidates/n:.1f}/case)")
    print(f"  non-duplicate-of-input: {total_non_dup} ({total_non_dup/total_candidates:.0%})")
    print(f"  cases where T5 produced ZERO non-duplicate candidates: {n_zero_nondup_candidates}/{n}")
    print(f"of non-duplicate candidates ({total_non_dup}):")
    print(f"  passed SBERT threshold ({MIN_SEMANTIC}): {total_sbert_pass} ({total_sbert_pass/max(1,total_non_dup):.0%})")
    print(f"  passed negation_consistent: {total_negation_ok} ({total_negation_ok/max(1,total_non_dup):.0%})")
    print(f"  leak-free (no flagged sound/word): {total_leak_free} ({total_leak_free/max(1,total_non_dup):.0%})")
    print(f"  accepted (all three): {total_accepted} ({total_accepted/max(1,total_non_dup):.0%})")
    print(f"cases with >=1 accepted candidate: {n_any_accepted}/{n}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
