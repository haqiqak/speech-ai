"""
grammar.py  —  Input sanitizer + morphological adaptation + semantic rewriting.

Pipeline
────────
  sanitize_input()    Comprehensive grammar correction:
                        • contractions (dont → don't)
                        • pronoun case (i → I)
                        • capitalisation
                        • spacing & punctuation
                        • tense correction (I eat yesterday → I ate yesterday)
                        • subject-verb agreement (He go → He goes)
                        • auxiliary verb forms (I am go → I am going)
                        • double negation, common errors

  is_sentence()       Detect sentence vs bare word list
  SentenceRewriter    POS-tag → protected-position check → synonym candidates
                      → SBERT contextual ranking → inflect → rebuild
  rebuild_with_choices()  Reassemble with user's per-word choice

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

# ── Past tense markers ────────────────────────────────────────────────────────
# Words that signal past tense context (adverbs, time expressions)
_PAST_MARKERS = {
    "yesterday", "ago", "previously", "formerly", "once", "earlier",
    "last", "before", "already", "since", "lately", "recently",
    "back", "then", "afterwards", "afterward",
}
# Phrases that signal past tense
_PAST_PHRASES = [
    r"\blast\s+\w+\b",          # last week, last year, last night
    r"\b\d+\s+\w+\s+ago\b",     # 3 days ago, 2 weeks ago
    r"\bin\s+\d{4}\b",          # in 1990, in 2020
    r"\byesterday\b",
]

# Words that signal present tense (to avoid over-correcting)
_PRESENT_MARKERS = {
    "now", "today", "currently", "nowadays", "always", "usually",
    "often", "sometimes", "generally", "typically",
}

# 3rd person singular subjects (for subject-verb agreement)
_THIRD_PERSON_SING = {"he", "she", "it", "this", "that", "one"}

# ─────────────────────────────────────────────────────────────────────────────
# 1. Input sanitizer (comprehensive grammar correction)
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

# Common wrong-word substitutions and spelling errors
_WORD_FIXES = {
    r"\bgonna\b":   "going to",
    r"\bwanna\b":   "want to",
    r"\bgotta\b":   "got to",
    r"\bkinda\b":   "kind of",
    r"\bsorta\b":   "sort of",
    r"\bdunno\b":   "don't know",
    r"\bngl\b":     "not going to lie",
    r"\bidk\b":     "I don't know",
    r"\btbh\b":     "to be honest",
}


def _has_past_time_marker(tokens: list[str]) -> bool:
    """Detect if sentence has a past-tense time marker word."""
    lower = {t.lower() for t in tokens}
    if lower & _PAST_MARKERS:
        return True
    joined = " ".join(t.lower() for t in tokens)
    for pattern in _PAST_PHRASES:
        if re.search(pattern, joined):
            return True
    return False


def _has_present_time_marker(tokens: list[str]) -> bool:
    lower = {t.lower() for t in tokens}
    return bool(lower & _PRESENT_MARKERS)


def _get_subject(tags: list[tuple]) -> str | None:
    """Return the lowercase surface form of the first subject-like noun/pronoun."""
    for word, tag in tags:
        if tag == "PRP" or tag in ("NN", "NNS", "NNP", "NNPS"):
            return word.lower()
    return None


def _correct_tense(tokens: list[str]) -> tuple[list[str], list[dict]]:
    """
    Fix tense mismatches:
      - Present tense verb + past time marker → past tense
      - Auxiliary 'did' + past tense verb → base form
      - 'to be' + bare infinitive where gerund needed
    Returns (corrected_tokens, fixes).
    """
    fixes = []
    tags = pos_tag(tokens)
    lower_tokens = [t.lower() for t in tokens]

    has_past   = _has_past_time_marker(tokens)
    has_pres   = _has_present_time_marker(tokens)

    # Did + past tense verb → did + base form  (e.g. "did went" → "did go")
    for i, (word, tag) in enumerate(tags):
        if word.lower() == "did" and i + 1 < len(tags):
            next_word, next_tag = tags[i + 1]
            if next_tag == "VBD":
                base = _lemmatizer.lemmatize(next_word.lower(), "v")
                if base != next_word.lower():
                    inf = pyinflect.getInflection(base, "VB")
                    corrected = inf[0] if inf else base
                    fixes.append({
                        "type": "tense",
                        "original": next_word,
                        "corrected": corrected,
                        "description": f'After "did" use base form: "{next_word}" → "{corrected}"',
                        "index": i + 1,
                    })
                    tokens = list(tokens)
                    tokens[i + 1] = _preserve_case(next_word, corrected)

    # Re-tag after possible did-fix
    tags = pos_tag(tokens)

    # Present tense verb + past time marker → past tense
    if has_past and not has_pres:
        for i, (word, tag) in enumerate(tags):
            # Skip auxiliaries
            if word.lower() in _STOP:
                continue
            # VBP = non-3rd-person present, VBZ = 3rd-person present
            if tag in ("VBP", "VBZ"):
                base = _lemmatizer.lemmatize(word.lower(), "v")
                past = pyinflect.getInflection(base, "VBD")
                if past and past[0].lower() != word.lower():
                    fixes.append({
                        "type": "tense",
                        "original": word,
                        "corrected": past[0],
                        "description": f'Past time context: "{word}" → "{past[0]}"',
                        "index": i,
                    })
                    tokens = list(tokens)
                    tokens[i] = _preserve_case(word, past[0])

    return tokens, fixes


def _correct_subject_verb_agreement(tokens: list[str]) -> tuple[list[str], list[dict]]:
    """
    Fix subject-verb agreement:
      - 3rd person singular subject + base/non-3rd verb → 3rd person verb
        (He go → He goes)
      - 1st/2nd/plural subject + 3rd person singular verb → base form
        (I goes → I go, They goes → They go)
    """
    fixes = []
    tags = pos_tag(tokens)

    for i, (word, tag) in enumerate(tags):
        if tag in ("VBP", "VBZ", "VB"):
            # Find subject to the left
            subject = None
            subject_tag = None
            preceded_by_aux = False  # True if this verb is already governed by an auxiliary
            for j in range(i - 1, -1, -1):
                w_lower = tags[j][0].lower()
                # If there's a do/modal/have/be auxiliary before the verb, skip SV correction
                # (agreement belongs to the auxiliary, not the main verb)
                if tags[j][1] in ("MD",) or w_lower in (
                    "do", "does", "did", "don't", "doesn't", "didn't",
                    "will", "would", "can", "could", "should", "may", "might",
                    "have", "has", "had", "am", "is", "are", "was", "were",
                ):
                    preceded_by_aux = True
                    break
                if tags[j][1] in ("PRP", "NN", "NNS", "NNP", "NNPS"):
                    subject = tags[j][0].lower()
                    subject_tag = tags[j][1]
                    break

            if subject is None or preceded_by_aux:
                continue

            base = _lemmatizer.lemmatize(word.lower(), "v")
            if base in _STOP:
                continue

            # 3rd person singular subject + non-3rd-verb (VBP or base VB) → 3rd person
            if subject in _THIRD_PERSON_SING and tag in ("VBP", "VB"):
                third = pyinflect.getInflection(base, "VBZ")
                if third and third[0].lower() != word.lower():
                    fixes.append({
                        "type": "subject_verb_agreement",
                        "original": word,
                        "corrected": third[0],
                        "description": f'3rd person singular: "{word}" → "{third[0]}" (subject: "{subject}")',
                        "index": i,
                    })
                    tokens = list(tokens)
                    tokens[i] = _preserve_case(word, third[0])

            # 1st/2nd/plural subject + 3rd person singular verb → base
            elif subject in ("i", "we", "they", "you") and tag == "VBZ":
                base_inf = pyinflect.getInflection(base, "VBP")
                corrected = base_inf[0] if base_inf else base
                if corrected.lower() != word.lower():
                    fixes.append({
                        "type": "subject_verb_agreement",
                        "original": word,
                        "corrected": corrected,
                        "description": f'Plural/1st/2nd person: "{word}" → "{corrected}" (subject: "{subject}")',
                        "index": i,
                    })
                    tokens = list(tokens)
                    tokens[i] = _preserve_case(word, corrected)

    # was/were number agreement (They was → They were; He were → He was)
    tags = pos_tag(tokens)
    for i, (word, tag) in enumerate(tags):
        if word.lower() not in ("was", "were"):
            continue
        subject = None
        for j in range(i - 1, -1, -1):
            if tags[j][1] in ("PRP", "NN", "NNS", "NNP", "NNPS"):
                subject = tags[j][0].lower()
                break
        if subject is None:
            continue
        if subject in ("they", "we", "i", "you") and word.lower() == "was":
            fixes.append({
                "type": "subject_verb_agreement",
                "original": word,
                "corrected": "were",
                "description": f'Plural/1st person "be": "{word}" → "were" (subject: "{subject}")',
                "index": i,
            })
            tokens = list(tokens)
            tokens[i] = _preserve_case(word, "were")
        elif subject in _THIRD_PERSON_SING and word.lower() == "were":
            fixes.append({
                "type": "subject_verb_agreement",
                "original": word,
                "corrected": "was",
                "description": f'Singular "be": "{word}" → "was" (subject: "{subject}")',
                "index": i,
            })
            tokens = list(tokens)
            tokens[i] = _preserve_case(word, "was")

    return tokens, fixes


def _correct_auxiliary_forms(tokens: list[str]) -> tuple[list[str], list[dict]]:
    """
    Fix auxiliary + verb form errors:
      - am/is/are/was/were + base verb → gerund (I am go → I am going)
      - will/would/can/could/should/may/might + past/gerund → base (I will went → I will go)
      - has/have/had + base/gerund → past participle (I have eat → I have eaten)
    """
    fixes = []
    tags = pos_tag(tokens)
    _MODAL_AUX = {"will", "would", "can", "could", "should", "may", "might", "shall", "must"}
    _BE_AUX    = {"am", "is", "are", "was", "were", "be", "been", "being"}
    _HAVE_AUX  = {"have", "has", "had"}

    for i, (word, tag) in enumerate(tags):
        lw = word.lower()

        # BE auxiliary + bare verb → gerund (progressive)
        if lw in _BE_AUX and i + 1 < len(tags):
            next_word, next_tag = tags[i + 1]
            if next_tag in ("VBP", "VBZ", "VBD", "VB") and next_word.lower() not in _STOP:
                base = _lemmatizer.lemmatize(next_word.lower(), "v")
                gerund = pyinflect.getInflection(base, "VBG")
                if gerund and gerund[0].lower() != next_word.lower():
                    fixes.append({
                        "type": "auxiliary_form",
                        "original": next_word,
                        "corrected": gerund[0],
                        "description": f'After "{lw}" use gerund: "{next_word}" → "{gerund[0]}"',
                        "index": i + 1,
                    })
                    tokens = list(tokens)
                    tokens[i + 1] = _preserve_case(next_word, gerund[0])

        # Modal auxiliary + non-base verb → base
        elif lw in _MODAL_AUX and i + 1 < len(tags):
            next_word, next_tag = tags[i + 1]
            if next_tag in ("VBD", "VBZ", "VBG", "VBN") and next_word.lower() not in _STOP:
                base = _lemmatizer.lemmatize(next_word.lower(), "v")
                inf = pyinflect.getInflection(base, "VB")
                corrected = inf[0] if inf else base
                if corrected.lower() != next_word.lower():
                    fixes.append({
                        "type": "auxiliary_form",
                        "original": next_word,
                        "corrected": corrected,
                        "description": f'After modal "{lw}" use base form: "{next_word}" → "{corrected}"',
                        "index": i + 1,
                    })
                    tokens = list(tokens)
                    tokens[i + 1] = _preserve_case(next_word, corrected)

        # HAVE auxiliary + base/gerund → past participle
        elif lw in _HAVE_AUX and i + 1 < len(tags):
            next_word, next_tag = tags[i + 1]
            # Also catch: have + VBN where surface form ≠ correct participle (e.g. "have eat")
            if next_tag in ("VBP", "VBZ", "VBG", "VBN") and next_word.lower() not in _STOP:
                base = _lemmatizer.lemmatize(next_word.lower(), "v")
                participle = pyinflect.getInflection(base, "VBN")
                if participle and participle[0].lower() != next_word.lower():
                    fixes.append({
                        "type": "auxiliary_form",
                        "original": next_word,
                        "corrected": participle[0],
                        "description": f'After "{lw}" use past participle: "{next_word}" → "{participle[0]}"',
                        "index": i + 1,
                    })
                    tokens = list(tokens)
                    tokens[i + 1] = _preserve_case(next_word, participle[0])

    return tokens, fixes


def sanitize_input(text: str) -> tuple[str, list[dict]]:
    """
    Comprehensive grammar correction applied BEFORE the synonym pipeline.

    Layers (in order):
      1. Surface fixes: contractions, informal words
      2. Pronoun capitalisation (i → I)
      3. Sentence capitalisation
      4. Spacing cleanup
      5. Auxiliary verb form correction (am go → am going)
      6. Tense correction (eat yesterday → ate yesterday)
      7. Subject-verb agreement (He go → He goes)
      8. Punctuation

    Returns (corrected_text, list_of_fix_dicts).
    """
    all_fixes: list[dict] = []
    result = text.strip()

    # ── Layer 1a: Contractions ─────────────────────────────────────────────
    for pattern, replacement in _CONTRACTIONS.items():
        match = re.search(pattern, result, re.IGNORECASE)
        if match:
            original = match.group()
            if original.replace("'", "").lower() == replacement.replace("'", "").lower():
                all_fixes.append({
                    "type": "contraction",
                    "original": original,
                    "corrected": replacement,
                    "description": f'Added missing apostrophe: "{original}" → "{replacement}"',
                })
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # ── Layer 1b: Informal words ───────────────────────────────────────────
    for pattern, replacement in _WORD_FIXES.items():
        match = re.search(pattern, result, re.IGNORECASE)
        if match:
            original = match.group()
            all_fixes.append({
                "type": "informal_word",
                "original": original,
                "corrected": replacement,
                "description": f'Informal word: "{original}" → "{replacement}"',
            })
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # ── Layer 2: Pronoun case ──────────────────────────────────────────────
    new = re.sub(r"\b(i)\b", "I", result)
    if new != result:
        all_fixes.append({
            "type": "pronoun_case",
            "original": "i",
            "corrected": "I",
            "description": 'Capitalised pronoun "i" → "I"',
        })
        result = new

    # ── Layer 3: Sentence capitalisation ──────────────────────────────────
    if result and result[0].islower():
        all_fixes.append({
            "type": "capitalization",
            "original": result[0],
            "corrected": result[0].upper(),
            "description": f'Capitalised first letter: "{result[0]}" → "{result[0].upper()}"',
        })
        result = result[0].upper() + result[1:]

    # ── Layer 4: Spacing ──────────────────────────────────────────────────
    if re.search(r" {2,}", result):
        all_fixes.append({
            "type": "spacing",
            "original": "  ",
            "corrected": " ",
            "description": "Removed extra spaces",
        })
        result = re.sub(r" {2,}", " ", result)

    # ── Tokenise for grammar analysis ─────────────────────────────────────
    # Strip trailing punctuation before grammar analysis so POS tags are clean
    working = result.rstrip(".!?").strip()
    try:
        tokens = word_tokenize(working)
    except Exception:
        # Fallback if tokenisation fails (shouldn't happen but be safe)
        tokens = working.split()

    # ── Layer 5: Auxiliary verb forms ─────────────────────────────────────
    tokens, aux_fixes = _correct_auxiliary_forms(tokens)
    for f in aux_fixes:
        all_fixes.append({
            "type": f["type"],
            "original": f["original"],
            "corrected": f["corrected"],
            "description": f["description"],
        })

    # Re-tokenise after aux fixes (tokens list is already updated in-place above)
    # ── Layer 6: Tense correction ─────────────────────────────────────────
    tokens, tense_fixes = _correct_tense(tokens)
    for f in tense_fixes:
        all_fixes.append({
            "type": f["type"],
            "original": f["original"],
            "corrected": f["corrected"],
            "description": f["description"],
        })

    # ── Layer 7: Subject-verb agreement ───────────────────────────────────
    tokens, sv_fixes = _correct_subject_verb_agreement(tokens)
    for f in sv_fixes:
        all_fixes.append({
            "type": f["type"],
            "original": f["original"],
            "corrected": f["corrected"],
            "description": f["description"],
        })

    # Rebuild sentence from corrected tokens
    if any(all_fixes[i]["type"] in ("tense", "subject_verb_agreement", "auxiliary_form")
           for i in range(len(all_fixes))):
        result = _detokenize(tokens)
        # Re-apply capitalisation (detokenize can lowercase first word)
        if result and result[0].islower():
            result = result[0].upper() + result[1:]

    # ── Layer 8: Punctuation ──────────────────────────────────────────────
    stripped = result.rstrip()
    if stripped and stripped[-1] not in ".!?":
        all_fixes.append({
            "type": "punctuation",
            "original": "",
            "corrected": ".",
            "description": "Added missing full stop at end of sentence",
        })
        result = stripped + "."

    return result, all_fixes


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
    if not original or not replacement:
        return replacement
    if original.isupper():
        return replacement.upper()
    if original[0].isupper():
        return replacement.capitalize()
    return replacement.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Sentence rewriter  (SBERT-aware, POS-filtered WordNet)
# ─────────────────────────────────────────────────────────────────────────────
class SentenceRewriter:
    """
    Rewrites a (sanitized) sentence by substituting content words with
    semantically validated synonyms, inflected correctly.

    Key improvement over v2: synonym candidates are now retrieved with the
    WordNet POS filter matching the token's actual POS in context.  This
    prevents cross-POS contamination (e.g. verb hypernyms polluting noun lookups).

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
        - same broad POS (WordNet check — now passed to engine as wn_pos)
        - single token only
        - prefer -ly forms for -ly adverbs
        """
        wn_p = _wn_pos(pos_tag_str)

        # Pass wn_pos to engine so WordNet lookups are POS-restricted at the source
        all_syns = self.engine.get_synonyms(
            lemma, top_k=top_k * 2, wn_pos=wn_p
        ).get(lemma, [])

        prefer_ly = pos_tag_str.startswith("RB") and original_word.lower().endswith("ly")

        filtered = []
        for cand in all_syns:
            if cand in (lemma, original_word.lower()):
                continue
            if " " in cand:
                continue
            # Secondary POS check: candidate must have at least one WordNet sense
            # matching our expected POS (guards against Datamuse returning wrong POS)
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
             a. Get raw candidates (engine, POS-filtered)
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
                tokens            = list(new_tokens),   # use current rebuilt state
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
