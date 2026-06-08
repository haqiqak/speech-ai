# Rephrase Fine-Tuning Scaffolding

The deployed app never calls a cloud teacher at inference. The optional
`rephrase.py` layer uses a local/Transformers model and degrades to passthrough
when weights or tokenizer support are unavailable.

## Dataset

Build an offline self-distilled JSONL dataset:

```powershell
python scripts/build_rephrase_dataset.py --input tests/eval_corpus.txt --output data/rephrase.jsonl --n 8
```

Each row uses the control format:

```text
avoid: <onsets> | blocked: <words> | repair: <synonym-built sentence>
```

Teachers, if you add any, are offline-only dataset builders. They are never
called by the deployed Streamlit app.

## Smoke Run

```powershell
python scripts/build_rephrase_dataset.py --smoke --output scripts/toy_rephrase_dataset.jsonl
python scripts/train_rephrase.py --data scripts/toy_rephrase_dataset.jsonl --smoke
```

## Training

Install `scripts/requirements-train.txt` in a separate GPU notebook or training
environment, then run:

```powershell
python scripts/train_rephrase.py --data data/rephrase.jsonl --train --output outputs/rephrase-lora
```

Use Colab/Kaggle or another GPU environment for training. After training, point
`REPHRASE_MODEL` in `rephrase.py` (or the environment variable) at the merged
weights or adapter-compatible local path. For CPU inference, consider exporting
the final model to CTranslate2 after validation.
