# Phase 9B, step 1 — diagnosis of the R9 NaN failure

## Exact configuration used in the failed run (confirmed from `eval/r9_train_validator.py` + `eval/r9_train.log`)

- Base model: `microsoft/deberta-v3-xsmall` (~70M params), `CrossEncoder(num_labels=1)`
- Loss: `BinaryCrossEntropyLoss` with `pos_weight = n_defective/n_clean = 188/17 ≈ 11.06`
- `learning_rate=2e-5`, `num_train_epochs=8`, `per_device_train_batch_size=8`, `warmup_ratio=0.1`
- `eval_strategy="epoch"`, `save_strategy="no"`
- No explicit `max_grad_norm`, `fp16`, `bf16`, or `adam_epsilon` override — all left at library defaults.

## Correction to the original R9 diagnosis

R9's report hypothesized "no explicit gradient clipping" as a contributing cause. **That hypothesis was checked directly against `CrossEncoderTrainingArguments`'s actual defaults and is wrong**, disclosed here rather than left standing: `max_grad_norm` defaults to **`1.0`**, and `fp16`/`bf16` both default to `False` (full fp32). Gradient clipping and full precision were already active throughout the failed run. The logged `grad_norm` values (e.g. 24.47 at epoch 2.69) are the **pre-clip** norm that `torch.nn.utils.clip_grad_norm_` returns — the actual optimizer step used gradients already clipped to norm 1.0. Clipping was working as configured; it did not prevent the collapse at epoch 3.08.

## Revised root-cause hypothesis

With clipping and fp32 ruled out, the more likely contributors are:

1. **`pos_weight≈11.06` is still a large loss multiplier** even post-clipping — clipping bounds the gradient *norm* per step, but repeated large-magnitude updates on the 17 up-weighted CLEAN examples can still walk the model into a numerically unstable region (e.g. saturated logits) over a few dozen steps, at which point a single forward pass can produce `inf`/`nan` in DeBERTa's disentangled-attention softmax independent of gradient clipping.
2. **`adam_epsilon=1e-8`** (the library default) is smaller than the `1e-6` commonly recommended for DeBERTa-family fine-tuning specifically because of known numerical-stability sensitivity in its attention mechanism — a documented, model-family-specific issue, not unique to this dataset.
3. **`learning_rate=2e-5`** is on the higher end for a 205-example fine-tune regardless of the above.

## Phase 9B's conservative configuration (addresses all three, plus the explicitly requested items)

| Setting | R9 (failed) | R9B |
|---|---|---|
| learning_rate | 2e-5 | **3e-6** (within the requested 2e-6–5e-6 range) |
| pos_weight | ≈11.06 | **4.0** (capped, within the requested 3–5×) |
| max_grad_norm | 1.0 (default, unstated) | **1.0 (explicit)** |
| adam_epsilon | 1e-8 (default) | **1e-6** (extra precaution for DeBERTa stability, beyond what was explicitly requested but directly implied by the diagnosis) |
| epochs | 8, fixed | up to 8, **early stopping on eval_loss** (patience 2) |
| eval/save strategy | eval=epoch, save=no | eval=epoch, save=epoch (required for early stopping / best-checkpoint restore) |

Dataset and split are **unchanged** — `eval/r50_dataset/r9_final_dataset.json` and `r9_split.json` are reused exactly as written, not regenerated.
