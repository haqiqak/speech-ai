"""
R50 Phase 9 -- leakage-safe train/val/test split proposal.

Splits by DEDUP GROUP (word-pair or normalized-sentence), never by
individual record, so no near-duplicate substitution/sentence appears in
more than one split. Deterministic (sorted, no RNG) so it's reproducible.

This writes a FROZEN split file. Per direct instruction: the test split
must not be used for label refinement, threshold selection, or training,
now or later. Research-only, no training performed here.
"""
import json
from collections import defaultdict
from pathlib import Path

EVAL = Path(__file__).parent
data = json.load(open(EVAL / "r50_dataset" / "labeled_dataset.json", encoding="utf-8"))
records = data["records"]

groups = defaultdict(list)
for r in records:
    groups[r["dedup_key"]].append(r)

# representative label per group = most severe member's primary defect type
group_info = {}
for k, members in groups.items():
    rep = next((m for m in members if m["human_severity"] == "SEVERE"), members[0])
    group_info[k] = {
        "primary": rep["human_defect_labels"]["primary"],
        "uids": [m["uid"] for m in members],
    }

by_stratum = defaultdict(list)
for k, info in group_info.items():
    by_stratum[info["primary"]].append(k)

train, val, test = [], [], []
for stratum, keys in by_stratum.items():
    keys = sorted(keys)  # deterministic
    n = len(keys)
    if n <= 2:
        # too few to split -- keep in train only, flag as untested-by-split
        train.extend(keys)
        continue
    n_test = max(1, round(n * 0.15))
    n_val = max(1, round(n * 0.15))
    test.extend(keys[:n_test])
    val.extend(keys[n_test:n_test + n_val])
    train.extend(keys[n_test + n_val:])

def uids_for(keys):
    out = []
    for k in keys:
        out.extend(group_info[k]["uids"])
    return sorted(out)

split = {
    "note": "FROZEN at construction time (R50 Phase 9). Test split must not be used for label refinement, threshold selection, or training. Split is by dedup GROUP (word-pair / normalized sentence), not by record, to avoid leakage of near-duplicate substitutions across splits.",
    "n_groups": {"train": len(train), "val": len(val), "test": len(test)},
    "n_records": {"train": len(uids_for(train)), "val": len(uids_for(val)), "test": len(uids_for(test))},
    "train_uids": uids_for(train),
    "val_uids": uids_for(val),
    "test_uids": uids_for(test),
    "strata_too_small_to_split": [s for s, keys in by_stratum.items() if len(keys) <= 2],
}

with open(EVAL / "r50_dataset" / "split.json", "w", encoding="utf-8") as f:
    json.dump(split, f, indent=2)

print("Group counts:", split["n_groups"])
print("Record counts:", split["n_records"])
print("Strata too small to split (<=2 unique groups, kept entirely in train):",
      split["strata_too_small_to_split"])
