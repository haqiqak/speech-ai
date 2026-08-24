"""
eval/r47_fresh_sample.py — a fresh, small, hand-picked demonstration set
(not reused from R40's Wikipedia corpus — everyday/conversational
register this time, on purpose, for diversity) run through BOTH
reformulate() (production, unchanged) and reformulate_v2() (R46, opt-in)
side by side, so the two pipelines' actual behavior can be compared
directly on the same inputs. Diagnostic only, no production change.

Run:
    python eval/r47_fresh_sample.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic as sem
from grammar import sanitize_input
from difficulty_profile import DifficultyProfile
import reformulate

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "eval" / "r47_fresh_sample_results.json"

# (id, text, sound_patterns) -- fresh, everyday sentences, not from R40's corpus.
ITEMS: list[tuple[str, str, list[str]]] = [
    ("grab_presentation", "I need to grab my presentation materials before the meeting starts.", ["pr"]),
    ("quickly_finished", "She quickly finished writing the report and sent it to her supervisor.", ["r", "w"]),
    ("review_documents", "Can you please review these three documents before Friday?", ["r", "th", "f"]),
    ("restaurant_quiet", "The restaurant was surprisingly quiet for a Saturday evening.", ["r", "s"]),
    ("reschedule_strategy", "We should probably reschedule the strategy session for next week.", ["r", "s", "str"]),
    ("children_playing", "The children were playing happily in the garden all afternoon.", ["pl", "h"]),
    ("presentation_renewable", "His presentation about renewable energy sources was really impressive.", ["pr", "r"]),
    ("struggled_quantum", "I struggled to understand the professor's explanation of quantum mechanics.", ["str", "kw"]),
    ("weather_forecast", "The weather forecast predicts heavy rain throughout the weekend.", ["w", "pr", "r"]),
    ("research_discovered", "Our research team discovered a surprising pattern in the data.", ["r", "s", "d"]),
]


def _build_profile(name: str, sounds: list[str]) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__r47_{name}__")
    for s in sounds:
        p.add_sound(s, source="user_typed")
    return p


def run_one(item_id: str, text: str, sounds: list[str]) -> dict:
    profile = _build_profile(item_id, sounds)
    corrected, _ = sanitize_input(text)

    v1 = reformulate.reformulate(corrected, profile)
    v2 = reformulate.reformulate_v2(corrected, profile)

    def summarize(r):
        return {
            "status": r["status"],
            "reformulated_text": r["reformulated_text"],
            "sources": sorted({c["source"] for c in r["changes"]}),
            "n_changes": len(r["changes"]),
            "sbert": r["metrics"].get("meaning_preservation"),
            "validation": r.get("validation"),
        }

    return {
        "id": item_id, "sounds": sounds, "original_text": text,
        "v1": summarize(v1), "v2": summarize(v2),
    }


def main() -> int:
    sem.load_sbert()
    results = []
    for i, (item_id, text, sounds) in enumerate(ITEMS, 1):
        r = run_one(item_id, text, sounds)
        results.append(r)
        print(f"[{i}/{len(ITEMS)}] {item_id}", flush=True)
        print(f"  ORIG: {text}  (sounds={sounds})")
        print(f"  V1  : [{r['v1']['status']}] {r['v1']['reformulated_text']}")
        print(f"  V2  : [{r['v2']['status']}] {r['v2']['reformulated_text']}")
        if r["v2"]["validation"] and r["v2"]["validation"].get("flagged"):
            print(f"        (v2 validator flagged: {r['v2']['validation']})")
        print()

    OUT_PATH.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(results)} rows to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
