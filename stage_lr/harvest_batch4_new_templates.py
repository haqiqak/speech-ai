"""
stage_lr/harvest_batch4_new_templates.py — Stage LR data path (a),
batch 4. NOT a repeat of "more sentences against the same 4 templates"
(explicitly ruled out, 2026-08-30 — "no number of additional sentences
moves this" profile-shape cap). This batch targets that exact cap
directly: 3 NEW profile shapes, deliberately messier and more
idiosyncratic than the original 4 — informed by what the first real
participant's profile actually looked like (a common sound mixed with
several unrelated, personally-anticipated words, not a tidy single
pattern). Reuses batch 3's 30 sentences unchanged (already vetted for
topic diversity) — only the templates are new, isolating template
diversity as the actual variable being tested.

    DISABLE_DATAMUSE=1 python stage_lr/harvest_batch4_new_templates.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("DISABLE_DATAMUSE", "1")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import paths  # noqa: F401,E402
import reformulate  # noqa: E402
from grammar import sanitize_input  # noqa: E402
from difficulty_profile import DifficultyProfile  # noqa: E402
from stage_lr.generate_pairs import attempt_second_candidate  # noqa: E402
from stage_lr.harvest_batch3 import SENTENCES  # noqa: E402 — reused unchanged

OUT_LOG = ROOT / "stage_lr" / "data" / "lr1_candidate_generation_log_batch4.json"

# 3 new shapes, deliberately NOT clean single-pattern templates like the
# original 4 (light_single_sound=['str'], moderate_mixed=['pr','gr']+2
# words, heavy_dense=['s','th','r']+3 words+1 phrase,
# single_common_sound=['s']) — mirrors the real participant's profile
# structure: a common sound plus a handful of specific, seemingly
# unrelated words, not one tidy rule.
NEW_TEMPLATES = {
    "messy_s_plus_unrelated_words": {
        "sounds": ["s"],
        "words": ["essential", "possibility", "necessary", "convenient", "opportunity"],
        "phrases": [],
    },
    "no_common_thread_multi_sound": {
        # Several UNRELATED onset classes together, not a natural
        # phonological family the way "s/th/r" arguably is.
        "sounds": ["th", "w", "k"],
        "words": ["quality", "wonderful"],
        "phrases": [],
    },
    "word_heavy_sparse_sound": {
        # Mostly declared words, only one light, uncommon sound —
        # mimics a profile driven by specific difficult words rather
        # than a systematic phonetic pattern.
        "sounds": ["gl"],
        "words": ["comfortable", "temperature", "vegetable", "library", "February"],
        "phrases": [],
    },
}


def build_profile(name: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__lr1_b4_{name}__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for ph in spec.get("phrases", []):
        p.add_phrase(ph, source="user_typed")
    return p


def main() -> None:
    results = []
    counts = {"total_sentence_profile_pairs": 0, "no_substitution_change": 0,
              "attempt_error": 0, "no_second_candidate": 0, "second_candidate_found": 0}

    i = 0
    total = len(SENTENCES) * len(NEW_TEMPLATES)
    for text in SENTENCES:
        corrected, _ = sanitize_input(text)
        for tname, spec in NEW_TEMPLATES.items():
            i += 1
            counts["total_sentence_profile_pairs"] += 1
            profile = build_profile(tname, spec)
            result = reformulate.reformulate(corrected, profile)

            sub_changes = [c for c in result.get("changes", []) if c.get("source") == "substitution"]
            uid = f"B4-{tname}-{i}"
            if not sub_changes:
                results.append({"uid": uid, "outcome": "no_substitution_change",
                                 "reason": f"status={result.get('status')}"})
                counts["no_substitution_change"] += 1
                print(f"[{i}/{total}] {tname:<28} no_substitution_change", flush=True)
                continue

            change = sub_changes[0]
            pseudo_record = {
                "uid": uid, "original_text": corrected,
                "reformulated_text": result["reformulated_text"],
                "changed_word_pair": [change["original"], change["replacement"]],
            }
            profile_entry = {"profile": profile, "profile_spec": {"name": tname, **spec},
                              "source": "harvest_batch4_new_templates.py (new profile shapes)"}
            try:
                res = attempt_second_candidate(pseudo_record, profile_entry)
            except Exception as e:
                counts["attempt_error"] += 1
                results.append({"uid": uid, "outcome": "attempt_error", "reason": f"{type(e).__name__}: {e}"})
                print(f"[{i}/{total}] {tname:<28} attempt_error: {e}", flush=True)
                continue

            counts[res["outcome"]] = counts.get(res["outcome"], 0) + 1
            results.append(res)
            print(f"[{i}/{total}] {tname:<28} {res['outcome']}", flush=True)

    OUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    OUT_LOG.write_text(json.dumps({"counts": counts, "results": results}, indent=2), encoding="utf-8")

    print()
    print("=== FINAL COUNTS (batch 4, new templates) ===")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
