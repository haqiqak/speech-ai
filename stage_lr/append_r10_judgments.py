"""One-off script: builds the 41 judged R10-batch pairs from the
generation log + the judgments made in review, and appends them to the
existing stage_lr/data/lr1_preference_pairs.json (single running
dataset, not a parallel file). Run once; not part of the regular
pipeline.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "stage_lr" / "data" / "lr1_candidate_generation_log_r10.json"
OUT = ROOT / "stage_lr" / "data" / "lr1_preference_pairs.json"

data = json.loads(LOG.read_text(encoding="utf-8"))
found = {r["uid"]: r for r in data["results"] if r["outcome"] == "second_candidate_found"}

# (representative_uid, all uids in the dedup group, preferred, reason)
JUDGMENTS = [
    (["R10-001-core-word::pos18", "R10-001-calib-single_word::pos18", "R10-001-calib-word_plus_sound::pos18"], "B",
     "A creates an awkward, confusing duplicate word ('absorbed and absorbed'). B avoids the repetition and 'imbibed' is a plausible, if slightly formal, near-synonym for taking in nutrients."),
    (["R10-004-core-word::pos11"], "A",
     "'Small bowel' is standard anatomical terminology for 'small intestine' — accurate and natural. 'Small gut' is a less natural collocation; 'gut' alone is the common usage, not usually modified by 'small'."),
    (["R10-005-core-word::pos5"], "B",
     "A ('assumed') is a severe, nonsensical meaning substitution — has nothing to do with being physically taken back into the blood. B ('absorbed') loses the 're-' nuance but preserves the core physical-process meaning coherently."),
    (["R10-009-core-word::pos16"], "A",
     "'Compounds' stays within the correct chemical/biological domain, a plausible near-synonym for molecules. 'Units' is too generic and loses the specific chemical meaning entirely."),
    (["R10-010-core-word::pos18"], "A",
     "'Beings' stays within a plausible 'living things' semantic space appropriate for organisms being consumed. 'Systems' is a severe, nonsensical substitution — you don't consume a system."),
    (["R10-012-core-dense_mixed_generic::pos7"], "tie",
     "'Quick decrease' and 'fast decrease' are both natural, accurate, near-synonymous substitutions for 'sudden' here — no meaningful quality difference."),
    (["R10-020-core-dense_mixed_generic::pos28"], "B",
     "A breaks the core physics meaning: 'the value at which momentum is changing' isn't coherent (a value doesn't have a rate; this loses the entire 'speed of change' concept 'rate' was expressing). B ('pace') is a natural, meaning-preserving substitution in this exact 'rate/pace at which X changes' construction."),
    (["R10-021-core-sparse_common_sound::pos13"], "B",
     "Both are odd, but 'the like magnitude' at least gestures toward 'similar/equal' (an archaic but interpretable phrasing), while 'the one magnitude' reads as a clearer determiner/grammar error with less recoverable meaning."),
    (["R10-031-calib-multi_sound::pos32", "R10-031-calib-sparse_common_sound::pos32", "R10-031-calib-dense_mixed_generic::pos32"], "B",
     "A ('below the open') is nonsensical — 'the open' as a bare noun doesn't fit here. B ('below the layer'), while vague about which layer, stays within plausible geological-structure vocabulary."),
    (["R10-040-core-word::pos14"], "B",
     "A ('cloudless terms') uses the contract/agreement sense of 'terms', nonsensical for weather description. B ('cloudless states') stays closer to the intended condition/status meaning, even if slightly awkward."),
    (["R10-048-core-multi_sound::pos11"], "A",
     "'Quits' is the natural, common way to describe a program/algorithm terminating. 'Discontinues' is accurate but carries a register mismatch, more typical of product lines than execution halting."),
    (["R10-052-core-word::pos18"], "B",
     "'Quantitative' is a more precise semantic match for 'numerical' (expressed as numbers/quantities) than 'mathematical', which names a broader field. Both work, but B is the closer fit."),
    (["R10-064-core-multi_sound::pos3"], "tie",
     "Both substitute an unrelated sense of 'civil' for its 'civil engineering' technical/proper-noun-adjacent meaning — 'official' invents a status the original didn't have, 'polite' uses the courtesy sense entirely wrongly. A genuine word-sense-disambiguation failure either way."),
    (["R10-069-core-dense_mixed_generic::pos1"], "B",
     "'Told' is transitive and needs an object ('told them') — 'told she might be late' is a harder grammar violation. 'Expressed' is mildly awkward (missing 'that') but a smaller violation."),
    (["R10-072-core-word::pos5"], "tie",
     "'Maybe' and 'likely' are both natural, accurate substitutes for 'probably' here — no clear quality difference."),
    (["R10-073-core-word::pos1", "R10-073-calib-single_word::pos1"], "A",
     "'Prof' preserves the specific role meaning (professor) despite being informal in register. 'Academic' is broader — loses the specific 'teacher explaining a concept' role implication."),
    (["R10-073-calib-word_plus_sound::pos1"], "B",
     "'Faculty' is typically a collective noun (a body of professors/a department), so 'the faculty explained' introduces a confusing single-vs-collective mismatch for describing one professor. 'Academic' is grammatically clean, even though it loses some role-specificity."),
    (["R10-075-core-dense_mixed_generic::pos5"], "B",
     "'Examined' preserves the 'engaged with course material' sense of 'studied' more closely. 'Considered' drifts toward 'pondered', a mild sense weakening."),
    (["R10-079-core-sparse_common_sound::pos5"], "B",
     "A ('take their reports') is close to a meaning reversal — take and submit are near-opposite transfer directions. B ('propose their reports') is imprecise but at least preserves an offering/presenting directionality."),
    (["R10-080-core-multi_sound::pos9"], "B",
     "A ('deadlines might trip') is a category error — deadlines can't physically stumble, nonsensical. B ('deadlines might decline') carries a directional/negative-shift sense at least loosely compatible with 'slip'."),
    (["R10-084-core-word::pos11"], "A",
     "'The past week' is completely natural and standard. 'The old week' is not idiomatic English — weeks aren't described as 'old' this way."),
    (["R10-088-core-sparse_common_sound::pos7"], "B",
     "(Note: 'skipped'->'missed' also changed in both sentences, held constant across A and B, not part of this comparison.) 'View everything' fits the museum-exhibit context slightly more naturally than 'watch everything', which implies more sustained/continuous observation."),
    (["R10-093-core-word::pos14"], "B",
     "A ('time to produce') is grammatically incomplete — 'produce' is transitive and needs an object here. B ('time to grow') is natural, idiomatic, and grammatically sound for flavors developing."),
    (["R10-096-core-single_sound::pos4"], "A",
     "'Down the road' is completely natural and idiomatic. 'Down the neighborhood' is a non-standard, awkward collocation (you'd say 'in the neighborhood')."),
    (["R10-097-core-word::pos1", "R10-097-calib-single_word::pos1", "R10-097-calib-word_plus_sound::pos1"], "A",
     "A is essentially the same word (British spelling variant 'apologised'), perfectly natural. B ('excused for') has a real grammar error — 'excused' normally needs a reflexive object ('excused herself')."),
    (["R10-098-core-word::pos2"], "B",
     "'Regarded' is a much closer semantic match to 'considered' (both mean viewed/thought of as). Both have a minor missing-preposition issue ('regarded/taken AS impolite'), but 'taken impolite' reads as more broken than 'regarded impolite'."),
    (["R10-100-core-multi_sound::pos12"], "A",
     "'Find each other' is an imperfect but plausible reading (locating time to meet). 'Play each other' introduces a wrong competitive/sports sense entirely inappropriate for old friends socializing."),
    (["R10-101-core-sparse_common_sound::pos2"], "A",
     "'Shocked' preserves the surprise-emotion meaning closely (a stronger degree, same direction). 'Impressed' substitutes an unrelated, different emotional response (admiration, not being caught off guard)."),
    (["R10-102-core-dense_mixed_generic::pos8"], "tie",
     "Both substitutions introduce the identical missing-article grammar error ('meeting person'/'meeting individual' instead of 'meeting A person'/'AN individual') — no quality difference between the two words themselves."),
    (["R10-103-core-word::pos6", "R10-103-calib-single_word::pos6", "R10-103-calib-word_plus_sound::pos6"], "B",
     "(Note: 'creaked'->'noised' also changed in both sentences, held constant across A and B, not part of this comparison.) A ('a narrow stairs') has a real number-agreement error — 'stairs' is plural, mismatching the singular article. B ('a narrow stairway') is grammatically clean and a natural, accurate synonym."),
    (["R10-107-core-word::pos6", "R10-107-core-dense_mixed_generic::pos6"], "A",
     "A ('a weird noise') is natural, accurate, near-perfect. B ('a other noise') has both a grammar error (a/an mismatch) and a meaning shift toward 'different/additional' rather than 'unusual'."),
    (["R10-109-calib-single_word::pos8", "R10-109-calib-word_plus_sound::pos8"], "A",
     "'Substitute' is imperfectly phrased (usually needs 'for'/'with') but retains the core 'swap out' meaning of replace. 'Regenerate' substitutes a completely different concept — regrowth/restoration, not replacement with something new."),
    (["R10-111-core-word::pos4"], "tie",
     "(Note: 'seconds'->'times' also changed in both sentences, held constant across A and B, not part of this comparison.) Both substitute a verb-like/action word for what should be a physical object noun (the button itself), producing similarly awkward 'press and hold the [verb]' constructions. Neither is clearly better, though 'push' has some loose association with 'push-button'."),
    (["R10-113-core-dense_mixed_generic::pos7"], "tie",
     "Both substitute the literal/physical-walking sense of 'step' (paces, footsteps) for its procedural/sequential sense in a manual — a genuine word-sense failure either way, not one candidate being clearly better."),
    (["R10-115-calib-multi_sound::pos1", "R10-115-calib-dense_mixed_generic::pos1"], "A",
     "'Believe' is a precise, natural synonym for 'think' as an opinion marker. 'Mean' serves a different discourse function (clarifying/rephrasing a prior statement), a real functional meaning shift."),
    (["R10-122-core-word::pos10"], "B",
     "A ('manufacturings') has a real grammar error — 'manufacturing' is normally uncountable, this pluralization is non-standard. B ('manufactories') is a real, grammatically valid (if old-fashioned) word meaning factories."),
    (["R10-124-core-multi_sound::pos11"], "B",
     "'Municipality' is administratively accurate and doesn't imply a smaller scale (a city is a type of municipality). 'Town' introduces an unwarranted scale-down assumption relative to 'city'."),
    (["R10-125-core-word::pos14"], "B",
     "A ('opens newer') is nonsensical — 'newer' relates to recency of existence, not time-of-day, a wrong-sense substitution. B ('opens earliest') has a comparative/superlative mismatch but stays within the correct 'opening time' semantic domain."),
    (["R10-129-core-word::pos14"], "B",
     "A ('earned a two-year studies') has a real singular/plural agreement error. B ('earned a two-year aid') is a little ambiguous in its 'to' attachment but avoids that grammar problem and stays closer to the 'financial support' meaning of scholarship."),
    (["R10-129-core-dense_mixed_generic::pos14"], "B",
     "A ('earned a two-year learning') has an awkward countability issue (learning is normally uncountable) and shifts meaning toward 'knowledge gained' rather than 'financial award'. B ('aid') retains the financial-support sense central to 'scholarship'."),
    (["R10-131-core-word::pos11"], "A",
     "'Indicated' is grammatically clean and a reasonably close synonym for 'suggested'. 'Informed that' has a mild missing-object awkwardness (usually 'informed HIM that'), a smaller but real quality gap."),
]

pairs_out = []
for uids, preferred, reason in JUDGMENTS:
    r0 = found[uids[0]]
    pairs_out.append({
        "source_uids": uids,
        "original_sentence": r0["original_sentence"],
        "difficulty_profile": r0["profile_spec"],
        "flagged_word": r0["original_word"],
        "candidate_A": r0["candidate_a"],
        "candidate_B": r0["candidate_b"],
        "preferred": preferred,
        "reason": reason,
    })

R10_CONTAMINATED_UIDS = [
    "R10-001-core-word::pos10", "R10-008-core-dense_mixed_generic::pos12", "R10-008-core-dense_mixed_generic::pos27",
    "R10-017-core-word::pos4", "R10-017-core-word::pos6", "R10-022-core-word::pos4", "R10-022-core-word::pos6",
    "R10-032-core-dense_mixed_generic::pos1", "R10-032-core-dense_mixed_generic::pos11",
    "R10-042-core-dense_mixed_generic::pos17", "R10-044-core-word::pos4", "R10-044-core-word::pos7",
    "R10-052-core-word::pos1", "R10-064-core-word::pos2", "R10-064-core-word::pos10", "R10-071-core-word::pos3",
    "R10-071-core-word::pos8", "R10-072-core-word::pos1", "R10-074-core-word::pos5", "R10-074-core-word::pos7",
    "R10-076-core-sparse_common_sound::pos2", "R10-076-core-sparse_common_sound::pos5", "R10-083-core-word::pos12",
    "R10-083-core-word::pos16", "R10-084-core-multi_sound::pos6", "R10-086-core-word::pos6",
    "R10-086-core-word::pos12", "R10-093-core-word::pos9", "R10-098-core-dense_mixed_generic::pos6",
    "R10-098-core-dense_mixed_generic::pos10", "R10-103-core-word::pos8", "R10-128-core-sparse_common_sound::pos8",
]

existing = json.loads(OUT.read_text(encoding="utf-8"))
existing["pairs"].extend(pairs_out)
existing["excluded_multi_word_contaminated"]["uids"].extend(R10_CONTAMINATED_UIDS)
existing["excluded_multi_word_contaminated"]["note"] += (
    " (Batch 2, R10 source, added same guardrail: 32 more excluded here.)"
)
existing["_meta"]["batch_2_r10"] = {
    "source": "eval/r10_raw_results.json (Phase 10, 398 runs, never covered by the 135 labeled_dataset.json records)",
    "total_substitution_changes_examined": data["counts"]["total_substitution_changes"],
    "second_candidates_found_raw": data["counts"]["second_candidate_found"],
    "excluded_multi_word_contaminated": 32,
    "clean_single_variable_pairs_raw": 53,
    "unique_pairs_after_dedup": 41,
    "judged": 41,
}
existing["_meta"]["running_total_judged_pairs"] = len(existing["pairs"])

OUT.write_text(json.dumps(existing, indent=2), encoding="utf-8")
print("Appended", len(pairs_out), "pairs. Running total:", len(existing["pairs"]))
