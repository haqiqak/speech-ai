"""
eval/r50p8_make_split.py -- R50 Phase 8, step 11: a NEW leakage-safe
train/val/test split for the Phase 8 dataset, frozen separately from
R50's own frozen split (eval/r50_dataset/split.json, untouched). Split by
dedup group (word-pair or original+reformulated text pair), stratified by
primary defect type, deterministic (sorted, no RNG).

Records that duplicate an R50-baseline lexical phenomenon (same dedup_key
as an R50 record) are EXCLUDED from this split entirely -- they are not
independent Phase 8 evidence and should not inflate either dataset's
apparent size.

RESEARCH ONLY. This file is not to be used for label refinement,
threshold selection, or training.
"""
import json
from collections import defaultdict
from pathlib import Path

EVAL = Path(__file__).parent
data = json.load(open(EVAL / "r50_dataset" / "phase8_dataset.json", encoding="utf-8"))
overlap = set(data["overlap_with_r50_dedup_key"])
records = [r for r in data["records"] if r["uid"] not in overlap]

groups = defaultdict(list)
for r in records:
    groups[r["dedup_key"]].append(r)

group_info = {}
for k, members in groups.items():
    rep = next((m for m in members if m["human_severity"] == "SEVERE"), members[0])
    group_info[k] = {"primary": rep["human_defect_labels"]["primary"], "uids": [m["uid"] for m in members]}

by_stratum = defaultdict(list)
for k, info in group_info.items():
    by_stratum[info["primary"]].append(k)

train, val, test = [], [], []
for stratum, keys in by_stratum.items():
    keys = sorted(keys)
    n = len(keys)
    n_test = max(1, round(n * 0.2))
    n_val = max(1, round(n * 0.2))
    test.extend(keys[:n_test])
    val.extend(keys[n_test:n_test + n_val])
    train.extend(keys[n_test + n_val:])


def uids_for(keys):
    out = []
    for k in keys:
        out.extend(group_info[k]["uids"])
    return sorted(out)


split = {
    "note": "FROZEN Phase 8 split, SEPARATE from R50's own frozen split (eval/r50_dataset/split.json, which remains untouched). Not to be used for label refinement, threshold selection, or training. Records duplicating an R50-baseline lexical phenomenon are excluded entirely (not counted as independent Phase 8 evidence).",
    "n_groups": {"train": len(train), "val": len(val), "test": len(test)},
    "n_records": {"train": len(uids_for(train)), "val": len(uids_for(val)), "test": len(uids_for(test))},
    "train_uids": uids_for(train),
    "val_uids": uids_for(val),
    "test_uids": uids_for(test),
}

with open(EVAL / "r50_dataset" / "phase8_split.json", "w", encoding="utf-8") as f:
    json.dump(split, f, indent=2)

print("Group counts:", split["n_groups"])
print("Record counts:", split["n_records"])
