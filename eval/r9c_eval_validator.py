"""
eval/r9b_eval_validator.py -- Phase 9B, step 5: evaluate the retrained
validator on the SAME frozen test set as R9 (unchanged), compare against
the SAME baseline numbers already computed in R9
(r9_baseline_eval_summary.json, unchanged), and check generalization on
word-pairs never seen in train/val. Prioritizes CLEAN retention, defect
precision, and defect recall over raw accuracy, per instruction.

RESEARCH ONLY. Does not touch reformulate.py or app.py.
"""
import json
from pathlib import Path
from sentence_transformers import CrossEncoder
import torch

EVAL = Path(__file__).parent
MODEL_PATH = EVAL / "r9c_validator_model" / "final"

data = json.load(open(EVAL / "r50_dataset" / "r9_final_dataset.json", encoding="utf-8"))
by_uid = {r["uid"]: r for r in data["records"]}
split = json.load(open(EVAL / "r50_dataset" / "r9_split.json", encoding="utf-8"))
test_uids = split["test_uids"]
train_dedup_keys = {by_uid[u]["dedup_key"] for u in split["train_uids"] + split["val_uids"]}

model = CrossEncoder(str(MODEL_PATH))
pairs = [[by_uid[u]["original_text"], by_uid[u]["reformulated_text"]] for u in test_uids]
scores = model.predict(pairs, apply_softmax=False)
sig_scores = torch.sigmoid(torch.tensor(scores)).tolist()

# Threshold selection MUST happen on val, not test (test-set leakage otherwise).
val_uids = split["val_uids"]
val_pairs = [[by_uid[u]["original_text"], by_uid[u]["reformulated_text"]] for u in val_uids]
val_scores = model.predict(val_pairs, apply_softmax=False)
val_sig_scores = torch.sigmoid(torch.tensor(val_scores)).tolist()
val_truths = [by_uid[u]["acceptability"] for u in val_uids]

n_finite = sum(1 for s in sig_scores if s == s)  # nan != nan
print(f"Finite scores: {n_finite}/{len(sig_scores)}")
if n_finite < len(sig_scores):
    print("WARNING: some test-set scores are non-finite -- model did not fully recover.")

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

print("\nRaw sigmoid(P(CLEAN)) score distribution:")
for u, s, t in zip(test_uids, sig_scores, truths):
    print(f"  {u}: P(CLEAN)={s:.3f}  truth={t}")

print("\n--- Threshold selection on VAL set only (test set never touched for this) ---")
print("(NOTE: scores are compressed into a narrow band -- a coarse 0.9/0.7/0.5/0.3/0.1 "
      "grid misses all real operating points; sweeping finely across the observed VAL range instead.)")
val_results_by_thresh = {}
finite_val_scores = sorted(set(round(s, 4) for s in val_sig_scores if s == s))
if finite_val_scores:
    lo, hi = finite_val_scores[0], finite_val_scores[-1]
    span = hi - lo
    fine_grid = [round(lo + span * i / 60, 4) for i in range(61)] if span > 0 else [lo]
else:
    fine_grid = [0.5]
for thresh in fine_grid:
    preds = ["CLEAN" if (s == s and s >= thresh) else "DEFECTIVE" for s in val_sig_scores]
    val_results_by_thresh[thresh] = prf(preds, val_truths)

baselines = json.load(open(EVAL / "r50_dataset" / "r9_baseline_eval_summary.json", encoding="utf-8"))
combo = baselines["sbert095_or_nli_or_grammar"]
combo["clean_recall"] = combo["tn"] / (combo["tn"] + combo["fp"]) if (combo["tn"] + combo["fp"]) else 0.0

# Select thresholds on VAL ONLY (test never consulted for this):
# (a) pure lexicographic priority per instruction: clean_recall, then defect precision, then defect recall
lex_thresh = max(val_results_by_thresh, key=lambda t: (
    val_results_by_thresh[t]["clean_recall"], val_results_by_thresh[t]["precision"], val_results_by_thresh[t]["recall"]))

# (b) the val threshold that beats the baseline on ALL THREE prioritized metrics simultaneously, if any exists
beats_all_three = [t for t, r in val_results_by_thresh.items()
                    if r["clean_recall"] >= combo["clean_recall"]
                    and r["precision"] >= combo["precision"]
                    and r["recall"] >= combo["recall"]]
balanced_thresh = max(beats_all_three, key=lambda t: val_results_by_thresh[t]["recall"]) if beats_all_three else None

print(f"\n(a) Pure lexicographic best on VAL (clean_recall, then defect_precision, then defect_recall): "
      f"thresh={lex_thresh} -> {val_results_by_thresh[lex_thresh]}")
if balanced_thresh:
    print(f"(b) Best VAL threshold beating baseline on ALL THREE metrics simultaneously: "
          f"thresh={balanced_thresh} -> {val_results_by_thresh[balanced_thresh]}")
else:
    print("(b) No single VAL threshold beats the baseline on all three metrics simultaneously.")

best_thresh = balanced_thresh if balanced_thresh else lex_thresh
print(f"\nSelected threshold (from VAL only): {best_thresh}. Applying ONCE to test set below.")

# NOW apply the val-selected threshold(s) to TEST, a single time each.
lex_test = prf(["CLEAN" if (s == s and s >= lex_thresh) else "DEFECTIVE" for s in sig_scores], truths)
balanced_test = prf(["CLEAN" if (s == s and s >= balanced_thresh) else "DEFECTIVE" for s in sig_scores], truths) if balanced_thresh else None
best = balanced_test if balanced_test else lex_test

print("\n--- TEST SET results at the VAL-selected threshold(s), vs. R9's best baseline (unchanged) ---")
print(f"  Baseline:                  defect_recall={combo['recall']:.2f} defect_prec={combo['precision']:.2f} "
      f"clean_recall={combo['clean_recall']:.2f} acc={combo['accuracy']:.2f}")
print(f"  Learned (lex-thresh={lex_thresh}):    defect_recall={lex_test['recall']:.2f} defect_prec={lex_test['precision']:.2f} "
      f"clean_recall={lex_test['clean_recall']:.2f} acc={lex_test['accuracy']:.2f}")
if balanced_test:
    print(f"  Learned (balanced-thresh={balanced_thresh}): defect_recall={balanced_test['recall']:.2f} defect_prec={balanced_test['precision']:.2f} "
          f"clean_recall={balanced_test['clean_recall']:.2f} acc={balanced_test['accuracy']:.2f}")

n_unseen = sum(1 for u in test_uids if by_uid[u]["dedup_key"] not in train_dedup_keys)
print(f"\nTest records with a dedup_key never seen in train/val: {n_unseen}/{len(test_uids)}")
preds_at_best = ["CLEAN" if (s == s and s >= best_thresh) else "DEFECTIVE" for s in sig_scores]
unseen_preds = [p for u, p in zip(test_uids, preds_at_best) if by_uid[u]["dedup_key"] not in train_dedup_keys]
unseen_truths = [t for u, t in zip(test_uids, truths) if by_uid[u]["dedup_key"] not in train_dedup_keys]
if unseen_truths:
    print("Performance on UNSEEN-word-pair subset only:", prf(unseen_preds, unseen_truths))

print("\n--- FACTUAL_OR_LOGICAL_REVERSAL test cases, by evidence_quality ---")
for u, s, t in zip(test_uids, sig_scores, truths):
    r = by_uid[u]
    if r["primary_defect_for_analysis"] == "FACTUAL_OR_LOGICAL_REVERSAL":
        pred = "CLEAN" if (s == s and s >= best_thresh) else "DEFECTIVE"
        print(f"  {u} [{r['evidence_quality']}]: truth={t} pred={pred} P(CLEAN)={s:.3f}")

with open(EVAL / "r50_dataset" / "r9c_eval_results.json", "w", encoding="utf-8") as f:
    json.dump({
        "n_finite": n_finite, "n_test": len(test_uids),
        "val_results_by_threshold": {str(k): v for k, v in val_results_by_thresh.items()},
        "lex_threshold": lex_thresh, "lex_test_result": lex_test,
        "balanced_threshold": balanced_thresh, "balanced_test_result": balanced_test,
        "selected_threshold": best_thresh, "selected_test_result": best,
        "baseline_comparison": combo,
        "n_unseen_wordpair": n_unseen,
        "per_record": [{"uid": u, "p_clean": s, "truth": t} for u, s, t in zip(test_uids, sig_scores, truths)],
        "per_val_record": [{"uid": u, "p_clean": s, "truth": t} for u, s, t in zip(val_uids, val_sig_scores, val_truths)],
    }, f, indent=2)
print("\nwrote eval/r50_dataset/r9c_eval_results.json")
