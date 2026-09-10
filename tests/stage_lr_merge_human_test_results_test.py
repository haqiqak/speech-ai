"""
tests/stage_lr_merge_human_test_results_test.py -- stage_lr/merge_human_test_results.py,
the module that closes the loop opened by human_test_tool.html (2026-09-01).

    python tests/stage_lr_merge_human_test_results_test.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stage_lr.ingest_real_human_pair as ihp
import stage_lr.merge_human_test_results as merge_mod
from stage_lr.merge_human_test_results import load_merged, to_judge_payload, log_all

SAMPLE_PAIRS = [
    {
        "review_id": 1,
        "source_uids": ["x-1"],
        "sentence_with_A": "The manager will state the results tomorrow.",
        "sentence_with_B": "The manager will say the results tomorrow.",
        "changed_word": "present",
        "candidate_A": "state",
        "candidate_B": "say",
    },
    {
        "review_id": 2,
        "source_uids": ["x-2"],
        "sentence_with_A": "She was asked to show her work.",
        "sentence_with_B": "She was asked to exhibit her work.",
        "changed_word": "present",
        "candidate_A": "show",
        "candidate_B": "exhibit",
    },
]


class LoadMergedTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pairs_path = Path(self._tmp.name) / "pairs_for_review.json"
        self.pairs_path.write_text(json.dumps(SAMPLE_PAIRS), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _write_results(self, results):
        p = Path(self._tmp.name) / "human_test_results.json"
        p.write_text(json.dumps({"results": results}), encoding="utf-8")
        return p

    def test_joins_on_review_id_and_reconstructs_original_sentence(self):
        results_path = self._write_results([
            {"review_id": 1, "human_preferred": "A"},
            {"review_id": 2, "human_preferred": "B"},
        ])
        merged = load_merged(self.pairs_path, results_path)
        self.assertEqual(len(merged), 2)
        row1 = next(r for r in merged if r["review_id"] == 1)
        self.assertEqual(row1["human_preferred"], "A")
        self.assertEqual(row1["original_sentence"], "The manager will present the results tomorrow.")
        row2 = next(r for r in merged if r["review_id"] == 2)
        self.assertEqual(row2["human_preferred"], "B")
        self.assertEqual(row2["original_sentence"], "She was asked to present her work.")

    def test_accepts_bare_list_results_format_too(self):
        p = Path(self._tmp.name) / "bare_results.json"
        p.write_text(json.dumps([
            {"review_id": 1, "human_preferred": "tie"},
            {"review_id": 2, "human_preferred": "A"},
        ]), encoding="utf-8")
        merged = load_merged(self.pairs_path, p)
        self.assertEqual(len(merged), 2)

    def test_raises_if_a_review_id_is_missing_from_results(self):
        results_path = self._write_results([{"review_id": 1, "human_preferred": "A"}])
        with self.assertRaises(ValueError):
            load_merged(self.pairs_path, results_path)

    def test_raises_on_invalid_human_preferred_value(self):
        results_path = self._write_results([
            {"review_id": 1, "human_preferred": "A"},
            {"review_id": 2, "human_preferred": "banana"},
        ])
        with self.assertRaises(ValueError):
            load_merged(self.pairs_path, results_path)


class JudgePayloadTest(unittest.TestCase):
    def test_builds_correct_shape_for_judge_pairs(self):
        merged = [
            {"review_id": 1, "original_sentence": "The manager will present the results tomorrow.",
             "changed_word": "present", "candidate_A": "state", "candidate_B": "say",
             "human_preferred": "A"},
        ]
        profile = {"sounds": ["pr"], "words": ["present"], "phrases": []}
        payload = to_judge_payload(merged, profile)
        self.assertEqual(payload, [{
            "id": 1,
            "original_sentence": "The manager will present the results tomorrow.",
            "difficulty_profile": profile,
            "flagged_word": "present",
            "candidate_A": "state",
            "candidate_B": "say",
        }])
        # human_preferred must never leak into the judge payload -- the
        # judge call has to stay blind.
        self.assertNotIn("human_preferred", payload[0])


class LogAllTest(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._real_path = ihp.REAL_HUMAN_PAIRS_PATH
        ihp.REAL_HUMAN_PAIRS_PATH = Path(self._tmp_dir.name) / "real_human_pairs.json"

    def tearDown(self):
        ihp.REAL_HUMAN_PAIRS_PATH = self._real_path
        self._tmp_dir.cleanup()

    def test_logs_every_pair_and_returns_summary(self):
        merged = [
            {"review_id": 1, "original_sentence": "a", "changed_word": "w",
             "candidate_A": "x", "candidate_B": "y", "human_preferred": "A"},
            {"review_id": 2, "original_sentence": "b", "changed_word": "w",
             "candidate_A": "x", "candidate_B": "y", "human_preferred": "B"},
        ]
        claude_verdicts = {
            1: {"preferred": "A", "reason": "r1"},
            2: {"preferred": "tie", "reason": "r2"},
        }
        summary = log_all(merged, claude_verdicts, participant_label="p1",
                           difficulty_profile={"sounds": [], "words": [], "phrases": []})
        self.assertEqual(summary["n"], 2)
        self.assertEqual(summary["agree"], 1)

    def test_raises_if_a_pair_has_no_claude_verdict(self):
        merged = [
            {"review_id": 1, "original_sentence": "a", "changed_word": "w",
             "candidate_A": "x", "candidate_B": "y", "human_preferred": "A"},
        ]
        with self.assertRaises(ValueError):
            log_all(merged, {}, participant_label="p1",
                    difficulty_profile={"sounds": [], "words": [], "phrases": []})


if __name__ == "__main__":
    unittest.main(verbosity=2)
