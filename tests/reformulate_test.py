"""
tests/reformulate_test.py — tests for the consolidated reformulation engine
(reformulate.py, Architecture D', REFORMULATION_RESEARCH.md SS24-31).

Covers: the no-flag / substitution / restructuring-escalation / cannot-
safely-reformulate status states, the all-or-nothing per-sentence rule
(SS24.D), the antonym guard, the phoneme veto surviving into the final
text, word-specific vs. global sound-pattern flagging, multi-sentence
pass-through, and metrics sanity.

    DISABLE_DATAMUSE=1 python tests/reformulate_test.py
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

os.environ["DISABLE_DATAMUSE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import reformulate as rf
import semantic as sem
from difficulty_profile import DifficultyProfile

sem.load_sbert()  # best-effort; tests must pass whether or not this succeeds


def _profile(name: str) -> DifficultyProfile:
    return DifficultyProfile(profile_name=f"__test_{name}__")


class NoChangeNeededTest(unittest.TestCase):
    def test_empty_profile_leaves_text_untouched(self):
        result = rf.reformulate("The sky is blue today.", _profile("nochange"))
        self.assertEqual(result["status"], "no_change_needed")
        self.assertEqual(result["reformulated_text"], "The sky is blue today.")
        self.assertEqual(result["changes"], [])
        self.assertEqual(result["skipped"], [])


class SubstitutionTest(unittest.TestCase):
    def test_global_sound_flag_produces_substitution(self):
        profile = _profile("sub_sound")
        profile.add_sound("str", source="user_typed")
        result = rf.reformulate(
            "I need to review three reports before the strong deadline.", profile
        )
        self.assertEqual(result["status"], "reformulated")
        self.assertEqual(len(result["changes"]), 1)
        change = result["changes"][0]
        self.assertEqual(change["source"], "substitution")
        self.assertIn("global_sound", change["triggered_by"])
        self.assertNotIn("str", change["replacement"].lower())

    def test_antonym_never_chosen(self):
        profile = _profile("antonym_guard")
        profile.add_word("happy", source="user_typed")
        result = rf.reformulate("She felt happy about the news.", profile)
        self.assertNotIn("sad", result["reformulated_text"].lower())
        self.assertNotIn("unhappy", result["reformulated_text"].lower())

    def test_word_specific_pattern_does_not_flag_other_words_with_same_sound(self):
        profile = _profile("word_specific")
        profile.add_word("three", source="user_typed")
        profile.set_word_pattern("three", phones=("TH", "R"))
        # "through" also has TH+R but was never declared difficult, and the
        # global sound list is untouched -> it must not be flagged.
        result = rf.reformulate("We drove through the tunnel.", profile)
        self.assertEqual(result["status"], "no_change_needed")


class EscalationTest(unittest.TestCase):
    def test_count_threshold_triggers_restructuring(self):
        profile = _profile("escalate_count")
        profile.add_word("three", source="user_typed")
        profile.add_word("strong", source="user_typed")
        profile.add_word("review", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=1)
        result = rf.reformulate(
            "I need to review three reports before the strong deadline.", profile, settings
        )
        self.assertEqual(result["status"], "reformulated")
        self.assertEqual(result["changes"][0]["source"], "restructuring")

    def test_all_or_nothing_falls_back_to_restructuring(self):
        """If ANY flagged position in a sentence has no usable candidate,
        the whole sentence escalates rather than shipping a partial
        substitution (SS24.D) — verified by forcing candidate generation to
        fail for one specific flagged word."""
        profile = _profile("all_or_nothing")
        profile.add_word("review", source="user_typed")
        profile.add_word("strong", source="user_typed")

        real = rf._raw_candidates

        def flaky(engine, lemma, pos_tag_str, original_word, top_k):
            if lemma == "review":
                return []
            return real(engine, lemma, pos_tag_str, original_word, top_k)

        with mock.patch.object(rf, "_raw_candidates", side_effect=flaky):
            result = rf.reformulate(
                "I need to review the strong deadline.", profile
            )
        # Either a valid restructuring was found, or the engine correctly
        # reports it could not safely reformulate -- either way, there must
        # be no changes tagged "substitution" (no partial patchwork).
        for change in result["changes"]:
            self.assertNotEqual(change["source"], "substitution")

    def test_no_usable_restructuring_leaves_text_unchanged(self):
        profile = _profile("cannot_reformulate")
        profile.add_word("strong", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=0)
        original = "The strong wind blew."
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[original]):
            result = rf.reformulate(original, profile, settings)
        self.assertEqual(result["status"], "could_not_safely_reformulate")
        self.assertEqual(result["reformulated_text"], original)
        self.assertEqual(result["changes"], [])
        self.assertEqual(len(result["skipped"]), 1)


class MultiSentenceTest(unittest.TestCase):
    def test_unflagged_sentences_pass_through_untouched(self):
        profile = _profile("multi_sentence")
        profile.add_sound("str", source="user_typed")
        text = "The cat sat on the mat. The strong wind blew hard."
        result = rf.reformulate(text, profile)
        sentences = result["reformulated_text"].split(". ")
        self.assertTrue(sentences[0].startswith("The cat sat on the mat"))
        self.assertNotIn("strong", result["reformulated_text"].lower())


class MetricsTest(unittest.TestCase):
    def test_metrics_shape_and_bounds(self):
        profile = _profile("metrics")
        profile.add_sound("str", source="user_typed")
        result = rf.reformulate(
            "I need to review three reports before the strong deadline.", profile
        )
        m = result["metrics"]
        if m["meaning_preservation"] is not None:
            self.assertGreaterEqual(m["meaning_preservation"], 0.0)
            self.assertLessEqual(m["meaning_preservation"], 1.0)
        self.assertGreaterEqual(m["naturalness_edit_ratio"], 0.0)
        self.assertLessEqual(m["naturalness_edit_ratio"], 1.0)
        self.assertGreaterEqual(m["substitution_rate"], 0.0)
        self.assertEqual(m["flagged_words_after"], 0)

    def test_final_verification_never_reports_pass_on_no_improvement(self):
        profile = _profile("final_verify")
        profile.add_word("strong", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=0)
        original = "The strong wind blew."
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[original]):
            result = rf.reformulate(original, profile, settings)
        self.assertFalse(result["final_verification"]["passed"])


class SentenceSplitTest(unittest.TestCase):
    def test_abbreviations_do_not_split(self):
        parts = rf.split_sentences("I met Dr. Smith yesterday. It went well.")
        self.assertEqual(len(parts), 2)
        self.assertTrue(parts[0].startswith("I met Dr. Smith"))

    def test_empty_text(self):
        self.assertEqual(rf.split_sentences(""), [])


if __name__ == "__main__":
    unittest.main()
