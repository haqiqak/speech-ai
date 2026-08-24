"""eval/r50p8_stats.py -- R50 Phase 8: dataset statistics, dedup analysis,
and comparison against the R50 baseline. Research/reporting only."""
import json
from collections import Counter, defaultdict
from pathlib import Path

EVAL = Path(__file__).parent
data = json.load(open(EVAL / "r50_dataset" / "phase8_dataset.json", encoding="utf-8"))
records = data["records"]
overlap_uids = set(data["overlap_with_r50_dedup_key"])

print("=" * 70)
print("R50 Phase 8 -- dataset statistics")
print("=" * 70)
print(f"\nTotal records: {len(records)} ({data['n_organic']} organic, {data['n_constructed']} constructed)")
print(f"Records whose dedup_key already exists in the frozen R50 baseline "
      f"(same lexical phenomenon as R50, NOT new independent evidence): {len(overlap_uids)} -> {sorted(overlap_uids)}")

new_records = [r for r in records if r["uid"] not in overlap_uids]
print(f"Records counted as genuinely new/independent of R50: {len(new_records)}")

groups = defaultdict(list)
for r in new_records:
    groups[r["dedup_key"]].append(r["uid"])
print(f"\nUnique dedup groups among new records: {len(groups)}")
dup_groups = {k: v for k, v in groups.items() if len(v) > 1}
print(f"Groups with >1 member (repeated substitution within Phase 8 itself): {len(dup_groups)}")
for k, v in dup_groups.items():
    print(f"  {k}: {v}")

print("\nAcceptability distribution (new records):")
acc = Counter(r["human_acceptability"] for r in new_records)
for k, v in acc.items():
    print(f"  {k}: {v}")

print("\nSeverity distribution (new records):")
sev = Counter(r["human_severity"] for r in new_records)
for k, v in sorted(sev.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

print("\nPrimary defect-type distribution (new records, raw):")
prim = Counter(r["human_defect_labels"]["primary"] for r in new_records)
for k, v in sorted(prim.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

print("\nPrimary defect-type distribution at UNIQUE dedup-group level:")
group_primary = Counter()
for k, uids in groups.items():
    by_uid = {r["uid"]: r for r in new_records}
    rep = next((by_uid[u] for u in uids if by_uid[u]["human_severity"] == "SEVERE"), by_uid[uids[0]])
    group_primary[rep["human_defect_labels"]["primary"]] += 1
for k, v in sorted(group_primary.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

n_multi = sum(1 for r in new_records if r["human_defect_labels"]["secondary"])
print(f"\nRecords with multiple (primary+secondary) labels: {n_multi}")

gran = Counter(r["granularity"] for r in new_records)
print("\nGranularity:")
for k, v in gran.items():
    print(f"  {k}: {v}")

print("\nOrganic vs constructed, by primary defect type:")
cross = defaultdict(Counter)
for r in new_records:
    is_organic = "organic" in r["provenance"][0]
    cross[r["human_defect_labels"]["primary"]]["organic" if is_organic else "constructed"] += 1
for k in sorted(cross, key=lambda x: -sum(cross[x].values())):
    print(f"  {k}: {dict(cross[k])}")

# ---- comparison against R50 baseline unique-group counts for the two thin classes ----
r50 = json.load(open(EVAL / "r50_dataset" / "labeled_dataset.json", encoding="utf-8"))
r50_groups = defaultdict(list)
for r in r50["records"]:
    r50_groups[r["dedup_key"]].append(r)
r50_group_primary = Counter()
for k, members in r50_groups.items():
    rep = next((m for m in members if m["human_severity"] == "SEVERE"), members[0])
    r50_group_primary[rep["human_defect_labels"]["primary"]] += 1

print("\n" + "=" * 70)
print("R50 baseline vs. R50+Phase8 combined -- unique-case counts, two target classes")
print("=" * 70)
for cls in ["FACTUAL_OR_LOGICAL_REVERSAL", "FIXED_TERM_OR_IDIOM"]:
    baseline = r50_group_primary.get(cls, 0)
    new = group_primary.get(cls, 0)
    print(f"  {cls}: R50 baseline={baseline}, Phase8 new={new}, combined={baseline + new}")

with open(EVAL / "r50_dataset" / "phase8_stats_summary.json", "w", encoding="utf-8") as f:
    json.dump({
        "n_total_records": len(records),
        "n_overlap_with_r50": len(overlap_uids),
        "n_new_records": len(new_records),
        "n_new_dedup_groups": len(groups),
        "n_dup_groups_within_phase8": len(dup_groups),
        "acceptability": dict(acc),
        "severity": dict(sev),
        "primary_defect_raw": dict(prim),
        "primary_defect_unique_groups": dict(group_primary),
        "n_multi_label": n_multi,
        "granularity": dict(gran),
        "r50_baseline_unique_groups": dict(r50_group_primary),
    }, f, indent=2)
print("\nwrote eval/r50_dataset/phase8_stats_summary.json")
