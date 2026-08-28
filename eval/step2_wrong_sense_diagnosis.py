"""
eval/step2_wrong_sense_diagnosis.py -- Architecture Go/No-Go Step 2:
for every currently-DEFECTIVE, WRONG_WORD_OR_SENSE-labeled run in the
R10 corpus, expose the FULL candidate pool the production pipeline
actually considered (not just the winner it shipped), plus an extended
pool query at a much larger top_k, so the question "is the correct
word absent from the pool, or present but ranked below a worse one?"
can be answered from real data rather than assumed.

Substitution-tier cases: re-runs _raw_candidates() + rank_candidates_
contextually() for the exact flagged position, at both the production
top_k and an extended top_k=30, dumping every candidate with its score.

Escalation-tier (restructuring) cases: re-runs rephrase.generate_
candidates_phoneme_constrained() with the same parameters, dumping
every one of the k generated candidates (not just the one that passed
every gate), plus a larger k=15 pass for comparison.

Writes eval/step2_diagnosis_data.json -- one entry per case with full
context, for a non-blind (full-context) classification pass, same
methodology as Phase 10B's fixability analysis.

Run:
    python eval/step2_wrong_sense_diagnosis.py
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
import rephrase
from nltk import pos_tag, word_tokenize
from grammar import sanitize_input, lemmatize, inflect, _preserve_case, _wn_pos
from difficulty_profile import DifficultyProfile
import reformulate as rf

EVAL = Path(__file__).parent
EXTENDED_TOP_K = 30
EXTENDED_ESCALATION_K = 15


def build_profile(profile_id: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__step2_{profile_id}__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for ph in spec.get("phrases", []):
        p.add_phrase(ph, source="user_typed")
    return p


def diagnose_substitution(sentence: str, tokens: list[str], tags: list[tuple],
                           position: int, original_word: str, chosen_replacement: str,
                           profile, engine, settings) -> dict:
    tag = tags[position][1]
    base = lemmatize(original_word, tag)
    wn_p = _wn_pos(tag)
    context_window = rf._local_context_window(tokens, position)

    def pool_at(top_k):
        raw_cands = rf._raw_candidates(engine, base, tag, original_word, top_k, context=context_window)
        if not raw_cands:
            return []
        inflected_map = {lemma: _preserve_case(original_word, inflect(lemma, tag)) for lemma in raw_cands}
        min_semantic = settings.sbert_threshold if settings.sbert_threshold is not None else sem.MIN_SEMANTIC
        scored = sem.rank_candidates_contextually(
            original_sentence=sentence, word_to_replace=original_word, token_index=position,
            tokens=list(tokens), candidates=raw_cands, inflected_forms=inflected_map,
            min_semantic=min_semantic,
        )
        return [{"lemma": s["lemma"], "inflected": s["inflected"], "semantic_sim": s["semantic_sim"],
                  "accepted": s["accepted"]} for s in scored]

    production_pool = pool_at(settings.top_k)
    extended_pool = pool_at(EXTENDED_TOP_K)

    chosen_rank = None
    for i, c in enumerate(production_pool):
        if c["inflected"].lower() == chosen_replacement.lower():
            chosen_rank = i
            break

    return {
        "tier": "substitution",
        "original_word": original_word,
        "base_lemma": base,
        "chosen_replacement": chosen_replacement,
        "chosen_rank_in_production_pool": chosen_rank,
        "production_top_k": settings.top_k,
        "production_pool": production_pool,
        "extended_top_k": EXTENDED_TOP_K,
        "extended_pool": extended_pool,
    }


def diagnose_escalation(sentence: str, flagged_words: set, profile, settings) -> dict:
    blocked = flagged_words

    def gen_at(k):
        candidates, gen_stats = rephrase.generate_candidates_phoneme_constrained(
            sentence, k=k, blocked_words=blocked, blocked_patterns=profile.sound_values(),
        )
        return candidates, gen_stats

    production_candidates, prod_stats = gen_at(settings.t5_candidates)
    extended_candidates, ext_stats = gen_at(EXTENDED_ESCALATION_K)

    return {
        "tier": "restructuring",
        "production_k": settings.t5_candidates,
        "production_candidates": production_candidates,
        "production_beam_kills": prod_stats.get("beam_kills", 0),
        "extended_k": EXTENDED_ESCALATION_K,
        "extended_candidates": extended_candidates,
        "extended_beam_kills": ext_stats.get("beam_kills", 0),
    }


def main() -> int:
    corpus = json.load(open(EVAL / "r10_corpus.json", encoding="utf-8"))
    run_plan = json.load(open(EVAL / "r10_run_plan.json", encoding="utf-8"))
    raw = json.load(open(EVAL / "r11_reverify_raw_results.json", encoding="utf-8"))
    old_j = {}
    for f in EVAL.glob("r10_blind_batch_*_results.json"):
        old_j.update(json.load(open(f, encoding="utf-8")))
    new_j = json.load(open(EVAL / "r11_reverify_blind_merged.json", encoding="utf-8"))

    by_sentence = {r["sentence_id"]: r for r in corpus["records"]}
    by_run_id = {r["profile_id"]: r for r in run_plan["runs"]}
    raw_by_id = {r["run_id"]: r for r in raw["results"]}

    targets = []
    for run_id, r in raw_by_id.items():
        if r["status"] != "reformulated":
            continue
        j = new_j.get(run_id) or old_j.get(run_id)
        if j is None:
            continue
        if j["acceptability"] == "DEFECTIVE" and j["primary_defect"] == "WRONG_WORD_OR_SENSE":
            targets.append(run_id)

    print(f"Diagnosing {len(targets)} WRONG_WORD_OR_SENSE cases...")
    sem.load_sbert()
    engine = engine_module.SynonymEngine()
    settings = rf.ReformulateSettings()

    results = []
    for i, run_id in enumerate(targets, 1):
        run = by_run_id[run_id]
        sent = by_sentence[run["sentence_id"]]
        profile = build_profile(run["profile_id"], run["spec"])
        corrected_text, _ = sanitize_input(sent["sentence_text"])
        r = raw_by_id[run_id]

        tokens = word_tokenize(corrected_text)
        tags = pos_tag(tokens)

        change_diagnoses = []
        for change in r["changes"]:
            try:
                if change["source"] == "substitution":
                    pos = change["position"]
                    diag = diagnose_substitution(
                        corrected_text, tokens, tags, pos,
                        change["original"], change["replacement"],
                        profile, engine, settings,
                    )
                    change_diagnoses.append(diag)
                elif change["source"] == "restructuring":
                    # Same block set _try_escalation() computes: substitutable flagged words.
                    flagged_items = []
                    for t_i, (w, t) in enumerate(tags):
                        entry = profile.find_word(w.lower())
                        if entry is not None:
                            flagged_items.append(w.lower())
                    diag = diagnose_escalation(corrected_text, set(flagged_items), profile, settings)
                    change_diagnoses.append(diag)
            except Exception as exc:
                change_diagnoses.append({"error": str(exc), "source": change.get("source")})

        results.append({
            "run_id": run_id,
            "original_text": r["original_text"],
            "reformulated_text": r["reformulated_text"],
            "changes": r["changes"],
            "change_diagnoses": change_diagnoses,
        })
        print(f"  [{i}/{len(targets)}] {run_id}")

    (EVAL / "step2_diagnosis_data.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nwrote {len(results)} diagnoses to step2_diagnosis_data.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
