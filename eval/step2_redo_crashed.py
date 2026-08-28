"""
eval/step2_redo_crashed.py -- re-diagnose the 19 restructuring-tier
cases that crashed in the first step2_wrong_sense_diagnosis.py run due
to a dead-code bug (profile.words is a list of DifficultyEntry objects,
not strings; the removed line called .lower() on them directly).
Updates eval/step2_diagnosis_data.json in place for just these run_ids.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic as sem
import engine as engine_module
from nltk import pos_tag, word_tokenize
from grammar import sanitize_input
import reformulate as rf
import step2_wrong_sense_diagnosis as s2

EVAL = Path(__file__).parent

CRASHED = [
    'R10-001-calib-dense_mixed_generic', 'R10-016-core-word', 'R10-034-core-word',
    'R10-037-core-word', 'R10-037-calib-single_word', 'R10-037-calib-word_plus_sound',
    'R10-043-core-word', 'R10-043-calib-multi_word', 'R10-044-core-dense_mixed_generic',
    'R10-047-core-dense_mixed_generic', 'R10-065-core-word', 'R10-070-core-word',
    'R10-079-calib-multi_word', 'R10-080-core-word', 'R10-103-calib-dense_mixed_generic',
    'R10-109-core-word', 'R10-109-calib-multi_word', 'R10-123-core-word', 'R10-124-core-word',
]


def main() -> int:
    corpus = json.load(open(EVAL / "r10_corpus.json", encoding="utf-8"))
    run_plan = json.load(open(EVAL / "r10_run_plan.json", encoding="utf-8"))
    raw = json.load(open(EVAL / "r11_reverify_raw_results.json", encoding="utf-8"))
    data = json.load(open(EVAL / "step2_diagnosis_data.json", encoding="utf-8"))
    data_by_id = {d["run_id"]: d for d in data}

    by_sentence = {r["sentence_id"]: r for r in corpus["records"]}
    by_run_id = {r["profile_id"]: r for r in run_plan["runs"]}
    raw_by_id = {r["run_id"]: r for r in raw["results"]}

    sem.load_sbert()
    engine = engine_module.SynonymEngine()
    settings = rf.ReformulateSettings()

    for i, run_id in enumerate(CRASHED, 1):
        run = by_run_id[run_id]
        sent = by_sentence[run["sentence_id"]]
        profile = s2.build_profile(run["profile_id"], run["spec"])
        corrected_text, _ = sanitize_input(sent["sentence_text"])
        r = raw_by_id[run_id]

        tokens = word_tokenize(corrected_text)
        tags = pos_tag(tokens)

        change_diagnoses = []
        for change in r["changes"]:
            try:
                if change["source"] == "substitution":
                    diag = s2.diagnose_substitution(
                        corrected_text, tokens, tags, change["position"],
                        change["original"], change["replacement"],
                        profile, engine, settings,
                    )
                    change_diagnoses.append(diag)
                elif change["source"] == "restructuring":
                    flagged_items = []
                    for t_i, (w, t) in enumerate(tags):
                        entry = profile.find_word(w.lower())
                        if entry is not None:
                            flagged_items.append(w.lower())
                    diag = s2.diagnose_escalation(corrected_text, set(flagged_items), profile, settings)
                    change_diagnoses.append(diag)
            except Exception as exc:
                change_diagnoses.append({"error": str(exc), "source": change.get("source")})

        data_by_id[run_id]["change_diagnoses"] = change_diagnoses
        print(f"[{i}/{len(CRASHED)}] {run_id} -> {[d.get('tier', d.get('error')) for d in change_diagnoses]}")

    (EVAL / "step2_diagnosis_data.json").write_text(
        json.dumps(list(data_by_id.values()), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("updated step2_diagnosis_data.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
