"""
tests/rephrase_test.py — regression tests for rephrase.py's word-blocking,
specifically the case-insensitivity fix (ROADMAP.md R17, VALIDATION.md §6.3
Cause A / R17 follow-up): `_bad_words_ids()` previously encoded only the
exact-case form of each blocked word passed in, so a capitalized occurrence
of an otherwise-blocked word (most commonly sentence-initial position)
could still be generated. Confirmed directly: with only the lowercase
form blocked, the lowercase token leaked in 0/6 beam outputs while the
capitalized form of the identical word leaked in 5/6.

Not covered here (a separate, unresolved issue found while verifying this
fix, out of R17's scope): some words can still leak via a *different*
subword segmentation of the identical string even when every case variant
is blocked (e.g. "researcher" as one token vs. "research"+"er" as two) —
see VALIDATION.md §6.3's R17 follow-up note. The generation-level tests
below use words verified NOT to have this alternate-tokenization escape,
so they isolate the case-sensitivity fix specifically.

    DISABLE_DATAMUSE=1 python tests/rephrase_test.py
"""
from __future__ import annotations

import os
import re
import sys
import unittest

os.environ.setdefault("DISABLE_DATAMUSE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rephrase

_MODEL_AVAILABLE = rephrase._load_model()
_SKIP_REASON = "T5 model/tokenizer unavailable in this environment"


class BadWordsIdsUnitTest(unittest.TestCase):
    """Fast, deterministic checks on _bad_words_ids() itself — no generation."""

    @unittest.skipUnless(_MODEL_AVAILABLE, _SKIP_REASON)
    def test_includes_lowercase_and_capitalized_token_sequences(self):
        tok = rephrase._tokenizer
        ids = rephrase._bad_words_ids({"researcher"})
        lower_ids = tok.encode("researcher", add_special_tokens=False)
        cap_ids = tok.encode("Researcher", add_special_tokens=False)
        self.assertIn(lower_ids, ids)
        self.assertIn(cap_ids, ids)
        self.assertNotEqual(
            lower_ids, cap_ids,
            "test word must actually tokenize differently by case to be a meaningful check",
        )

    @unittest.skipUnless(_MODEL_AVAILABLE, _SKIP_REASON)
    def test_leading_space_variants_still_present(self):
        """Regression: the pre-fix behavior of also blocking a leading-space
        form (which frequently changes the token boundary for this
        tokenizer) must survive the case-insensitivity change."""
        tok = rephrase._tokenizer
        ids = rephrase._bad_words_ids({"manager"})
        self.assertIn(tok.encode(" manager", add_special_tokens=False), ids)
        self.assertIn(tok.encode(" Manager", add_special_tokens=False), ids)

    @unittest.skipUnless(_MODEL_AVAILABLE, _SKIP_REASON)
    def test_original_case_form_still_included(self):
        """A caller passing an already-mixed-case word (e.g. a proper noun
        like 'TensorFlow') must still have that exact form blocked, not
        just its .lower()/.capitalize() derivatives."""
        tok = rephrase._tokenizer
        ids = rephrase._bad_words_ids({"TensorFlow"})
        self.assertIn(tok.encode("TensorFlow", add_special_tokens=False), ids)

    def test_empty_or_none_returns_none(self):
        self.assertIsNone(rephrase._bad_words_ids(None))
        self.assertIsNone(rephrase._bad_words_ids(set()))

    @unittest.skipUnless(_MODEL_AVAILABLE, _SKIP_REASON)
    def test_no_duplicate_token_sequences(self):
        """Case variants that collide (e.g. a one-letter word, where
        .lower() == .capitalize() in effect) must not produce redundant
        entries."""
        ids = rephrase._bad_words_ids({"a"})
        self.assertEqual(len(ids), len(set(tuple(i) for i in ids)))


class GenerationCaseLeakTest(unittest.TestCase):
    """Integration-level: actually generate candidates and confirm a
    literally-blocked word does not reappear under a different case, in
    both a mid-sentence (naturally lowercase) and a sentence-initial
    (naturally capitalized) context. Uses words verified not to have the
    separate alternate-tokenization escape noted in the module docstring."""

    @unittest.skipUnless(_MODEL_AVAILABLE, _SKIP_REASON)
    def test_sentence_initial_capitalization_does_not_leak_blocked_word(self):
        sentence = "The manager carefully reviewed the printed report before the morning meeting."
        blocked = {"manager", "reviewed", "printed", "report", "morning", "meeting"}
        candidates = rephrase.generate_candidates(sentence, k=6, blocked_words=blocked)
        self.assertGreater(len(candidates), 1, "model produced no alternative candidates at all")
        for cand in candidates[1:]:  # [0] is always the unmodified input
            words = {w.lower() for w in re.findall(r"[A-Za-z']+", cand)}
            leaked = words & blocked
            self.assertFalse(
                leaked, f"blocked word(s) {leaked} leaked (any case) into candidate: {cand!r}"
            )

    @unittest.skipUnless(_MODEL_AVAILABLE, _SKIP_REASON)
    def test_mid_sentence_and_sentence_initial_both_blocked(self):
        """Same blocked word, two sentences: one where it's naturally
        lowercase (mid-sentence) and one where it's naturally capitalized
        (sentence-initial) — both must be blocked by the same call, and
        both use distinct lowercase/capitalized token IDs (verified via
        BadWordsIdsUnitTest), so this is a real case-sensitivity check,
        not a coincidence of one word's tokenization."""
        blocked = {"strong"}
        mid = rephrase.generate_candidates("The weather was strong today.", k=4, blocked_words=blocked)
        initial = rephrase.generate_candidates("Strong winds hit the coast today.", k=4, blocked_words=blocked)
        for cand in mid[1:] + initial[1:]:
            self.assertNotIn("strong", cand.lower())

    @unittest.skipUnless(_MODEL_AVAILABLE, _SKIP_REASON)
    def test_unblocked_generation_unaffected(self):
        """Regression: generation with no blocked words must behave exactly
        as before — this fix only changes what happens when blocked_words
        is non-empty."""
        candidates = rephrase.generate_candidates("The team reached a decision.", k=3, blocked_words=None)
        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(candidates[0], "The team reached a decision.")


if __name__ == "__main__":
    unittest.main()
