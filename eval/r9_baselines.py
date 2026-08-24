"""
eval/r9_baselines.py -- Phase 9, step 2: establish baselines on the
FINAL, unified test set before training anything. Runs the existing
production signals (SBERT similarity, NLI contradiction check, grammar
issue count, contextual_fit where a word-pair exists) fresh on every
test-set record -- most Phase 8/8B records never had these computed.

RESEARCH ONLY. Calls existing semantic.py functions read-only; no
production code changed, no thresholds altered anywhere else.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: F401
import semantic as sem

EVAL = Path(__file__).parent

data = json.load(open(EVAL / "r50_dataset" / "r9_final_dataset.json", encoding="utf-8"))
by_uid = {r["uid"]: r for r in data["records"]}
split = json.load(open(EVAL / "r50_dataset" / "r9_split.json", encoding="utf-8"))
test_records = [by_uid[u] for u in split["test_uids"]]

print(f"Computing baselines on {len(test_records)} test records...")
sem.load_sbert()
sem.load_nli_model()
sem.load_grammar_tool()

results = []
for i, r in enumerate(test_records, 1):
    orig, refm = r["original_text"], r["reformulated_text"]
    sbert = sem.semantic_similarity(orig, refm)
    nli = sem.logical_consistency_check(orig, refm)
    grammar_n = sem.grammar_issue_count(refm)
    cf = None
    # contextual_fit needs the specific replacement word; skip for
    # restructuring/constructed records that have no single word pair
    # tracked in this dataset (word pair isn't preserved in r9_final_dataset;
    # left as a documented limitation of this baseline pass).
    results.append({
        "uid": r["uid"], "acceptability": r["acceptability"],
        "sbert": sbert,
        "nli_contradiction": nli["contradiction"] if nli else None,
        "grammar_issues": grammar_n,
    })
    print(f"  [{i}/{len(test_records)}] {r['uid']} sbert={sbert} nli_contra={results[-1]['nli_contradiction']} grammar={grammar_n}")

with open(EVAL / "r50_dataset" / "r9_baseline_signals.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
print(f"\nwrote {len(results)} baseline signal records to eval/r50_dataset/r9_baseline_signals.json")
