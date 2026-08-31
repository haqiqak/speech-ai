"""
stage_lr/harvest_batch3.py — Stage LR data path (a), batch 3. Unlike
batches 1-2 (which reused existing rated records from
eval/r50_dataset/labeled_dataset.json and eval/r10_raw_results.json),
no further unused corpus of the right shape was found (checked: R11's
reverify data covers the exact same 398 R10 runs batch 2 already used,
just at a later harvest point — not genuinely new sentences; R43a/R44/
R49 results don't carry substitution-tier "changes" lists with
original/replacement pairs). Per the pre-approved fallback, this batch
runs 30 fresh, previously-unused sentences through the real,
unmodified `reformulate()` pipeline for the first time (against the
same 4 profile templates `ceiling_probe_r40.py` already defines) to
get real candidate_A values, then applies the exact same
generate-second-candidate method as batches 1-2.

    DISABLE_DATAMUSE=1 python stage_lr/harvest_batch3.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DISABLE_DATAMUSE", "1")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

import paths  # noqa: F401,E402
import reformulate  # noqa: E402
from grammar import sanitize_input  # noqa: E402
from ceiling_probe_r40 import PROFILES  # noqa: E402
from stage_lr.generate_pairs import _build_r40_style_profile, attempt_second_candidate  # noqa: E402

OUT_PATH = ROOT / "stage_lr" / "data" / "lr1_candidate_generation_log_batch3.json"

# 30 fresh sentences, not reused from any prior batch (R40's Wikipedia
# climate/AI/smalltalk/cooking corpus, R47's presentation/deadline/
# professor/weather set, R10's biology/physics/computing/workplace
# set) — new domains: gardening, travel, cars, sports, home repair,
# finance, pets, art, health, shopping — chosen to contain a good mix
# of the 4 profile templates' target sounds (str/pr/gr/s/th/r).
SENTENCES = [
    "Remember to water the tomato plants twice a week during summer.",
    "The mechanic said the brakes needed replacing before the road trip.",
    "She practices piano for thirty minutes every morning before school.",
    "The airline rescheduled our flight because of a severe storm warning.",
    "Grandpa always tells the same story about his first fishing trip.",
    "The recipe requires precise measurements for the sauce to thicken properly.",
    "Our neighbor's dog keeps digging through the fence into the garden.",
    "The gym instructor recommended stretching before starting any strength training.",
    "He forgot his umbrella again despite the forecast predicting heavy rain.",
    "The museum's new exhibit features artifacts from ancient trading routes.",
    "Prices for groceries have risen sharply over the past few months.",
    "The plumber fixed the leaking pipe under the kitchen sink yesterday.",
    "Her thesis argues that early exposure to music improves language development.",
    "The coach benched the striker after he missed three straight practices.",
    "They spent the afternoon assembling furniture from the new store.",
    "The professor's lecture on probability confused half the classroom.",
    "A sudden gust of wind knocked over the outdoor market stalls.",
    "The library extended its hours during final exam week.",
    "Traffic was terrible because of construction on the main bridge.",
    "The nurse explained the treatment plan clearly to the worried patient.",
    "He struggled to parallel park in the crowded downtown street.",
    "The startup raised significant funding to expand its engineering team.",
    "She switched careers after realizing accounting wasn't fulfilling.",
    "The children built a sandcastle before the tide came rushing in.",
    "Our thermostat broke during the coldest week of the winter.",
    "The editor suggested trimming the article's introduction significantly.",
    "A stray cat has been sleeping on our porch for three nights straight.",
    "The contractor promised the renovation would finish before spring.",
    "Researchers discovered a strange pattern in the migratory bird data.",
    "The waiter recommended the grilled salmon over the pasta special.",
]


def main() -> None:
    results = []
    counts = {"total_sentence_profile_pairs": 0, "no_substitution_change": 0,
              "attempt_error": 0, "no_second_candidate": 0, "second_candidate_found": 0}

    i = 0
    total = len(SENTENCES) * len(PROFILES)
    for text in SENTENCES:
        corrected, _ = sanitize_input(text)
        for profile_name, spec in PROFILES.items():
            i += 1
            counts["total_sentence_profile_pairs"] += 1
            profile = _build_r40_style_profile(profile_name)
            result = reformulate.reformulate(corrected, profile)

            sub_changes = [c for c in result.get("changes", []) if c.get("source") == "substitution"]
            if not sub_changes:
                results.append({"uid": f"B3-{profile_name}-{i}", "outcome": "no_substitution_change",
                                 "reason": f"status={result.get('status')}, no substitution-tier change produced"})
                counts["no_substitution_change"] += 1
                print(f"[{i}/{total}] {profile_name:<20} no_substitution_change", flush=True)
                continue

            # One target per (sentence, profile): the first substitution
            # change, same convention as batch 1/2's per-record scope.
            change = sub_changes[0]
            uid = f"B3-{profile_name}-{i}"
            pseudo_record = {
                "uid": uid,
                "original_text": corrected,
                "reformulated_text": result["reformulated_text"],
                "changed_word_pair": [change["original"], change["replacement"]],
            }
            profile_entry = {
                "profile": profile,
                "profile_spec": {"name": profile_name, **spec},
                "source": "harvest_batch3.py (fresh, first-run)",
            }
            try:
                res = attempt_second_candidate(pseudo_record, profile_entry)
            except Exception as e:
                counts["attempt_error"] += 1
                results.append({"uid": uid, "outcome": "attempt_error", "reason": f"{type(e).__name__}: {e}"})
                print(f"[{i}/{total}] {profile_name:<20} attempt_error: {e}", flush=True)
                continue

            counts[res["outcome"]] = counts.get(res["outcome"], 0) + 1
            results.append(res)
            print(f"[{i}/{total}] {profile_name:<20} {res['outcome']}", flush=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({"counts": counts, "results": results}, indent=2), encoding="utf-8")

    print()
    print("=== FINAL COUNTS (batch 3) ===")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
