"""
SynonymEngine v2 — multi-source synonym retrieval with frequency-based ranking.

Sources:
  1. WordNet (NLTK) — enriched extraction: synset lemmas + similar_tos +
     also_sees + attributes + hypernyms.  Dramatically improves coverage
     for adjectives (beautiful, happy, etc.) that have sparse direct synsets.
  2. Datamuse API  — rel_syn (synonyms) + ml (meaning-like).
     Both endpoints queried and merged for maximum breadth.

Ranking:
  Zipf frequency (wordfreq) — words are sorted by how commonly they appear
  in real-world English corpora so the most natural replacement comes first.

Quality filters:
  - Multi-word phrases with 3+ tokens removed (too awkward as substitutes)
  - Hyphenated compounds kept (they often inflect fine, e.g. "well-known")
  - Candidates that share no WordNet synset with the query are deprioritised
    but NOT removed (Datamuse surface forms are still useful)
"""

import re
import requests
import nltk
from nltk.corpus import wordnet as wn
from wordfreq import zipf_frequency

nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)

# Tokens we always strip from candidate lists
_JUNK = {
    "be", "have", "do", "make", "get",   # too generic
}


class SynonymEngine:
    DATAMUSE_TIMEOUT = 4

    def __init__(self, language: str = "en"):
        self.language = language

    # ── Source 1: enriched WordNet ──────────────────────────────────────────
    def _wordnet_synonyms(self, word: str) -> set[str]:
        syns: set[str] = set()
        for synset in wn.synsets(word):
            # Direct lemmas of every sense
            for lemma in synset.lemmas():
                syns.add(lemma.name().replace("_", " ").lower())
            # Similar adjectives / also-sees (huge boost for JJ)
            for related in (*synset.similar_tos(), *synset.also_sees()):
                for lemma in related.lemmas():
                    syns.add(lemma.name().replace("_", " ").lower())
            # Attributes (adjective ↔ noun links)
            for attr in synset.attributes():
                for lemma in attr.lemmas():
                    syns.add(lemma.name().replace("_", " ").lower())
            # Hypernyms — one level up gives broader but still relevant terms
            for hyper in synset.hypernyms():
                for lemma in hyper.lemmas():
                    syns.add(lemma.name().replace("_", " ").lower())
        return syns

    # ── Source 2: Datamuse (synonyms + meaning-like) ────────────────────────
    def _datamuse_synonyms(self, word: str) -> set[str]:
        syns: set[str] = set()
        for endpoint in (f"rel_syn={word}", f"ml={word}&max=15"):
            try:
                url = f"https://api.datamuse.com/words?{endpoint}"
                data = requests.get(url, timeout=self.DATAMUSE_TIMEOUT).json()
                syns |= {item["word"].lower() for item in data}
            except Exception:
                pass
        return syns

    # ── Collection & cleaning ───────────────────────────────────────────────
    def _collect(self, word: str) -> set[str]:
        word = word.strip().lower()
        synonyms: set[str] = set()
        synonyms |= self._wordnet_synonyms(word)
        synonyms |= self._datamuse_synonyms(word)

        # Remove the query word and clearly junk entries
        synonyms.discard(word)
        synonyms -= _JUNK

        # Keep only single-token candidates (no spaces).
        # Multi-word phrases like "with child" or "go through" don't inflect
        # cleanly. Hyphenated compounds (e.g. "well-known") are fine.
        synonyms = {s for s in synonyms if s and " " not in s}

        # Drop very rare/archaic words (Zipf < 2.0)
        synonyms = {s for s in synonyms if zipf_frequency(s, self.language) >= 2.0}

        return synonyms

    # ── Ranking ─────────────────────────────────────────────────────────────
    def _rank(self, words: list[str]) -> list[str]:
        """Sort by Zipf frequency — higher = more natural in everyday English."""
        return sorted(
            words,
            key=lambda w: zipf_frequency(w, self.language),
            reverse=True,
        )

    # ── Public API ──────────────────────────────────────────────────────────
    def get_synonyms(self, query: str, top_k: int = 15) -> dict[str, list[str]]:
        """
        Accept a single word OR multiple words (space/comma-separated).
        Returns dict: word → ranked synonym list (length ≤ top_k).
        """
        tokens = [t.strip() for t in re.split(r"[\s,]+", query) if t.strip()]
        results: dict[str, list[str]] = {}
        for word in tokens:
            raw = self._collect(word)
            ranked = self._rank(list(raw))
            results[word] = ranked[:top_k]
        return results
