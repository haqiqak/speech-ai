"""Meaning-preserving, profile-aware paragraph rewriting."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from engine import SynonymEngine
from grammar import _detokenize, _preserve_case, inflect
import phonetic

from profiling.config import load_config
from profiling.profile import SpeakerDifficultyProfile
from .candidates import detect_protected_words, gather_candidate_slots, safe_word_tokenize
from .rank import rank_candidates


def _split_sentences(text: str) -> list[str]:
    parts = re.findall(r"[^.!?]+[.!?]?", text or "")
    return [p.strip() for p in parts if p.strip()] or ([text.strip()] if text.strip() else [])


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'-]*", text or "")


def _surface_for(lemma: str, tag: str, original_word: str) -> str:
    try:
        return _preserve_case(original_word, inflect(lemma, tag))
    except Exception:
        return _preserve_case(original_word, lemma)


@dataclass
class RewriteSettings:
    lambda_: float
    mu: float
    tau: float
    top_k: int
    risk_threshold: float
    min_improvement: float


class DifficultyAwareRewriter:
    """Soft difficulty-penalty rewriter backed by a speaker profile."""

    def __init__(self, engine: SynonymEngine | None = None, config: dict | None = None):
        self.engine = engine or SynonymEngine()
        self.config = config or load_config()

    @property
    def settings(self) -> RewriteSettings:
        cfg = self.config.get("rewrite", {})
        return RewriteSettings(
            lambda_=float(cfg.get("lambda", 0.55)),
            mu=float(cfg.get("mu", 0.12)),
            tau=float(cfg.get("tau", 0.80)),
            top_k=int(cfg.get("top_k", 12)),
            risk_threshold=float(cfg.get("risk_threshold", 0.55)),
            min_improvement=float(cfg.get("min_improvement", 0.01)),
        )

    def rewrite_paragraph(
        self,
        text: str,
        profile: SpeakerDifficultyProfile,
        always_keep: Iterable[str] | None = None,
        always_replace: Iterable[str] | None = None,
        lambda_: float | None = None,
        mu: float | None = None,
        tau: float | None = None,
    ) -> dict:
        settings = self.settings
        lam = settings.lambda_ if lambda_ is None else float(lambda_)
        mu_val = settings.mu if mu is None else float(mu)
        tau_val = settings.tau if tau is None else float(tau)
        always_keep_set = {str(w).strip().lower() for w in (always_keep or []) if str(w).strip()}
        always_replace_set = {str(w).strip().lower() for w in (always_replace or []) if str(w).strip()}

        rewritten_sentences: list[str] = []
        original_sentences = _split_sentences(text)
        changes: list[dict] = []
        skipped: list[dict] = []

        for sid, sentence in enumerate(original_sentences):
            protected = detect_protected_words(sentence, always_keep=always_keep_set)
            tokens, slots = gather_candidate_slots(
                sentence,
                top_k=settings.top_k,
                protected_words=protected,
                engine=self.engine,
            )
            current_tokens = list(tokens)

            for slot in slots:
                original_word = current_tokens[slot.position]
                original_low = original_word.lower()
                orig_diff = profile.difficulty(original_word, slot.tag)
                force = original_low in always_replace_set
                if not force and orig_diff < settings.risk_threshold:
                    continue

                surfaces = {
                    lemma: _surface_for(lemma, slot.tag, original_word)
                    for lemma in slot.candidates
                }
                ranked = rank_candidates(
                    sentence,
                    current_tokens,
                    slot.position,
                    surfaces,
                    profile,
                    lambda_=lam,
                    mu=mu_val,
                    tau=tau_val,
                )
                accepted = [row for row in ranked if row.accepted]
                if not accepted:
                    skipped.append({"word": original_word, "reason": "semantic gate"})
                    continue

                best = accepted[0]
                improvement = orig_diff - best.difficulty
                if not force and improvement < settings.min_improvement:
                    skipped.append({"word": original_word, "reason": "no easier candidate"})
                    continue

                current_tokens[slot.position] = best.surface
                onset = "/".join(phonetic.onset(original_word)) or "-"
                changes.append(
                    {
                        "id": f"{sid}:{slot.position}:{original_word}:{best.surface}",
                        "sentence_index": sid,
                        "position": slot.position,
                        "orig": original_word,
                        "replacement": best.surface,
                        "lemma": best.lemma,
                        "reason": f"avoided /{onset}/ onset",
                        "sim": best.sim,
                        "sim_source": best.sim_source,
                        "difficulty_before": round(orig_diff, 4),
                        "difficulty_after": round(best.difficulty, 4),
                        "score": round(best.score, 4),
                        "accepted": True,
                        "candidates": [r.to_dict() for r in ranked[:8]],
                    }
                )

            rewritten_sentences.append(_detokenize(current_tokens))

        rewritten = " ".join(rewritten_sentences)
        metrics = self.metrics(text, rewritten, profile)
        return {
            "original_text": text,
            "rewritten_text": rewritten,
            "change_log": changes,
            "skipped": skipped,
            "metrics": metrics,
            "settings": {"lambda": lam, "mu": mu_val, "tau": tau_val},
        }

    def metrics(self, original: str, rewritten: str, profile: SpeakerDifficultyProfile) -> dict:
        before_diff = profile.sentence_difficulty(original)
        after_diff = profile.sentence_difficulty(rewritten)
        before_count = profile.risk_count(original, self.settings.risk_threshold)
        after_count = profile.risk_count(rewritten, self.settings.risk_threshold)
        substitutions = sum(
            1 for a, b in zip(_words(original), _words(rewritten)) if a.lower() != b.lower()
        )
        total = max(1, len(_words(original)))
        count_reduction = 0.0
        if before_count:
            count_reduction = (before_count - after_count) / before_count
        return {
            "difficulty_before": round(before_diff, 4),
            "difficulty_after": round(after_diff, 4),
            "difficulty_delta": round(after_diff - before_diff, 4),
            "difficulty_onset_before": before_count,
            "difficulty_onset_after": after_count,
            "difficulty_onset_reduction_pct": round(100.0 * count_reduction, 2),
            "substitution_rate": round(substitutions / total, 4),
        }

    def render_with_decisions(self, result: dict, accepted_change_ids: Iterable[str]) -> str:
        accepted = set(accepted_change_ids)
        sentences = _split_sentences(result.get("original_text", ""))
        token_rows = [safe_word_tokenize(sentence) for sentence in sentences]
        for change in result.get("change_log", []):
            if change.get("id") not in accepted:
                continue
            sid = int(change.get("sentence_index", 0))
            pos = int(change.get("position", -1))
            if 0 <= sid < len(token_rows) and 0 <= pos < len(token_rows[sid]):
                token_rows[sid][pos] = str(change.get("replacement", token_rows[sid][pos]))
        return " ".join(_detokenize(tokens) for tokens in token_rows)

    def sweep_lambda(
        self,
        text: str,
        profile: SpeakerDifficultyProfile,
        lambdas: Iterable[float] | None = None,
        always_keep: Iterable[str] | None = None,
        always_replace: Iterable[str] | None = None,
    ) -> list[dict]:
        vals = list(lambdas or self.config.get("rewrite", {}).get("lambda_sweep", [0.0, 0.5, 1.0]))
        rows: list[dict] = []
        for lam in vals:
            result = self.rewrite_paragraph(
                text,
                profile,
                always_keep=always_keep,
                always_replace=always_replace,
                lambda_=float(lam),
            )
            rows.append(
                {
                    "lambda": float(lam),
                    "changes": len(result.get("change_log", [])),
                    **result.get("metrics", {}),
                }
            )
        return rows
