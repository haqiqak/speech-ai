"""
tests/meaningbert_test.py — coverage for semantic.py's MeaningBERT signal
(R24/R27), which had none: the model executes live inside every real
reformulate() call (test_metrics_shape_and_bounds in reformulate_test.py
calls it unmocked) but nothing previously asserted it works, is present in
the reported metrics, degrades gracefully, or actually behaves the way
R24's validation (VALIDATION.md SS15) found it to.

Loads the real MeaningBERT model (109.5M params, davebulaval/MeaningBERT) —
not mocked, since the point is to prove the actual signal works, the same
way rephrase_test.py exercises the real T5 model rather than mocking it.
Slower than the rest of the suite for that reason; kept in its own file so
tests/semantic_test.py's "no model loading required" guarantee stays true.

    python tests/meaningbert_test.py
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic as sem
import reformulate as rf
from difficulty_profile import DifficultyProfile


def _profile(name: str) -> DifficultyProfile:
    return DifficultyProfile(profile_name=f"__test_{name}__")


class MeaningBERTLoadTest(unittest.TestCase):
    def test_load_meaningbert_succeeds_in_this_environment(self):
        # Not a hard requirement of the signal (it degrades gracefully if
        # unavailable — see DegradationTest below), but this environment
        # has the model cached, so a silent load failure here would be a
        # real regression worth catching rather than passing by accident.
        ok = sem.load_meaningbert()
        self.assertTrue(ok, sem.meaningbert_status()[1])

    def test_status_reports_loaded(self):
        sem.load_meaningbert()
        ok, message = sem.meaningbert_status()
        self.assertTrue(ok)
        self.assertIn("loaded successfully", message)


class MeaningBERTScoreTest(unittest.TestCase):
    def test_identical_sentences_score_high(self):
        score = sem.meaningbert_score(
            "The team reached a strong decision after the meeting.",
            "The team reached a strong decision after the meeting.",
        )
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 90.0)

    def test_score_is_within_native_0_100_range(self):
        score = sem.meaningbert_score(
            "Good morning, did you sleep well?",
            "Good morning, did you rest well?",
        )
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_known_disagreement_case_scores_low(self):
        # VALIDATION.md SS15.2 — R24's own recorded finding: this exact pair
        # is the clearest case where MeaningBERT catches a causative-
        # construction break SBERT rates as near-perfect (0.968). MeaningBERT
        # scored it 48.0, more than 20 points below every control pair's
        # 81.5-94.5 range. Re-asserted here as a regression guard on that
        # specific, already-validated finding — not a new claim.
        score = sem.meaningbert_score(
            "The kids are driving me crazy today.",
            "The kids are going me crazy today.",
        )
        self.assertIsNotNone(score)
        self.assertLess(score, 65.0)


class MeaningBERTDegradationTest(unittest.TestCase):
    """Mirrors semantic.py's existing SBERT-unavailable fallback pattern —
    confirm meaningbert_score() degrades the same way (returns None, does
    not raise) rather than assuming it does because SBERT's does."""

    def test_returns_none_when_model_unavailable(self):
        with mock.patch.object(sem, "_meaningbert_ok", False), \
             mock.patch.object(sem, "load_meaningbert", return_value=False):
            score = sem.meaningbert_score("Hello there.", "Hi there.")
        self.assertIsNone(score)


class MeaningBERTReformulateIntegrationTest(unittest.TestCase):
    """The gap the audit found: reformulate() already calls
    meaningbert_score() unmocked in every real run, but nothing asserted
    the result actually reaches the returned metrics dict correctly."""

    def test_metric_present_and_in_range_when_model_available(self):
        profile = _profile("meaningbert_integration")
        profile.add_sound("s", source="user_typed")
        result = rf.reformulate("Good morning, did you sleep well?", profile)
        mb = result["metrics"]["meaning_preservation_meaningbert"]
        self.assertIsNotNone(mb)
        self.assertGreaterEqual(mb, 0.0)
        self.assertLessEqual(mb, 100.0)

    def test_metric_is_none_not_missing_when_model_unavailable(self):
        profile = _profile("meaningbert_degraded")
        profile.add_sound("s", source="user_typed")
        with mock.patch.object(sem, "meaningbert_score", return_value=None):
            result = rf.reformulate("Good morning, did you sleep well?", profile)
        self.assertIn("meaning_preservation_meaningbert", result["metrics"])
        self.assertIsNone(result["metrics"]["meaning_preservation_meaningbert"])

    def test_meaningbert_never_gates_final_verification(self):
        # Practice.md SS10 / the R27 wiring comment in reformulate.py: a low
        # MeaningBERT score must never by itself flip final_verification's
        # pass/fail -- only overall_sim (SBERT) and flagged-word counts do.
        # Force MeaningBERT to the lowest possible score and confirm a
        # clean, gate-passing substitution still reports passed=True.
        profile = _profile("meaningbert_no_gate")
        profile.add_sound("s", source="user_typed")
        with mock.patch.object(sem, "meaningbert_score", return_value=0.0):
            result = rf.reformulate("Good morning, did you sleep well?", profile)
        self.assertTrue(result["final_verification"]["passed"])
        self.assertEqual(result["metrics"]["meaning_preservation_meaningbert"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
