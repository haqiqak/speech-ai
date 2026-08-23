"""
eval/r44_phoneme_decoding.py — R44 Prototype 2: phoneme-aware
DECODING-TIME constraint for T5's escalation generation, as opposed to
A1's generate-then-block-named-words or A2's generate-then-reject-then-
regenerate. Both A1/A2 still let T5 finish a full candidate sentence
before anything checks it. This prototype intervenes mid-generation:
a custom `LogitsProcessor` decodes the in-progress beam text at every
step, and the moment any word (complete OR still-forming, as soon as its
onset is determinable) matches the profile's blocked sound patterns,
that beam's score is set to -inf so beam search abandons it in favor of
surviving beams that avoided the violation — the model is steered away
from the forbidden sound WHILE generating, not filtered after the fact.

Reuses existing infrastructure only: `phonetic.matches_any` (the same
onset-matching function the production phoneme veto already uses),
`rephrase.py`'s already-loaded T5 model/tokenizer (imported, not
reloaded, and not modified), the same 23 escalation-invoked cases as
R43/A1/A5.

Diagnostic only. Does NOT modify rephrase.py or reformulate.py — this
calls `_model.generate()` directly with an extra `logits_processor`,
which `transformers` already supports as a public parameter; the
production code path (`rephrase.generate_candidates`) is untouched.

Run:
    python eval/r44_phoneme_decoding.py            # full 23 cases
    python eval/r44_phoneme_decoding.py --smoke     # 2 cases, verbose, for correctness-checking first
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
from transformers import LogitsProcessor, LogitsProcessorList

import semantic as sem
import phonetic as ph
import rephrase
from grammar import sanitize_input
import reformulate

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ceiling_probe_r40 import SENTENCES, PROFILES, _build_profile  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "eval" / "ceiling_probe_r40_results.json"
BASELINE_PATH = ROOT / "eval" / "r43_escalation_instrumentation.json"
OUT_PATH = ROOT / "eval" / "r44_phoneme_decoding_results.json"

MIN_SEMANTIC = sem.MIN_SEMANTIC


class PhonemeConstraintLogitsProcessor(LogitsProcessor):
    """Kills (score = -inf) any beam whose decoded text-so-far contains a
    word matching one of `blocked_patterns` (phonetic.matches_any — the
    same onset-prefix check the production phoneme veto already uses),
    checked every generation step against every word in the beam's
    running text, including the still-forming last word — the moment a
    word's onset is long enough to determine a match, the beam dies.
    """

    def __init__(self, tokenizer, blocked_patterns: list[str], decoder_start_len: int):
        self.tokenizer = tokenizer
        self.blocked_patterns = blocked_patterns
        self.decoder_start_len = decoder_start_len
        self.kill_count = 0
        self.total_calls = 0

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        self.total_calls += 1
        if not self.blocked_patterns:
            return scores
        n_rows = input_ids.shape[0]
        for i in range(n_rows):
            if torch.isneginf(scores[i]).all():
                continue  # already dead, skip re-decoding for speed
            gen_ids = input_ids[i, self.decoder_start_len:]
            if gen_ids.numel() == 0:
                continue
            text = self.tokenizer.decode(gen_ids, skip_special_tokens=True)
            words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
            for w in words:
                if ph.matches_any(w, self.blocked_patterns):
                    scores[i, :] = float("-inf")
                    self.kill_count += 1
                    break
        return scores


def phoneme_constrained_generate(sentence: str, k: int, blocked_words: set[str],
                                  blocked_patterns: list[str]) -> tuple[list[str], dict]:
    """Mirrors rephrase.generate_candidates()'s call shape (base cleaning,
    prompt prefix, bad_words_ids for the literal blocked words — same as
    production) but ADDS the phoneme-level LogitsProcessor on top, and
    reports how many beams the processor actually killed."""
    if not rephrase._load_model():
        return [sentence], {"model_unavailable": True}

    base = rephrase._clean_generation(sentence)
    prompt = rephrase.REPHRASE_PREFIX + base
    encoded = rephrase._tokenizer(prompt, return_tensors="pt", truncation=True)
    device = next(rephrase._model.parameters()).device
    encoded = {key: val.to(device) for key, val in encoded.items()}
    in_len = int(encoded["input_ids"].shape[1])
    max_new_tokens = max(16, int(in_len * 1.5) + 8)
    beams = max(4, min(12, k * 2))
    bad_ids = rephrase._bad_words_ids(blocked_words)

    # decoder_start_len: T5 generation starts from a single decoder_start_token_id
    decoder_start_len = 1
    processor = PhonemeConstraintLogitsProcessor(rephrase._tokenizer, blocked_patterns, decoder_start_len)

    gen_kwargs = dict(
        num_beams=beams,
        num_return_sequences=min(beams, max(k * 2, k)),
        max_new_tokens=max_new_tokens,
        no_repeat_ngram_size=3,
        early_stopping=True,
        logits_processor=LogitsProcessorList([processor]),
    )
    if bad_ids:
        gen_kwargs["bad_words_ids"] = bad_ids

    with torch.no_grad():
        outputs = rephrase._model.generate(**encoded, **gen_kwargs)

    candidates = []
    seen = set()
    for output in outputs:
        text = rephrase._clean_generation(rephrase._tokenizer.decode(output, skip_special_tokens=True))
        sig = text.lower()
        if text and sig not in seen:
            seen.add(sig)
            candidates.append(text)

    return candidates[:k], {"beam_kills": processor.kill_count, "processor_calls": processor.total_calls}


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
    blocked_words = {item["word"].lower() for item in flagged}
    blocked_patterns = profile.sound_values()

    settings = reformulate.ReformulateSettings()
    raw_candidates, gen_stats = phoneme_constrained_generate(
        corrected_text, k=settings.t5_candidates,
        blocked_words=blocked_words, blocked_patterns=blocked_patterns,
    )

    candidates_out = []
    for cand in raw_candidates:
        is_dup = cand.strip().lower() == corrected_text.strip().lower()
        sim = sem.semantic_similarity(cand, corrected_text) if not is_dup else None
        sim_pass = (sim is not None and sim >= MIN_SEMANTIC) if not is_dup else False
        neg_ok = sem.negation_consistent(corrected_text, cand) if not is_dup else False
        content_words = re.findall(r"[A-Za-z][A-Za-z'-]*", cand)
        leaked = [w for w in content_words
                  if ph.matches_any(w, blocked_patterns) or w.lower() in blocked_words]
        accepted = (not is_dup) and sim_pass and neg_ok and not leaked
        candidates_out.append({
            "text": cand, "is_duplicate_of_input": is_dup,
            "sbert_sim": round(sim, 4) if sim is not None else None,
            "sbert_pass": sim_pass, "negation_consistent": neg_ok,
            "leaked_words": leaked, "leak_free": not leaked, "accepted": accepted,
        })

    return {
        "source": source, "profile": profile_name, "sentence": corrected_text,
        "blocked_patterns": blocked_patterns,
        "gen_stats": gen_stats,
        "n_raw_candidates": len(raw_candidates),
        "n_nondup": sum(1 for c in candidates_out if not c["is_duplicate_of_input"]),
        "n_sbert_pass": sum(1 for c in candidates_out if c["sbert_pass"]),
        "n_leak_free": sum(1 for c in candidates_out if c["leak_free"]),
        "n_accepted": sum(1 for c in candidates_out if c["accepted"]),
        "any_accepted": any(c["accepted"] for c in candidates_out),
        "candidates": candidates_out,
    }


def main() -> int:
    smoke = "--smoke" in sys.argv
    sem.load_sbert()
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))["results"]
    targets = [
        r for r in data
        if r["status"] == "could_not_safely_reformulate" or "restructuring" in r["change_sources"]
    ]
    if smoke:
        targets = targets[:2]
    print(f"R44 Prototype 2: {len(targets)} cases, phoneme-aware decoding-time constraint...", flush=True)

    results = []
    for i, r in enumerate(targets, 1):
        out = instrument_one(r["source"], r["original_text"], r["profile"], PROFILES[r["profile"]])
        results.append(out)
        print(f"  [{i}/{len(targets)}] {r['profile']:<22} {r['source']:<10} "
              f"beam_kills={out['gen_stats'].get('beam_kills','?')} "
              f"nondup={out['n_nondup']} sbert_pass={out['n_sbert_pass']} "
              f"leak_free={out['n_leak_free']} accepted={out['n_accepted']}", flush=True)
        if smoke:
            for c in out["candidates"]:
                print(f"      -> ({'DUP' if c['is_duplicate_of_input'] else c.get('sbert_sim')}) {c['text']}")

    OUT_PATH.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {len(results)} rows to {OUT_PATH}")

    if not smoke:
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["results"]
        b_nondup = sum(r["n_unique_non_duplicate"] for r in baseline)
        b_leak_free = sum(r["n_leak_free"] for r in baseline)
        b_accepted = sum(r["n_accepted"] for r in baseline)
        b_any = sum(1 for r in baseline if r["any_accepted"])

        p2_nondup = sum(r["n_nondup"] for r in results)
        p2_leak_free = sum(r["n_leak_free"] for r in results)
        p2_accepted = sum(r["n_accepted"] for r in results)
        p2_any = sum(1 for r in results if r["any_accepted"])

        print("\n=== R43 baseline vs R44 Prototype 2 (phoneme-aware decoding) ===")
        print(f"{'':<30}{'baseline':<20}{'Prototype 2':<20}")
        print(f"{'non-dup candidates':<30}{b_nondup:<20}{p2_nondup:<20}")
        print(f"{'leak-free':<30}{f'{b_leak_free} ({b_leak_free/b_nondup:.0%})':<20}"
              f"{f'{p2_leak_free} ({p2_leak_free/max(1,p2_nondup):.0%})':<20}")
        print(f"{'accepted':<30}{f'{b_accepted} ({b_accepted/b_nondup:.0%})':<20}"
              f"{f'{p2_accepted} ({p2_accepted/max(1,p2_nondup):.0%})':<20}")
        print(f"{'cases with >=1 accepted':<30}{f'{b_any}/23':<20}{f'{p2_any}/23':<20}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
