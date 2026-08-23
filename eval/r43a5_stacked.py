"""
eval/r43a5_stacked.py — R43-A5: what happens when A1 (expanded
inflected-form blocking), A3 (NLI logical-consistency check), and A4
(LanguageTool grammaticality check) run TOGETHER on the same 23
escalation-invoked cases, instead of each being tested in isolation?

This is the ceiling number the extend/redesign/fine-tune decision needs:
how much of the escalation tier's failure survives after stacking every
fix validated so far. A2 (generate-verify-regenerate) is deliberately
NOT included here -- it's a different kind of change (an iterative
control-flow change vs. a per-candidate filter) and mixing it in would
conflate two different questions. This tests the filter-stack question
cleanly first.

Diagnostic only. Does not modify reformulate.py, rephrase.py, or
semantic.py. Candidate generation reuses A1's exact expansion logic
(imported, not reimplemented); the three post-generation checks
(SBERT+negation+leak, unchanged from R43) get two NEW filters added on
top, using the exact same NLI model (A3) and LanguageTool setup (A4)
already validated in isolation.

Run:
    python eval/r43a5_stacked.py
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
import reformulate

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ceiling_probe_r40 import SENTENCES, PROFILES, _build_profile  # noqa: E402
from r43a1_inflected_blocking import _expand_blocked  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "eval" / "ceiling_probe_r40_results.json"
BASELINE_PATH = ROOT / "eval" / "r43_escalation_instrumentation.json"
A1_PATH = ROOT / "eval" / "r43a1_inflected_blocking_results.json"
OUT_PATH = ROOT / "eval" / "r43a5_stacked_results.json"

MIN_SEMANTIC = sem.MIN_SEMANTIC
T5_CANDIDATES = reformulate.ReformulateSettings().t5_candidates

JRE_BIN = ROOT / ".cache" / "jre17" / "bin"
os.environ.pop("LTP_PATH", None)
os.environ["PATH"] = str(JRE_BIN) + os.pathsep + os.environ.get("PATH", "")


def _load_grammar_tool():
    from language_tool_python import LanguageTool
    return LanguageTool("en-US")


def main() -> int:
    sem.load_sbert()
    print("loading NLI model (cross-encoder/nli-deberta-v3-xsmall)...", flush=True)
    from sentence_transformers import CrossEncoder
    nli = CrossEncoder("cross-encoder/nli-deberta-v3-xsmall")
    id2label = nli.model.config.id2label
    print("loading LanguageTool...", flush=True)
    lt = _load_grammar_tool()
    print("all models loaded.", flush=True)

    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))["results"]
    targets = [
        r for r in data
        if r["status"] == "could_not_safely_reformulate" or "restructuring" in r["change_sources"]
    ]
    print(f"R43-A5: {len(targets)} escalation-invoked cases, stacked A1+A3+A4...", flush=True)

    results = []
    for i, r in enumerate(targets, 1):
        source, text, profile_name = r["source"], r["original_text"], r["profile"]
        spec = PROFILES[profile_name]
        profile = _build_profile(profile_name, spec)
        corrected_text, _ = sanitize_input(text)

        from nltk import pos_tag, word_tokenize
        try:
            tokens = word_tokenize(corrected_text)
        except Exception:
            tokens = re.findall(r"[A-Za-z][A-Za-z'-]*|[.,!?;:]", corrected_text)
        tags = reformulate._correct_predicate_adjective_tags(tokens, pos_tag(tokens))
        flagged = reformulate._flagged_positions(tokens, tags, profile)
        blocked = {item["word"].lower() for item in flagged}
        expanded_blocked = _expand_blocked(blocked, tokens, tags)  # A1

        raw_candidates = rephrase.generate_candidates(
            corrected_text, k=T5_CANDIDATES, blocked_words=expanded_blocked
        )

        candidates_out = []
        for cand in raw_candidates:
            is_dup = cand.strip().lower() == corrected_text.strip().lower()
            if is_dup:
                candidates_out.append({"text": cand, "is_duplicate_of_input": True, "accepted": False,
                                        "fail_reasons": ["duplicate"]})
                continue

            fail_reasons = []
            sim = sem.semantic_similarity(cand, corrected_text)
            sim_pass = sim is not None and sim >= MIN_SEMANTIC
            if not sim_pass:
                fail_reasons.append("sbert")
            neg_ok = sem.negation_consistent(corrected_text, cand)
            if not neg_ok:
                fail_reasons.append("negation")
            content_words = re.findall(r"[A-Za-z][A-Za-z'-]*", cand)
            leaked = [w for w in content_words
                      if ph.matches_any(w, profile.sound_values()) or w.lower() in blocked]
            if leaked:
                fail_reasons.append("leak")

            # A3: NLI, neither direction may predict contradiction
            fwd, rev = nli.predict([(corrected_text, cand), (cand, corrected_text)])
            fwd_label = id2label[int(fwd.argmax())]
            rev_label = id2label[int(rev.argmax())]
            nli_ok = fwd_label != "contradiction" and rev_label != "contradiction"
            if not nli_ok:
                fail_reasons.append("nli_contradiction")

            # A4: LanguageTool, zero matches required (same bar as A4)
            try:
                lt_matches = lt.check(cand)
            except Exception:
                lt_matches = []
            grammar_ok = len(lt_matches) == 0
            if not grammar_ok:
                fail_reasons.append("grammar")

            accepted = not fail_reasons
            candidates_out.append({
                "text": cand,
                "is_duplicate_of_input": False,
                "sbert_sim": round(sim, 4) if sim is not None else None,
                "sbert_pass": sim_pass,
                "negation_consistent": neg_ok,
                "leaked_words": leaked,
                "leak_free": not leaked,
                "nli_fwd": fwd_label, "nli_rev": rev_label, "nli_ok": nli_ok,
                "grammar_matches": [m.ruleId if hasattr(m, "ruleId") else getattr(m, "rule_id", None) for m in lt_matches],
                "grammar_ok": grammar_ok,
                "fail_reasons": fail_reasons,
                "accepted": accepted,
            })

        n_nondup = sum(1 for c in candidates_out if not c["is_duplicate_of_input"])
        n_accepted = sum(1 for c in candidates_out if c["accepted"])
        result = {
            "source": source, "profile": profile_name, "sentence": corrected_text,
            "n_raw_candidates": len(raw_candidates),
            "n_nondup": n_nondup,
            "n_accepted": n_accepted,
            "any_accepted": n_accepted > 0,
            "candidates": candidates_out,
        }
        results.append(result)
        print(f"  [{i}/{len(targets)}] {profile_name:<22} {source:<10} "
              f"nondup={n_nondup} accepted={n_accepted}", flush=True)

    OUT_PATH.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    lt.close()

    # ── Compare against baseline and A1 ──
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["results"]
    a1 = json.loads(A1_PATH.read_text(encoding="utf-8"))["results"]

    def summarize(rows, nondup_key, accepted_key, any_key):
        total_nondup = sum(r[nondup_key] for r in rows)
        total_accepted = sum(r[accepted_key] for r in rows)
        n_any = sum(1 for r in rows if r[any_key])
        return total_nondup, total_accepted, n_any

    b_nondup, b_acc, b_any = summarize(baseline, "n_unique_non_duplicate", "n_accepted", "any_accepted")
    a1_nondup, a1_acc, a1_any = summarize(a1, "n_unique_non_duplicate", "n_accepted", "any_accepted")
    a5_nondup, a5_acc, a5_any = summarize(results, "n_nondup", "n_accepted", "any_accepted")

    print("\n=== R43 baseline vs A1 (blocking only) vs A5 (A1+A3+A4 stacked) ===")
    print(f"{'':<30}{'baseline':<20}{'A1':<20}{'A5 (stacked)':<20}")
    print(f"{'non-dup candidates':<30}{b_nondup:<20}{a1_nondup:<20}{a5_nondup:<20}")
    print(f"{'accepted':<30}{f'{b_acc} ({b_acc/b_nondup:.0%})':<20}"
          f"{f'{a1_acc} ({a1_acc/a1_nondup:.0%})':<20}"
          f"{f'{a5_acc} ({a5_acc/a5_nondup:.0%})':<20}")
    print(f"{'cases with >=1 accepted':<30}{f'{b_any}/23':<20}{f'{a1_any}/23':<20}{f'{a5_any}/23':<20}")

    # Fail-reason breakdown for A5 specifically
    reason_counts: dict[str, int] = {}
    for r in results:
        for c in r["candidates"]:
            if c["is_duplicate_of_input"] or c["accepted"]:
                continue
            for reason in c["fail_reasons"]:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
    print(f"\nA5 rejection reasons (candidates can fail >1 check): {reason_counts}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
