"""
reformulate.py — the consolidated reformulation engine (Architecture D′,
REFORMULATION_RESEARCH.md §24-31). Replaces grammar.py::SentenceRewriter and
rewrite/rewriter.py::DifficultyAwareRewriter as the live orchestrator; both
are kept in the repo, unused by app.py, until this engine is measured to be
at least as good on the failure-mode corpus (§30's migration plan) — this
module does not delete them.

Pipeline (§30):
    1. TAG    — which content words in each sentence are flagged by the
                profile (declared word / declared global sound onset match).
                Reuses engine.py/phonetic.py/semantic.py exactly as before;
                no new candidate source, no new scoring formula.
    2. Escalation decision — per sentence, BEFORE attempting substitution:
                escalate straight to restructuring if too many words are
                flagged at once (§24.D's new trigger) or too large a
                fraction of the sentence is flagged (§24.F's degenerate-
                profile cap) — both funnel into the SAME T5 escalation path,
                not a separate give-up path.
    3. SUBSTITUTE-AND-RANK — for sentences that don't pre-escalate: try a
                candidate for every flagged position. All-or-nothing per
                sentence — if any flagged position has no candidate that
                clears every gate, the whole sentence escalates instead of
                shipping a partial patchwork (§24.D).
    4. Tiered semantic verification (§24.A) — WordNet antonym rejection
                (free) -> SBERT threshold (existing) -> phoneme veto
                (existing). NLI is Strong-tier, not built here (§27).
    5. ESCALATE (T5, rephrase.py, unchanged code, new role) — generate
                candidates from the ORIGINAL sentence (not a partial
                substitution), each re-checked with the SAME phoneme veto,
                SBERT threshold, and a sentence-level negation-consistency
                check (semantic.negation_consistent) in place of the
                single-word antonym check, which doesn't apply to a
                freely-generated paraphrase.
    6. FINAL VERIFICATION — re-run the flagging check on the actual
                assembled output (not just per-candidate) and require it to
                have improved — SpeechAgent's "recovery rate" idea (§2.2),
                independently arrived at.
    7. METRICS — meaning preservation, difficulty (flag) reduction, and
                naturalness reported separately, never blended (Practice §10).

No model training. No new heavy dependency — antonym checking is stdlib
NLTK WordNet (already a dependency), edit-amount scoring is difflib
(already used elsewhere in this codebase, rephrase.py).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re

import nltk
from nltk import pos_tag, word_tokenize
from nltk.stem import PorterStemmer

import engine as engine_module
import phonetic as ph
import semantic as sem
import naturalness as nat
import rephrase
from freq import zipf_frequency as _zipf_frequency
from difficulty_profile import DifficultyProfile
from grammar import _SUBSTITUTABLE, _STOP, _wn_pos, lemmatize, inflect, _preserve_case, _detokenize, has_unknown_tokens

nltk.download("averaged_perceptron_tagger_eng", quiet=True)
nltk.download("punkt_tab", quiet=True)

_stemmer = PorterStemmer()


def _duplicates_sentence_word(candidate_word: str, tokens: list[str], exclude_index: int) -> bool:
    """Phase 11 (VALIDATION.md SS48, eval/r10b_failure_analysis.md) -- reject
    a substitution candidate that duplicates a word already present
    elsewhere in the sentence (e.g. "Solar" -> "Renewable" when the same
    sentence already says "renewable energy" later on, R10-038). Porter
    stemming, not plain lower-case equality, because several verified cases
    share a derivational root without being the same surface word
    ("recessions" next to "economic", R10-060) -- exact-string matching
    would miss those. Stopwords are skipped: they legitimately recur in
    almost every sentence and aren't the kind of duplication being caught
    here. Verified against R10-060's actual pair: Porter alone does NOT
    unify "economies"/"economic" (stems to "economi" vs "econom" --
    different derivational families under suffix-stripping), so a
    shared-long-prefix check is added alongside the stem check to catch
    that specific evidenced case; each is a cheap proxy, not a
    morphological analyzer, so both are kept deliberately narrow (6+
    shared characters, both words 7+ long) to limit false positives on
    unrelated words that merely start alike."""
    cand = candidate_word.lower()
    cand_stem = _stemmer.stem(cand)
    for j, tok in enumerate(tokens):
        if j == exclude_index:
            continue
        tok_lower = tok.lower()
        if tok_lower in _STOP or not tok_lower.isalpha():
            continue
        if tok_lower == cand or _stemmer.stem(tok_lower) == cand_stem:
            return True
        if len(cand) >= 7 and len(tok_lower) >= 7 and cand[:6] == tok_lower[:6]:
            return True
    return False


def _content_word_key(word: str) -> str:
    """Same duplicate-detection logic as _duplicates_sentence_word() above
    (Porter stem for short words, 6-char prefix for long ones, to catch
    derivational families like "economies"/"economic"), reshaped into a
    single canonical key per word instead of a pairwise comparison, so
    whole-sentence content can be counted into a Counter."""
    w = word.lower()
    if len(w) >= 7:
        return w[:6]
    return _stemmer.stem(w)


def _content_word_key_counts(text: str) -> Counter:
    """Splits on internal hyphens before keying, unlike the plain content-
    word regex used elsewhere in this file for leak-scanning/dictionary
    checks -- verified necessary, not assumed: "self-gravity" and
    "self-gravitational" both key to "self-g" (the hyphen-dominated
    6-char prefix) if kept as single hyphenated tokens, which hides the
    shared "gravit-" root that a bare "gravity" token elsewhere in the
    same text needs to be compared against (R10-025's actual case).
    Splitting each hyphenated word into its parts for THIS function only
    reproduces the same "gravit" key on both sides and lets the
    duplicate show up."""
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text.lower())
    counts = Counter()
    for w in words:
        for part in (w.split("-") if "-" in w else (w,)):
            if part and part not in _STOP:
                counts[_content_word_key(part)] += 1
    return counts


def introduces_new_duplicate(original_text: str, candidate_text: str) -> bool:
    """Phase 11C (VALIDATION.md SS51) -- the escalation-tier counterpart to
    _duplicates_sentence_word(), which only ever gated substitution-tier
    candidates. Named as a "concrete, evidenced" gap after Phase 11
    (VALIDATION.md SS48 FUTURE WORK) but dropped between write-ups before
    Phase 11B -- recorded here so it isn't dropped a second time.

    NOT a blanket "no repeated words" rule: R10-024's own ORIGINAL
    sentence already legitimately says "force" twice, so simple self-
    consistency would over-reject. Instead this counts each content
    word's key (see _content_word_key) in the ORIGINAL as a baseline and
    only flags a key that ALREADY occurred at least once in the original
    AND occurs MORE often in the candidate -- a net NEW duplication
    introduced by restructuring, not a pre-existing one, and critically
    not just "any word the candidate introduces that wasn't in the
    original" (that describes almost every legitimate paraphrase word --
    an earlier version of this function used exactly that looser rule
    and, caught by this phase's own test suite before being trusted,
    rejected ordinary one-for-one synonym restructurings wholesale:
    "requires"->"needs", "proceed"->"happen", neither a duplicate of
    anything, both flagged as one under the broken rule since the
    ORIGINAL simply had never said "needs" or "happen" at all).

    Verified against R10-061 ("the design, construction, and
    maintenance" -> "the design, design and maintenance") and R10-024
    ("...of equal magnitude..." -> introducing a third "force" where two
    were legitimate). R10-025's hyphenated case ("held together by
    self-gravity" -> "surrounded by self-gravitational gravity") needs
    _content_word_key_counts()'s hyphen-splitting (see its own docstring)
    to actually see the shared root -- without it, "self-gravity" and
    "self-gravitational" key identically to each other via their shared
    "self-g" prefix while the new bare "gravity" gets its own unrelated
    "gravit" key, and the defect is missed entirely."""
    orig_counts = _content_word_key_counts(original_text)
    cand_counts = _content_word_key_counts(candidate_text)
    return any(
        orig_counts.get(key, 0) > 0 and count > orig_counts[key]
        for key, count in cand_counts.items()
    )


@dataclass
class ReformulateSettings:
    sbert_threshold: float = None       # None -> use semantic.MIN_SEMANTIC at call time
    top_k: int = 10
    escalation_word_count: int = 2      # >this many flagged content words -> escalate (§24.D)
    degenerate_fraction: float = 0.6    # >this fraction of content words flagged -> escalate (§24.F)
    t5_candidates: int = 5
    phrase_window_radius: int = 5       # tokens of context on each side of an idiom span, for the phrase tier (§5 item 4)
    escalation_max_rounds: int = 4      # _try_escalation_v3 only (§38) — A2's own bound, unused by v1/v2 escalation


_ABBREVS = {
    "mr.", "mrs.", "ms.", "dr.", "prof.",
    "sr.", "jr.", "vs.", "etc.", "approx.",
    "fig.", "vol.", "no.", "dept.", "est.",
    "p.m.", "a.m.", "u.s.", "u.k.",
}


def split_sentences(text: str) -> list[str]:
    """Canonical sentence splitter — the one place this logic now lives.
    (Previously duplicated in app.py and rewrite/rewriter.py; both of those
    copies are dead code once app.py calls this module instead.)"""
    sentences: list[str] = []
    current: list[str] = []
    for word in (text or "").split():
        current.append(word)
        if word.endswith((".", "!", "?")) and word.lower() not in _ABBREVS:
            sentences.append(" ".join(current))
            current = []
    if current:
        sentences.append(" ".join(current))
    return [s for s in sentences if s.strip()]


_BE_FORMS = frozenset({"am", "is", "are", "was", "were", "be", "been", "being"})

# "Flat adverbs" -- identical surface form for the adjective and adverb
# senses (arrived late / was late; ran fast / was fast) -- the specific,
# well-established class of word nltk's tagger can mis-tag as RB even
# when it's functioning as a predicate adjective right after a copula.
# A curated list, not a general WordNet-sense check: tried checking
# "does WordNet list any adjective sense for this word" first and found
# it over-fires directly -- WordNet lists a rare satellite-adjective
# sense for "here" ("here.s.01", being here now), which reclassified
# "He was here." into treating "here" as an adjective, a real regression
# risk for a genuinely adverbial word. Same curated-list-over-general-
# detector tradeoff this project already makes for IDIOM_PHRASES.
_FLAT_ADVERBS: frozenset[str] = frozenset({
    "late", "early", "fast", "hard", "high", "low", "deep", "wide",
    "long", "near", "close", "right", "tight", "clean", "clear",
    "straight", "direct", "quick", "loud", "sharp", "smooth", "far",
})


def _correct_predicate_adjective_tags(tokens: list[str], tags: list[tuple]) -> list[tuple]:
    """nltk's tagger sometimes mis-tags a flat adverb as RB when it's
    actually a predicate adjective directly after a copula ("was late",
    not "arrived late"). Confirmed directly, not assumed: pos_tag() tags
    "late" RB in "The bus was late again this morning.", which then
    restricts candidate generation to adverb-sense synonyms only
    ("recently"/"lately"/"later") -- valid answers to the wrong question,
    producing "The bus was recently again" (a long-standing known bug,
    VALIDATION.md SS9.9/SS11.5's pair_13). Reclassifying the tag to JJ
    before candidate generation lets WordNet return actual predicate-
    adjective synonyms instead.

    Scoped to the curated `_FLAT_ADVERBS` list, not every RB-after-copula
    occurrence -- see that list's own comment for why a general WordNet-
    sense check was tried and rejected (it over-fired on "here"). Also
    requires direct adjacency to the copula, so a purely adverbial
    occurrence elsewhere in the sentence ("arrived late") is unaffected,
    and an intervening word ("n't", another adverb) between the copula
    and the flat adverb is not handled -- scoped to the evidenced case,
    not a general re-tagger."""
    corrected = list(tags)
    for i, (word, tag) in enumerate(tags):
        if tag != "RB" or i == 0:
            continue
        if word.lower() not in _FLAT_ADVERBS:
            continue
        if tokens[i - 1].lower() not in _BE_FORMS:
            continue
        corrected[i] = (word, "JJ")
    return corrected


def _local_context_window(tokens: list[str], index: int, radius: int = 6) -> str:
    """A small window of tokens around `index`, not the whole sentence —
    needed so two occurrences of the same word with different senses in
    ONE sentence ("He runs the company... before he runs three miles")
    get disambiguated independently. Using the full sentence as context
    (the first version of this fix) fed both occurrences the identical
    string, so both got the identical sense — confirmed directly as a
    regression via the Stage 6 corpus re-run, not assumed: it made an
    already-known failure mode (REFORMULATION_RESEARCH.md §17 row 5,
    VALIDATION.md §6.4's context-dependent-substitution case) measurably
    worse (SBERT similarity 0.9475 -> 0.8739) before this fix."""
    start = max(0, index - radius)
    end = min(len(tokens), index + radius + 1)
    return _detokenize(tokens[start:end])


def _raw_candidates(engine: "engine_module.SynonymEngine", lemma: str, pos_tag_str: str,
                     original_word: str, top_k: int, context: str | None = None) -> list[str]:
    """Same filtering as the old grammar.py::SentenceRewriter._raw_candidates
    (same-POS check via wn_pos, single-token only, prefer -ly forms for -ly
    adverbs) — reimplemented standalone here rather than depending on the
    class being discarded, so this module has no hidden coupling to it.

    `context`, when given, is used to disambiguate WHICH sense of `lemma`
    candidates should come from (semantic.disambiguate_synset() —
    REFORMULATION_PROBLEM_MAP.md §2.6 item 2), instead of unioning synonyms
    across every same-POS sense the way engine.py always did before. None
    (the default) preserves the exact prior all-senses behavior — callers
    that don't have context yet still work unchanged. Callers should pass a
    LOCAL window (_local_context_window()), not necessarily the whole
    sentence — see that function's docstring for why."""
    wn_p = _wn_pos(pos_tag_str)
    restrict_synsets = None
    if context is not None:
        picked = sem.disambiguate_synset(lemma, wn_p, context)
        if picked is not None:
            restrict_synsets = [picked]
    all_syns = engine.get_synonyms(
        lemma, top_k=top_k * 2, wn_pos=wn_p, restrict_synsets=restrict_synsets
    ).get(lemma, [])
    prefer_ly = pos_tag_str.startswith("RB") and original_word.lower().endswith("ly")

    from nltk.corpus import wordnet as wn
    filtered = []
    for cand in all_syns:
        if cand in (lemma, original_word.lower()):
            continue
        if " " in cand:
            continue
        is_adverb = pos_tag_str.startswith("RB")
        if wn_p and not is_adverb and not wn.synsets(cand, pos=wn_p):
            continue
        filtered.append(cand)

    if prefer_ly:
        ly = [c for c in filtered if c.endswith("ly")]
        rest = [c for c in filtered if not c.endswith("ly")]
        filtered = ly + rest

    return filtered[:top_k]


def _flagged_positions(tokens: list[str], tags: list[tuple], profile: DifficultyProfile) -> list[dict]:
    """Which substitutable, unprotected positions does the profile flag,
    and why (declared word / global sound onset) — the 'tag' stage."""
    phrase_protected = sem.protected_positions(tokens)
    sound_patterns = profile.sound_values()
    flagged = []
    for i, (word, tag) in enumerate(tags):
        lower = word.lower()
        if not re.match(r"[a-z]", lower):
            continue
        if tag not in _SUBSTITUTABLE or lower in _STOP:
            continue
        if i in phrase_protected:
            continue
        word_entry = profile.find_word(lower)
        sound_hit = ph.matches_any(word, sound_patterns)
        if word_entry is not None or sound_hit:
            flagged.append({
                "position": i, "word": word, "tag": tag,
                "word_entry": word_entry, "sound_hit": sound_hit,
            })
    return flagged


def _idiom_protected_matches(tokens: list[str], tags: list[tuple], profile: DifficultyProfile) -> list[dict]:
    """Positions inside an idiom/fixed-expression span that would
    otherwise match the profile — never substitutable (excluded from
    _flagged_positions()'s result the same as before), but the match
    itself must stay visible: counted in _flagged_word_count() and
    reported in reformulate()'s `skipped` list, rather than silently
    treated as if the difficulty were never there. See
    semantic.idiom_protected_positions()'s docstring for why this needs
    its own check instead of reusing protected_positions().

    Entries carry `tag`/`word_entry`/`sound_hit` (same shape as
    _flagged_positions()'s entries, not just position/word) so
    _try_phrase_replacement() can reuse _trigger_reasons()/
    feedback_targets() for attribution instead of inventing a parallel
    scheme (REFORMULATION_PROBLEM_MAP.md SS5 item 4)."""
    idiom_protected = sem.idiom_protected_positions(tokens)
    if not idiom_protected:
        return []
    sound_patterns = profile.sound_values()
    matches = []
    for i, (word, tag) in enumerate(tags):
        if i not in idiom_protected:
            continue
        lower = word.lower()
        if not re.match(r"[a-z]", lower):
            continue
        word_entry = profile.find_word(lower)
        sound_hit = ph.matches_any(word, sound_patterns)
        if word_entry is not None or sound_hit:
            matches.append({
                "position": i, "word": word, "tag": tag,
                "word_entry": word_entry, "sound_hit": sound_hit,
            })
    return matches


def _idiom_skip_entries(matches: list[dict], exclude_positions: set[int] | None = None) -> list[dict]:
    """Build `skipped` entries for idiom-protected matches — factored out
    since this now fires from three places (phrase-tier failure, phrase-
    tier partial success leaving other spans untouched, and the
    unchanged mixed-case path)."""
    exclude = exclude_positions or set()
    return [
        {
            "word": m["word"], "position": m["position"],
            "reason": "part of a fixed expression — left unchanged to avoid breaking it",
        }
        for m in matches if m["position"] not in exclude
    ]


def _substitutable_content_word_count(tags: list[tuple], phrase_protected: set) -> int:
    count = 0
    for i, (word, tag) in enumerate(tags):
        if not re.match(r"[a-z]", word.lower()):
            continue
        if tag not in _SUBSTITUTABLE or word.lower() in _STOP:
            continue
        if i in phrase_protected:
            continue
        count += 1
    return max(count, 1)


def _try_substitution(
    sentence: str, tokens: list[str], tags: list[tuple], flagged: list[dict],
    profile: DifficultyProfile, engine: "engine_module.SynonymEngine", settings: ReformulateSettings,
) -> tuple[list[str] | None, list[dict], list[dict]]:
    """All-or-nothing: every flagged position must find a candidate that
    clears every gate, or this returns (None, ..., ...) so the caller
    escalates the whole sentence instead of shipping a patchwork (§24.D)."""
    new_tokens = list(tokens)
    changes: list[dict] = []
    skipped: list[dict] = []
    min_semantic = settings.sbert_threshold if settings.sbert_threshold is not None else sem.MIN_SEMANTIC

    for item in flagged:
        i, word, tag = item["position"], item["word"], item["tag"]
        base = lemmatize(word, tag)
        wn_p = _wn_pos(tag)
        context_window = _local_context_window(tokens, i)
        raw_cands = _raw_candidates(engine, base, tag, word, settings.top_k, context=context_window)
        if not raw_cands:
            skipped.append({"word": word, "position": i, "reason": "no candidates found"})
            return None, changes, skipped

        inflected_map = {lemma: _preserve_case(word, inflect(lemma, tag)) for lemma in raw_cands}
        scored = sem.rank_candidates_contextually(
            original_sentence=sentence, word_to_replace=word, token_index=i,
            tokens=list(new_tokens), candidates=raw_cands, inflected_forms=inflected_map,
            min_semantic=min_semantic,
        )

        usable = None
        for s in scored:
            if not s["accepted"]:
                continue
            if sem.is_known_antonym(base, s["lemma"], wn_p):
                s["antonym_rejected"] = True
                continue
            if ph.matches_any(s["inflected"], profile.sound_values()):
                continue
            if _duplicates_sentence_word(s["inflected"], new_tokens, i):
                continue
            if sem.blocked_pair(base, s["lemma"]):
                s["blocked_pair_rejected"] = True
                continue
            if sem.is_number_word_mismatch(base, s["lemma"]):
                s["number_word_rejected"] = True
                continue
            if sem.is_mass_noun_substitution(base, s["lemma"]):
                # Phase 11C (VALIDATION.md SS51) -- no countability signal
                # existed anywhere in this codebase; a specific blocklist
                # pair (professor->faculty, Phase 11B) just gets bypassed
                # by the next bad candidate (R10-073: moved to "teacher").
                # This closed set catches the countable-noun-to-mass-noun
                # shape directly instead of chasing one pair at a time.
                s["mass_noun_rejected"] = True
                continue
            if has_unknown_tokens(s["inflected"]):
                # Phase 11B (VALIDATION.md SS50) -- found during this
                # phase's own re-verification: "weekdays"->"dayss" is a
                # SUBSTITUTION-tier garbled token, not an escalation one --
                # inflect()'s own documented NNS fallback (lemma + "s")
                # double-pluralizes when pyinflect fails on an
                # already-plural lemma. Not caught by the escalation/
                # phrase-tier gates below since this candidate never goes
                # through either path.
                s["unknown_token_rejected"] = True
                continue
            if profile.find_word(s["inflected"].lower()) is not None:
                # A candidate must never itself be one of the profile's
                # OTHER declared-difficult words. Not a hypothetical case:
                # "reviewed"/"examined" both declared difficult in one
                # sentence -- WSD's more precise ranking (item 2) picked
                # "examined" as the top candidate FOR "reviewed", silently
                # reintroducing a declared difficulty via the replacement
                # itself. REFORMULATION_RESEARCH.md §17's "no interaction
                # modeling" limitation, concretely reproduced by the Stage 6
                # corpus re-run, not hypothesized (VALIDATION.md §11).
                continue
            usable = s
            break

        if usable is None:
            skipped.append({"word": word, "position": i, "reason": "no candidate passed verification"})
            return None, changes, skipped

        new_tokens[i] = usable["inflected"]
        changes.append({
            "sentence_index": None,  # filled in by caller
            "position": i,
            "span_text": word,
            "original": word,
            "replacement": usable["inflected"],
            "source": "substitution",
            "triggered_by": _trigger_reasons(item),
            "verification": {
                "antonym_check": "pass",
                "sbert_sim": usable["semantic_sim"],
                "nli": "not_run",
                "phoneme_ok": True,
                "difficulty_before": round(ph.word_difficulty(word), 4),
                "difficulty_after": round(ph.word_difficulty(usable["inflected"]), 4),
            },
        })

    if changes:
        # Phase 11C (VALIDATION.md SS51) -- per R45's own recommendation
        # (VALIDATION.md SS36.3: "apply the combined NLI... validator to
        # the final assembled output of both tiers, not just escalation's"),
        # one check on the fully assembled sentence, not per-candidate --
        # bounds cost to one model call per successful substitution attempt
        # rather than one per candidate per position. R10-005/R10-101 (two
        # of this gap's directly evidenced cases) are both substitution-
        # tier, so this tier needs the same entailment check escalation/
        # phrase-tier just got, applied once the whole sentence is known
        # rather than word-by-word (no single word-level antonym check can
        # see a reversal that only emerges from the combination, or a
        # role-flip like "surprised"->"surprising" that isn't a lexical
        # antonym at all). All-or-nothing, matching this function's own
        # existing philosophy: a contradiction here fails the whole
        # attempt, not just the last change.
        assembled = _detokenize(new_tokens)
        nli = sem.logical_consistency_check(sentence, assembled)
        if nli is not None and nli["contradiction"]:
            skipped.append({"word": None, "position": None, "reason": "final sentence failed NLI contradiction check"})
            return None, changes, skipped

    return new_tokens, changes, skipped


def _trigger_reasons(flagged_item: dict) -> list[str]:
    reasons = []
    if flagged_item["word_entry"] is not None:
        reasons.append("declared_word")
        if flagged_item["word_entry"].problem_phones:
            reasons.append("word_specific_pattern")
    if flagged_item["sound_hit"]:
        reasons.append("global_sound")
    return reasons


def _try_escalation(
    sentence: str, flagged: list[dict], profile: DifficultyProfile, settings: ReformulateSettings,
) -> tuple[str | None, dict | None]:
    """Generate-then-verify restructuring (§24.E) — every candidate is
    re-checked with the same SBERT threshold used for substitution, plus a
    sentence-level negation check standing in for the single-word antonym
    check (which doesn't apply to a freely generated paraphrase).

    The word-block set is the *substitutable* words this sentence actually
    flagged (`flagged`), not the full declared-word list: a declared-difficult
    word that isn't substitutable in this position (a numeral, a proper noun
    — anything _SUBSTITUTABLE excludes) is equally unfixable by restructuring,
    so blocking on it would only ever reject every candidate T5 produces.

    Architecture Go/No-Go Step 1 (VALIDATION.md SS52) -- generation now uses
    rephrase.generate_candidates_phoneme_constrained() (R45 Prototype 2,
    VALIDATION.md SS36.2/SS37), not the plain post-hoc-rejection generator:
    T5 IS now told about phonemes, via a LogitsProcessor that kills a beam
    the instant its in-progress text matches a blocked sound, instead of
    generating a full candidate and rejecting it afterward. Measured (on
    its own validation corpus, not yet re-measured on this one) to take the
    leak-free rate from 4% to 100% and the fraction of dense-profile
    sentences producing ANY usable candidate from ~9-13% to 52% -- this
    project's single largest measured generation-side improvement, sitting
    unused in the experimental _try_escalation_v2()/v3() path (reachable
    only via an opt-in app.py toggle) since R46. Ported here exactly as
    built, per explicit instruction not to redesign it: same call v2 already
    makes, every gate below (including the ones added after v2 was written)
    left unchanged -- this is a generation-source swap, not a gate change.
    The phoneme/blocked-word leak re-scan a few lines down is kept as a
    safety net even though this constraint should already guarantee no
    leaks, matching v2's own established precedent for the same reasoning."""
    min_semantic = settings.sbert_threshold if settings.sbert_threshold is not None else sem.MIN_SEMANTIC
    blocked = {item["word"].lower() for item in flagged}
    candidates, gen_stats = rephrase.generate_candidates_phoneme_constrained(
        sentence, k=settings.t5_candidates, blocked_words=blocked, blocked_patterns=profile.sound_values(),
    )

    best = None
    for cand in candidates:
        if cand.strip().lower() == sentence.strip().lower():
            continue  # T5 unavailable or returned the input unchanged — not a real alternative
        sim = sem.semantic_similarity(cand, sentence)
        # Matches semantic.rank_candidates_contextually's own documented
        # fallback: SBERT unavailable -> don't gate on it, don't rank on it.
        if sim is not None and sim < min_semantic:
            continue
        if not sem.negation_consistent(sentence, cand):
            continue
        content_words = re.findall(r"[A-Za-z][A-Za-z'-]*", cand)
        if any(ph.matches_any(w, profile.sound_values()) or w.lower() in blocked for w in content_words):
            continue
        # Phase 11 (VALIDATION.md SS48, eval/r10b_failure_analysis.md) --
        # protected_positions() only ever gated substitution-tier candidate
        # generation; free restructuring here was never checked against the
        # same fixed-term list, and Phase 10B found this is how most of the
        # verified fixed-term breaks happened ("magma chamber" -> "magma
        # cave", etc.). A dropped fixed term is a meaning change, not a
        # style choice, so it's rejected the same as a failed SBERT/negation
        # check rather than merely down-ranked.
        if sem.dropped_protected_phrases(sentence, cand):
            continue
        # Phase 11B (VALIDATION.md SS50) -- nothing previously checked
        # whether T5's freely generated text was made of real words.
        # has_unknown_tokens() reuses grammar.py's existing spellcheck
        # infrastructure (previously input-side only, via sanitize_input())
        # to catch exactly the garbled-token defects Phase 10B and Phase
        # 11's own re-verification both found ("thermonuklear", "rockyer",
        # "goodss", "dayss", "otherrer") -- a non-word is never an
        # acceptable simplification, rejected here rather than merely
        # down-ranked.
        if has_unknown_tokens(cand):
            continue
        # Phase 11C (VALIDATION.md SS51) -- _duplicates_sentence_word()
        # only ever gated substitution-tier candidates; free restructuring
        # here was never checked for a NEW word repetition it introduces
        # ("design, construction" -> "design, design", R10-061; a third
        # "force" where two were legitimate, R10-024). Named as a gap
        # after Phase 11 but dropped before Phase 11B's plan -- closed now.
        if introduces_new_duplicate(sentence, cand):
            continue
        # Phase 11C (VALIDATION.md SS51) -- is_known_antonym() is word-level
        # and lexical, so it structurally cannot catch a candidate that
        # reverses the ORIGINAL's claim without using a WordNet antonym pair
        # (R10-005: "reabsorbed" -> "eliminated" cleared antonym_check="pass"
        # since the two aren't listed antonyms, despite being a genuine
        # process-reversal); negation_consistent() only counts negation
        # MARKERS, so a reversal with none present (R10-088: "skipped the
        # museum" -> "went to the museums instead") is equally invisible to
        # it. This is the exact gate R45/R46 already designed, built, and
        # validated for this -- it was gating in the experimental
        # _try_escalation_v3() (reformulate_v2(), never wired to app.py's
        # default path) the whole time; porting it here is what actually
        # ships it.
        nli = sem.logical_consistency_check(sentence, cand)
        if nli is not None and nli["contradiction"]:
            continue
        # Phase 11C (VALIDATION.md SS51) -- none of the checks above verify
        # whether the generated sentence actually PARSES as grammatical
        # English (R10-002 "esophageal" filling a noun slot; R10-013
        # singular subject/plural verb; R10-061 "Civil engineers is").
        # grammar_issue_count() (LanguageTool, already a dependency) was
        # built and validated for exactly this (R45, VALIDATION.md SS36.1)
        # but only ever reported, never gated, and only in reformulate_v2()'s
        # non-production output. Measured directly against this phase's own
        # evidence before wiring this in (not assumed): 2/7 evidenced cases
        # actually caught (R10-013-shaped and R10-108-shaped patterns) --
        # real but partial recall, consistent with R45's own ~25% figure;
        # it will not catch the majority of remaining defects, only the
        # smaller GRAMMAR-labeled slice. Fails closed (None) if the tool
        # isn't loaded, same as every other reported-only signal in this
        # module -- never blocks output just because the checker itself is
        # unavailable.
        if (sem.grammar_issue_count(cand) or 0) > 0:
            continue
        rank_score = sim if sim is not None else -1.0
        if best is None or (rank_score > best["rank_score"]):
            best = {"text": cand, "sim": sim, "rank_score": rank_score, "nli": nli}

    if best is None:
        return None, None

    return best["text"], {
        "sentence_index": None,
        "position": None,
        "span_text": sentence,
        "original": sentence,
        "replacement": best["text"],
        "source": "restructuring",
        "triggered_by": ["multiple_difficulties_or_no_valid_substitution"],
        "verification": {
            "antonym_check": "n/a_sentence_level",
            "sbert_sim": round(best["sim"], 4) if best["sim"] is not None else None,
            "nli": best["nli"] if best["nli"] is not None else "not_run",
            "phoneme_ok": True,
            "difficulty_before": round(ph.sentence_difficulty(re.findall(r"[A-Za-z]+", sentence)), 4),
            "difficulty_after": round(ph.sentence_difficulty(re.findall(r"[A-Za-z]+", best["text"])), 4),
            "beam_kills": gen_stats.get("beam_kills", 0),
        },
    }


def _try_escalation_v2(
    sentence: str, flagged: list[dict], profile: DifficultyProfile, settings: ReformulateSettings,
) -> tuple[str | None, dict | None]:
    """R45's redesigned escalation path (VALIDATION.md §36.2/§36.3) — same
    contract and same three post-generation gates as _try_escalation()
    above, but candidates come from rephrase.generate_candidates_
    phoneme_constrained() instead of generate_candidates(): a decoding-
    time constraint kills a beam the moment its in-progress text matches
    a blocked sound, instead of generating a full candidate and rejecting
    it after the fact. Measured result on this project's escalation-
    invoked corpus: leak-free 4% -> 100%, cases with >=1 accepted
    candidate 9% -> 52% (VALIDATION.md §36.2).

    Deliberately a separate function, not a parameter on _try_escalation()
    — reformulate() (production, unchanged) keeps calling the original;
    only reformulate_v2() (this module's new, not-yet-wired-to-app.py
    entry point) calls this one."""
    min_semantic = settings.sbert_threshold if settings.sbert_threshold is not None else sem.MIN_SEMANTIC
    blocked = {item["word"].lower() for item in flagged}
    candidates, gen_stats = rephrase.generate_candidates_phoneme_constrained(
        sentence, k=settings.t5_candidates, blocked_words=blocked, blocked_patterns=profile.sound_values(),
    )

    best = None
    for cand in candidates:
        if cand.strip().lower() == sentence.strip().lower():
            continue  # T5 unavailable or returned the input unchanged — not a real alternative
        sim = sem.semantic_similarity(cand, sentence)
        if sim is not None and sim < min_semantic:
            continue
        if not sem.negation_consistent(sentence, cand):
            continue
        content_words = re.findall(r"[A-Za-z][A-Za-z'-]*", cand)
        if any(ph.matches_any(w, profile.sound_values()) or w.lower() in blocked for w in content_words):
            continue
        rank_score = sim if sim is not None else -1.0
        if best is None or (rank_score > best["rank_score"]):
            best = {"text": cand, "sim": sim, "rank_score": rank_score}

    if best is None:
        return None, None

    return best["text"], {
        "sentence_index": None,
        "position": None,
        "span_text": sentence,
        "original": sentence,
        "replacement": best["text"],
        "source": "restructuring_v2",
        "triggered_by": ["multiple_difficulties_or_no_valid_substitution"],
        "verification": {
            "antonym_check": "n/a_sentence_level",
            "sbert_sim": round(best["sim"], 4) if best["sim"] is not None else None,
            "nli": "not_run",  # filled in by reformulate_v2()'s post-assembly validation pass
            "phoneme_ok": True,
            "difficulty_before": round(ph.sentence_difficulty(re.findall(r"[A-Za-z]+", sentence)), 4),
            "difficulty_after": round(ph.sentence_difficulty(re.findall(r"[A-Za-z]+", best["text"])), 4),
            "beam_kills": gen_stats.get("beam_kills", 0),
        },
    }


def _try_escalation_v3(
    sentence: str, flagged: list[dict], profile: DifficultyProfile, settings: ReformulateSettings,
) -> tuple[str | None, dict | None]:
    """Combines the two mechanisms that each independently worked, tested
    together for the first time (VALIDATION.md §38): _try_escalation_v2's
    phoneme-aware decoding (leak-free 4% -> 100%, R45 Prototype 2) with
    A2's iterative generate-verify-regenerate loop (accept rate 9% -> 26%
    on its own, VALIDATION.md §36.2's Part 2/§35's A2 finding).

    A2's own retry signal (re-block whatever LEAKED) doesn't apply once
    leaks are structurally prevented every round by the phoneme
    processor. **A first version of this function re-blocked every
    content word of the best below-threshold near-miss instead — found,
    by direct tracing, to be a real bug, not a safe adaptation**: by
    round 2 that blocks nearly the sentence's entire ordinary vocabulary,
    and T5 degenerates into gibberish word-lists within 2-3 rounds
    (VALIDATION.md §38.2). Fixed here: at most `_MAX_NEW_BLOCKS_PER_ROUND`
    new words per round, non-stopwords only, preferring the RAREST (most
    content-specific, by Zipf frequency) words in the near-miss — a
    narrow, targeted nudge toward a different lexical choice, not a
    vocabulary lockout.

    Same three post-generation gates as _try_escalation_v2 every round
    (SBERT, negation, a leak re-check kept as a safety net even though
    the phoneme processor should already guarantee it). Bounded to
    `settings.escalation_max_rounds` calls, same discipline as A2."""
    min_semantic = settings.sbert_threshold if settings.sbert_threshold is not None else sem.MIN_SEMANTIC
    literal_blocked = {item["word"].lower() for item in flagged}
    sound_patterns = profile.sound_values()
    extra_blocked: set[str] = set()
    total_beam_kills = 0

    for round_i in range(settings.escalation_max_rounds):
        candidates, gen_stats = rephrase.generate_candidates_phoneme_constrained(
            sentence, k=settings.t5_candidates,
            blocked_words=literal_blocked | extra_blocked, blocked_patterns=sound_patterns,
        )
        total_beam_kills += gen_stats.get("beam_kills", 0)

        best = None
        best_near_miss = None  # highest-sim candidate this round, even if rejected — seeds next round's block set
        for cand in candidates:
            if cand.strip().lower() == sentence.strip().lower():
                continue
            sim = sem.semantic_similarity(cand, sentence)
            content_words = re.findall(r"[A-Za-z][A-Za-z'-]*", cand)
            leaked = any(ph.matches_any(w, sound_patterns) or w.lower() in literal_blocked for w in content_words)
            rank_score = sim if sim is not None else -1.0
            if best_near_miss is None or rank_score > best_near_miss["rank_score"]:
                best_near_miss = {"text": cand, "sim": sim, "rank_score": rank_score, "words": content_words}
            if sim is not None and sim < min_semantic:
                continue
            if not sem.negation_consistent(sentence, cand):
                continue
            if leaked:
                continue  # should not happen given the phoneme processor — safety net, not the expected path
            if best is not None and rank_score <= best["rank_score"]:
                continue  # already have a better-ranked candidate; skip the extra NLI call
            # A REAL gate here, not just a report (VALIDATION.md §38.3): a
            # live case found during this same pass, "rational"->
            # "irrational", cleared SBERT/negation/leak cleanly (a direct
            # antonym is still a fluent, meaning-similar-looking sentence)
            # and was only caught by NLI — reported-only would have
            # shipped it with nothing but a dismissable banner. Escalation
            # has no per-word antonym check at all (free-form text, no
            # fixed position to check against); this is the one signal
            # standing between a sentence-level antonym flip and the
            # user, so it gates here, unlike reformulate_v2()'s existing
            # whole-output validation pass (kept, for the classes NLI
            # doesn't cover, e.g. grammar).
            nli = sem.logical_consistency_check(sentence, cand)
            if nli is not None and nli["contradiction"]:
                continue
            best = {"text": cand, "sim": sim, "rank_score": rank_score, "nli": nli}

        if best is not None:
            return best["text"], {
                "sentence_index": None, "position": None, "span_text": sentence,
                "original": sentence, "replacement": best["text"], "source": "restructuring_v3",
                "triggered_by": ["multiple_difficulties_or_no_valid_substitution"],
                "verification": {
                    "antonym_check": "n/a_sentence_level",
                    "sbert_sim": round(best["sim"], 4) if best["sim"] is not None else None,
                    "nli": best["nli"],
                    "phoneme_ok": True,
                    "difficulty_before": round(ph.sentence_difficulty(re.findall(r"[A-Za-z]+", sentence)), 4),
                    "difficulty_after": round(ph.sentence_difficulty(re.findall(r"[A-Za-z]+", best["text"])), 4),
                    "beam_kills": total_beam_kills,
                    "rounds_used": round_i + 1,
                },
            }

        if best_near_miss is None:
            break  # T5 produced nothing but the input itself — no signal to iterate on
        candidate_words = {w.lower() for w in best_near_miss["words"]} - literal_blocked - extra_blocked - _STOP
        if not candidate_words:
            break  # converged — nothing new (non-stopword) to block, another round won't explore anything different
        # Rarest words first — a cheap, content-specificity proxy for "most
        # likely to be the actual source of meaning drift," per this
        # function's own docstring on why blocking everything was wrong.
        ranked = sorted(candidate_words, key=lambda w: _zipf_frequency(w, "en"))
        new_words = set(ranked[:_MAX_NEW_BLOCKS_PER_ROUND])
        extra_blocked |= new_words

    return None, None


_MAX_NEW_BLOCKS_PER_ROUND = 2


def _try_phrase_replacement(
    sentence: str, tokens: list[str], span: tuple[int, int], span_matches: list[dict],
    profile: DifficultyProfile, settings: ReformulateSettings,
) -> dict | None:
    """Phrase-level replacement tier (REFORMULATION_PROBLEM_MAP.md §3.8/
    §5 item 4) — the middle ground between "protect the idiom and leave
    it alone" (§2.4/R19) and "restructure the whole sentence" (§2.8):
    when a flagged word sits inside a fixed expression, try replacing
    just the expression (plus a little local context) with an
    equivalent, easier phrase, before giving up on the sentence.

    Reuses rephrase.generate_candidates() unchanged — same model, same
    `bad_words_ids` blocking — but scoped to a local window around the
    span (settings.phrase_window_radius on each side) rather than the
    whole sentence, per §3.8's own recommendation (the checkpoint in use
    is fine-tuned for whole-sentence paraphrase, not sentinel-infilling,
    so a real span-only splice would need a different model; whole-
    window replacement reuses proven machinery instead). Every candidate
    is verified against the FULL resulting sentence — never the window
    in isolation — with the exact same three checks _try_escalation
    already uses (SBERT similarity vs. the original *sentence*,
    negation consistency, a full-sentence phoneme/blocked-word leak
    scan), plus the R20 candidate-collision check (§2.7). Returns None
    if nothing clears every gate — the caller leaves the span alone,
    identical to R19's pre-existing behavior."""
    start, end = span
    blocked = {m["word"].lower() for m in span_matches}
    min_semantic = settings.sbert_threshold if settings.sbert_threshold is not None else sem.MIN_SEMANTIC

    radius = settings.phrase_window_radius
    window_start = max(0, start - radius)
    window_end = min(len(tokens), end + radius)
    window_text = _detokenize(tokens[window_start:window_end])

    candidates = rephrase.generate_candidates(window_text, k=settings.t5_candidates, blocked_words=blocked)

    best = None
    for cand in candidates:
        if cand.strip().lower() == window_text.strip().lower():
            continue  # T5 unavailable or returned the window unchanged -- not a real alternative
        try:
            replacement_tokens = word_tokenize(cand)
        except Exception:
            replacement_tokens = re.findall(r"[A-Za-z][A-Za-z'-]*|[.,!?;:]", cand)
        candidate_tokens = tokens[:window_start] + replacement_tokens + tokens[window_end:]
        candidate_sentence = _detokenize(candidate_tokens)

        sim = sem.semantic_similarity(candidate_sentence, sentence)
        # Matches _try_escalation's own documented fallback: SBERT
        # unavailable -> don't gate on it, don't rank on it.
        if sim is not None and sim < min_semantic:
            continue
        if not sem.negation_consistent(sentence, candidate_sentence):
            continue
        content_words = re.findall(r"[A-Za-z][A-Za-z'-]*", candidate_sentence)
        if any(ph.matches_any(w, profile.sound_values()) or w.lower() in blocked for w in content_words):
            continue
        if any(profile.find_word(w.lower()) is not None for w in content_words):
            continue  # never reintroduce another declared word (§2.7/R20)
        # Phase 11 re-verification (VALIDATION.md SS49) -- the same gap
        # _try_escalation() had: this splices a locally-generated window
        # into the sentence, so any OTHER protected phrase living outside
        # the window survives automatically (the splice copies it
        # verbatim), but a protected phrase that overlaps the window
        # itself needs the same post-generation check _try_escalation()
        # uses. When the flagged word IS part of the protected phrase
        # being replaced (blocked_words above already forces T5 to avoid
        # it), this will correctly never find a preserving candidate --
        # the sentence is left unchanged and reported as skipped, an
        # honest refusal rather than shipping a broken phrase
        # ("golden brown" -> "gold brown", "with distinction" -> "with
        # distinguished", "money supply" -> "money market", all observed
        # SEVERE defects this closes).
        if sem.dropped_protected_phrases(sentence, candidate_sentence):
            continue
        # Phase 11B (VALIDATION.md SS50) -- same reasoning as
        # _try_escalation()'s has_unknown_tokens() gate: this window is
        # also T5-generated free text, so it needs the same real-word
        # check, not just the sentence-level ones above.
        if has_unknown_tokens(candidate_sentence):
            continue
        # Phase 11C (VALIDATION.md SS51) -- same reasoning as
        # _try_escalation()'s introduces_new_duplicate() gate: this
        # splices T5-generated free text back into the sentence too, so
        # it can just as easily introduce a new word repetition.
        if introduces_new_duplicate(sentence, candidate_sentence):
            continue
        # Phase 11C (VALIDATION.md SS51) -- same reasoning as
        # _try_escalation()'s NLI gate: this is also free-text generation
        # spliced back into the sentence, so it needs the same
        # entailment/contradiction check, not just the negation-marker
        # count above.
        nli = sem.logical_consistency_check(sentence, candidate_sentence)
        if nli is not None and nli["contradiction"]:
            continue
        # Phase 11C (VALIDATION.md SS51) -- same reasoning as
        # _try_escalation()'s grammar_issue_count() gate.
        if (sem.grammar_issue_count(candidate_sentence) or 0) > 0:
            continue
        rank_score = sim if sim is not None else -1.0
        if best is None or rank_score > best["rank_score"]:
            best = {"tokens": candidate_tokens, "text": candidate_sentence, "sim": sim, "rank_score": rank_score, "nli": nli}

    if best is None:
        return None

    triggered: list[str] = []
    for m in span_matches:
        for r in _trigger_reasons(m):
            if r not in triggered:
                triggered.append(r)

    return {
        "new_tokens": best["tokens"],
        "change": {
            "sentence_index": None,
            "position": start,
            "span_text": _detokenize(tokens[start:end]),
            "original": sentence,
            "replacement": best["text"],
            "source": "phrase",
            "triggered_by": triggered,
            "matched_words": [m["word"] for m in span_matches],
            "verification": {
                "antonym_check": "n/a_phrase_level",
                "sbert_sim": round(best["sim"], 4) if best["sim"] is not None else None,
                "nli": best["nli"] if best["nli"] is not None else "not_run",
                "phoneme_ok": True,
                "difficulty_before": round(ph.sentence_difficulty(re.findall(r"[A-Za-z]+", sentence)), 4),
                "difficulty_after": round(ph.sentence_difficulty(re.findall(r"[A-Za-z]+", best["text"])), 4),
            },
        },
    }


def _flagged_word_count(text: str, profile: DifficultyProfile) -> int:
    """The 'recovery rate' check (§2.2/§24) — how many content words in
    *text* the profile would flag right now. Used both to decide whether a
    sentence needs attention and, re-run on the final output, as the
    reformulation-effectiveness metric."""
    try:
        tokens = word_tokenize(text)
    except Exception:
        tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    tags = _correct_predicate_adjective_tags(tokens, pos_tag(tokens))
    return len(_flagged_positions(tokens, tags, profile)) + len(_idiom_protected_matches(tokens, tags, profile))


def reformulate(text: str, profile: DifficultyProfile, settings: ReformulateSettings | None = None) -> dict:
    """The engine's public entry point — §25's contract."""
    settings = settings or ReformulateSettings()
    sem.load_sbert()  # idempotent; no-op if already loaded or already failed once
    engine = engine_module.SynonymEngine()

    sentences = split_sentences(text)
    rebuilt: list[str] = []
    all_changes: list[dict] = []
    all_skipped: list[dict] = []
    any_flagged = False

    for sid, sentence in enumerate(sentences):
        try:
            tokens = word_tokenize(sentence)
        except Exception:
            tokens = re.findall(r"[A-Za-z][A-Za-z'-]*|[.,!?;:]", sentence)
        tags = _correct_predicate_adjective_tags(tokens, pos_tag(tokens))
        phrase_protected = sem.protected_positions(tokens)
        flagged = _flagged_positions(tokens, tags, profile)
        idiom_matches = _idiom_protected_matches(tokens, tags, profile)

        if not flagged and not idiom_matches:
            rebuilt.append(sentence)
            continue

        any_flagged = True

        if not flagged and idiom_matches:
            # The ONLY difficulty in this sentence is idiom-locked --
            # word-level substitution is trivially impossible (nothing
            # substitutable). Try a phrase-level replacement before
            # giving up (§3.8/§5 item 4) instead of jumping straight to
            # either "leave it alone" (R19's prior behavior) or a
            # whole-sentence restructure. One span per sentence -- the
            # common, observed case (VALIDATION.md §9's pilot never saw
            # two idiom spans in one sentence); any additional match
            # falls back to the existing skip behavior rather than
            # chaining replacements against shifting token indices.
            spans = sem.idiom_spans(tokens)
            phrase_result = None
            handled_span = None
            if spans:
                span = spans[0]
                span_matches = [m for m in idiom_matches if span[0] <= m["position"] < span[1]]
                if span_matches:
                    phrase_result = _try_phrase_replacement(
                        sentence, tokens, span, span_matches, profile, settings
                    )
                    if phrase_result is not None:
                        handled_span = span

            if phrase_result is not None:
                phrase_result["change"]["sentence_index"] = sid
                all_changes.append(phrase_result["change"])
                rebuilt.append(_detokenize(phrase_result["new_tokens"]))
                handled_positions = set(range(handled_span[0], handled_span[1]))
                all_skipped.extend(_idiom_skip_entries(idiom_matches, exclude_positions=handled_positions))
            else:
                all_skipped.extend(_idiom_skip_entries(idiom_matches))
                rebuilt.append(sentence)  # leave unchanged -- never ship a bad guess
            continue

        # Mixed case (flagged is non-empty): unchanged from before this
        # tier existed -- idiom-protected matches (if any) are still
        # just reported as skipped. Phrase-tier is not attempted here;
        # no observed real-world case needs it (see §5 item 4), and
        # substitution below already handles the substitutable part of
        # the sentence correctly on its own.
        if idiom_matches:
            all_skipped.extend(_idiom_skip_entries(idiom_matches))

        content_count = _substitutable_content_word_count(tags, phrase_protected)
        flagged_fraction = len(flagged) / content_count
        pre_escalate = (
            len(flagged) > settings.escalation_word_count
            or flagged_fraction > settings.degenerate_fraction
        )

        new_tokens, sentence_changes, sentence_skipped = (None, [], [])
        if not pre_escalate:
            new_tokens, sentence_changes, sentence_skipped = _try_substitution(
                sentence, tokens, tags, flagged, profile, engine, settings
            )

        if new_tokens is not None:
            rebuilt_sentence = _detokenize(new_tokens)
            for c in sentence_changes:
                c["sentence_index"] = sid
                # Contextual-fit signal (R33-R36, Option A -- reported
                # only, never gates anything here). Scored against the
                # FINAL assembled sentence, not the original -- this
                # checks whether the word reads naturally in its actual
                # shipped context, a different question from meaning
                # preservation. Word-level substitutions only; phrase/
                # restructuring output isn't validated for this signal.
                c["verification"]["contextual_fit"] = sem.contextual_fit_score(
                    rebuilt_sentence, c["replacement"]
                )
            all_changes.extend(sentence_changes)
            rebuilt.append(rebuilt_sentence)
            continue

        # Escalate: either pre-triggered, or substitution failed for some position.
        restructured_text, change = _try_escalation(sentence, flagged, profile, settings)
        if restructured_text is not None:
            change["sentence_index"] = sid
            all_changes.append(change)
            rebuilt.append(restructured_text)
        else:
            reason = "profile too restrictive for this sentence" if flagged_fraction > settings.degenerate_fraction \
                else "could not safely reformulate this sentence"
            all_skipped.append({"word": sentence, "position": None, "reason": reason})
            rebuilt.append(sentence)  # leave unchanged — never ship a bad guess

    reformulated_text = " ".join(rebuilt)

    if not any_flagged:
        status = "no_change_needed"
    elif all_changes:
        status = "reformulated"
    else:
        status = "could_not_safely_reformulate"

    flagged_before = _flagged_word_count(text, profile)
    flagged_after = _flagged_word_count(reformulated_text, profile)
    overall_sim = sem.semantic_similarity(text, reformulated_text)
    final_ok = (flagged_after < flagged_before) or (flagged_before == 0)
    if overall_sim is not None:
        final_ok = final_ok and overall_sim >= (settings.sbert_threshold or sem.MIN_SEMANTIC) - 0.05

    # Second meaning-preservation signal (R24/R27, VALIDATION.md §15/§18) —
    # reported ALONGSIDE overall_sim, never blended into final_ok/gating.
    # Real but partial per R24: catches some idiom-adjacent breaks SBERT
    # misses, misses others SBERT also misses. A None here (model
    # unavailable) is reported honestly, not silently hidden or defaulted.
    meaningbert = sem.meaningbert_score(text, reformulated_text)

    metrics = {
        "meaning_preservation": round(overall_sim, 4) if overall_sim is not None else None,
        "meaning_preservation_meaningbert": round(meaningbert, 2) if meaningbert is not None else None,
        "flagged_words_before": flagged_before,
        "flagged_words_after": flagged_after,
        "difficulty_reduction_pct": (
            round(100.0 * (flagged_before - flagged_after) / flagged_before, 2) if flagged_before else 0.0
        ),
        "naturalness_edit_ratio": nat.edit_ratio(text, reformulated_text),
        "substitution_rate": round(
            nat.changed_word_count(text, reformulated_text) / max(1, len(nat._word_tokens(text))), 4
        ),
    }

    return {
        "original_text": text,
        "reformulated_text": reformulated_text,
        "status": status,
        "changes": all_changes,
        "skipped": all_skipped,
        "metrics": metrics,
        "final_verification": {
            "passed": bool(final_ok),
            "details": {
                "flagged_before": flagged_before,
                "flagged_after": flagged_after,
                "sbert_sim": round(overall_sim, 4) if overall_sim is not None else None,
            },
        },
    }


def reformulate_v2(text: str, profile: DifficultyProfile, settings: ReformulateSettings | None = None) -> dict:
    """R45's next-generation hybrid entry point (VALIDATION.md §36.3's
    decision) — NOT called by app.py, NOT a drop-in replacement for
    reformulate() yet. A separate, parallel function so reformulate()'s
    production behavior is completely unaffected by anything in this one.

    Two changes from reformulate(), both directly evidenced, nothing
    else:
      1. Escalation uses _try_escalation_v2() (phoneme-aware decoding-
         time constraint) instead of _try_escalation() — substitution
         stays byte-identical to reformulate(), per the decision that
         substitution "stays primary and unchanged."
      2. The final assembled output gets ONE additional validation pass
         — sem.logical_consistency_check() (NLI) and
         sem.grammar_issue_count() — combined the same way R45's
         Prototype 1 measured (32% recall on R40's SEVERE class,
         VALIDATION.md §36.1). Reported in the new `validation` key,
         same reported-only discipline as contextual_fit_score()
         (Practice.md §10) — does NOT gate `status` or
         `final_verification.passed`. Promoting it to an actual gate is
         a separate, deliberate decision, not made here.
    """
    settings = settings or ReformulateSettings()
    sem.load_sbert()
    engine = engine_module.SynonymEngine()

    sentences = split_sentences(text)
    rebuilt: list[str] = []
    all_changes: list[dict] = []
    all_skipped: list[dict] = []
    any_flagged = False

    for sid, sentence in enumerate(sentences):
        try:
            tokens = word_tokenize(sentence)
        except Exception:
            tokens = re.findall(r"[A-Za-z][A-Za-z'-]*|[.,!?;:]", sentence)
        tags = _correct_predicate_adjective_tags(tokens, pos_tag(tokens))
        phrase_protected = sem.protected_positions(tokens)
        flagged = _flagged_positions(tokens, tags, profile)
        idiom_matches = _idiom_protected_matches(tokens, tags, profile)

        if not flagged and not idiom_matches:
            rebuilt.append(sentence)
            continue

        any_flagged = True

        if not flagged and idiom_matches:
            spans = sem.idiom_spans(tokens)
            phrase_result = None
            handled_span = None
            if spans:
                span = spans[0]
                span_matches = [m for m in idiom_matches if span[0] <= m["position"] < span[1]]
                if span_matches:
                    phrase_result = _try_phrase_replacement(
                        sentence, tokens, span, span_matches, profile, settings
                    )
                    if phrase_result is not None:
                        handled_span = span

            if phrase_result is not None:
                phrase_result["change"]["sentence_index"] = sid
                all_changes.append(phrase_result["change"])
                rebuilt.append(_detokenize(phrase_result["new_tokens"]))
                handled_positions = set(range(handled_span[0], handled_span[1]))
                all_skipped.extend(_idiom_skip_entries(idiom_matches, exclude_positions=handled_positions))
            else:
                all_skipped.extend(_idiom_skip_entries(idiom_matches))
                rebuilt.append(sentence)
            continue

        if idiom_matches:
            all_skipped.extend(_idiom_skip_entries(idiom_matches))

        content_count = _substitutable_content_word_count(tags, phrase_protected)
        flagged_fraction = len(flagged) / content_count
        pre_escalate = (
            len(flagged) > settings.escalation_word_count
            or flagged_fraction > settings.degenerate_fraction
        )

        new_tokens, sentence_changes, sentence_skipped = (None, [], [])
        if not pre_escalate:
            new_tokens, sentence_changes, sentence_skipped = _try_substitution(
                sentence, tokens, tags, flagged, profile, engine, settings
            )

        if new_tokens is not None:
            rebuilt_sentence = _detokenize(new_tokens)
            for c in sentence_changes:
                c["sentence_index"] = sid
                c["verification"]["contextual_fit"] = sem.contextual_fit_score(
                    rebuilt_sentence, c["replacement"]
                )
            all_changes.extend(sentence_changes)
            rebuilt.append(rebuilt_sentence)
            continue

        # R47/§38: phoneme-aware decoding combined with iterative
        # regeneration — the two independently-validated mechanisms,
        # tested together for the first time. _try_escalation_v2 (single-
        # round phoneme-only) stays defined and available above for
        # direct comparison; reformulate_v2() now uses v3.
        restructured_text, change = _try_escalation_v3(sentence, flagged, profile, settings)
        if restructured_text is not None:
            change["sentence_index"] = sid
            all_changes.append(change)
            rebuilt.append(restructured_text)
        else:
            reason = "profile too restrictive for this sentence" if flagged_fraction > settings.degenerate_fraction \
                else "could not safely reformulate this sentence"
            all_skipped.append({"word": sentence, "position": None, "reason": reason})
            rebuilt.append(sentence)

    reformulated_text = " ".join(rebuilt)

    if not any_flagged:
        status = "no_change_needed"
    elif all_changes:
        status = "reformulated"
    else:
        status = "could_not_safely_reformulate"

    flagged_before = _flagged_word_count(text, profile)
    flagged_after = _flagged_word_count(reformulated_text, profile)
    overall_sim = sem.semantic_similarity(text, reformulated_text)
    final_ok = (flagged_after < flagged_before) or (flagged_before == 0)
    if overall_sim is not None:
        final_ok = final_ok and overall_sim >= (settings.sbert_threshold or sem.MIN_SEMANTIC) - 0.05

    meaningbert = sem.meaningbert_score(text, reformulated_text)

    metrics = {
        "meaning_preservation": round(overall_sim, 4) if overall_sim is not None else None,
        "meaning_preservation_meaningbert": round(meaningbert, 2) if meaningbert is not None else None,
        "flagged_words_before": flagged_before,
        "flagged_words_after": flagged_after,
        "difficulty_reduction_pct": (
            round(100.0 * (flagged_before - flagged_after) / flagged_before, 2) if flagged_before else 0.0
        ),
        "naturalness_edit_ratio": nat.edit_ratio(text, reformulated_text),
        "substitution_rate": round(
            nat.changed_word_count(text, reformulated_text) / max(1, len(nat._word_tokens(text))), 4
        ),
    }

    # ── R45's combined validator, on the final assembled output only ────────
    # Reported, not gating (see docstring). Skipped when nothing changed —
    # there's nothing new to validate against the original.
    validation: dict = {"nli": None, "grammar_issue_count": None, "flagged": False}
    if status == "reformulated":
        nli_result = sem.logical_consistency_check(text, reformulated_text)
        grammar_count = sem.grammar_issue_count(reformulated_text)
        validation = {
            "nli": nli_result,
            "grammar_issue_count": grammar_count,
            "flagged": bool(nli_result and nli_result["contradiction"]) or bool(grammar_count),
        }

    return {
        "original_text": text,
        "reformulated_text": reformulated_text,
        "status": status,
        "changes": all_changes,
        "skipped": all_skipped,
        "metrics": metrics,
        "final_verification": {
            "passed": bool(final_ok),
            "details": {
                "flagged_before": flagged_before,
                "flagged_after": flagged_after,
                "sbert_sim": round(overall_sim, 4) if overall_sim is not None else None,
            },
        },
        "validation": validation,
    }


def feedback_targets(change: dict, profile: DifficultyProfile) -> list:
    """Which declared DifficultyEntry objects a Keep/Revert decision on
    *change* should be attributed to (ROADMAP.md R9). Read-only — does not
    mutate the profile or affect reformulate()'s own behavior in any way;
    callers (app.py) decide what to do with the returned entries.

    Substitution-sourced changes are attributed directly: each one
    already names, via 'triggered_by', exactly which declared word/
    pattern/sound caused it, and 'original' is the single word that was
    replaced. Phrase-sourced changes (§5 item 4) are attributable too,
    just not via 'original' — that field is the whole original sentence
    for this source, not one word — so they carry their own
    'matched_words' list (the specific flagged word(s) inside the
    replaced span) to attribute against instead, a direct, non-guessed
    link since the phrase tier only ever fires for the exact idiom span
    those words matched. Restructuring-sourced changes remain
    deliberately unattributed: they're genuinely sentence-level
    (multiple flagged spans can collapse into one T5 rewrite with no
    reliable way to tell which one drove the accept/reject decision),
    and this project's own discipline (Practice.md §6) is not to invent
    an attribution without evidence it's the right one.
    """
    source = change.get("source")
    if source not in ("substitution", "phrase"):
        return []
    triggered_by = change.get("triggered_by", [])
    words = [change.get("original", "")] if source == "substitution" else change.get("matched_words", [])
    targets = []
    for word in words:
        if "declared_word" in triggered_by or "word_specific_pattern" in triggered_by:
            entry = profile.find_word(word.lower())
            if entry is not None and entry not in targets:
                targets.append(entry)
        if "global_sound" in triggered_by:
            for entry in profile.sounds:
                if ph.matches_any(word, [entry.value]) and entry not in targets:
                    targets.append(entry)
    return targets
