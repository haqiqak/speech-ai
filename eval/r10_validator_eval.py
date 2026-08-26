"""
eval/r10_validator_eval.py -- Phase 10, step 16: run the frozen Phase
9B/9C validator checkpoints on this corpus's reformulated pairs. No
retraining, no threshold changes -- reuse the val-selected thresholds
exactly as reported in r9b/r9c_eval_results.json. This corpus is
disjoint from R40-Phase 8B (what Phase 9's train/val/test was built
from), so this is a genuine generalization test.

RESEARCH ONLY.
"""
import json
from pathlib import Path
from sentence_transformers import CrossEncoder
import torch

EVAL = Path(__file__).parent

# thresholds selected on Phase 9's OWN validation set, reused as-is (no new tuning)
R9B_THRESHOLD = json.load(open(EVAL / "r50_dataset" / "r9b_eval_results.json", encoding="utf-8"))["balanced_threshold"]
R9C_THRESHOLD = json.load(open(EVAL / "r50_dataset" / "r9c_eval_results.json", encoding="utf-8"))["balanced_threshold"]
print(f"Reusing thresholds: 9B={R9B_THRESHOLD}, 9C={R9C_THRESHOLD}")

raw = json.load(open(EVAL / "r10_raw_results.json", encoding="utf-8"))
rows = [r for r in raw["results"] if r["status"] == "reformulated"]
pairs = [[r["original_text"], r["reformulated_text"]] for r in rows]

model_b = CrossEncoder(str(EVAL / "r9b_validator_model" / "final"))
scores_b = torch.sigmoid(torch.tensor(model_b.predict(pairs, apply_softmax=False))).tolist()

model_c = CrossEncoder(str(EVAL / "r9c_validator_model" / "final"))
scores_c = torch.sigmoid(torch.tensor(model_c.predict(pairs, apply_softmax=False))).tolist()

n_finite_b = sum(1 for s in scores_b if s == s)
n_finite_c = sum(1 for s in scores_c if s == s)
print(f"Finite scores: 9B={n_finite_b}/{len(scores_b)}, 9C={n_finite_c}/{len(scores_c)}")

out = []
for r, sb, sc in zip(rows, scores_b, scores_c):
    out.append({
        "run_id": r["run_id"],
        "original_text": r["original_text"],
        "reformulated_text": r["reformulated_text"],
        "p_clean_9b": sb,
        "pred_9b": "CLEAN" if (sb == sb and sb >= R9B_THRESHOLD) else "DEFECTIVE",
        "p_clean_9c": sc,
        "pred_9c": "CLEAN" if (sc == sc and sc >= R9C_THRESHOLD) else "DEFECTIVE",
    })

with open(EVAL / "r10_validator_predictions.json", "w", encoding="utf-8") as f:
    json.dump({"r9b_threshold": R9B_THRESHOLD, "r9c_threshold": R9C_THRESHOLD, "predictions": out}, f, indent=2)

from collections import Counter
print("9B predictions:", Counter(o["pred_9b"] for o in out))
print("9C predictions:", Counter(o["pred_9c"] for o in out))
agree = sum(1 for o in out if o["pred_9b"] == o["pred_9c"])
print(f"9B/9C agreement on this new corpus: {agree}/{len(out)} = {agree/len(out):.0%}")
print(f"\nwrote eval/r10_validator_predictions.json ({len(out)} rows)")
