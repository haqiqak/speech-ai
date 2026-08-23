"""
eval/pilot_select_pairs_v5.py — Track C: next-round human-rating corpus,
stratified directly against R40's manual audit (VALIDATION.md SS33.6).

Purpose, distinct from v3/v4: v3/v4 curated pairs to demonstrate specific
historical defects/fixes. v5 asks a different, more load-bearing question:
**does a real human's judgment agree with Claude's own CLEAN/MINOR/SEVERE
classification of the same real-text corpus (R40)?** That classification
is the evidentiary backbone of R40-R43's architecture recommendations —
it has never been checked against independent human judgment at any scale
beyond the n=1, pre-R40 pilot rounds. This corpus makes that check
possible without regenerating anything: it reuses R40's FROZEN, already-
captured original/reformulated text and metrics verbatim (no live
reformulate() call here — this is a selection/formatting step only, not a
new generation run), paired with the sentence's own worst individual-
change verdict from eval/r40_change_audit_verdicts.json as a
`claude_audit_verdict` field.

Per Practice.md's proxy-metric discipline: `claude_audit_verdict` is
metadata for POST-HOC comparison only (see eval/pilot_analyze.py's
existing precedent for `profile_match`) — never shown to the participant
during rating (eval/pilot_app.py only ever reads pair_id/original_text/
reformulated_text) and never blended into their scores.

20 sentences, stratified: 4 CLEAN, 4 MINOR, 12 SEVERE (spanning nonsense/
duplicate-token, wrong-sense/factual, grammar corruption, fixed-term
erosion, the "slower->easier" logical inversion, nonsense compounds, wrong
POS, letter-as-word, the scientifically-backwards restructuring case,
appliance-type sense confusion, and non-standard plural/agreement),
across all 4 R40 profile densities.

Writes to eval/pilot_pairs.json (same file eval/pilot_app.py reads) —
per this project's own established practice, the file being overwritten
is archived first if it hasn't been already for this version.

Run:
    python eval/pilot_select_pairs_v5.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBE_PATH = ROOT / "eval" / "ceiling_probe_r40_results.json"
AUDIT_DATA_PATH = ROOT / "eval" / "r40_change_audit_data.json"
VERDICTS_PATH = ROOT / "eval" / "r40_change_audit_verdicts.json"
OUT_PATH = ROOT / "eval" / "pilot_pairs.json"
ARCHIVE_DIR = ROOT / "eval" / "archive_v4"

# (profile, unique original_text prefix, short defect-class label for the
# human-readable summary only -- NOT shown to the participant)
SELECTION: list[tuple[str, str, str]] = [
    # ── CLEAN (4) ──
    ("moderate_mixed", "Vitamin C is especially prone", "clean: prone->vulnerable"),
    ("moderate_mixed", "Cooking is done both by people", "clean: professional->expert"),
    ("heavy_dense", "Deep learning uses several layers", "clean: several->various"),
    ("moderate_mixed", "Small talk consists of three main parts", "clean: greeting->welcome"),
    # ── MINOR (4) ──
    ("light_single_sound", "Small talk is a bonding ritual and a strategy", "minor: strategy->way"),
    ("moderate_mixed", "A rational agent has goals or preferences", "minor: preferences->options"),
    ("moderate_mixed", "When proteins are heated", "minor: proteins->peptides"),
    ("heavy_dense", "In a business meeting, it enables people", "minor: reputation->esteem"),
    # ── SEVERE (12), one per named defect class from R40's taxonomy ──
    ("moderate_mixed", "The upper atmosphere is cooling, because greenhouse gas", "severe: nonsense duplicate (gas gases)"),
    ("moderate_mixed", "Since the pre-industrial period", "severe: wrong sense/factual (palaeolithic)"),
    ("moderate_mixed", "Machine learning is the study of programs", "severe: grammar corruption (softwares)"),
    ("heavy_dense", "Small talk is an informal type of discourse", "severe: fixed-term erosion (little talk)"),
    ("single_common_sound", "Many of these algorithms were insufficient for solving", "severe: logical inversion (slower->easier)"),
    ("heavy_dense", "An ontology is the set of objects", "severe: nonsense compound (lot of objects, telling)"),
    ("heavy_dense", "Gradient descent is a type of local search", "severe: wrong POS + nonsense (quest, optimists, place)"),
    ("heavy_dense", "Between the 18th century and 1970", "severe: factual/logical (half-century, letter-as-word)"),
    ("heavy_dense", "Long-chain sugars such as starch", "severe: restructuring, scientifically backwards (glucose)"),
    ("single_common_sound", "The upper atmosphere is cooling, because greenhouse gas", "severe: wrong sense, stealth-plausible (space->place)"),
    ("heavy_dense", "Cooking techniques and ingredients vary widely, from gr", "severe: appliance-type sense confusion (stoves->fires)"),
    ("heavy_dense", "Speech patterns between women", "severe: non-standard plural/agreement (Words patterns)"),
]


def _find_row(profile: str, prefix: str, probe: list[dict]) -> dict:
    matches = [
        r for r in probe
        if r["profile"] == profile and r["status"] == "reformulated"
        and r["original_text"].startswith(prefix)
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly 1 match for ({profile!r}, {prefix!r}), got {len(matches)}")
    return matches[0]


def _worst_verdict(profile: str, reformulated_text: str, sentence_verdicts: dict) -> str:
    key = (profile, reformulated_text)
    vs = sentence_verdicts.get(key)
    if not vs:
        return "unknown"
    rank = {"CLEAN": 0, "MINOR": 1, "SEVERE": 2}
    return max(vs, key=lambda x: rank[x])


def main() -> int:
    probe = json.loads(PROBE_PATH.read_text(encoding="utf-8"))["results"]
    audit_data = json.loads(AUDIT_DATA_PATH.read_text(encoding="utf-8"))["changes"]
    verdict_rows = json.loads(VERDICTS_PATH.read_text(encoding="utf-8"))["verdicts"]

    sentence_verdicts: dict[tuple, list[str]] = {}
    for c, v in zip(audit_data, verdict_rows):
        key = (c["profile"], c["reformulated_sentence"])
        sentence_verdicts.setdefault(key, []).append(v["verdict"])

    pairs = []
    for i, (profile, prefix, label) in enumerate(SELECTION, 1):
        row = _find_row(profile, prefix, probe)
        worst = _worst_verdict(profile, row["reformulated_text"], sentence_verdicts)
        pairs.append({
            "pair_id": f"pair_{i:02d}",
            "case_id": f"r40_{profile}_{i:02d}",
            "category": "r40_real_text",
            "profile": profile,
            "source_article": row["source"],
            "original_text": row["original_text"],
            "reformulated_text": row["reformulated_text"],
            "status": row["status"],
            "n_changes": row["n_changes"],
            "change_sources": row["change_sources"],
            "metrics": row["metrics"],
            "final_verification": row["final_verification"],
            "claude_audit_verdict": worst,
            "claude_audit_defect_label": label,
            "_note": "claude_audit_verdict/defect_label are for POST-HOC "
                     "comparison only (VALIDATION.md SS33.6) -- never shown "
                     "to the participant, never blended into their ratings.",
        })

    if OUT_PATH.exists() and not ARCHIVE_DIR.exists():
        ARCHIVE_DIR.mkdir(parents=True)
        shutil.copy(OUT_PATH, ARCHIVE_DIR / "pilot_pairs_v4.json")
        v4_responses = ROOT / "eval" / "pilot_responses" / "P1.csv"
        if v4_responses.exists():
            shutil.copy(v4_responses, ARCHIVE_DIR / "P1_v4_responses.csv")
        print(f"archived prior pilot_pairs.json/P1.csv to {ARCHIVE_DIR}")

    verdict_counts: dict[str, int] = {}
    for p in pairs:
        verdict_counts[p["claude_audit_verdict"]] = verdict_counts.get(p["claude_audit_verdict"], 0) + 1

    out = {
        "_doc": "eval/pilot_pairs.json - v5, Track C (per direct instruction "
                "after R43). 20 pairs selected from R40's real-text corpus "
                "(VALIDATION.md SS33), frozen output reused verbatim -- no new "
                "reformulate() run. Stratified across R40's CLEAN/MINOR/SEVERE "
                "manual-audit verdicts and all 4 profile densities, so a real "
                "human rating this corpus provides the first independent check "
                "of R40's severity classification, the evidentiary basis for "
                "R42/R43's architecture recommendations.",
        "verdict_counts": verdict_counts,
        "pairs": pairs,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    # Reset the response file the same way v4 did, so the app doesn't think
    # these pair_ids (pair_01..20, reused numbering) are already rated.
    p1 = ROOT / "eval" / "pilot_responses" / "P1.csv"
    if p1.exists():
        p1.write_text(
            "participant_id,pair_id,presentation_order_index,shown_first,"
            "meaning_preservation,naturalness,speaking_ease,preference,"
            "diagnostic_tag,comment,timestamp\n",
            encoding="utf-8",
        )
        print(f"reset {p1} to header-only (v4 responses archived above)")

    print(f"\nwrote {len(pairs)} pairs to {OUT_PATH}")
    print(f"verdict distribution: {verdict_counts}")
    for p in pairs:
        print(f"  {p['pair_id']} [{p['claude_audit_verdict']:<7}][{p['profile']:<20}] {p['claude_audit_defect_label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
