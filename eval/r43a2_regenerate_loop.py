"""
eval/r43a2_regenerate_loop.py — R43-A2: prototype a generate-verify-
regenerate loop with targeted feedback, instead of a static pre-
generation blocklist, for the T5 escalation tier.

Diagnostic only. Does NOT modify reformulate.py or rephrase.py -- calls
`rephrase.generate_candidates()` repeatedly, each round expanding
`blocked_words` with whatever specific words leaked in the PREVIOUS
round's best (highest-SBERT) candidate. This directly targets the R43
mechanism finding: T5's default move is a minimal edit that dodges the
letter of a static block, not the spirit of it -- so telling it exactly
which word it just used, and blocking THAT, should close more of the gap
than a single upfront guess (R43-A1) alone.

Same 23 escalation-invoked cases as R43/R43-A1, same three verification
gates, so results are directly comparable. Max 3 additional rounds
(4 total generate_candidates calls per case) -- bounded so this stays a
diagnostic, not an open-ended search. Latency measured per case.

Run:
    python eval/r43a2_regenerate_loop.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
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
from ceiling_probe_r40 import PROFILES, _build_profile  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "eval" / "ceiling_probe_r40_results.json"
OUT_PATH = ROOT / "eval" / "r43a2_regenerate_loop_results.json"

MIN_SEMANTIC = sem.MIN_SEMANTIC
T5_CANDIDATES = reformulate.ReformulateSettings().t5_candidates
MAX_ROUNDS = 4  # 1 baseline round + up to 3 targeted-feedback rounds


def _flagged_for(sentence: str, profile: DifficultyProfile):
    from nltk import pos_tag, word_tokenize
    try:
        tokens = word_tokenize(sentence)
    except Exception:
        tokens = re.findall(r"[A-Za-z][A-Za-z'-]*|[.,!?;:]", sentence)
    tags = reformulate._correct_predicate_adjective_tags(tokens, pos_tag(tokens))
    return reformulate._flagged_positions(tokens, tags, profile)


def _evaluate(cand: str, sentence: str, sound_values, literal_blocked: set[str]):
    is_dup = cand.strip().lower() == sentence.strip().lower()
    sim = sem.semantic_similarity(cand, sentence) if not is_dup else None
    sim_pass = (sim is not None and sim >= MIN_SEMANTIC) if not is_dup else False
    neg_ok = sem.negation_consistent(sentence, cand) if not is_dup else False
    content_words = re.findall(r"[A-Za-z][A-Za-z'-]*", cand)
    leaked = [
        w for w in content_words
        if ph.matches_any(w, sound_values) or w.lower() in literal_blocked
    ]
    accepted = (not is_dup) and sim_pass and neg_ok and not leaked
    return {
        "text": cand, "is_duplicate_of_input": is_dup,
        "sbert_sim": round(sim, 4) if sim is not None else None,
        "sbert_pass": sim_pass, "negation_consistent": neg_ok,
        "leaked_words": leaked, "leak_free": not leaked, "accepted": accepted,
    }


def run_one(source: str, text: str, profile_name: str, spec: dict) -> dict:
    profile = _build_profile(profile_name, spec)
    corrected_text, _ = sanitize_input(text)
    flagged = _flagged_for(corrected_text, profile)
    literal_blocked = {item["word"].lower() for item in flagged}
    sound_values = profile.sound_values()

    blocking_set = set(literal_blocked)
    rounds = []
    accepted_result = None
    t0 = time.perf_counter()

    for round_i in range(1, MAX_ROUNDS + 1):
        raw_candidates = rephrase.generate_candidates(
            corrected_text, k=T5_CANDIDATES, blocked_words=blocking_set
        )
        evaluated = [_evaluate(c, corrected_text, sound_values, literal_blocked) for c in raw_candidates]
        rounds.append({
            "round": round_i,
            "blocked_words_this_round": sorted(blocking_set),
            "candidates": evaluated,
        })

        for e in evaluated:
            if e["accepted"]:
                accepted_result = e
                break
        if accepted_result is not None:
            break

        # Targeted feedback: pull leaked words from the BEST (highest-
        # SBERT) non-duplicate candidate this round, add them to the
        # block set for the next round.
        non_dup = [e for e in evaluated if not e["is_duplicate_of_input"]]
        if not non_dup:
            break  # T5 has nothing left to offer (model unavailable / degenerate)
        best = max(non_dup, key=lambda e: e["sbert_sim"] or -1.0)
        new_words = {w.lower() for w in best["leaked_words"]} - blocking_set
        if not new_words:
            break  # converged -- nothing new to block, further rounds won't help
        blocking_set |= new_words

    elapsed = time.perf_counter() - t0
    return {
        "source": source, "profile": profile_name, "sentence": corrected_text,
        "n_rounds_run": len(rounds), "accepted": accepted_result is not None,
        "accepted_candidate": accepted_result,
        "final_blocking_set_size": len(blocking_set),
        "literal_blocked_size": len(literal_blocked),
        "elapsed_seconds": round(elapsed, 2),
        "rounds": rounds,
    }


def main() -> int:
    sem.load_sbert()
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))["results"]
    targets = [
        r for r in data
        if r["status"] == "could_not_safely_reformulate" or "restructuring" in r["change_sources"]
    ]
    print(f"R43-A2: {len(targets)} cases, up to {MAX_ROUNDS} rounds each with targeted feedback...", flush=True)

    results = []
    for i, r in enumerate(targets, 1):
        out = run_one(r["source"], r["original_text"], r["profile"], PROFILES[r["profile"]])
        results.append(out)
        print(f"  [{i}/{len(targets)}] {r['profile']:<22} {r['source']:<10} "
              f"rounds={out['n_rounds_run']} accepted={out['accepted']} "
              f"time={out['elapsed_seconds']}s", flush=True)

    OUT_PATH.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False), encoding="utf-8")

    n = len(results)
    n_accepted = sum(1 for r in results if r["accepted"])
    avg_rounds = sum(r["n_rounds_run"] for r in results) / n
    avg_time = sum(r["elapsed_seconds"] for r in results) / n
    baseline_avg_time = 2.5  # ~T5 single-call cost per case, per R14/R23's measured baseline

    print("\n=== R43-A2 SUMMARY ===")
    print(f"accepted: {n_accepted}/{n} ({n_accepted/n:.0%})  (R43 baseline: 2/23, 9%)")
    print(f"avg rounds used: {avg_rounds:.1f} / {MAX_ROUNDS} max")
    print(f"avg time/case: {avg_time:.1f}s (baseline single-call ~{baseline_avg_time}s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
