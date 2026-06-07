"""
paths.py — keep all runtime caches/data inside the project, and keep startup
memory low.

Import this FIRST — before nltk / sentence_transformers / torch / wordfreq —
in every entry module.  It points NLTK data and the HuggingFace/Torch model
caches at a project-local `.cache/` folder, so first-run downloads (WordNet,
tagger, cmudict, the SBERT model, torch hub) live next to the app instead of
scattered in per-user system cache directories.

setdefault() is used everywhere, so an explicit environment override (e.g. set
by a launcher or CI) always wins.
"""
import os
from pathlib import Path

_ROOT  = Path(__file__).resolve().parent          # project root
_CACHE = _ROOT / ".cache"

# Cap BLAS/OpenMP threads BEFORE numpy/torch import.  OpenBLAS otherwise
# pre-allocates per-thread buffers sized for every CPU core, a large upfront
# allocation that fails on RAM-constrained machines ("OpenBLAS error: Memory
# allocation still failed").  setdefault lets a machine with spare RAM override.
for _t in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_t, "1")

_TARGETS = {
    "NLTK_DATA":                  _CACHE / "nltk_data",
    "HF_HOME":                    _CACHE / "hf",
    "SENTENCE_TRANSFORMERS_HOME": _CACHE / "hf" / "sbert",
    "TORCH_HOME":                 _CACHE / "torch",
}

for _var, _path in _TARGETS.items():
    _path.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(_var, str(_path))

# Quiet, offline-friendly HF behaviour
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

# Ensure nltk searches the project data dir first (covers data already there).
try:
    import nltk
    _nltk_dir = os.environ["NLTK_DATA"]
    if _nltk_dir not in nltk.data.path:
        nltk.data.path.insert(0, _nltk_dir)
except Exception:
    pass
