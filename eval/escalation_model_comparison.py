"""
eval/escalation_model_comparison.py — diagnostic experiment (NOT wired
into the live engine): does a stronger, promptable model, given the
speaker's difficulty profile and the REASON for the constraint (not
just a blocked-word list), out-perform the current T5 escalation path
on the sentences that path already fails on?

REFORMULATION_PROBLEM_MAP.md SS5 item 3 — this is the diagnostic
experiment named there, run before any decision to change the live
escalation path. reformulate.py/rephrase.py are NOT modified by this
script; it only reads them (reuses rephrase.generate_candidates() for
the baseline, and semantic.py's own verification functions for a fair,
apples-to-apples pass/fail check on both models' candidates).

Failing-case set: every (profile, sentence) pair from the committed
210-case ordinary-text corpus (tests/reformulation_ordinary_corpus.json,
via eval/reformulation_escalation_rate.py) where escalation was
triggered and failed — i.e. the exact cases this diagnostic is about,
not hand-picked.

Candidate model: google/flan-t5-base (247.6M params — comparable size
to the current Vamsi/T5_Paraphrase_Paws, 222.9M params, so this isn't
"a much bigger model wins," it's "does instruction-following + an
explained reason beat blocklist-only token blocking at a similar
parameter budget"). Same transformers library already in requirements.txt,
no new dependency beyond one more cached checkpoint.

    DISABLE_DATAMUSE=1 python eval/escalation_model_comparison.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("DISABLE_DATAMUSE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
from nltk import pos_tag, word_tokenize
import torch

import semantic as sem
import phonetic as ph
import rephrase
import reformulate as rf
from difficulty_profile import DifficultyProfile

ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT / "tests" / "reformulation_ordinary_corpus.json"
FLAN_MODEL_NAME = os.environ.get("FLAN_MODEL_NAME", "google/flan-t5-base")
OUT_CSV = ROOT / "eval" / f"escalation_model_comparison_results__{FLAN_MODEL_NAME.replace('/', '_')}.csv"

_SENTENCE_LEVEL_SKIP_REASONS = {
    "could not safely reformulate this sentence",
    "profile too restrictive for this sentence",
}


def _build_profile(name: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__cmp_{name}__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for ph_ in spec.get("phrases", []):
        p.add_phrase(ph_, source="user_typed")
    return p


def _flagged_words_for_sentence(sentence: str, profile: DifficultyProfile) -> list[str]:
    try:
        tokens = word_tokenize(sentence)
    except Exception:
        tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", sentence)
    tags = pos_tag(tokens)
    flagged = rf._flagged_positions(tokens, tags, profile)
    return [item["word"] for item in flagged]


def _find_failing_sentences() -> list[dict]:
    """Every (profile, sentence) pair where escalation triggered and
    failed, re-derived directly from reformulate.reformulate() (not from
    the committed results CSV, so this stays correct even if that CSV is
    regenerated later) -- the real 210-case ordinary-text corpus, not a
    hand-picked set."""
    data = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    cases = []
    for prof_spec in data["profiles"]:
        profile = _build_profile(prof_spec["name"], prof_spec)
        for text in data["texts"]:
            result = rf.reformulate(text, profile)
            for skip in result["skipped"]:
                if skip["reason"] in _SENTENCE_LEVEL_SKIP_REASONS:
                    sentence = skip["word"]  # sentence-level skips store the full sentence here
                    flagged = _flagged_words_for_sentence(sentence, profile)
                    cases.append({
                        "profile_name": prof_spec["name"],
                        "profile_spec": prof_spec,
                        "sentence": sentence,
                        "flagged_words": flagged,
                    })
    return cases


def _profile_reason(spec: dict) -> str:
    parts = []
    if spec.get("sounds"):
        parts.append(f"words that start with the sound(s) {', '.join(spec['sounds'])}")
    if spec.get("words"):
        parts.append(f"the specific word(s) {', '.join(spec['words'])}")
    if spec.get("phrases"):
        parts.append(f"the phrase(s) {', '.join(spec['phrases'])}")
    joined = " and ".join(parts) if parts else "certain sounds"
    return f"The speaker stutters on {joined}, so those must not appear in the rewrite."


_flan_tokenizer = None
_flan_model = None


def _load_flan():
    global _flan_tokenizer, _flan_model
    if _flan_model is not None:
        return
    from transformers import T5Tokenizer, T5ForConditionalGeneration
    _flan_tokenizer = T5Tokenizer.from_pretrained(FLAN_MODEL_NAME)
    _flan_model = T5ForConditionalGeneration.from_pretrained(FLAN_MODEL_NAME)
    _flan_model.eval()


def _flan_bad_words_ids(blocked_words) -> list[list[int]] | None:
    """Same case-variant blocking logic as rephrase.py::_bad_words_ids
    (R17), adapted to flan-t5's own tokenizer for the hybrid condition —
    can't reuse rephrase.py's version directly since it's bound to the
    Vamsi model's module-level tokenizer global."""
    if _flan_tokenizer is None or not blocked_words:
        return None
    ids: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    for raw in blocked_words:
        word = str(raw or "").strip()
        if not word:
            continue
        for variant in {word, word.lower(), word.capitalize()}:
            for form in (variant, " " + variant):
                encoded = _flan_tokenizer.encode(form, add_special_tokens=False)
                if encoded:
                    sig = tuple(encoded)
                    if sig not in seen:
                        seen.add(sig)
                        ids.append(encoded)
    return ids or None


def _generate_with_flan(sentence: str, flagged_words: list[str], reason: str, k: int = 5,
                         use_bad_words_ids: bool = False) -> list[str]:
    _load_flan()
    blocked_str = ", ".join(sorted(set(w.lower() for w in flagged_words)))
    prompt = (
        f"Rewrite this sentence so it does NOT contain any of these words: {blocked_str}. "
        f"{reason} Keep the exact same meaning and make it sound natural. "
        f"Sentence: {sentence}"
    )
    encoded = _flan_tokenizer(prompt, return_tensors="pt", truncation=True)
    max_beams = int(os.environ.get("FLAN_MAX_BEAMS", "12"))
    beams = max(4, min(max_beams, k * 2))
    kwargs = dict(
        num_beams=beams,
        num_return_sequences=min(beams, max(k, 1)),
        max_new_tokens=max(16, int(encoded["input_ids"].shape[1] * 1.5) + 8),
        no_repeat_ngram_size=3,
        early_stopping=True,
    )
    if use_bad_words_ids:
        bad_ids = _flan_bad_words_ids(flagged_words)
        if bad_ids:
            kwargs["bad_words_ids"] = bad_ids
    with torch.no_grad():
        outputs = _flan_model.generate(**encoded, **kwargs)
    seen, out = set(), []
    for o in outputs:
        text = _flan_tokenizer.decode(o, skip_special_tokens=True).strip()
        if text and text.lower() not in seen:
            seen.add(text.lower())
            out.append(text)
    return out


def _verify(original_sentence: str, candidate: str, profile: DifficultyProfile,
            blocked_words: set[str], min_semantic: float) -> dict:
    """Same three checks reformulate.py::_try_escalation applies, applied
    identically to a candidate from EITHER model -- the fairness contract
    of this whole experiment."""
    if candidate.strip().lower() == original_sentence.strip().lower():
        return {"pass": False, "reason": "unchanged", "sim": None}
    sim = sem.semantic_similarity(candidate, original_sentence)
    if sim is not None and sim < min_semantic:
        return {"pass": False, "reason": "below_sbert_threshold", "sim": sim}
    if not sem.negation_consistent(original_sentence, candidate):
        return {"pass": False, "reason": "negation_flip", "sim": sim}
    content_words = re.findall(r"[A-Za-z][A-Za-z'-]*", candidate)
    leaked = [w for w in content_words
              if ph.matches_any(w, profile.sound_values()) or w.lower() in blocked_words]
    if leaked:
        return {"pass": False, "reason": f"leaked:{','.join(sorted(set(leaked)))}", "sim": sim}
    return {"pass": True, "reason": "ok", "sim": sim}


def run_case(case: dict) -> dict:
    sentence = case["sentence"]
    profile = _build_profile(case["profile_name"], case["profile_spec"])
    blocked = {w.lower() for w in case["flagged_words"]}
    min_semantic = sem.MIN_SEMANTIC

    # -- baseline: current production model + bad_words_ids --
    t0 = time.time()
    base_cands = rephrase.generate_candidates(sentence, k=5, blocked_words=blocked)
    base_elapsed = time.time() - t0
    base_results = [_verify(sentence, c, profile, blocked, min_semantic) for c in base_cands]
    base_pass = [r for r in base_results if r["pass"]]
    base_best = max(base_pass, key=lambda r: r["sim"] or 0) if base_pass else \
        max(base_results, key=lambda r: r["sim"] or -1) if base_results else None

    # -- candidate A: flan-t5-base, prompted with reason, no bad_words_ids --
    reason = _profile_reason(case["profile_spec"])
    t0 = time.time()
    flan_cands = _generate_with_flan(sentence, case["flagged_words"], reason, k=5, use_bad_words_ids=False)
    flan_elapsed = time.time() - t0
    flan_results = [_verify(sentence, c, profile, blocked, min_semantic) for c in flan_cands]
    flan_pass = [r for r in flan_results if r["pass"]]
    flan_best = max(flan_pass, key=lambda r: r["sim"] or 0) if flan_pass else \
        max(flan_results, key=lambda r: r["sim"] or -1) if flan_results else None

    # -- candidate B: flan-t5-base, reason prompt AND bad_words_ids (hybrid) --
    t0 = time.time()
    hybrid_cands = _generate_with_flan(sentence, case["flagged_words"], reason, k=5, use_bad_words_ids=True)
    hybrid_elapsed = time.time() - t0
    hybrid_results = [_verify(sentence, c, profile, blocked, min_semantic) for c in hybrid_cands]
    hybrid_pass = [r for r in hybrid_results if r["pass"]]
    hybrid_best = max(hybrid_pass, key=lambda r: r["sim"] or 0) if hybrid_pass else \
        max(hybrid_results, key=lambda r: r["sim"] or -1) if hybrid_results else None

    base_best_text = base_cands[base_results.index(base_best)] if base_best and base_results else None
    flan_best_text = flan_cands[flan_results.index(flan_best)] if flan_best and flan_results else None
    hybrid_best_text = hybrid_cands[hybrid_results.index(hybrid_best)] if hybrid_best and hybrid_results else None

    return {
        "profile": case["profile_name"],
        "sentence": sentence,
        "flagged_words": ";".join(sorted(blocked)),
        "baseline_pass": bool(base_pass),
        "baseline_best_text": base_best_text,
        "baseline_best_sim": round(base_best["sim"], 4) if base_best and base_best["sim"] is not None else None,
        "baseline_best_reason": base_best["reason"] if base_best else "no_candidates",
        "baseline_seconds": round(base_elapsed, 2),
        "flan_pass": bool(flan_pass),
        "flan_best_text": flan_best_text,
        "flan_best_sim": round(flan_best["sim"], 4) if flan_best and flan_best["sim"] is not None else None,
        "flan_best_reason": flan_best["reason"] if flan_best else "no_candidates",
        "flan_seconds": round(flan_elapsed, 2),
        "hybrid_pass": bool(hybrid_pass),
        "hybrid_best_text": hybrid_best_text,
        "hybrid_best_sim": round(hybrid_best["sim"], 4) if hybrid_best and hybrid_best["sim"] is not None else None,
        "hybrid_best_reason": hybrid_best["reason"] if hybrid_best else "no_candidates",
        "hybrid_seconds": round(hybrid_elapsed, 2),
    }


def main() -> int:
    sem.load_sbert()
    cases = _find_failing_sentences()
    print(f"{len(cases)} failing sentences found (escalation triggered and failed in production)")

    limit = os.environ.get("LIMIT_CASES")
    if limit:
        # A stratified sample (every Nth case) rather than a plain prefix,
        # so a smaller run still covers more than one profile -- avoids
        # biasing a lighter robustness check toward whichever profile
        # happens to be listed first.
        n = int(limit)
        step = max(1, len(cases) // n)
        cases = cases[::step][:n]
        print(f"LIMIT_CASES set -- using a stratified sample of {len(cases)} cases")
    print()

    rows = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['profile_name']}: {case['sentence'][:70]}")
        row = run_case(case)
        rows.append(row)
        print(f"    baseline: pass={row['baseline_pass']} sim={row['baseline_best_sim']} "
              f"({row['baseline_seconds']}s)  |  flan-t5: pass={row['flan_pass']} "
              f"sim={row['flan_best_sim']} ({row['flan_seconds']}s)  |  hybrid: pass={row['hybrid_pass']} "
              f"sim={row['hybrid_best_sim']} ({row['hybrid_seconds']}s)")

    import csv
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwrote {len(rows)} rows to {OUT_CSV}")

    n = len(rows)
    base_pass_n = sum(1 for r in rows if r["baseline_pass"])
    flan_pass_n = sum(1 for r in rows if r["flan_pass"])
    hybrid_pass_n = sum(1 for r in rows if r["hybrid_pass"])
    base_time = sum(r["baseline_seconds"] for r in rows)
    flan_time = sum(r["flan_seconds"] for r in rows)
    hybrid_time = sum(r["hybrid_seconds"] for r in rows)
    base_sims = [r["baseline_best_sim"] for r in rows if r["baseline_best_sim"] is not None]
    flan_sims = [r["flan_best_sim"] for r in rows if r["flan_best_sim"] is not None]
    hybrid_sims = [r["hybrid_best_sim"] for r in rows if r["hybrid_best_sim"] is not None]
    print(f"\nBaseline (current T5 + bad_words_ids): {base_pass_n}/{n} passed ({base_pass_n/n:.1%}), "
          f"avg sim {sum(base_sims)/len(base_sims):.4f}, total {base_time:.1f}s, avg {base_time/n:.2f}s/case")
    print(f"flan-t5-base + reason prompt (no bad_words_ids): {flan_pass_n}/{n} passed ({flan_pass_n/n:.1%}), "
          f"avg sim {sum(flan_sims)/len(flan_sims):.4f}, total {flan_time:.1f}s, avg {flan_time/n:.2f}s/case")
    print(f"flan-t5-base + reason prompt + bad_words_ids (hybrid): {hybrid_pass_n}/{n} passed ({hybrid_pass_n/n:.1%}), "
          f"avg sim {sum(hybrid_sims)/len(hybrid_sims):.4f}, total {hybrid_time:.1f}s, avg {hybrid_time/n:.2f}s/case")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
