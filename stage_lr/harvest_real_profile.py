"""
stage_lr/harvest_real_profile.py — Stage LR data path (b), reusable
across real participants. Unlike the first version of this script
(which hardcoded one friend's actual profile/sentences as Python
literals — a privacy mistake, corrected 2026-08-30), this one takes
its input from a per-participant JSON file under
`stage_lr/data/private/` (gitignored — see `.gitignore`'s "Stage LR:
real-participant data" block) and writes its output there too. The
mechanism is committed and reusable; a real person's actual words
never are.

Input file shape (`stage_lr/data/private/<name>_input.json`):
    {"profile_spec": {"sounds": [...], "words": [...], "phrases": [...]},
     "sentences": [...]}

Builds a real DifficultyProfile from `profile_spec`, runs each sentence
through the real, unmodified `reformulate()` for the first time, then
the same generate-second-candidate method as data path (a)'s batches.
Deliberately does NOT judge anything — no Claude call here. Per
`stage_lr/ingest_real_human_pair.py`'s hard rule, a Claude verdict is
only ever obtained in the same session as the human verdict.

    DISABLE_DATAMUSE=1 python stage_lr/harvest_real_profile.py <name>
    (reads stage_lr/data/private/<name>_input.json, writes
    stage_lr/data/private/<name>_generation_log.json and
    stage_lr/data/private/<name>_pairs_for_review.json)
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

PRIVATE_DIR = ROOT / "stage_lr" / "data" / "private"


def build_profile(name: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__real_{name}__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for ph in spec.get("phrases", []):
        p.add_phrase(ph, source="user_typed")
    return p


def main(name: str) -> None:
    in_path = PRIVATE_DIR / f"{name}_input.json"
    out_log = PRIVATE_DIR / f"{name}_generation_log.json"
    out_for_review = PRIVATE_DIR / f"{name}_pairs_for_review.json"

    data = json.loads(in_path.read_text(encoding="utf-8"))
    spec = data["profile_spec"]
    sentences = data["sentences"]
    profile = build_profile(name, spec)

    results = []
    counts = {"total": len(sentences), "no_substitution_change": 0,
              "attempt_error": 0, "no_second_candidate": 0, "second_candidate_found": 0}

    for i, text in enumerate(sentences, 1):
        corrected, _ = sanitize_input(text)
        result = reformulate.reformulate(corrected, profile)
        sub_changes = [c for c in result.get("changes", []) if c.get("source") == "substitution"]

        uid = f"{name}-{i}"
        if not sub_changes:
            counts["no_substitution_change"] += 1
            results.append({"uid": uid, "outcome": "no_substitution_change",
                             "reason": f"status={result.get('status')}, sentence={text!r}"})
            print(f"[{i}/{len(sentences)}] no_substitution_change: {text!r}", flush=True)
            continue

        change = sub_changes[0]
        pseudo_record = {
            "uid": uid, "original_text": corrected,
            "reformulated_text": result["reformulated_text"],
            "changed_word_pair": [change["original"], change["replacement"]],
        }
        profile_entry = {"profile": profile, "profile_spec": {"name": name, **spec},
                          "source": f"harvest_real_profile.py (real participant '{name}', first-run)"}
        try:
            res = attempt_second_candidate(pseudo_record, profile_entry)
        except Exception as e:
            counts["attempt_error"] += 1
            results.append({"uid": uid, "outcome": "attempt_error", "reason": f"{type(e).__name__}: {e}"})
            print(f"[{i}/{len(sentences)}] attempt_error: {e}", flush=True)
            continue

        counts[res["outcome"]] = counts.get(res["outcome"], 0) + 1
        results.append(res)
        print(f"[{i}/{len(sentences)}] {res['outcome']}: {text!r}", flush=True)

    out_log.parent.mkdir(parents=True, exist_ok=True)
    out_log.write_text(json.dumps({"counts": counts, "profile_spec": spec, "results": results}, indent=2),
                        encoding="utf-8")

    # Contamination check + dedup, same method as every prior batch. Also
    # flags (does not silently drop) any candidate whose sentence differs
    # from what sanitize_input() itself would produce pre-substitution —
    # catches the class of bug found in the first real participant's data
    # (sanitize_input() corrupting a sentence before reformulate() ever runs).
    found = {r["uid"]: r for r in results if r["outcome"] == "second_candidate_found"}

    def tok(s):
        return re.findall(r"[A-Za-z']+", s.lower())

    clean, contaminated = [], []
    for uid, r in found.items():
        a, b = tok(r["candidate_a_sentence"]), tok(r["candidate_b_sentence"])
        if len(a) != len(b) or sum(1 for i in range(len(a)) if a[i] != b[i]) > 1:
            contaminated.append(uid)
        else:
            clean.append(uid)

    seen = {}
    for uid in clean:
        r = found[uid]
        key = (r["original_sentence"], r["original_word"], r["candidate_a"], r["candidate_b"])
        seen.setdefault(key, []).append(uid)

    for_review = []
    for idx, (key, uids) in enumerate(seen.items(), 1):
        r = found[uids[0]]
        for_review.append({
            "review_id": idx, "source_uids": uids,
            "sentence_with_A": r["candidate_a_sentence"],
            "sentence_with_B": r["candidate_b_sentence"],
            "changed_word": r["original_word"],
            "candidate_A": r["candidate_a"], "candidate_B": r["candidate_b"],
        })

    out_for_review.write_text(json.dumps(for_review, indent=2), encoding="utf-8")

    print()
    print("=== FINAL COUNTS ===")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print(f"  found_raw: {len(found)}  contaminated: {len(contaminated)}  "
          f"clean: {len(clean)}  unique: {len(seen)}")
    print(f"  -> {out_for_review}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python stage_lr/harvest_real_profile.py <name>")
        print("  (reads stage_lr/data/private/<name>_input.json)")
        sys.exit(1)
    main(sys.argv[1])
