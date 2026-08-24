"""
eval/r9_make_split.py -- Phase 9, step 1b: build ONE unified leakage-safe
train/val/test split over the final combined dataset (r9_final_dataset.json).

Respects the prior FROZEN splits (eval/r50_dataset/split.json,
phase8_split.json) for any dedup group that already existed there -- a
group assigned to R50's or Phase 8's frozen TEST set stays in test now;
this is the first time those frozen sets are actually consumed for their
reserved purpose (a strict held-out evaluation), not a violation of
"never touched for tuning". Phase 8B's new groups (never previously
split) are assigned fresh, stratified by acceptability + primary_defect,
deterministic (sorted, no RNG).
"""
import json
from collections import defaultdict
from pathlib import Path

EVAL = Path(__file__).parent

data = json.load(open(EVAL / "r50_dataset" / "r9_final_dataset.json", encoding="utf-8"))
records = data["records"]

r50_split = json.load(open(EVAL / "r50_dataset" / "split.json", encoding="utf-8"))
p8_split = json.load(open(EVAL / "r50_dataset" / "phase8_split.json", encoding="utf-8"))

uid_to_prior_split = {}
for u in r50_split["test_uids"]:
    uid_to_prior_split[u] = "test"
for u in r50_split["val_uids"]:
    uid_to_prior_split[u] = "val"
for u in r50_split["train_uids"]:
    uid_to_prior_split[u] = "train"
for u in p8_split["test_uids"]:
    uid_to_prior_split[u] = "test"
for u in p8_split["val_uids"]:
    uid_to_prior_split[u] = "val"
for u in p8_split["train_uids"]:
    uid_to_prior_split[u] = "train"

groups = defaultdict(list)
for r in records:
    groups[r["dedup_key"]].append(r)

group_prior_split = {}
group_new = {}
for k, members in groups.items():
    prior_votes = {uid_to_prior_split[m["uid"]] for m in members if m["uid"] in uid_to_prior_split}
    if prior_votes:
        # a group should never have been split across train/test before;
        # if it somehow has multiple votes, prefer test (safer: don't leak)
        group_prior_split[k] = "test" if "test" in prior_votes else ("val" if "val" in prior_votes else "train")
    else:
        group_new[k] = members

# stratify the NEW (Phase 8B) groups by (acceptability, primary_defect_for_analysis) of the group's worst/representative member
def rep_of(members):
    order = {"DEFECTIVE": 1, "CLEAN": 0}
    return max(members, key=lambda m: order.get(m["acceptability"], 0))

by_stratum = defaultdict(list)
for k, members in group_new.items():
    rep = rep_of(members)
    stratum = (rep["acceptability"], rep["primary_defect_for_analysis"])
    by_stratum[stratum].append(k)

new_train, new_val, new_test = [], [], []
for stratum, keys in by_stratum.items():
    keys = sorted(keys)
    n = len(keys)
    n_test = max(1, round(n * 0.2)) if n >= 3 else 0
    n_val = max(1, round(n * 0.2)) if n >= 3 else 0
    new_test.extend(keys[:n_test])
    new_val.extend(keys[n_test:n_test + n_val])
    new_train.extend(keys[n_test + n_val:])

final_group_split = dict(group_prior_split)
for k in new_train:
    final_group_split[k] = "train"
for k in new_val:
    final_group_split[k] = "val"
for k in new_test:
    final_group_split[k] = "test"

train_uids, val_uids, test_uids = [], [], []
for k, members in groups.items():
    split = final_group_split[k]
    uids = [m["uid"] for m in members]
    {"train": train_uids, "val": val_uids, "test": test_uids}[split].extend(uids)

out = {
    "note": "Unified Phase 9 split over the final combined dataset. Groups that existed in R50's or Phase 8's frozen splits keep that assignment (first real use of those reserved test sets). Phase 8B's new groups are freshly split, stratified by acceptability + primary_defect_for_analysis, deterministic.",
    "n_groups": {"train": sum(1 for v in final_group_split.values() if v == "train"),
                 "val": sum(1 for v in final_group_split.values() if v == "val"),
                 "test": sum(1 for v in final_group_split.values() if v == "test")},
    "n_records": {"train": len(train_uids), "val": len(val_uids), "test": len(test_uids)},
    "train_uids": sorted(train_uids),
    "val_uids": sorted(val_uids),
    "test_uids": sorted(test_uids),
}
with open(EVAL / "r50_dataset" / "r9_split.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print("Group counts:", out["n_groups"])
print("Record counts:", out["n_records"])

# sanity: acceptability distribution per split
by_uid = {r["uid"]: r for r in records}
from collections import Counter
for name, uids in [("train", train_uids), ("val", val_uids), ("test", test_uids)]:
    c = Counter(by_uid[u]["acceptability"] for u in uids)
    print(f"{name} acceptability: {dict(c)}")
