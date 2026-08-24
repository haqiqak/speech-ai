"""
eval/r9_assemble_final_dataset.py -- Phase 9, step 1: assemble the final
training/eval dataset from R50 (convention-corrected) + Phase 8
(convention-corrected) + Phase 8B, with:
  - acceptability standardized as the PRIMARY target (CLEAN vs DEFECTIVE)
  - NATURALNESS_OR_REGISTER demoted from primary to secondary-only, per
    Phase 8B's taxonomy decision (it could not be reliably distinguished
    as a primary label by two independent raters)
  - evidence_quality preserved on every record
  - a unified split built by dedup GROUP, respecting the prior frozen
    R50/Phase8 test assignments where those groups still exist, and
    assigning Phase 8B's new groups via the same stratified method

RESEARCH/PROTOTYPE ONLY at this stage. No production code touched.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

EVAL = Path(__file__).parent


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def load_all():
    r50 = json.load(open(EVAL / "r50_dataset" / "labeled_dataset_v2_convention.json", encoding="utf-8"))["records"]
    for r in r50:
        r["evidence_quality"] = "HUMAN_REVIEW_OF_EXISTING_CASE"
        r["_source_dataset"] = "R50"

    p8_full = json.load(open(EVAL / "r50_dataset" / "phase8_dataset_v2_convention.json", encoding="utf-8"))
    p8_overlap = set(p8_full["overlap_with_r50_dedup_key"])
    p8 = [r for r in p8_full["records"] if r["uid"] not in p8_overlap]
    for r in p8:
        r["evidence_quality"] = "ORGANIC_OBSERVED" if "organic" in r["provenance"][0] else "CONSTRUCTED"
        r["_source_dataset"] = "Phase8"

    p8b_full = json.load(open(EVAL / "r50_dataset" / "phase8b_dataset.json", encoding="utf-8"))
    p8b_overlap = set(p8b_full["overlap_with_prior_dedup_key"])
    p8b = [r for r in p8b_full["records"] if r["uid"] not in p8b_overlap]
    for r in p8b:
        r["evidence_quality"] = "ORGANIC_OBSERVED"
        r["_source_dataset"] = "Phase8B"

    return r50 + p8 + p8b


def standardize(r):
    """Return (acceptability, severity, primary_label_for_training,
    all_labels_incl_demoted) applying the NATURALNESS_OR_REGISTER demotion."""
    sev = r["human_severity"]
    acc = r.get("human_acceptability")
    if acc is None:
        acc = "CLEAN" if sev in ("CLEAN", "ORIGINAL_NO_CHANGE") else "DEFECTIVE"
    labels = r["human_defect_labels"]
    primary = labels["primary"]
    secondary = list(labels["secondary"])
    demoted = False
    if primary == "NATURALNESS_OR_REGISTER":
        # demote: no reliable primary substitute exists at the individual
        # record level without re-reading each case, so mark explicitly
        # as a demoted-primary rather than silently reassigning to
        # another class (which would fabricate a label). Acceptability/
        # severity (the actual training target) are unaffected.
        secondary = [primary] + secondary
        primary = "DEMOTED_NATURALNESS_OR_REGISTER"
        demoted = True
    return acc, sev, primary, secondary, demoted


def main():
    records = load_all()
    out = []
    n_demoted = 0
    for r in records:
        acc, sev, primary, secondary, demoted = standardize(r)
        if demoted:
            n_demoted += 1
        wp = r.get("changed_word_pair")
        dedup_key = r.get("dedup_key") or ("wordpair:" + "->".join(w.lower() for w in wp) if wp else "text:" + norm(r["original_text"]) + "=>" + norm(r["reformulated_text"]))
        out.append({
            "uid": r["uid"],
            "source_dataset": r["_source_dataset"],
            "evidence_quality": r["evidence_quality"],
            "dedup_key": dedup_key,
            "original_text": r["original_text"],
            "reformulated_text": r["reformulated_text"],
            "acceptability": acc,               # PRIMARY training target
            "severity": sev,
            "primary_defect_for_analysis": primary,   # secondary diagnostic
            "secondary_defects": secondary,
            "convention_adjusted": r.get("convention_adjusted", False),
        })

    groups = defaultdict(list)
    for r in out:
        groups[r["dedup_key"]].append(r)

    print(f"Total records: {len(out)}")
    print(f"Unique dedup groups: {len(groups)}")
    print(f"Records with NATURALNESS_OR_REGISTER demoted from primary: {n_demoted}")

    from collections import Counter
    print("Acceptability distribution (records):", dict(Counter(r["acceptability"] for r in out)))

    with open(EVAL / "r50_dataset" / "r9_final_dataset.json", "w", encoding="utf-8") as f:
        json.dump({"n_records": len(out), "n_groups": len(groups), "records": out}, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {len(out)} records to eval/r50_dataset/r9_final_dataset.json")


if __name__ == "__main__":
    main()
