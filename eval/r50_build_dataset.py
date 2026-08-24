"""
R50 Phase 2 -- dataset construction and defect-taxonomy labeling.

Joins/dedupes the labeled evidence accumulated across R40, R44, R47, R48,
R49, and the v5 human pilot into one unified, provenance-tagged dataset,
and assigns a structured defect taxonomy (in addition to the existing
CLEAN/MINOR/SEVERE severity) to every example.

This is a RESEARCH-ONLY, DATASET-CONSTRUCTION script. It trains nothing
and touches no production code path. See eval/r50_dataset_report.md for
the resulting analysis and the sufficiency assessment.

Discipline (per direct instruction):
  - Human defect-type labels are assigned from the actual original/
    reformulated TEXT (and, for R40, the existing per-case rationale
    written when that text was originally read -- not from automated
    scores), never from nli_flag/grammar_flag/contextual_fit/sbert_sim.
  - Automated signals are attached as a SEPARATE, clearly-marked block
    and never overwrite a human label.
  - Where the documented evidence for a case is incomplete or was never
    recorded at per-case granularity, the case is marked UNCERTAIN (or
    its provenance is flagged) rather than inferring a label.
"""
import json
import re
from pathlib import Path

EVAL = Path(__file__).parent

# ---------------------------------------------------------------------------
# 1. R40 -- 112 human-audited substitutions. Severity + reason already exist
#    (eval/r40_change_audit_verdicts.json / _data.json, index-joined). What's
#    missing is the defect-TYPE taxonomy. Assigned below from a fresh read of
#    each case's original R40 reason + word pair (its severity call was
#    itself made from the full sentence text at R40 time) -- not from any
#    automated score.
# ---------------------------------------------------------------------------

R40_TAXONOMY = {
    1: ["WRONG_WORD_OR_SENSE"], 2: ["GRAMMAR"], 3: ["NATURALNESS_OR_REGISTER"],
    4: ["WRONG_WORD_OR_SENSE"], 5: ["WRONG_WORD_OR_SENSE"], 6: ["CLEAN"],
    7: ["WRONG_WORD_OR_SENSE"], 8: ["GRAMMAR"], 9: ["FIXED_TERM_OR_IDIOM"],
    10: ["GRAMMAR"], 11: ["NATURALNESS_OR_REGISTER"], 12: ["FIXED_TERM_OR_IDIOM"],
    13: ["NATURALNESS_OR_REGISTER"], 14: ["OTHER_DEFECT"],
    15: ["FACTUAL_OR_LOGICAL_REVERSAL", "WRONG_WORD_OR_SENSE"], 16: ["OTHER_DEFECT"],
    17: ["FACTUAL_OR_LOGICAL_REVERSAL", "WRONG_WORD_OR_SENSE"],
    18: ["NATURALNESS_OR_REGISTER"], 19: ["WRONG_WORD_OR_SENSE"],
    20: ["NATURALNESS_OR_REGISTER"], 21: ["CLEAN"], 22: ["CLEAN"], 23: ["CLEAN"],
    24: ["CLEAN"], 25: ["FIXED_TERM_OR_IDIOM"], 26: ["WRONG_WORD_OR_SENSE"],
    27: ["FIXED_TERM_OR_IDIOM"], 28: ["WRONG_WORD_OR_SENSE"], 29: ["WRONG_WORD_OR_SENSE"],
    30: ["GRAMMAR"], 31: ["WRONG_WORD_OR_SENSE", "FACTUAL_OR_LOGICAL_REVERSAL"],
    32: ["WRONG_WORD_OR_SENSE", "OTHER_DEFECT"], 33: ["OTHER_DEFECT"],
    34: ["NATURALNESS_OR_REGISTER"], 35: ["WRONG_WORD_OR_SENSE"], 36: ["CLEAN"],
    37: ["OTHER_DEFECT"], 38: ["OTHER_DEFECT"], 39: ["GRAMMAR"],
    40: ["NATURALNESS_OR_REGISTER"],
    41: ["FACTUAL_OR_LOGICAL_REVERSAL", "WRONG_WORD_OR_SENSE"], 42: ["GRAMMAR"],
    43: ["FACTUAL_OR_LOGICAL_REVERSAL"], 44: ["OTHER_DEFECT"],
    45: ["WRONG_WORD_OR_SENSE"], 46: ["WRONG_WORD_OR_SENSE"], 47: ["WRONG_WORD_OR_SENSE"],
    48: ["WRONG_WORD_OR_SENSE", "FACTUAL_OR_LOGICAL_REVERSAL"],
    49: ["WRONG_WORD_OR_SENSE"], 50: ["FACTUAL_OR_LOGICAL_REVERSAL"],
    51: ["WRONG_WORD_OR_SENSE", "FACTUAL_OR_LOGICAL_REVERSAL"],
    52: ["WRONG_WORD_OR_SENSE"], 53: ["OTHER_DEFECT"], 54: ["NATURALNESS_OR_REGISTER"],
    55: ["WRONG_WORD_OR_SENSE"],
    56: ["FACTUAL_OR_LOGICAL_REVERSAL", "WRONG_WORD_OR_SENSE"],
    57: ["FIXED_TERM_OR_IDIOM"], 58: ["FIXED_TERM_OR_IDIOM"], 59: ["FIXED_TERM_OR_IDIOM"],
    60: ["WRONG_WORD_OR_SENSE"], 61: ["FIXED_TERM_OR_IDIOM"], 62: ["WRONG_WORD_OR_SENSE"],
    63: ["WRONG_WORD_OR_SENSE"], 64: ["GRAMMAR"], 65: ["GRAMMAR"], 66: ["CLEAN"],
    67: ["GRAMMAR"], 68: ["FIXED_TERM_OR_IDIOM"], 69: ["WRONG_WORD_OR_SENSE"],
    70: ["WRONG_WORD_OR_SENSE"], 71: ["NATURALNESS_OR_REGISTER"],
    72: ["NATURALNESS_OR_REGISTER"],
    73: ["FACTUAL_OR_LOGICAL_REVERSAL", "WRONG_WORD_OR_SENSE"],
    74: ["WRONG_WORD_OR_SENSE"], 75: ["WRONG_WORD_OR_SENSE", "FACTUAL_OR_LOGICAL_REVERSAL"],
    76: ["NATURALNESS_OR_REGISTER"], 77: ["WRONG_WORD_OR_SENSE"], 78: ["CLEAN"],
    79: ["NATURALNESS_OR_REGISTER"], 80: ["WRONG_WORD_OR_SENSE"], 81: ["OTHER_DEFECT"],
    82: ["NATURALNESS_OR_REGISTER"],
    83: ["FACTUAL_OR_LOGICAL_REVERSAL", "WRONG_WORD_OR_SENSE"], 84: ["GRAMMAR"],
    85: ["FACTUAL_OR_LOGICAL_REVERSAL"], 86: ["OTHER_DEFECT"], 87: ["GRAMMAR"],
    88: ["WRONG_WORD_OR_SENSE"], 89: ["OTHER_DEFECT"], 90: ["OTHER_DEFECT"],
    91: ["WRONG_WORD_OR_SENSE"], 92: ["WRONG_WORD_OR_SENSE", "FACTUAL_OR_LOGICAL_REVERSAL"],
    93: ["WRONG_WORD_OR_SENSE"], 94: ["FACTUAL_OR_LOGICAL_REVERSAL"], 95: ["GRAMMAR"],
    96: ["NATURALNESS_OR_REGISTER"], 97: ["WRONG_WORD_OR_SENSE"], 98: ["OTHER_DEFECT"],
    99: ["NATURALNESS_OR_REGISTER"], 100: ["WRONG_WORD_OR_SENSE"],
    101: ["FIXED_TERM_OR_IDIOM"], 102: ["FIXED_TERM_OR_IDIOM"], 103: ["FIXED_TERM_OR_IDIOM"],
    104: ["WRONG_WORD_OR_SENSE"], 105: ["FIXED_TERM_OR_IDIOM"], 106: ["FIXED_TERM_OR_IDIOM"],
    107: ["NATURALNESS_OR_REGISTER"], 108: ["FIXED_TERM_OR_IDIOM"], 109: ["GRAMMAR"],
    110: ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"],
    111: ["WRONG_WORD_OR_SENSE", "FIXED_TERM_OR_IDIOM"], 112: ["GRAMMAR"],
}

def load_r40():
    data = json.load(open(EVAL / "r40_change_audit_data.json", encoding="utf-8"))["changes"]
    verdicts = json.load(open(EVAL / "r40_change_audit_verdicts.json", encoding="utf-8"))["verdicts"]
    v_by_idx = {v["index"]: v for v in verdicts}
    out = []
    for i, d in enumerate(data, start=1):
        v = v_by_idx[i]
        sev = v["verdict"]
        labels = ["CLEAN"] if sev == "CLEAN" else R40_TAXONOMY[i]
        out.append({
            "uid": f"R40-{i:03d}",
            "provenance": ["R40"],
            "granularity": "restructuring" if d["change_source"] != "substitution" else "substitution",
            "original_text": d["original_sentence"],
            "reformulated_text": d["reformulated_sentence"],
            "changed_word_pair": [d["original_word"], d["replacement_word"]] if d["change_source"] == "substitution" else None,
            "human_severity": sev,
            "human_defect_labels": {"primary": labels[0], "secondary": labels[1:]},
            "human_rationale": v["reason"],
            "human_rationale_source": "R40-original-read-2026-08-2x",
            "human_ratings": None,
            "automated": {
                "contextual_fit": d.get("contextual_fit"),
                "sbert_sim": d.get("sbert_sim"),
                "antonym_check": d.get("antonym_check"),
                "nli_flag": None, "grammar_flag": None, "grammar_matches": None,
            },
            "r40_index": i,
        })
    return out


def load_r44_flags():
    res = json.load(open(EVAL / "r44_substitution_validator_results.json", encoding="utf-8"))["results"]
    by_text = {}
    for r in res:
        by_text[(r["original_text"], r["reformulated_text"])] = r
    return by_text


def load_v5():
    return json.load(open(EVAL / "r_v5_merged.json", encoding="utf-8"))


# ---------------------------------------------------------------------------
# 2 & 3. R47 -- only the cases that actually produced a distinct output get
#    a defect label; "could_not_safely_reformulate" cases with byte-identical
#    output are kept separately as ORIGINAL_NO_CHANGE (no defect to label).
#    One case (presentation_renewable) has a v1 output that differs from the
#    input DESPITE status="could_not_safely_reformulate" -- a real grammar
#    defect introduced by sanitize_input() with no reformulation intended;
#    labeled here as its own case, not folded into the v2 restructuring case.
# ---------------------------------------------------------------------------

R47_LABELS = {
    "grab_presentation": {
        "output": "v1_and_v2",
        "severity": "MINOR",
        "labels": ["NATURALNESS_OR_REGISTER", "WRONG_WORD_OR_SENSE"],
        "rationale": "\"showing materials\" for \"presentation materials\": \"showing\" as a bare noun for a presentation is atypical (more naturally reads as a film/exhibit screening); comprehensible but odd register and a mild sense narrowing.",
    },
    "review_documents": {
        "output": "v1_and_v2",
        "severity": "MINOR",
        "labels": ["WRONG_WORD_OR_SENSE"],
        "rationale": "\"critique\" for \"review\" adds an evaluative/critical connotation not present in the original's neutral \"review\" -- a real but survivable sense narrowing.",
    },
    "restaurant_quiet": {
        "output": "v1_and_v2",
        "severity": "MINOR",
        "labels": ["WRONG_WORD_OR_SENSE", "NATURALNESS_OR_REGISTER"],
        "rationale": "\"diner\" for \"restaurant\" narrows to a specific casual-dining subtype; \"amazingly\" for \"surprisingly\" is a mild register shift. Both survivable.",
    },
    "children_playing": {
        "output": "v1_and_v2",
        "severity": "SEVERE",
        "labels": ["WRONG_WORD_OR_SENSE"],
        "rationale": "\"acting\" for \"playing\" (children in a garden) swaps the recreational sense of \"play\" for the performance/theatrical sense of \"act\" -- a real meaning change (R48 traced this to a WordNet hypernym relationship, play.v.05 -> act.v.08).",
    },
}

R47_V2_ONLY_LABELS = {
    "presentation_renewable": {
        "severity": "SEVERE",
        "labels": ["WRONG_WORD_OR_SENSE"],
        "rationale": "\"alternative energy\" is not equivalent to \"renewable energy\" (alternative energy includes non-renewable sources such as nuclear) -- a real technical-term substitution error that reads fluently. \"expositions\" for \"presentation\" is also unusually formal/rare (secondary register issue).",
    },
}

R47_V1_BUG_LABEL = {
    "id": "presentation_renewable_v1_sva_bug",
    "severity": "SEVERE",
    "labels": ["GRAMMAR"],
    "rationale": "v1 status is could_not_safely_reformulate (no reformulation intended) yet the returned text differs from the input: \"sources was\" -> \"sources were\", breaking correct subject-verb agreement with the sentence's true head noun (\"presentation\"). A third independent instance of the sanitize_input() SVA bug, found unprompted in R47.",
}

R47_NO_CHANGE_IDS = {
    "quickly_finished", "reschedule_strategy", "struggled_quantum",
    "weather_forecast", "research_discovered",
}


def load_r47():
    res = json.load(open(EVAL / "r47_fresh_sample_results.json", encoding="utf-8"))["results"]
    out = []
    for r in res:
        rid = r["id"]
        if rid in R47_NO_CHANGE_IDS:
            out.append({
                "uid": f"R47-{rid}-nochange",
                "provenance": ["R47"],
                "granularity": "n/a",
                "original_text": r["original_text"],
                "reformulated_text": r["original_text"],
                "changed_word_pair": None,
                "human_severity": "ORIGINAL_NO_CHANGE",
                "human_defect_labels": {"primary": "ORIGINAL_NO_CHANGE", "secondary": []},
                "human_rationale": "could_not_safely_reformulate in both v1 and v2; output identical to input.",
                "human_rationale_source": "fresh-2026-08-24",
                "human_ratings": None,
                "automated": {"contextual_fit": None, "sbert_sim": 1.0, "antonym_check": None,
                              "nli_flag": None, "grammar_flag": None, "grammar_matches": None},
                "r40_index": None,
            })
            continue
        lab = R47_LABELS.get(rid)
        if lab:
            out.append({
                "uid": f"R47-{rid}-v1v2",
                "provenance": ["R47"],
                "granularity": "substitution",
                "original_text": r["original_text"],
                "reformulated_text": r["v1"]["reformulated_text"],
                "changed_word_pair": None,
                "human_severity": lab["severity"],
                "human_defect_labels": {"primary": lab["labels"][0], "secondary": lab["labels"][1:]},
                "human_rationale": lab["rationale"],
                "human_rationale_source": "fresh-2026-08-24",
                "human_ratings": None,
                "automated": {"contextual_fit": None, "sbert_sim": r["v1"]["sbert"], "antonym_check": None,
                              "nli_flag": (r["v2"]["validation"] or {}).get("nli", {}).get("contradiction")
                              if r["v2"]["validation"] else None,
                              "grammar_flag": bool((r["v2"]["validation"] or {}).get("grammar_issue_count"))
                              if r["v2"]["validation"] else None,
                              "grammar_matches": None},
                "r40_index": None,
            })
        if rid in R47_V2_ONLY_LABELS and r["v2"]["status"] == "reformulated" and r["v1"]["status"] != "reformulated":
            lab = R47_V2_ONLY_LABELS[rid]
            out.append({
                "uid": f"R47-{rid}-v2only",
                "provenance": ["R47"],
                "granularity": "restructuring",
                "original_text": r["original_text"],
                "reformulated_text": r["v2"]["reformulated_text"],
                "changed_word_pair": None,
                "human_severity": lab["severity"],
                "human_defect_labels": {"primary": lab["labels"][0], "secondary": lab["labels"][1:]},
                "human_rationale": lab["rationale"],
                "human_rationale_source": "fresh-2026-08-24",
                "human_ratings": None,
                "automated": {"contextual_fit": None, "sbert_sim": r["v2"]["sbert"], "antonym_check": None,
                              "nli_flag": r["v2"]["validation"]["nli"]["contradiction"],
                              "grammar_flag": bool(r["v2"]["validation"]["grammar_issue_count"]),
                              "grammar_matches": None},
                "r40_index": None,
            })
        if rid == "presentation_renewable" and r["v1"]["reformulated_text"] != r["original_text"]:
            lab = R47_V1_BUG_LABEL
            out.append({
                "uid": f"R47-{lab['id']}",
                "provenance": ["R47"],
                "granularity": "n/a (unintended pipeline mutation)",
                "original_text": r["original_text"],
                "reformulated_text": r["v1"]["reformulated_text"],
                "changed_word_pair": None,
                "human_severity": lab["severity"],
                "human_defect_labels": {"primary": lab["labels"][0], "secondary": lab["labels"][1:]},
                "human_rationale": lab["rationale"],
                "human_rationale_source": "fresh-2026-08-24",
                "human_ratings": None,
                "automated": {"contextual_fit": None, "sbert_sim": r["v1"]["sbert"], "antonym_check": None,
                              "nli_flag": None, "grammar_flag": None, "grammar_matches": None},
                "r40_index": None,
            })
    return out


# ---------------------------------------------------------------------------
# 4. R48 -- 12 "reformulated" escalation-tier cases. Only 3 have a documented,
#    text-matched manual verdict in VALIDATION.md Sec 38.3 (the SEVERE ones);
#    the remaining 9 were only ever summarized in aggregate ("5 CLEAN, 4
#    MINOR"), never attached to specific sentences. Per direct instruction
#    not to infer where evidence is ambiguous: the 3 documented cases carry
#    that documented verdict; the other 9 get a FRESH read here, clearly
#    flagged as such (not a reconstruction of the original aggregate tally).
# ---------------------------------------------------------------------------

R48_LABELS = {
    0: {  # issues/develop -- R49 LLM-judge "GOOD" ground truth case
        "severity": "MINOR", "labels": ["NATURALNESS_OR_REGISTER"],
        "source": "fresh-2026-08-24",
        "rationale": "\"issues\" for \"problems\" and \"develop\" for \"grow\" are each defensible synonyms individually; \"as the issues develop\" is a slightly less idiomatic collocation than \"as the problems grow\" but not wrong.",
    },
    2: {  # hyphenation of GPT
        "severity": "MINOR", "labels": ["FIXED_TERM_OR_IDIOM"],
        "source": "fresh-2026-08-24",
        "rationale": "\"Generative pre-trained transformers\" is a fixed technical term (GPT); adding a hyphen (\"Generative-pre-trained\") is a nonstandard rendering of that term, though it does not change meaning.",
    },
    3: {  # systems/networks, reasoning/analyzing
        "severity": "MINOR", "labels": ["WRONG_WORD_OR_SENSE"],
        "source": "fresh-2026-08-24",
        "rationale": "\"computational networks\" narrows \"computational systems\" (AI includes non-networked systems, e.g. symbolic/rule-based AI); \"analyzing\" for \"reasoning\" is a related but distinct cognitive process. Real but mild imprecision in an abstract definitional sentence.",
    },
    4: {  # researchers/physicists
        "severity": "SEVERE", "labels": ["WRONG_WORD_OR_SENSE", "FACTUAL_OR_LOGICAL_REVERSAL"],
        "source": "fresh-2026-08-24",
        "rationale": "\"physicists\" for \"researchers\" asserts a specific (and likely incorrect) professional category not present in the original -- early AI researchers were predominantly computer scientists/mathematicians/cognitive scientists, not physicists specifically. Reads fluently while introducing an unsupported factual claim.",
    },
    8: {  # semantic relationships/meaning, sentences/phrases
        "severity": "SEVERE", "labels": ["WRONG_WORD_OR_SENSE"],
        "source": "fresh-2026-08-24",
        "rationale": "\"phrases\" is not equivalent to \"sentences\" (a phrase is a grammatical unit within a sentence, not interchangeable with it) -- a real technical-term substitution; \"meaning of words\" also drops the relational sense of \"semantic relationships\".",
    },
    9: {  # documented: atmosphere/space physics reversal
        "severity": "SEVERE", "labels": ["FACTUAL_OR_LOGICAL_REVERSAL"],
        "source": "documented-VALIDATION-38.3",
        "rationale": "\"radiating into space\" -> \"emitted into the atmosphere\" reverses the actual physical claim (heat escaping the system vs. heat staying within it) while reading fluently and topically coherently; nothing in the pipeline is built to catch this class.",
    },
    11: {  # documented: replaced/displaced wrong-word
        "severity": "SEVERE", "labels": ["WRONG_WORD_OR_SENSE", "OTHER_DEFECT"],
        "source": "documented-VALIDATION-38.3",
        "rationale": "\"not replaced by new trees\" -> \"not displaced by new trees\" is a direct wrong-word error (documented, recurring independently of A2). Secondary: the restructured clause \"contributor to the global warming of land use change\" garbles the original's actual relationship (deforestation -> [via land use change] -> global warming) into a backwards-reading compound.",
    },
    12: {  # starch/cornstarch -- documented genuine improvement
        "severity": "CLEAN", "labels": ["CLEAN"],
        "source": "documented-VALIDATION-38.3",
        "rationale": "\"cornstarch\" is a genuinely correct concrete example of a long-chain sugar, replacing the earlier buggy candidate (\"glucose\", scientifically backwards) once that candidate was excluded by the NLI gate -- a real quality improvement, not just a safer refusal.",
    },
    13: {  # attain/cooking -- R49 LLM-judge GOOD case
        "severity": "MINOR", "labels": ["NATURALNESS_OR_REGISTER"],
        "source": "fresh-2026-08-24",
        "rationale": "\"attain\" for \"reach\" is a clean synonym; \"cooking\" for \"sautéing\" is a hypernym substitution that loses specificity (sautéing is a specific cooking method) but remains technically true, not wrong.",
    },
    15: {  # documented: small talk -> little talk fixed-term erosion
        "severity": "SEVERE", "labels": ["FIXED_TERM_OR_IDIOM"],
        "source": "documented-VALIDATION-38.3",
        "rationale": "\"small talk\" -> \"little talk\" is the long-standing fixed-term-erosion gap (REFORMULATION_PROBLEM_MAP.md Sec 3.1); \"small talk\" is this article's own named subject, not interchangeable with a literal size descriptor.",
    },
    17: {  # small talk -> short talk, "a lesser importance"
        "severity": "MINOR", "labels": ["GRAMMAR", "WRONG_WORD_OR_SENSE"],
        "source": "fresh-2026-08-24 (differs slightly from R48's prose characterization)",
        "rationale": "R48 characterized this as \"genuinely fine... with one real grammar slip\". Fresh read confirms the grammar slip (\"generally a lesser importance than\" is ungrammatical) but also finds \"function in the community\" loses the specific sociological sense of \"social function\" -- a real, if secondary, sense shift beyond the grammar issue alone.",
    },
}

# The one case in R48's history that was CORRECTLY REJECTED by the new
# per-candidate NLI gate, not shipped -- included as a critical negative
# training/eval example even though it never reached the final JSON
# (it existed only in the intermediate, ungated run). Full sentence text
# is reconstructed from the fixed portion of the source sentence (verified
# in v5 pair_06 / R40 #7) plus the documented word-level flip; the exact
# full escalated sentence was not preserved in any stored artifact.
R48_REJECTED_ANTONYM_CASE = {
    "uid": "R48-rejected-rational-irrational",
    "provenance": ["R48", "R49-llm-judge-crosscheck"],
    "granularity": "restructuring",
    "original_text": "A rational agent has goals or preferences and takes actions to make them happen.",
    "reformulated_text": "[reconstruction, NOT verified against a stored artifact] An irrational agent has goals or preferences and takes actions to make them happen.",
    "changed_word_pair": ["rational", "irrational"],
    "human_severity": "SEVERE",
    "human_defect_labels": {"primary": "FACTUAL_OR_LOGICAL_REVERSAL", "secondary": ["WRONG_WORD_OR_SENSE"]},
    "human_rationale": "Direct antonym flip -- the single worst class of error this project tracks. Cleared SBERT (0.8777), negation-consistency, and the leak check cleanly; caught only by NLI. Correctly rejected once NLI became a real per-candidate gate (not shipped in the final v3 pipeline) -- included here as a confirmed-dangerous negative example for validator training/eval, with the caveat that the exact full reformulated sentence text was never written to a stored JSON artifact and is reconstructed here from the documented word-level description.",
    "human_rationale_source": "documented-VALIDATION-38.3 (word-level only; sentence text reconstructed, UNVERIFIED)",
    "human_ratings": None,
    "automated": {"contextual_fit": None, "sbert_sim": 0.8777, "antonym_check": None,
                  "nli_flag": True, "grammar_flag": None, "grammar_matches": None},
    "r40_index": None,
    "text_verification": "UNCERTAIN",
}


def load_r48():
    res = json.load(open(EVAL / "r48_v3_verification_results.json", encoding="utf-8"))["results"]
    out = []
    for i, r in enumerate(res):
        if r["status"] != "reformulated":
            continue
        lab = R48_LABELS.get(i)
        if lab is None:
            continue
        out.append({
            "uid": f"R48-{i:02d}",
            "provenance": ["R48"],
            "granularity": "restructuring",
            "original_text": r["original_text"],
            "reformulated_text": r["reformulated_text"],
            "changed_word_pair": None,
            "human_severity": lab["severity"],
            "human_defect_labels": {"primary": lab["labels"][0], "secondary": lab["labels"][1:]},
            "human_rationale": lab["rationale"],
            "human_rationale_source": lab["source"],
            "human_ratings": None,
            "automated": {
                "contextual_fit": None, "sbert_sim": r.get("sbert"), "antonym_check": None,
                "nli_flag": (r["validation"]["nli"] or {}).get("contradiction") if r.get("validation") else None,
                "grammar_flag": bool(r["validation"].get("grammar_issue_count")) if r.get("validation") else None,
                "grammar_matches": None,
            },
            "r40_index": None,
            "r48_result_index": i,
        })
    out.append(R48_REJECTED_ANTONYM_CASE)
    return out


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def main():
    r40 = load_r40()
    r44_flags = load_r44_flags()
    v5 = load_v5()
    r47 = load_r47()
    r48 = load_r48()

    # attach R44 automated flags to matching R40 records (same text)
    r40_by_text = {(norm(r["original_text"]), norm(r["reformulated_text"])): r for r in r40}
    n_r44_matched = 0
    for (o, rf), rec in r44_flags.items():
        key = (norm(o), norm(rf))
        if key in r40_by_text:
            t = r40_by_text[key]
            t["automated"]["nli_flag"] = rec["nli_flag"]
            t["automated"]["grammar_flag"] = rec["grammar_flag"]
            t["automated"]["grammar_matches"] = rec["grammar_matches"]
            t["provenance"].append("R44")
            n_r44_matched += 1

    # attach v5 human ratings to matching R40 records (v5 = verbatim R40 subset)
    n_v5_matched = 0
    n_v5_unmatched = 0
    for p in v5:
        key = (norm(p["original"]), norm(p["reformulated"]))
        if key in r40_by_text:
            t = r40_by_text[key]
            t["human_ratings"] = {
                "meaning": p["meaning"], "naturalness": p["naturalness"],
                "ease": p["ease"], "preference": p["preference"],
                "v5_pair_id": p["pair_id"], "v5_claude_verdict": p["claude_verdict"],
                "v5_defect_label_freetext": p["defect_label"],
            }
            t["provenance"].append("v5")
            n_v5_matched += 1
        else:
            n_v5_unmatched += 1

    dataset = r40 + r47 + r48

    # dedup key for leakage-safe splitting: word-pair based for substitutions
    # (many R40 rows are the exact same substitution on a different sentence,
    # or the literal same sentence duplicated for a different profile), and
    # normalized-text based otherwise.
    for rec in dataset:
        if rec["changed_word_pair"]:
            rec["dedup_key"] = "wordpair:" + "->".join(w.lower() for w in rec["changed_word_pair"])
        else:
            rec["dedup_key"] = "text:" + norm(rec["original_text"])

    out_path = EVAL / "r50_dataset"
    out_path.mkdir(exist_ok=True)
    with open(out_path / "labeled_dataset.json", "w", encoding="utf-8") as f:
        json.dump({
            "n_records": len(dataset),
            "n_r44_matched_to_r40": n_r44_matched,
            "n_v5_matched_to_r40": n_v5_matched,
            "n_v5_unmatched": n_v5_unmatched,
            "records": dataset,
        }, f, indent=2, ensure_ascii=False)

    print(f"wrote {len(dataset)} records to {out_path / 'labeled_dataset.json'}")
    print(f"R44 flags matched to {n_r44_matched}/{len(r44_flags)} R40 records")
    print(f"v5 ratings matched to {n_v5_matched}/{len(v5)} v5 pairs ({n_v5_unmatched} unmatched)")


if __name__ == "__main__":
    main()
