"""
eval/r10_nli_isolation.py -- same diagnostic as
eval/step3_gencheck_nli_isolation.py, applied to the R10 corpus (the
one underlying the 31-34% CLEAN-rate plateau, VALIDATION.md SS48-53),
added 2026-09-01 on branch `stage-lr` to make VALIDATION.md SS58's
NLI caveat precise for this figure too, not just the fresh-corpus one.

Isolates reformulate.py::_try_substitution() (deterministic, per
VALIDATION.md SS8.4) across all 398 (sentence, profile) pairs in
eval/r10_run_plan.json, run twice per pair -- once with
semantic.logical_consistency_check() live, once monkeypatched to
always return None -- to find every substitution-tier outcome that
flips from failure to success purely because of this specific NLI
gate. Read-only diagnostic: no gate, threshold, or pipeline file is
edited, per the architecture freeze (CLAUDE.md).

Run:
    DISABLE_DATAMUSE=1 python eval/r10_nli_isolation.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic
import engine as engine_module
from grammar import sanitize_input
from difficulty_profile import DifficultyProfile
import reformulate
import nltk

EVAL = Path(__file__).parent


def build_profile(run_id: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__r10_iso_{run_id}__")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for ph in spec.get("phrases", []):
        p.add_phrase(ph, source="user_typed")
    return p


def run_substitution(text: str, profile: DifficultyProfile, engine: "engine_module.SynonymEngine",
                      settings: "reformulate.ReformulateSettings") -> dict:
    tokens = nltk.word_tokenize(text)
    tags = nltk.pos_tag(tokens)
    flagged = reformulate._flagged_positions(tokens, tags, profile)
    if not flagged:
        return {"outcome": "no_flagged_words", "assembled": None, "changes": [], "skipped": []}
    new_tokens, changes, skipped = reformulate._try_substitution(text, tokens, tags, flagged, profile, engine, settings)
    if new_tokens is None:
        return {"outcome": "substitution_failed", "assembled": None, "changes": changes, "skipped": skipped}
    return {"outcome": "substitution_succeeded", "assembled": reformulate._detokenize(new_tokens),
            "changes": changes, "skipped": skipped}


def main() -> int:
    if os.environ.get("DISABLE_DATAMUSE") != "1":
        print("ERROR: run with DISABLE_DATAMUSE=1 for a controlled comparison.", file=sys.stderr)
        return 1

    corpus = json.loads((EVAL / "r10_corpus.json").read_text(encoding="utf-8"))
    sent_by_id = {r["sentence_id"]: r["sentence_text"] for r in corpus["records"]}
    run_plan = json.loads((EVAL / "r10_run_plan.json").read_text(encoding="utf-8"))["runs"]

    semantic.load_sbert()
    semantic.load_nli_model()
    semantic.load_grammar_tool()

    engine = engine_module.SynonymEngine()
    settings = reformulate.ReformulateSettings()
    real_nli = semantic.logical_consistency_check

    results = []
    total = len(run_plan)
    for i, run in enumerate(run_plan, 1):
        sid = run["sentence_id"]
        text = sent_by_id.get(sid)
        if text is None:
            continue
        run_id = run["profile_id"]
        profile = build_profile(run_id, run["spec"])
        corrected_text, _ = sanitize_input(text)

        semantic.logical_consistency_check = real_nli
        with_nli = run_substitution(corrected_text, profile, engine, settings)

        semantic.logical_consistency_check = lambda *a, **kw: None
        without_nli = run_substitution(corrected_text, profile, engine, settings)

        nli_blocked = any(
            s.get("reason") == "final sentence failed NLI contradiction check" for s in with_nli["skipped"]
        )
        flip = (with_nli["outcome"] != "substitution_succeeded"
                and without_nli["outcome"] == "substitution_succeeded")

        results.append({
            "run_id": run_id, "sentence_id": sid, "profile_type": run["profile_type"],
            "original_text": corrected_text,
            "with_nli_outcome": with_nli["outcome"],
            "without_nli_outcome": without_nli["outcome"],
            "nli_directly_blocked_it": nli_blocked,
            "nli_attributable_flip": flip,
            "assembled_without_nli": without_nli["assembled"] if flip else None,
        })
        if i % 20 == 0 or flip:
            flag = " <-- FLIP" if flip else ""
            print(f"  [{i}/{total}] {run_id:<28} with={with_nli['outcome']:<22} without={without_nli['outcome']:<22}{flag}", flush=True)

    semantic.logical_consistency_check = real_nli

    n_flips = sum(1 for r in results if r["nli_attributable_flip"])
    n_direct = sum(1 for r in results if r["nli_directly_blocked_it"])
    n_total = len(results)
    print(f"\n=== {n_direct}/{n_total} runs had NLI directly reject the assembled sentence ===")
    print(f"=== {n_flips}/{n_total} runs flip substitution-failure -> substitution-success with NLI disabled ===")

    OUT = EVAL / "r10_nli_isolation_results.json"
    OUT.write_text(json.dumps({"n_runs": n_total, "n_nli_direct_blocks": n_direct,
                                "n_nli_attributable_flips": n_flips, "results": results},
                               indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
