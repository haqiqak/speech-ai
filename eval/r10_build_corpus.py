"""
eval/r10_build_corpus.py -- Phase 10, steps 1-9: assemble, contamination-
check, build the (sentence,profile) run plan, and FREEZE the corpus.

Does NOT call reformulate() or any production code. Read-only w.r.t.
production; writes only new eval/ artifacts.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

EVAL = Path(__file__).parent
sys.path.insert(0, str(EVAL))
from r10_corpus_source import ALL_SENTENCES  # noqa: E402


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


# ---------------------------------------------------------------------
# Contamination check against every prior corpus's ORIGINAL sentences
# ---------------------------------------------------------------------
def prior_sentence_set():
    prior = set()

    from ceiling_probe_r40 import SENTENCES as r40_sentences
    prior.update(norm(t) for _, t in r40_sentences)

    from r50p8_corpus import SENTENCES as p8_sentences
    prior.update(norm(t) for _, t in p8_sentences)

    from r50p8b_corpus import SENTENCES as p8b_sentences
    prior.update(norm(t) for _, t in p8b_sentences)

    r47 = json.load(open(EVAL / "r47_fresh_sample_results.json", encoding="utf-8"))
    prior.update(norm(r["original_text"]) for r in r47["results"])

    return prior


def main():
    prior = prior_sentence_set()
    print(f"Prior-corpus sentence set size (R40+Phase8+Phase8B+R47): {len(prior)}")

    records = []
    collisions = []
    for i, (domain, subcat, source_type, source_ref, text, tags, opp) in enumerate(ALL_SENTENCES, start=1):
        key = norm(text)
        if key in prior:
            collisions.append((i, text))
            continue
        records.append({
            "sentence_id": f"R10-{i:03d}",
            "domain": domain,
            "subcategory": subcat,
            "linguistic_tags": tags,
            "expected_opportunity": opp,
            "sentence_text": text,
            "sentence_length_words": len(text.split()),
            "source_type": source_type,
            "source_reference": source_ref,
        })

    print(f"Collisions with prior corpora: {len(collisions)}")
    for i, t in collisions:
        print(f"  COLLISION at source index {i}: {t[:80]}")
    print(f"Frozen corpus size: {len(records)}")

    # -------------------------------------------------------------
    # Profile design (spec-dict format matching DifficultyProfile /
    # ceiling_probe_r40.PROFILES -- sounds/words/phrases).
    # -------------------------------------------------------------
    GENERIC_SOUND_PROFILES = {
        "single_sound": {"sounds": ["str"], "words": [], "phrases": []},
        "multi_sound": {"sounds": ["s", "th", "r"], "words": [], "phrases": []},
        "sparse_common_sound": {"sounds": ["s"], "words": [], "phrases": []},
        "dense_mixed_generic": {"sounds": ["s", "th", "r"], "words": ["important", "significant"], "phrases": []},
    }

    _STOP = {
        "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at", "for",
        "with", "by", "from", "as", "is", "was", "were", "are", "be", "been",
        "that", "this", "these", "those", "it", "its", "his", "her", "their",
        "which", "who", "into", "than", "then", "so", "not", "no", "if", "when",
        "while", "because", "such", "each", "other", "some", "any", "more",
        "most", "over", "under", "about", "there", "here", "has", "have", "had",
        "can", "could", "would", "will", "shall", "may", "might", "must",
    }

    def content_words(text, n):
        words = re.findall(r"[A-Za-z][A-Za-z'-]+", text)
        cands = [w for w in words if w.lower() not in _STOP and len(w) >= 5]
        # rarest/longest-first as a simple proxy for "most content-bearing"
        cands_sorted = sorted(set(cands), key=lambda w: -len(w))
        return [w.lower() for w in cands_sorted[:n]]

    N_BY_OPPORTUNITY = {"easy": 1, "moderate": 2, "hard": 3, "very_hard": 4}

    # Calibration subset: ~20 sentences spanning domains/opportunity tiers,
    # deterministic selection (every 6th-7th record, adjusted for spread).
    calibration_ids = set()
    step = max(1, len(records) // 20)
    for idx in range(0, len(records), step):
        calibration_ids.add(records[idx]["sentence_id"])
    calibration_ids = set(list(calibration_ids)[:22])

    run_plan = []
    for rec in records:
        sid = rec["sentence_id"]
        opp = rec["expected_opportunity"]
        n = N_BY_OPPORTUNITY[opp]
        own_words = content_words(rec["sentence_text"], max(n, 4))

        # -- CORE: 2 profiles per sentence --
        word_profile_words = own_words[:n] if own_words else []
        core_word_profile = {"sounds": [], "words": word_profile_words, "phrases": []}
        sound_pool = list(GENERIC_SOUND_PROFILES.items())
        sound_name, sound_spec = sound_pool[hash(sid) % len(sound_pool)]

        run_plan.append({"sentence_id": sid, "profile_id": f"{sid}-core-word",
                          "profile_type": "sentence_specific_word", "spec": core_word_profile})
        run_plan.append({"sentence_id": sid, "profile_id": f"{sid}-core-{sound_name}",
                          "profile_type": sound_name, "spec": sound_spec})

        if sid in calibration_ids:
            # -- CALIBRATION: remaining profile types for full-7 coverage --
            single_word_spec = {"sounds": [], "words": own_words[:1], "phrases": []}
            multi_word_spec = {"sounds": [], "words": own_words[:3] if len(own_words) >= 3 else own_words, "phrases": []}
            word_plus_sound_spec = {"sounds": ["pr"], "words": own_words[:1], "phrases": []}
            for pname, pspec in [
                ("single_word", single_word_spec),
                ("multi_word", multi_word_spec),
                ("word_plus_sound", word_plus_sound_spec),
            ]:
                run_plan.append({"sentence_id": sid, "profile_id": f"{sid}-calib-{pname}",
                                  "profile_type": pname, "spec": pspec})
            for sname, sspec in GENERIC_SOUND_PROFILES.items():
                pid = f"{sid}-calib-{sname}"
                if not any(r["profile_id"] == f"{sid}-core-{sname}" for r in run_plan):
                    run_plan.append({"sentence_id": sid, "profile_id": pid,
                                      "profile_type": sname, "spec": sspec})

    print(f"\nTotal (sentence, profile) runs planned: {len(run_plan)}")
    print(f"Calibration sentences (full 7-profile coverage): {len(calibration_ids)}")

    corpus_json = json.dumps({"records": records}, indent=2, ensure_ascii=False, sort_keys=True)
    corpus_hash = hashlib.sha256(corpus_json.encode("utf-8")).hexdigest()

    with open(EVAL / "r10_corpus.json", "w", encoding="utf-8") as f:
        json.dump({
            "corpus_version_hash": corpus_hash,
            "n_sentences": len(records),
            "n_technical": sum(1 for r in records if r["domain"] == "technical"),
            "n_general": sum(1 for r in records if r["domain"] == "general"),
            "prior_corpora_checked": ["R40 (48)", "Phase8 (54)", "Phase8B (42)", "R47 (10)"],
            "n_collisions_found_and_excluded": len(collisions),
            "records": records,
        }, f, indent=2, ensure_ascii=False)

    with open(EVAL / "r10_run_plan.json", "w", encoding="utf-8") as f:
        json.dump({
            "corpus_version_hash": corpus_hash,
            "n_runs": len(run_plan),
            "calibration_sentence_ids": sorted(calibration_ids),
            "generic_sound_profiles": GENERIC_SOUND_PROFILES,
            "runs": run_plan,
        }, f, indent=2, ensure_ascii=False)

    print(f"\nCorpus hash: {corpus_hash}")
    print(f"wrote eval/r10_corpus.json ({len(records)} sentences)")
    print(f"wrote eval/r10_run_plan.json ({len(run_plan)} runs)")

    # -------------------------------------------------------------
    # Coverage report
    # -------------------------------------------------------------
    from collections import Counter
    print("\n--- Domain coverage ---")
    print(Counter(r["subcategory"] for r in records))
    print("\n--- Opportunity-tier coverage ---")
    print(Counter(r["expected_opportunity"] for r in records))
    print("\n--- Linguistic-tag coverage (top counts) ---")
    tag_counts = Counter()
    for r in records:
        for t in r["linguistic_tags"]:
            tag_counts[t] += 1
    for t, c in tag_counts.most_common():
        print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
