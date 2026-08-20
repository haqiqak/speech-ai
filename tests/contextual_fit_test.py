"""
tests/contextual_fit_test.py — coverage for semantic.py's contextual-fit
signal (R33-R36, wired in R36/Option A as a reported-only diagnostic).

Loads the real DistilBERT model (66M params, distilbert-base-uncased) —
not mocked, same rationale as meaningbert_test.py/rephrase_test.py: the
point is to prove the actual signal works. Kept in its own file so
tests/semantic_test.py's "no model loading required" guarantee stays true.

    python tests/contextual_fit_test.py
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


class ContextualFitLoadTest(unittest.TestCase):
    def test_load_succeeds_in_this_environment(self):
        ok = sem.load_contextual_fit_model()
        self.assertTrue(ok, sem.contextual_fit_status()[1])

    def test_status_reports_loaded(self):
        sem.load_contextual_fit_model()
        ok, message = sem.contextual_fit_status()
        self.assertTrue(ok)
        self.assertIn("loaded successfully", message)


class ContextualFitScoreTest(unittest.TestCase):
    def test_known_bad_case_scores_low(self):
        # VALIDATION.md SS26/29 (R33/R36) -- one of the core known-bad
        # cases, reproduced as a regression guard.
        score = sem.contextual_fit_score(
            "We need to purchase supplies before we starting the project.",
            "starting",
        )
        self.assertIsNotNone(score)
        self.assertLess(score, 0.01)

    def test_known_good_case_scores_higher(self):
        score = sem.contextual_fit_score(
            "We need to purchase supplies before we start the project.",
            "start",
        )
        self.assertIsNotNone(score)
        self.assertGreater(score, 0.1)

    def test_score_is_within_0_1_range(self):
        score = sem.contextual_fit_score(
            "Good morning, did you rest well?", "rest",
        )
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_register_mismatch_blind_spot_is_real_not_a_regression(self):
        # VALIDATION.md SS28/29 (R35/R36) -- the known, disclosed blind
        # spot: "belated" scores HIGH despite a human rating it Unnatural.
        # Asserted here as a documented characteristic, not a bug -- if
        # this ever flips low, that's a model/behavior change worth
        # noticing, not a silent drift.
        score = sem.contextual_fit_score(
            "The bus was belated again this morning.", "belated",
        )
        self.assertIsNotNone(score)
        self.assertGreater(score, 0.1)

    def test_word_not_in_sentence_returns_none(self):
        score = sem.contextual_fit_score("The bus was late again.", "asleep")
        self.assertIsNone(score)


class ContextualFitDegradationTest(unittest.TestCase):
    """Mirrors semantic.py's existing SBERT/MeaningBERT-unavailable
    fallback pattern."""

    def test_returns_none_when_model_unavailable(self):
        with mock.patch.object(sem, "_contextual_fit_ok", False), \
             mock.patch.object(sem, "load_contextual_fit_model", return_value=False):
            score = sem.contextual_fit_score("Hello there.", "there")
        self.assertIsNone(score)


class ContextualFitReformulateIntegrationTest(unittest.TestCase):
    """reformulate() calls contextual_fit_score() unmocked for every
    substitution-sourced change -- confirm it actually reaches the
    change's verification dict, degrades cleanly, and never gates
    anything (Option A: reported-only, per explicit scope)."""

    def test_field_present_and_in_range_for_substitution_changes(self):
        profile = _profile("contextual_fit_integration")
        profile.add_sound("s", source="user_typed")
        result = rf.reformulate("Good morning, did you sleep well?", profile)
        subs = [c for c in result["changes"] if c["source"] == "substitution"]
        self.assertTrue(subs)
        for c in subs:
            fit = c["verification"]["contextual_fit"]
            self.assertIsNotNone(fit)
            self.assertGreaterEqual(fit, 0.0)
            self.assertLessEqual(fit, 1.0)

    def test_field_is_none_not_missing_when_model_unavailable(self):
        profile = _profile("contextual_fit_degraded")
        profile.add_sound("s", source="user_typed")
        with mock.patch.object(sem, "contextual_fit_score", return_value=None):
            result = rf.reformulate("Good morning, did you sleep well?", profile)
        subs = [c for c in result["changes"] if c["source"] == "substitution"]
        self.assertTrue(subs)
        for c in subs:
            self.assertIn("contextual_fit", c["verification"])
            self.assertIsNone(c["verification"]["contextual_fit"])

    def test_never_gates_final_verification_or_status(self):
        # Force the lowest possible score and confirm a clean, gate-
        # passing substitution still ships and reports passed=True --
        # Option A is reported-only; this is the actual behavioral
        # contract, not just documentation.
        profile = _profile("contextual_fit_no_gate")
        profile.add_sound("s", source="user_typed")
        with mock.patch.object(sem, "contextual_fit_score", return_value=0.0):
            result = rf.reformulate("Good morning, did you sleep well?", profile)
        self.assertEqual(result["status"], "reformulated")
        self.assertTrue(result["final_verification"]["passed"])

    def test_not_computed_for_restructuring_changes(self):
        # Scope discipline: validated for single-word substitutions only
        # (R33-R36) -- restructuring/phrase output should not silently
        # pick up an unvalidated score.
        profile = _profile("contextual_fit_restructuring")
        profile.add_word("three", source="user_typed")
        profile.add_word("strong", source="user_typed")
        profile.add_word("review", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=1)
        result = rf.reformulate(
            "I need to review three reports before the strong deadline.", profile, settings
        )
        restructured = [c for c in result["changes"] if c["source"] == "restructuring"]
        if restructured:
            self.assertNotIn("contextual_fit", restructured[0]["verification"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
