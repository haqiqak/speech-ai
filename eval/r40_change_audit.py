"""
eval/r40_change_audit.py — R40 (expanded): change-level data capture for
the manual linguistic audit.

The original eval/ceiling_probe_r40.py captured only sentence-level
aggregates (status, n_changes, overall metrics). This script re-runs the
same 48 sentences x 4 profiles through today's live engine and captures
every individual substitution CHANGE — original word, replacement,
sentence context before/after, contextual_fit, sbert_sim, source,
profile — so each change can be read and rated individually rather than
only spot-checked. 112 changes across 79 sentence-level reformulations
(2026-08-21 run). This is the dataset R41 validates contextual_fit
against.

Re-running (rather than reusing the original JSON) is a disclosed,
accepted limitation: substitution ranking is deterministic given a fixed
profile/text/candidate pool, but Datamuse network responses and (for the
2 restructuring cases) T5 sampling are not guaranteed byte-identical
across runs. Any drift is itself worth noting, not hidden.

Run:
    python eval/r40_change_audit.py
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

# Import the exact same corpus/profiles as the original probe.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ceiling_probe_r40 import SENTENCES, PROFILES, _build_profile  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "eval" / "r40_change_audit_data.json"


def main() -> int:
    semantic.load_sbert()
    changes_out = []
    total = len(SENTENCES) * len(PROFILES)
    done = 0
    for profile_name, spec in PROFILES.items():
        for source, text in SENTENCES:
            done += 1
            profile = _build_profile(profile_name, spec)
            corrected_text, _ = sanitize_input(text)
            result = reformulate.reformulate(corrected_text, profile)
            if result["status"] != "reformulated":
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
            print(f"  [{done}/{total}] {profile_name:<22} {source:<10} "
                  f"{len(result['changes'])} change(s)", flush=True)

    OUT_PATH.write_text(json.dumps({"changes": changes_out}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {len(changes_out)} individual changes to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
