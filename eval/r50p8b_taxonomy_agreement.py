"""eval/r50p8b_taxonomy_agreement.py -- R50 Phase 8B, task 2: does a
strict, ordered 3-step decision procedure (GRAMMAR -> WRONG_WORD_OR_SENSE
-> NATURALNESS_OR_REGISTER) let an independent rater reproduce the
primary rater's original labels, on the specific pool where Phase 8's
second-rater study found poor agreement (25%/33%)?"""
import json
from collections import Counter
from pathlib import Path

EVAL = Path(__file__).parent
truth = json.load(open(EVAL / "r50_dataset" / "phase8b_taxonomy_truth.json", encoding="utf-8"))
third = json.load(open(EVAL / "r50_dataset" / "phase8b_taxonomy_secondrater_results.json", encoding="utf-8"))

n = len(truth)
agree = 0
rows = []
for uid, t in truth.items():
    r = third[uid]
    t_prim = t["human_defect_labels"]["primary"]
    r_cat = r["category"]
    a = (t_prim == r_cat)
    agree += a
    rows.append((uid, t_prim, r_cat, a))

print(f"n = {n}")
print(f"Exact agreement with refined 3-step procedure: {agree}/{n} = {agree/n:.0%}")

by_class = Counter()
by_class_total = Counter()
for uid, t_prim, r_cat, a in rows:
    by_class_total[t_prim] += 1
    if a:
        by_class[t_prim] += 1
print("\nBy original class:")
for cls, total in by_class_total.items():
    print(f"  {cls}: {by_class.get(cls,0)}/{total} = {by_class.get(cls,0)/total:.0%}")

print("\nDisagreements:")
for uid, t_prim, r_cat, a in rows:
    if not a:
        print(f"  {uid}: primary={t_prim}  third-rater(refined proc.)={r_cat}")

with open(EVAL / "r50_dataset" / "phase8b_taxonomy_agreement_summary.json", "w", encoding="utf-8") as f:
    json.dump({"n": n, "agreement": agree / n, "by_class": {k: by_class.get(k,0)/v for k,v in by_class_total.items()}}, f, indent=2)
print("\nwrote eval/r50_dataset/phase8b_taxonomy_agreement_summary.json")
