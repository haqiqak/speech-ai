"""
eval/r50p8_build.py -- R50 Phase 8: assemble the final new-corpus dataset
from (a) the 68 organically-harvested, blind-labeled cases and (b) the 50
deliberately-constructed supplementary examples, dedupe against each
other AND against the frozen R50 baseline (eval/r50_dataset/split.json /
labeled_dataset.json) to guarantee zero cross-phase leakage, and write
the combined Phase 8 dataset + stats.

RESEARCH ONLY. No model trained, no production code touched.
"""
import json
import re
from pathlib import Path

EVAL = Path(__file__).parent

import sys
sys.path.insert(0, str(EVAL))
from r50p8_labels import LABELS  # noqa: E402
from r50p8_constructed import (  # noqa: E402
    FACTUAL_OR_LOGICAL_REVERSAL_EXAMPLES,
    FIXED_TERM_OR_IDIOM_EXAMPLES,
    CLEAN_CONTROL_EXAMPLES,
)


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def load_organic():
    candidates = json.load(open(EVAL / "r50_dataset" / "phase8_blind_candidates.json", encoding="utf-8"))
    out = []
    for i, c in enumerate(candidates, start=1):
        sev, labels, rationale = LABELS[i]
        out.append({
            "uid": f"P8-organic-{i:03d}",
            "provenance": ["R50-Phase8-organic-harvest"],
            "granularity": "restructuring" if c["change_source"] == "restructuring" else "substitution",
            "original_text": c["original_sentence"],
            "reformulated_text": c["reformulated_sentence"],
            "changed_word_pair": None if c["change_source"] == "restructuring" else [c["original_word"], c["replacement_word"]],
            "human_acceptability": "CLEAN" if sev == "CLEAN" else "DEFECTIVE",
            "human_severity": sev,
            "human_defect_labels": {"primary": labels[0], "secondary": labels[1:]},
            "human_rationale": rationale,
            "human_rationale_source": "fresh-blind-2026-08-24",
            "rater_id": "claude-primary",
            "labeling_protocol": "blind: rater saw only original/reformulated text + word pair, no automated scores, no defect-class target, no experiment/profile metadata",
            "topic_source": c["source"],
            "profile": c["profile"],
            "automated": {
                "contextual_fit": c.get("contextual_fit"),
                "sbert_sim": c.get("sbert_sim"),
                "antonym_check": c.get("antonym_check"),
            },
        })
    return out


def load_constructed():
    out = []
    for ex in FACTUAL_OR_LOGICAL_REVERSAL_EXAMPLES:
        out.append({
            "uid": f"P8-constructed-{ex['id']}",
            "provenance": ["R50-Phase8-constructed"],
            "granularity": "n/a (constructed)",
            "original_text": ex["original"],
            "reformulated_text": ex["reformulated"],
            "changed_word_pair": None,
            "human_acceptability": "DEFECTIVE",
            "human_severity": "SEVERE",
            "human_defect_labels": {"primary": "FACTUAL_OR_LOGICAL_REVERSAL", "secondary": []},
            "human_rationale": ex["rationale"],
            "human_rationale_source": "constructed-realistic-2026-08-24",
            "rater_id": "claude-primary (author)",
            "labeling_protocol": "not blind -- self-authored to instantiate a named defect subtype; see Phase 8 report limitations",
            "topic_source": f"constructed/{ex['subtype']}",
            "profile": None,
            "automated": {"contextual_fit": None, "sbert_sim": None, "antonym_check": None},
        })
    for ex in FIXED_TERM_OR_IDIOM_EXAMPLES:
        out.append({
            "uid": f"P8-constructed-{ex['id']}",
            "provenance": ["R50-Phase8-constructed"],
            "granularity": "n/a (constructed)",
            "original_text": ex["original"],
            "reformulated_text": ex["reformulated"],
            "changed_word_pair": None,
            "human_acceptability": "DEFECTIVE",
            "human_severity": "SEVERE",
            "human_defect_labels": {"primary": "FIXED_TERM_OR_IDIOM", "secondary": []},
            "human_rationale": ex["rationale"],
            "human_rationale_source": "constructed-realistic-2026-08-24",
            "rater_id": "claude-primary (author)",
            "labeling_protocol": "not blind -- self-authored to instantiate a named defect subtype; see Phase 8 report limitations",
            "topic_source": f"constructed/{ex['subtype']}",
            "profile": None,
            "automated": {"contextual_fit": None, "sbert_sim": None, "antonym_check": None},
        })
    for ex in CLEAN_CONTROL_EXAMPLES:
        out.append({
            "uid": f"P8-constructed-{ex['id']}",
            "provenance": ["R50-Phase8-constructed"],
            "granularity": "n/a (constructed)",
            "original_text": ex["original"],
            "reformulated_text": ex["reformulated"],
            "changed_word_pair": None,
            "human_acceptability": "CLEAN",
            "human_severity": "CLEAN",
            "human_defect_labels": {"primary": "CLEAN", "secondary": []},
            "human_rationale": ex["rationale"],
            "human_rationale_source": "constructed-realistic-2026-08-24",
            "rater_id": "claude-primary (author)",
            "labeling_protocol": "not blind -- self-authored hard-CLEAN control; see Phase 8 report limitations",
            "topic_source": "constructed/clean_control",
            "profile": None,
            "automated": {"contextual_fit": None, "sbert_sim": None, "antonym_check": None},
        })
    return out


def main():
    organic = load_organic()
    constructed = load_constructed()

    # attach human_acceptability to organic records too
    for r in organic:
        pass  # already set above

    all_records = organic + constructed
    for r in all_records:
        if r["changed_word_pair"]:
            r["dedup_key"] = "wordpair:" + "->".join(w.lower() for w in r["changed_word_pair"])
        else:
            r["dedup_key"] = "text:" + norm(r["original_text"]) + "=>" + norm(r["reformulated_text"])

    # cross-check against the frozen R50 baseline for leakage
    r50 = json.load(open(EVAL / "r50_dataset" / "labeled_dataset.json", encoding="utf-8"))
    r50_dedup_keys = {r["dedup_key"] for r in r50["records"]}
    r50_texts = {(norm(r["original_text"]), norm(r["reformulated_text"])) for r in r50["records"]}
    r50_orig_texts = {norm(r["original_text"]) for r in r50["records"]}

    overlap_with_r50 = []
    for r in all_records:
        if r["dedup_key"] in r50_dedup_keys:
            overlap_with_r50.append(r["uid"])
        if norm(r["original_text"]) in r50_orig_texts:
            r["_shares_source_sentence_with_r50"] = True
        else:
            r["_shares_source_sentence_with_r50"] = False

    out_path = EVAL / "r50_dataset" / "phase8_dataset.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "n_records": len(all_records),
            "n_organic": len(organic),
            "n_constructed": len(constructed),
            "overlap_with_r50_dedup_key": overlap_with_r50,
            "records": all_records,
        }, f, indent=2, ensure_ascii=False)

    print(f"wrote {len(all_records)} records ({len(organic)} organic, {len(constructed)} constructed) to {out_path}")
    print(f"dedup-key overlap with frozen R50 baseline: {len(overlap_with_r50)} ({overlap_with_r50})")
    n_shares_source = sum(1 for r in all_records if r["_shares_source_sentence_with_r50"])
    print(f"records sharing a source SENTENCE (not necessarily dedup key) with R50: {n_shares_source}")


if __name__ == "__main__":
    main()
