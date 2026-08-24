"""eval/r50p8b_final_stats.py -- R50 Phase 8B, task 5: recompute full
dataset statistics across R50 baseline (convention-corrected) + Phase 8
(convention-corrected) + Phase 8B, with evidence-quality breakdown."""
import json
from collections import Counter, defaultdict
from pathlib import Path

EVAL = Path(__file__).parent

r50 = json.load(open(EVAL / "r50_dataset" / "labeled_dataset_v2_convention.json", encoding="utf-8"))["records"]
for r in r50:
    r["evidence_quality"] = "HUMAN_REVIEW_OF_EXISTING_CASE"
    r["_dataset"] = "R50"

p8_full = json.load(open(EVAL / "r50_dataset" / "phase8_dataset_v2_convention.json", encoding="utf-8"))
p8_overlap = set(p8_full["overlap_with_r50_dedup_key"])
p8 = [r for r in p8_full["records"] if r["uid"] not in p8_overlap]
for r in p8:
    r["evidence_quality"] = "ORGANIC_OBSERVED" if "organic" in r["provenance"][0] else "CONSTRUCTED"
    r["_dataset"] = "Phase8"

p8b_full = json.load(open(EVAL / "r50_dataset" / "phase8b_dataset.json", encoding="utf-8"))
p8b_overlap = set(p8b_full["overlap_with_prior_dedup_key"])
p8b = [r for r in p8b_full["records"] if r["uid"] not in p8b_overlap]
for r in p8b:
    r["evidence_quality"] = "ORGANIC_OBSERVED"
    r["_dataset"] = "Phase8B"

all_records = r50 + p8 + p8b
print(f"Total records across R50+Phase8+Phase8B (deduped against each other): {len(all_records)}")
print(f"  R50: {len(r50)}, Phase8 new: {len(p8)}, Phase8B new: {len(p8b)}")

groups = defaultdict(list)
for r in all_records:
    groups[r["dedup_key"]].append(r)
print(f"Unique dedup groups: {len(groups)}")

group_primary = {}
group_evidence = {}
for k, members in groups.items():
    rep = max(members, key=lambda m: {"SEVERE": 2, "MINOR": 1}.get(m["human_severity"], 0))
    group_primary[k] = rep["human_defect_labels"]["primary"]
    # evidence quality: best (most trustworthy) evidence in the group, ORGANIC > HUMAN_REVIEW > CONSTRUCTED
    rank = {"ORGANIC_OBSERVED": 2, "HUMAN_REVIEW_OF_EXISTING_CASE": 1, "CONSTRUCTED": 0}
    best = max(members, key=lambda m: rank.get(m["evidence_quality"], 0))
    group_evidence[k] = best["evidence_quality"]

prim_counts = Counter(group_primary.values())
print("\nUnique-case counts by primary defect type:")
for cls, n in sorted(prim_counts.items(), key=lambda x: -x[1]):
    print(f"  {cls}: {n}")

print("\n--- Evidence-quality breakdown for the two target classes ---")
for cls in ["FACTUAL_OR_LOGICAL_REVERSAL", "FIXED_TERM_OR_IDIOM"]:
    keys = [k for k, v in group_primary.items() if v == cls]
    ev = Counter(group_evidence[k] for k in keys)
    print(f"{cls}: total unique = {len(keys)}  |  {dict(ev)}")

sev_counts = Counter()
for k, members in groups.items():
    rep = max(members, key=lambda m: {"SEVERE": 2, "MINOR": 1}.get(m["human_severity"], 0))
    sev_counts[rep["human_severity"]] += 1
print("\nUnique-case severity distribution:", dict(sev_counts))

acc_counts = Counter()
for k, members in groups.items():
    accs = [m.get("human_acceptability") for m in members if m.get("human_acceptability")]
    acc_counts[accs[0] if accs else "?"] += 1
print("Unique-case acceptability distribution:", dict(acc_counts))

gran_counts = Counter()
for r in all_records:
    gran_counts[r["granularity"]] += 1
print("\nGranularity (raw records):", dict(gran_counts))

n_multi = sum(1 for r in all_records if r["human_defect_labels"]["secondary"])
print(f"Records with multiple labels: {n_multi}/{len(all_records)}")

n_convention_adjusted = sum(1 for r in (r50 + p8) if r.get("convention_adjusted"))
print(f"\nRecords adjusted by the whole-sentence labeling convention (task 3): {n_convention_adjusted}")

with open(EVAL / "r50_dataset" / "phase8b_final_stats.json", "w", encoding="utf-8") as f:
    json.dump({
        "total_records": len(all_records),
        "by_source": {"R50": len(r50), "Phase8_new": len(p8), "Phase8B_new": len(p8b)},
        "n_unique_dedup_groups": len(groups),
        "unique_case_primary_defect": dict(prim_counts),
        "unique_case_severity": dict(sev_counts),
        "evidence_quality_factual": dict(Counter(group_evidence[k] for k, v in group_primary.items() if v == "FACTUAL_OR_LOGICAL_REVERSAL")),
        "evidence_quality_fixedterm": dict(Counter(group_evidence[k] for k, v in group_primary.items() if v == "FIXED_TERM_OR_IDIOM")),
        "n_convention_adjusted": n_convention_adjusted,
    }, f, indent=2)
print("\nwrote eval/r50_dataset/phase8b_final_stats.json")
