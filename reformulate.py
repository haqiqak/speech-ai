"""
reformulate.py — the consolidated reformulation engine (Architecture D′,
REFORMULATION_RESEARCH.md §24-31). Replaces grammar.py::SentenceRewriter and
rewrite/rewriter.py::DifficultyAwareRewriter as the live orchestrator; both
are kept in the repo, unused by app.py, until this engine is measured to be
at least as good on the failure-mode corpus (§30's migration plan) — this
module does not delete them.

Pipeline (§30):
    1. TAG    — which content words in each sentence are flagged by the
                profile (declared word / declared global sound onset match).
                Reuses engine.py/phonetic.py/semantic.py exactly as before;
                no new candidate source, no new scoring formula.
    2. Escalation decision — per sentence, BEFORE attempting substitution:
                escalate straight to restructuring if too many words are
                flagged at once (§24.D's new trigger) or too large a
                fraction of the sentence is flagged (§24.F's degenerate-
                profile cap) — both funnel into the SAME T5 escalation path,
                not a separate give-up path.
    3. SUBSTITUTE-AND-RANK — for sentences that don't pre-escalate: try a
                candidate for every flagged position. All-or-nothing per
                sentence — if any flagged position has no candidate that
                clears every gate, the whole sentence escalates instead of
                shipping a partial patchwork (§24.D).
    4. Tiered semantic verification (§24.A) — WordNet antonym rejection
                (free) -> SBERT threshold (existing) -> phoneme veto
                (existing). NLI is Strong-tier, not built here (§27).
    5. ESCALATE (T5, rephrase.py, unchanged code, new role) — generate
                candidates from the ORIGINAL sentence (not a partial
                substitution), each re-checked with the SAME phoneme veto,
                SBERT threshold, and a sentence-level negation-consistency
                check (semantic.negation_consistent) in place of the
                single-word antonym check, which doesn't apply to a
                freely-generated paraphrase.
    6. FINAL VERIFICATION — re-run the flagging check on the actual
                assembled output (not just per-candidate) and require it to
                have improved — SpeechAgent's "recovery rate" idea (§2.2),
                independently arrived at.
    7. METRICS — meaning preservation, difficulty (flag) reduction, and
                naturalness reported separately, never blended (Practice §10).

No model training. No new heavy dependency — antonym checking is stdlib
NLTK WordNet (already a dependency), edit-amount scoring is difflib
(already used elsewhere in this codebase, rephrase.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

import nltk
from nltk import pos_tag, word_tokenize

import engine as engine_module
import phonetic as ph
import semantic as sem
import naturalness as nat
import rephrase
from difficulty_profile import DifficultyProfile
from grammar import _SUBSTITUTABLE, _STOP, _wn_pos, lemmatize, inflect, _preserve_case, _detokenize

nltk.download("averaged_perceptron_tagger_eng", quiet=True)
nltk.download("punkt_tab", quiet=True)


@dataclass
class ReformulateSettings:
    sbert_threshold: float = None       # None -> use semantic.MIN_SEMANTIC at call time
    top_k: int = 10
    escalation_word_count: int = 2      # >this many flagged content words -> escalate (§24.D)
    degenerate_fraction: float = 0.6    # >this fraction of content words flagged -> escalate (§24.F)
    t5_candidates: int = 5


_ABBREVS = {
    "mr.", "mrs.", "ms.", "dr.", "prof.",
    "sr.", "jr.", "vs.", "etc.", "approx.",
    "fig.", "vol.", "no.", "dept.", "est.",
    "p.m.", "a.m.", "u.s.", "u.k.",
}


def split_sentences(text: str) -> list[str]:
    """Canonical sentence splitter — the one place this logic now lives.
    (Previously duplicated in app.py and rewrite/rewriter.py; both of those
    copies are dead code once app.py calls this module instead.)"""
    sentences: list[str] = []
    current: list[str] = []
    for word in (text or "").split():
        current.append(word)
        if word.endswith((".", "!", "?")) and word.lower() not in _ABBREVS:
            sentences.append(" ".join(current))
            current = []
    if current:
        sentences.append(" ".join(current))
    return [s for s in sentences if s.strip()]


def _raw_candidates(engine: "engine_module.SynonymEngine", lemma: str, pos_tag_str: str,
                     original_word: str, top_k: int) -> list[str]:
    """Same filtering as the old grammar.py::SentenceRewriter._raw_candidates
    (same-POS check via wn_pos, single-token only, prefer -ly forms for -ly
    adverbs) — reimplemented standalone here rather than depending on the
    class being discarded, so this module has no hidden coupling to it."""
    wn_p = _wn_pos(pos_tag_str)
    all_syns = engine.get_synonyms(lemma, top_k=top_k * 2, wn_pos=wn_p).get(lemma, [])
    prefer_ly = pos_tag_str.startswith("RB") and original_word.lower().endswith("ly")

    from nltk.corpus import wordnet as wn
    filtered = []
    for cand in all_syns:
        if cand in (lemma, original_word.lower()):
            continue
        if " " in cand:
            continue
        is_adverb = pos_tag_str.startswith("RB")
        if wn_p and not is_adverb and not wn.synsets(cand, pos=wn_p):
            continue
        filtered.append(cand)

    if prefer_ly:
        ly = [c for c in filtered if c.endswith("ly")]
        rest = [c for c in filtered if not c.endswith("ly")]
        filtered = ly + rest

    return filtered[:top_k]


def _flagged_positions(tokens: list[str], tags: list[tuple], profile: DifficultyProfile) -> list[dict]:
    """Which substitutable, unprotected positions does the profile flag,
    and why (declared word / global sound onset) — the 'tag' stage."""
    phrase_protected = sem.protected_positions(tokens)
    sound_patterns = profile.sound_values()
    flagged = []
    for i, (word, tag) in enumerate(tags):
        lower = word.lower()
        if not re.match(r"[a-z]", lower):
            continue
        if tag not in _SUBSTITUTABLE or lower in _STOP:
            continue
        if i in phrase_protected:
            continue
        word_entry = profile.find_word(lower)
        sound_hit = ph.matches_any(word, sound_patterns)
        if word_entry is not None or sound_hit:
            flagged.append({
                "position": i, "word": word, "tag": tag,
                "word_entry": word_entry, "sound_hit": sound_hit,
            })
    return flagged


def _substitutable_content_word_count(tags: list[tuple], phrase_protected: set) -> int:
    count = 0
    for i, (word, tag) in enumerate(tags):
        if not re.match(r"[a-z]", word.lower()):
            continue
        if tag not in _SUBSTITUTABLE or word.lower() in _STOP:
            continue
        if i in phrase_protected:
            continue
        count += 1
    return max(count, 1)


def _try_substitution(
    sentence: str, tokens: list[str], tags: list[tuple], flagged: list[dict],
    profile: DifficultyProfile, engine: "engine_module.SynonymEngine", settings: ReformulateSettings,
) -> tuple[list[str] | None, list[dict], list[dict]]:
    """All-or-nothing: every flagged position must find a candidate that
    clears every gate, or this returns (None, ..., ...) so the caller
    escalates the whole sentence instead of shipping a patchwork (§24.D)."""
    new_tokens = list(tokens)
    changes: list[dict] = []
    skipped: list[dict] = []
    min_semantic = settings.sbert_threshold if settings.sbert_threshold is not None else sem.MIN_SEMANTIC

    for item in flagged:
        i, word, tag = item["position"], item["word"], item["tag"]
        base = lemmatize(word, tag)
        wn_p = _wn_pos(tag)
        raw_cands = _raw_candidates(engine, base, tag, word, settings.top_k)
        if not raw_cands:
            skipped.append({"word": word, "position": i, "reason": "no candidates found"})
            return None, changes, skipped

        inflected_map = {lemma: _preserve_case(word, inflect(lemma, tag)) for lemma in raw_cands}
        scored = sem.rank_candidates_contextually(
            original_sentence=sentence, word_to_replace=word, token_index=i,
            tokens=list(new_tokens), candidates=raw_cands, inflected_forms=inflected_map,
            min_semantic=min_semantic,
        )

        usable = None
        for s in scored:
            if not s["accepted"]:
                continue
            if sem.is_known_antonym(base, s["lemma"], wn_p):
                s["antonym_rejected"] = True
                continue
            if ph.matches_any(s["inflected"], profile.sound_values()):
                continue
            usable = s
            break

        if usable is None:
            skipped.append({"word": word, "position": i, "reason": "no candidate passed verification"})
            return None, changes, skipped

        new_tokens[i] = usable["inflected"]
        changes.append({
            "sentence_index": None,  # filled in by caller
            "position": i,
            "span_text": word,
            "original": word,
            "replacement": usable["inflected"],
            "source": "substitution",
            "triggered_by": _trigger_reasons(item),
            "verification": {
                "antonym_check": "pass",
                "sbert_sim": usable["semantic_sim"],
                "nli": "not_run",
                "phoneme_ok": True,
                "difficulty_before": round(ph.word_difficulty(word), 4),
                "difficulty_after": round(ph.word_difficulty(usable["inflected"]), 4),
            },
        })

    return new_tokens, changes, skipped


def _trigger_reasons(flagged_item: dict) -> list[str]:
    reasons = []
    if flagged_item["word_entry"] is not None:
        reasons.append("declared_word")
        if flagged_item["word_entry"].problem_phones:
            reasons.append("word_specific_pattern")
    if flagged_item["sound_hit"]:
        reasons.append("global_sound")
    return reasons


def _try_escalation(
    sentence: str, flagged: list[dict], profile: DifficultyProfile, settings: ReformulateSettings,
) -> tuple[str | None, dict | None]:
    """Generate-then-verify restructuring (§24.E) — T5 is never told about
    phonemes; every candidate is re-checked with the same phoneme veto and
    SBERT threshold used for substitution, plus a sentence-level negation
    check standing in for the single-word antonym check (which doesn't
    apply to a freely generated paraphrase).

    The word-block set is the *substitutable* words this sentence actually
    flagged (`flagged`), not the full declared-word list: a declared-difficult
    word that isn't substitutable in this position (a numeral, a proper noun
    — anything _SUBSTITUTABLE excludes) is equally unfixable by restructuring,
    so blocking on it would only ever reject every candidate T5 produces."""
    min_semantic = settings.sbert_threshold if settings.sbert_threshold is not None else sem.MIN_SEMANTIC
    blocked = {item["word"].lower() for item in flagged}
    candidates = rephrase.generate_candidates(sentence, k=settings.t5_candidates, blocked_words=blocked)

    best = None
    for cand in candidates:
        if cand.strip().lower() == sentence.strip().lower():
            continue  # T5 unavailable or returned the input unchanged — not a real alternative
        sim = sem.semantic_similarity(cand, sentence)
        # Matches semantic.rank_candidates_contextually's own documented
        # fallback: SBERT unavailable -> don't gate on it, don't rank on it.
        if sim is not None and sim < min_semantic:
            continue
        if not sem.negation_consistent(sentence, cand):
            continue
        content_words = re.findall(r"[A-Za-z][A-Za-z'-]*", cand)
        if any(ph.matches_any(w, profile.sound_values()) or w.lower() in blocked for w in content_words):
            continue
        rank_score = sim if sim is not None else -1.0
        if best is None or (rank_score > best["rank_score"]):
            best = {"text": cand, "sim": sim, "rank_score": rank_score}

    if best is None:
        return None, None

    return best["text"], {
        "sentence_index": None,
        "position": None,
        "span_text": sentence,
        "original": sentence,
        "replacement": best["text"],
        "source": "restructuring",
        "triggered_by": ["multiple_difficulties_or_no_valid_substitution"],
        "verification": {
            "antonym_check": "n/a_sentence_level",
            "sbert_sim": round(best["sim"], 4) if best["sim"] is not None else None,
            "nli": "not_run",
            "phoneme_ok": True,
            "difficulty_before": round(ph.sentence_difficulty(re.findall(r"[A-Za-z]+", sentence)), 4),
            "difficulty_after": round(ph.sentence_difficulty(re.findall(r"[A-Za-z]+", best["text"])), 4),
        },
    }


def _flagged_word_count(text: str, profile: DifficultyProfile) -> int:
    """The 'recovery rate' check (§2.2/§24) — how many content words in
    *text* the profile would flag right now. Used both to decide whether a
    sentence needs attention and, re-run on the final output, as the
    reformulation-effectiveness metric."""
    try:
        tokens = word_tokenize(text)
    except Exception:
        tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    tags = pos_tag(tokens)
    return len(_flagged_positions(tokens, tags, profile))


def reformulate(text: str, profile: DifficultyProfile, settings: ReformulateSettings | None = None) -> dict:
    """The engine's public entry point — §25's contract."""
    settings = settings or ReformulateSettings()
    sem.load_sbert()  # idempotent; no-op if already loaded or already failed once
    engine = engine_module.SynonymEngine()

    sentences = split_sentences(text)
    rebuilt: list[str] = []
    all_changes: list[dict] = []
    all_skipped: list[dict] = []
    any_flagged = False

    for sid, sentence in enumerate(sentences):
        try:
            tokens = word_tokenize(sentence)
        except Exception:
            tokens = re.findall(r"[A-Za-z][A-Za-z'-]*|[.,!?;:]", sentence)
        tags = pos_tag(tokens)
        phrase_protected = sem.protected_positions(tokens)
        flagged = _flagged_positions(tokens, tags, profile)

        if not flagged:
            rebuilt.append(sentence)
            continue

        any_flagged = True
        content_count = _substitutable_content_word_count(tags, phrase_protected)
        flagged_fraction = len(flagged) / content_count
        pre_escalate = (
            len(flagged) > settings.escalation_word_count
            or flagged_fraction > settings.degenerate_fraction
        )

        new_tokens, sentence_changes, sentence_skipped = (None, [], [])
        if not pre_escalate:
            new_tokens, sentence_changes, sentence_skipped = _try_substitution(
                sentence, tokens, tags, flagged, profile, engine, settings
            )

        if new_tokens is not None:
            rebuilt_sentence = _detokenize(new_tokens)
            for c in sentence_changes:
                c["sentence_index"] = sid
            all_changes.extend(sentence_changes)
            rebuilt.append(rebuilt_sentence)
            continue

        # Escalate: either pre-triggered, or substitution failed for some position.
        restructured_text, change = _try_escalation(sentence, flagged, profile, settings)
        if restructured_text is not None:
            change["sentence_index"] = sid
            all_changes.append(change)
            rebuilt.append(restructured_text)
        else:
            reason = "profile too restrictive for this sentence" if flagged_fraction > settings.degenerate_fraction \
                else "could not safely reformulate this sentence"
            all_skipped.append({"word": sentence, "position": None, "reason": reason})
            rebuilt.append(sentence)  # leave unchanged — never ship a bad guess

    reformulated_text = " ".join(rebuilt)

    if not any_flagged:
        status = "no_change_needed"
    elif all_changes:
        status = "reformulated"
    else:
        status = "could_not_safely_reformulate"

    flagged_before = _flagged_word_count(text, profile)
    flagged_after = _flagged_word_count(reformulated_text, profile)
    overall_sim = sem.semantic_similarity(text, reformulated_text)
    final_ok = (flagged_after < flagged_before) or (flagged_before == 0)
    if overall_sim is not None:
        final_ok = final_ok and overall_sim >= (settings.sbert_threshold or sem.MIN_SEMANTIC) - 0.05

    metrics = {
        "meaning_preservation": round(overall_sim, 4) if overall_sim is not None else None,
        "flagged_words_before": flagged_before,
        "flagged_words_after": flagged_after,
        "difficulty_reduction_pct": (
            round(100.0 * (flagged_before - flagged_after) / flagged_before, 2) if flagged_before else 0.0
        ),
        "naturalness_edit_ratio": nat.edit_ratio(text, reformulated_text),
        "substitution_rate": round(
            nat.changed_word_count(text, reformulated_text) / max(1, len(nat._word_tokens(text))), 4
        ),
    }

    return {
        "original_text": text,
        "reformulated_text": reformulated_text,
        "status": status,
        "changes": all_changes,
        "skipped": all_skipped,
        "metrics": metrics,
        "final_verification": {
            "passed": bool(final_ok),
            "details": {
                "flagged_before": flagged_before,
                "flagged_after": flagged_after,
                "sbert_sim": round(overall_sim, 4) if overall_sim is not None else None,
            },
        },
    }
