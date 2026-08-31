"""
tests/stage_lr_judge_pairs_test.py — stage_lr/judge_pairs.py, the
standard Claude-as-judge harness for Stage LR data path (a)
(effective 2026-08-30, DECISION_LOG.md 2026-08-30-O). Pure
prompt-building/response-parsing tests only — no actual model call,
since this module deliberately doesn't make one itself (see its
docstring).

    python tests/stage_lr_judge_pairs_test.py
"""
from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stage_lr.judge_pairs import build_judge_prompt, parse_judge_response, batches

_PAIR = {
    "id": 1, "original_sentence": "The report was late.",
    "difficulty_profile": {"sounds": ["pr"], "words": [], "phrases": []},
    "flagged_word": "report", "candidate_A": "summary", "candidate_B": "memo",
}


class PromptBuildingTest(unittest.TestCase):
    def test_prompt_never_reveals_a_preferred_answer(self):
        """The instructions text legitimately mentions 'preferred' as a
        concept — what must never happen is the DATA payload itself
        carrying a preferred/reason value for any pair, which would
        leak an already-known verdict into a supposedly blind task."""
        prompt = build_judge_prompt([_PAIR])
        data_section = prompt.split("Here is the data")[1]
        self.assertNotIn('"preferred"', data_section)
        self.assertNotIn('"reason"', data_section)

    def test_prompt_data_payload_only_carries_expected_fields(self):
        prompt = build_judge_prompt([_PAIR])
        data_section = prompt.split("Here is the data")[1]
        payload = json.loads(data_section.split("```json")[1].split("```")[0])
        self.assertEqual(set(payload[0].keys()), {
            "id", "original_sentence", "difficulty_profile", "flagged_word", "candidate_A", "candidate_B",
        })

    def test_prompt_never_mentions_phoneme_judgment(self):
        """Hard invariant: Claude is never asked to judge phonetics."""
        prompt = build_judge_prompt([_PAIR]).lower()
        self.assertNotIn("phoneme", prompt.replace("phoneme-avoidance filters", ""))
        self.assertIn("do not need to and should not judge phonetics", prompt.lower())

    def test_prompt_includes_all_pair_data(self):
        prompt = build_judge_prompt([_PAIR])
        self.assertIn("summary", prompt)
        self.assertIn("memo", prompt)
        self.assertIn("report", prompt)


class ResponseParsingTest(unittest.TestCase):
    def test_parses_fenced_json_array(self):
        resp = '```json\n[{"id": 1, "preferred": "A", "reason": "clear"}]\n```'
        result = parse_judge_response(resp)
        self.assertEqual(result, {1: {"preferred": "A", "reason": "clear"}})

    def test_parses_multiple_items(self):
        resp = '```json\n[{"id": 1, "preferred": "A", "reason": "x"}, {"id": 2, "preferred": "tie", "reason": "y"}]\n```'
        result = parse_judge_response(resp)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[2]["preferred"], "tie")


class BatchingTest(unittest.TestCase):
    def test_batches_respect_size(self):
        pairs = [dict(_PAIR, id=i) for i in range(60)]
        chunks = list(batches(pairs, size=25))
        self.assertEqual([len(c) for c in chunks], [25, 25, 10])


if __name__ == "__main__":
    unittest.main(verbosity=2)
