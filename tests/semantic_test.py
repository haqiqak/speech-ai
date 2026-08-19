"""
tests/semantic_test.py — unit tests for semantic.py's protected-position
logic, specifically the idiom/fixed-expression guard added per
REFORMULATION_PROBLEM_MAP.md SS2.4/SS5 item 1 (found from VALIDATION.md
SS9.7/SS9.9's pilot: "how's it going" and "drives me crazy" were broken by
substituting one word inside them; "right now" separately mis-substituted
by a word-sense bug this guard also happens to prevent, ahead of the
general word-sense-disambiguation fix planned as item 2).

No model loading required — protected_positions() is pure token matching.

    python tests/semantic_test.py
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nltk import word_tokenize
import paths  # noqa: F401
import semantic as sem


def _protected_words(text: str) -> set[str]:
    tokens = word_tokenize(text)
    idx = sem.protected_positions(tokens)
    return {tokens[i].lower() for i in idx}


class ExistingProtectedPhrasesUnaffectedTest(unittest.TestCase):
    """The new idiom lists are additive — confirm the pre-existing
    PROTECTED_PHRASES / single-stop-word behavior is unchanged."""

    def test_existing_connector_phrase_still_protected(self):
        protected = _protected_words("We proceeded according to the plan.")
        self.assertIn("according", protected)
        self.assertIn("to", protected)

    def test_plain_stop_word_still_protected(self):
        protected = _protected_words("It was a good day.")
        self.assertIn("it", protected)
        self.assertIn("was", protected)


class IdiomPhraseGuardTest(unittest.TestCase):
    def test_hows_it_going_protects_going(self):
        protected = _protected_words("Hey, how's it going today?")
        self.assertIn("going", protected)
        self.assertIn("how", protected)
        self.assertIn("'s", protected)

    def test_going_alone_not_protected_outside_the_idiom(self):
        # "going" in an unrelated sentence must NOT be swept up by the
        # idiom guard -- it's still a normal substitutable content word.
        protected = _protected_words("We are going to the store.")
        self.assertNotIn("going", protected)

    def test_whats_going_on_protects_going(self):
        protected = _protected_words("What's going on with the report?")
        self.assertIn("going", protected)

    def test_right_now_protects_right(self):
        protected = _protected_words("I need a break right now.")
        self.assertIn("right", protected)
        self.assertIn("now", protected)

    def test_right_alone_not_protected_outside_the_idiom(self):
        # "right" in "civil right" / "turn right" etc. must stay a normal
        # substitutable word -- only the fixed "right now/away/here" forms
        # are guarded.
        protected = _protected_words("She has the right to vote.")
        self.assertNotIn("right", protected)

    def test_right_away_and_right_here_protected(self):
        self.assertIn("right", _protected_words("Come here right away."))
        self.assertIn("right", _protected_words("Stop right here."))

    def test_push_the_meeting_protects_push(self):
        # R26/R27 (VALIDATION.md SS17-18): "push [a meeting]" (postpone) has
        # no WordNet sense at all, so every substitution candidate was a
        # semantically-close but wrong "exert force" synonym.
        protected = _protected_words("Can we push the meeting and grab coffee after?")
        self.assertIn("push", protected)
        self.assertIn("meeting", protected)

    def test_push_alone_not_protected_outside_the_idiom(self):
        # "push" in an unrelated sentence ("push the button", "push harder")
        # must stay a normal substitutable content word -- only the exact
        # observed phrase is guarded (REFORMULATION_PROBLEM_MAP.md SS3.1's
        # disclosed [GAP]: a curated list, not a general phrasal-verb
        # detector).
        protected = _protected_words("Please push the button to start.")
        self.assertNotIn("push", protected)


class IdiomPronounPatternTest(unittest.TestCase):
    def test_drives_me_crazy_protects_driving_slot(self):
        protected = _protected_words("The kids are driving me crazy today.")
        self.assertIn("driving", protected)
        self.assertIn("me", protected)
        self.assertIn("crazy", protected)

    def test_pronoun_wildcard_covers_other_pronouns(self):
        for pron in ("him", "her", "us", "you", "them", "it"):
            with self.subTest(pron=pron):
                protected = _protected_words(f"This weather drives {pron} crazy.")
                self.assertIn("drives", protected)
                self.assertIn(pron, protected)

    def test_unrelated_pronoun_not_matched(self):
        # A word not in the small pronoun set must not match the wildcard.
        protected = _protected_words("This weather drives Sam crazy.")
        self.assertNotIn("drives", protected)

    def test_crazy_alone_not_protected_outside_the_idiom(self):
        protected = _protected_words("That was a crazy idea.")
        self.assertNotIn("crazy", protected)


class IdiomSpansTest(unittest.TestCase):
    """Regression tests for idiom_spans() — REFORMULATION_PROBLEM_MAP.md
    SS5 item 4's phrase-level tier needs the actual (start, end) span
    boundaries, not just the flat position set idiom_protected_positions()
    returns, to know exactly what contiguous stretch to replace."""

    def test_span_boundaries_for_exact_phrase(self):
        tokens = word_tokenize("Hey, how's it going today?")
        spans = sem.idiom_spans(tokens)
        self.assertEqual(len(spans), 1)
        start, end = spans[0]
        self.assertEqual([t.lower() for t in tokens[start:end]], ["how", "'s", "it", "going"])

    def test_span_boundaries_for_pronoun_pattern(self):
        tokens = word_tokenize("The kids are driving me crazy today.")
        spans = sem.idiom_spans(tokens)
        self.assertEqual(len(spans), 1)
        start, end = spans[0]
        self.assertEqual([t.lower() for t in tokens[start:end]], ["driving", "me", "crazy"])

    def test_no_spans_when_no_idiom_present(self):
        tokens = word_tokenize("We are going to the store.")
        self.assertEqual(sem.idiom_spans(tokens), [])

    def test_idiom_protected_positions_still_matches_flattened_spans(self):
        # idiom_protected_positions() is now derived from idiom_spans() --
        # confirm the refactor is behavior-preserving, not just re-tested
        # indirectly through the pre-existing protected_positions() tests.
        tokens = word_tokenize("I really need a break right now.")
        spans = sem.idiom_spans(tokens)
        flattened = set()
        for start, end in spans:
            flattened.update(range(start, end))
        self.assertEqual(flattened, sem.idiom_protected_positions(tokens))
        self.assertTrue(flattened)  # sanity: "right now" should have matched


if __name__ == "__main__":
    unittest.main(verbosity=2)
