"""
eval/r43a1_inflected_blocking.py — R43-A1: does robustly blocking every
inflected/orthographic form of each flagged word (not just the literal
form + case/spacing variants `_bad_words_ids` already handles) reduce
T5's leak rate in the escalation tier?

Diagnostic only. Does NOT modify reformulate.py or rephrase.py — calls
`rephrase.generate_candidates()` exactly as production code does, just
with a richer `blocked_words` argument (a parameter that function already
accepts). Same 23 escalation-invoked (sentence, profile) pairs as R43,
same three verification checks, so results are directly comparable to
`eval/r43_escalation_instrumentation.json`'s baseline.

Expansion method for each flagged word:
  1. lemmatize (grammar.lemmatize, POS-aware, reuses existing code)
  2. also lemmatize a hyphen-stripped variant (pyinflect's own gap on
     compounds like "pre-trained" -> "" — found directly this pass)
  3. pyinflect.getAllInflections() on both lemmas -> every JJ/JJR/JJS/
     RB/RBR/RBS/NN/NNS/VB/VBD/VBG/VBN/VBP/VBZ form pyinflect knows
  4. re-hyphenate each generated form at the same position as the
     original word, as an additional spelling variant, since T5 leaked
     both "pretrained" and "pre-training" for one blocked "pre-trained"

Run:
    python eval/r43a1_inflected_blocking.py
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
from grammar import sanitize_input, lemmatize, _wn_pos
from difficulty_profile import DifficultyProfile
import reformulate
import pyinflect

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ceiling_probe_r40 import SENTENCES, PROFILES, _build_profile  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "eval" / "ceiling_probe_r40_results.json"
BASELINE_PATH = ROOT / "eval" / "r43_escalation_instrumentation.json"
OUT_PATH = ROOT / "eval" / "r43a1_inflected_blocking_results.json"

MIN_SEMANTIC = sem.MIN_SEMANTIC
T5_CANDIDATES = reformulate.ReformulateSettings().t5_candidates

_ALL_TAGS = ["JJ", "JJR", "JJS", "RB", "RBR", "RBS", "NN", "NNS",
             "VB", "VBD", "VBG", "VBN", "VBP", "VBZ"]


def _expand_one_word(word: str, tag: str) -> set[str]:
    """Every inflected/spelling variant of `word` this pass can derive,
    on top of the literal word itself."""
    variants = {word}
    lemma = lemmatize(word, tag)
    variants.add(lemma)

    candidates_for_inflection = {lemma}
    if "-" in word:
        stripped = word.replace("-", "")
        variants.add(stripped)
        candidates_for_inflection.add(stripped)
        candidates_for_inflection.add(lemmatize(stripped, tag))

    hyphen_pos = word.find("-")  # -1 if none

    for base in candidates_for_inflection:
        try:
            forms = pyinflect.getAllInflections(base)
        except Exception:
            forms = {}
        for t in _ALL_TAGS:
            for form in forms.get(t, ()):
                variants.add(form)
                if hyphen_pos != -1 and "-" not in form and len(form) > hyphen_pos:
                    # re-insert a hyphen at the same relative position as
                    # the original word had, e.g. "pretraining" -> "pre-training"
                    variants.add(form[:hyphen_pos] + "-" + form[hyphen_pos:])
    return variants


def _expand_blocked(blocked: set[str], tokens: list[str], tags: list[tuple]) -> set[str]:
    tag_by_lower = {t.lower(): tg for t, tg in zip(tokens, [tg for _, tg in tags])}
    expanded: set[str] = set()
    for w in blocked:
        tag = tag_by_lower.get(w, "NN")
        expanded |= _expand_one_word(w, tag)
    return expanded


def instrument_one(source: str, text: str, profile_name: str, spec: dict) -> dict:
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

    expanded_blocked = _expand_blocked(blocked, tokens, tags)

    raw_candidates = rephrase.generate_candidates(
        corrected_text, k=T5_CANDIDATES, blocked_words=expanded_blocked
    )

    candidates_out = []
    for cand in raw_candidates:
        is_dup = cand.strip().lower() == corrected_text.strip().lower()
        sim = sem.semantic_similarity(cand, corrected_text) if not is_dup else None
        sim_pass = (sim is not None and sim >= MIN_SEMANTIC) if not is_dup else False
        neg_ok = sem.negation_consistent(corrected_text, cand) if not is_dup else False
        content_words = re.findall(r"[A-Za-z][A-Za-z'-]*", cand)
        # Safety/leak definition UNCHANGED from R43 baseline (original
        # flagged sounds + original literal blocked words) -- expanding
        # what we ask T5 to avoid must not quietly expand what counts as
        # "safe," or this would not be a fair comparison.
        leaked = [
            w for w in content_words
            if ph.matches_any(w, profile.sound_values()) or w.lower() in blocked
        ]
        accepted = (not is_dup) and sim_pass and neg_ok and not leaked
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
        "blocked_words_original": sorted(blocked),
        "blocked_words_expanded": sorted(expanded_blocked),
        "n_expanded_over_original": len(expanded_blocked) - len(blocked),
        "n_raw_candidates_from_t5": len(raw_candidates),
        "n_unique_non_duplicate": sum(1 for c in candidates_out if not c["is_duplicate_of_input"]),
        "n_sbert_pass": sum(1 for c in candidates_out if c["sbert_pass"]),
        "n_leak_free": sum(1 for c in candidates_out if c["leak_free"]),
        "n_accepted": sum(1 for c in candidates_out if c["accepted"]),
        "any_accepted": any(c["accepted"] for c in candidates_out),
        "candidates": candidates_out,
    }


def main() -> int:
    sem.load_sbert()
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))["results"]
    targets = [
        r for r in data
        if r["status"] == "could_not_safely_reformulate" or "restructuring" in r["change_sources"]
    ]
    print(f"R43-A1: re-running {len(targets)} escalation-invoked cases with "
          f"inflected-form-expanded blocking...", flush=True)

    results = []
    for i, r in enumerate(targets, 1):
        out = instrument_one(r["source"], r["original_text"], r["profile"], PROFILES[r["profile"]])
        results.append(out)
        print(f"  [{i}/{len(targets)}] {r['profile']:<22} {r['source']:<10} "
              f"blocked {len(out['blocked_words_original'])}->{len(out['blocked_words_expanded'])} words "
              f"sbert_pass={out['n_sbert_pass']} leak_free={out['n_leak_free']} accepted={out['n_accepted']}",
              flush=True)

    OUT_PATH.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Compare against R43 baseline ────────────────────────────────
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["results"]
    b_total_nondup = sum(r["n_unique_non_duplicate"] for r in baseline)
    b_leak_free = sum(r["n_leak_free"] for r in baseline)
    b_accepted = sum(r["n_accepted"] for r in baseline)
    b_any_accepted = sum(1 for r in baseline if r["any_accepted"])

    a1_total_nondup = sum(r["n_unique_non_duplicate"] for r in results)
    a1_leak_free = sum(r["n_leak_free"] for r in results)
    a1_accepted = sum(r["n_accepted"] for r in results)
    a1_any_accepted = sum(1 for r in results if r["any_accepted"])

    print("\n=== R43-A1 vs R43 BASELINE ===")
    print(f"{'metric':<30} {'baseline':<15} {'A1 (expanded block)':<20}")
    print(f"{'non-duplicate candidates':<30} {b_total_nondup:<15} {a1_total_nondup:<20}")
    print(f"{'leak-free':<30} {f'{b_leak_free} ({b_leak_free/b_total_nondup:.0%})':<15} "
          f"{f'{a1_leak_free} ({a1_leak_free/a1_total_nondup:.0%})':<20}")
    print(f"{'accepted (all gates)':<30} {f'{b_accepted} ({b_accepted/b_total_nondup:.0%})':<15} "
          f"{f'{a1_accepted} ({a1_accepted/a1_total_nondup:.0%})':<20}")
    print(f"{'cases with >=1 accepted':<30} {f'{b_any_accepted}/23':<15} {f'{a1_any_accepted}/23':<20}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
