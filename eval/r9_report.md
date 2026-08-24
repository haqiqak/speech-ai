# Phase 9 — Learned validator prototype: training run report

**Status: prototype/research only. Not integrated into `reformulate.py`
or `app.py`.** Scripts: `eval/r9_assemble_final_dataset.py` (dataset),
`eval/r9_make_split.py` (unified split), `eval/r9_baselines.py` +
`_baseline_eval.py` (existing-signal baselines), `eval/r9_train_validator.py`
(fine-tuning), `eval/r9_eval_validator.py` (evaluation). Outputs in
`eval/r50_dataset/r9_*.json`; the fine-tuned checkpoint is at
`eval/r9_validator_model/final/` (git-ignored, not committed — see
why below).

## Headline result, stated plainly

**The training run diverged. The resulting model is non-functional.**
100% of its 70,830,337 parameters are NaN, confirmed by direct
inspection of the saved `model.safetensors`. Every prediction it
produces is `nan`. This is a genuine negative result of *this specific*
prototype configuration, reported in full rather than concealed or
re-run — per the explicit instruction to finish, evaluate, and report
the current run exactly as it happened, not to alter or retry it.

## 1. Dataset and split (completed successfully)

Assembled from R50 (convention-corrected) + Phase 8 (convention-corrected)
+ Phase 8B: 313 records, 252 unique dedup groups. Acceptability is the
primary target (`CLEAN` vs `DEFECTIVE`); `NATURALNESS_OR_REGISTER` is
demoted to secondary-only per Phase 8B's taxonomy decision. A unified
split was built respecting R50's and Phase 8's frozen test assignments
(their first real use, as reserved) and freshly, stratified-splitting
Phase 8B's new groups: **205 train / 57 val / 51 test records** (158/47/47
groups). Train set: 188 DEFECTIVE / 17 CLEAN — a ~11:1 imbalance.

## 2. Baselines (completed successfully — these are the only trustworthy numbers from this phase)

Computed fresh on the 51-record test set (existing signals had never been
run on most Phase 8/8B records):

| Rule | Accuracy | DEFECTIVE recall | DEFECTIVE precision | CLEAN recall |
|---|---|---|---|---|
| Reject everything (trivial) | 84% | 100% | 84% | **0%** |
| Accept everything (trivial) | 16% | 0% | — | 100% |
| NLI contradiction only | 41% | 30% | 100% | 100% |
| Grammar issues > 0 only | 18% | 2% | 100% | 100% |
| NLI OR grammar (production-style gate) | 43% | 33% | 100% | 100% |
| SBERT < 0.99 | 80% | 91% | 87% | — |
| **SBERT<0.95 OR NLI OR grammar (best combo)** | **61%** | **60%** | **90%** | **63%** |

**[FINDING]** Raw accuracy is a misleading metric here because of the
84%-DEFECTIVE class skew — "reject everything" wins on accuracy/F1 while
being the exact useless validator the proposal warned about (0% CLEAN
recall: it would block every single good reformulation). The best simple
combined rule (SBERT<0.95 OR NLI-contradiction OR grammar-issue) is the
real floor a learned validator needs to beat: 60% DEFECTIVE recall, 90%
DEFECTIVE precision, 63% CLEAN recall, simultaneously.

## 3. Fine-tuning run — diverged

**Setup:** `microsoft/deberta-v3-xsmall` (~70M params) cross-encoder,
`BinaryCrossEntropyLoss` with `pos_weight≈11.06` (to compensate for the
17:188 CLEAN:DEFECTIVE train imbalance), lr=2e-5, 8 epochs, batch size 8,
no explicit gradient-clipping override (left at the trainer default).

**What happened, from the actual training log:**

| Epoch | loss | grad_norm |
|---|---|---|
| 0.38 | 1.208 | 3.30 |
| 0.77 | 1.472 | 3.36 |
| 1.15 | 0.788 | 1.67 |
| 1.54 | 2.188 | 17.89 |
| 1.92 | 2.207 | 3.14 |
| 2.31 | 1.183 | 7.04 |
| 2.69 | 3.297 | **24.47** |
| **3.08** | **0.070** | **nan** |
| 3.46 – 7.69 (every logged step) | 0 | nan |

Training was progressing (if noisily) through epoch ~2.7, with a warning
sign — grad_norm spiked to 24.5 at epoch 2.69. By epoch 3.08 the gradient
norm was `nan`, and it stayed `nan` for the remaining ~5 epochs; loss
displaying as flat `0` after that point is a symptom of the collapse
(NaN-valued forward passes), not evidence of a converged model. Final
`eval_loss` at epoch 8: `nan`.

**[FINDING] Root-cause hypothesis (not verified by a repeat run, per
instruction not to re-run):** the combination of a fairly aggressive
learning rate (2e-5 peak) and a large `pos_weight` (~11×) on a very small
training set (205 examples, only 17 positive/CLEAN) is a known recipe for
gradient explosion in `BCEWithLogitsLoss`-style training — a single
high-confidence wrong prediction on a heavily-upweighted CLEAN example
produces a disproportionately large loss and gradient, and without an
explicit, aggressive gradient-clipping value, that can overflow to `inf`/
`nan` in a handful of steps. This is consistent with the observed timing
(instability visible by epoch 2.7, full collapse by epoch 3.1).

## 4. Evaluation (run exactly as planned — output is not meaningful)

`eval/r9_eval_validator.py` executed the complete planned pipeline —
threshold sweep, unseen-word-pair generalization check, and
`FACTUAL_OR_LOGICAL_REVERSAL` stratification by `evidence_quality` — all
without error. Every one of the 51 test predictions came back `P(CLEAN) =
nan`. Because Python evaluates `nan >= threshold` as `False` for every
threshold, the script's fallback branch classified all 51 records as
`DEFECTIVE`, which **happens to numerically match the "reject everything"
trivial baseline** (84% accuracy, 100% DEFECTIVE recall, 0% CLEAN
recall) at every threshold tested. **This is a coincidence of comparison
semantics, not a result.** The model did not learn anything, retained
nothing about unseen word-pairs, and has no real position on any
`FACTUAL_OR_LOGICAL_REVERSAL` case — reporting these numbers as "ties the
baseline" would misstate what happened, so they are logged here as
non-results.

## 5. The three gate questions — cannot be answered by this run

1. **Does it generalize?** Unanswerable — the model has no learned
   behavior to generalize.
2. **Does it beat the existing stack?** No — it produces no usable
   signal at all, so it cannot beat anything.
3. **What's the precision/coverage tradeoff?** Unanswerable for the same
   reason.

**None of Phase 9's three gate questions were resolved by this run.**
This is a failed training configuration, not evidence about whether a
learned validator can work — the baselines in §2 (SBERT<0.95 OR NLI OR
grammar's 60%/90%/63% split, notably beatable) remain the target a
correctly-trained prototype would need to clear.

## 6. What would need to change (recommended, NOT executed — no re-run performed per instruction)

- A substantially lower learning rate (e.g. 2e-6 to 5e-6) and/or explicit
  gradient clipping (`max_grad_norm=1.0` or lower, set explicitly rather
  than relying on the default).
- A less extreme class-imbalance correction — e.g. cap `pos_weight` at
  ~3-5× and/or combine with oversampling of the CLEAN class, rather than
  relying on an 11× loss multiplier alone.
- Early stopping on `eval_loss` (which was already trending the wrong
  direction — 1.75 → 1.85 — between epochs 1 and 2, before the collapse)
  rather than a fixed 8-epoch schedule.
- Given the very small dataset (205 train records), a smaller/simpler
  classifier head or few-shot/prompting-based approach may be worth
  comparing against fine-tuning at all, before investing in further
  fine-tuning attempts.

## 7. Outputs verified saved

- `eval/r50_dataset/r9_final_dataset.json` — 313-record assembled dataset. ✓
- `eval/r50_dataset/r9_split.json` — unified split. ✓
- `eval/r50_dataset/r9_baseline_signals.json`, `r9_baseline_eval_summary.json` — baseline results (the phase's only valid numbers). ✓
- `eval/r9_train.log` — full training log, including the divergence trace. ✓
- `eval/r50_dataset/r9_eval_results.json` — evaluation output (all-NaN, documented as non-meaningful above). ✓
- `eval/r9_validator_model/final/` — the diverged checkpoint. **Not committed to git** (already `.gitignore`d as a large, reproducible artifact) — and here specifically not worth committing since it is confirmed non-functional; the training log fully documents what happened without needing the broken weights preserved.

## Bottom line

Phase 9's infrastructure (dataset assembly, unified leakage-safe split,
baseline computation) worked correctly and produced the real floor a
validator must beat: **60% DEFECTIVE recall / 90% precision / 63% CLEAN
recall from simple existing signals combined.** The fine-tuning attempt
itself failed due to a training-stability issue in the chosen
hyperparameters, not a finding about the underlying approach. Per
instruction, this run was not altered or repeated — a corrected attempt
(§6) is a natural next step, but is a decision left to the user, not
undertaken automatically.
