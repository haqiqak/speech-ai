"""eval/r9_baseline_eval.py -- Phase 9, step 2b: evaluate baseline rules
against the human labels on the test set. Establishes the floor a
learned validator must beat."""
import json
from pathlib import Path

EVAL = Path(__file__).parent
sigs = json.load(open(EVAL / "r50_dataset" / "r9_baseline_signals.json", encoding="utf-8"))
n = len(sigs)
print(f"n = {n}")

def prf(preds, truths, positive="DEFECTIVE"):
    tp = sum(1 for p, t in zip(preds, truths) if p == positive and t == positive)
    fp = sum(1 for p, t in zip(preds, truths) if p == positive and t != positive)
    fn = sum(1 for p, t in zip(preds, truths) if p != positive and t == positive)
    tn = sum(1 for p, t in zip(preds, truths) if p != positive and t != positive)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    acc = (tp + tn) / len(preds)
    return {"precision": prec, "recall": rec, "f1": f1, "accuracy": acc, "tp": tp, "fp": fp, "fn": fn, "tn": tn}

truths = [s["acceptability"] for s in sigs]

print("\n--- Trivial baseline: reject everything (predict DEFECTIVE always) ---")
preds = ["DEFECTIVE"] * n
print(prf(preds, truths))

print("\n--- Trivial baseline: accept everything (predict CLEAN always) ---")
preds = ["CLEAN"] * n
print(prf(preds, truths))

print("\n--- NLI contradiction only ---")
preds = ["DEFECTIVE" if s["nli_contradiction"] else "CLEAN" for s in sigs]
print(prf(preds, truths))

print("\n--- Grammar issues > 0 only ---")
preds = ["DEFECTIVE" if (s["grammar_issues"] or 0) > 0 else "CLEAN" for s in sigs]
print(prf(preds, truths))

print("\n--- NLI OR grammar (existing production-style combined gate) ---")
preds = ["DEFECTIVE" if (s["nli_contradiction"] or (s["grammar_issues"] or 0) > 0) else "CLEAN" for s in sigs]
print(prf(preds, truths))

print("\n--- SBERT threshold sweep (below threshold = DEFECTIVE) ---")
for thresh in [0.99, 0.97, 0.95, 0.93, 0.90, 0.85, 0.80]:
    preds = ["DEFECTIVE" if (s["sbert"] or 1.0) < thresh else "CLEAN" for s in sigs]
    r = prf(preds, truths)
    print(f"  thresh={thresh}: acc={r['accuracy']:.2f} prec={r['precision']:.2f} rec={r['recall']:.2f} f1={r['f1']:.2f}")

print("\n--- SBERT<0.95 OR NLI OR grammar (best simple combo) ---")
preds = ["DEFECTIVE" if ((s["sbert"] or 1.0) < 0.95 or s["nli_contradiction"] or (s["grammar_issues"] or 0) > 0) else "CLEAN" for s in sigs]
print(prf(preds, truths))

with open(EVAL / "r50_dataset" / "r9_baseline_eval_summary.json", "w", encoding="utf-8") as f:
    combo_preds = ["DEFECTIVE" if ((s["sbert"] or 1.0) < 0.95 or s["nli_contradiction"] or (s["grammar_issues"] or 0) > 0) else "CLEAN" for s in sigs]
    nli_gram_preds = ["DEFECTIVE" if (s["nli_contradiction"] or (s["grammar_issues"] or 0) > 0) else "CLEAN" for s in sigs]
    json.dump({
        "n": n,
        "reject_everything": prf(["DEFECTIVE"] * n, truths),
        "nli_or_grammar": prf(nli_gram_preds, truths),
        "sbert095_or_nli_or_grammar": prf(combo_preds, truths),
    }, f, indent=2)
print("\nwrote eval/r50_dataset/r9_baseline_eval_summary.json")
