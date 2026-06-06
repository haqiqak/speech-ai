"""
grammar.py  —  Input sanitizer + morphological adaptation + semantic rewriting.

Pipeline
────────
  sanitize_input()    fix contractions, capitalisation, spacing, punctuation
  is_sentence()       detect sentence vs bare word list
  SentenceRewriter    POS-tag → protected-position check → synonym candidates
                      → SBERT contextual ranking → inflect → rebuild
  rebuild_with_choices()  reassemble with user's per-word choice

Dependencies: nltk, pyinflect, semantic.py  (fully offline except SBERT model
download on first run)
"""

import re
import nltk
from nltk import pos_tag, word_tokenize
from nltk.corpus import wordnet as wn
from nltk.stem import WordNetLemmatizer
import pyinflect

import semantic as sem

for _pkg in ("averaged_perceptron_tagger_eng", "punkt_tab", "wordnet", "omw-1.4"):
    nltk.download(_pkg, quiet=True)

_lemmatizer = WordNetLemmatizer()

# ── POS constants ─────────────────────────────────────────────────────────────
_SUBSTITUTABLE = {
    "NN", "NNS",
    "VB", "VBD", "VBG", "VBN", "VBP", "VBZ",
    "JJ", "JJR", "JJS",
    "RB", "RBR", "RBS",
}

def _wn_pos(tag: str):
    if tag.startswith("J"): return wn.ADJ
    if tag.startswith("V"): return wn.VERB
    if tag.startswith("N"): return wn.NOUN
    if tag.startswith("R"): return wn.ADV
    return None

# Protected single words (auxiliaries, pronouns, determiners, prepositions)
_STOP = {
    "be","is","are","was","were","am","been","being",
    "have","has","had","do","does","did",
    "will","would","could","should","may","might","shall","can","must","need","dare",
    "to","of","in","on","at","by","for","with","into","from","about","over","under",
    "it","its","this","that","these","those",
    "i","me","my","we","us","our","you","your","he","him","his","she","her","they","them","their",
    "a","an","the",
    "and","but","or","nor","so","yet","both",
    "not","no","never",
    "just","also","even","still","already","again","always","often","sometimes",
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Input sanitizer
# ─────────────────────────────────────────────────────────────────────────────
_CONTRACTIONS = {
    r"\bdont\b":     "don't",
    r"\bdoesnt\b":   "doesn't",
    r"\bcant\b":     "can't",
    r"\bwont\b":     "won't",
    r"\bisnt\b":     "isn't",
    r"\barent\b":    "aren't",
    r"\bwasnt\b":    "wasn't",
    r"\bwerent\b":   "weren't",
    r"\bcouldnt\b":  "couldn't",
    r"\bwouldnt\b":  "wouldn't",
    r"\bshouldnt\b": "shouldn't",
    r"\bhavent\b":   "haven't",
    r"\bhasnt\b":    "hasn't",
    r"\bhadnt\b":    "hadn't",
    r"\bdidnt\b":    "didn't",
    r"\bim\b":       "I'm",
    r"\bive\b":      "I've",
    r"\bill\b":      "I'll",
    r"\bthats\b":    "that's",
    r"\bwhats\b":    "what's",
    r"\bwhos\b":     "who's",
    r"\bits\b":      "it's",
    r"\btheyre\b":   "they're",
    r"\btheyve\b":   "they've",
    r"\btheyll\b":   "they'll",
    r"\byoure\b":    "you're",
    r"\byouve\b":    "you've",
    r"\byoull\b":    "you'll",
}

def sanitize_input(text: str) -> tuple[str, list[dict]]:
    """
    Rule-based grammar fixes applied BEFORE the synonym pipeline.
    Returns (corrected_text, list_of_fix_dicts).
    """
    fixes: list[dict] = []
    result = text.strip()

    for pattern, replacement in _CONTRACTIONS.items():
        match = re.search(pattern, result, re.IGNORECASE)
        if match:
            original = match.group()
            if original.replace("'", "").lower() == replacement.replace("'", "").lower():
                fixes.append({"type": "contraction", "original": original,
                               "corrected": replacement,
                               "description": f'Added missing apostrophe: "{original}" → "{replacement}"'})
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    new = re.sub(r"\b(i)\b", "I", result)
    if new != result:
        fixes.append({"type": "pronoun_case", "original": "i", "corrected": "I",
                      "description": 'Capitalised pronoun "i" → "I"'})
        result = new

    if result and result[0].islower():
        fixes.append({"type": "capitalization", "original": result[0],
                      "corrected": result[0].upper(),
                      "description": f'Capitalised first letter: "{result[0]}" → "{result[0].upper()}"'})
        result = result[0].upper() + result[1:]

    if re.search(r" {2,}", result):
        fixes.append({"type": "spacing", "original": "  ", "corrected": " ",
                      "description": "Removed extra spaces"})
        result = re.sub(r" {2,}", " ", result)

    stripped = result.rstrip()
    if stripped and stripped[-1] not in ".!?":
        fixes.append({"type": "punctuation", "original": "", "corrected": ".",
                      "description": "Added missing full stop at end of sentence"})
        result = stripped + "."

    return result, fixes


# ─────────────────────────────────────────────────────────────────────────────
# 2. Sentence detection
# ─────────────────────────────────────────────────────────────────────────────
def is_sentence(text: str) -> bool:
    tokens = word_tokenize(text)
    if len(tokens) <= 2:
        return False
    if "," in text and all(len(t.split()) == 1 for t in text.split(",")):
        return False
    tags = pos_tag(tokens)
    has_verb = any(t.startswith("VB") for _, t in tags)
    return has_verb or len(tokens) > 3


# ─────────────────────────────────────────────────────────────────────────────
# 3. Morphological helpers
# ─────────────────────────────────────────────────────────────────────────────
def lemmatize(word: str, pos_tag_str: str) -> str:
    wn_p = _wn_pos(pos_tag_str)
    if wn_p:
        return _lemmatizer.lemmatize(word.lower(), pos=wn_p)
    return word.lower()

def inflect(lemma: str, target_tag: str) -> str:
    result = pyinflect.getInflection(lemma, target_tag)
    if result:
        return result[0]
    if target_tag == "NNS":
        return lemma + "s"
    return lemma

def _preserve_case(original: str, replacement: str) -> str:
    if original.isupper():
        return replacement.upper()
    if original[0].isupper():
        return replacement.capitalize()
    return replacement.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Sentence rewriter  (now SBERT-aware)
# ─────────────────────────────────────────────────────────────────────────────
class SentenceRewriter:
    """
    Rewrites a (sanitized) sentence by substituting content words with
    semantically validated synonyms, inflected correctly.

    rewrite() returns full scoring metadata per word so the UI can show
    semantic similarity scores, accepted/rejected candidates, etc.
    """

    def __init__(self, synonym_engine):
        self.engine = synonym_engine

    def _raw_candidates(
        self, lemma: str, pos_tag_str: str, original_word: str, top_k: int
    ) -> list[str]:
        """
        Get frequency-ranked lemma candidates from engine, filtered by:
        - same broad POS (WordNet check)
        - single token only
        - prefer -ly forms for -ly adverbs
        """
        all_syns = self.engine.get_synonyms(lemma, top_k=top_k * 2).get(lemma, [])
        wn_p = _wn_pos(pos_tag_str)
        prefer_ly = pos_tag_str.startswith("RB") and original_word.lower().endswith("ly")

        filtered = []
        for cand in all_syns:
            if cand in (lemma, original_word.lower()):
                continue
            if " " in cand:
                continue
            if wn_p and not wn.synsets(cand, pos=wn_p):
                continue
            filtered.append(cand)

        if prefer_ly:
            ly   = [c for c in filtered if c.endswith("ly")]
            rest = [c for c in filtered if not c.endswith("ly")]
            filtered = ly + rest

        return filtered[:top_k]

    def rewrite(self, sentence: str, top_k: int = 10) -> dict:
        """
        Full pipeline:
          1. Tokenise + POS tag
          2. Identify protected positions (phrases + stop words)
          3. For each substitutable word:
             a. Get raw candidates (engine)
             b. Build inflected forms
             c. SBERT-rank contextually (semantic.py)
             d. Pick best accepted candidate
          4. Rebuild sentence
          5. Grammar notes

        Returns dict with full scoring metadata per substitution.
        """
        tokens = word_tokenize(sentence)
        tags   = pos_tag(tokens)

        # Protected token positions
        phrase_protected = sem.protected_positions(tokens)

        new_tokens    = list(tokens)
        substitutions = []
        skipped       = []

        for i, (word, tag) in enumerate(tags):
            lower = word.lower()
            if not re.match(r"[a-z]", lower):
                continue
            if tag not in _SUBSTITUTABLE:
                continue
            if lower in _STOP:
                continue
            if i in phrase_protected:        # protected phrase member
                continue

            base       = lemmatize(word, tag)
            raw_cands  = self._raw_candidates(base, tag, word, top_k=top_k)

            if not raw_cands:
                skipped.append(word)
                continue

            # Build inflected form map  {lemma → inflected_surface}
            inflected_map: dict[str, str] = {}
            for lemma in raw_cands:
                inf = inflect(lemma, tag)
                inf = _preserve_case(word, inf)
                inflected_map[lemma] = inf

            # SBERT contextual ranking
            scored = sem.rank_candidates_contextually(
                original_sentence = sentence,
                word_to_replace   = word,
                token_index       = i,
                tokens            = list(new_tokens),   # use current state of rebuilt tokens
                candidates        = raw_cands,
                inflected_forms   = inflected_map,
            )

            # Best accepted candidate
            accepted = [s for s in scored if s["accepted"]]
            if not accepted:
                skipped.append(word)
                continue

            best        = accepted[0]
            new_tokens[i] = best["inflected"]

            substitutions.append({
                "original_word": word,
                "lemma":         base,
                "tag":           tag,
                "position":      i,
                "chosen":        best["inflected"],
                "chosen_lemma":  best["lemma"],
                # Full scoring data for UI display
                "scored":        scored,          # all candidates with scores
                # Convenience: just the accepted lemma list for the dropdown
                "candidates":    [s["lemma"] for s in scored if s["accepted"]],
                "all_candidates": [s["lemma"] for s in scored],
                "sbert_active":  sem._sbert_ok,
            })

        rewritten     = _detokenize(new_tokens)
        grammar_notes = _grammar_notes(sentence, rewritten, substitutions)

        return {
            "original":      sentence,
            "rewritten":     rewritten,
            "substitutions": substitutions,
            "skipped":       skipped,
            "grammar_notes": grammar_notes,
            "sbert_active":  sem._sbert_ok,
        }

    def rebuild_with_choices(
        self,
        original_sentence: str,
        substitutions: list[dict],
        user_choices: dict[int, str],   # {position → chosen_lemma}
    ) -> str:
        tokens     = word_tokenize(original_sentence)
        new_tokens = list(tokens)
        for sub in substitutions:
            pos   = sub["position"]
            lemma = user_choices.get(pos, sub["chosen_lemma"])
            inf   = inflect(lemma, sub["tag"])
            inf   = _preserve_case(sub["original_word"], inf)
            new_tokens[pos] = inf
        return _detokenize(new_tokens)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _detokenize(tokens: list[str]) -> str:
    result = ""
    for i, tok in enumerate(tokens):
        if i == 0:
            result = tok
        elif tok in (".", ",", "!", "?", ";", ":", "'s", "n't", "'re",
                     "'ve", "'ll", "'d", "'m"):
            result += tok
        elif result and result[-1] == "'":
            result += tok
        else:
            result += " " + tok
    return result


def _grammar_notes(original: str, rewritten: str, subs: list[dict]) -> list[str]:
    notes = []
    if not subs:
        return notes
    rewr_tags = dict(pos_tag(word_tokenize(rewritten)))
    for sub in subs:
        if sub["tag"].startswith("VB"):
            actual = rewr_tags.get(sub["chosen"].lower()) or rewr_tags.get(sub["chosen"])
            if actual and actual != sub["tag"]:
                notes.append(
                    f'"{sub["chosen"]}" re-tagged as {actual} '
                    f'(expected {sub["tag"]}) — check verb agreement.'
                )
    if subs and not notes:
        notes.append("Grammar check passed — all substitutions correctly inflected.")
    return notes
