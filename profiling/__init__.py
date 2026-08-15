"""Profiling package — persistent speaker difficulty profile for text reformulation.

As of the Stage 2 scope-narrowing pass (see DECISION_LOG.md), this package holds
only the parts of the fluency-profiling stack that the text reformulation module
itself needs: the profile model and its cold-start priors. The audio-facing
pieces that used to live here (CrisperWhisper ASR wrapper, rule-based disfluency
detection over ASR timing) were moved to out_of_scope/profiling/ — they belong to
the separate Audio Module, not this repository. See out_of_scope/README.md.
"""

from .profile import SpeakerDifficultyProfile

__all__ = [
    "SpeakerDifficultyProfile",
]
