"""
eval/r43a3_nli_validation.py — R43-A3: bounded validation of an NLI
cross-encoder as a candidate logical-consistency signal, against R40's
own labeled ground truth (VALIDATION.md SS33.6's 79 sentence-level
CLEAN/MINOR/SEVERE verdicts). Diagnostic only -- semantic.py is not
modified, no production gate is added, no threshold is promoted.

Model: cross-encoder/nli-deberta-v3-xsmall (the smallest of the two
candidates REFORMULATION_RESEARCH.md SS9 named), chosen after
cross-encoder/nli-deberta-v3-small failed to download three times on a
network that repeatedly resets long-lived connections around 50-60MB in
(httpcore.RemoteProtocolError, confirmed directly in eval/nli_download
diagnostics, not a timeout).

Method: for each of the 79 R40 sentence-level (original, reformulated)
pairs, run the NLI model BOTH directions (premise=original/hypothesis=
reformulated, and the reverse -- entailment is directional) and record
the predicted label (contradiction/entailment/neutral) and raw logits.
Compare against each sentence's own worst individual-change verdict
(CLEAN/MINOR/SEVERE, from eval/r40_change_audit_verdicts.json) the same
way R41 compared contextual_fit.

Run:
    python eval/r43a3_nli_validation.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
from sentence_transformers import CrossEncoder

ROOT = Path(__file__).resolve().parent.parent
PROBE_PATH = ROOT / "eval" / "ceiling_probe_r40_results.json"
AUDIT_DATA_PATH = ROOT / "eval" / "r40_change_audit_data.json"
VERDICTS_PATH = ROOT / "eval" / "r40_change_audit_verdicts.json"
OUT_PATH = ROOT / "eval" / "r43a3_nli_validation_results.json"

MODEL_NAME = "cross-encoder/nli-deberta-v3-xsmall"


def worst_verdicts() -> dict[tuple[str, str], str]:
    audit_data = json.loads(AUDIT_DATA_PATH.read_text(encoding="utf-8"))["changes"]
    verdict_rows = json.loads(VERDICTS_PATH.read_text(encoding="utf-8"))["verdicts"]
    per_sentence: dict[tuple[str, str], list[str]] = defaultdict(list)
    for c, v in zip(audit_data, verdict_rows):
        key = (c["profile"], c["reformulated_sentence"])
        per_sentence[key].append(v["verdict"])
    rank = {"CLEAN": 0, "MINOR": 1, "SEVERE": 2}
    return {k: max(vs, key=lambda x: rank[x]) for k, vs in per_sentence.items()}


def main() -> int:
    probe = json.loads(PROBE_PATH.read_text(encoding="utf-8"))["results"]
    reformulated = [r for r in probe if r["status"] == "reformulated"]
    verdicts = worst_verdicts()

    print(f"loading {MODEL_NAME}...", flush=True)
    model = CrossEncoder(MODEL_NAME)
    id2label = model.model.config.id2label
    print(f"loaded. labels: {id2label}", flush=True)

    rows = []
    seen_keys = set()
    for r in reformulated:
        key = (r["profile"], r["reformulated_text"])
        if key in seen_keys:
            continue  # dedupe identical (profile, reformulated_text) pairs
        seen_keys.add(key)
        verdict = verdicts.get(key, "unknown")

        orig, new = r["original_text"], r["reformulated_text"]
        fwd_logits, rev_logits = model.predict([(orig, new), (new, orig)])
        fwd_label = id2label[int(fwd_logits.argmax())]
        rev_label = id2label[int(rev_logits.argmax())]
        rows.append({
            "profile": r["profile"],
            "source": r["source"],
            "verdict": verdict,
            "original_text": orig,
            "reformulated_text": new,
            "fwd_label": fwd_label,
            "fwd_logits": {id2label[i]: round(float(x), 4) for i, x in enumerate(fwd_logits)},
            "rev_label": rev_label,
            "rev_logits": {id2label[i]: round(float(x), 4) for i, x in enumerate(rev_logits)},
            "either_contradiction": fwd_label == "contradiction" or rev_label == "contradiction",
        })
        print(f"  [{verdict:<7}] fwd={fwd_label:<13} rev={rev_label:<13} {orig[:55]}", flush=True)

    OUT_PATH.write_text(json.dumps({"results": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {len(rows)} rows to {OUT_PATH}")

    # ── Aggregate: does "either direction = contradiction" separate SEVERE from CLEAN/MINOR? ──
    by_verdict: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_verdict[row["verdict"]].append(row)

    print("\n=== AGGREGATE: contradiction-flag rate by verdict ===")
    for v in ["CLEAN", "MINOR", "SEVERE"]:
        subset = by_verdict.get(v, [])
        if not subset:
            continue
        flagged = sum(1 for row in subset if row["either_contradiction"])
        print(f"{v}: {flagged}/{len(subset)} ({flagged/len(subset):.0%}) flagged as contradiction in >=1 direction")

    print("\n=== SEVERE cases flagged as contradiction (candidates NLI catches) ===")
    for row in by_verdict.get("SEVERE", []):
        if row["either_contradiction"]:
            print(f"  {row['original_text'][:50]} -> {row['reformulated_text'][:50]}")

    print("\n=== SEVERE cases NOT flagged (NLI's blind spots) ===")
    for row in by_verdict.get("SEVERE", []):
        if not row["either_contradiction"]:
            print(f"  {row['original_text'][:50]} -> {row['reformulated_text'][:50]}")

    print("\n=== CLEAN/MINOR cases wrongly flagged as contradiction (false positives) ===")
    for v in ["CLEAN", "MINOR"]:
        for row in by_verdict.get(v, []):
            if row["either_contradiction"]:
                print(f"  [{v}] {row['original_text'][:50]} -> {row['reformulated_text'][:50]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
