"""
tests/difficulty_profile_test.py — Stage 4A foundation tests, extended in
the Stage 4A refinement (2026-08-16) for word-specific sound patterns and
the single-default-profile storage layer.

Covers: add/remove/dedup for sounds/words/phrases, persistence across a
fresh DifficultyProfile.load() (simulating an app restart), legacy
phoneme_profile migration/seeding, pronunciation derivation (including OOV),
text-edge-case normalization (punctuation, capitalization, contractions,
numbers, proper nouns), and — new this pass — word-specific problem-sound
patterns: setting/clearing them, that they never create a global sound
entry unless explicitly promoted, and that they're validated against the
word's own real pronunciation.

    DISABLE_DATAMUSE=1 python tests/difficulty_profile_test.py
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ["DISABLE_DATAMUSE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import profile_store
from difficulty_profile import DifficultyProfile, extract_candidate_words, record_feedback, undo_feedback
import phonetic

ROOT = Path(__file__).resolve().parent.parent
TEMP_PROFILE = "codex_diffprofile_tmp"
TEMP_PATH = ROOT / "users" / f"{TEMP_PROFILE}.json"


def _fresh_profile():
    if TEMP_PATH.exists():
        TEMP_PATH.unlink()


def _cleanup():
    if TEMP_PATH.exists():
        TEMP_PATH.unlink()


class AddRemoveDedupTest(unittest.TestCase):
    def setUp(self):
        _fresh_profile()

    def tearDown(self):
        _cleanup()

    def test_add_word_sound_phrase(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, status = p.add_word("thoroughly")
        self.assertEqual(status, "added")
        self.assertEqual(entry.value, "thoroughly")
        self.assertEqual(entry.category, "word")

        entry, status = p.add_sound("str")
        self.assertEqual(status, "added")
        self.assertEqual(entry.normalized, "S T R")

        entry, status = p.add_phrase("through the research")
        self.assertEqual(status, "added")
        self.assertEqual(entry.normalized, "through the research")

        self.assertEqual(len(p.words), 1)
        self.assertEqual(len(p.sounds), 1)
        self.assertEqual(len(p.phrases), 1)

    def test_duplicate_word_is_rejected_case_insensitive(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        p.add_word("Thoroughly")
        entry, status = p.add_word("thoroughly")
        self.assertEqual(status, "duplicate")
        self.assertEqual(len(p.words), 1)

    def test_duplicate_sound_by_arpabet_not_spelling(self):
        """'c' and 'k' are spelled differently but both normalize to /K/ —
        should dedup as the SAME sound, per RESEARCH.md's pronunciation-not-
        spelling finding."""
        p = DifficultyProfile.load(TEMP_PROFILE)
        _, status1 = p.add_sound("c")
        _, status2 = p.add_sound("k")
        self.assertEqual(status1, "added")
        self.assertEqual(status2, "duplicate")
        self.assertEqual(len(p.sounds), 1)

    def test_word_and_sound_are_independent_categories(self):
        """Flagging the word 'three' must NOT auto-flag /TH/ as a difficult
        sound — the two categories are explicitly not the same claim."""
        p = DifficultyProfile.load(TEMP_PROFILE)
        p.add_word("three")
        self.assertEqual(len(p.words), 1)
        self.assertEqual(len(p.sounds), 0)

    def test_remove_entry(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, _ = p.add_word("particular")
        removed = p.remove("word", entry.normalized)
        self.assertTrue(removed)
        self.assertEqual(len(p.words), 0)

    def test_remove_nonexistent_entry_is_safe(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        removed = p.remove("word", "nonexistent")
        self.assertFalse(removed)

    def test_empty_input_rejected(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        _, status = p.add_word("   ")
        self.assertEqual(status, "empty")
        _, status = p.add_sound("")
        self.assertEqual(status, "empty")
        _, status = p.add_phrase("  ,.!  ")
        self.assertEqual(status, "empty")


class TextEdgeCaseTest(unittest.TestCase):
    def setUp(self):
        _fresh_profile()

    def tearDown(self):
        _cleanup()

    def test_punctuation_adjacent_word_stripped(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, status = p.add_word("results.")
        self.assertEqual(status, "added")
        self.assertEqual(entry.normalized, "results")

    def test_capitalization_normalized_but_original_preserved(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, _ = p.add_word("Thoroughly")
        self.assertEqual(entry.value, "Thoroughly")  # display form preserved
        self.assertEqual(entry.normalized, "thoroughly")  # dedup form lowercased

    def test_contraction_preserved(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, status = p.add_word("don't")
        self.assertEqual(status, "added")
        self.assertEqual(entry.normalized, "don't")

    def test_number_allowed(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, status = p.add_word("2024")
        self.assertEqual(status, "added")

    def test_proper_noun_allowed(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, status = p.add_word("Alice")
        self.assertEqual(status, "added")
        self.assertEqual(entry.normalized, "alice")

    def test_beginning_end_whitespace_stripped(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, status = p.add_phrase("  through the research  ")
        self.assertEqual(status, "added")
        self.assertEqual(entry.normalized, "through the research")

    def test_multi_word_selection_stored_as_phrase_verbatim(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, _ = p.add_phrase("I thoroughly reviewed")
        self.assertEqual(entry.normalized, "i thoroughly reviewed")


class PronunciationDerivationTest(unittest.TestCase):
    def setUp(self):
        _fresh_profile()

    def tearDown(self):
        _cleanup()

    def test_known_word_gets_pronunciation(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, _ = p.add_word("three")
        self.assertIsNotNone(entry.pronunciation)
        self.assertGreater(len(entry.pronunciation), 0)
        # no stress digits should leak through
        for phone in entry.pronunciation:
            self.assertFalse(any(ch.isdigit() for ch in phone))

    def test_oov_word_gets_no_fabricated_pronunciation(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, _ = p.add_word("zxqvblorp")
        self.assertIsNone(entry.pronunciation)

    def test_phrase_and_sound_never_get_pronunciation_field(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        sound_entry, _ = p.add_sound("str")
        phrase_entry, _ = p.add_phrase("through the research")
        self.assertIsNone(sound_entry.pronunciation)
        self.assertIsNone(phrase_entry.pronunciation)

    def test_full_pronunciation_direct_oov_vs_known(self):
        self.assertIsNone(phonetic.full_pronunciation("zxqvblorp"))
        self.assertIsNotNone(phonetic.full_pronunciation("present"))

    def test_friendly_phone_label_covers_common_phones(self):
        label = phonetic.friendly_phone_label("TH")
        self.assertIn("TH", label)
        self.assertIn("think", label)
        # unknown code degrades to the bare code rather than raising
        self.assertEqual(phonetic.friendly_phone_label("ZZZ"), "ZZZ")

    def test_variant_count_detects_heteronyms(self):
        # 'read' (present/past) and 'the' both have real CMU alternates;
        # 'three' does not. OOV words report 0, not 1.
        self.assertGreater(phonetic.pronunciation_variant_count("read"), 1)
        self.assertEqual(phonetic.pronunciation_variant_count("three"), 1)
        self.assertEqual(phonetic.pronunciation_variant_count("zxqvblorp"), 0)


class AmbiguityAuditTest(unittest.TestCase):
    """Findings from the post-Stage-4A-refinement audit (2026-08-16): two
    real, silent ambiguities the foundation must not hide. Both are now
    recorded as explicit `meta` flags rather than left undetectable."""

    def setUp(self):
        _fresh_profile()

    def tearDown(self):
        _cleanup()

    def test_heteronym_word_flags_alternate_pronunciation_ambiguity(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, _ = p.add_word("read")
        self.assertTrue(entry.meta.get("has_alternate_pronunciations"))

    def test_unambiguous_word_does_not_get_the_flag(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, _ = p.add_word("three")
        self.assertNotIn("has_alternate_pronunciations", entry.meta)

    def test_ambiguity_flag_persists_across_reload(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        p.add_word("read")
        p.save()
        reloaded = DifficultyProfile.load(TEMP_PROFILE)
        self.assertTrue(reloaded.find_word("read").meta.get("has_alternate_pronunciations"))

    def test_promoted_sound_with_clean_roundtrip_has_no_warning(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, status = p.add_sound_from_phones(["TH", "R"])
        self.assertEqual(status, "added")
        self.assertNotIn("legacy_bridge_unreliable", entry.meta)

    def test_promoted_sound_with_lossy_roundtrip_is_flagged(self):
        """ZH has no English onset spelling that phonetic.normalize_pattern
        can decode back correctly (it degrades to Z + HH) — this must be a
        recorded, visible fact, not a silent gap in the legacy bridge that
        feeds the existing (unmodified) reformulation pipeline."""
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, status = p.add_sound_from_phones(["ZH"])
        self.assertEqual(status, "added")
        self.assertTrue(entry.meta.get("legacy_bridge_unreliable"))


class WordSpecificPatternTest(unittest.TestCase):
    """The Stage 4A refinement's central new concept: a word being flagged
    difficult must not automatically make its phonemes globally difficult;
    the user may OPTIONALLY narrow down to a specific sound/pattern within
    that one word, and separately, EXPLICITLY promote it to a global sound."""

    def setUp(self):
        _fresh_profile()

    def tearDown(self):
        _cleanup()

    def test_set_pattern_on_flagged_word(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, _ = p.add_word("three")  # pronunciation: TH, R, IY
        ok = p.set_word_pattern("three", ["TH", "R"])
        self.assertTrue(ok)
        self.assertEqual(p.find_word("three").problem_phones, ("TH", "R"))

    def test_setting_pattern_does_not_create_global_sound(self):
        """The central requirement: 'three' -> difficult word with a
        TH+R pattern must NOT produce global sounds entries for TH or R
        unless the user explicitly promotes them."""
        p = DifficultyProfile.load(TEMP_PROFILE)
        p.add_word("three")
        p.set_word_pattern("three", ["TH", "R"])
        self.assertEqual(len(p.sounds), 0)

    def test_pattern_must_be_subset_of_real_pronunciation(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        p.add_word("three")  # TH, R, IY — no 'ZZ' phone exists in this word
        ok = p.set_word_pattern("three", ["ZZ"])
        self.assertFalse(ok)
        self.assertIsNone(p.find_word("three").problem_phones)

    def test_pattern_requires_word_already_flagged(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        ok = p.set_word_pattern("nonexistent", ["TH"])
        self.assertFalse(ok)

    def test_pattern_impossible_for_oov_word(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        p.add_word("zxqvblorp")
        ok = p.set_word_pattern("zxqvblorp", ["TH"])
        self.assertFalse(ok)

    def test_clear_pattern(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        p.add_word("three")
        p.set_word_pattern("three", ["TH"])
        cleared = p.clear_word_pattern("three")
        self.assertTrue(cleared)
        self.assertIsNone(p.find_word("three").problem_phones)

    def test_clear_pattern_when_none_set_is_a_safe_no_op(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        p.add_word("three")
        self.assertFalse(p.clear_word_pattern("three"))

    def test_leaving_word_as_plain_difficulty_without_a_pattern(self):
        """The task's explicit 'or simply leave it as a word-level
        difficulty' case — a word entry with no pattern set is valid,
        complete, and not an error state."""
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, status = p.add_word("three")
        self.assertEqual(status, "added")
        self.assertIsNone(entry.problem_phones)

    def test_explicit_promotion_to_global_sound(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        p.add_word("three")
        p.set_word_pattern("three", ["TH", "R"])
        entry, status = p.add_sound_from_phones(["TH", "R"])
        self.assertEqual(status, "added")
        self.assertEqual(entry.normalized, "TH R")
        self.assertEqual(len(p.sounds), 1)

    def test_promoted_sound_dedups_against_typed_sound(self):
        """A sound promoted from a word pattern and one typed by hand that
        normalize to the same ARPAbet key must be treated as the same
        declared difficulty, not two."""
        p = DifficultyProfile.load(TEMP_PROFILE)
        p.add_sound("thr")  # -> TH R via grapheme rules
        p.add_word("three")
        p.set_word_pattern("three", ["TH", "R"])
        _, status = p.add_sound_from_phones(["TH", "R"])
        self.assertEqual(status, "duplicate")
        self.assertEqual(len(p.sounds), 1)

    def test_pattern_persists_across_reload(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        p.add_word("three")
        p.set_word_pattern("three", ["TH", "R"])
        p.save()

        reloaded = DifficultyProfile.load(TEMP_PROFILE)
        self.assertEqual(reloaded.find_word("three").problem_phones, ("TH", "R"))
        self.assertEqual(len(reloaded.sounds), 0)  # still not globally promoted

    def test_word_difficult_and_pattern_specific_stored_distinctly(self):
        """Directly exercises the task's own worked example: 'three' is
        difficult, and TH+R is problematic specifically in this word — the
        stored representation must reflect exactly that distinction."""
        p = DifficultyProfile.load(TEMP_PROFILE)
        p.add_word("three")
        p.set_word_pattern("three", ["TH", "R"])
        p.save()

        raw = profile_store.load_difficulty_profile(TEMP_PROFILE)
        self.assertEqual(len(raw["words"]), 1)
        self.assertEqual(raw["words"][0]["value"], "three")
        self.assertEqual(raw["words"][0]["problem_phones"], ["TH", "R"])
        self.assertEqual(raw["sounds"], [])  # no global sound entries at all


class PersistenceTest(unittest.TestCase):
    def setUp(self):
        _fresh_profile()

    def tearDown(self):
        _cleanup()

    def test_persists_across_reload(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        p.add_word("thoroughly")
        p.add_sound("str")
        p.add_phrase("through the research")
        p.save()

        # Simulate an app restart: fresh object, load from disk only.
        reloaded = DifficultyProfile.load(TEMP_PROFILE)
        self.assertEqual(reloaded.word_values(), ["thoroughly"])
        self.assertEqual(reloaded.sound_values(), ["str"])
        self.assertEqual(reloaded.phrase_values(), ["through the research"])

    def test_existing_legacy_profile_is_migrated_not_lost(self):
        """A profile that only ever had the OLD phoneme_profile fields
        (pre-Stage-4A) must see that data show up in the new profile, not
        an empty one."""
        TEMP_PATH.parent.mkdir(exist_ok=True)
        import json
        with open(TEMP_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"phoneme_profile": {"stutter_patterns": ["str", "pr"],
                                      "blocked_words": ["particular", "statistics"]}},
                f,
            )
        p = DifficultyProfile.load(TEMP_PROFILE)
        self.assertEqual(set(p.sound_values()), {"str", "pr"})
        self.assertEqual(set(p.word_values()), {"particular", "statistics"})

    def test_migration_happens_once_not_every_load(self):
        TEMP_PATH.parent.mkdir(exist_ok=True)
        import json
        with open(TEMP_PATH, "w", encoding="utf-8") as f:
            json.dump({"phoneme_profile": {"stutter_patterns": ["str"], "blocked_words": []}}, f)

        p1 = DifficultyProfile.load(TEMP_PROFILE)
        p1.save()  # writes difficulty_profile for the first time
        p1.remove("sound", "S T R")
        p1.save()  # removal should stick — no re-migration should resurrect it

        p2 = DifficultyProfile.load(TEMP_PROFILE)
        self.assertEqual(p2.sound_values(), [])

    def test_no_account_fields_survive_a_save(self):
        """A Stage-4A-era record with now-obsolete password_hash/username
        fields gets a clean record on the next save — no auth-era fields
        carried forward."""
        TEMP_PATH.parent.mkdir(exist_ok=True)
        import json
        with open(TEMP_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "username": TEMP_PROFILE,
                    "password_hash": "deadbeef",
                    "difficulty_profile": {"sounds": [], "words": [], "phrases": []},
                    "preferences": {},
                },
                f,
            )
        p = DifficultyProfile.load(TEMP_PROFILE)
        p.add_word("particular")
        p.save()

        with open(TEMP_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self.assertNotIn("password_hash", raw)
        self.assertNotIn("username", raw)
        self.assertNotIn("phoneme_profile", raw)


class FeedbackTest(unittest.TestCase):
    """ROADMAP.md R9 — record_feedback()/undo_feedback()."""

    def setUp(self):
        _fresh_profile()

    def tearDown(self):
        _cleanup()

    def test_record_feedback_increments_kept_and_reverted_independently(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, _ = p.add_word("particular")
        record_feedback(entry, kept=True)
        record_feedback(entry, kept=True)
        record_feedback(entry, kept=False)
        self.assertEqual(entry.meta["feedback"], {"kept": 2, "reverted": 1})

    def test_undo_feedback_decrements_the_right_counter(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, _ = p.add_word("particular")
        record_feedback(entry, kept=True)
        record_feedback(entry, kept=False)
        undo_feedback(entry, kept=True)
        self.assertEqual(entry.meta["feedback"], {"kept": 0, "reverted": 1})

    def test_undo_feedback_never_goes_negative(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, _ = p.add_word("particular")
        undo_feedback(entry, kept=True)
        undo_feedback(entry, kept=False)
        self.assertEqual(entry.meta["feedback"], {"kept": 0, "reverted": 0})

    def test_feedback_is_per_entry_not_shared(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        word_entry, _ = p.add_word("particular")
        sound_entry, _ = p.add_sound("str")
        record_feedback(word_entry, kept=True)
        self.assertEqual(word_entry.meta.get("feedback"), {"kept": 1, "reverted": 0})
        self.assertIsNone(sound_entry.meta.get("feedback"))

    def test_feedback_persists_across_reload(self):
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, _ = p.add_word("particular")
        record_feedback(entry, kept=True)
        record_feedback(entry, kept=False)
        record_feedback(entry, kept=False)
        p.save()

        reloaded = DifficultyProfile.load(TEMP_PROFILE)
        reloaded_entry = reloaded.find_word("particular")
        self.assertEqual(reloaded_entry.meta["feedback"], {"kept": 1, "reverted": 2})

    def test_recording_feedback_does_not_touch_declared_sounds_words_phrases(self):
        """The whole point of storing this in meta rather than mutating
        sounds/words/phrases directly: recording feedback must never add,
        remove, or reweight a declared entry — only annotate it."""
        p = DifficultyProfile.load(TEMP_PROFILE)
        entry, _ = p.add_word("particular")
        p.add_sound("str")
        p.add_phrase("through the research")
        before = (list(p.word_values()), list(p.sound_values()), list(p.phrase_values()))
        record_feedback(entry, kept=True)
        record_feedback(entry, kept=False)
        after = (list(p.word_values()), list(p.sound_values()), list(p.phrase_values()))
        self.assertEqual(before, after)


class CandidateWordExtractionTest(unittest.TestCase):
    def test_unique_lowercased_ordered(self):
        words = extract_candidate_words("I thoroughly reviewed the research and thoroughly enjoyed it.")
        self.assertEqual(words[0], "i")
        self.assertIn("thoroughly", words)
        self.assertEqual(words.count("thoroughly"), 1)

    def test_handles_empty_and_punctuation_only(self):
        self.assertEqual(extract_candidate_words(""), [])
        self.assertEqual(extract_candidate_words("... , !"), [])

    def test_contraction_and_hyphenation(self):
        words = extract_candidate_words("I don't like well-known facts.")
        self.assertIn("don't", words)
        self.assertIn("well-known", words)


if __name__ == "__main__":
    unittest.main()
