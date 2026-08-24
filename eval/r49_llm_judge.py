"""
eval/r49_llm_judge.py — cheap lever #2 (per the user's own framing after
R48): a prompted, locally-run instruction-tuned LLM as a fact/meaning-
preservation JUDGE, not a generator. R14/R23 already found Qwen2.5 poor
at *generating* paraphrases (VALIDATION.md §14) -- judging a given pair
is a structurally different, generally easier task, and hasn't been
tested. Reuses the exact same, already-downloaded, already-proven-to-
load-without-trust_remote_code models from that pass
(Qwen2.5-0.5B/1.5B-Instruct) -- no new dependency, no API call (this
project's own standing rule, REFORMULATION_RESEARCH.md SS15, against any
API-based frontier LLM as a default path -- unaffected by this, since
this stays fully local).

Targets specifically the two defect classes VALIDATION.md SS38.3 found
nothing in the current pipeline can see: wrong-word substitution
("replaced"->"displaced") and factual/physical-claim reversal
("into space"->"into the atmosphere"). Tested against those PLUS known-
good cases from R48's own 12 final successes, to check false-positive
risk before trusting anything -- same discipline as every other signal
validated in this project.

Diagnostic only. Does not modify reformulate.py/semantic.py.

Run:
    python eval/r49_llm_judge.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "eval" / "r49_llm_judge_results.json"

SYSTEM_PROMPT = (
    "You are a careful fact-checker comparing two sentences. Given an ORIGINAL "
    "sentence and a REWRITTEN version, decide whether the REWRITTEN sentence "
    "preserves the same specific facts, claims, and word meanings as the "
    "ORIGINAL -- not just the same topic or fluent grammar. Pay close attention "
    "to word substitutions that quietly change a specific meaning (for example "
    "'replaced' vs 'displaced'), and to claims that get reversed or altered in "
    "direction, magnitude, or category (for example something moving into space "
    "vs into the atmosphere are very different claims)."
)

# (label, original, candidate, expected) -- known-bad (the two blind-spot
# cases) and known-good (from R48's own 12 final successes) mixed together.
CASES: list[tuple[str, str, str, str]] = [
    ("BAD: replaced->displaced",
     "Deforestation is the main land use change contributor to global warming, as the destroyed trees release carbon dioxide, and are not replaced by new trees.",
     "Deforestation is the main contributor to the global warming of land use change, as the destroyed trees emit carbon dioxide and are not displaced by new trees.",
     "NO"),
    ("BAD: space->atmosphere",
     "The upper atmosphere is cooling, because greenhouse gases are trapping heat near the Earth's surface, and so less heat is radiating into space.",
     "The upper atmosphere is cooling, because greenhouse gases are trapping heat near the Earth's top and thus less heat is emitted into the atmosphere.",
     "NO"),
    ("BAD (cross-check): rational->irrational",
     "A rational agent has goals or preferences and take actions to make them happen.",
     "An irrational agent has goals or wants and takes actions to make them happen.",
     "NO"),
    ("GOOD: issues/develop",
     "Many of these algorithms were insufficient for solving large reasoning problems because they experienced a combinatorial explosion, meaning they become exponentially slower as the problems grow.",
     "Many of these algorithms were insufficient for solving large reasoning issues because they experienced a combinatorial explosion, meaning that they become exponentially slower as the issues develop.",
     "YES"),
    ("GOOD: starch->cornstarch",
     "Long-chain sugars such as starch tends to break down into more digestible simpler sugars.",
     "Long-chain sugars like cornstarch tend to break down into more digestible sugars.",
     "YES"),
    ("GOOD: attain/cooking",
     "Fats can reach temperatures above the boiling point of water and is often used to transfer high heat to other ingredients, such as in frying or sauteing.",
     "Fats can attain temperatures above the boiling point of water and is often used to transfer high heat to other ingredients, like in frying or cooking.",
     "YES"),
    ("GOOD: networks/analyzing",
     "Artificial intelligence (AI) is the capability of computational systems to perform tasks typically associated with human intelligence, such as learning, reasoning, problem-solving, perception, and decision-making.",
     "Artificial Intelligence (AI) is the capability of computational networks to perform tasks typically associated with human intelligence, including learning, analyzing, problem-solving, perception and decision-making.",
     "YES"),
    ("BAD (known, R40): pre-industrial->palaeolithic",
     "The 2016 to 2025 decade warmed to an average of 1.26 degrees compared to the pre-industrial baseline.",
     "The 2016 to 2025 decade warmed to an average of 1.26 degrees compared to the palaeolithic baseline.",
     "NO"),
]

MODELS = ["Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct"]


def judge(model, tokenizer, original: str, candidate: str) -> tuple[str, float]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"ORIGINAL: {original}\nREWRITTEN: {candidate}\n\n"
                                     f"Does the REWRITTEN sentence preserve the same specific facts and "
                                     f"meaning as the ORIGINAL? Answer with exactly one word first, YES or "
                                     f"NO, then a brief one-sentence reason."}
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    encoded = tokenizer(prompt, return_tensors="pt")
    t0 = time.perf_counter()
    with torch.no_grad():
        out = model.generate(
            **encoded, max_new_tokens=60, do_sample=False,
            no_repeat_ngram_size=3, repetition_penalty=1.3,
            pad_token_id=tokenizer.eos_token_id,
        )
    elapsed = time.perf_counter() - t0
    text = tokenizer.decode(out[0][encoded["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    return text, elapsed


def main() -> int:
    all_results = {}
    for model_name in MODELS:
        print(f"\n=== {model_name} ===", flush=True)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        model.eval()

        rows = []
        for label, orig, cand, expected in CASES:
            verdict, elapsed = judge(model, tokenizer, orig, cand)
            verdict_word = verdict.strip().split()[0].upper().rstrip(".,:;") if verdict.strip() else "?"
            correct = verdict_word == expected
            rows.append({
                "label": label, "expected": expected, "verdict_raw": verdict,
                "verdict_word": verdict_word, "correct": correct, "seconds": round(elapsed, 2),
            })
            print(f"  [{label}] expected={expected} got={verdict_word} "
                  f"{'OK' if correct else 'WRONG'} ({elapsed:.1f}s)\n    -> {verdict[:150]}", flush=True)

        n_correct = sum(1 for r in rows if r["correct"])
        print(f"  accuracy: {n_correct}/{len(rows)}")
        all_results[model_name] = rows

    OUT_PATH.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote results to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
