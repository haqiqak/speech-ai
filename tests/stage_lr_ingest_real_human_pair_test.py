"""
tests/stage_lr_ingest_real_human_pair_test.py — stage_lr/ingest_real_human_pair.py,
data path (b)'s ingestion mechanism (DECISION_LOG.md 2026-08-30-Q). No
real human data has been collected yet; these tests exercise the
mechanism with synthetic stand-in verdicts to prove it works and, most
importantly, that it CANNOT be used to log a human verdict without a
matching same-session Claude verdict.

    python tests/stage_lr_ingest_real_human_pair_test.py
"""
from __future__ import annotations

import inspect
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stage_lr.ingest_real_human_pair as ihp

TEST_PATH = Path(__file__).resolve().parent.parent / "stage_lr" / "data" / "real_human_pairs.json"


class RequiredArgumentsTest(unittest.TestCase):
    """The core invariant: both verdicts are required, no defaults."""

    def test_human_preferred_and_claude_preferred_have_no_default(self):
        sig = inspect.signature(ihp.record_real_human_pair)
        self.assertEqual(sig.parameters["human_preferred"].default, inspect.Parameter.empty)
        self.assertEqual(sig.parameters["claude_preferred"].default, inspect.Parameter.empty)
        self.assertEqual(sig.parameters["claude_reason"].default, inspect.Parameter.empty)

    def test_calling_without_claude_preferred_raises(self):
        with self.assertRaises(TypeError):
            ihp.record_real_human_pair(
                participant_label="test", original_sentence="x",
                difficulty_profile={}, flagged_word="w",
                candidate_A="a", candidate_B="b",
                human_preferred="A",
                # claude_preferred and claude_reason deliberately omitted
            )

    def test_calling_without_human_preferred_raises(self):
        with self.assertRaises(TypeError):
            ihp.record_real_human_pair(
                participant_label="test", original_sentence="x",
                difficulty_profile={}, flagged_word="w",
                candidate_A="a", candidate_B="b",
                claude_preferred="A", claude_reason="because",
                # human_preferred deliberately omitted
            )

    def test_human_reason_is_optional_claude_reason_is_not(self):
        """The friend-facing ask deliberately doesn't require an
        explanation (LEARNED_REFORMULATION_RESEARCH.md's "concrete,
        minimal ask") -- but Claude is always asked for one."""
        sig = inspect.signature(ihp.record_real_human_pair)
        self.assertEqual(sig.parameters["human_reason"].default, None)
        self.assertEqual(sig.parameters["claude_reason"].default, inspect.Parameter.empty)


class RecordingTest(unittest.TestCase):
    def setUp(self):
        self._backup = TEST_PATH.read_text(encoding="utf-8") if TEST_PATH.exists() else None

    def tearDown(self):
        if self._backup is not None:
            TEST_PATH.write_text(self._backup, encoding="utf-8")
        elif TEST_PATH.exists():
            TEST_PATH.unlink()

    def test_record_carries_both_verdicts_and_source_tag(self):
        record = ihp.record_real_human_pair(
            participant_label="test_friend",
            original_sentence="The report was late.",
            difficulty_profile={"sounds": ["r"], "words": [], "phrases": []},
            flagged_word="report",
            candidate_A="summary", candidate_B="memo",
            human_preferred="A",
            claude_preferred="A",
            claude_reason="Summary is closer in register.",
            human_reason=None,
        )
        self.assertEqual(record["source"], "real_human")
        self.assertEqual(record["human_preferred"], "A")
        self.assertEqual(record["claude_preferred"], "A")
        self.assertTrue(record["agree"])
        self.assertIsNotNone(record["judged_together_at"])

    def test_disagreement_recorded_correctly(self):
        record = ihp.record_real_human_pair(
            participant_label="test_friend",
            original_sentence="The report was late.",
            difficulty_profile={"sounds": ["r"], "words": [], "phrases": []},
            flagged_word="report",
            candidate_A="summary", candidate_B="memo",
            human_preferred="A", claude_preferred="B",
            claude_reason="Memo fits the context better.",
        )
        self.assertFalse(record["agree"])

    def test_appends_not_overwrites(self):
        ihp.record_real_human_pair(
            participant_label="p1", original_sentence="a", difficulty_profile={},
            flagged_word="w", candidate_A="x", candidate_B="y",
            human_preferred="A", claude_preferred="A", claude_reason="r",
        )
        ihp.record_real_human_pair(
            participant_label="p1", original_sentence="b", difficulty_profile={},
            flagged_word="w", candidate_A="x", candidate_B="y",
            human_preferred="B", claude_preferred="tie", claude_reason="r2",
        )
        data = json.loads(TEST_PATH.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["pairs"]), 2)

    def test_stored_separately_from_synthetic_template_pairs_file(self):
        """Structural check that this really is a different file, not a
        tag inside lr1_preference_pairs.json."""
        main_pairs_path = TEST_PATH.parent / "lr1_preference_pairs.json"
        self.assertNotEqual(TEST_PATH, main_pairs_path)

    def test_summarize_computes_real_human_agreement_rate(self):
        ihp.record_real_human_pair(
            participant_label="p1", original_sentence="a", difficulty_profile={},
            flagged_word="w", candidate_A="x", candidate_B="y",
            human_preferred="A", claude_preferred="A", claude_reason="r",
        )
        ihp.record_real_human_pair(
            participant_label="p1", original_sentence="b", difficulty_profile={},
            flagged_word="w", candidate_A="x", candidate_B="y",
            human_preferred="B", claude_preferred="tie", claude_reason="r2",
        )
        summary = ihp.summarize()
        self.assertEqual(summary["n"], 2)
        self.assertEqual(summary["agree"], 1)
        self.assertAlmostEqual(summary["rate"], 0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
