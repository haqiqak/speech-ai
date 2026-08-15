"""Archived audio-facing profiling package — NOT wired into the live app.

Preserved standalone (with its own copy of config.py) so it stays runnable and
testable in isolation. See out_of_scope/README.md for why this was moved out of
the active `profiling/` package.
"""

from .asr import CrisperWhisperASR, VerbatimToken
from .detect import detect_disfluencies

__all__ = [
    "CrisperWhisperASR",
    "VerbatimToken",
    "detect_disfluencies",
]
