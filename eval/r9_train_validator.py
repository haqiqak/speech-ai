"""
eval/r9_train_validator.py -- Phase 9, step 3: fine-tune a SMALL
cross-encoder classifier (binary ACCEPT/REJECT) on the human-labeled
train split, validate on val, evaluate on the frozen test split.

Base model: microsoft/deberta-v3-xsmall (~70M params) -- same
architecture family as the existing NLI cross-encoder already proven to
load and run in this environment, chosen per "start with the smallest
viable model."

Label convention: 1.0 = CLEAN (the minority/rare class), 0.0 = DEFECTIVE.
pos_weight compensates for class imbalance (train: 188 DEFECTIVE / 17
CLEAN) so the model doesn't collapse to always predicting DEFECTIVE.

RESEARCH/PROTOTYPE ONLY. This model is NOT wired into reformulate.py or
app.py. It is saved to a local, git-ignored directory for evaluation
only; per instruction, integration happens only after passing the three
gate questions (generalization, beats-baseline, precision/coverage).
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

EVAL = Path(__file__).parent
MODEL_OUT = EVAL / "r9_validator_model"

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
pos_weight = torch.tensor(n_defective / max(n_clean, 1))
print(f"train n={len(train_rows['label'])} (CLEAN={int(n_clean)}, DEFECTIVE={int(n_defective)}), pos_weight={pos_weight.item():.2f}")

train_ds = Dataset.from_dict(train_rows)
val_ds = Dataset.from_dict(val_rows)

model = CrossEncoder("microsoft/deberta-v3-xsmall", num_labels=1)
loss = BinaryCrossEntropyLoss(model, pos_weight=pos_weight)

args = CrossEncoderTrainingArguments(
    output_dir=str(MODEL_OUT / "checkpoints"),
    num_train_epochs=8,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    learning_rate=2e-5,
    warmup_ratio=0.1,
    eval_strategy="epoch",
    save_strategy="no",
    logging_steps=10,
    seed=42,
)

trainer = CrossEncoderTrainer(
    model=model,
    args=args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    loss=loss,
)
trainer.train()

MODEL_OUT.mkdir(exist_ok=True)
model.save(str(MODEL_OUT / "final"))
print(f"\nsaved prototype validator model to {MODEL_OUT / 'final'}")
