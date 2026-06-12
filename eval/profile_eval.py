"""Profile predictive evaluation for self-report, observed, and fused signals."""

from __future__ import annotations

from typing import Iterable

import phonetic
from profiling.coldstart import self_report_prior
from profiling.profile import SpeakerDifficultyProfile


def _auc(labels: list[int], scores: list[float]) -> float | None:
    try:
        from sklearn.metrics import roc_auc_score

        if len(set(labels)) < 2:
            return None
        return float(roc_auc_score(labels, scores))
    except Exception:
        return None


def _onset_key(word: str) -> str:
    return " ".join(phonetic.onset(word))


def compare_profile_auc(
    events: Iterable[dict],
    self_reported_sounds: Iterable[str],
    observed_profile: SpeakerDifficultyProfile,
    fused_profile: SpeakerDifficultyProfile | None = None,
) -> dict[str, float | None]:
    rows = [e for e in events if e.get("word")]
    labels = [1 if e.get("disfluent", e.get("type") is not None) else 0 for e in rows]
    report_prior = self_report_prior(self_reported_sounds)

    self_scores = [report_prior.get(_onset_key(e["word"]), 0.0) for e in rows]
    observed_scores = [observed_profile.difficulty(e["word"]) for e in rows]
    fused = fused_profile or observed_profile
    fused_scores = [fused.difficulty(e["word"]) for e in rows]

    return {
        "self_report_auc": _auc(labels, self_scores),
        "observed_auc": _auc(labels, observed_scores),
        "fused_auc": _auc(labels, fused_scores),
        "n_events": len(rows),
    }
