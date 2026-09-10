"""
tests/stage_lr_claude_only_pairs_test.py -- stage_lr/claude_only_pairs.py
(2026-09-01), the Claude-only-judged dataset-growth track, kept
separate from stage_lr/ingest_real_human_pair.py's dual-verdict file.

    python tests/stage_lr_claude_only_pairs_test.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stage_lr.claude_only_pairs as cop


class ClaudeOnlyPairsTest(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._real_path = cop.CLAUDE_ONLY_PAIRS_PATH
        cop.CLAUDE_ONLY_PAIRS_PATH = Path(self._tmp_dir.name) / "claude_only_pairs.json"

    def tearDown(self):
        cop.CLAUDE_ONLY_PAIRS_PATH = self._real_path
        self._tmp_dir.cleanup()

    def test_record_carries_source_tag_and_no_human_field(self):
        record = cop.record_claude_only_pair(
            participant_label="friend_1", original_sentence="a", difficulty_profile={},
            flagged_word="w", candidate_A="x", candidate_B="y",
            claude_preferred="A", claude_reason="r",
        )
        self.assertEqual(record["source"], "real_profile_claude_only")
        self.assertNotIn("human_preferred", record)
        self.assertIsNotNone(record["judged_at"])

    def test_summarize_counts_by_participant(self):
        cop.record_claude_only_pair(
            participant_label="friend_1", original_sentence="a", difficulty_profile={},
            flagged_word="w", candidate_A="x", candidate_B="y", claude_preferred="A", claude_reason="r",
        )
        cop.record_claude_only_pair(
            participant_label="friend_1", original_sentence="b", difficulty_profile={},
            flagged_word="w", candidate_A="x", candidate_B="y", claude_preferred="B", claude_reason="r",
        )
        cop.record_claude_only_pair(
            participant_label="friend_2", original_sentence="c", difficulty_profile={},
            flagged_word="w", candidate_A="x", candidate_B="y", claude_preferred="tie", claude_reason="r",
        )
        summary = cop.summarize()
        self.assertEqual(summary["n"], 3)
        self.assertEqual(summary["by_participant"], {"friend_1": 2, "friend_2": 1})

    def test_stored_separately_from_real_human_pairs_file(self):
        import stage_lr.ingest_real_human_pair as ihp
        self.assertNotEqual(cop.CLAUDE_ONLY_PAIRS_PATH.name, ihp.REAL_HUMAN_PAIRS_PATH.name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
