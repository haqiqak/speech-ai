"""Regression tests for the fluency rewrite roadmap implementation."""

from __future__ import annotations

import os
import sys
import unittest

os.environ["DISABLE_DATAMUSE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from profiling.detect import detect_disfluencies
from profiling.profile import SpeakerDifficultyProfile
from rewrite.rewriter import DifficultyAwareRewriter


def fresh_profile() -> SpeakerDifficultyProfile:
    profile = SpeakerDifficultyProfile(username="test-roadmap")
    profile.onboarding(["b"])
    return profile


class RoadmapTest(unittest.TestCase):
    def test_detector_matches_tiny_fixture(self):
        tokens = [
            {"word": "I", "start": 0.0, "end": 0.1},
            {"word": "um", "start": 0.2, "end": 0.4, "is_filler": True},
            {"word": "b-", "start": 0.5, "end": 0.7, "is_stutter": True},
            {"word": "buy", "start": 1.4, "end": 2.2},
            {"word": "buy", "start": 2.25, "end": 2.45},
        ]
        events = detect_disfluencies(
            tokens,
            {
                "block_gap_seconds": 0.5,
                "prolongation_min_seconds": 0.6,
                "prolongation_percentile": 80,
                "filler_words": ["um"],
            },
        )
        kinds = {(event["word"], event["type"]) for event in events}
        self.assertIn(("um", "filler"), kinds)
        self.assertIn(("b-", "stutter_marker"), kinds)
        self.assertIn(("buy", "block"), kinds)
        self.assertIn(("buy", "repetition"), kinds)

    def test_profile_elevates_and_data_overrides_prior(self):
        profile = fresh_profile()
        b_before = profile.onset_risk.get("B", 0.0)
        profile.update(
            [
                {"word": "sun", "disfluent": True},
                {"word": "strong", "disfluent": True},
                {"word": "big", "disfluent": False},
                {"word": "buy", "disfluent": False},
            ],
            alpha=0.8,
        )
        self.assertGreater(profile.onset_risk.get("S", 0.0), b_before)
        self.assertLess(profile.onset_risk.get("B", 1.0), b_before)

    def test_rewriter_protects_words_and_reduces_or_preserves_risk(self):
        profile = fresh_profile()
        rewriter = DifficultyAwareRewriter()
        text = "Alice begins a big project."
        result = rewriter.rewrite_paragraph(
            text,
            profile,
            always_keep={"Alice"},
            always_replace={"begins", "big"},
            lambda_=0.7,
            tau=0.0,
        )
        self.assertIn("Alice", result["rewritten_text"])
        self.assertNotIn("large Alice", result["rewritten_text"])
        self.assertLessEqual(
            result["metrics"]["difficulty_onset_after"],
            result["metrics"]["difficulty_onset_before"],
        )
        for change in result["change_log"]:
            self.assertTrue(change["replacement"])
            self.assertTrue(
                change["sim_source"] == "fallback"
                or change["sim"] is None
                or change["sim"] >= 0.0
            )

    def test_returning_profile_tracks_sessions(self):
        profile = SpeakerDifficultyProfile(username="test-returning")
        profile.onboarding([])
        for idx in range(3):
            profile.update(
                [{"word": "project", "disfluent": True}, {"word": "calm", "disfluent": False}],
                session_id=f"s{idx}",
                alpha=0.5,
            )
        top = dict(profile.top_onsets(3))
        self.assertIn("P R", top)
        self.assertEqual(len(profile.sessions), 3)


if __name__ == "__main__":
    unittest.main()
