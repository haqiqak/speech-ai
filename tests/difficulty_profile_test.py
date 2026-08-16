"""
tests/difficulty_profile_test.py — Stage 4A foundation tests.

Covers: add/remove/dedup for sounds/words/phrases, persistence across a
fresh DifficultyProfile.load() (simulating an app restart), legacy
phoneme_profile migration/seeding, pronunciation derivation (including OOV),
the legacy-mirror write into phoneme_profile that keeps the existing
reformulation pipeline fed, and text-edge-case normalization (punctuation,
capitalization, contractions, numbers, proper nouns).

    DISABLE_DATAMUSE=1 python tests/difficulty_profile_test.py
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ["DISABLE_DATAMUSE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import user_store
from difficulty_profile import DifficultyProfile, extract_candidate_words
import phonetic

ROOT = Path(__file__).resolve().parent.parent
TEMP_USER = "codex_diffprofile_tmp"
TEMP_PATH = ROOT / "users" / f"{TEMP_USER}.json"


def _fresh_user():
    if TEMP_PATH.exists():
        TEMP_PATH.unlink()
    ok, msg = user_store.register_user(TEMP_USER, "speech")
    assert ok, msg


def _cleanup():
    if TEMP_PATH.exists():
        TEMP_PATH.unlink()


class AddRemoveDedupTest(unittest.TestCase):
    def setUp(self):
        _fresh_user()

    def tearDown(self):
        _cleanup()

    def test_add_word_sound_phrase(self):
        p = DifficultyProfile.load(TEMP_USER)
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
        p = DifficultyProfile.load(TEMP_USER)
        p.add_word("Thoroughly")
        entry, status = p.add_word("thoroughly")
        self.assertEqual(status, "duplicate")
        self.assertEqual(len(p.words), 1)

    def test_duplicate_sound_by_arpabet_not_spelling(self):
        """'c' and 'k' are spelled differently but both normalize to /K/ —
        should dedup as the SAME sound, per RESEARCH.md's pronunciation-not-
        spelling finding."""
        p = DifficultyProfile.load(TEMP_USER)
        _, status1 = p.add_sound("c")
        _, status2 = p.add_sound("k")
        self.assertEqual(status1, "added")
        self.assertEqual(status2, "duplicate")
        self.assertEqual(len(p.sounds), 1)

    def test_word_and_sound_are_independent_categories(self):
        """Flagging the word 'three' must NOT auto-flag /TH/ as a difficult
        sound — the two categories are explicitly not the same claim."""
        p = DifficultyProfile.load(TEMP_USER)
        p.add_word("three")
        self.assertEqual(len(p.words), 1)
        self.assertEqual(len(p.sounds), 0)

    def test_remove_entry(self):
        p = DifficultyProfile.load(TEMP_USER)
        entry, _ = p.add_word("particular")
        removed = p.remove("word", entry.normalized)
        self.assertTrue(removed)
        self.assertEqual(len(p.words), 0)

    def test_remove_nonexistent_entry_is_safe(self):
        p = DifficultyProfile.load(TEMP_USER)
        removed = p.remove("word", "nonexistent")
        self.assertFalse(removed)

    def test_empty_input_rejected(self):
        p = DifficultyProfile.load(TEMP_USER)
        _, status = p.add_word("   ")
        self.assertEqual(status, "empty")
        _, status = p.add_sound("")
        self.assertEqual(status, "empty")
        _, status = p.add_phrase("  ,.!  ")
        self.assertEqual(status, "empty")


class TextEdgeCaseTest(unittest.TestCase):
    def setUp(self):
        _fresh_user()

    def tearDown(self):
        _cleanup()

    def test_punctuation_adjacent_word_stripped(self):
        p = DifficultyProfile.load(TEMP_USER)
        entry, status = p.add_word("results.")
        self.assertEqual(status, "added")
        self.assertEqual(entry.normalized, "results")

    def test_capitalization_normalized_but_original_preserved(self):
        p = DifficultyProfile.load(TEMP_USER)
        entry, _ = p.add_word("Thoroughly")
        self.assertEqual(entry.value, "Thoroughly")  # display form preserved
        self.assertEqual(entry.normalized, "thoroughly")  # dedup form lowercased

    def test_contraction_preserved(self):
        p = DifficultyProfile.load(TEMP_USER)
        entry, status = p.add_word("don't")
        self.assertEqual(status, "added")
        self.assertEqual(entry.normalized, "don't")

    def test_number_allowed(self):
        p = DifficultyProfile.load(TEMP_USER)
        entry, status = p.add_word("2024")
        self.assertEqual(status, "added")

    def test_proper_noun_allowed(self):
        p = DifficultyProfile.load(TEMP_USER)
        entry, status = p.add_word("Alice")
        self.assertEqual(status, "added")
        self.assertEqual(entry.normalized, "alice")

    def test_beginning_end_whitespace_stripped(self):
        p = DifficultyProfile.load(TEMP_USER)
        entry, status = p.add_phrase("  through the research  ")
        self.assertEqual(status, "added")
        self.assertEqual(entry.normalized, "through the research")

    def test_multi_word_selection_stored_as_phrase_verbatim(self):
        p = DifficultyProfile.load(TEMP_USER)
        entry, _ = p.add_phrase("I thoroughly reviewed")
        self.assertEqual(entry.normalized, "i thoroughly reviewed")


class PronunciationDerivationTest(unittest.TestCase):
    def setUp(self):
        _fresh_user()

    def tearDown(self):
        _cleanup()

    def test_known_word_gets_pronunciation(self):
        p = DifficultyProfile.load(TEMP_USER)
        entry, _ = p.add_word("three")
        self.assertIsNotNone(entry.pronunciation)
        self.assertGreater(len(entry.pronunciation), 0)
        # no stress digits should leak through
        for phone in entry.pronunciation:
            self.assertFalse(any(ch.isdigit() for ch in phone))

    def test_oov_word_gets_no_fabricated_pronunciation(self):
        p = DifficultyProfile.load(TEMP_USER)
        entry, _ = p.add_word("zxqvblorp")
        self.assertIsNone(entry.pronunciation)

    def test_phrase_and_sound_never_get_pronunciation_field(self):
        p = DifficultyProfile.load(TEMP_USER)
        sound_entry, _ = p.add_sound("str")
        phrase_entry, _ = p.add_phrase("through the research")
        self.assertIsNone(sound_entry.pronunciation)
        self.assertIsNone(phrase_entry.pronunciation)

    def test_full_pronunciation_direct_oov_vs_known(self):
        self.assertIsNone(phonetic.full_pronunciation("zxqvblorp"))
        self.assertIsNotNone(phonetic.full_pronunciation("present"))


class PersistenceTest(unittest.TestCase):
    def setUp(self):
        _fresh_user()

    def tearDown(self):
        _cleanup()

    def test_persists_across_reload(self):
        p = DifficultyProfile.load(TEMP_USER)
        p.add_word("thoroughly")
        p.add_sound("str")
        p.add_phrase("through the research")
        p.save()

        # Simulate an app restart: fresh object, load from disk only.
        reloaded = DifficultyProfile.load(TEMP_USER)
        self.assertEqual(reloaded.word_values(), ["thoroughly"])
        self.assertEqual(reloaded.sound_values(), ["str"])
        self.assertEqual(reloaded.phrase_values(), ["through the research"])

    def test_legacy_mirror_kept_in_sync_for_existing_reformulation_pipeline(self):
        p = DifficultyProfile.load(TEMP_USER)
        p.add_word("particular")
        p.add_sound("pr")
        p.save()

        legacy = user_store.load_profile(TEMP_USER)
        self.assertIn("particular", legacy["blocked_words"])
        self.assertIn("pr", legacy["stutter_patterns"])

    def test_removal_updates_legacy_mirror_too(self):
        p = DifficultyProfile.load(TEMP_USER)
        entry, _ = p.add_word("particular")
        p.save()
        p.remove("word", entry.normalized)
        p.save()

        legacy = user_store.load_profile(TEMP_USER)
        self.assertNotIn("particular", legacy["blocked_words"])

    def test_existing_legacy_profile_is_migrated_not_lost(self):
        """A user who only ever used the OLD stutter_patterns/blocked_words
        UI must see that data show up in the NEW profile, not an empty one."""
        user_store.save_profile(
            TEMP_USER, patterns=["str", "pr"], blocked=["particular", "statistics"],
        )
        p = DifficultyProfile.load(TEMP_USER)
        self.assertEqual(set(p.sound_values()), {"str", "pr"})
        self.assertEqual(set(p.word_values()), {"particular", "statistics"})

    def test_migration_happens_once_not_every_load(self):
        user_store.save_profile(TEMP_USER, patterns=["str"], blocked=[])
        p1 = DifficultyProfile.load(TEMP_USER)
        p1.save()  # writes difficulty_profile for the first time
        p1.remove("sound", "S T R")
        p1.save()  # removal should stick — no re-migration should resurrect it

        p2 = DifficultyProfile.load(TEMP_USER)
        self.assertEqual(p2.sound_values(), [])


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
