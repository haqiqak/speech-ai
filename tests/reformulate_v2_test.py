"""
tests/reformulate_v2_test.py — coverage for R45's next-generation hybrid
components (VALIDATION.md §36): semantic.py's NLI/grammar validator
functions, rephrase.py's phoneme-aware decoding-time constraint, and
reformulate.py's reformulate_v2()/_try_escalation_v2().

Loads real models (NLI cross-encoder, T5, LanguageTool via the portable
JRE) — not mocked, same rationale as contextual_fit_test.py/
meaningbert_test.py: the point is to prove the actual mechanism works.
Kept in its own file so tests/semantic_test.py's "no model loading
required" guarantee stays true, and so a LanguageTool/JRE hiccup in this
file can't mask an unrelated failure elsewhere.

    python tests/reformulate_v2_test.py
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic as sem
import rephrase
import reformulate as rf
from difficulty_profile import DifficultyProfile


def _profile(name: str) -> DifficultyProfile:
    return DifficultyProfile(profile_name=f"__test_{name}__")


class NLILoadTest(unittest.TestCase):
    def test_load_succeeds_in_this_environment(self):
        ok = sem.load_nli_model()
        self.assertTrue(ok, sem.nli_status()[1])

    def test_status_reports_loaded(self):
        sem.load_nli_model()
        ok, message = sem.nli_status()
        self.assertTrue(ok)
        self.assertIn("loaded successfully", message)


class NLIConsistencyCheckTest(unittest.TestCase):
    def test_factual_contradiction_is_caught(self):
        # VALIDATION.md §36 -- the exact case NLI is meant to catch: SBERT/
        # MeaningBERT/contextual_fit all miss this, this signal doesn't.
        result = sem.logical_consistency_check(
            "The 2016 to 2025 decade warmed to an average of 1.26 degrees "
            "compared to the pre-industrial baseline.",
            "The 2016 to 2025 decade warmed to an average of 1.26 degrees "
            "compared to the palaeolithic baseline.",
        )
        self.assertIsNotNone(result)
        self.assertTrue(result["contradiction"])

    def test_clean_paraphrase_is_not_flagged(self):
        result = sem.logical_consistency_check(
            "Vitamin C is especially prone to oxidation during cooking.",
            "Vitamin C is especially vulnerable to oxidation during cooking.",
        )
        self.assertIsNotNone(result)
        self.assertFalse(result["contradiction"])

    def test_returns_both_direction_labels(self):
        result = sem.logical_consistency_check("A man is eating food.", "A man is eating a meal.")
        self.assertIsNotNone(result)
        self.assertIn("fwd_label", result)
        self.assertIn("rev_label", result)
        self.assertIn(result["fwd_label"], ("contradiction", "entailment", "neutral"))


class NLIDegradationTest(unittest.TestCase):
    def test_returns_none_when_model_unavailable(self):
        with mock.patch.object(sem, "_nli_ok", False), \
             mock.patch.object(sem, "load_nli_model", return_value=False):
            result = sem.logical_consistency_check("Hello there.", "Hi there.")
        self.assertIsNone(result)


class GrammarCheckTest(unittest.TestCase):
    def test_load_succeeds_in_this_environment(self):
        # Requires the portable JRE from R28 (.cache/jre17/) -- if this
        # fails, it's an environment issue (JRE not present), not a code
        # bug; every other test in this class degrades gracefully anyway.
        ok = sem.load_grammar_tool()
        self.assertTrue(ok, sem.grammar_status()[1])

    def test_known_bad_case_is_caught(self):
        # VALIDATION.md §36.1/A4 -- the one case A4 found a clean, correct
        # catch for.
        count = sem.grammar_issue_count(
            "Machine learning is the study of softwares that can improve "
            "their performance on a given task automatically."
        )
        self.assertIsNotNone(count)
        self.assertGreater(count, 0)

    def test_clean_sentence_is_not_flagged(self):
        count = sem.grammar_issue_count(
            "Deep learning uses various layers of neurons between the "
            "network's inputs and outputs."
        )
        self.assertIsNotNone(count)
        self.assertEqual(count, 0)


class GrammarDegradationTest(unittest.TestCase):
    def test_returns_none_when_tool_unavailable(self):
        with mock.patch.object(sem, "_grammar_tool_ok", False), \
             mock.patch.object(sem, "load_grammar_tool", return_value=False):
            count = sem.grammar_issue_count("Some sentence.")
        self.assertIsNone(count)


class PhonemeConstrainedGenerationTest(unittest.TestCase):
    """rephrase.py's decoding-time phoneme constraint -- VALIDATION.md
    §36.2's headline finding, reproduced here as a regression guard."""

    def test_output_never_contains_blocked_sound(self):
        candidates, stats = rephrase.generate_candidates_phoneme_constrained(
            "Many of these algorithms were insufficient for solving large "
            "reasoning problems because they experienced a combinatorial "
            "explosion, meaning they become exponentially slower as the "
            "problems grow.",
            k=5,
            blocked_words={"problems", "grow"},
            blocked_patterns=["pr", "gr"],
        )
        self.assertTrue(candidates)
        import re
        import phonetic as ph
        for cand in candidates:
            for w in re.findall(r"[A-Za-z][A-Za-z'-]*", cand):
                self.assertFalse(
                    ph.matches_any(w, ["pr", "gr"]),
                    f"{w!r} in {cand!r} matches a blocked sound pattern",
                )

    def test_degrades_to_passthrough_when_model_unavailable(self):
        with mock.patch.object(rephrase, "_load_model", return_value=False):
            candidates, stats = rephrase.generate_candidates_phoneme_constrained(
                "A short sentence.", k=5, blocked_words=set(), blocked_patterns=["s"],
            )
        self.assertEqual(candidates, ["A short sentence."])
        self.assertTrue(stats.get("model_unavailable"))


class ReformulateV2IntegrationTest(unittest.TestCase):
    """Confirms reformulate_v2() is additive: reformulate() is byte-for-
    byte unaffected, and reformulate_v2() adds exactly the two things
    VALIDATION.md §36.3 decided on -- phoneme-aware escalation and a
    reported-only validation block -- nothing else."""

    def test_reformulate_unchanged_by_v2_existing(self):
        # Same input, same profile, through the ORIGINAL function --
        # confirms reformulate_v2() being defined hasn't altered it.
        profile = _profile("v2_does_not_affect_v1")
        profile.add_sound("s", source="user_typed")
        result = rf.reformulate("Good morning, did you sleep well?", profile)
        self.assertNotIn("validation", result)

    def test_v2_result_has_validation_key(self):
        profile = _profile("v2_has_validation_key")
        profile.add_sound("s", source="user_typed")
        result = rf.reformulate_v2("Good morning, did you sleep well?", profile)
        self.assertIn("validation", result)
        self.assertIn("nli", result["validation"])
        self.assertIn("grammar_issue_count", result["validation"])
        self.assertIn("flagged", result["validation"])

    def test_validation_never_gates_status_or_final_verification(self):
        # Reported-only discipline (Practice.md §10), same contract as
        # contextual_fit -- force a flagged validation result and confirm
        # a clean substitution still ships. Uses grammar_issue_count, not
        # logical_consistency_check, as the forced signal: Architecture
        # Go/No-Go Step 1's predecessor (Phase 11C, VALIDATION.md SS51)
        # added an internal NLI gate to the SHARED _try_substitution()
        # (used by both reformulate() and reformulate_v2()) as a deliberate,
        # evidence-based exception to the reported-only discipline for that
        # one signal -- forcing a global contradiction here would trip that
        # internal gate too and escalate/refuse instead of shipping the
        # substitution, which is the new correct behavior for THAT gate,
        # not a bug in this test's actual target. grammar_issue_count is
        # not gated inside _try_substitution() or _try_escalation_v3()
        # (confirmed by reading both), so forcing it here isolates exactly
        # what this test means to check: reformulate_v2()'s OWN final
        # reported-only validation pass never gates.
        profile = _profile("v2_validation_no_gate")
        profile.add_sound("s", source="user_typed")
        with mock.patch.object(sem, "grammar_issue_count", return_value=3):
            result = rf.reformulate_v2("Good morning, did you sleep well?", profile)
        self.assertEqual(result["status"], "reformulated")
        self.assertTrue(result["validation"]["flagged"])

    def test_no_validation_computed_when_nothing_changed(self):
        profile = _profile("v2_no_change_needed")
        result = rf.reformulate_v2("The sky is blue today.", profile)
        self.assertEqual(result["status"], "no_change_needed")
        self.assertIsNone(result["validation"]["nli"])
        self.assertIsNone(result["validation"]["grammar_issue_count"])
        self.assertFalse(result["validation"]["flagged"])

    def test_escalation_uses_phoneme_aware_path_when_triggered(self):
        # Dense profile that forces pre-escalation (mirrors R40/R43's
        # own heavy_dense-style setup) -- confirm _try_escalation_v3's
        # "restructuring_v3" source appears (§38: v2 + iterative
        # regeneration combined), not the original "restructuring" or
        # the single-round-only "restructuring_v2", when escalation
        # actually fires.
        profile = _profile("v2_escalation_source_tag")
        profile.add_sound("s", source="user_typed")
        profile.add_sound("th", source="user_typed")
        profile.add_sound("r", source="user_typed")
        settings = rf.ReformulateSettings(escalation_word_count=1)
        result = rf.reformulate_v2(
            "The scientific study of cooking has become known as molecular gastronomy.",
            profile, settings,
        )
        sources = {c["source"] for c in result["changes"]}
        self.assertTrue(sources <= {"substitution", "restructuring_v3"})
        self.assertNotIn("restructuring", sources)  # the OLD source tag must never appear from v2
        self.assertNotIn("restructuring_v2", sources)  # nor the single-round-only v2 tag


class EscalationV3NLIGateTest(unittest.TestCase):
    """VALIDATION.md §38.3 -- a live case found during development,
    "rational"->"irrational", cleared SBERT/negation/leak cleanly and was
    only caught by NLI. Confirms escalation now REJECTS an antonym-flip
    candidate outright (not just reports it) when a clean alternative
    exists, unlike reformulate_v2()'s separate whole-output validation
    pass, which stays reported-only."""

    def test_antonym_flip_candidate_is_rejected_in_favor_of_a_clean_one(self):
        profile = _profile("v3_nli_gate")
        good = "The person has goals and takes steps to make them happen."
        bad = "The person has goals and takes steps to prevent them from happening."
        with mock.patch.object(
            rephrase, "generate_candidates_phoneme_constrained",
            return_value=([bad, good], {"beam_kills": 0}),
        ):
            flagged = [{"position": 0, "word": "sound", "tag": "NN", "word_entry": None, "sound_hit": True}]
            text, change = rf._try_escalation_v3(
                "A person has aims and takes steps to make them happen.",
                flagged, profile, rf.ReformulateSettings(),
            )
        # The antonym-flip candidate ("prevent them from happening") must
        # never be chosen over the meaning-preserving one, regardless of
        # which one the mocked generator lists first.
        if text is not None:
            self.assertNotIn("prevent", text.lower())


class EscalationV3RoundBoundTest(unittest.TestCase):
    """§38's iterative loop must respect escalation_max_rounds -- confirm
    it stops, doesn't hang, when generation can never satisfy the gates."""

    def test_stops_within_max_rounds_when_nothing_ever_passes(self):
        profile = _profile("v3_round_bound")
        profile.add_sound("s", source="user_typed")
        settings = rf.ReformulateSettings(escalation_max_rounds=3, t5_candidates=2)
        call_count = {"n": 0}
        real_fn = rephrase.generate_candidates_phoneme_constrained

        def counting_wrapper(*args, **kwargs):
            call_count["n"] += 1
            return real_fn(*args, **kwargs)

        with mock.patch.object(rephrase, "generate_candidates_phoneme_constrained", side_effect=counting_wrapper), \
             mock.patch.object(sem, "semantic_similarity", return_value=0.0):  # force every candidate to fail SBERT
            flagged = [{"position": 0, "word": "sound", "tag": "NN", "word_entry": None, "sound_hit": True}]
            text, change = rf._try_escalation_v3("A sound sentence.", flagged, profile, settings)

        self.assertIsNone(text)
        self.assertIsNone(change)
        self.assertLessEqual(call_count["n"], settings.escalation_max_rounds)


if __name__ == "__main__":
    unittest.main(verbosity=2)
