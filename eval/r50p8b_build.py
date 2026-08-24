"""
eval/r50p8b_build.py -- R50 Phase 8B, tasks 1+3+4: build the final
Phase 8B dataset from the 58 whole-sentence-labeled groups (task 1's
organic harvest, labeled under the resolved whole-sentence convention
from task 3), attach ORGANIC_OBSERVED/CONSTRUCTED/HUMAN_REVIEW_OF_
EXISTING_CASE provenance to every record (task 4), and check for
leakage against R50 baseline + Phase 8.

RESEARCH ONLY. No model trained, no production code touched.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

EVAL = Path(__file__).parent
sys.path.insert(0, str(EVAL))
from r50p8b_labels import LABELS, ORGANIC_FACTUAL_REVERSAL_GROUP_INDICES  # noqa: E402


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def main():
    raw = json.load(open(EVAL / "r50_dataset" / "phase8b_raw_harvest.json", encoding="utf-8"))
    changes = raw["changes"]

    groups = defaultdict(list)
    order = []
    for c in changes:
        key = (c["original_sentence"], c["reformulated_sentence"])
        if key not in groups:
            order.append(key)
        groups[key].append(c)

    assert len(order) == 58, len(order)

    records = []
    for i, key in enumerate(order, start=1):
        sev, labels, rationale = LABELS[i]
        members = groups[key]
        distinct_pairs = list({(m["original_word"], m["replacement_word"]) for m in members})
        is_restructuring = any(m["change_source"] == "restructuring" for m in members)
        provenance_evidence = "ORGANIC_OBSERVED"

        for j, (ow, rw) in enumerate(distinct_pairs):
            m = next(m for m in members if m["original_word"] == ow and m["replacement_word"] == rw)
            uid = f"P8B-organic-{i:03d}" + (f"-{j}" if len(distinct_pairs) > 1 else "")
            records.append({
                "uid": uid,
                "provenance": ["R50-Phase8B-organic-harvest"],
                "evidence_quality": provenance_evidence,
                "granularity": "restructuring" if is_restructuring else "substitution",
                "original_text": key[0],
                "reformulated_text": key[1],
                "changed_word_pair": None if is_restructuring else [ow, rw],
                "human_acceptability": "CLEAN" if sev == "CLEAN" else "DEFECTIVE",
                "human_severity": sev,
                "human_defect_labels": {"primary": labels[0], "secondary": labels[1:]},
                "human_rationale": rationale,
                "human_rationale_source": "fresh-blind-whole-sentence-2026-08-24",
                "rater_id": "claude-primary",
                "labeling_protocol": "blind, WHOLE-DELIVERED-SENTENCE convention (Phase 8B task 3): judged the complete original->reformulated pair, not an isolated word change; same verdict applied to every word-pair that produced this sentence.",
                "topic_source": raw["changes"][0].get("source"),  # placeholder, corrected below
                "profile": None,
                "sentence_group_index": i,
                "n_distinct_changes_in_sentence": len(distinct_pairs),
                "automated": {"contextual_fit": None, "sbert_sim": None, "antonym_check": None},
            })
        # fix topic_source per-record from the actual member
        for r in records[-len(distinct_pairs):]:
            src_member = next((m for m in members), None)
            r["topic_source"] = src_member["source"]
            r["profile"] = src_member["profile"]

    for r in records:
        if r["changed_word_pair"]:
            r["dedup_key"] = "wordpair:" + "->".join(w.lower() for w in r["changed_word_pair"])
        else:
            r["dedup_key"] = "text:" + norm(r["original_text"]) + "=>" + norm(r["reformulated_text"])

    # cross-check leakage against R50 baseline AND Phase 8
    r50 = json.load(open(EVAL / "r50_dataset" / "labeled_dataset.json", encoding="utf-8"))
    p8 = json.load(open(EVAL / "r50_dataset" / "phase8_dataset.json", encoding="utf-8"))
    p8_overlap = set(p8["overlap_with_r50_dedup_key"])
    p8_records = [r for r in p8["records"] if r["uid"] not in p8_overlap]

    prior_keys = {r["dedup_key"] for r in r50["records"]} | {r["dedup_key"] for r in p8_records}

    overlap_uids = []
    for r in records:
        if r["dedup_key"] in prior_keys:
            overlap_uids.append(r["uid"])

    out_path = EVAL / "r50_dataset" / "phase8b_dataset.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "n_records": len(records),
            "n_sentence_groups": len(order),
            "overlap_with_prior_dedup_key": overlap_uids,
            "organic_factual_reversal_group_count": len(ORGANIC_FACTUAL_REVERSAL_GROUP_INDICES),
            "records": records,
        }, f, indent=2, ensure_ascii=False)

    print(f"wrote {len(records)} records ({len(order)} sentence groups) to {out_path}")
    print(f"overlap with R50+Phase8 prior dedup keys: {len(overlap_uids)} -> {overlap_uids}")

    prim = defaultdict(int)
    for r in records:
        if r["uid"] not in overlap_uids:
            prim[r["human_defect_labels"]["primary"]] += 1
    print("Primary defect distribution (new records only):", dict(prim))


if __name__ == "__main__":
    main()
