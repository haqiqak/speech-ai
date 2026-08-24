"""
eval/r49_wider_sampling.py — cheap lever #1 (per the user's own framing
after R48): does genuinely wider candidate diversity rescue any of the
11 cases that still refuse under _try_escalation_v3 (52% ceiling, held
across three different combination strategies)? rephrase.py's beam
count is capped at 12 regardless of `k` (`beams = max(4, min(12, k*2))`,
rephrase.py:181/295) -- this tests two genuinely different diversity
sources, not just a bigger number fed through the same cap:
  (a) wider beam search (24 beams instead of 12), and
  (b) sampling-based generation (do_sample, temperature/top-p) --
      structurally different from beam search's tendency toward closely
      related top-N sequences.

Both reuse PhonemeConstraintLogitsProcessor exactly as-is (it's a
LogitsProcessor, compatible with either decoding strategy) -- no change
to rephrase.py or reformulate.py, this calls _model.generate() directly
with different kwargs. Diagnostic only.

Run:
    python eval/r49_wider_sampling.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import torch
import semantic as sem
import phonetic as ph
import rephrase
from rephrase import PhonemeConstraintLogitsProcessor
from grammar import sanitize_input
import reformulate
from transformers import LogitsProcessorList

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ceiling_probe_r40 import PROFILES, _build_profile  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROBE_PATH = ROOT / "eval" / "ceiling_probe_r40_results.json"
V3_RESULTS_PATH = ROOT / "eval" / "r48_v3_verification_results.json"
OUT_PATH = ROOT / "eval" / "r49_wider_sampling_results.json"

MIN_SEMANTIC = sem.MIN_SEMANTIC


def _generate(sentence, blocked_words, blocked_patterns, *, num_beams=None, do_sample=False,
              temperature=1.0, top_p=1.0, num_return=12):
    if not rephrase._load_model():
        return []
    base = rephrase._clean_generation(sentence)
    prompt = rephrase.REPHRASE_PREFIX + base
    encoded = rephrase._tokenizer(prompt, return_tensors="pt", truncation=True)
    device = next(rephrase._model.parameters()).device
    encoded = {k: v.to(device) for k, v in encoded.items()}
    in_len = int(encoded["input_ids"].shape[1])
    max_new_tokens = max(16, int(in_len * 1.5) + 8)
    bad_ids = rephrase._bad_words_ids(blocked_words)
    processor = PhonemeConstraintLogitsProcessor(rephrase._tokenizer, blocked_patterns)

    kwargs = dict(
        max_new_tokens=max_new_tokens,
        no_repeat_ngram_size=3,
        logits_processor=LogitsProcessorList([processor]),
        num_return_sequences=num_return,
    )
    if do_sample:
        kwargs.update(do_sample=True, temperature=temperature, top_p=top_p, num_beams=1)
    else:
        kwargs.update(num_beams=num_beams, early_stopping=True)
    if bad_ids:
        kwargs["bad_words_ids"] = bad_ids

    with torch.no_grad():
        outputs = rephrase._model.generate(**encoded, **kwargs)

    seen, cands = set(), []
    for output in outputs:
        text = rephrase._clean_generation(rephrase._tokenizer.decode(output, skip_special_tokens=True))
        sig = text.lower()
        if text and sig not in seen:
            seen.add(sig)
            cands.append(text)
    return cands


def _best_passing(sentence, cands, blocked_words, blocked_patterns):
    best = None
    for cand in cands:
        if cand.strip().lower() == sentence.strip().lower():
            continue
        sim = sem.semantic_similarity(cand, sentence)
        if sim is not None and sim < MIN_SEMANTIC:
            continue
        if not sem.negation_consistent(sentence, cand):
            continue
        content_words = re.findall(r"[A-Za-z][A-Za-z'-]*", cand)
        if any(ph.matches_any(w, blocked_patterns) or w.lower() in blocked_words for w in content_words):
            continue
        nli = sem.logical_consistency_check(sentence, cand)
        if nli is not None and nli["contradiction"]:
            continue
        rank = sim if sim is not None else -1.0
        if best is None or rank > best[1]:
            best = (cand, rank)
    return best


def main() -> int:
    sem.load_sbert()
    v3 = json.loads(V3_RESULTS_PATH.read_text(encoding="utf-8"))["results"]
    still_failing = [r for r in v3 if r["status"] == "could_not_safely_reformulate"]
    print(f"{len(still_failing)} cases still refuse under v3 (52% ceiling) -- "
          f"testing wider beams + sampling on these specifically.", flush=True)

    results = []
    for i, r in enumerate(still_failing, 1):
        src = "n/a"
        profile = _build_profile(r["profile"], PROFILES[r["profile"]])
        corrected, _ = sanitize_input(r["original_text"])

        from nltk import pos_tag, word_tokenize
        try:
            tokens = word_tokenize(corrected)
        except Exception:
            tokens = re.findall(r"[A-Za-z][A-Za-z'-]*|[.,!?;:]", corrected)
        tags = reformulate._correct_predicate_adjective_tags(tokens, pos_tag(tokens))
        flagged = reformulate._flagged_positions(tokens, tags, profile)
        blocked_words = {item["word"].lower() for item in flagged}
        blocked_patterns = profile.sound_values()

        wide_beam_cands = _generate(corrected, blocked_words, blocked_patterns,
                                     num_beams=24, num_return=24)
        sample_cands = _generate(corrected, blocked_words, blocked_patterns,
                                  do_sample=True, temperature=1.1, top_p=0.92, num_return=24)

        wide_best = _best_passing(corrected, wide_beam_cands, blocked_words, blocked_patterns)
        sample_best = _best_passing(corrected, sample_cands, blocked_words, blocked_patterns)

        rescued_by = None
        winner = None
        if wide_best is not None:
            rescued_by = "wide_beam"
            winner = wide_best
        if sample_best is not None and (winner is None or sample_best[1] > winner[1]):
            rescued_by = "sampling" if winner is None or sample_best[1] > wide_best[1] else rescued_by
            if sample_best[1] > (winner[1] if winner else -1):
                winner = sample_best
                rescued_by = "sampling"

        results.append({
            "source": src, "profile": r["profile"], "original_text": r["original_text"],
            "rescued": winner is not None,
            "rescued_by": rescued_by,
            "winning_text": winner[0] if winner else None,
            "winning_sim": winner[1] if winner else None,
            "n_wide_beam_candidates": len(wide_beam_cands),
            "n_sample_candidates": len(sample_cands),
        })
        print(f"  [{i}/{len(still_failing)}] rescued={winner is not None} by={rescued_by} "
              f"(wide_beam n={len(wide_beam_cands)}, sample n={len(sample_cands)})", flush=True)

    OUT_PATH.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    n_rescued = sum(1 for r in results if r["rescued"])
    print(f"\n=== R49: wider sampling on the 11 still-refusing cases ===")
    print(f"rescued: {n_rescued}/{len(results)}")
    print(f"If all {n_rescued} are genuinely good on manual read, escalation ceiling moves "
          f"from 12/23 (52%) to {12+n_rescued}/23 ({(12+n_rescued)/23:.0%}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
