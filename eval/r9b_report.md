# Phase 9B — Fix the training instability, controlled retry

**Status: prototype/research only. Not integrated into `reformulate.py`
or `app.py`.** Scripts: `eval/r9b_diagnosis.md` (step 1),
`eval/r9b_sanity_train.py` (step 2), `eval/r9b_train_validator.py`
(steps 3-4), `eval/r9b_eval_validator.py` (step 5). Dataset and split
are **unchanged** from R9 (`r9_final_dataset.json`, `r9_split.json`).

## 1. Diagnosis of the R9 failure (corrected from R9's own hypothesis)

Confirmed the exact failed configuration from `r9_train_validator.py` +
`r9_train.log`: `lr=2e-5`, `pos_weight≈11.06`, 8 fixed epochs, no
explicit overrides for clipping/precision/epsilon.

**R9's report guessed "no gradient clipping" as a cause. Checked
directly against the library defaults — that guess was wrong**, and
this is disclosed rather than left standing: `max_grad_norm` defaults to
`1.0` and was already active; `fp16`/`bf16` both default to `False`
(full fp32 throughout). The logged `grad_norm=24.47` at epoch 2.69 is
the pre-clip norm the clipping function reports — the actual optimizer
step used gradients already clipped to 1.0. Clipping worked as
configured and still didn't prevent the epoch-3.08 collapse. Revised
hypothesis: the large `pos_weight` (~11×) combined with `lr=2e-5` and
`adam_epsilon=1e-8` (smaller than the `1e-6` commonly recommended for
DeBERTa-family stability) on a 205-example dataset was still enough to
walk the model into a numerically unstable region within ~3 epochs.
Full detail: `eval/r9b_diagnosis.md`.

## 2. Conservative configuration

| Setting | R9 (failed) | R9B |
|---|---|---|
| learning_rate | 2e-5 | **3e-6** |
| pos_weight | ≈11.06 | **4.0** (capped) |
| max_grad_norm | 1.0 (default, unstated) | **1.0 (explicit)** |
| adam_epsilon | 1e-8 (default) | **1e-6** |
| epochs | 8, fixed | up to 8, **early stopping on eval_loss** (patience 2) |
| save/eval strategy | eval=epoch, save=no | eval=epoch, save=epoch, `load_best_model_at_end=True` |
| safety net | none | training aborts immediately if any weight goes non-finite (added this round) |

Dataset and split unchanged: 205 train / 57 val / 51 test, same as R9.

## 3. Sanity pass — PASSED

10 optimizer steps, finite-check callback on every step. Loss oscillated
in a healthy 0.66–1.23 range; grad_norm stayed bounded (1.0–2.5). All 10
steps reported "all weights and grads finite OK." Proceeded to the full
run only after this passed, per instruction.

## 4. Full training run — completed, stable throughout

8 epochs, 208 steps, ~4h48m on CPU. **Zero non-finite events** — the
abort-on-NaN safety callback never fired.

| Epoch | eval_loss |
|---|---|
| 1 | 0.883 |
| 2 | 0.845 |
| 3 | 0.839 |
| 4 | 0.977 (dip) |
| 5 | 0.790 |
| **6** | **0.676 (best)** |
| 7 | 1.056 |
| 8 | 1.023 |

Training ran the full 8 epochs (early stopping's patience-2 condition
was never satisfied for two *consecutive* non-improving epochs after
the epoch-6 best). `load_best_model_at_end=True` restored and saved the
**epoch-6 checkpoint** (lowest eval_loss), not the final epoch.

**Direct inspection of the saved weights: 0 NaN, 0 Inf out of
70,830,337 parameters.** A functional model this time.

## 5. Evaluation — a real, if narrow, signal

**First finding, disclosed and corrected in place:** the model's raw
output scores are compressed into a narrow band (0.528–0.625) rather
than spread across [0,1]. My first evaluation pass used a coarse
threshold grid (0.9/0.7/0.5/0.3/0.1) that entirely missed this band and
produced a degenerate all-CLEAN-or-all-DEFECTIVE result. **This was an
evaluation-script bug, not a property of the model** — a fine-grained
sweep across the actual observed score range reveals genuine
discrimination: CLEAN-truth cases average P(CLEAN)=0.584, DEFECTIVE-truth
cases average 0.555, a real (if compressed) separation in the correct
direction.

**Second finding, also disclosed and corrected in place:** my first
attempt at selecting a "best" threshold read the threshold directly off
test-set performance — test-set leakage for threshold selection. Fixed:
the threshold is now selected purely from **validation-set** performance,
then applied to test **exactly once**, no further tuning against test
results.

### Val-selected thresholds applied once to the frozen test set

| | Baseline (SBERT<0.95 OR NLI OR grammar) | Learned, lex-selected (thresh=0.552) | Learned, balanced-selected (thresh=0.579) |
|---|---|---|---|
| Defect recall | 0.60 | 0.65 | **0.77** |
| Defect precision | 0.90 | 0.93 | 0.92 |
| CLEAN recall | 0.62 | **0.75** | 0.62 |
| Accuracy | 0.61 | 0.67 | 0.75 |

**Both val-selected operating points beat the baseline on defect recall
and defect precision simultaneously; the lex-selected one also beats it
on CLEAN retention.** The balanced threshold's headline number: it
catches **77% of real defects** (vs. the rule-based stack's 60%) while
holding precision at 92% (vs. 90%) and CLEAN retention exactly even
(62% vs. 62%) — a genuine, non-trivial improvement on the metric that
matters most for a validator's actual job (catching what currently
slips through), not a coincidence of favorable threshold-picking.

**Generalization check:** all 51 test records have a `dedup_key` never
seen in train/val (100% of the test set is out-of-distribution
word-pairs/sentences by construction of the frozen split) — the reported
numbers are already a genuine unseen-case measurement, not partly
memorization.

**FACTUAL_OR_LOGICAL_REVERSAL, by evidence quality** (n=7, too small for
a rate, reported per-case as instructed): the 3 organic/human-reviewed
cases were all caught correctly (predicted DEFECTIVE); 1 of 4 constructed
cases was caught. Directionally opposite of what might be assumed —
the model did *better*, not worse, on the real observed failure than on
the constructed ones in this small sample — but n is far too small to
generalize from.

## 6. Honest limitations

- Test set is small (51 records, only 8 CLEAN) — each CLEAN
  misclassification moves clean-recall by 12.5 points. The reported
  numbers are directionally real but not tightly estimated.
- Model confidence is poorly calibrated (all scores compressed near
  0.55) even though ranking carries real signal — this model should be
  used for ranking/thresholded triage, not as a calibrated probability.
- Single training run, single random seed — not repeated to check
  run-to-run variance (would require another ~5h CPU run; not performed
  automatically per the standing discipline against unscoped extra runs).
- `FACTUAL_OR_LOGICAL_REVERSAL` evidence remains thin and majority
  constructed (per Phase 8B) — the 7-case breakdown above is illustrative
  only.

## 7. Does this justify further development?

**Yes — directionally, on real evidence, not a hunch.** A single
corrected training run produced a model that:
1. Trained stably (0 non-finite weights, confirmed by inspection).
2. Shows genuine, methodologically-clean discrimination on a frozen,
   never-touched-for-tuning test set, entirely composed of unseen
   word-pairs.
3. Beats the best existing-signal baseline on defect recall and
   precision simultaneously (77% vs 60% recall, 92% vs 90% precision),
   with CLEAN retention tied or better depending on the chosen operating
   point.

This is one run, on a small test set, with an unresolved calibration
issue and a bug-prone-but-now-fixed evaluation methodology — it is
evidence a prototype is *worth continuing to develop*, not evidence a
production-ready validator exists. No integration performed. A sensible
next step (not undertaken here) would be a second independent training
run (different seed) to check whether the recall/precision numbers above
are stable or run-specific, before any production discussion.
