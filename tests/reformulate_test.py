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


class IdiomGuardTest(unittest.TestCase):
    """Regression tests for REFORMULATION_PROBLEM_MAP.md SS5 item 1, using the
    exact sentences/profiles from the real VALIDATION.md SS9.6-9.9 pilot that
    found each failure -- not synthetic restatements. Before this guard,
    reformulate() broke each idiom by substituting one word inside it
    (pair_01: "going"->awkward substitute; pair_11: "driving"->"going",
    producing "going me crazy"; pair_15's "right"->"justly"/"properly" word-
    sense error is also prevented here since "right now" is now a protected
    phrase, ahead of the separate general word-sense-disambiguation fix)."""

    def test_hows_it_going_is_left_completely_unchanged(self):
        # As of SS5 item 4 (the phrase-level tier), a live T5 call now
        # happens here where none did before -- mocked to return no
        # usable candidate (the established EscalationTest pattern) so
        # this stays deterministic and keeps testing what it always
        # tested: when NOTHING works, the idiom is left alone and the
        # unresolved difficulty is reported honestly, not silently.
        profile = _profile("idiom_hows_it_going")
        profile.add_sound("g", source="user_typed")
        with mock.patch.object(rf.rephrase, "generate_candidates", side_effect=lambda sentence, **kw: [sentence]):
            result = rf.reformulate("Hey, how's it going today?", profile)
        self.assertEqual(result["status"], "could_not_safely_reformulate")
        self.assertIn("going", result["reformulated_text"].lower())
        self.assertEqual(result["metrics"]["flagged_words_before"], 1)
        self.assertEqual(result["metrics"]["flagged_words_after"], 1)
        self.assertTrue(any("fixed expression" in s["reason"] for s in result["skipped"]))

    def test_drives_me_crazy_is_left_completely_unchanged(self):
        profile = _profile("idiom_drives_me_crazy")
        profile.add_sound("d", source="user_typed")
        with mock.patch.object(rf.rephrase, "generate_candidates", side_effect=lambda sentence, **kw: [sentence]):
            result = rf.reformulate("The kids are driving me crazy today.", profile)
        self.assertEqual(result["status"], "could_not_safely_reformulate")
        self.assertIn("driving me crazy", result["reformulated_text"].lower())
        self.assertEqual(result["metrics"]["flagged_words_before"], 1)
        self.assertEqual(result["metrics"]["flagged_words_after"], 1)

    def test_right_now_survives_even_when_a_sibling_word_is_substituted(self):
        # "really" (also R-onset) is NOT part of the idiom and remains a
        # normal substitution target -- the guard must protect "right now"
        # specifically, not suppress the whole sentence.
        profile = _profile("idiom_right_now")
        profile.add_sound("r", source="user_typed")
        result = rf.reformulate("I really need a break right now.", profile)
        self.assertIn("right now", result["reformulated_text"].lower())

    def test_push_the_meeting_survives_while_grab_is_still_substituted(self):
        # R26/R27 (VALIDATION.md SS17-18): before this guard, "push" (no
        # WordNet sense for "postpone") got substituted to "force"/"urge",
        # a meaning-drifting fix. This is a MIXED case (push AND grab both
        # flagged) -- per R25's design the phrase tier is never attempted
        # here; "push" is simply left alone (an honest, disclosed partial
        # result) while "grab" -- a separate, still-open problem
        # (VALIDATION.md SS18.2's generic-word-ranking pattern) -- is still
        # substituted normally, unaffected by this guard.
        profile = _profile("idiom_push_meeting")
        profile.add_sound("p", source="user_typed")
        profile.add_sound("gr", source="user_typed")
        result = rf.reformulate("Can we push the meeting and grab coffee after?", profile)
        self.assertIn("push the meeting", result["reformulated_text"].lower())
        self.assertNotIn(" grab ", f" {result['reformulated_text'].lower()} ")
        self.assertTrue(any("fixed expression" in s["reason"] for s in result["skipped"]))
        self.assertEqual(result["metrics"]["flagged_words_before"], 2)
        self.assertEqual(result["metrics"]["flagged_words_after"], 1)


class PhraseTierTest(unittest.TestCase):
    """Regression tests for REFORMULATION_PROBLEM_MAP.md SS5 item 4 -- the
    phrase-level replacement tier between word-substitution and whole-
    sentence restructuring. All T5 generation is mocked (the same
    determinism discipline EscalationTest uses) since live T5 output is
    documented elsewhere in this project as non-deterministic across
    process launches -- these tests are about reformulate.py's own
    trigger/splice/verify logic, not about what T5 happens to produce."""

    def test_phrase_replacement_used_when_word_substitution_impossible(self):
        profile = _profile("phrase_hows_it_going")
        profile.add_sound("g", source="user_typed")
        good = "Hey, how are you doing today?"
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[good]):
            result = rf.reformulate("Hey, how's it going today?", profile)
        self.assertEqual(result["status"], "reformulated")
        self.assertEqual(len(result["changes"]), 1)
        change = result["changes"][0]
        self.assertEqual(change["source"], "phrase")
        self.assertIn("global_sound", change["triggered_by"])
        self.assertNotIn("going", result["reformulated_text"].lower())
        self.assertEqual(result["metrics"]["flagged_words_after"], 0)

    def test_phrase_tier_falls_back_to_skip_when_candidate_still_leaks(self):
        # The candidate changes the window but the flagged word is still
        # literally present -- the full-sentence leak scan must still
        # catch it (same discipline _try_escalation already applies),
        # not just accept because SOMETHING changed.
        profile = _profile("phrase_leak")
        profile.add_sound("g", source="user_typed")
        leaky = "Hey, how's it going still today?"
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[leaky]):
            result = rf.reformulate("Hey, how's it going today?", profile)
        self.assertEqual(result["status"], "could_not_safely_reformulate")
        self.assertIn("going", result["reformulated_text"].lower())
        self.assertTrue(any("fixed expression" in s["reason"] for s in result["skipped"]))

    def test_phrase_change_feedback_targets_attribution(self):
        profile = _profile("phrase_feedback")
        profile.add_sound("g", source="user_typed")
        good = "Hey, how are you doing today?"
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[good]):
            result = rf.reformulate("Hey, how's it going today?", profile)
        change = result["changes"][0]
        targets = rf.feedback_targets(change, profile)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].value, "g")

    def test_splice_preserves_text_outside_the_local_window(self):
        # A longer sentence where the idiom span + context radius is a
        # true SUBSET of the sentence -- confirms splicing doesn't
        # disturb text well outside the window, not just that the idiom
        # itself gets replaced.
        profile = _profile("phrase_splice")
        profile.add_sound("d", source="user_typed")
        original = (
            "Well, to be fair, the kids are driving me crazy today, "
            "and I have no idea what to do about it."
        )
        result = rf.reformulate(original, profile)
        self.assertIn("well, to be fair", result["reformulated_text"].lower())
        self.assertIn("no idea what to do about it", result["reformulated_text"].lower())
        if result["status"] == "reformulated":
            self.assertEqual(result["changes"][0]["source"], "phrase")
            self.assertNotIn("driving", result["reformulated_text"].lower())
        else:
            # T5 unavailable/no usable candidate in this environment --
            # still must be the honest, disclosed skip, not silence.
            self.assertEqual(result["status"], "could_not_safely_reformulate")
            self.assertIn("driving me crazy", result["reformulated_text"].lower())


class WordSenseDisambiguationTest(unittest.TestCase):
    """Regression tests for REFORMULATION_PROBLEM_MAP.md SS5 item 2. Unlike
    IdiomGuardTest, these deliberately use sentences the idiom guard does
    NOT cover, to confirm the fix generalizes beyond the one "right now"
    phrase -- it corrects candidate-generation sense selection, not just
    that specific idiom."""

    def test_immediate_sense_of_right_not_confused_with_correct_sense(self):
        # "right" here means "immediately" (right.r.02), not "correctly"/
        # "properly"/"justly" (the wrong senses the old, sense-unaware
        # candidate pool used to surface -- VALIDATION.md SS9.9). Not
        # covered by the idiom guard (only literal "right now/away/here"
        # are on that list) -- this exercises WSD itself.
        profile = _profile("wsd_right_immediate")
        profile.add_sound("r", source="user_typed")
        result = rf.reformulate("He'll be right over to help.", profile)
        for wrong in ("justly", "properly", "correctly", "mighty", "mightily"):
            self.assertNotIn(wrong, result["reformulated_text"].lower())

    def test_candidate_never_reintroduces_another_declared_word(self):
        # A follow-up bug found via the Stage 6 corpus re-run: WSD's more
        # precise ranking picked "examined" -- itself one of the profile's
        # OTHER declared-difficult words -- as the top candidate for
        # "reviewed" in the same sentence. A candidate must never match
        # any of the profile's OTHER declared words either.
        profile = _profile("wsd_no_collision")
        profile.add_word("reviewed", source="user_typed")
        profile.add_word("examined", source="user_typed")
        result = rf.reformulate(
            "I thoroughly reviewed three reports and carefully examined the results.",
            profile,
        )
        self.assertEqual(result["metrics"]["flagged_words_after"], 0)
        for change in result["changes"]:
            self.assertNotIn(change["replacement"].lower(), {"reviewed", "examined"})

    def test_repeated_word_different_senses_get_different_replacements(self):
        # Whole-sentence disambiguation (the first version of this fix) fed
        # BOTH occurrences of "runs" the identical context string, so both
        # got the identical sense and the identical (wrong-for-at-least-one)
        # replacement -- confirmed directly via the Stage 6 corpus re-run
        # (VALIDATION.md SS11). Fixed with a local context window per
        # occurrence instead of the whole sentence.
        profile = _profile("wsd_local_window")
        profile.add_word("runs", source="user_typed")
        result = rf.reformulate(
            "He runs the company every morning before he runs three miles.", profile
        )
        subs = [c for c in result["changes"] if c["source"] == "substitution"]
        self.assertEqual(len(subs), 2)
        self.assertNotEqual(subs[0]["replacement"].lower(), subs[1]["replacement"].lower())


class PredicateAdjectiveTaggingTest(unittest.TestCase):
    """Regression tests for a POS-tagging bug found during the R30 design
    investigation (VALIDATION.md's pair_13 record): nltk's pos_tag()
    mis-tags a flat adverb (late/fast/early/...) as RB when it's actually
    a predicate adjective right after a copula ("was late"), so candidate
    generation was restricted to adverb-sense synonyms only, producing
    "The bus was recently again" -- a long-standing known bug, unrelated
    to CONAN's escalation-trigger design work. Fixed narrowly with a
    curated flat-adverb list (reformulate._correct_predicate_adjective_tags),
    not a general WordNet-sense check -- that broader approach was tried
    first and found to over-fire (WordNet lists a rare adjective sense for
    "here," which would have mis-tagged "He was here.")."""

    def test_predicate_late_gets_adjective_synonym_not_adverb(self):
        profile = _profile("predicate_late")
        profile.add_word("late", source="user_typed")
        result = rf.reformulate("The bus was late again this morning.", profile)
        for wrong in ("recently", "lately", "later"):
            self.assertNotIn(wrong, result["reformulated_text"].lower())
        self.assertEqual(result["metrics"]["flagged_words_after"], 0)

    def test_adverbial_late_elsewhere_in_sentence_still_tagged_adverb(self):
        # "arrived late" -- purely adverbial, no copula precedes it --
        # must NOT be reclassified; confirms the fix doesn't just always
        # treat "late" as an adjective regardless of context.
        tokens = ["The", "train", "arrived", "late", "."]
        tags = [("The", "DT"), ("train", "NN"), ("arrived", "VBD"), ("late", "RB"), (".", ".")]
        corrected = rf._correct_predicate_adjective_tags(tokens, tags)
        self.assertEqual(corrected[3], ("late", "RB"))

    def test_genuine_predicate_adverb_not_reclassified(self):
        # "here"/"now" are genuinely adverbial predicate complements, not
        # adjectives -- the exact false positive the curated-list approach
        # was chosen specifically to avoid (see class docstring).
        tokens = ["He", "was", "here", "."]
        tags = [("He", "PRP"), ("was", "VBD"), ("here", "RB"), (".", ".")]
        corrected = rf._correct_predicate_adjective_tags(tokens, tags)
        self.assertEqual(corrected[2], ("here", "RB"))

        tokens = ["It", "is", "now", "."]
        tags = [("It", "PRP"), ("is", "VBZ"), ("now", "RB"), (".", ".")]
        corrected = rf._correct_predicate_adjective_tags(tokens, tags)
        self.assertEqual(corrected[2], ("now", "RB"))


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


class FeedbackTargetsTest(unittest.TestCase):
    """ROADMAP.md R9 — reformulate.feedback_targets(). Read-only: these
    tests also confirm calling it never mutates the profile or the result
    it was given (the reformulation engine itself must be unaffected)."""

    def test_declared_word_substitution_attributes_to_the_word_entry(self):
        profile = _profile("fbt_word")
        profile.add_word("particular", source="user_typed")
        result = rf.reformulate("I have a particular preference for the third option.", profile)
        subs = [c for c in result["changes"] if c["source"] == "substitution"]
        self.assertTrue(subs)
        targets = rf.feedback_targets(subs[0], profile)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].normalized, "particular")

    def test_global_sound_substitution_attributes_to_the_sound_entry(self):
        profile = _profile("fbt_sound")
        profile.add_sound("str", source="user_typed")
        # Same sentence as SubstitutionTest.test_global_sound_flag_produces_
        # substitution -- known to reliably survive as a substitution (not
        # an escalation) with the word-sense-disambiguation fix (item 2)
        # in place, unlike a lone "strong decision", which now correctly
        # escalates to restructuring since its single-sense candidate pool
        # (firm/forceful) doesn't clear the SBERT gate for that sentence
        # (VALIDATION.md SS11 -- a disclosed trade-off, not a bug).
        result = rf.reformulate(
            "I need to review three reports before the strong deadline.", profile
        )
        subs = [c for c in result["changes"] if c["source"] == "substitution"]
        self.assertTrue(subs)
        targets = rf.feedback_targets(subs[0], profile)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].value, "str")

    def test_restructuring_change_has_no_targets(self):
        """A whole-sentence restructuring can't be cleanly attributed to
        one declared entry — feedback_targets must return [] rather than
        guess, per its own documented design."""
        profile = _profile("fbt_restructure")
        profile.add_sound("str", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=0)
        result = rf.reformulate("The team reached a strong decision.", profile, settings)
        restructured = [c for c in result["changes"] if c["source"] == "restructuring"]
        if restructured:  # escalation succeeding isn't guaranteed; only assert when it happens
            self.assertEqual(rf.feedback_targets(restructured[0], profile), [])

    def test_no_targets_for_a_change_that_matches_nothing(self):
        profile = _profile("fbt_none")
        fake_change = {"source": "substitution", "original": "unrelated", "triggered_by": []}
        self.assertEqual(rf.feedback_targets(fake_change, profile), [])

    def test_feedback_targets_does_not_mutate_profile_or_change(self):
        profile = _profile("fbt_no_mutate")
        profile.add_word("particular", source="user_typed")
        result = rf.reformulate("I have a particular preference for the third option.", profile)
        subs = [c for c in result["changes"] if c["source"] == "substitution"]
        before_words = list(profile.word_values())
        before_change = dict(subs[0])
        rf.feedback_targets(subs[0], profile)
        self.assertEqual(profile.word_values(), before_words)
        self.assertEqual(subs[0], before_change)


if __name__ == "__main__":
    unittest.main()
