"""
eval/escalation_model_comparison_decoder.py — R23: does a small,
decoder-only, instruction-tuned model do better than the encoder-decoder
candidates already tested in R21 (VALIDATION.md SS12), on the exact same
22 real currently-failing escalation cases?

Environment constraints, per direct instruction: the installed
`transformers` version, the current T5 implementation, and the
production pipeline are all left untouched. No dependency downgrade, no
`trust_remote_code=True`. Candidate models are restricted to small,
UNGATED, natively-supported (no `trust_remote_code`) checkpoints --
verified directly against this environment before being chosen, not
assumed from documentation or general reputation (the same lesson
VALIDATION.md SS13 already paid for once with constrained beam search).

Reuses eval/escalation_model_comparison.py's case-finding, profile-
reason, and verification logic directly (import, not reimplemented) so
this experiment's numbers are directly comparable to R21's -- same 22
cases, same three checks (SBERT similarity threshold, negation
consistency, a post-hoc phoneme/blocked-word leak scan). Grammar is
additionally checked with LanguageTool where available (this project's
existing, already-optional grammar-check dependency); if unavailable in
the running environment, this is reported honestly as "n/a," not
faked or skipped silently.

    DISABLE_DATAMUSE=1 DECODER_MODEL_NAME=Qwen/Qwen2.5-0.5B-Instruct \\
        python eval/escalation_model_comparison_decoder.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("DISABLE_DATAMUSE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import torch

import semantic as sem
import rephrase
import grammar
from eval.escalation_model_comparison import (
    _find_failing_sentences, _profile_reason, _verify, _build_profile,
)

ROOT = Path(__file__).resolve().parent.parent
DECODER_MODEL_NAME = os.environ.get("DECODER_MODEL_NAME", "Qwen/Qwen2.5-0.5B-Instruct")
OUT_CSV = ROOT / "eval" / f"escalation_model_comparison_decoder__{DECODER_MODEL_NAME.replace('/', '_')}.csv"

SYSTEM_PROMPT = (
    "You are a careful text editor. You rewrite a single sentence so it avoids "
    "specific words, while preserving its exact meaning and sounding natural. "
    "You output ONLY the rewritten sentence, with no explanation, no quotes, "
    "and no extra commentary."
)

_dec_tokenizer = None
_dec_model = None
_dec_load_seconds = None
_dec_param_count = None


def _load_decoder() -> None:
    global _dec_tokenizer, _dec_model, _dec_load_seconds, _dec_param_count
    if _dec_model is not None:
        return
    from transformers import AutoModelForCausalLM, AutoTokenizer
    t0 = time.time()
    _dec_tokenizer = AutoTokenizer.from_pretrained(DECODER_MODEL_NAME)
    _dec_model = AutoModelForCausalLM.from_pretrained(DECODER_MODEL_NAME)
    _dec_model.eval()
    _dec_load_seconds = time.time() - t0
    _dec_param_count = sum(p.numel() for p in _dec_model.parameters())


def _build_messages(sentence: str, flagged_words: list[str], reason: str) -> list[dict]:
    blocked_str = ", ".join(sorted(set(w.lower() for w in flagged_words)))
    user = (
        f"Rewrite this sentence so it does NOT contain any of these words: {blocked_str}. "
        f"{reason} Keep the exact same meaning and make it sound natural. "
        f"Output only the rewritten sentence.\n\nSentence: {sentence}"
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def _extract_rewrite(raw: str) -> str:
    """Decoder-only instruct models routinely add commentary even when
    told not to -- take the first non-empty line and strip surrounding
    quotes, rather than trusting the model followed the instruction
    literally."""
    text = raw.strip()
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if len(line) >= 2 and line[0] in "\"'“" and line[-1] in "\"'”":
            line = line[1:-1].strip()
        return line
    return text


def _decoder_bad_words_ids(blocked_words) -> list[list[int]] | None:
    """Same case-variant blocking logic as rephrase.py::_bad_words_ids
    (R17) / eval/escalation_model_comparison.py::_flan_bad_words_ids,
    adapted to the decoder tokenizer for the hybrid condition."""
    if _dec_tokenizer is None or not blocked_words:
        return None
    ids: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    for raw in blocked_words:
        word = str(raw or "").strip()
        if not word:
            continue
        for variant in {word, word.lower(), word.capitalize(), word.upper()}:
            for form in (variant, " " + variant):
                encoded = _dec_tokenizer.encode(form, add_special_tokens=False)
                if encoded:
                    sig = tuple(encoded)
                    if sig not in seen:
                        seen.add(sig)
                        ids.append(encoded)
    return ids or None


def _generate_with_decoder(sentence: str, flagged_words: list[str], reason: str, k: int = 5,
                            use_bad_words_ids: bool = False) -> list[str]:
    """Defaults to GREEDY decoding (num_beams=1, one candidate) --
    calibrated directly, not assumed: a timing/quality probe on this
    model found beam search (num_beams=2) took ~60s per call and k=3
    sampling took ~74s, for candidates that clustered tightly around the
    same output regardless of strategy (all still leaked the constraint).
    Beam/sampling search wasn't buying meaningfully different outcomes
    at this model's scale, only ~3x the CPU cost -- a real, disclosed
    methodological difference from the T5 experiments (beam=10-12,
    k=5), not an oversight. Set DECODER_NUM_CANDIDATES>1 to override and
    use sampling-based multi-candidate generation instead."""
    _load_decoder()
    messages = _build_messages(sentence, flagged_words, reason)
    prompt = _dec_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    encoded = _dec_tokenizer(prompt, return_tensors="pt")
    input_len = encoded["input_ids"].shape[1]
    pad_id = _dec_tokenizer.pad_token_id
    if pad_id is None:
        pad_id = _dec_tokenizer.eos_token_id
    n_candidates = int(os.environ.get("DECODER_NUM_CANDIDATES", "1"))
    if n_candidates <= 1:
        kwargs = dict(num_beams=1, do_sample=False, max_new_tokens=40,
                      no_repeat_ngram_size=3, repetition_penalty=1.3, pad_token_id=pad_id)
    else:
        kwargs = dict(num_beams=1, do_sample=True, temperature=0.7, top_p=0.9,
                      num_return_sequences=n_candidates, max_new_tokens=40,
                      no_repeat_ngram_size=3, pad_token_id=pad_id)
    if use_bad_words_ids:
        bad_ids = _decoder_bad_words_ids(flagged_words)
        if bad_ids:
            kwargs["bad_words_ids"] = bad_ids
    with torch.no_grad():
        outputs = _dec_model.generate(**encoded, **kwargs)
    seen, out = set(), []
    for o in outputs:
        raw = _dec_tokenizer.decode(o[input_len:], skip_special_tokens=True)
        text = _extract_rewrite(raw)
        if text and text.lower() not in seen:
            seen.add(text.lower())
            out.append(text)
    return out


def _grammar_issue_count(text: str) -> int | None:
    tool = grammar._get_lt_tool()
    if tool is None:
        return None
    try:
        return len(tool.check(text))
    except Exception:
        return None


def run_case(case: dict) -> dict:
    sentence = case["sentence"]
    profile = _build_profile(case["profile_name"], case["profile_spec"])
    blocked = {w.lower() for w in case["flagged_words"]}
    min_semantic = sem.MIN_SEMANTIC
    reason = _profile_reason(case["profile_spec"])

    t0 = time.time()
    base_cands = rephrase.generate_candidates(sentence, k=5, blocked_words=blocked)
    base_elapsed = time.time() - t0
    base_results = [_verify(sentence, c, profile, blocked, min_semantic) for c in base_cands]
    base_pass = [r for r in base_results if r["pass"]]
    base_best = max(base_pass, key=lambda r: r["sim"] or 0) if base_pass else \
        max(base_results, key=lambda r: r["sim"] or -1) if base_results else None
    base_best_text = base_cands[base_results.index(base_best)] if base_best and base_results else None

    t0 = time.time()
    dec_cands = _generate_with_decoder(sentence, case["flagged_words"], reason, k=5, use_bad_words_ids=False)
    dec_elapsed = time.time() - t0
    dec_results = [_verify(sentence, c, profile, blocked, min_semantic) for c in dec_cands]
    dec_pass = [r for r in dec_results if r["pass"]]
    dec_best = max(dec_pass, key=lambda r: r["sim"] or 0) if dec_pass else \
        max(dec_results, key=lambda r: r["sim"] or -1) if dec_results else None
    dec_best_text = dec_cands[dec_results.index(dec_best)] if dec_best and dec_results else None

    t0 = time.time()
    hyb_cands = _generate_with_decoder(sentence, case["flagged_words"], reason, k=5, use_bad_words_ids=True)
    hyb_elapsed = time.time() - t0
    hyb_results = [_verify(sentence, c, profile, blocked, min_semantic) for c in hyb_cands]
    hyb_pass = [r for r in hyb_results if r["pass"]]
    hyb_best = max(hyb_pass, key=lambda r: r["sim"] or 0) if hyb_pass else \
        max(hyb_results, key=lambda r: r["sim"] or -1) if hyb_results else None
    hyb_best_text = hyb_cands[hyb_results.index(hyb_best)] if hyb_best and hyb_results else None

    return {
        "profile": case["profile_name"],
        "sentence": sentence,
        "flagged_words": ";".join(sorted(blocked)),
        "baseline_pass": bool(base_pass),
        "baseline_best_text": base_best_text,
        "baseline_best_sim": round(base_best["sim"], 4) if base_best and base_best["sim"] is not None else None,
        "baseline_best_reason": base_best["reason"] if base_best else "no_candidates",
        "baseline_seconds": round(base_elapsed, 2),
        "decoder_pass": bool(dec_pass),
        "decoder_best_text": dec_best_text,
        "decoder_best_sim": round(dec_best["sim"], 4) if dec_best and dec_best["sim"] is not None else None,
        "decoder_best_reason": dec_best["reason"] if dec_best else "no_candidates",
        "decoder_grammar_issues": _grammar_issue_count(dec_best_text) if dec_best_text else None,
        "decoder_seconds": round(dec_elapsed, 2),
        "hybrid_pass": bool(hyb_pass),
        "hybrid_best_text": hyb_best_text,
        "hybrid_best_sim": round(hyb_best["sim"], 4) if hyb_best and hyb_best["sim"] is not None else None,
        "hybrid_best_reason": hyb_best["reason"] if hyb_best else "no_candidates",
        "hybrid_grammar_issues": _grammar_issue_count(hyb_best_text) if hyb_best_text else None,
        "hybrid_seconds": round(hyb_elapsed, 2),
    }


def main() -> int:
    import psutil
    proc = psutil.Process(os.getpid())
    rss_before = proc.memory_info().rss

    sem.load_sbert()
    cases = _find_failing_sentences()
    print(f"{len(cases)} failing sentences found (escalation triggered and failed in production)")

    limit = os.environ.get("LIMIT_CASES")
    if limit:
        n = int(limit)
        step = max(1, len(cases) // n)
        cases = cases[::step][:n]
        print(f"LIMIT_CASES set -- using a stratified sample of {len(cases)} cases")
    print(f"Decoder model: {DECODER_MODEL_NAME}\n")

    _load_decoder()
    rss_after_load = proc.memory_info().rss
    print(f"Decoder loaded in {_dec_load_seconds:.1f}s, params={_dec_param_count/1e6:.1f}M, "
          f"RSS delta from load: {(rss_after_load - rss_before) / 1e6:.0f}MB\n")

    rows = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['profile_name']}: {case['sentence'][:70]}")
        row = run_case(case)
        rows.append(row)
        print(f"    baseline: pass={row['baseline_pass']} sim={row['baseline_best_sim']} "
              f"({row['baseline_seconds']}s)  |  decoder: pass={row['decoder_pass']} "
              f"sim={row['decoder_best_sim']} gram={row['decoder_grammar_issues']} "
              f"({row['decoder_seconds']}s)  |  hybrid: pass={row['hybrid_pass']} "
              f"sim={row['hybrid_best_sim']} gram={row['hybrid_grammar_issues']} ({row['hybrid_seconds']}s)")

    import csv
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwrote {len(rows)} rows to {OUT_CSV}")

    n = len(rows)
    for label, key_pass, key_sim, key_sec in [
        ("Baseline", "baseline_pass", "baseline_best_sim", "baseline_seconds"),
        (f"{DECODER_MODEL_NAME} + reason (no bad_words_ids)", "decoder_pass", "decoder_best_sim", "decoder_seconds"),
        (f"{DECODER_MODEL_NAME} + reason + bad_words_ids (hybrid)", "hybrid_pass", "hybrid_best_sim", "hybrid_seconds"),
    ]:
        passed = sum(1 for r in rows if r[key_pass])
        sims = [r[key_sim] for r in rows if r[key_sim] is not None]
        secs = sum(r[key_sec] for r in rows)
        avg_sim = sum(sims) / len(sims) if sims else float("nan")
        print(f"{label}: {passed}/{n} passed ({passed/n:.1%}), avg sim {avg_sim:.4f}, "
              f"total {secs:.1f}s, avg {secs/n:.2f}s/case")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
