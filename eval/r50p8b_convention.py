"""
eval/r50p8b_convention.py -- R50 Phase 8B, task 3: apply the resolved
labeling convention.

CONVENTION (per direct instruction, adopted verbatim): the validator
target is "would this reformulated sentence be acceptable to deliver to
the user as a replacement for the original sentence?" -- judged on the
COMPLETE original->reformulated pair as delivered, not an isolated word
change. A word substitution that looks questionable alone but produces a
valid delivered sentence is not automatically defective; a locally
plausible substitution that makes the DELIVERED sentence wrong is.

Mechanically: for every unique delivered sentence (reformulated_text)
that resulted from MULTIPLE distinct simultaneous word-pair changes, all
per-word-pair records sharing that delivered sentence must carry at
least that sentence's worst observed severity/acceptability -- a record
cannot be called CLEAN if the sentence it actually produced is
SEVERE/MINOR-defective elsewhere. This is applied to both the R50
baseline (eval/r50_dataset/labeled_dataset.json) and Phase 8
(eval/r50_dataset/phase8_dataset.json). The original per-word rationale
is PRESERVED (not deleted) as `human_rationale_word_level`; a new
`human_rationale_sentence_level` and `convention_adjusted: true` are
added to every record this changes, so the correction is traceable, not
silent.

RESEARCH ONLY. No model trained, no production code touched.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

EVAL = Path(__file__).parent

SEVERITY_RANK = {"CLEAN": 0, "MINOR": 1, "SEVERE": 2, "ORIGINAL_NO_CHANGE": 0, "UNCERTAIN": 1}


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def apply_convention(records, label):
    """records: list of dicts with human_severity, human_defect_labels,
    original_text, reformulated_text. Mutates in place; returns count
    changed and the sentence-level groups found."""
    groups = defaultdict(list)
    for r in records:
        key = (norm(r["original_text"]), norm(r["reformulated_text"]))
        groups[key].append(r)

    n_changed = 0
    n_multi_change_groups = 0
    for key, members in groups.items():
        if len(members) < 2:
            continue
        # only a genuine "isolation" confound if this delivered sentence
        # resulted from >1 DISTINCT underlying substitution (word-pair or
        # otherwise) -- not just the same change duplicated across profiles
        distinct_pairs = set()
        for m in members:
            wp = m.get("changed_word_pair")
            distinct_pairs.add(tuple(w.lower() for w in wp) if wp else m["uid"])
        if len(distinct_pairs) < 2:
            continue  # pure duplicate rows, not a co-occurrence case
        n_multi_change_groups += 1

        worst = max(members, key=lambda m: SEVERITY_RANK.get(m["human_severity"], 0))
        worst_rank = SEVERITY_RANK.get(worst["human_severity"], 0)

        for m in members:
            my_rank = SEVERITY_RANK.get(m["human_severity"], 0)
            if my_rank < worst_rank:
                m["human_rationale_word_level"] = m["human_rationale"]
                m["human_rationale_sentence_level"] = (
                    f"[Phase 8B convention correction] This word-pair's own contribution "
                    f"is fine in isolation, but the DELIVERED sentence it appears in also "
                    f"contains a separate, worse defect ({worst['human_severity']}: "
                    f"{worst.get('changed_word_pair') or worst['uid']} -- "
                    f"\"{worst['human_rationale'][:140]}\"). Per the resolved labeling "
                    f"convention, the delivered sentence -- not the isolated word change -- "
                    f"is the unit of judgment, so this record is upgraded to match."
                )
                old_sev, old_acc = m["human_severity"], m.get("human_acceptability")
                m["human_severity"] = worst["human_severity"]
                if "human_acceptability" in m:
                    m["human_acceptability"] = worst.get("human_acceptability", "DEFECTIVE" if worst["human_severity"] != "CLEAN" else "CLEAN")
                m["convention_adjusted"] = True
                m["convention_adjustment_detail"] = f"{old_sev}->{m['human_severity']}" + (f" (acc {old_acc}->{m['human_acceptability']})" if "human_acceptability" in m else "")
                n_changed += 1
            else:
                m.setdefault("convention_adjusted", False)

    for r in records:
        r.setdefault("convention_adjusted", False)

    print(f"[{label}] sentence-groups with genuinely distinct co-occurring changes: {n_multi_change_groups}")
    print(f"[{label}] records upgraded to match their delivered sentence's worst severity: {n_changed}")
    return n_changed


def main():
    r50 = json.load(open(EVAL / "r50_dataset" / "labeled_dataset.json", encoding="utf-8"))
    n_r50 = apply_convention(r50["records"], "R50 baseline")
    with open(EVAL / "r50_dataset" / "labeled_dataset_v2_convention.json", "w", encoding="utf-8") as f:
        json.dump(r50, f, indent=2, ensure_ascii=False)

    p8 = json.load(open(EVAL / "r50_dataset" / "phase8_dataset.json", encoding="utf-8"))
    n_p8 = apply_convention(p8["records"], "Phase 8")
    with open(EVAL / "r50_dataset" / "phase8_dataset_v2_convention.json", "w", encoding="utf-8") as f:
        json.dump(p8, f, indent=2, ensure_ascii=False)

    print(f"\nTotal records adjusted by the resolved convention: {n_r50 + n_p8}")
    print("Wrote labeled_dataset_v2_convention.json and phase8_dataset_v2_convention.json")


if __name__ == "__main__":
    main()
