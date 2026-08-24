"""
eval/r50p8b_harvest.py -- R50 Phase 8, step 1: run the NEW 54-sentence
corpus (eval/r50p8b_corpus.py) through TODAY's live production engine
(reformulate.reformulate(), the same function app.py calls by default)
across the same 4 profiles R40 used, and capture every individual change
-- exactly R40's own methodology (eval/r40_change_audit.py), applied to
genuinely new source material so the resulting examples are independent
evidence, not a re-read of R40-R49.

RESEARCH ONLY. Calls only the existing reformulate.reformulate() entry
point exactly as app.py does by default -- no production code is
modified, no threshold changed, no new capability added.

Run:
    python eval/r50p8b_harvest.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic
from grammar import sanitize_input
from difficulty_profile import DifficultyProfile
import reformulate

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r50p8b_corpus import SENTENCES, PROFILES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "eval" / "r50_dataset" / "phase8b_raw_harvest.json"


def _build_profile(tag: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__r50p8b_{tag}__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    return p


def main() -> int:
    semantic.load_sbert()
    changes_out = []
    no_change_out = []
    total = len(SENTENCES) * len(PROFILES)
    done = 0
    for profile_name, spec in PROFILES.items():
        for source, text in SENTENCES:
            done += 1
            profile = _build_profile(profile_name, spec)
            corrected_text, _ = sanitize_input(text)
            result = reformulate.reformulate(corrected_text, profile)
            if result["status"] != "reformulated":
                no_change_out.append({
                    "source": source, "profile": profile_name,
                    "original_text": corrected_text, "status": result["status"],
                })
                print(f"  [{done}/{total}] {profile_name:<22} {source:<24} no change ({result['status']})", flush=True)
                continue
            for c in result["changes"]:
                v = c["verification"]
                changes_out.append({
                    "source": source,
                    "profile": profile_name,
                    "change_source": c["source"],
                    "triggered_by": c.get("triggered_by", []),
                    "original_word": c["original"],
                    "replacement_word": c["replacement"],
                    "original_sentence": result["original_text"],
                    "reformulated_sentence": result["reformulated_text"],
                    "contextual_fit": v.get("contextual_fit"),
                    "sbert_sim": v.get("sbert_sim"),
                    "antonym_check": v.get("antonym_check"),
                })
            print(f"  [{done}/{total}] {profile_name:<22} {source:<24} {len(result['changes'])} change(s)", flush=True)

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(
        json.dumps({"changes": changes_out, "no_change": no_change_out}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nwrote {len(changes_out)} individual changes + {len(no_change_out)} no-change cases to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
