"""
eval/r10_analysis.py -- Phase 10, steps 14-15: merge raw results + blind
judgments + validator predictions + corpus metadata, and produce the
full stratified analysis matrix.

RESEARCH ONLY. No production code touched.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

EVAL = Path(__file__).parent

corpus = json.load(open(EVAL / "r10_corpus.json", encoding="utf-8"))
by_sentence = {r["sentence_id"]: r for r in corpus["records"]}

raw = json.load(open(EVAL / "r10_raw_results.json", encoding="utf-8"))
by_run = {r["run_id"]: r for r in raw["results"]}

judgments = {}
for i in range(1, 6):
    batch = json.load(open(EVAL / f"r10_blind_batch_{i}_results.json", encoding="utf-8"))
    judgments.update(batch)

validator = json.load(open(EVAL / "r10_validator_predictions.json", encoding="utf-8"))
val_by_run = {p["run_id"]: p for p in validator["predictions"]}

# ---------------------------------------------------------------------
# Build the full merged table
# ---------------------------------------------------------------------
merged = []
for run_id, raw_row in by_run.items():
    sent = by_sentence[raw_row["sentence_id"]]
    row = {
        "run_id": run_id,
        "sentence_id": raw_row["sentence_id"],
        "domain": sent["domain"],
        "subcategory": sent["subcategory"],
        "linguistic_tags": sent["linguistic_tags"],
        "expected_opportunity": sent["expected_opportunity"],
        "profile_type": raw_row["profile_type"],
        "status": raw_row["status"],
        "escalated": any(c["source"] != "substitution" for c in raw_row["changes"]),
        "n_changes": len(raw_row["changes"]),
        "latency": raw_row["latency_seconds"],
    }
    if raw_row["status"] == "reformulated":
        j = judgments.get(run_id)
        row["acceptability"] = j["acceptability"] if j else "MISSING_JUDGMENT"
        row["severity"] = j["severity"] if j else None
        row["primary_defect"] = j["primary_defect"] if j else None
        row["secondary_defects"] = j.get("secondary_defects", []) if j else []
        v = val_by_run.get(run_id)
        row["validator_9b_pred"] = v["pred_9b"] if v else None
        row["validator_9c_pred"] = v["pred_9c"] if v else None
    else:
        # no_change_needed / could_not_safely_reformulate: output==original, trivially safe
        row["acceptability"] = "CLEAN" if raw_row["status"] == "no_change_needed" else "REFUSED_SAFE"
        row["severity"] = "CLEAN"
        row["primary_defect"] = "CLEAN"
        row["secondary_defects"] = []
        row["validator_9b_pred"] = None
        row["validator_9c_pred"] = None
    merged.append(row)

with open(EVAL / "r10_merged.json", "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)
print(f"wrote eval/r10_merged.json ({len(merged)} rows)")

n_missing = sum(1 for r in merged if r["acceptability"] == "MISSING_JUDGMENT")
print(f"Rows missing a blind judgment (should be 0): {n_missing}")

judged = [r for r in merged if r["status"] == "reformulated"]

# ---------------------------------------------------------------------
# Overall
# ---------------------------------------------------------------------
print("\n" + "=" * 70)
print("OVERALL")
print("=" * 70)
print("Status:", Counter(r["status"] for r in merged))
print("Escalated (of reformulated):", sum(1 for r in judged if r["escalated"]), "/", len(judged))
print("Acceptability (of judged/reformulated):", Counter(r["acceptability"] for r in judged))
print("Severity (of judged/reformulated):", Counter(r["severity"] for r in judged))
print("Primary defect (of judged/reformulated):", Counter(r["primary_defect"] for r in judged))

# clean rate over ALL 398 runs (treating no_change/refused as non-harmful)
overall_clean = sum(1 for r in merged if r["acceptability"] == "CLEAN")
overall_defective = sum(1 for r in merged if r["acceptability"] == "DEFECTIVE")
print(f"\nAcross all {len(merged)} runs: CLEAN-or-no-change={overall_clean}, "
      f"DEFECTIVE={overall_defective}, refused-safe={sum(1 for r in merged if r['acceptability']=='REFUSED_SAFE')}")

# ---------------------------------------------------------------------
# By domain / subcategory
# ---------------------------------------------------------------------
print("\n" + "=" * 70)
print("BY DOMAIN")
print("=" * 70)
for domain in ["general", "technical"]:
    sub = [r for r in judged if r["domain"] == domain]
    if not sub:
        continue
    n_clean = sum(1 for r in sub if r["acceptability"] == "CLEAN")
    n_defective = sum(1 for r in sub if r["acceptability"] == "DEFECTIVE")
    print(f"{domain}: n={len(sub)}, CLEAN={n_clean} ({n_clean/len(sub):.0%}), "
          f"DEFECTIVE={n_defective} ({n_defective/len(sub):.0%})")

print("\nBy subcategory:")
by_subcat = defaultdict(list)
for r in judged:
    by_subcat[r["subcategory"]].append(r)
for subcat, rows in sorted(by_subcat.items(), key=lambda x: -sum(1 for r in x[1] if r["acceptability"] == "DEFECTIVE") / len(x[1])):
    n = len(rows)
    n_clean = sum(1 for r in rows if r["acceptability"] == "CLEAN")
    n_severe = sum(1 for r in rows if r["severity"] == "SEVERE")
    print(f"  {subcat:<28} n={n:<4} clean={n_clean:<4} ({n_clean/n:.0%})  severe={n_severe} ({n_severe/n:.0%})")

# ---------------------------------------------------------------------
# By linguistic tag
# ---------------------------------------------------------------------
print("\n" + "=" * 70)
print("BY LINGUISTIC TAG")
print("=" * 70)
by_tag = defaultdict(list)
for r in judged:
    for t in r["linguistic_tags"]:
        by_tag[t].append(r)
for tag, rows in sorted(by_tag.items(), key=lambda x: -len(x[1])):
    n = len(rows)
    n_clean = sum(1 for r in rows if r["acceptability"] == "CLEAN")
    print(f"  {tag:<24} n={n:<4} clean={n_clean} ({n_clean/n:.0%})")

# ---------------------------------------------------------------------
# By expected_opportunity (gradient check)
# ---------------------------------------------------------------------
print("\n" + "=" * 70)
print("BY EXPECTED_OPPORTUNITY (predicted at design time, never shown to evaluator)")
print("=" * 70)
by_opp = defaultdict(list)
for r in judged:
    by_opp[r["expected_opportunity"]].append(r)
for opp in ["easy", "moderate", "hard", "very_hard"]:
    rows = by_opp.get(opp, [])
    if not rows:
        continue
    n = len(rows)
    n_clean = sum(1 for r in rows if r["acceptability"] == "CLEAN")
    n_severe = sum(1 for r in rows if r["severity"] == "SEVERE")
    print(f"  {opp:<12} n={n:<4} clean={n_clean} ({n_clean/n:.0%})  severe={n_severe} ({n_severe/n:.0%})")

# ---------------------------------------------------------------------
# By profile type
# ---------------------------------------------------------------------
print("\n" + "=" * 70)
print("BY PROFILE TYPE")
print("=" * 70)
by_profile = defaultdict(list)
for r in judged:
    by_profile[r["profile_type"]].append(r)
for ptype, rows in sorted(by_profile.items(), key=lambda x: -len(x[1])):
    n = len(rows)
    n_clean = sum(1 for r in rows if r["acceptability"] == "CLEAN")
    print(f"  {ptype:<28} n={n:<4} clean={n_clean} ({n_clean/n:.0%})")

# ---------------------------------------------------------------------
# Failure type
# ---------------------------------------------------------------------
print("\n" + "=" * 70)
print("FAILURE TYPE (primary defect, defective rows only)")
print("=" * 70)
defective = [r for r in judged if r["acceptability"] == "DEFECTIVE"]
print(Counter(r["primary_defect"] for r in defective))

# ---------------------------------------------------------------------
# Generation pathway
# ---------------------------------------------------------------------
print("\n" + "=" * 70)
print("GENERATION PATHWAY")
print("=" * 70)
sub_clean = sum(1 for r in judged if not r["escalated"] and r["acceptability"] == "CLEAN")
sub_defective = sum(1 for r in judged if not r["escalated"] and r["acceptability"] == "DEFECTIVE")
esc_clean = sum(1 for r in judged if r["escalated"] and r["acceptability"] == "CLEAN")
esc_defective = sum(1 for r in judged if r["escalated"] and r["acceptability"] == "DEFECTIVE")
refused = sum(1 for r in merged if r["status"] == "could_not_safely_reformulate")
no_change = sum(1 for r in merged if r["status"] == "no_change_needed")
print(f"substitution-only, clean: {sub_clean}")
print(f"substitution-only, defective: {sub_defective}")
print(f"escalation-invoked, clean: {esc_clean}")
print(f"escalation-invoked, defective: {esc_defective}")
print(f"refused (could_not_safely_reformulate): {refused}")
print(f"no_change_needed: {no_change}")

# ---------------------------------------------------------------------
# Validator comparison
# ---------------------------------------------------------------------
print("\n" + "=" * 70)
print("VALIDATOR COMPARISON (judged rows only)")
print("=" * 70)
for model in ["validator_9b_pred", "validator_9c_pred"]:
    tp = sum(1 for r in judged if r[model] == "DEFECTIVE" and r["acceptability"] == "DEFECTIVE")
    fp = sum(1 for r in judged if r[model] == "DEFECTIVE" and r["acceptability"] == "CLEAN")
    fn = sum(1 for r in judged if r[model] == "CLEAN" and r["acceptability"] == "DEFECTIVE")
    tn = sum(1 for r in judged if r[model] == "CLEAN" and r["acceptability"] == "CLEAN")
    prec = tp / (tp + fp) if (tp + fp) else 0
    rec = tp / (tp + fn) if (tp + fn) else 0
    clean_rec = tn / (tn + fp) if (tn + fp) else 0
    print(f"{model}: defect_recall={rec:.0%} defect_precision={prec:.0%} clean_recall={clean_rec:.0%} "
          f"(tp={tp} fp={fp} fn={fn} tn={tn})")

print("\nwrote eval/r10_merged.json; full analysis printed above")
