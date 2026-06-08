"""
LoRA fine-tuning skeleton for the optional rephrase model.

Default mode is a five-row smoke validator and does not train:

    python scripts/train_rephrase.py --data scripts/toy_rephrase_dataset.jsonl --smoke

Actual training is intentionally opt-in and should be run on Colab/Kaggle or a
local GPU after installing scripts/requirements-train.txt:

    python scripts/train_rephrase.py --data data/rephrase.jsonl --train
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if limit and len(rows) >= limit:
                break
    return rows


def _validate(rows: list[dict]) -> None:
    if not rows:
        raise ValueError("dataset is empty")
    for i, row in enumerate(rows, 1):
        if not row.get("input") or not row.get("target"):
            raise ValueError(f"row {i} must contain input and target")


def _train_lora(args, rows: list[dict]) -> None:
    # TODO: move this into a real training run once a curated dataset exists.
    # Suggested flow:
    #   1. upload JSONL to Colab/Kaggle GPU
    #   2. train LoRA adapters with PEFT
    #   3. merge adapters or keep adapter path
    #   4. point rephrase.REPHRASE_MODEL at the fine-tuned local/HF path
    #   5. optionally export to CTranslate2 for faster CPU inference
    try:
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, TrainingArguments, Trainer
    except Exception as exc:
        print(f"training deps unavailable ({exc.__class__.__name__}: {exc}); smoke validation passed")
        return

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model)
    config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=["q", "v"],
        lora_dropout=0.05,
        bias="none",
        task_type="SEQ_2_SEQ_LM",
    )
    model = get_peft_model(model, config)

    def preprocess(batch):
        encoded = tokenizer(batch["input"], truncation=True, max_length=args.max_length)
        labels = tokenizer(batch["target"], truncation=True, max_length=args.max_length)
        encoded["labels"] = labels["input_ids"]
        return encoded

    dataset = Dataset.from_list(rows).map(preprocess, batched=True)
    training_args = TrainingArguments(
        output_dir=str(args.output),
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        learning_rate=args.lr,
        logging_steps=1,
        save_steps=max(args.max_steps, 1),
        report_to=[],
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=dataset)
    trainer.train()
    trainer.save_model(str(args.output))
    tokenizer.save_pretrained(str(args.output))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parent / "toy_rephrase_dataset.jsonl")
    parser.add_argument("--model", default="Vamsi/T5_Paraphrase_Paws")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "rephrase_lora_out")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--max-length", type=int, default=160)
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    args = parser.parse_args()

    rows = _read_jsonl(args.data, limit=5 if args.smoke else None)
    _validate(rows)
    print(f"loaded {len(rows)} rows from {args.data}")
    for row in rows[:5]:
        print(f"- input:  {row['input']}")
        print(f"  target: {row['target']}")

    if args.train:
        _train_lora(args, rows)
    else:
        print("smoke validation only; pass --train to start LoRA training")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
