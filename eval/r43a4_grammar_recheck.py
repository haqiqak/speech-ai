"""
eval/r43a4_grammar_recheck.py — R43-A4: does LanguageTool catch R40's
grammar-corruption class, which is a DIFFERENT error class than the one
R28 tested (R28's corpus was "syntactically well-formed sentences built
from the wrong word" -- 0/7 caught; this is literal surface grammar
errors: subject-verb agreement, non-standard plurals, a noun used as a
verb).

Diagnostic only. Bypasses grammar.py::_correct_with_languagetool()
entirely (R28 already found and left unfixed a real attribute-name bug
in that wrapper) -- calls `language_tool_python.LanguageTool` directly.
Uses the portable JRE already cached from R28 (.cache/jre17/), and the
DEFAULT language_tool_python cache location rather than paths.py's
LTP_PATH redirect, since R28 found that redirect reproducibly fails
(download completes, target directory ends up empty).

Also verifies, directly (not assumed), a new finding surfaced while
preparing this test: the "gases was->were" corruption in R40's audit is
NOT a reformulation-engine substitution at all -- sanitize_input()'s own
subject-verb-agreement layer changes it BEFORE reformulate() ever runs,
misidentifying the nearby plural "gases" as the grammatical subject
instead of the true singular head noun "the warming effect". A third,
independent bug source, distinct from both the spellchecker
(optimises->optimists, already found) and the substitution engine's
wrong-sense picks.

Run:
    python eval/r43a4_grammar_recheck.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401 -- still needed for HF/torch cache redirects

ROOT = Path(__file__).resolve().parent.parent
JRE_BIN = ROOT / ".cache" / "jre17" / "bin"
OUT_PATH = ROOT / "eval" / "r43a4_grammar_recheck_results.json"

# R28's own finding: paths.py's LTP_PATH redirect reproducibly fails.
# Undo it for this diagnostic so LanguageTool uses its own working
# default cache (~/.cache/language_tool_python/), same workaround R28
# already verified works.
os.environ.pop("LTP_PATH", None)
os.environ["PATH"] = str(JRE_BIN) + os.pathsep + os.environ.get("PATH", "")

import semantic as sem  # noqa: E402


# 12 SEVERE, grammar-labeled cases from R40's audit (index into
# eval/r40_change_audit_verdicts.json), plus the 4 "was->were" cases
# (already baked into `original_sentence` by sanitize_input, not stored
# as their own change entry -- see module docstring).
GRAMMAR_CASE_INDICES = [2, 8, 39, 64, 65]  # one representative per distinct defect
# CLEAN-verdict cases, as a false-positive check.
CLEAN_CASE_INDICES = [6, 21, 22, 23, 36, 66]


def load_cases():
    verdicts = json.loads((ROOT / "eval" / "r40_change_audit_verdicts.json").read_text(encoding="utf-8"))["verdicts"]
    data = json.loads((ROOT / "eval" / "r40_change_audit_data.json").read_text(encoding="utf-8"))["changes"]
    by_index = {v["index"]: v for v in verdicts}
    return by_index, data


def main() -> int:
    from language_tool_python import LanguageTool

    print("Loading LanguageTool (portable JRE)...", flush=True)
    try:
        tool = LanguageTool("en-US")
    except Exception as exc:
        print(f"FAILED TO LOAD: {exc.__class__.__name__}: {exc}")
        OUT_PATH.write_text(json.dumps({"error": str(exc)}), encoding="utf-8")
        return 1
    print("Loaded.", flush=True)

    by_index, data = load_cases()
    results = []

    def check(label: str, index: int, sentence: str):
        matches = tool.check(sentence)
        found = [{"rule_id": m.ruleId if hasattr(m, "ruleId") else getattr(m, "rule_id", None),
                  "message": m.message, "context": m.context} for m in matches]
        results.append({"label": label, "index": index, "sentence": sentence,
                         "n_matches": len(found), "matches": found})
        print(f"  [{label} #{index}] {len(found)} match(es): {sentence[:70]}")
        for m in found:
            print(f"      {m['rule_id']}: {m['message']}")

    print("\n=== Grammar-corruption SEVERE cases (does LT catch these?) ===")
    for idx in GRAMMAR_CASE_INDICES:
        c = data[idx - 1]
        check("GRAMMAR-SEVERE", idx, c["reformulated_sentence"])

    print("\n=== The was->were case, both original (should be clean) and corrupted ===")
    was_were_original = ("Before the 1980s, it was unclear whether the warming effect of "
                          "increased greenhouse gases was stronger than the cooling effect "
                          "of airborne particulates in air pollution.")
    was_were_corrupted = ("Before the 1980s, it was unclear whether the warming effect of "
                           "increased greenhouse gases were stronger than the cooling effect "
                           "of airborne particulates in air pollution.")
    check("WAS-WERE-ORIGINAL(correct)", 0, was_were_original)
    check("WAS-WERE-CORRUPTED(sanitize_input bug)", 0, was_were_corrupted)

    print("\n=== CLEAN-verdict cases (false-positive check) ===")
    for idx in CLEAN_CASE_INDICES:
        c = data[idx - 1]
        check("CLEAN", idx, c["reformulated_sentence"])

    OUT_PATH.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False), encoding="utf-8")

    n_grammar_caught = sum(1 for r in results if r["label"] == "GRAMMAR-SEVERE" and r["n_matches"] > 0)
    n_grammar_total = sum(1 for r in results if r["label"] == "GRAMMAR-SEVERE")
    n_clean_false_positive = sum(1 for r in results if r["label"] == "CLEAN" and r["n_matches"] > 0)
    n_clean_total = sum(1 for r in results if r["label"] == "CLEAN")
    was_were_result = [r for r in results if "WAS-WERE" in r["label"]]

    print("\n=== SUMMARY ===")
    print(f"grammar-corruption cases caught: {n_grammar_caught}/{n_grammar_total}")
    print(f"clean cases false-flagged: {n_clean_false_positive}/{n_clean_total}")
    for r in was_were_result:
        print(f"{r['label']}: {r['n_matches']} match(es)")

    tool.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
