"""
eval/r49_llm_judge_reasonfirst.py - quick follow-up to r49_llm_judge.py:
the 1.5B model's own reasoning for the palaeolithic case correctly named
the discrepancy but still answered YES - a verdict-before-reasoning
prompt-order artifact, not necessarily a capability ceiling. Tests
reasoning-first (explain, then answer) on the same 8 cases, 1.5B only.

Run:
    python eval/r49_llm_judge_reasonfirst.py
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: F401
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r49_llm_judge import CASES, SYSTEM_PROMPT  # noqa: E402

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

def judge(model, tokenizer, original, candidate):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"ORIGINAL: {original}\nREWRITTEN: {candidate}\n\n"
                                     f"First, in one or two sentences, explain what (if anything) is "
                                     f"different in meaning between the two. Then, on a new final line, "
                                     f"write exactly one word: YES if meaning was preserved, NO if not."}
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    encoded = tokenizer(prompt, return_tensors="pt")
    t0 = time.perf_counter()
    with torch.no_grad():
        out = model.generate(**encoded, max_new_tokens=100, do_sample=False,
                              no_repeat_ngram_size=3, repetition_penalty=1.3,
                              pad_token_id=tokenizer.eos_token_id)
    elapsed = time.perf_counter() - t0
    text = tokenizer.decode(out[0][encoded["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    return text, elapsed

def main():
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(MODEL)
    model.eval()
    rows = []
    for label, orig, cand, expected in CASES:
        verdict, elapsed = judge(model, tokenizer, orig, cand)
        lines = [l.strip() for l in verdict.strip().splitlines() if l.strip()]
        last_line = lines[-1].upper() if lines else ""
        verdict_word = "YES" if "YES" in last_line and "NO" not in last_line else ("NO" if "NO" in last_line else "?")
        correct = verdict_word == expected
        rows.append({"label": label, "expected": expected, "verdict_raw": verdict,
                      "verdict_word": verdict_word, "correct": correct, "seconds": round(elapsed, 2)})
        print(f"  [{label}] expected={expected} got={verdict_word} {'OK' if correct else 'WRONG'} ({elapsed:.1f}s)")
        print(f"    -> {verdict[:250]}")
    n_correct = sum(1 for r in rows if r["correct"])
    print(f"\naccuracy (reasoning-first): {n_correct}/{len(rows)}  (verdict-first was 5/8)")
    json.dump(rows, open("eval/r49_llm_judge_reasonfirst_results.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)

if __name__ == "__main__":
    raise SystemExit(main())
