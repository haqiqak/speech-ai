"""eval/r50p8_agreement.py -- R50 Phase 8, step 7: inter-rater agreement
between the primary rater (blind, r50p8_labels.py) and an independent
second rater (a separate subagent, blind to the primary rater's labels,
given only original/reformulated text and the taxonomy definitions).
Research/reporting only."""
import json
from collections import Counter, defaultdict
from pathlib import Path

EVAL = Path(__file__).parent
truth = json.load(open(EVAL / "r50_dataset" / "phase8_secondrater_truth.json", encoding="utf-8"))
second = json.load(open(EVAL / "r50_dataset" / "phase8_secondrater_results.json", encoding="utf-8"))

n = len(truth)
acc_agree = 0
sev_agree = 0
sev_agree_collapsed = 0  # CLEAN/MINOR vs SEVERE (coarser, arguably the decision that matters most)
primary_agree = 0
primary_agree_or_secondary = 0  # counts as agreement if second rater's primary is in primary rater's primary+secondary or vice versa
rows = []

for uid, t in truth.items():
    s = second[uid]
    t_acc = t["human_acceptability"]
    s_acc = s["human_acceptability"]
    t_sev = t["human_severity"]
    s_sev = s["human_severity"]
    t_prim = t["human_defect_labels"]["primary"]
    s_prim = s["primary_defect"]
    t_all = {t_prim} | set(t["human_defect_labels"]["secondary"])
    s_all = {s_prim} | set(s.get("secondary_defects") or [])

    a = (t_acc == s_acc)
    sv = (t_sev == s_sev)
    sv_c = (t_sev == "SEVERE") == (s_sev == "SEVERE")
    p = (t_prim == s_prim)
    p_loose = bool(t_all & s_all)

    acc_agree += a
    sev_agree += sv
    sev_agree_collapsed += sv_c
    primary_agree += p
    primary_agree_or_secondary += p_loose

    rows.append((uid, t_acc, s_acc, t_sev, s_sev, t_prim, s_prim, a, sv, p, p_loose))

print(f"n = {n}")
print(f"Acceptability (CLEAN/DEFECTIVE/UNCERTAIN) exact agreement: {acc_agree}/{n} = {acc_agree/n:.0%}")
print(f"Severity (CLEAN/MINOR/SEVERE) exact agreement: {sev_agree}/{n} = {sev_agree/n:.0%}")
print(f"Severity collapsed (SEVERE vs not-SEVERE) agreement: {sev_agree_collapsed}/{n} = {sev_agree_collapsed/n:.0%}")
print(f"Primary defect type exact agreement: {primary_agree}/{n} = {primary_agree/n:.0%}")
print(f"Primary defect type agreement allowing either's secondary label: {primary_agree_or_secondary}/{n} = {primary_agree_or_secondary/n:.0%}")

print("\nDisagreements (uid, primary-rater-acc/sev/primary vs second-rater-acc/sev/primary):")
for row in rows:
    uid, t_acc, s_acc, t_sev, s_sev, t_prim, s_prim, a, sv, p, p_loose = row
    if not (a and sv and p):
        print(f"  {uid}: primary=({t_acc},{t_sev},{t_prim})  second=({s_acc},{s_sev},{s_prim})  acc_agree={a} sev_agree={sv} prim_agree={p} prim_loose={p_loose}")

# by-class primary agreement (using primary rater's label as the class)
by_class = defaultdict(lambda: [0, 0])
for uid, t in truth.items():
    s = second[uid]
    cls = t["human_defect_labels"]["primary"]
    by_class[cls][1] += 1
    if cls == s["primary_defect"]:
        by_class[cls][0] += 1
print("\nPrimary-label agreement by class (primary rater's label as reference):")
for cls, (agree, total) in sorted(by_class.items(), key=lambda x: -x[1][1]):
    print(f"  {cls}: {agree}/{total} = {agree/total:.0%}")

with open(EVAL / "r50_dataset" / "phase8_agreement_summary.json", "w", encoding="utf-8") as f:
    json.dump({
        "n": n,
        "acceptability_agreement": acc_agree / n,
        "severity_exact_agreement": sev_agree / n,
        "severity_collapsed_agreement": sev_agree_collapsed / n,
        "primary_defect_exact_agreement": primary_agree / n,
        "primary_defect_loose_agreement": primary_agree_or_secondary / n,
        "by_class_primary_agreement": {k: v[0] / v[1] for k, v in by_class.items()},
    }, f, indent=2)
print("\nwrote eval/r50_dataset/phase8_agreement_summary.json")
