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

import paths  # noqa: F401  — must precede nltk import; redirects caches into ./.cache
import re
import nltk
from nltk import pos_tag, word_tokenize
from nltk.corpus import wordnet as wn
from nltk.stem import WordNetLemmatizer
import pyinflect

import semantic as sem
import phonetic as ph

for _pkg in ("averaged_perceptron_tagger_eng", "punkt_tab", "wordnet", "omw-1.4"):
    nltk.download(_pkg, quiet=True)

# ── Spelling correction (pyspellchecker — fast, fully offline) ────────────────
try:
    from spellchecker import SpellChecker as _SpellChecker
    _spell = _SpellChecker()
    _SPELL_OK = True
except ImportError:
    _spell = None
    _SPELL_OK = False

# ── LanguageTool integration (optional; requires Java 8+) ─────────────────────
# Loaded lazily on first use so startup time is not affected if Java is absent.
_lt_tool = None
_LT_OK   = False   # set True once the tool loads successfully

def _get_lt_tool():
    """Return a (cached) LanguageTool instance, or None if unavailable."""
    global _lt_tool, _LT_OK
    if _LT_OK:
        return _lt_tool
    if _lt_tool is not None:   # already tried and failed
        return None
    try:
        import language_tool_python as _ltp
        _lt_tool = _ltp.LanguageTool("en-US")
        _LT_OK   = True
    except Exception:
        _lt_tool = None   # sentinel — don't retry
    return _lt_tool

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
_THIRD_PERSON_SING  = {"he", "she", "it", "this", "that", "one"}
_FIRST_PERSON_SING  = {"i"}
_PLURAL_OR_2ND      = {"we", "they", "you"}
_ALL_NON_THIRD_SING = _FIRST_PERSON_SING | _PLURAL_OR_2ND

# BE-verb agreement table  (subject, tense) → correct form
_BE_AGREE = {
    ("i",    "present"): "am",
    ("he",   "present"): "is",  ("she",  "present"): "is",
    ("it",   "present"): "is",  ("this", "present"): "is",
    ("that", "present"): "is",  ("one",  "present"): "is",
    ("we",   "present"): "are", ("they", "present"): "are",
    ("you",  "present"): "are",
    ("i",    "past"):    "was",
    ("he",   "past"):    "was",  ("she",  "past"):    "was",
    ("it",   "past"):    "was",  ("this", "past"):    "was",
    ("that", "past"):    "was",  ("one",  "past"):    "was",
    ("we",   "past"):    "were", ("they", "past"):    "were",
    ("you",  "past"):    "were",
}

# Correct contracted negation per subject
_DO_NEG_PRESENT = {
    "he": "doesn't", "she": "doesn't", "it": "doesn't",
    "this": "doesn't", "that": "doesn't", "one": "doesn't",
    "i": "don't", "we": "don't", "they": "don't", "you": "don't",
}

# Predicate complements after "be" that are commonly adjectives/adverbs even
# though they also happen to be verb base forms.  Never treat these as a missing
# gerund — protects "I am well", "she is free", "it is right", etc.
_BE_COMPLEMENT_STOP = {
    "well", "fine", "free", "right", "close", "clear", "fast", "sure", "present",
    "last", "light", "clean", "complete", "content", "secure", "firm", "sound",
    "warm", "cool", "calm", "open", "even", "fit", "level", "ready", "busy",
    "slow", "square", "like", "worth", "fair", "plain", "wet", "dry", "blind",
    "kind", "mean", "just", "past", "out", "up", "down", "off", "on", "over",
}


# Words that signal an action in progress — used to disambiguate "BE + verb"
# for verbs whose past participle equals their base form (read, run, set, cut…),
# where "is read" could be a passive OR a missing-progressive error.
_PROGRESSIVE_CUES = {
    "now", "currently", "right", "today", "tonight", "presently",
    "nowadays", "still", "again", "constantly", "continually",
}


def _is_bare_verb(word: str) -> bool:
    """
    True if *word* is the base (lemma) form of a real verb — not an inflected
    participle/adjective.

    'run'/'go' → True;  'tired'/'broken'/'gone'/'running' → False, because their
    verb lemma differs from the surface form.  This is what lets the auxiliary
    fix correct "she is run" while leaving predicate participles untouched,
    independent of how the POS tagger (mis)labels the word.
    """
    w = word.lower()
    return _lemmatizer.lemmatize(w, "v") == w and bool(wn.synsets(w, pos=wn.VERB))


_BE_FORMS = {"am", "is", "are", "was", "were", "be", "been", "being"}


def _is_predicate_participle(tags: list[tuple], i: int) -> bool:
    """
    True if tags[i] is a past participle (VBN) acting as a predicate adjective
    after a BE auxiliary — 'tired' in "she is tired", 'broken' in "the door is
    broken".  Adverbs and 'not' between the auxiliary and the word are skipped.

    The rewriter uses this to look up *adjective* synonyms for such words instead
    of verb synonyms (so "tired" → weary/exhausted, not eaten/bore).
    """
    if tags[i][1] != "VBN":
        return False
    j = i - 1
    while j >= 0:
        w, t = tags[j]
        if t.startswith("RB") or w.lower() in ("not", "n't"):
            j -= 1
            continue
        return w.lower() in _BE_FORMS
    return False

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
    # "im" → "I'm" only when followed by a letter-word (not end-of-line/punct)
    r"\bim\b(?=\s+[a-zA-Z])": "I'm",
    r"\bive\b":      "I've",
    r"\bill\b":      "I'll",
    r"\bthats\b":    "that's",
    r"\bwhats\b":    "what's",
    r"\bwhos\b":     "who's",
    # "its" → "it's": handled below by _fix_its_contraction() after POS tagging
    # (the regex r"\bits\b" cannot distinguish possessive from contraction)
    r"\btheyre\b":   "they're",
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


def _find_subject_left(tags: list[tuple], verb_index: int) -> tuple:
    """
    Scan LEFT from verb_index to find the closest subject pronoun or noun.
    Stops at clause boundaries. Returns (subject_lower, pos_tag) or (None, None).
    Much more accurate than _get_subject() for multi-clause sentences.
    """
    for j in range(verb_index - 1, -1, -1):
        w_lower = tags[j][0].lower()
        t = tags[j][1]
        if t == "PRP":
            return w_lower, t
        if t in ("NN", "NNS", "NNP", "NNPS"):
            return w_lower, t
        if w_lower in (",", ";", ".", "because", "that", "which", "who", "when"):
            break
    return None, None


def _is_governed_by_aux(tags: list[tuple], verb_index: int) -> bool:
    """
    True if there is a modal/auxiliary to the LEFT of verb_index that
    already governs this verb — meaning we should NOT apply bare SVA to it.
    """
    _GOVERNING = {
        "do", "does", "did", "don't", "doesn't", "didn't",
        "will", "would", "can", "could", "should", "may", "might", "shall", "must",
        "have", "has", "had", "am", "is", "are", "was", "were", "be", "been",
    }
    for j in range(verb_index - 1, -1, -1):
        w_lower = tags[j][0].lower()
        tag = tags[j][1]
        if tag == "MD" or w_lower in _GOVERNING:
            return True
        if tag in ("PRP", "NN", "NNS", "NNP", "NNPS"):
            break
    return False


def _correct_be_agreement(tokens: list[str]) -> tuple[list[str], list[dict]]:
    """
    Fix BE-verb number/person agreement:
      "They is running"  → "They are running"
      "He are tired"     → "He is tired"
      "I is happy"       → "I am happy"
      "We was there"     → "We were there"
      "She were wrong"   → "She was wrong"
    """
    fixes  = []
    tokens = list(tokens)
    tags   = pos_tag(tokens)
    BE_PRESENT = {"am", "is", "are"}
    BE_PAST    = {"was", "were"}

    for i, (word, tag) in enumerate(tags):
        lw = word.lower()
        if lw not in BE_PRESENT and lw not in BE_PAST:
            continue
        subj, stag = _find_subject_left(tags, i)
        if subj is None:
            continue
        tense = "present" if lw in BE_PRESENT else "past"
        correct = _BE_AGREE.get((subj, tense))
        # Fallback for noun subjects not in table
        if correct is None:
            if stag in ("NNS", "NNPS"):
                correct = "are" if tense == "present" else "were"
            elif stag in ("NN", "NNP"):
                correct = "is"  if tense == "present" else "was"
        if correct and lw != correct:
            fixes.append({
                "type":        "subject_verb_agreement",
                "original":    word,
                "corrected":   correct,
                "description": f'BE agreement: "{word}" → "{correct}" (subject: "{subj}")',
                "index":       i,
            })
            tokens[i] = _preserve_case(word, correct)

    return tokens, fixes


def _correct_negation_agreement(tokens: list[str]) -> tuple[list[str], list[dict]]:
    """
    Fix do-negation contraction mismatches:
      "She don't like"    → "She doesn't like"
      "They doesn't go"   → "They don't go"
      "He don't know"     → "He doesn't know"
      "I doesn't care"    → "I don't care"
    Also fixes uncontracted "do not" / "does not" mismatches.
    Handles both surface forms: "don't" and the tokenized split "do" + "n't".
    """
    fixes  = []
    tokens = list(tokens)
    tags   = pos_tag(tokens)

    # Pass A: contracted forms — handle "don't"/"doesn't" AND tokenized "do/does" + "n't"
    i = 0
    while i < len(tags):
        word, tag = tags[i]
        lw = word.lower()

        # Case 1: single token "don't" or "doesn't"
        if lw in ("don't", "doesn't"):
            subj, _ = _find_subject_left(tags, i)
            if subj is not None:
                correct_neg = _DO_NEG_PRESENT.get(subj)
                if correct_neg and lw != correct_neg:
                    fixes.append({
                        "type":        "negation_agreement",
                        "original":    word,
                        "corrected":   correct_neg,
                        "description": f'Negation agreement: "{word}" → "{correct_neg}" (subject: "{subj}")',
                        "index":       i,
                    })
                    tokens[i] = _preserve_case(word, correct_neg)
            i += 1
            continue

        # Case 2: tokenized "do"/"does" + "n't"
        if lw in ("do", "does") and i + 1 < len(tags) and tags[i + 1][0].lower() == "n't":
            subj, _ = _find_subject_left(tags, i)
            if subj is not None:
                # Determine what the contracted form should be
                correct_neg = _DO_NEG_PRESENT.get(subj)  # e.g. "doesn't" or "don't"
                if correct_neg:
                    # The expected "do/does" part before "n't"
                    correct_do = "does" if subj in _THIRD_PERSON_SING else "do"
                    if lw != correct_do:
                        fixes.append({
                            "type":        "negation_agreement",
                            "original":    word,
                            "corrected":   correct_do,
                            "description": f'Negation agreement: "{word} n\'t" → "{correct_do} n\'t" (subject: "{subj}")',
                            "index":       i,
                        })
                        tokens[i] = _preserve_case(word, correct_do)
            i += 1
            continue

        i += 1

    # Re-tag then Pass B: uncontracted "do not" / "does not"
    tags = pos_tag(tokens)
    for i, (word, tag) in enumerate(tags):
        lw = word.lower()
        if lw not in ("do", "does") or i + 1 >= len(tags):
            continue
        if tags[i + 1][0].lower() != "not":
            continue
        subj, _ = _find_subject_left(tags, i)
        if subj is None:
            continue
        correct_do = "does" if subj in _THIRD_PERSON_SING else "do"
        if lw != correct_do:
            fixes.append({
                "type":        "negation_agreement",
                "original":    word,
                "corrected":   correct_do,
                "description": f'Negation: "{word} not" → "{correct_do} not" (subject: "{subj}")',
                "index":       i,
            })
            tokens[i] = _preserve_case(word, correct_do)

    return tokens, fixes


def _correct_tense(tokens: list[str]) -> tuple[list[str], list[dict]]:
    """
    Fix tense mismatches:
      - Present tense verb + past time marker → past tense
      - Auxiliary 'did' + past tense verb → base form
    Returns (corrected_tokens, fixes).

    Bug fix (v2): after each individual token mutation we update `tokens`
    in-place AND re-derive `tags` before continuing, so a sentence with
    multiple present-tense verbs and a past marker has every verb corrected,
    not just the first one.
    """
    fixes  = []
    tokens = list(tokens)   # own copy; mutations are to this list throughout
    tags   = pos_tag(tokens)

    has_past = _has_past_time_marker(tokens)
    has_pres = _has_present_time_marker(tokens)

    # ── Pass A: did + past-tense verb → base form ("did went" → "did go") ──
    changed = False
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
                    tokens[i + 1] = _preserve_case(next_word, corrected)
                    changed = True

    # Re-tag once after all did-fixes before the next pass
    if changed:
        tags = pos_tag(tokens)

    # ── Pass B: present verb + past time marker → past tense ───────────────
    # Re-tag after EVERY individual fix so subsequent verbs in the same
    # sentence are evaluated against the already-corrected token list.
    if has_past and not has_pres:
        for i in range(len(tokens)):
            word, tag = tokens[i], pos_tag([tokens[i]])[0][1]
            if word.lower() in _STOP:
                continue
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
                    tokens[i] = _preserve_case(word, past[0])
                    # No need to re-tag the full sentence after each fix;
                    # per-token tagging above is sufficient since we iterate
                    # by position, not by the cached tags list.

    return tokens, fixes


def _correct_subject_verb_agreement(tokens: list[str]) -> tuple[list[str], list[dict]]:
    """
    Fix subject-verb agreement for main (non-BE, non-auxiliary-governed) verbs:
      - 3rd person singular subject + base/non-3rd verb → 3rd person verb
        (He go → He goes, She run → She runs)
      - 1st/2nd/plural subject + 3rd person singular verb → base form
        (I goes → I go, They goes → They go)
      - Singular/plural noun subjects also handled (The cat run → The cat runs)
    Uses _find_subject_left() for accurate per-verb subject detection.
    Uses _is_governed_by_aux() to skip verbs already controlled by an auxiliary.
    BE-verb agreement is handled separately by _correct_be_agreement().
    """
    fixes  = []
    tokens = list(tokens)
    tags   = pos_tag(tokens)

    BE_SET = {"am", "is", "are", "was", "were", "be", "been", "being"}

    for i, (word, tag) in enumerate(tags):
        if tag not in ("VBP", "VBZ", "VB"):
            continue
        lw = word.lower()
        if lw in _STOP or lw in BE_SET:
            continue
        if _is_governed_by_aux(tags, i):
            continue

        subj, stag = _find_subject_left(tags, i)
        if subj is None:
            continue

        base = _lemmatizer.lemmatize(lw, "v")
        if base in _STOP:
            continue

        # 3rd-person singular pronoun + VBP/VB → VBZ
        if subj in _THIRD_PERSON_SING and tag in ("VBP", "VB"):
            third = pyinflect.getInflection(base, "VBZ")
            if third and third[0].lower() != lw:
                fixes.append({
                    "type": "subject_verb_agreement",
                    "original": word,
                    "corrected": third[0],
                    "description": f'3rd person singular: "{word}" → "{third[0]}" (subject: "{subj}")',
                    "index": i,
                })
                tokens = list(tokens)
                tokens[i] = _preserve_case(word, third[0])

        # 1st/2nd/plural pronoun + VBZ → base
        elif subj in _ALL_NON_THIRD_SING and tag == "VBZ":
            base_inf  = pyinflect.getInflection(base, "VBP")
            corrected = base_inf[0] if base_inf else base
            if corrected.lower() != lw:
                fixes.append({
                    "type": "subject_verb_agreement",
                    "original": word,
                    "corrected": corrected,
                    "description": f'Plural/1st/2nd person: "{word}" → "{corrected}" (subject: "{subj}")',
                    "index": i,
                })
                tokens = list(tokens)
                tokens[i] = _preserve_case(word, corrected)

        # Singular noun subject + VBP → VBZ
        elif stag in ("NN", "NNP") and tag == "VBP":
            third = pyinflect.getInflection(base, "VBZ")
            if third and third[0].lower() != lw:
                fixes.append({
                    "type": "subject_verb_agreement",
                    "original": word,
                    "corrected": third[0],
                    "description": f'Singular noun subject: "{word}" → "{third[0]}" (subject: "{subj}")',
                    "index": i,
                })
                tokens = list(tokens)
                tokens[i] = _preserve_case(word, third[0])

        # Plural noun subject + VBZ → base
        elif stag in ("NNS", "NNPS") and tag == "VBZ":
            base_inf  = pyinflect.getInflection(base, "VBP")
            corrected = base_inf[0] if base_inf else base
            if corrected.lower() != lw:
                fixes.append({
                    "type": "subject_verb_agreement",
                    "original": word,
                    "corrected": corrected,
                    "description": f'Plural noun subject: "{word}" → "{corrected}" (subject: "{subj}")',
                    "index": i,
                })
                tokens = list(tokens)
                tokens[i] = _preserve_case(word, corrected)

    return tokens, fixes


def _correct_existential_there(tokens: list[str]) -> tuple[list[str], list[dict]]:
    """
    Fix existential 'there is/was' before a plural noun:
      "there is many problems" → "there are many problems"
      "there was two cats"     → "there were two cats"
    Only fires when the head noun after the verb is clearly plural (NNS/NNPS)
    and no singular noun intervenes — conservative to avoid false edits.
    """
    fixes = []
    tags  = pos_tag(tokens)
    for i, (w, t) in enumerate(tags):
        if w.lower() != "there" or i + 1 >= len(tags):
            continue
        vw = tags[i + 1][0]
        if vw.lower() not in ("is", "was"):
            continue
        plural = None
        for j in range(i + 2, min(i + 7, len(tags))):
            if tags[j][1] in ("NN", "NNP"):
                plural = False
                break
            if tags[j][1] in ("NNS", "NNPS"):
                plural = True
                break
        if plural:
            corrected = "are" if vw.lower() == "is" else "were"
            fixes.append({
                "type": "subject_verb_agreement",
                "original": vw,
                "corrected": corrected,
                "description": f'Existential "there": plural subject → "{vw}" → "{corrected}"',
                "index": i + 1,
            })
            tokens = list(tokens)
            tokens[i + 1] = _preserve_case(vw, corrected)
            tags = pos_tag(tokens)
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

        # BE auxiliary + stray base verb → gerund (progressive).
        # Decide "is this a stray base verb?" from the verb lexicon + bare-form
        # test, NOT from the POS tag — the tagger mislabels exactly these errors
        # ("she is run" → run/VBN, "I am go" → go/RB).  The bare-form test also
        # auto-protects predicate participles/adjectives (tired, broken, gone),
        # and _BE_COMPLEMENT_STOP guards verb-also-adjective words (well, free…).
        if lw in _BE_AUX and i + 1 < len(tags):
            next_word = tags[i + 1][0]
            nlw = next_word.lower()
            if (nlw not in _STOP
                    and nlw not in _BE_COMPLEMENT_STOP
                    and _is_bare_verb(nlw)):
                gerund     = pyinflect.getInflection(nlw, "VBG")
                participle = pyinflect.getInflection(nlw, "VBN")
                # Verbs whose participle == base form (read, run, set, cut, put,
                # hit, shut…) make "BE + verb" indistinguishable from a real
                # passive ("the book is read by many", "the race is run").  For
                # these, only convert to progressive when there is a clear
                # progressive cue AND no 'by'-agent — otherwise leave the
                # (possibly passive) clause untouched.  Verbs with a distinct
                # participle (go→gone, eat→eaten) are unambiguous and always fixed.
                ambiguous = bool(participle) and participle[0].lower() == nlw
                allow = True
                if ambiguous:
                    rest_lower = {t.lower() for t in tokens[i + 2:]}
                    all_lower  = {t.lower() for t in tokens}
                    allow = bool(all_lower & _PROGRESSIVE_CUES) and "by" not in rest_lower
                if allow and gerund and gerund[0].lower() != nlw:
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


def _fix_its_contraction(text: str) -> tuple[str, list[dict]]:
    """
    POS-aware "its" → "it's" fix.

    "its" is possessive when followed by a NOUN (NN/NNS/NNP/NNPS) or
    determiner/adjective that precedes a noun — i.e. "its policy", "its own".
    "its" is a contraction error when followed by a VERB, ADJ, or ADV —
    i.e. "its going well", "its great", "its been done".

    We tokenize a tiny window around each occurrence and POS-tag only that
    window to keep this fast.
    """
    fixes = []
    # Find all occurrences of bare "its" (case-insensitive, no apostrophe)
    for m in list(re.finditer(r"\bits\b", text, re.IGNORECASE)):
        # Grab the word that follows (skip whitespace)
        after = text[m.end():].lstrip()
        if not after:
            continue
        next_word = re.match(r"[a-zA-Z']+", after)
        if not next_word:
            continue
        nw = next_word.group()
        # POS-tag just the next word in isolation — cheap and sufficient
        nw_tag = pos_tag([nw])[0][1]
        # Possessive: next word is a noun, determiner, number, or adjective
        # that commonly precedes a noun.  These tags → keep "its" as-is.
        _POSSESSIVE_NEXT = {"NN", "NNS", "NNP", "NNPS", "DT", "PRP$", "CD", "JJ", "JJR", "JJS", "WP$"}
        if nw_tag in _POSSESSIVE_NEXT:
            continue  # correct possessive — do not touch
        # Otherwise the next word is a verb/adverb/particle → contraction error
        original = m.group()
        corrected = "it's" if original[0].islower() else "It's"
        fixes.append({
            "type": "contraction",
            "original": original,
            "corrected": corrected,
            "description": f'Added missing apostrophe: "{original}" → "{corrected}"',
        })
        # Replace only this specific occurrence by offset
        text = text[:m.start()] + corrected + text[m.end():]
    return text, fixes


# ─────────────────────────────────────────────────────────────────────────────
# Spelling correction  (pyspellchecker)
# ─────────────────────────────────────────────────────────────────────────────

# Words that look "wrong" to the spell-checker but are intentional:
# proper names, technical terms, abbreviations, already-handled contractions.
_SPELL_WHITELIST: set[str] = {
    # pronouns / particles that the checker flags
    "i", "i'm", "i've", "i'll", "i'd",
    # common abbreviations
    "mr", "mrs", "ms", "dr", "prof", "vs",
    # project-domain tokens
    "sbert", "nltk", "pos", "nlp",
}

# POS tags whose words we never try to spell-correct (names, places, brands …)
_SPELL_SKIP_TAGS = {"NNP", "NNPS", "CD", "FW", "LS", "SYM", "$", "``", "''",
                    ":", ",", ".", "-LRB-", "-RRB-"}

def _correct_spelling(tokens: list[str], tags: list[tuple]) -> tuple[list[str], list[dict]]:
    """
    Spell-check every non-proper, non-punctuation token.

    Strategy
    --------
    1. Collect all alphabetic tokens that are NOT whitelisted and NOT tagged as
       proper nouns / punctuation.
    2. Ask pyspellchecker which ones are unknown (misspelled).
    3. For each unknown token take the single best correction.  Accept only if:
       - The correction is different from the original.
       - The correction is not an empty string.
       - The Levenshtein distance (approximated by length ratio) is not too large,
         to avoid wild replacements for very short tokens.
    4. Return corrected token list + fix dicts compatible with the rest of the
       pipeline.

    Falls back silently when pyspellchecker is not installed.
    """
    if not _SPELL_OK or _spell is None:
        return tokens, []

    fixes  = []
    tokens = list(tokens)

    # Gather candidate (index, word) pairs
    candidates: list[tuple[int, str]] = []
    for i, (word, tag) in enumerate(tags):
        if tag in _SPELL_SKIP_TAGS:
            continue
        if not re.match(r"^[a-zA-Z]+$", word):  # skip punctuation / hyphenated
            continue
        if word.lower() in _SPELL_WHITELIST:
            continue
        candidates.append((i, word))

    if not candidates:
        return tokens, []

    # Batch-check
    words_only = [w for _, w in candidates]
    unknown    = _spell.unknown(words_only)

    for i, word in candidates:
        if word.lower() not in unknown:
            continue  # correctly spelled

        correction = _spell.correction(word.lower())
        if not correction or correction == word.lower():
            continue

        # Sanity gate: reject if correction is more than 60 % different in length
        # (catches cases where a very short typo maps to an unrelated word).
        ratio = len(correction) / max(len(word), 1)
        if ratio < 0.4 or ratio > 2.5:
            continue

        corrected = _preserve_case(word, correction)
        fixes.append({
            "type":        "spelling",
            "original":    word,
            "corrected":   corrected,
            "description": f'Spelling: "{word}" → "{corrected}"',
            "index":       i,
        })
        tokens[i] = corrected

    return tokens, fixes


# ─────────────────────────────────────────────────────────────────────────────
# Article correction  ("a" / "an" before vowel / consonant sounds)
# ─────────────────────────────────────────────────────────────────────────────

# Words starting with a consonant letter but a vowel sound → need "an"
_VOWEL_SOUND_EXCEPTIONS: set[str] = {
    "hour", "honest", "honour", "honor", "heir", "herb",
    "homage", "hors",
}
# Words starting with a vowel letter but a consonant sound → need "a"
_CONSONANT_SOUND_EXCEPTIONS: set[str] = {
    "unicorn", "uniform", "unique", "united", "unity", "university",
    "universe", "union", "unit", "universal", "user", "use", "used",
    "useful", "usual", "utility", "utensil", "european", "eulogy",
    "euphemism", "ewe", "ewok", "one",
}

def _needs_an(next_word: str) -> bool:
    """Return True if the article before *next_word* should be 'an'."""
    nw = next_word.lower().rstrip(".,!?;:")
    if not nw:
        return False
    if nw in _CONSONANT_SOUND_EXCEPTIONS:
        return False
    if nw in _VOWEL_SOUND_EXCEPTIONS:
        return True
    return nw[0] in "aeiou"


def _correct_articles(tokens: list[str]) -> tuple[list[str], list[dict]]:
    """
    Fix 'a/an' article errors:
      "a apple"       → "an apple"
      "an cat"        → "a cat"
      "an university" → "a university"
      "a hour"        → "an hour"
    Only fires when the very next token is an ordinary word (not punctuation).
    """
    fixes  = []
    tokens = list(tokens)
    for i, word in enumerate(tokens):
        lw = word.lower()
        if lw not in ("a", "an"):
            continue
        if i + 1 >= len(tokens):
            continue
        next_tok = tokens[i + 1]
        if not re.match(r"[a-zA-Z]", next_tok):
            continue  # skip if next token is punctuation

        should_be_an = _needs_an(next_tok)
        correct = "an" if should_be_an else "a"
        if lw != correct:
            corrected = _preserve_case(word, correct)
            fixes.append({
                "type":        "article",
                "original":    word,
                "corrected":   corrected,
                "description": f'Article: "{word}" → "{corrected}" before "{next_tok}"',
                "index":       i,
            })
            tokens[i] = corrected

    return tokens, fixes


# ─────────────────────────────────────────────────────────────────────────────
# LanguageTool layer  (optional deep-check; requires Java)
# ─────────────────────────────────────────────────────────────────────────────

# Rule IDs we intentionally skip because our own pipeline already handles them
# (or because they produce too many false positives for stutter-aid text).
_LT_SKIP_RULES: set[str] = {
    "UPPERCASE_SENTENCE_START",    # handled by our capitalisation layer
    "COMMA_PARENTHESIS_WHITESPACE",
    "WHITESPACE_RULE",
    "EN_QUOTES",
    "DASH_RULE",
    "WORD_CONTAINS_UNDERSCORE",
    # SVA rules — our own engine is more conservative and already covers these
    "SUBJECT_VERB_AGREEMENT",
    "HE_VERB_AGR",
    "NON_STANDARD_VERB_FORM",
}

def _correct_with_languagetool(text: str) -> tuple[str, list[dict]]:
    """
    Run LanguageTool over *text* and apply all non-skipped suggestions.

    - Applies corrections from right to left so character offsets stay valid.
    - Returns (corrected_text, list_of_fix_dicts).
    - If LanguageTool is unavailable, returns (text, []) silently.
    """
    tool = _get_lt_tool()
    if tool is None:
        return text, []

    try:
        matches = tool.check(text)
    except Exception:
        return text, []

    fixes   = []
    matches = [m for m in matches
               if m.ruleId not in _LT_SKIP_RULES
               and m.replacements]          # only actionable matches

    # Apply right-to-left so earlier offsets remain valid
    for m in sorted(matches, key=lambda x: x.offset, reverse=True):
        suggestion = m.replacements[0]
        original   = text[m.offset: m.offset + m.errorLength]
        if original == suggestion:
            continue
        fixes.append({
            "type":        "languagetool",
            "original":    original,
            "corrected":   suggestion,
            "description": f'[{m.ruleId}] {m.message}: "{original}" → "{suggestion}"',
        })
        text = text[: m.offset] + suggestion + text[m.offset + m.errorLength :]

    return text, list(reversed(fixes))   # restore left-to-right order for display


# ─────────────────────────────────────────────────────────────────────────────
# 1. Input sanitizer (comprehensive grammar correction)
# ─────────────────────────────────────────────────────────────────────────────
def sanitize_input(text: str) -> tuple[str, list[dict]]:
    """
    Comprehensive grammar correction applied BEFORE the synonym pipeline.

    Layers (in order):
      0. Spelling correction      (pyspellchecker — fast, offline)
      1. Surface fixes            contractions (POS-safe "its"), informal words
      2. Pronoun capitalisation   (i → I)
      3. Sentence capitalisation
      4. Spacing cleanup
      5. Article correction       (a/an agreement)
      6. Auxiliary verb forms     (am go → am going)
      7. Tense correction         (eat yesterday → ate yesterday)
      8. Subject-verb agreement   (He go → He goes)
      9. Punctuation
     10. LanguageTool deep-check  (optional; requires Java — skipped gracefully)

    Returns (corrected_text, list_of_fix_dicts).
    """
    all_fixes: list[dict] = []
    result = text.strip()

    # ── Layer 0: Spelling correction ──────────────────────────────────────
    # Run BEFORE contraction/grammar fixes so downstream layers see correctly
    # spelled words.  We tokenise a scratch copy, spell-check, then rebuild
    # the string — the contraction layers work on the rebuilt string.
    if _SPELL_OK:
        try:
            _sp_tokens = word_tokenize(result)
            _sp_tags   = pos_tag(_sp_tokens)
            _sp_tokens, sp_fixes = _correct_spelling(_sp_tokens, _sp_tags)
            if sp_fixes:
                all_fixes.extend(sp_fixes)
                # Rebuild from corrected tokens (simple join — contractions
                # re-tokenise later anyway)
                result = _detokenize(_sp_tokens)
        except Exception:
            pass   # never break the pipeline

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

    # POS-aware "its" → "it's" (cannot be done with a bare regex — see helper)
    result, its_fixes = _fix_its_contraction(result)
    all_fixes.extend(its_fixes)

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

    # ── Layer 4b: Article correction (a/an) ───────────────────────────────
    try:
        _art_tokens = word_tokenize(result)
        _art_tokens, art_fixes = _correct_articles(_art_tokens)
        if art_fixes:
            all_fixes.extend(art_fixes)
            result = _detokenize(_art_tokens)
    except Exception:
        pass

    # ── Tokenise for grammar analysis ─────────────────────────────────────
    # Preserve trailing punctuation (.!?) so it survives the token rebuild.
    # We strip it from the *working copy* only — for clean POS tags — then
    # re-attach the original punctuation after _detokenize().
    _trail_m = re.search(r"([.!?]+)\s*$", result)
    _trailing_punct = _trail_m.group(1) if _trail_m else ""
    working = result[:_trail_m.start()].strip() if _trail_m else result.strip()
    try:
        tokens = word_tokenize(working)
    except Exception:
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

    # ── Layer 7: BE-verb agreement (They is → They are) ───────────────────
    tokens, be_fixes = _correct_be_agreement(tokens)
    for f in be_fixes:
        all_fixes.append({
            "type": f["type"],
            "original": f["original"],
            "corrected": f["corrected"],
            "description": f["description"],
        })

    # ── Layer 7b: Subject-verb agreement (main verbs) ─────────────────────
    tokens, sv_fixes = _correct_subject_verb_agreement(tokens)
    for f in sv_fixes:
        all_fixes.append({
            "type": f["type"],
            "original": f["original"],
            "corrected": f["corrected"],
            "description": f["description"],
        })

    # ── Layer 7c: Negation agreement (She don't → She doesn't) ───────────
    tokens, neg_fixes = _correct_negation_agreement(tokens)
    for f in neg_fixes:
        all_fixes.append({
            "type": f["type"],
            "original": f["original"],
            "corrected": f["corrected"],
            "description": f["description"],
        })

    # ── Layer 7d: Existential "there is/are" agreement ────────────────────
    tokens, there_fixes = _correct_existential_there(tokens)
    for f in there_fixes:
        all_fixes.append({
            "type": f["type"],
            "original": f["original"],
            "corrected": f["corrected"],
            "description": f["description"],
        })

    # Rebuild sentence from corrected tokens
    _STRUCTURAL = {"tense", "subject_verb_agreement", "auxiliary_form", "negation_agreement"}
    if any(all_fixes[i]["type"] in _STRUCTURAL
           for i in range(len(all_fixes))):
        result = _detokenize(tokens)
        # Re-apply capitalisation (detokenize can lowercase first word)
        if result and result[0].islower():
            result = result[0].upper() + result[1:]
        # Re-attach the trailing punctuation we stripped before tokenising.
        # _detokenize() won't have it because we didn't put it in the token list.
        if _trailing_punct and not result.endswith(_trailing_punct):
            result = result.rstrip(".!?") + _trailing_punct
    else:
        # No structural fix rebuilt the sentence — but we still need to
        # restore the trailing punctuation if it got eaten by rstrip earlier.
        if _trailing_punct and not result.rstrip().endswith(_trailing_punct[-1]):
            result = result.rstrip(".!?") + _trailing_punct

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

    # ── Layer 10: LanguageTool deep-check (optional) ──────────────────────
    # Only runs if Java is available.  Catches things our rule-based layers
    # miss: punctuation nuances, preposition errors, word repetition, complex
    # article/determiner mistakes, etc.
    # We strip the terminal period we just added before passing to LT (LT
    # adds its own end-of-sentence analysis) then re-add it afterwards.
    try:
        _lt_input = result
        _had_period = _lt_input.endswith(".")
        if _had_period:
            _lt_input = _lt_input[:-1].rstrip()
        _lt_result, lt_fixes = _correct_with_languagetool(_lt_input)
        if lt_fixes:
            all_fixes.extend(lt_fixes)
            result = _lt_result
            if _had_period and not result.rstrip().endswith("."):
                result = result.rstrip() + "."
    except Exception:
        pass   # never let LT break the core pipeline

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
            # matching our expected POS — guards against Datamuse returning wrong POS.
            # EXCEPTION: skip this check for adverbs (RB/RBR/RBS) because WordNet
            # severely underrepresents adverbs — valid words like "rapidly", "broadly",
            # "merely" have no WN adverb synset but are perfect substitutes.
            is_adverb = pos_tag_str.startswith("RB")
            if wn_p and not is_adverb and not wn.synsets(cand, pos=wn_p):
                continue
            filtered.append(cand)

        if prefer_ly:
            ly   = [c for c in filtered if c.endswith("ly")]
            rest = [c for c in filtered if not c.endswith("ly")]
            filtered = ly + rest

        return filtered[:top_k]

    def rewrite(
        self,
        sentence: str,
        top_k: int = 10,
        stutter_patterns: list[str] | None = None,
        blocked_words: set[str] | None = None,
    ) -> dict:
        """
        Full pipeline:
          1. Tokenise + POS tag
          2. Identify protected positions (phrases + stop words)
          3. For each substitutable word:
             Gate A — if stutter patterns are active, only process words that
                      START with a trouble onset (or are personally blocked)
             a. Get raw candidates (engine, POS-filtered)
             b. Build inflected forms
             c. SBERT-rank contextually (semantic.py)
             Gate B — drop candidates that share the user's stutter onset (or are
                      blocked); ordering from the ranker is preserved
             d. Pick best surviving candidate
          4. Rebuild sentence
          5. Grammar notes

        stutter_patterns / blocked_words are the phoneme feature.  When BOTH are
        empty (the default) Gate A and Gate B are exact no-ops, so the legacy
        synonym behaviour is reproduced unchanged.

        Returns dict with full scoring metadata per substitution.
        """
        patterns = [p for p in (stutter_patterns or []) if p and p.strip()]
        blocked  = {w.lower() for w in (blocked_words or set()) if w and w.strip()}
        gating   = bool(patterns or blocked)

        tokens = word_tokenize(sentence)
        tags   = pos_tag(tokens)

        # Protected token positions
        phrase_protected = sem.protected_positions(tokens)

        new_tokens    = list(tokens)
        substitutions = []
        skipped       = []   # list of {"word", "reason"}

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

            # ── Gate A: stutter targeting ─────────────────────────────────────
            # Only when the user has supplied patterns/blocked words.  A word is
            # "risky" if it is personally blocked or its onset matches a pattern.
            # Non-risky words are left untouched and silently passed through.
            if gating:
                risky = (lower in blocked) or ph.matches_any(word, patterns)
                if not risky:
                    continue

            # Predicate participle after BE ("she is tired") → treat as an
            # adjective for synonym lookup, not a verb.  If it has no adjective
            # sense, skip it rather than offer misleading verb synonyms.
            eff_tag = tag
            if _is_predicate_participle(tags, i):
                if wn.synsets(lower, pos=wn.ADJ):
                    eff_tag = "JJ"
                else:
                    skipped.append({"word": word, "reason": "predicate adjective — left as is"})
                    continue

            base       = lemmatize(word, eff_tag)
            raw_cands  = self._raw_candidates(base, eff_tag, word, top_k=top_k)

            if not raw_cands:
                skipped.append({"word": word, "reason": "no synonyms found"})
                continue

            # Build inflected form map  {lemma → inflected_surface}
            inflected_map: dict[str, str] = {}
            for lemma in raw_cands:
                inf = inflect(lemma, eff_tag)
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

            # ── Gate B: phoneme firewall ──────────────────────────────────────
            # Annotate each ranked candidate with phoneme_ok (avoids the user's
            # stutter onset AND the blocked list).  Ranking order is untouched;
            # we just skip past same-onset candidates.  No patterns/blocked =>
            # phoneme_ok is always True, so this is a no-op.
            for s in scored:
                if not gating:
                    s["phoneme_ok"] = True
                    continue
                cand_lemma = s["lemma"].lower()
                bad = (cand_lemma in blocked
                       or ph.matches_any(s["inflected"], patterns)
                       or ph.matches_any(s["lemma"], patterns))
                s["phoneme_ok"] = not bad

            usable = [s for s in scored if s["accepted"] and s["phoneme_ok"]]
            if not usable:
                if gating and any(s["accepted"] for s in scored):
                    reason = "all synonyms share your stutter onset"
                else:
                    reason = "no valid synonym"
                skipped.append({"word": word, "reason": reason})
                continue

            best        = usable[0]
            new_tokens[i] = best["inflected"]

            substitutions.append({
                "original_word": word,
                "lemma":         base,
                "tag":           eff_tag,
                "position":      i,
                "chosen":        best["inflected"],
                "chosen_lemma":  best["lemma"],
                # Full scoring data for UI display (each entry carries phoneme_ok)
                "scored":        scored,          # all candidates with scores
                # Convenience: surviving lemma list for the dropdown
                "candidates":    [s["lemma"] for s in usable],
                "all_candidates": [s["lemma"] for s in scored],
                "sbert_active":  sem._sbert_ok,
            })

        rewritten     = _detokenize(new_tokens)
        grammar_notes = _grammar_notes(new_tokens, substitutions)

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


def _grammar_notes(rewritten_tokens: list[str], subs: list[dict]) -> list[str]:
    """
    Sanity-check verb substitutions by re-tagging the rebuilt tokens and
    comparing the tag AT EACH SUBSTITUTION POSITION (not by surface word — a
    word can appear twice, which a word-keyed lookup would conflate).
    """
    notes = []
    if not subs:
        return notes
    tags = pos_tag(rewritten_tokens)
    for sub in subs:
        if not sub["tag"].startswith("VB"):
            continue
        pos = sub["position"]
        if pos >= len(tags):
            continue
        actual = tags[pos][1]
        if actual != sub["tag"]:
            notes.append(
                f'"{sub["chosen"]}" re-tagged as {actual} '
                f'(expected {sub["tag"]}) — check verb agreement.'
            )
    if subs and not notes:
        notes.append("Grammar check passed — all substitutions correctly inflected.")
    return notes
