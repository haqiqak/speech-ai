"""
eval/r9b_sanity_train.py -- Phase 9B, step 2: a SHORT sanity pass (10
optimizer steps, no full training) with the new conservative config, to
verify loss/gradients/weights stay finite BEFORE committing to a full
8-epoch CPU run. Uses the exact same dataset/split as R9 -- unchanged.

If this reports any non-finite value, the full run in
eval/r9b_train_validator.py must NOT be started; a further reduced
learning rate or pos_weight would be needed first (not attempted
automatically here).
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
from transformers import TrainerCallback

EVAL = Path(__file__).parent

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
train_ds = Dataset.from_dict(train_rows)

POS_WEIGHT = 4.0
model = CrossEncoder("microsoft/deberta-v3-xsmall", num_labels=1)
loss = BinaryCrossEntropyLoss(model, pos_weight=torch.tensor(POS_WEIGHT))

class FiniteCheckCallback(TrainerCallback):
    def __init__(self):
        self.saw_nonfinite = False

    def on_step_end(self, args, state, control, model=None, **kwargs):
        bad = []
        for name, p in model.named_parameters():
            if p.requires_grad and not torch.isfinite(p).all():
                bad.append(f"WEIGHT non-finite: {name}")
            if p.grad is not None and not torch.isfinite(p.grad).all():
                bad.append(f"GRAD non-finite: {name}")
        if bad:
            self.saw_nonfinite = True
            print(f"  [step {state.global_step}] NON-FINITE DETECTED: {bad[:3]} (+{max(0,len(bad)-3)} more)")
        else:
            print(f"  [step {state.global_step}] all weights and grads finite OK")

checker = FiniteCheckCallback()

args = CrossEncoderTrainingArguments(
    output_dir=str(EVAL / "r9b_sanity_checkpoints"),
    max_steps=10,
    per_device_train_batch_size=8,
    learning_rate=3e-6,
    max_grad_norm=1.0,
    adam_epsilon=1e-6,
    warmup_ratio=0.1,
    eval_strategy="no",
    save_strategy="no",
    logging_steps=1,
    seed=42,
)

trainer = CrossEncoderTrainer(
    model=model,
    args=args,
    train_dataset=train_ds,
    loss=loss,
    callbacks=[checker],
)
trainer.train()

print("\n" + "=" * 60)
if checker.saw_nonfinite:
    print("SANITY CHECK RESULT: FAILED -- non-finite values detected. "
          "Do NOT proceed to the full training run without further changes.")
else:
    print("SANITY CHECK RESULT: PASSED -- loss, gradients, and weights "
          "remained finite for all 10 steps. Safe to proceed to the full run.")
