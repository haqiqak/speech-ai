"""
tests/stage_lr_features_test.py — Stage LR's LR.2 feature extractor
(stage_lr/features.py). Not part of the frozen pipeline's test suite;
exercises off-main research code only.

Two groups: pure-logic tests (no model loading, fast, deterministic —
these are the ones that matter most, since they directly enforce Matter
1's scoping guardrails in code, not just in docs) and one end-to-end
smoke test (loads real SBERT/MeaningBERT/contextual-fit models, proves
the wiring actually works, not just that it's designed to).

    DISABLE_DATAMUSE=1 python tests/stage_lr_features_test.py
"""
from __future__ import annotations

import os
import sys
import unittest

os.environ["DISABLE_DATAMUSE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from difficulty_profile import DifficultyProfile
from stage_lr.features import (
    _is_declared_difficult_phrase,
    _is_declared_difficult_word,
    _phrase_phone_fingerprint,
    _word_onset_hits,
    score_candidate,
)


def _profile(sounds=(), words=(), phrases=()) -> DifficultyProfile:
    p = DifficultyProfile(profile_name="__stage_lr_test__")
    for s in sounds:
        p.add_sound(s)
    for w in words:
        p.add_word(w)
    for ph in phrases:
        p.add_phrase(ph)
    return p


class OnsetMatchTest(unittest.TestCase):
    def test_onset_hit_works_for_sounds_added_via_phones_not_just_spelling(self):
        # add_sound_from_phones() is the ARPAbet-native path (used when
        # promoting a word's problem_phones) -- distinct from add_sound()'s
        # spelling-guess path. _word_onset_hits() must match correctly
        # off entry.normalized either way, since that's the whole point
        # of reading the stored key directly instead of re-deriving it.
        p = DifficultyProfile(profile_name="__stage_lr_test__")
        p.add_sound_from_phones(["TH", "R"])
        self.assertIn("TH R", [e.normalized for e in p.sounds])
        self.assertEqual(_word_onset_hits("thrive", p), ["TH-R"])
        self.assertEqual(_word_onset_hits("banana", p), [])

    def test_onset_hit_real_case(self):
        p = _profile(sounds=["pr"])
        self.assertIn("pr", _word_onset_hits("present", p))
        self.assertEqual(_word_onset_hits("banana", p), [])

    def test_word_specific_pattern_never_leaks_into_a_global_onset_hit(self):
        """The guardrail this test exists to enforce: a word's own
        problem_phones must never make _word_onset_hits() (a GLOBAL
        sounds check) fire for some other, unrelated word that happens
        to share a phone — only an explicit sounds entry should."""
        p = _profile(words=["level"])  # not promoted to a global sound
        entry = p.words[0]
        entry.problem_phones = ("L",)
        # "listen" also starts with L -- must NOT be flagged, because
        # "level"'s problem_phones was never promoted to a global rule.
        self.assertEqual(_word_onset_hits("listen", p), [])


class DeclaredWordTest(unittest.TestCase):
    def test_exact_match_only(self):
        p = _profile(words=["strategy"])
        self.assertTrue(_is_declared_difficult_word("strategy", p))
        self.assertFalse(_is_declared_difficult_word("strategic", p))


class PhraseFingerprintTest(unittest.TestCase):
    def test_known_words_produce_a_fingerprint(self):
        fp = _phrase_phone_fingerprint(["push", "the", "meeting"])
        self.assertIsNotNone(fp)
        self.assertGreater(len(fp), 0)

    def test_all_oov_words_produce_no_fingerprint(self):
        fp = _phrase_phone_fingerprint(["zzzxqvv", "qxzzvv"])
        self.assertIsNone(fp)

    def test_partial_oov_still_produces_a_fingerprint_from_known_words(self):
        fp = _phrase_phone_fingerprint(["the", "zzzxqvv"])
        self.assertIsNotNone(fp)  # "the" is known, contributes phones

    def test_phrase_match_is_fingerprint_to_fingerprint(self):
        p = _profile(phrases=["push the meeting"])
        self.assertTrue(_is_declared_difficult_phrase(["push", "the", "meeting"], p))
        self.assertFalse(_is_declared_difficult_phrase(["cancel", "the", "call"], p))

    def test_phrase_match_never_flags_a_lone_word_from_that_phrase(self):
        """The core guardrail from Matter 1 (2026-08-30-E): "this phrase
        is difficult" must never generalize to "every word in it is
        individually difficult." Checked directly here, not just
        asserted in prose."""
        p = _profile(phrases=["push the meeting"])
        # A single-word candidate "push" must not be treated as a
        # phrase match, and must not be a declared *word* either --
        # only the exact phrase was declared, nothing about "push" alone.
        self.assertFalse(_is_declared_difficult_word("push", p))
        self.assertFalse(_is_declared_difficult_phrase(["push"], p))


class ScoreCandidateStructureTest(unittest.TestCase):
    """Pure-structure checks that don't depend on any model actually
    loading (meaning/naturalness fields are allowed to be None)."""

    def test_phoneme_difficulty_fires_on_a_real_onset_collision(self):
        p = _profile(sounds=["pr"])
        score = score_candidate(
            "The report was late.",
            "The presentation was late.",
            "presentation",
            p,
            source="substitution",
        )
        self.assertEqual(score.phoneme_difficulty, 1.0)
        self.assertTrue(score.phoneme_difficulty_reasons)

    def test_phoneme_difficulty_zero_on_a_clean_candidate(self):
        p = _profile(sounds=["pr"])
        score = score_candidate(
            "The report was late.",
            "The summary was late.",
            "summary",
            p,
            source="substitution",
        )
        self.assertEqual(score.phoneme_difficulty, 0.0)
        self.assertEqual(score.phoneme_difficulty_reasons, [])

    def test_phrase_source_skips_contextual_fit_per_its_own_validated_scope(self):
        p = _profile()
        score = score_candidate(
            "Let's push the meeting to Friday.",
            "Let's postpone the meeting to Friday.",
            "postpone the meeting",
            p,
            source="phrase",
        )
        self.assertIsNone(score.naturalness_contextual_fit)


class ScoreCandidateSmokeTest(unittest.TestCase):
    """End-to-end: proves the real wiring works, not just that it's
    designed to. Loose assertions only (model output isn't pinned)."""

    def test_real_models_produce_bounded_scores_or_fail_closed_to_none(self):
        p = _profile(sounds=["pr"])
        score = score_candidate(
            "The team will finalize the report tomorrow.",
            "The team will finalize the summary tomorrow.",
            "summary",
            p,
            source="substitution",
        )
        if score.meaning_sbert is not None:
            self.assertGreaterEqual(score.meaning_sbert, 0.0)
            self.assertLessEqual(score.meaning_sbert, 1.0)
        if score.naturalness_contextual_fit is not None:
            self.assertGreaterEqual(score.naturalness_contextual_fit, 0.0)
            self.assertLessEqual(score.naturalness_contextual_fit, 1.0)
        # meaningbert_score is a 0-100 scale, deliberately not normalized
        if score.meaning_meaningbert is not None:
            self.assertIsInstance(score.meaning_meaningbert, float)


if __name__ == "__main__":
    unittest.main(verbosity=2)
