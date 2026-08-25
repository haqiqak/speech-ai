"""
eval/r9b_train_validator.py -- Phase 9B, step 4: the full training run
with the conservative configuration, using the EXACT SAME dataset/split
as R9 (unchanged). Only run this after eval/r9b_sanity_train.py has
reported PASSED.

Changes from R9 (see eval/r9b_diagnosis.md for the full rationale):
  - learning_rate: 2e-5 -> 3e-6
  - pos_weight: ~11.06 -> 4.0 (capped)
  - max_grad_norm: 1.0, set explicitly (was already the default, but
    unstated in R9)
  - adam_epsilon: 1e-8 -> 1e-6 (DeBERTa-specific stability precaution)
  - early stopping on eval_loss (patience 2), save_strategy="epoch" +
    load_best_model_at_end=True so the restored model is the best
    checkpoint, not necessarily the last one

RESEARCH/PROTOTYPE ONLY. Not integrated into reformulate.py or app.py.
"""
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from sentence_transformers import CrossEncoder
from sentence_transformers.cross_encoder import CrossEncoderTrainer, CrossEncoderTrainingArguments
from sentence_transformers.cross_encoder.losses import BinaryCrossEntropyLoss
from datasets import Dataset
from transformers import TrainerCallback, EarlyStoppingCallback

EVAL = Path(__file__).parent
MODEL_OUT = EVAL / "r9b_validator_model"

data = json.load(open(EVAL / "r50_dataset" / "r9_final_dataset.json", encoding="utf-8"))
by_uid = {r["uid"]: r for r in data["records"]}
split = json.load(open(EVAL / "r50_dataset" / "r9_split.json", encoding="utf-8"))

def to_rows(uids):
    rows = {"sentence1": [], "sentence2": [], "label": []}
    for u in uids:
        r = by_uid[u]
        rows["sentence1"].append(r["original_text"])
        rows["sentence2"].append(r["reformulated_text"])
        rows["label"].append(1.0 if r["acceptability"] == "CLEAN" else 0.0)
    return rows

train_rows = to_rows(split["train_uids"])
val_rows = to_rows(split["val_uids"])
n_clean = sum(train_rows["label"])
n_defective = len(train_rows["label"]) - n_clean
print(f"train n={len(train_rows['label'])} (CLEAN={int(n_clean)}, DEFECTIVE={int(n_defective)})")

POS_WEIGHT = 4.0
print(f"pos_weight (capped, was ~{n_defective/max(n_clean,1):.2f} uncapped) = {POS_WEIGHT}")

train_ds = Dataset.from_dict(train_rows)
val_ds = Dataset.from_dict(val_rows)

model = CrossEncoder("microsoft/deberta-v3-xsmall", num_labels=1)
loss = BinaryCrossEntropyLoss(model, pos_weight=torch.tensor(POS_WEIGHT))

class FiniteCheckCallback(TrainerCallback):
    def __init__(self):
        self.saw_nonfinite = False
        self.first_nonfinite_step = None

    def on_step_end(self, args, state, control, model=None, **kwargs):
        for name, p in model.named_parameters():
            if p.requires_grad and not torch.isfinite(p).all():
                self.saw_nonfinite = True
                if self.first_nonfinite_step is None:
                    self.first_nonfinite_step = state.global_step
                print(f"  [step {state.global_step}] NON-FINITE WEIGHT: {name} -- STOPPING")
                control.should_training_stop = True
                return

checker = FiniteCheckCallback()

args = CrossEncoderTrainingArguments(
    output_dir=str(MODEL_OUT / "checkpoints"),
    num_train_epochs=8,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    learning_rate=3e-6,
    max_grad_norm=1.0,
    adam_epsilon=1e-6,
    warmup_ratio=0.1,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    logging_steps=5,
    seed=42,
)

trainer = CrossEncoderTrainer(
    model=model,
    args=args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    loss=loss,
    callbacks=[checker, EarlyStoppingCallback(early_stopping_patience=2)],
)
trainer.train()

print("\n" + "=" * 60)
if checker.saw_nonfinite:
    print(f"TRAINING ABORTED -- non-finite weights detected at step {checker.first_nonfinite_step}. "
          "The conservative config still diverged; not saving a broken model.")
else:
    MODEL_OUT.mkdir(exist_ok=True)
    model.save(str(MODEL_OUT / "final"))
    print(f"TRAINING COMPLETED, stable throughout. Saved best checkpoint (by eval_loss) to {MODEL_OUT / 'final'}")
