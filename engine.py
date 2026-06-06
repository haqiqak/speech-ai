"""
SynonymEngine v3 — multi-source synonym retrieval with POS-filtered WordNet.

Root fix in this version
─────────────────────────
The original engine called wn.synsets(word) with NO pos filter, so it pulled
in synsets from ALL parts of speech.  For 'stress' (used as a NOUN) it was
also crawling stress.v.01 and stress.v.02 whose hypernyms include 'say',
'show', 'evince', 'pronounce', 'articulate' — clearly wrong-POS words that
then survived the SBERT filter because they appear in plausible sentences.

Fix: _wordnet_synonyms() now accepts an optional wn_pos argument.  When the
caller (SentenceRewriter in grammar.py) knows the POS tag of the token being
substituted, it passes the WordNet POS constant so that ONLY same-POS synsets
are crawled.  Multi-word-expression candidates are still stripped out.

Sources (unchanged):
  1. WordNet (NLTK) — enriched extraction: synset lemmas + similar_tos +
     also_sees + attributes + hypernyms (same-POS only).
  2. Datamuse API  — rel_syn (synonyms) + ml (meaning-like).

Ranking (unchanged):
  Zipf frequency (wordfreq) — words sorted by how commonly they appear in
  real-world English corpora so the most natural replacement comes first.

Quality filters (unchanged):
  - Multi-word phrases removed (no spaces allowed in candidates)
  - Hyphenated compounds kept (they inflect fine, e.g. "well-known")
  - Words with Zipf < 2.0 dropped (too rare / archaic)
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

    # ── Source 1: POS-filtered WordNet ──────────────────────────────────────
    def _wordnet_synonyms(self, word: str, wn_pos=None) -> set[str]:
        """
        Extract synonyms from WordNet, restricted to the given POS.

        wn_pos: one of wn.NOUN, wn.VERB, wn.ADJ, wn.ADV, or None.
                When None, all senses are crawled (word-mode lookup).
                When provided, ONLY synsets matching that POS are visited
                and hypernym chains are also restricted to the same POS —
                this is the key fix that prevents cross-POS contamination.
        """
        syns: set[str] = set()
        synsets = wn.synsets(word, pos=wn_pos)   # <── KEY: POS filter here

        for synset in synsets:
            # Direct lemmas of this sense
            for lemma in synset.lemmas():
                syns.add(lemma.name().replace("_", " ").lower())

            # Similar adjectives / also-sees (huge boost for JJ)
            for related in (*synset.similar_tos(), *synset.also_sees()):
                for lemma in related.lemmas():
                    syns.add(lemma.name().replace("_", " ").lower())

            # Attributes (adjective ↔ noun links) — skip when POS-locked to avoid drift
            if wn_pos is None:
                for attr in synset.attributes():
                    for lemma in attr.lemmas():
                        syns.add(lemma.name().replace("_", " ").lower())

            # Hypernyms — same-POS restriction prevents cross-POS bleeding
            for hyper in synset.hypernyms():
                if wn_pos is None or hyper.pos() == wn_pos:   # <── KEY: same-POS check
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
    def _collect(self, word: str, wn_pos=None) -> set[str]:
        """
        Gather candidates from all sources.
        wn_pos filters WordNet to a specific POS (prevents cross-POS leak).
        Datamuse is unfiltered (it has its own relevance ranking).
        """
        word = word.strip().lower()
        synonyms: set[str] = set()
        synonyms |= self._wordnet_synonyms(word, wn_pos=wn_pos)
        synonyms |= self._datamuse_synonyms(word)

        # Remove the query word and clearly junk entries
        synonyms.discard(word)
        synonyms -= _JUNK

        # Keep only single-token candidates (no spaces).
        # Multi-word phrases like "with child" or "go through" don't inflect
        # cleanly.  Hyphenated compounds (e.g. "well-known") are fine.
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
    def get_synonyms(self, query: str, top_k: int = 15, wn_pos=None) -> dict[str, list[str]]:
        """
        Accept a single word OR multiple words (space/comma-separated).
        Returns dict: word → ranked synonym list (length ≤ top_k).

        wn_pos: WordNet POS constant (wn.NOUN, wn.VERB, wn.ADJ, wn.ADV)
                to restrict WordNet lookups.  Pass None for word-mode (all senses).
        """
        tokens = [t.strip() for t in re.split(r"[\s,]+", query) if t.strip()]
        results: dict[str, list[str]] = {}
        for word in tokens:
            raw = self._collect(word, wn_pos=wn_pos)
            ranked = self._rank(list(raw))
            results[word] = ranked[:top_k]
        return results
