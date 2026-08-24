"""R50 Phase 2/3/7/9 -- compute dataset statistics, dedup groups, and a
leakage-safe train/val/test split proposal from eval/r50_dataset/labeled_dataset.json.
Research/reporting only -- no training, no production changes.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

EVAL = Path(__file__).parent
data = json.load(open(EVAL / "r50_dataset" / "labeled_dataset.json", encoding="utf-8"))
records = data["records"]

# --- known near-duplicate v5<->R40 pairs that failed exact text-match
# (v5's "original" field has pre-existing minor grammar fixes vs R40's raw
# corpus, e.g. "tend" vs "tends" -- documented limitation, not silently fixed)
V5_NEAR_DUP_R40_INDEX = {
    "pair_06": 7,    # preferences->options ("A rational agent has goals or preferences...")
    "pair_15": None, # quest+optimists+place combined -- spans R40 #34+#35 (two separate single-word audits)
    "pair_16": None, # half-century+s combined -- spans R40 #43+#44
    "pair_17": 50,   # glucose restructuring, "tend" vs "tends" grammar variant
}

print("=" * 70)
print("R50 Phase 2/3/7 -- Dataset report inputs")
print("=" * 70)

print(f"\nTotal records: {len(records)}")

by_source = Counter()
for r in records:
    by_source[",".join(sorted(set(r["provenance"])))] += 1
print("\nProvenance distribution:")
for k, v in sorted(by_source.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

print("\nSeverity distribution:")
sev = Counter(r["human_severity"] for r in records)
for k, v in sorted(sev.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

print("\nPrimary defect-type distribution:")
prim = Counter(r["human_defect_labels"]["primary"] for r in records)
for k, v in sorted(prim.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

print("\nSecondary defect-type distribution (co-occurring):")
sec = Counter()
for r in records:
    for s in r["human_defect_labels"]["secondary"]:
        sec[s] += 1
for k, v in sorted(sec.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

n_multi = sum(1 for r in records if r["human_defect_labels"]["secondary"])
print(f"\nRecords with multiple (primary+secondary) labels: {n_multi}")

n_uncertain = sum(1 for r in records if r["human_severity"] == "UNCERTAIN"
                   or r["human_defect_labels"]["primary"] == "UNCERTAIN"
                   or r.get("text_verification") == "UNCERTAIN")
print(f"Records with an UNCERTAIN flag (severity/label/text-verification): {n_uncertain}")

gran = Counter(r["granularity"] for r in records)
print("\nGranularity distribution:")
for k, v in sorted(gran.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

clean_vs_defect = Counter()
for r in records:
    if r["human_severity"] in ("CLEAN", "ORIGINAL_NO_CHANGE"):
        clean_vs_defect["CLEAN/no-change"] += 1
    else:
        clean_vs_defect["defective (MINOR or SEVERE)"] += 1
print("\nClean(+no-change) vs defective:")
for k, v in clean_vs_defect.items():
    print(f"  {k}: {v}")

n_ratings = sum(1 for r in records if r["human_ratings"])
print(f"\nRecords enriched with v5 human 1-5 ratings (meaning/naturalness/ease/preference): {n_ratings}")

n_r44 = sum(1 for r in records if "R44" in r["provenance"])
print(f"Records with R44 automated NLI+grammar flags attached: {n_r44}")

# --- dedup / leakage groups ---
groups = defaultdict(list)
for r in records:
    groups[r["dedup_key"]].append(r["uid"])

multi_groups = {k: v for k, v in groups.items() if len(v) > 1}
print(f"\nUnique dedup groups (leakage-safe split unit): {len(groups)}")
print(f"Groups with >1 member (duplicate/near-duplicate substitution reused across sentences): {len(multi_groups)}")
largest = sorted(multi_groups.items(), key=lambda x: -len(x[1]))[:8]
print("Largest duplicate groups:")
for k, v in largest:
    print(f"  {k}: {len(v)} records -> {v}")

# --- primary defect-type x severity cross-tab (the class-imbalance table) ---
print("\nPrimary defect type x severity:")
cross = defaultdict(Counter)
for r in records:
    cross[r["human_defect_labels"]["primary"]][r["human_severity"]] += 1
for k in sorted(cross, key=lambda x: -sum(cross[x].values())):
    row = cross[k]
    print(f"  {k}: " + ", ".join(f"{sv}={n}" for sv, n in row.items()))

with open(EVAL / "r50_dataset" / "stats_summary.json", "w", encoding="utf-8") as f:
    json.dump({
        "n_records": len(records),
        "by_source": dict(by_source),
        "severity": dict(sev),
        "primary_defect": dict(prim),
        "secondary_defect": dict(sec),
        "n_multi_label": n_multi,
        "n_uncertain": n_uncertain,
        "granularity": dict(gran),
        "clean_vs_defect": dict(clean_vs_defect),
        "n_v5_ratings": n_ratings,
        "n_r44_flags": n_r44,
        "n_dedup_groups": len(groups),
        "n_dup_groups_gt1": len(multi_groups),
    }, f, indent=2)
print("\nwrote eval/r50_dataset/stats_summary.json")
