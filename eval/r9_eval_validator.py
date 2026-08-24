"""
eval/r9_eval_validator.py -- Phase 9, step 4: evaluate the fine-tuned
validator prototype on the frozen test set, compare against the
baselines from r9_baseline_eval.py, and answer the three gate
questions: does it beat the existing stack, does it generalize (not just
memorize training word-pairs), and what's the precision/coverage
tradeoff. Also stratifies FACTUAL_OR_LOGICAL_REVERSAL results by
evidence_quality per the "directional/low-confidence" caveat.

RESEARCH ONLY. Does not touch reformulate.py or app.py.
"""
import json
from pathlib import Path
from sentence_transformers import CrossEncoder

EVAL = Path(__file__).parent
MODEL_PATH = EVAL / "r9_validator_model" / "final"

data = json.load(open(EVAL / "r50_dataset" / "r9_final_dataset.json", encoding="utf-8"))
by_uid = {r["uid"]: r for r in data["records"]}
split = json.load(open(EVAL / "r50_dataset" / "r9_split.json", encoding="utf-8"))
test_uids = split["test_uids"]
train_dedup_keys = set()
for u in split["train_uids"] + split["val_uids"]:
    train_dedup_keys.add(by_uid[u]["dedup_key"])

model = CrossEncoder(str(MODEL_PATH))
pairs = [[by_uid[u]["original_text"], by_uid[u]["reformulated_text"]] for u in test_uids]
scores = model.predict(pairs, apply_softmax=False)

def prf(preds, truths, positive="DEFECTIVE"):
    tp = sum(1 for p, t in zip(preds, truths) if p == positive and t == positive)
    fp = sum(1 for p, t in zip(preds, truths) if p == positive and t != positive)
    fn = sum(1 for p, t in zip(preds, truths) if p != positive and t == positive)
    tn = sum(1 for p, t in zip(preds, truths) if p != positive and t != positive)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    acc = (tp + tn) / len(preds)
    clean_recall = tn / (tn + fp) if (tn + fp) else 0.0
    return {"precision": prec, "recall": rec, "f1": f1, "accuracy": acc,
            "clean_recall": clean_recall, "tp": tp, "fp": fp, "fn": fn, "tn": tn}

truths = [by_uid[u]["acceptability"] for u in test_uids]

import torch
sig_scores = torch.sigmoid(torch.tensor(scores)).tolist()  # P(CLEAN)
print("Raw sigmoid(P(CLEAN)) score distribution:")
for u, s, t in zip(test_uids, sig_scores, truths):
    print(f"  {u}: P(CLEAN)={s:.3f}  truth={t}")

print("\n--- Threshold sweep (predict CLEAN if P(CLEAN) >= threshold) ---")
best = None
for thresh in [0.9, 0.7, 0.5, 0.3, 0.1]:
    preds = ["CLEAN" if s >= thresh else "DEFECTIVE" for s in sig_scores]
    r = prf(preds, truths)
    print(f"  thresh={thresh}: acc={r['accuracy']:.2f} defect_recall={r['recall']:.2f} "
          f"defect_prec={r['precision']:.2f} clean_recall={r['clean_recall']:.2f} f1={r['f1']:.2f}")
    if best is None or r["f1"] > best[1]["f1"]:
        best = (thresh, r)

print(f"\nBest-F1 threshold: {best[0]} -> {best[1]}")

# generalization check: how many test dedup_keys share a word-pair with train?
n_unseen_wordpair = sum(1 for u in test_uids if by_uid[u]["dedup_key"] not in train_dedup_keys)
print(f"\nTest records with a dedup_key NEVER seen in train/val (true generalization check): {n_unseen_wordpair}/{len(test_uids)}")

preds_at_best = ["CLEAN" if s >= best[0] else "DEFECTIVE" for s in sig_scores]
unseen_preds = [p for u, p in zip(test_uids, preds_at_best) if by_uid[u]["dedup_key"] not in train_dedup_keys]
unseen_truths = [t for u, t in zip(test_uids, truths) if by_uid[u]["dedup_key"] not in train_dedup_keys]
if unseen_truths:
    print("Performance on UNSEEN-word-pair subset only:", prf(unseen_preds, unseen_truths))

# FACTUAL_OR_LOGICAL_REVERSAL, stratified by evidence quality
print("\n--- FACTUAL_OR_LOGICAL_REVERSAL test cases, by evidence_quality ---")
for u, s, t in zip(test_uids, sig_scores, truths):
    r = by_uid[u]
    if r["primary_defect_for_analysis"] == "FACTUAL_OR_LOGICAL_REVERSAL":
        pred = "CLEAN" if s >= best[0] else "DEFECTIVE"
        print(f"  {u} [{r['evidence_quality']}]: truth={t} pred={pred} P(CLEAN)={s:.3f}")

with open(EVAL / "r50_dataset" / "r9_eval_results.json", "w", encoding="utf-8") as f:
    json.dump({
        "best_threshold": best[0],
        "best_result": best[1],
        "n_unseen_wordpair": n_unseen_wordpair,
        "n_test": len(test_uids),
        "per_record": [{"uid": u, "p_clean": s, "truth": t, "pred": ("CLEAN" if s >= best[0] else "DEFECTIVE")}
                        for u, s, t in zip(test_uids, sig_scores, truths)],
    }, f, indent=2)
print("\nwrote eval/r50_dataset/r9_eval_results.json")
