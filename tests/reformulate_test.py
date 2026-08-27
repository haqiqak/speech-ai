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
import engine as engine_module
from nltk import pos_tag, word_tokenize
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


class ProtectedPhraseEscalationTest(unittest.TestCase):
    """Phase 11 category 1 (VALIDATION.md SS48, eval/r10b_failure_analysis.md)
    -- protected_positions() only ever gated substitution-tier candidate
    generation; escalation's freely restructured T5 output was never checked
    against the same fixed-term list, which is how most of Phase 10's
    verified fixed-term breaks happened ("magma chamber" -> "magma cave",
    etc, R10-031 and siblings). These tests use "activation energy"
    (semantic.py IDIOM_PHRASES, added for R10-015) the same way EscalationTest
    mocks rf.rephrase.generate_candidates for determinism."""

    def test_escalation_candidate_dropping_protected_phrase_is_rejected(self):
        # Two flagged words (neither is "activation" itself) push this past
        # the escalation threshold directly -- matching R10-015's real
        # trigger, where some OTHER declared difficulty forced a whole-
        # sentence restructure and "activation energy" was collateral
        # damage, not the flagged word being fixed.
        profile = _profile("escalation_phrase_drop")
        profile.add_word("requires", source="user_typed")
        profile.add_word("specific", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=1)
        original = "The reaction requires a specific activation energy to proceed."
        leaky = "The reaction needs a certain amount of energy to proceed."
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[leaky]):
            result = rf.reformulate(original, profile, settings)
        self.assertEqual(result["status"], "could_not_safely_reformulate")
        self.assertIn("activation energy", result["reformulated_text"].lower())

    def test_escalation_candidate_preserving_protected_phrase_is_accepted(self):
        profile = _profile("escalation_phrase_keep")
        profile.add_word("requires", source="user_typed")
        profile.add_word("specific", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=1)
        original = "The reaction requires a specific activation energy to proceed."
        good = "The reaction needs the right activation energy to move forward."
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[good]):
            result = rf.reformulate(original, profile, settings)
        self.assertEqual(result["status"], "reformulated")
        self.assertEqual(result["changes"][0]["source"], "restructuring")
        self.assertIn("activation energy", result["reformulated_text"].lower())


class DuplicateWordRejectionTest(unittest.TestCase):
    """Phase 11 category 2 -- reject a substitution candidate that
    duplicates a word/stem already present elsewhere in the sentence
    (R10-038's "Solar"->"Renewable" next to "renewable energy",
    R10-060's "recessions"->"economies" next to "economic")."""

    def test_exact_duplicate_detected(self):
        tokens = ["Switch", "to", "renewable", "energy", "sources", "now", "."]
        self.assertTrue(rf._duplicates_sentence_word("renewable", tokens, exclude_index=0))

    def test_shared_stem_detected(self):
        # "economies" and "economic" share a Porter stem ("econom") despite
        # not being surface-identical -- the R10-060 case plain string
        # equality would miss.
        tokens = ["Economic", "downturns", "cause", "recessions", "."]
        self.assertTrue(rf._duplicates_sentence_word("economies", tokens, exclude_index=3))

    def test_unrelated_word_not_flagged(self):
        tokens = ["The", "cat", "sat", "on", "the", "mat", "."]
        self.assertFalse(rf._duplicates_sentence_word("dog", tokens, exclude_index=1))

    def test_stopword_recurrence_not_flagged(self):
        # "the" legitimately repeats in almost every sentence -- must not
        # be treated as a duplication.
        tokens = ["the", "cat", "sat", "on", "the", "mat", "."]
        self.assertFalse(rf._duplicates_sentence_word("the", tokens, exclude_index=4))


class BlockedSubstitutionPairTest(unittest.TestCase):
    """Phase 11 category 3 -- specific (original, replacement) pairs
    verified against their actual Phase 10 failure instances
    (eval/r10b_defective_enriched.json), not general antonyms or low-
    similarity matches (those are already caught elsewhere) but wrong-sense
    pairs that only observation could catch."""

    def test_known_bad_pair_blocked(self):
        # R10-091: "original" -> "new" reads as a near-opposite in context
        # but is not a WordNet-listed antonym, so is_known_antonym() misses
        # it -- exactly the gap this blocklist exists to close.
        self.assertTrue(sem.blocked_pair("original", "new"))
        self.assertFalse(sem.is_known_antonym("original", "new"))

    def test_unrelated_pair_not_blocked(self):
        self.assertFalse(sem.blocked_pair("original", "initial"))

    def test_blocked_pair_skipped_in_favor_of_next_candidate(self):
        profile = _profile("blocked_pair_wiring")
        profile.add_word("original", source="user_typed")
        fake_scored = [
            {"lemma": "new", "inflected": "new", "semantic_sim": 0.95,
             "freq_score": 0.9, "combined": 0.95, "accepted": True},
            {"lemma": "initial", "inflected": "initial", "semantic_sim": 0.9,
             "freq_score": 0.8, "combined": 0.9, "accepted": True},
        ]
        with mock.patch.object(rf, "_raw_candidates", return_value=["new", "initial"]), \
             mock.patch.object(rf.sem, "rank_candidates_contextually", return_value=fake_scored):
            result = rf.reformulate("This is the original document.", profile)
        self.assertEqual(result["status"], "reformulated")
        self.assertNotIn("new", result["reformulated_text"].lower())
        self.assertIn("initial", result["reformulated_text"].lower())


class NumberWordMismatchTest(unittest.TestCase):
    """Phase 11B (VALIDATION.md SS50) -- a generalizable rule rather than a
    one-off blocklist pair, since R10-127's "third"->"fourth" swap was
    global_sound-triggered (phonetic similarity), which will keep drawing
    near-miss number-word candidates for any number word a profile flags,
    not just this one pair."""

    def test_different_number_words_flagged(self):
        self.assertTrue(sem.is_number_word_mismatch("third", "fourth"))
        self.assertTrue(sem.is_number_word_mismatch("six", "sixteen"))

    def test_same_number_word_not_flagged(self):
        self.assertFalse(sem.is_number_word_mismatch("third", "third"))

    def test_non_number_words_not_flagged(self):
        self.assertFalse(sem.is_number_word_mismatch("dog", "cat"))
        self.assertFalse(sem.is_number_word_mismatch("third", "cat"))

    def test_number_word_mismatch_skipped_in_favor_of_next_candidate(self):
        profile = _profile("number_word_wiring")
        profile.add_word("third", source="user_typed")
        fake_scored = [
            {"lemma": "fourth", "inflected": "fourth", "semantic_sim": 0.95,
             "freq_score": 0.9, "combined": 0.95, "accepted": True},
            {"lemma": "third", "inflected": "3rd", "semantic_sim": 0.9,
             "freq_score": 0.8, "combined": 0.9, "accepted": True},
        ]
        with mock.patch.object(rf, "_raw_candidates", return_value=["fourth", "third"]), \
             mock.patch.object(rf.sem, "rank_candidates_contextually", return_value=fake_scored):
            result = rf.reformulate("He was the third of four children.", profile)
        self.assertEqual(result["status"], "reformulated")
        self.assertNotIn("fourth", result["reformulated_text"].lower())
        self.assertIn("3rd", result["reformulated_text"].lower())


class UnknownTokenRejectionTest(unittest.TestCase):
    """Phase 11B (VALIDATION.md SS50) -- nothing previously checked whether
    T5-generated escalation/phrase-tier output was made of real words.
    Reuses grammar.py's existing pyspellchecker-based infrastructure
    (previously input-side only, via sanitize_input()) -- these tests use
    the exact garbled tokens Phase 10B and Phase 11's own re-verification
    both found ("thermonuklear", "rockyer", "goodss")."""

    def test_garbled_token_detected(self):
        self.assertTrue(rf.has_unknown_tokens("The thermonuklear fusion process was described."))

    def test_clean_text_not_flagged(self):
        self.assertFalse(rf.has_unknown_tokens("The thermonuclear fusion process was described."))

    def test_proper_nouns_and_numbers_not_flagged(self):
        # _SPELL_SKIP_TAGS excludes NNP/NNPS/CD -- an unusual proper name or
        # a number must never trigger a false-positive refusal.
        self.assertFalse(rf.has_unknown_tokens("Zzyzxville has 4827 residents."))

    def test_escalation_candidate_with_garbled_token_is_rejected(self):
        profile = _profile("escalation_garbled_token")
        profile.add_word("requires", source="user_typed")
        profile.add_word("specific", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=1)
        original = "The reaction requires a specific amount of thermal energy to proceed."
        garbled = "The reaction needs a certain amount of thermonuklear energy to happen."
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[garbled]):
            result = rf.reformulate(original, profile, settings)
        self.assertEqual(result["status"], "could_not_safely_reformulate")

    def test_escalation_candidate_without_garbled_token_is_accepted(self):
        profile = _profile("escalation_clean_token")
        profile.add_word("requires", source="user_typed")
        profile.add_word("specific", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=1)
        original = "The reaction requires a specific amount of thermal energy to proceed."
        clean = "The reaction needs a certain amount of thermal energy to happen."
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[clean]):
            result = rf.reformulate(original, profile, settings)
        self.assertEqual(result["status"], "reformulated")


class EscalationDuplicateWordTest(unittest.TestCase):
    """Phase 11C (VALIDATION.md SS51) -- introduces_new_duplicate() is the
    escalation-tier counterpart to Phase 11's substitution-tier
    _duplicates_sentence_word(): a gap named "concrete, evidenced" after
    Phase 11 (VALIDATION.md SS48 FUTURE WORK) but dropped before Phase
    11B's plan, closed here. Integration tests mock the NLI/grammar
    gates to "pass" so only the duplicate check under test can reject."""

    def test_new_duplicate_introduced_is_detected(self):
        orig = "the design, construction, and maintenance of roads"
        cand = "the design, design and maintenance of roads"
        self.assertTrue(rf.introduces_new_duplicate(orig, cand))

    def test_preexisting_repetition_not_flagged(self):
        # R10-024's own original legitimately says "force" twice -- a
        # candidate that keeps the SAME count must not be rejected.
        orig = "a body exerts a force on a second body, which exerts a force back"
        cand = "a body applies a force to a second body, which applies a force back"
        self.assertFalse(rf.introduces_new_duplicate(orig, cand))

    def test_ordinary_paraphrase_not_flagged(self):
        # An earlier version of this function flagged ANY word new to the
        # candidate (not just an increased repeat of an existing one),
        # which would have rejected almost every legitimate paraphrase --
        # caught by this exact test before being trusted.
        orig = "The reaction requires a specific amount of thermal energy to proceed."
        cand = "The reaction needs a certain amount of thermal energy to happen."
        self.assertFalse(rf.introduces_new_duplicate(orig, cand))

    def test_hyphenated_root_duplication_detected(self):
        orig = "A star is a luminous spheroid of plasma held together by self-gravity."
        cand = "A star is a luminous spheroid of plasma surrounded by self-gravitational gravity."
        self.assertTrue(rf.introduces_new_duplicate(orig, cand))

    def test_escalation_candidate_with_new_duplicate_is_rejected(self):
        profile = _profile("escalation_new_duplicate")
        profile.add_word("professional", source="user_typed")
        profile.add_word("naturally", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=1)
        original = ("Civil engineering is a professional discipline that deals with the "
                    "design, construction, and maintenance of the naturally built environment.")
        duped = ("Civil engineering is a technical discipline that deals with the "
                 "design, design and maintenance of the built environment.")
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[duped]), \
             mock.patch.object(rf.sem, "logical_consistency_check", return_value=None), \
             mock.patch.object(rf.sem, "grammar_issue_count", return_value=0):
            result = rf.reformulate(original, profile, settings)
        self.assertEqual(result["status"], "could_not_safely_reformulate")

    def test_escalation_candidate_without_new_duplicate_is_accepted(self):
        profile = _profile("escalation_no_new_duplicate")
        profile.add_word("professional", source="user_typed")
        profile.add_word("naturally", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=1)
        original = ("Civil engineering is a professional discipline that deals with the "
                    "design, construction, and maintenance of the naturally built environment.")
        clean = ("Civil engineering is a technical discipline that deals with the "
                 "design, construction, and upkeep of the built environment.")
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[clean]), \
             mock.patch.object(rf.sem, "logical_consistency_check", return_value=None), \
             mock.patch.object(rf.sem, "grammar_issue_count", return_value=0):
            result = rf.reformulate(original, profile, settings)
        self.assertEqual(result["status"], "reformulated")


class EscalationNLITest(unittest.TestCase):
    """Phase 11C (VALIDATION.md SS51) -- ports the NLI entailment gate
    already designed, built, and validated in R45/R46
    (semantic.logical_consistency_check(), cross-encoder/nli-deberta-v3-
    xsmall) from the experimental _try_escalation_v3()/reformulate_v2()
    path into production's _try_escalation()/_try_phrase_replacement(),
    and adds one whole-sentence check on _try_substitution()'s final
    assembled output per R45's own recommendation (VALIDATION.md SS36.3).
    R10-005 ("reabsorbed"->"eliminated") is the direct evidence this
    closes a gap is_known_antonym() structurally cannot: not a WordNet
    antonym pair, so the existing antonym check passes it cleanly."""

    def test_real_contradiction_detected(self):
        # Grounding check with the real model (already proven loaded in
        # this environment), not just the mocked wiring tests below.
        result = sem.logical_consistency_check(
            "The train arrives at the station at nine.",
            "The train departs from the station at nine.",
        )
        self.assertIsNotNone(result)
        self.assertTrue(result["contradiction"])

    def test_real_entailment_not_flagged(self):
        result = sem.logical_consistency_check(
            "The train arrives at the station at nine.",
            "The train comes to the station at nine.",
        )
        self.assertIsNotNone(result)
        self.assertFalse(result["contradiction"])

    def test_escalation_candidate_with_contradiction_is_rejected(self):
        profile = _profile("escalation_nli_contradiction")
        profile.add_word("requires", source="user_typed")
        profile.add_word("specific", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=1)
        original = "The reaction requires a specific amount of thermal energy to proceed."
        reversed_ = "The reaction releases a certain amount of thermal energy as it ends."
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[reversed_]), \
             mock.patch.object(rf.sem, "logical_consistency_check",
                                return_value={"fwd_label": "contradiction", "rev_label": "contradiction", "contradiction": True}), \
             mock.patch.object(rf.sem, "grammar_issue_count", return_value=0):
            result = rf.reformulate(original, profile, settings)
        self.assertEqual(result["status"], "could_not_safely_reformulate")

    def test_escalation_candidate_without_contradiction_is_accepted(self):
        profile = _profile("escalation_nli_clean")
        profile.add_word("requires", source="user_typed")
        profile.add_word("specific", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=1)
        original = "The reaction requires a specific amount of thermal energy to proceed."
        clean = "The reaction needs a certain amount of thermal energy to happen."
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[clean]), \
             mock.patch.object(rf.sem, "logical_consistency_check",
                                return_value={"fwd_label": "entailment", "rev_label": "entailment", "contradiction": False}), \
             mock.patch.object(rf.sem, "grammar_issue_count", return_value=0):
            result = rf.reformulate(original, profile, settings)
        self.assertEqual(result["status"], "reformulated")

    def test_substitution_final_sentence_contradiction_forces_escalation(self):
        # R10-005/R10-101 are both substitution-tier -- this checks the
        # ONE whole-sentence gate on _try_substitution()'s final assembled
        # output (not per-candidate), so a contradiction only visible once
        # every position is resolved still gets caught, and the sentence
        # correctly falls through to escalation rather than shipping it.
        profile = _profile("substitution_final_nli")
        profile.add_word("original", source="user_typed")
        fake_scored = [{"lemma": "new", "inflected": "new", "semantic_sim": 0.95,
                         "freq_score": 0.9, "combined": 0.95, "accepted": True}]
        with mock.patch.object(rf, "_raw_candidates", return_value=["new"]), \
             mock.patch.object(rf.sem, "rank_candidates_contextually", return_value=fake_scored), \
             mock.patch.object(rf.sem, "logical_consistency_check",
                                return_value={"fwd_label": "contradiction", "rev_label": "contradiction", "contradiction": True}), \
             mock.patch.object(rf.rephrase, "generate_candidates", return_value=[]):
            result = rf.reformulate("This is the original document.", profile)
        self.assertEqual(result["status"], "could_not_safely_reformulate")


class EscalationGrammarTest(unittest.TestCase):
    """Phase 11C (VALIDATION.md SS51) -- ports grammar_issue_count()
    (LanguageTool, already a dependency, already validated in R45 at
    ~25% recall on the GRAMMAR-labeled defect class -- real but partial,
    confirmed directly against this phase's own evidence before wiring,
    not assumed) from reformulate_v2()'s reported-only validation pass
    into an actual reject gate in production's _try_escalation()/
    _try_phrase_replacement()."""

    def test_real_grammar_error_detected(self):
        # Grounding check with the real LanguageTool instance (confirmed
        # loadable in this environment as this phase's own Step 0).
        self.assertGreater(sem.grammar_issue_count("She go to the store yesterday and buys many apple."), 0)

    def test_real_clean_sentence_not_flagged(self):
        self.assertEqual(sem.grammar_issue_count("She went to the store yesterday and bought many apples."), 0)

    def test_escalation_candidate_with_grammar_error_is_rejected(self):
        profile = _profile("escalation_grammar_error")
        profile.add_word("requires", source="user_typed")
        profile.add_word("specific", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=1)
        original = "The reaction requires a specific amount of thermal energy to proceed."
        broken = "The reaction need a certain amounts of thermal energy for to happen."
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[broken]), \
             mock.patch.object(rf.sem, "logical_consistency_check", return_value=None), \
             mock.patch.object(rf.sem, "grammar_issue_count", return_value=2):
            result = rf.reformulate(original, profile, settings)
        self.assertEqual(result["status"], "could_not_safely_reformulate")

    def test_escalation_candidate_without_grammar_error_is_accepted(self):
        profile = _profile("escalation_grammar_clean")
        profile.add_word("requires", source="user_typed")
        profile.add_word("specific", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=1)
        original = "The reaction requires a specific amount of thermal energy to proceed."
        clean = "The reaction needs a certain amount of thermal energy to happen."
        with mock.patch.object(rf.rephrase, "generate_candidates", return_value=[clean]), \
             mock.patch.object(rf.sem, "logical_consistency_check", return_value=None), \
             mock.patch.object(rf.sem, "grammar_issue_count", return_value=0):
            result = rf.reformulate(original, profile, settings)
        self.assertEqual(result["status"], "reformulated")


class MassNounSubstitutionTest(unittest.TestCase):
    """Phase 11C (VALIDATION.md SS51) -- no countability/mass-noun signal
    existed anywhere in this codebase; a single blocklisted pair
    (professor->faculty, Phase 11B) was confirmed to just get bypassed by
    the next bad candidate (R10-073: moved to "teacher"). A small curated
    closed set (_MASS_NOUNS), same shape as _NUMBER_WORDS, catches the
    countable-to-mass-noun shape directly."""

    def test_known_mass_noun_substitution_flagged(self):
        self.assertTrue(sem.is_mass_noun_substitution("recipe", "cooking"))
        self.assertTrue(sem.is_mass_noun_substitution("factory", "manufacturing"))
        self.assertTrue(sem.is_mass_noun_substitution("nutrient", "nutrition"))

    def test_unrelated_pair_not_flagged(self):
        self.assertFalse(sem.is_mass_noun_substitution("recipe", "dish"))

    def test_mass_to_mass_not_flagged(self):
        # Guards specifically against countable->mass, not mass->mass --
        # a legitimate simplification between two already-uncountable
        # words must not be blocked by this check.
        self.assertFalse(sem.is_mass_noun_substitution("faculty", "cooking"))

    def test_mass_noun_substitution_skipped_in_favor_of_next_candidate(self):
        profile = _profile("mass_noun_wiring")
        profile.add_word("recipe", source="user_typed")
        fake_scored = [
            {"lemma": "cooking", "inflected": "cooking", "semantic_sim": 0.9,
             "freq_score": 0.85, "combined": 0.9, "accepted": True},
            {"lemma": "dish", "inflected": "dish", "semantic_sim": 0.85,
             "freq_score": 0.8, "combined": 0.85, "accepted": True},
        ]
        with mock.patch.object(rf, "_raw_candidates", return_value=["cooking", "dish"]), \
             mock.patch.object(rf.sem, "rank_candidates_contextually", return_value=fake_scored):
            result = rf.reformulate("This recipe calls for less sugar.", profile)
        self.assertEqual(result["status"], "reformulated")
        self.assertNotIn("cooking", result["reformulated_text"].lower())
        self.assertIn("dish", result["reformulated_text"].lower())


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
        #
        # Tests the candidate-generation step directly (local context window
        # -> different candidate set per occurrence) rather than end-to-end
        # pipeline output: under DISABLE_DATAMUSE=1 (this module's own
        # determinism setting), WordNet's only candidates for "runs" in the
        # "jogs three miles" sense are poor (e.g. "pass"), which Phase 11C's
        # sentence-level NLI check on the final assembled substitution
        # (VALIDATION.md SS51) correctly rejects -- a real quality gate,
        # not a false positive, but downstream of what this test is
        # actually regression-testing (that the two occurrences get
        # DIFFERENT candidate pools at all, not whether the pipeline's
        # other gates later accept them).
        engine = engine_module.SynonymEngine()
        sentence = "He runs the company every morning before he runs in the park."
        tokens = word_tokenize(sentence)
        tags = pos_tag(tokens)
        positions = [i for i, (w, _) in enumerate(tags) if w.lower() == "runs"]
        self.assertEqual(len(positions), 2)
        candidate_sets = []
        for i in positions:
            ctx = rf._local_context_window(tokens, i)
            candidate_sets.append(set(rf._raw_candidates(engine, "run", tags[i][1], "runs", 10, context=ctx)))
        self.assertNotEqual(candidate_sets[0], candidate_sets[1])


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
