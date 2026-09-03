"""
eval/step3_gencheck_nli_isolation.py -- corrected diagnostic (replaces
the first attempt in step3_gencheck_harvest_no_nli.py, which compared
full reformulate() outcomes and got contaminated by T5 escalation's
own documented non-determinism, VALIDATION.md SS8.4: "substitution-only
items showed no such instability... every affected item involved T5
restructuring escalation").

This isolates reformulate.py::_try_substitution() directly -- the
deterministic tier, per that same finding -- and runs it twice per
(sentence, profile) pair from step3_gencheck_corpus.py: once with
semantic.logical_consistency_check() live, once monkeypatched to
always return None. Escalation is never invoked, so T5 sampling cannot
confound the comparison. DISABLE_DATAMUSE=1 must be set when running
this (both passes happen in the same process, so Datamuse variance
cannot differ between them either way).

Answers precisely: of the 36 (sentence, profile) pairs, how many have
a substitution-tier outcome that flips from failure to success purely
because the NLI gate stopped rejecting the assembled sentence -- and,
for each flip, whether the newly-accepted candidate is actually good
(a true false positive) via the same blind-judge rubric this project
uses everywhere else.

Run:
    DISABLE_DATAMUSE=1 python eval/step3_gencheck_nli_isolation.py
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
from step3_gencheck_corpus import CORPUS, RUN_PLAN

EVAL = Path(__file__).parent


def build_profile(run_id: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__step3_iso_{run_id}__")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
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

    by_id = {c["id"]: c for c in CORPUS}
    semantic.load_sbert()
    semantic.load_nli_model()
    semantic.load_grammar_tool()

    engine = engine_module.SynonymEngine()
    settings = reformulate.ReformulateSettings()

    real_nli = semantic.logical_consistency_check

    results = []
    for run in RUN_PLAN:
        sent = by_id[run["id"]]
        run_id = f"{run['id']}-{run['profile_type']}"
        profile = build_profile(run_id, run)
        corrected_text, _ = sanitize_input(sent["text"])

        semantic.logical_consistency_check = real_nli
        with_nli = run_substitution(corrected_text, profile, engine, settings)

        semantic.logical_consistency_check = lambda *a, **kw: None
        without_nli = run_substitution(corrected_text, profile, engine, settings)

        nli_blocked_with_nli_on = any(
            s.get("reason") == "final sentence failed NLI contradiction check" for s in with_nli["skipped"]
        )
        flip = (with_nli["outcome"] != "substitution_succeeded"
                and without_nli["outcome"] == "substitution_succeeded")

        row = {
            "run_id": run_id, "sentence_id": run["id"], "profile_type": run["profile_type"],
            "original_text": corrected_text,
            "with_nli_outcome": with_nli["outcome"],
            "without_nli_outcome": without_nli["outcome"],
            "nli_directly_blocked_it": nli_blocked_with_nli_on,
            "nli_attributable_flip": flip,
            "assembled_without_nli": without_nli["assembled"] if flip else None,
        }
        results.append(row)
        flag = " <-- NLI-ATTRIBUTABLE FLIP" if flip else ""
        print(f"  {run_id:<22} with_nli={with_nli['outcome']:<24} without_nli={without_nli['outcome']:<24}{flag}", flush=True)

    semantic.logical_consistency_check = real_nli  # restore before exiting

    n_flips = sum(1 for r in results if r["nli_attributable_flip"])
    n_direct_blocks = sum(1 for r in results if r["nli_directly_blocked_it"])
    print(f"\n=== {n_direct_blocks}/36 runs had NLI directly reject the assembled sentence at least once ===")
    print(f"=== {n_flips}/36 runs flip from substitution-failure to substitution-success with NLI disabled ===")

    OUT = EVAL / "step3_gencheck_nli_isolation_results.json"
    OUT.write_text(json.dumps({"n_runs": len(results), "n_nli_direct_blocks": n_direct_blocks,
                                "n_nli_attributable_flips": n_flips, "results": results},
                               indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
