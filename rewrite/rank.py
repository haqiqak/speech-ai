"""Soft-constraint ranking for difficulty-aware rewrites."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import difflib
import math
from pathlib import Path
from typing import Iterable

from freq import zipf_frequency
from grammar import _detokenize
import semantic
from profiling.profile import SpeakerDifficultyProfile


@dataclass
class RankedCandidate:
    lemma: str
    surface: str
    candidate_sentence: str
    sim: float | None
    sim_source: str
    difficulty: float
    zipf_norm: float
    score: float
    accepted: bool

    def to_dict(self) -> dict:
        row = asdict(self)
        row["score"] = round(float(row["score"]), 4)
        row["difficulty"] = round(float(row["difficulty"]), 4)
        row["zipf_norm"] = round(float(row["zipf_norm"]), 4)
        if row["sim"] is not None:
            row["sim"] = round(float(row["sim"]), 4)
        return row


def zipf_norm(word: str) -> float:
    raw = max(0.0, zipf_frequency(word, "en"))
    return min(math.log(1.0 + raw) / math.log(8.0), 1.0)


def candidate_sentence(tokens: list[str], position: int, replacement: str) -> str:
    new_tokens = list(tokens)
    new_tokens[position] = replacement
    return _detokenize(new_tokens)


def _fallback_similarity(original: str, candidate: str) -> float:
    return difflib.SequenceMatcher(None, original.lower(), candidate.lower()).ratio()


def semantic_similarity(original: str, candidate: str) -> tuple[float | None, str]:
    sim = semantic.semantic_similarity(candidate, original)
    if sim is not None:
        return float(sim), "sbert"
    # Existing app behavior accepts candidates when SBERT is unavailable. Keep a
    # lexical value for sorting only; mark its source so evaluations know it is
    # not an SBERT score.
    return _fallback_similarity(original, candidate), "fallback"


def rank_candidates(
    original_sentence: str,
    tokens: list[str],
    position: int,
    candidate_surfaces: dict[str, str],
    profile: SpeakerDifficultyProfile,
    lambda_: float = 0.55,
    mu: float = 0.12,
    tau: float = 0.80,
) -> list[RankedCandidate]:
    rows: list[RankedCandidate] = []
    for lemma, surface in candidate_surfaces.items():
        sent = candidate_sentence(tokens, position, surface)
        sim, source = semantic_similarity(original_sentence, sent)
        if source == "sbert":
            accepted = bool(sim is not None and sim >= tau)
            sim_for_score = float(sim or 0.0)
        else:
            accepted = True
            sim_for_score = max(float(sim or 0.0), tau)
        diff = profile.difficulty(surface)
        freq = zipf_norm(surface)
        score = sim_for_score - (lambda_ * diff) + (mu * freq)
        rows.append(
            RankedCandidate(
                lemma=lemma,
                surface=surface,
                candidate_sentence=sent,
                sim=sim,
                sim_source=source,
                difficulty=diff,
                zipf_norm=freq,
                score=score,
                accepted=accepted,
            )
        )
    rows.sort(key=lambda row: (not row.accepted, -row.score, row.difficulty, row.surface))
    return rows


def write_tradeoff_csv(rows: Iterable[dict], path: str | Path) -> None:
    rows = list(rows)
    if not rows:
        return
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
