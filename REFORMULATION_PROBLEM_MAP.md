# REFORMULATION_PROBLEM_MAP.md — Problem Definition & Research Map (living document)

**Status: living.** Unlike every other `*_RESEARCH.md`/`*_FORMULATION.md` file in
this repo, which records a single dated research pass, this file is meant to be
**re-opened and edited** every time an experiment, pilot, or piece of code reveals
a new factor, failure mode, constraint, or workable technique. Practice.md's
evidence vocabulary (`[FINDING]` / `[INTERPRETATION]` / `[HYPOTHESIS]` /
`[LIMITATION]` / `[RECOMMENDATION]` / `[FUTURE WORK]`) still applies to every
claim. Two more tags are used specifically for external-literature claims in
§3, borrowed from how the 2026-08-17 research pass reported them:

- **[SOURCED]** — a real, named paper/system/library was found and can be
  cited; claims here are not invented.
- **[GAP]** — actively searched for and found genuinely sparse or unaddressed
  in the literature for this specific use case, not just "didn't look."

**How to maintain this file:** when a pilot, an eval run, or a debugging
session produces a new fact about the reformulation problem, add it to §2
(Problem Definition) under the relevant factor, or add a new factor if none
of the nine fit. When new literature or a new candidate technique surfaces,
add it to §3. When a decision gets made about what to build next, update §5
and log the decision in `DECISION_LOG.md` as usual — this file is the map,
`DECISION_LOG.md` is still the append-only record of what was decided and
when. Add an entry to the Changelog (§7) every time this file itself changes
materially.

---

## 0. Why this document exists now, not earlier

Through Stage 6 (`VALIDATION.md` §6) and the two human pilots (§8-§9), this
project treated the reformulation engine largely as a **word-substitution
problem with a restructuring fallback**: tag flagged words, swap them for a
verified-safe synonym, escalate to a paraphrase model if too many words are
flagged at once. That framing was good enough to build Architecture D′ and
get it evaluated, but the evidence gathered since then — especially
`VALIDATION.md` §9.6-9.11's real 30-item pilot — shows the actual problem is
**multi-factor**: getting the *input's* intended meaning right, preserving
meaning *in context* (not just embedding-distance), grammaticality,
naturalness/idiomaticity, whether the speaker's actual difficulty was
addressed, word sense, cross-substitution interaction, when to restructure
vs. substitute, and how much change is too much — are at least nine
semi-independent things the engine has to get right, and the pilot found
concrete, reproducible failures in several of them independently. This
document is the place that problem gets defined and kept current, instead of
being re-discovered piecemeal in `VALIDATION.md` entries that don't talk to
each other.

## 1. The product objective this all serves

Restated here because every factor below is subordinate to it, per
Practice.md §1: **the objective is not "a good word-substitution algorithm."**
The objective — the one the user has stated directly and that this project
is ultimately aimed at — is a system that, working from what it knows about
a specific speaker's declared and observed difficulty, gets that speaker's
own intended message and sentiment across in the way that is most natural
and easiest for *them* specifically to actually say out loud. Text
reformulation (this repo's current scope) is the piece of that system this
project has chosen to build and validate first — a deliberate, evidence-based
narrowing (`DOCS.md`'s Stage 2 scope note), not a redefinition of the end
goal. Everything in §2-§6 is in service of that end goal, and every
implementation decision should be checked against it, not against "did this
make the substitution algorithm more sophisticated" for its own sake.

**[LIMITATION, carried forward from `RESEARCH.md`/`REFORMULATION_RESEARCH.md`,
restated here because it bears directly on §1]** This project has already
done the literature and architecture research that justifies treating
phoneme-aware, profile-driven text rewriting as a credible piece of that
larger system (`REFORMULATION_RESEARCH.md`'s ranked recommendation,
`RESEARCH.md`'s component-by-component review) — that groundwork is not
being redone here. What this document adds is the recognition, forced by
real pilot evidence, that the piece already chosen is itself a multi-factor
research problem, not a solved sub-problem waiting on tuning.

## 2. Problem Definition — the nine factors

For each factor: what it is, where the engine currently stands on it (fact,
verified against the actual code as of this pass — not assumed), and what
evidence exists. This section is expected to grow entries under each factor
over time; it does not attempt to be complete on day one.

### 2.1 Input may itself be malformed — infer intent, or ask, don't silently guess

**What it is:** the speaker's typed/spoken-then-transcribed input may be
ungrammatical, ambiguous, or otherwise not a clean expression of what they
meant. Reformulating it as typed risks confidently rewriting the wrong
meaning; auto-correcting it silently risks changing what they meant to say
without them noticing.

**Current state [FINDING, verified against code]:** `grammar.py::sanitize_input()`
runs a fixed ~10-layer pipeline (pyspellchecker → several rule-based passes →
optional LanguageTool deep-check) and **always** produces a single corrected
string that reformulation then proceeds on. There is no confidence score
surfaced, no threshold, and no code path that stops and asks the user
anything — every input is auto-corrected and used, full stop. `app.py` does
show the user what was auto-corrected (the "Spelling/grammar fixes applied"
expander), so the change isn't invisible, but nothing ever blocks and asks
*before* proceeding.

**Evidence this matters:** not yet directly evidenced by a pilot failure
(no pilot item was deliberately malformed input) — this factor is currently
a **[HYPOTHESIS]** grounded in the user's own stated concern and in §3.4's
literature (GEC/clarification precedent), not yet in an observed failure
case from this project's own data. Flagged here so it doesn't get lost, and
so a future pilot can deliberately test it.

### 2.2 Semantic/meaning preservation must be judged in context, not by sentence embedding alone

**Current state [FINDING, now confirmed twice, independently]:** SBERT cosine
similarity between original and reformulated text is the only automated
meaning-preservation signal in the pipeline (`semantic.semantic_similarity`,
used both per-candidate during substitution and once more at final
verification). `VALIDATION.md` §6.5 found one case where this proxy scored a
redundant, arguably-worse sentence at 0.965. §9.7 found the same failure
mode **9 times** in a second, independent 30-item pilot, and — critically —
**always in the same direction**: SBERT never rated a pair worse than the
human did, only better, and the gap was largest exactly when a substitution
broke a fixed idiom or grammatical construction. This is no longer a
theoretical concern; it is a repeatable, characterized proxy blind spot.

### 2.3 Grammaticality

**Current state [FINDING]:** `grammar.py`'s `inflect()`/`_preserve_case()`
handle basic morphological agreement (tense, number, case) for single-word
substitutions, and this machinery is verified working correctly (§6.4's
`SentenceRewriter` double-`s` bug was found in the *other*, legacy pipeline,
not in `reformulate.py`, which produced the correct inflection on the same
input). But grammaticality beyond single-word morphology is not checked at
all: `VALIDATION.md` §9.8's pair_04 ("forgot"→"missed about that") and
pair_24 ("valuable"→"worth") are cases where a substitution is
morphologically fine in isolation but produces an ungrammatical
preposition/adjective-slot in the sentence it lands in — nothing in the
pipeline catches this class of error; it was only caught because a human
happened to notice and comment.

**Update, 2026-08-18 — a fourth instance, this time from the new
phrase-level tier, not substitution.** `VALIDATION.md` §16.3: the
phrase tier's one recovered pilot case ("how's it going" → "Hey, how's
it today?") is grammatically thin — passed SBERT similarity, negation
consistency, and the leak scan cleanly, and still reads as missing a
word. None of the existing gates check grammaticality at the phrase or
sentence level; every instance found of this factor so far (pair_04,
pair_24, now pair_01) was caught by a human noticing, never by the
pipeline itself. Still unaddressed, still open — this factor keeps
accumulating separate, real evidence across every tier that's been
built (substitution, and now phrase replacement).

### 2.4 Naturalness and idiomaticity

**Current state [FINDING, the single best-evidenced problem in this
document]:** `VALIDATION.md` §9.7 and §9.9 independently converge on the
same mechanism from two directions — the largest SBERT-vs-human gaps, and
the largest category-level score gap (`global_sound` vs. `declared_word`) —
both trace to substitution breaking a fixed idiom or collocation ("how's it
going," "drives me crazy," adjective-for-adverb in "was late"→"was
recently"). The phoneme-onset flagging mechanism has no concept of "this
word is a load-bearing idiom component" vs. "this word is a free content
slot" — it flags by pronunciation match alone. §3.1 below researches
concrete fixes.

**Update, 2026-08-17 — item 1 of §5 implemented and verified:**
`semantic.py` now has a curated idiom-phrase guard (`IDIOM_PHRASES`,
`IDIOM_PHRASE_PATTERNS`) covering the specific pilot-evidenced breaks
("how's it going," "drives/driving me crazy," "right now/away/here").
`VALIDATION.md` §10 has the full verification: the exact broken outputs
P1 rated ("how's it **taking**," "going me crazy") no longer occur, all
26 unrelated pilot pairs are byte-identical (no collateral change), and
Stage 6's corpus is unaffected (zero phrase overlap, confirmed not
assumed). This closes the specific evidenced cases, not the general
class — the guard is a curated list, not a general MWE detector (§3.1's
`[GAP]`: no off-the-shelf general detector was found either), so a novel
idiom not on the list will still break exactly as before. Still open.

**Update, 2026-08-18 — item 4 of §5 implemented and verified: the
"protect and leave alone" gap this factor's own update above named is
now partially closed.** A phrase-level replacement tier
(`VALIDATION.md` §16) attempts a local, verified replacement for an
idiom-only difficulty before giving up — recovered the frozen pilot's
pair_01 case exactly. Still not a general fix (same curated-list scope
as item 1 — a novel idiom not on the list is still just left alone, now
via the phrase tier's fallback path rather than R19's original one) and
the recovered output itself surfaced a new, smaller finding: it can
pass every automated gate while still being grammatically thin (factor
2.3) — disclosed, not treated as solved.

### 2.5 Whether the reformulation actually removes the speaker's declared difficulty

**Current state [FINDING]:** this is the one factor with a dedicated,
already-separated measurement path — `reformulate()`'s own
`flagged_words_before`/`flagged_words_after` counts, reported in
`metrics`/`final_verification` and never blended with human judgment
(Practice.md §10, enforced throughout `eval/pilot_analyze.py`). §6.9
measured this on ordinary (non-adversarial) text: escalation succeeds
roughly 43% of the time it triggers, and triggers for about 1 in 10
sentences under a moderately-populated realistic profile. This factor is
comparatively well-instrumented already; the gap is in factors 2-4 and 6-8
below, which can silently defeat a "success" on this metric (e.g. §9.6's
pair_19: `flagged_words_after` correctly dropped to zero, but the
replacement also silently changed singular to plural — a difficulty-removed,
meaning-changed case that this metric alone cannot see).

**Update, 2026-08-17 — a second, unplanned finding from implementing
§2.4's idiom guard:** protecting an idiom span can make this factor
*worse* for that specific sentence, not just neutral — if the only word
matching the speaker's declared difficulty sits inside a protected idiom,
the engine now correctly refuses to touch it (status
`could_not_safely_reformulate`) rather than shipping a broken
substitution, but the declared difficulty is then **not addressed at
all** in that sentence (`VALIDATION.md` §10.3's pair_01/pair_11). This
is the same "never ship a bad guess" trade-off §6.3's Cause B already
established for escalation failures, now shown to also apply to
substitution once an idiom guard exists — a real cost of §2.4's fix,
disclosed rather than presented as a strict improvement. A follow-up
correctness bug in this same work is also worth recording here directly:
the first implementation silently excluded these idiom-locked-but-
matching words from `flagged_words_before`/`after` entirely (as if the
difficulty had never existed), which would have made "difficulty
resolved" misleading in a *new* way; fixed before shipping (`VALIDATION.md`
§10.1) so the metric now honestly reports "unresolved," not "never
existed" or "resolved."

### 2.6 Word sense and contextual appropriateness

**Current state [FINDING, concrete and reproducible]:** WordNet-based
candidate generation (`engine.py`) does not disambiguate sense before
pulling synonyms. `VALIDATION.md` §9.9 found the same specific bug twice,
independently: "right" in "right now" (the immediate/temporal sense)
substituted using the correct/fair sense ("justly", "properly") both times.
§3.2 below found this is a solved-in-principle problem in the literature,
not a research gap — the gap is implementation, not knowledge.

**Update, 2026-08-17:** the *literal* "right now" case is now also
prevented as a side effect of §2.4's idiom guard (the phrase is on the
protected list). This is not a fix for this factor in general — it
covers one specific two-word phrase, not word-sense disambiguation as a
capability. Item 2 (§5) — general WSD before candidate generation —
remains the next planned step for this factor, per the user's own
sequencing, precisely because only this one word/phrase has been
observed to fail so far and the general problem is still unaddressed.

**Update, 2026-08-17 — item 2 of §5 implemented, and corrected against
two real regressions before shipping.** `semantic.py::disambiguate_synset()`
now picks one sense (via SBERT gloss-matching against a local context
window) before `engine.py` generates candidates, closing the general
problem, not just "right now" — verified on a sentence the idiom guard
doesn't cover ("He'll be right over to help." correctly resolves to the
"immediately" sense). Testing this against Stage 6's corpus (per the
user's explicit "re-run and see" instruction) found it isn't a clean
win: full account in `VALIDATION.md` §11, including two regressions
found and fixed in the same pass (a candidate colliding with another
declared-difficult word — factor 2.7 below; two occurrences of one word
forced to the identical sense) and one real, disclosed cost that
*wasn't* fixed (single-sense candidate pools are sometimes smaller and
score lower than the old sense-mixed pools, even when correct).

### 2.7 Interactions between multiple substitutions in one sentence

**Current state [FINDING, code-verified mechanism, not just a hypothesis]:**
traced directly in `reformulate.py::_try_substitution` and
`semantic.py::rank_candidates_contextually` for this pass. Each candidate at
position *i* **is** scored against a sentence that includes prior
substitutions from earlier positions in the same loop (`tokens=list(new_tokens)`
is passed in), so it is not scoring positions in total isolation — but the
comparison target is always the pristine, fully-original sentence
(`original_sentence=sentence`), and each position's SBERT/phoneme/antonym
checks are otherwise independent per-slot decisions. There is a whole-text
final re-verification (`reformulate()`'s `overall_sim = sem.semantic_similarity(text,
reformulated_text)`, gated at `threshold - 0.05`), so a badly-compounding
pair of substitutions is *not* entirely unchecked — but that gate inherits
the exact same SBERT idiom-blindness documented in 2.2/2.4, and it is a
single coarse pass/fail over the *whole document*, not a localized check of
whether substitution 2 specifically interacts badly with substitution 1.
`VALIDATION.md` §9.6's `multi_difficulty` category (n=3, meaning=2.00/5,
worst of all four categories) is consistent with this mechanism: two
independent substitutions each have their own (correlated, not independent)
chance of hitting factor 2.4's idiom-blindness, and nothing currently
reasons about the pair jointly beyond the same blind whole-text gate that
already misses single-substitution idiom breaks.

**Update, 2026-08-17 — a concrete, reproduced instance of this factor,
not just a hypothesis anymore.** Found while testing §2.6's WSD fix
against Stage 6's corpus: a profile declaring both "reviewed" and
"examined" as difficult produced a substitution of "reviewed" →
**"examined"** — one flagged word's replacement was literally the
*other* flagged word, because nothing checked a candidate against the
profile's other declared words, only against the global-sound phoneme
veto. Fixed narrowly (`_try_substitution` now also rejects a candidate
matching `profile.find_word()`), but the mechanism that exposed it is
worth recording here: making candidate ranking *more* semantically
precise (§2.6's fix) made this collision *more* likely, not less — a
real, non-obvious interaction between fixing one factor and surfacing
another. `VALIDATION.md` §11.2/§11.3 has the full account.

**Update, 2026-08-18 — R26 (§5 item 7): the "compounding is mostly
idiom-blindness" hypothesis above is corrected, not confirmed, by
direct evidence.** Traced each of the pilot's three `multi_difficulty`
cases against the now-live phrase tier (R25) directly, not inferred:
only 1 of 3 (pair_28) involves an idiom span at all, and it's a *mixed*
case the phrase tier correctly doesn't touch by design (substitution
already resolves its non-idiom word on its own). The other 2 of 3
(pair_29, pair_30) have **no idiom span whatsoever** — two ordinary
substitutable words, no fixed expression connecting them. Their poor
pilot scores trace to a *different* mechanism this document already
named separately: the "generic overused replacement" pattern
(`VALIDATION.md` §9.9 — `push`→`force`/`urge`, `grab`→`catch`/`take`/
`get`), where two independent substitution slots each have their own
chance of a weak, loosely-fitting pick, and two chances compound that
risk. **This factor is not substantially explained by §2.4/idiom-
blindness** — at least not in this n=3 sample — and stays open as its
own problem, with the candidate-ranking/frequency-bias pattern now the
better-evidenced lever if it's picked up again, not another idiom-
detection mechanism. Full record: `VALIDATION.md` §17.

### 2.8 Sentence/phrase restructuring when substitution isn't enough

**Current state [FINDING, and the pilot's most counter-intuitive result]:**
the T5 escalation path (`rephrase.py`, generate-then-verify against the same
SBERT/phoneme gates) succeeds only ~43% of the time it triggers on ordinary
text (§6.9), and Stage 6's adversarial corpus found two separable failure
causes: a case-sensitivity bug in `bad_words_ids` (R17, fixed) and a deeper
mismatch — `bad_words_ids` can only block literal token strings, never a
phoneme class, so semantically-central flagged sounds resurface via
unblocked synonyms (§6.3's Cause B, still open). The counter-intuitive part:
`VALIDATION.md` §9.10 found that **when restructuring does succeed**, it
scores higher than substitution on every human axis (meaning 4.75 vs 3.91,
naturalness 4.50 vs 3.91, n=8 vs n=22) — plausibly because a whole-sentence
SBERT check is less likely to miss a *local* idiom break the way a
single-word substitution's narrower check can. This reframes restructuring
from "the risky fallback" to "the higher-quality-when-it-works path with a
success-rate problem," which changes its priority (§5).

**Update, 2026-08-17 — two research passes, and a convergence neither
one was told about the other.** Following a direct question from the
user ("can't we replace idiom-to-idiom / phrase-to-phrase instead of
just leaving it alone or rewriting the whole sentence?" and "should we
fine-tune T5 for this specifically?"), two research passes were run in
parallel. §3.8 covers phrase-level replacement as a third tier between
word-substitution and whole-sentence restructuring; §3.9 covers
fine-tuning/specializing a model for this task. Both independently
converged on the same near-term recommendation — see §5 item 3.

**Update, 2026-08-17, second — the diagnostic experiment §5 item 3
called for was run, and it settled the question with a real, informative
negative result.** `VALIDATION.md` §12: `google/flan-t5-base`, prompted
with the flagged words plus a natural-language reason (no
`bad_words_ids`), was tested against all 22 real currently-failing
escalation cases. It robustly improved meaning preservation (avg. SBERT
similarity 0.865 → 0.950, confirmed again at 3.5× model size: 0.982) —
but the actual pass rate barely moved (0% → 4.5%, or 9.1% with a hybrid
hard-blocking variant), because constraint satisfaction, not meaning
preservation, is the real bottleneck, and telling the model *why* in
prose does not reliably make it obey a phonological rule, at any tested
model size. Cause B (§2.8's original finding) is now confirmed to
survive a genuinely different mechanism (explanation instead of pure
blocking), not just a genuinely different model — a stronger piece of
evidence that this is a structural limitation of prompting/blocking
approaches on a generic paraphrase-style model, not a fixable framing
gap. Per the plan's own condition, the phrase-level tier (§5 item 4)
was correctly **not** started as a result.

### 2.9 The help-vs-harm trade-off: how much change is too much

**Current state:** no explicit mechanism currently reasons about this
trade-off as a first-class decision — the engine either substitutes,
restructures, or leaves a sentence unchanged based on flagged-word count
thresholds (`escalation_word_count`, `degenerate_fraction`), not on any
measure of "how much has this sentence already changed and is that
starting to cost more than it's worth." `naturalness.edit_ratio()` computes
an edit-distance-based "how much changed" number and reports it as a metric,
but nothing currently *acts* on it as a stopping signal.

**[LIMITATION — a framing note surfaced by this pass's literature research,
not previously recorded anywhere in this project]** The 2026-08-17 research
pass found that mainstream stuttering-therapy literature (e.g. Avoidance
Reduction Therapy for Stuttering, ARTS) treats **word avoidance/substitution
itself as a maladaptive coping behavior that therapy works to reduce**, not
something to automate and hand back to the speaker. This project automates
exactly that behavior. This is not evidence the project's approach is wrong
— the objective (§1) is about ease of producing a specific piece of text in
a specific moment, e.g. reading a prepared statement or sending a message,
which is a different situation than a therapy relationship — but it is a
genuine tension in how this system's role should be framed to a real
speaker, and it belongs in this document rather than staying an unrecorded
aside. **[FUTURE WORK]** worth a deliberate, explicit decision (not a silent
default) about how the product frames itself — a communication aid for
specific moments vs. anything that could be read as a therapy substitute —
before this goes in front of real speakers who stutter outside this
project's own pilot.

## 3. Research pass (executed 2026-08-17) — targeted at Stage 6/pilot findings

Scope, per the user's explicit direction: prioritize idiom/fixed-expression
preservation, word-sense/context disambiguation, multi-difficulty
interactions, and T5 restructuring/escalation — the four areas §2 above
found the most concrete evidence for — while also surveying how adjacent
NLP fields (stuttering/disfluency systems, text simplification, GEC,
constrained generation, semantic-preservation evaluation, idiom detection,
lexical substitution) already address these problems. Findings below are
from a dedicated literature-research pass (WebSearch/WebFetch against real
sources); every claim is tagged **[SOURCED]** (a real, named paper/system/
library was found), **[GENERAL KNOWLEDGE]** (plausible, not verified this
session — treated with correspondingly less confidence), or **[GAP]**
(actively searched, found genuinely sparse). No code was changed to produce
this section.

### 3.1 Idiom / multiword-expression (MWE) detection and preservation

- **[SOURCED]** The failure mode itself is named in the literature, not
  unique to this project: lexical-substitution research explicitly
  distinguishes MWE components ("cannot be freely substituted with
  synonyms without distortion of meaning") from ordinary collocations.
- **[SOURCED]** spaCy's `PhraseMatcher`/rule-based `Matcher` does exact-span
  phrase matching against a curated list — directly usable as a pre-
  substitution guard: match spans against an idiom/fixed-expression list,
  mark matched spans "don't substitute inside this span" before word-level
  substitution runs. **Feasibility: small** — spaCy is a standard CPU
  dependency; this is a lookup-list guard, not a model or a training run.
- **[SOURCED]** PARSEME (shared task + corpora for verbal MWE
  identification across languages) and PMI/statistical collocation
  detection (built into NLTK) are the two research-grade alternatives to a
  curated list — PARSEME has no off-the-shelf English pip package
  (**feasibility: medium**, would mean adapting a tagger); PMI-based
  detection is small-effort to run but needs a reference corpus and a
  threshold, which crosses into tuning territory this project's own rules
  (Practice.md §6) require a separate go-ahead for.
- **[GAP]** No lexical-substitution system was found that ships a
  deployable, off-the-shelf idiom guard as a discrete pre-check step —
  idiom-awareness in the literature is mostly an evaluation-benchmark
  property (e.g. SemEval-2022 Task 2 idiomaticity embeddings), not a
  packaged filter. A curated-list + spaCy-PhraseMatcher guard is the
  practical path, not an "import and done" one.

### 3.2 Word-sense disambiguation for lexical substitution

- **[SOURCED]** `pywsd` (pure-Python, WordNet-backed Lesk-family WSD,
  no training) is directly usable as a pre-substitution step: disambiguate
  the sense of the flagged word in its actual sentence context *before*
  pulling WordNet synonyms for it, rather than pulling synonyms for the
  word's most common/first sense. **Feasibility: small.**
- **[SOURCED]** An alternative requiring no new dependency: embed each
  candidate WordNet synset's gloss with the SBERT model already loaded in
  this project, embed the sentence context, and pick the closest — the same
  pattern used in lexical-substitution literature as a lightweight
  Lesk alternative. **Feasibility: small** — reuses `semantic.py`'s existing
  SBERT model, no new model to load.
- **[SOURCED]** LexSubCon (ACL 2022) folds sense-selection into candidate
  ranking via sentence-definition embeddings and beats prior lexical-
  substitution benchmarks — useful as a design reference for how a fuller
  system does this, but it's a full research system (fine-tuned similarity
  model), heavier than this project needs. **Feasibility: medium**, not a
  drop-in.
- **Net assessment: this is a solved-in-principle problem.** The "right
  now" bug (§2.6) has a small, off-the-shelf fix path (`pywsd`, or reusing
  SBERT for gloss-matching) — the gap here is implementation, not missing
  research.

### 3.3 Lexically-constrained generation (for T5 escalation, §2.8)

- **[SOURCED] The single most actionable finding in this pass:**
  HuggingFace `transformers`' `model.generate()` already supports
  constrained beam search with disjunctive positive constraints
  (`force_words_ids`) alongside negative constraints (`bad_words_ids`) —
  same library this project's T5 model already runs on, CPU-compatible,
  no new model, no training. It does not solve phoneme-*class* blocking
  (still token-level), but it's a strictly more expressive replacement for
  the current manual `bad_words_ids`-only approach, and may reduce the
  search-space-shrinkage side effect the R17 follow-up found (tighter
  blocking pushing surviving candidates to lower similarity —
  `VALIDATION.md` §6.8). **Feasibility: small.**
- **[SOURCED]** NeuroLogic Decoding / NeuroLogic A*esque (NAACL 2021/2022)
  handle arbitrary predicate-logic constraints, which is a closer semantic
  match to "block this phoneme cluster" than plain token blocking — but no
  maintained pip package exists; would mean porting released research code
  onto this project's T5 checkpoint. **Feasibility: medium**, more
  implementation weight than constrained beam search, and still doesn't
  block a phoneme *class* directly — it would still need the phoneme class
  translated into an explicit (long, generated) disjunction of blocked
  word forms.
- **[GAP]** No constrained-decoding technique found actually blocks a
  *phonological feature* (e.g. "no STR onset anywhere in the output")
  rather than specific token strings. Cause B (`VALIDATION.md` §6.3) is a
  genuine, still-open gap in the field as applied to this exact problem,
  not something this pass found a ready answer to. The actionable move is
  upgrading token-level blocking (small effort), not expecting a
  found technique to fully close Cause B.

### 3.4 Grammatical error correction, and abstaining/asking instead of guessing (§2.1)

- **[SOURCED]** GECToR exposes inference-time confidence thresholds
  (`min_error_probability` and related) below which it leaves a span
  unchanged rather than editing it — real precedent for "abstain instead of
  guess," though GECToR abstains silently, it does not ask a clarifying
  question. **Feasibility: medium** — GECToR is a full model that would
  replace, not sit alongside, the current pyspellchecker/LanguageTool
  pipeline; the *confidence-threshold pattern* is easy to imitate without
  adopting the whole model (e.g. reuse LanguageTool's own match/confidence
  signal as an abstain trigger).
- **[SOURCED]** A detect-ambiguity → generate-a-clarifying-question →
  only-then-proceed control-flow pattern is an active, generalizable
  research pattern (CLAM, arXiv 2212.07769; two 2024-2026 follow-ups on
  uncertainty-guided clarification), not QA-specific despite most examples
  being from QA. **Feasibility: medium** — the control-flow pattern itself
  is cheap to adopt; the ambiguity-detection signal would need adaptation
  to this project's short, informal-register input, which nothing off-the-
  shelf currently provides tuned for.
- **Net assessment:** the *architecture* (abstain or ask, rather than
  always auto-correct-and-proceed) is well precedented and doesn't require
  new infrastructure to prototype; the specific classifier for "is this
  input ambiguous enough in *this* domain to need asking" would need to be
  built, most plausibly bootstrapped from LanguageTool's own match count/
  confidence rather than a new model.

### 3.5 Stuttering/AAC-specific reformulation systems

- **[GAP, re-confirmed]** This pass could not independently verify the
  "SpeechAgent (2026)" system `REFORMULATION_RESEARCH.md` cited in Stage 5
  via a fresh search — that citation still rests on the earlier pass's
  authority, not on anything re-verified here. AAC literature found this
  pass (foundation models in AAC, predictive-authoring systems) is real and
  active but addresses *motor/selection effort* (fewer keystrokes), not
  *phoneme-level speakability* of output text — no overlap with this
  project's actual problem. This remains a genuinely sparse area, confirmed
  independently a second time, not just inherited.
- See §2.9's therapy-framing note — the one substantive new thing this
  literature pass surfaced in this area, and it's a framing question, not a
  technique.

### 3.6 Controllable text simplification (relevant to §2.9's trade-off)

- **[SOURCED]** ACCESS, MUSS, and a 2026 follow-up (CATS) all use an
  explicit scalar/discrete **control-token knob** (target length, amount of
  paraphrasing, lexical/syntactic complexity) prepended to the input of a
  fine-tuned seq2seq model, as the mechanism for tuning how aggressively to
  rewrite. **Feasibility: medium-large** — all three need real fine-tuning
  infrastructure (BART-large-scale training on mined paraphrase corpora)
  this project does not have; not adoptable as-is. The *design idea* — a
  single tunable control signal governing aggressiveness, distinct from
  picking among independently-generated candidates (what this project's
  ranking already does) — is a legitimate alternative worth naming, not
  currently actionable given infra constraints.

### 3.7 Semantic-preservation metrics beyond SBERT cosine (directly relevant to §2.2)

- **[SOURCED]** MeaningBERT — a metric trained specifically to correlate
  with human judgment of meaning preservation *for text simplification*,
  the closest found match to this project's exact evaluation need.
  Pretrained checkpoint on HuggingFace, CPU-runnable. **Feasibility: small.**
- **[SOURCED]** BERTScore/MoverScore use token-level (not single pooled
  sentence-vector) contextual embeddings, which in principle should be more
  sensitive to local/idiomatic shifts than one SBERT cosine number.
  **Feasibility: small** (maintained `bert-score` pip package, CPU-capable)
  — but **[GAP]**, no paper was found demonstrating either metric actually
  catches idiom-breaking better than SBERT cosine; this is an inference
  from architecture, not a verified empirical claim.
- **[SOURCED]** Bidirectional NLI entailment (source⇒output and
  output⇒source) is a standard faithfulness-checking technique in NLG
  literature, and is a plausible catch for idiom-breaking specifically
  (an idiom-broken paraphrase plausibly fails bidirectional entailment in
  ways cosine similarity misses). Off-the-shelf NLI models
  (`roberta-large-mnli` or similar) are CPU-runnable. **Feasibility:
  small-medium** — one more model call in the verification step, no
  training.
- **[GAP, important]** No benchmark was found running SBERT cosine,
  BERTScore, MoverScore, NLI-entailment, and MeaningBERT head-to-head
  specifically on idiom-breaking substitution errors. "Metric X catches
  what SBERT misses" is currently **this project's own empirical finding**
  (the two pilot rounds), not literature-corroborated — any metric swap
  here would need this project's own re-evaluation against real pilot
  data, not just borrowed confidence from a paper.
  **Update, 2026-08-18 — this project's own re-evaluation was run
  (R24, `VALIDATION.md` §15).** MeaningBERT catches several idiom-
  adjacent breaks SBERT missed badly, but also completely misses the
  single worst-rated case in the dataset — a real, partial signal with
  its own distinct blind spot, not a strict improvement. The gap named
  here is now partially closed for MeaningBERT specifically; still open
  for BERTScore/MoverScore/NLI-entailment, none of which were tested.

### 3.8 Phrase-level replacement — a third tier between word-substitution and whole-sentence restructuring

Prompted directly by the user's question: instead of only choosing
between "protect the idiom, leave it alone" (§2.4/R19) and "escalate
the whole sentence" (§2.8), should there be a middle tier that replaces
the *whole flagged phrase* with a different, equally natural phrase
that conveys the same meaning without the flagged sound? Researched as
its own literature question, not assumed to be a good idea in advance.

- **[SOURCED] This is a real, actively-studied task, not a stretch.**
  The PIE corpus (Paraphrasing Idiomatic Expressions, ACL MWE 2021)
  frames idiom↔literal rewriting explicitly as: disambiguate the idiom's
  sense in context → generate a literal phrase → fit it back into the
  sentence for fluency — i.e. phrase-level, context-conditioned
  generation, not single-word substitution and not whole-sentence
  paraphrase. A larger follow-up (AAAI 2022, "Idiomatic Expression
  Paraphrasing without Strong Supervision") built a 15,627-pair parallel
  corpus via weak supervision and reports SARI — a metric built
  specifically for evaluating edits *smaller than the whole sentence*
  (keep/add/delete n-gram operations), which most other paraphrase
  metrics don't distinguish from whole-sentence rewrites.
- **[SOURCED, the strongest single piece of evidence]** PARSEME 2.0's
  MWE-2026 shared task (co-located with EACL 2026 — current, not
  historical) has a subtask defined as **"paraphrasing a sentence
  containing an MWE, so as to remove idiomaticity"** — almost exactly
  the operation being considered here, across 14 languages. This is
  strong confirmation the task is real and separately worth studying,
  not an invented framing.
- **[SOURCED] Idiomaticity is usage-dependent, not phrase-dependent —
  a real gap in R19's current design.** The MAGPIE corpus's whole
  reason for existing is that the same surface phrase ("how's it
  going") can be literal or figurative depending on context. R19's
  curated list can't see that distinction — it protects the phrase
  every time it appears, correct or not. Not a blocking problem today
  (false positives on a curated list of genuinely-almost-always-
  idiomatic phrases are rare) but a real limitation if the list grows.
- **[SOURCED] A concrete, low-risk implementation path exists using
  machinery already in this codebase.** T5's own pretraining objective
  is span-corruption with sentinel tokens (mask a span, fill it in) —
  architecturally exactly "mask the idiom, ask the model to fill it" —
  but the checkpoint already in use (`Vamsi/T5_Paraphrase_Paws`) is
  fine-tuned for whole-sentence paraphrase, not sentinel-infilling, so
  falling back to raw span-corruption behavior would likely produce
  short, generic fills, not idiomatically fluent ones (reasoned from
  architecture, not benchmarked). The more promising near-term
  approach, per "Sequence Span Rewriting" (arXiv 2101.00416) and the
  agent's own read: reuse the *existing* restructuring call
  (`rephrase.generate_candidates`), but scope its input to a short
  window around the idiom span instead of the whole sentence, then
  splice the result back in — same model, same gates, no new
  dependency, no training. ILM (Donahue et al., ACL 2020, GPT-2-based
  infilling with published code) is a real alternative if dedicated
  infilling quality is needed later.
- **[SOURCED] Runtime detection beyond a curated list is possible but
  not free.** PMI/statistical MWE detection (PARSEME's own toolkit) is
  cheap and training-free but, per MAGPIE's insight above, would
  false-positive on literal, non-idiomatic uses of fixed phrases.
  SemEval-2022 Task 2 (idiomaticity detection *in context*) shows the
  field's actual solution is a small fine-tuned classifier (BERT/XLM-R-
  scale), not statistics alone — a real, medium-effort upgrade path,
  not needed to build the tier itself (R19's existing curated-list
  trigger already provides a deterministic, zero-cost detection signal
  to start from).
- **[SOURCED] Evaluation must score the resulting FULL sentence, not
  the isolated phrase swap — and this project already does this for
  the other two tiers.** "Don't Take This Out of Context!" (arXiv
  2305.14755) found isolated-span metrics correlate poorly with human
  judgment (ρ 0–0.3) versus context-aware scoring of the whole result
  (ρ 0.7–0.9) for exactly this shape of localized-edit-in-a-larger-text
  problem. Directly actionable: reuse the same "SBERT on original vs.
  full reformulated sentence" pattern §2.8's restructuring tier already
  uses, not a new evaluation design.
- **Agent's own assessment (not a literature finding, stated as such):**
  well-justified conceptually with real, current prior art (PARSEME
  2.0's live shared task especially), and a genuine third tier — it
  doesn't require touching the existing word-level or sentence-level
  code paths. Not a slam-dunk free win: the idiom-paraphrase literature
  optimizes for idiom→literal, not idiom→*phonetically-safer*, so this
  project's own phoneme veto still has to do that half of the work
  regardless of which generation approach is used; and rushing the
  detection side (PMI alone, skipping context-sensitivity) would trade
  today's failure mode (idioms wrongly left untouched) for a new one
  (literal, non-idiomatic uses wrongly phrase-replaced).

### 3.9 Fine-tuning or specializing a model for this task specifically

The user's second question: given the eventual goal is a full
profile-to-profile reformulation service, should this project invest in
fine-tuning/specializing T5 (or another model) for phoneme-avoiding,
profile-conditioned reformulation, rather than continuing to rely on an
off-the-shelf generic paraphrase checkpoint?

- **[SOURCED] The closest real precedent is ParaDetox (ACL 2022),** not
  anything phoneme-specific. ParaDetox fine-tuned BART-base on ~10K
  parallel toxic→non-toxic pairs to build a small model specialized to
  rewrite around a *forbidden-content class* while preserving meaning —
  structurally the closest match to "avoid X, preserve meaning" at this
  project's scale. A 2025 follow-up (ParaDeHate) reused the exact same
  recipe for a *different* avoid-class by regenerating training data
  with an LLM in the loop instead of human annotators — direct
  precedent for this project bootstrapping training pairs from its own
  rule-based engine, or from LLM distillation for the harder cases.
- **[SOURCED] PEFT (LoRA) fine-tuning of a T5-base-scale model is
  realistic on a single consumer GPU, not on CPU alone.** A 2025
  profiling study found LoRA/QLoRA fine-tuning feasible on an 8GB-class
  consumer GPU (RTX 4060-tier); T5-base LoRA at rank 16 updates ~0.4%
  of parameters, cutting peak memory from ~12GB (full fine-tune) to
  ~3GB. **No sourced benchmark documents CPU-only *training* of a
  T5-base-scale model at a usable speed** — this project's current
  CPU-only setup is fine for inference (already proven) but fine-tuning
  would need at minimum a free-tier Colab/Kaggle GPU or equivalent, a
  real infrastructure decision, not assumed available.
- **[SOURCED, the load-bearing finding for this whole question]**
  Prompting a capable instruction-tuned model, with the constraint
  spelled out in the prompt, is a **documented, evaluated, competing
  alternative to fine-tuning** in the closest analogous literature — not
  a lesser fallback. ReadCtrl/MedReadCtrl (2024–2025) explicitly frame
  "audience-aware, prompt-based simplification with no fine-tuning" as
  "a viable alternative to fine-tuning... rapid personalization that
  incurs no training overhead," and report their own fine-tuned model
  only modestly beating a strong prompted baseline (52%:36% human-eval
  win rate) — a real edge, but not a rout, and demonstrated at 7B scale,
  not at this project's T5-base scale.
- **[GAP, the central risk to any fine-tuning investment]** No published
  work fine-tunes specifically for *phoneme*-level avoidance in
  paraphrase generation — every real "avoid X" precedent (ParaDetox,
  ParaDeHate, detoxification generally) operates at the word/topic/
  style level, where an off-the-shelf classifier can already detect a
  violation. Phoneme-conditioned avoidance in a meaning-preserving
  paraphraser appears to be a genuine, first-of-kind gap this project
  would be filling itself, not a template to copy — a materially bigger
  lift than "fine-tune BART on 10K pairs" suggests at first glance.
- **[SOURCED] Profile-conditioning architectures exist (prefix-tuning,
  PPlug/Persona-Plug) but are demonstrated at LLM scale, not T5-base.**
  Adapting a learned or hand-built per-speaker prefix to a T5-base model
  is conceptually simple; the specific published results proving it
  works are not at this project's model scale.
- **[SOURCED] Document/speech-level, profile-conditioned reformulation
  is confirmed real, harder, and not solved by looping the sentence-
  level engine.** Document-level text simplification work (arXiv
  2412.18655, 2024) shows naive sentence-by-sentence processing is
  *not* considered adequate for coherence at the document level in this
  literature — cross-sentence pronoun/vocabulary/tone consistency needs
  explicit handling. **[GAP]** All document-level personalization
  literature found is reader-facing (simplify for comprehension), not
  speaker-facing (rewrite for ease of utterance) — the project's
  eventual "profile-to-profile full speech" goal (§1) has no direct
  precedent at the document level; it's confirmed future work, not
  something with a template to follow yet.
- **[SOURCED] A reusable joint evaluation metric already exists,
  independent of whether fine-tuning happens.** ParaDetox's own
  "J-score" (constraint-satisfaction × content-preservation × fluency,
  multiplied into one number) is a real, human-correlated pattern this
  project could adopt now — it already has the content-preservation
  piece (SBERT) and the constraint-satisfaction piece (the phoneme/
  flagged-word check); only a fluency scorer would be new.
- **Agent's own assessment (not a literature finding, stated as such):**
  fine-tuning a *phoneme-level* model is not supported as the right next
  investment — no template exists, and the closest real precedents
  target a categorically easier constraint class. The evidence instead
  supports, in order: (1) try prompting a stronger, more capable
  instruction-tuned model with the constraint's *reason* spelled out in
  natural language, before assuming the current architecture's ceiling
  is the model's fault — zero training cost, directly tests whether
  Cause B (§2.8) is a knowledge problem (the model doesn't know *why*
  to avoid these words) rather than a mechanism problem; (2) only if
  that under-delivers, a ParaDetox-style *word/token-level* LoRA
  fine-tune (real precedent, needs one consumer GPU) — not a
  phoneme-level one.

**The convergence neither research pass was told about the other:**
§3.8's practical near-term recommendation (reuse the existing
restructuring call, scoped to a smaller span, no new model) and §3.9's
practical near-term recommendation (try a stronger *prompted* model
with the constraint's reason spelled out, no fine-tuning) point at the
same shape of next step — improve what the generation call is *told*
and *shown*, before spending on either a idiom classifier or a
fine-tune. See §5's new item 1a.

## 4. Candidate techniques — feasibility summary

| Technique | Targets | Off-the-shelf? | New model/training? | Rough effort |
|---|---|---|---|---|
| spaCy `PhraseMatcher` + curated idiom list | 2.4, 2.7 | Yes | No | Small |
| `pywsd` Lesk-family sense disambiguation | 2.6 | Yes | No | Small |
| SBERT-gloss WSD (reuse existing SBERT) | 2.6 | Yes | No | Small |
| HF constrained beam search (`force_words_ids`) | 2.8 | **No, as of `transformers==5.10.2` — VALIDATION.md §13** | No, but needs `trust_remote_code` or a version pin | Was rated Small; corrected to **Medium+, blocked** until a packaging path is chosen |
| MeaningBERT as a second verification signal | 2.2 | **Yes — validated, VALIDATION.md §15** | No | Small — validation done, engine wiring not yet built |
| NLI bidirectional-entailment check | 2.2, 2.4 | Yes | No | Small-medium |
| BERTScore/MoverScore as a second signal | 2.2 | Yes | No | Small |
| GECToR-style confidence-threshold abstention | 2.1 | Partial (pattern only) | No (if imitating pattern, not model) | Medium |
| Detect-ambiguity → clarify → proceed control flow | 2.1 | No (pattern only) | No | Medium |
| PMI/statistical collocation detection | 2.4 | Partial (NLTK has the math, not a ready list) | No | Small-medium, but crosses into tuning (needs go-ahead) |
| NeuroLogic Decoding/A*esque | 2.8 (partially — Cause B) | No (no pip package) | No, but requires porting research code | Medium |
| PARSEME-trained MWE tagger | 2.4 | No | Adapting an existing tagger | Medium |
| ACCESS/MUSS-style control-token aggressiveness knob | 2.9 | No | Yes — real fine-tuning infra needed | Large — not currently feasible |
| Span-scoped restructuring (existing T5 call, windowed input) | 2.4, 2.8 | Yes (reuses existing model) | No | Small |
| Prompt a stronger instruction-tuned model with the constraint's reason spelled out | 2.6, 2.8 | Depends on model chosen | No | Small-medium |
| Decoder-only instruction-tuned model swap (Qwen2.5-0.5B/1.5B) | 2.8 | **Tested, negative — VALIDATION.md §14** | No | Ruled out at this scale: worse meaning preservation than the T5 baseline, 10-40x slower on CPU |
| Optimized/quantized local inference runtime (`llama.cpp`/GGUF or similar) | 2.8 | No — new dependency, not evaluated | No | Not sized — a separate dependency decision, same category as the `force_words_ids` question |
| MAGPIE-trained in-context idiomaticity classifier | 2.4 | No | Yes, small classifier | Medium |
| ILM-style GPT-2 span infilling | 2.4 | Partial (published code, not a package) | Yes, if used | Medium |
| ParaDetox-style LoRA fine-tune (word/token-level avoidance) | 2.8 | No | Yes — needs a consumer GPU | Medium-large, and needs a GPU decision first |
| Phoneme-level fine-tuning of a paraphrase model | 2.8 | No | Yes, first-of-kind, no template | Large, not currently recommended (§3.9) |
| ParaDetox-style J-score (joint constraint × meaning × fluency metric) | 2.2, 2.5 | Mostly (reuses SBERT + existing constraint check) | Small (a fluency scorer) | Small |

## 5. Ordered implementation plan (proposed — not yet approved or built)

Ranked by strength of evidence (does more than one independent finding point
here) crossed with feasibility (§4). This ranking updates `VALIDATION.md`
§9.11's list with this pass's concrete technique findings; it does not
replace that section, which stays as the dated record of what the pilot
itself supported.

1. **[DONE, 2026-08-17 — `VALIDATION.md` §10] Idiom/fixed-expression
   guard before substitution** (§2.4, §3.1) — highest-evidence problem
   (two independent pilot analyses converge on it). Implemented as a
   curated exact-match list (`semantic.py`'s `IDIOM_PHRASES` +
   pronoun-wildcard `IDIOM_PHRASE_PATTERNS`), reusing the existing
   `protected_positions()` mechanism rather than adding spaCy — smaller,
   lower-risk than the `PhraseMatcher` route §3.1/§4 named, at the cost of
   only covering phrases actually on the list (not a general MWE
   detector — §3.1's `[GAP]` still stands). Verified: the exact broken
   outputs P1 rated no longer occur, 26/30 pilot pairs byte-identical
   (zero collateral change), Stage 6 corpus unaffected. Found and fixed
   one follow-up correctness issue in the same pass (§2.5's update above)
   before calling it done — not shipped with a silently-known gap.
2. **[DONE, 2026-08-17 — `VALIDATION.md` §11] Word-sense disambiguation
   before candidate generation** (§2.6, §3.2) — implemented via
   SBERT-gloss matching against a local context window (reusing the
   existing SBERT model, no new dependency, over the `pywsd` alternative).
   Fixes the general "right"-style sense confusion, not just the one
   phrase §5 item 1 already covered. Re-running Stage 6's corpus (per
   the user's explicit instruction) found two real regressions before
   this was done: a candidate colliding with another declared-difficult
   word (§2.7's update) and two occurrences of one word in a sentence
   forced to the identical sense — both root-caused and fixed in the
   same pass, not shipped with a known gap. One cost accepted and
   disclosed, not engineered around: single-sense candidate pools are
   sometimes smaller/lower-scoring than the old sense-mixed pools even
   when correct (`avg_meaning_preservation` 0.9785 → 0.9652 on Stage 6's
   corpus). Re-checked against the real pilot data: two of P1's own
   articulated grammar complaints (`VALIDATION.md` §9.8) are now
   directly fixed; two unrelated, different-class bugs (POS mismatch,
   a phrasal-verb idiom not on §5 item 1's curated list) remain open,
   named rather than glossed over.
3. **[TESTED, 2026-08-17 — `VALIDATION.md` §12 — result: negative, not
   pursued further as a model swap] Try a stronger, promptable model for
   restructuring, with the constraint's *reason* spelled out in-context**
   (§2.8, §3.8, §3.9) — the diagnostic both parallel research passes
   converged on. Run against all 22 real, currently-failing escalation
   cases (not hand-picked), comparing `google/flan-t5-base` (comparable
   parameter count to the current model) prompted with the profile's
   reason, against the current production baseline, using the exact
   same verification checks for both. **Result: reason-based prompting
   robustly improved meaning preservation (avg. SBERT similarity 0.865 →
   0.950, confirmed again at 3.5× model capacity: 0.982) but did not
   meaningfully improve the actual pass rate (0% → 4.5%, or 9.1% with a
   hybrid hard-blocking variant) — constraint satisfaction, not meaning
   preservation, is the real bottleneck, and a natural-language
   explanation does not reliably fix it at up to ~800M parameters.** Did
   not clear the bar for proceeding to item 4 below (correctly not
   started as a result). Real, useful negative result: rules out "the
   current model just needs a bigger/more-instructable replacement" as
   the fix, and reframes item 5 (constrained beam search) as worth
   testing in combination with reason-prompting, not as an alternative
   to it — the two mechanisms weren't shown to be redundant, just that
   neither alone (nor the specific hybrid tested) was sufficient.
   **Update, 2026-08-18 — R23, `VALIDATION.md` §14: a different
   architecture family (decoder-only instruction-tuned, not just a
   different encoder-decoder checkpoint) was also tested, per direct
   instruction, and also closed negative.** Qwen2.5-0.5B/1.5B-Instruct
   lost to both the T5 baseline and to this item's own flan-t5-base
   result on meaning preservation, and were 10-40x slower per case —
   likely a structural cost of decoder-only generation via plain
   `transformers` CPU inference (no quantization/optimized runtime),
   not a "wrong checkpoint" problem. Item 3 is now closed on three
   independent angles (reason-prompting, constrained decoding, model-
   family swap) — none cleared the bar. The one remaining lever
   (an optimized inference runtime) is a new-dependency decision, not
   a model choice — see item 5's blocked status for the same category
   of open question.
4. **[DONE, 2026-08-18 — `VALIDATION.md` §16] Phrase-level replacement
   tier** (§2.4, §3.8) — the third granularity between word-substitution
   and whole-sentence restructuring, built after the user's own
   reassessment approved it directly (C → A → E → reassess) rather than
   waiting on item 3's original gate. Implemented exactly as designed:
   R19's curated idiom list as the trigger (`semantic.idiom_spans()`,
   new), `rephrase.generate_candidates()` reused unchanged but scoped to
   a local window (span ± 5 tokens) instead of the whole sentence, the
   result spliced back into the full sentence and verified there — never
   the window in isolation — with the same three checks the sentence-
   restructuring tier already uses plus the R20 candidate-collision
   check. Scoped to the "idiom-only" case only (nothing else flagged in
   the sentence); the "mixed" case (idiom span + a separately-
   substitutable word, e.g. pilot pair_15/pair_28) is untouched — every
   real observed case is one of these two shapes, and substitution
   already handles the mixed case correctly. Falls back to R19's exact
   prior behavior when nothing clears every gate.
   **Verified with an isolated, controlled before/after** (`git stash`
   to get a true pre-phrase-tier baseline, not inferred from a stale
   target list): changed exactly one pair in the frozen 30-item pilot
   corpus (pair_01, `gs_hows_it_going` — resolved, SBERT 0.9522),
   byte-identical everywhere else, including Stage 6's 18-case corpus
   and the 210-case ordinary-text corpus (zero collateral change, both
   confirmed, not assumed from zero phrase overlap alone). One honest
   limitation surfaced, not hidden: pair_01's actual output ("Hey, how's
   it today?") is grammatically a little thin despite passing every
   automated gate — the same class of proxy-metric blind spot §9.7/§15
   already found, now observed a third time on a different mechanism.
5. **[BLOCKED, 2026-08-17 — `VALIDATION.md` §13 — feasibility rating
   corrected from Small] Upgrade T5 escalation to HF constrained beam
   search** (§2.8, §3.3) — attempted, not completed. `transformers==5.10.2`
   (this project's installed version) no longer supports
   `force_words_ids` through the standard `generate()` call — the
   feature was moved out of core into a community `custom_generate` repo
   that, tested directly, does not currently provide a loadable
   implementation, and requires `trust_remote_code=True` (a new class of
   risk — running Hub-fetched code at call time — this project has not
   taken on anywhere else). The underlying constraint classes
   (`DisjunctiveConstraint`/`PhrasalConstraint`) are also no longer
   importable in this version. **This item's technique itself was never
   evaluated — the packaging path assumed by §3.3's research
   (documentation-based, not tested against this project's actual
   environment) turned out not to exist.** Real options, none decided
   here: pin an older `transformers` (a real dependency-risk decision
   affecting every model call in this project, not just this one),
   accept `trust_remote_code=True` and wait for the community repo, or
   hand-implement disjunctive decoding (materially larger than "small,"
   closer to the NeuroLogic Decoding route already flagged as
   medium-effort with no maintained package). Surfaced to the user
   rather than decided unilaterally, since it's a dependency-footprint
   decision, not a pure research/implementation one.
6. **[VALIDATED, 2026-08-18 — `VALIDATION.md` §15 — R24, result: real
   but partial, proceed as a second signal only] Add a second semantic-
   preservation signal** (§2.2, §3.7) — candidate: MeaningBERT, reported
   alongside SBERT (never replacing it silently, per Practice.md §10).
   A cheap validation check (14 pairs already in the repo, no new
   corpus, single small model, single forward passes — no long-running
   sweep) found it catches several idiom-adjacent breaks SBERT missed
   badly (largest: SBERT 0.968 vs. MeaningBERT 48.0 on a genuine
   causative-construction break) — but it **completely misses the
   single worst-rated case on record** (human meaning=1/5; both SBERT
   and MeaningBERT score it as fine). Not a strict improvement — a
   different, overlapping-but-not-superset blind spot. Concrete evidence
   (not just an architectural argument) that this doesn't substitute for
   item 4's structural detection: the case MeaningBERT missed is exactly
   the class item 4 targets by *detecting* the fixed expression, not by
   scoring the result more cleverly. Scope going forward: wire in as a
   reported-alongside signal, flag disagreement, don't treat as "the
   fix." §3.9's ParaDetox-style J-score is a related, cheap addition
   worth doing alongside this — both are evaluation-infrastructure
   improvements, not engine changes. **Actual engine wiring not yet
   done** — this was the validation step only, per explicit scope.
7. **[DONE, 2026-08-18 — `VALIDATION.md` §17 — result: not
   substantially explained] Re-examine multi-difficulty interaction
   after (1)** (§2.7) — re-evaluated directly against the live phrase
   tier (R25), as planned. Result: only 1 of the pilot's 3
   `multi_difficulty` cases even involves an idiom span, and that one is
   a mixed case R25 correctly excludes by design; the other 2 have no
   idiom span at all and trace to the separate "generic overused
   replacement" pattern (§9.9) instead. The original hypothesis here —
   compounding mostly explained by §2.4 — does not hold in this sample.
   Stays open as its own problem; n=3 still too small to generalize
   beyond this specific finding, and no further work was started on it.
8. **Input-ambiguity detection + clarification flow** (§2.1, §3.4) — real
   precedent exists for the abstain/ask *pattern*, but this is the largest
   item on this list: it needs a new UX interaction (a clarification
   round-trip), not just an engine change, and deserves its own design pass
   (in the spirit of `PROBLEM_FORMULATION.md`'s treatment of the difficulty
   profile) rather than being bundled into an engine-only sprint.
9. **[NEW, 2026-08-17, explicitly deferred] A ParaDetox-style word/
   token-level LoRA fine-tune** (§2.8, §3.9) — real precedent, but only
   worth it if item 3 (prompting) under-delivers, and gated on an
   infrastructure decision this project hasn't made yet: this needs a
   consumer GPU (or free-tier Colab/Kaggle), not the CPU-only setup used
   everywhere else in this repo. Explicitly **not** a phoneme-level
   fine-tune — §3.9's `[GAP]` found no template for that; scope would be
   word/token-level avoidance only, the same class of problem ParaDetox
   actually solved.
10. **[NEW, 2026-08-17, explicitly future work, not started]
    Document/speech-level, profile-conditioned reformulation** (§1, §3.9)
    — the project's own longer-term "profile-to-profile" goal. §3.9
    confirmed this is a real, harder, distinct problem in the literature
    (naive sentence-by-sentence processing is not considered adequate
    for document-level coherence) with no direct speaker-facing
    precedent to build from — worth its own design pass when the time
    comes, not something to bolt onto the current sentence-level engine.

None of the above is implemented as part of this pass. This is the
prioritized map for a future, explicitly-approved implementation cycle.

## 6. Open questions — what we still do not know

- Whether an idiom guard (item 1) meaningfully improves `global_sound`
  category scores in a follow-up pilot, or whether idiom-breaking is only
  one contributor among others not yet isolated. Won't be known until
  re-tested.
- Whether NLI-entailment or MeaningBERT actually catches this project's
  specific idiom-breaking cases better than SBERT — §3.7 is explicit that
  no external benchmark answers this; it would need this project's own
  small validation experiment before being trusted as a fix rather than a
  plausible idea.
- Whether the "right now"-style WSD bug generalizes broadly (a systemic
  gap in how any polysemous function word is handled) or is concentrated
  in a small set of high-frequency ambiguous words — only two instances
  have been observed so far, both from the same word.
- Whether Cause B (phoneme-class reintroduction in T5 escalation) has any
  feasible near-term fix at this project's scale, or is a standing,
  disclosed limitation of using an off-the-shelf paraphrase model for a
  phoneme-avoidance task — §3.3 did not find one.
- How the therapy-framing tension in §2.9 should actually shape the
  product's positioning — an open product question, not an engineering one,
  and explicitly not decided here.
- Whether a stronger prompted model (§5 item 3) actually outperforms the
  current `bad_words_ids`-only approach when given the constraint's
  reason in natural language, or whether Cause B is more of a mechanism
  problem than a knowledge problem after all — this is exactly why item
  3 is scoped as a diagnostic experiment first, not assumed as a fix.
  Which specific stronger model is even feasible on this project's
  CPU-only setup is itself unresolved — not researched yet, deliberately
  left for the implementation step rather than guessed at here.
- Whether R19's curated idiom list is a large enough trigger set to make
  a phrase-level tier (§5 item 4) worth building now, or whether it
  should wait until the list has grown enough (via real usage/future
  pilots) to justify the tier's added complexity.
- Whether this project will actually get access to a consumer GPU (or
  free-tier cloud GPU) — §3.9's fine-tuning item (§5 item 9) is gated on
  this and it hasn't been decided or even asked about yet.

## 7. Changelog (of this document)

- **2026-08-17** — Document created. Problem Definition (§2) built from
  `VALIDATION.md` §9.6-9.11's real pilot findings, cross-checked directly
  against `reformulate.py`/`semantic.py` source for §2.7's interaction
  mechanism (not assumed from the metrics alone). Research pass (§3)
  executed via WebSearch/WebFetch against real sources, prioritized per the
  user's explicit direction (idiom preservation, WSD, multi-difficulty
  interaction, T5 escalation, plus adjacent-field survey). No code changed
  as part of producing this document.
- **2026-08-17** — §5 item 1 (idiom/fixed-expression guard) implemented
  and verified; §2.4 and §2.5 updated with what was found, including an
  unplanned discovery (protecting an idiom can leave a sentence's declared
  difficulty fully unaddressed, and a follow-up metrics-visibility bug
  found and fixed in the same pass) — not just a status flip to "done."
  Full record: `VALIDATION.md` §10.
- **2026-08-17** — §5 item 2 (word-sense disambiguation) implemented;
  §2.6 and §2.7 updated. Unlike item 1, this one did NOT go smoothly on
  the first pass: re-running Stage 6's corpus (as instructed) found two
  real regressions — a candidate colliding with another declared-
  difficult word, and whole-sentence context failing to distinguish two
  occurrences of the same word — both root-caused and fixed before being
  called done, not shipped with a known gap. One real, disclosed cost
  (smaller candidate pools sometimes score lower even when sense-correct)
  was NOT engineered around, per this project's no-speculative-tuning
  rule. Full record: `VALIDATION.md` §11.
- **2026-08-17** — Two new research passes added (§3.8 phrase-level
  replacement as a third tier; §3.9 fine-tuning/specializing a model for
  this task), prompted directly by user questions, not self-initiated.
  Both independently converged on the same near-term recommendation
  (try a stronger prompted model with the constraint's reason spelled
  out, before either building an idiom classifier or fine-tuning
  anything) — §5's implementation plan re-ranked accordingly (new items
  3–4, existing items renumbered 5–8, two new explicitly-deferred items
  9–10 for fine-tuning and document-level reformulation). No code
  changed — research only, per direct instruction to research before
  deciding next steps.
- **2026-08-17** — §5 item 3 (the promptable-model diagnostic) executed
  and closed with a real negative result, not a positive one: reason-
  based prompting robustly helps meaning preservation but does not fix
  constraint satisfaction, confirmed at two model sizes. §2.8 and §5
  updated. Item 4 (phrase-level tier) correctly stays queued, not
  started, since the plan's own gate for it wasn't met. Full record:
  `VALIDATION.md` §12. The current engine was not touched or replaced —
  this was a side-by-side diagnostic only, per direct instruction.
- **2026-08-17, second** — §5 item 5 (constrained beam search) attempted
  next and found blocked, not evaluated: `transformers==5.10.2`
  (installed) no longer supports `force_words_ids` through `generate()`
  without `trust_remote_code=True`, and the replacement community repo
  doesn't currently provide a loadable implementation either — found by
  direct testing, not assumed from documentation. §4's feasibility
  rating and §5 item 5 corrected from "Small" to "blocked, needs a
  dependency-risk decision." Full record: `VALIDATION.md` §13.
- **2026-08-18** — R23: tested whether a decoder-only instruction-tuned
  model (a different architecture family, not just a different
  checkpoint) beats the T5 baseline, per direct instruction. Closed
  negative — Qwen2.5-0.5B/1.5B-Instruct lost on meaning preservation to
  both the baseline and R21's flan-t5-base result, and were 10-40x
  slower per case on this project's CPU-only, plain-`transformers`
  setup. §4 and §5 item 3 updated. This closes item 3's investigation on
  a third independent angle (prompting, constrained decoding, model-
  family swap) — none cleared the bar. The one remaining lever (an
  optimized/quantized inference runtime) is flagged as a separate,
  not-yet-decided dependency question, same category as item 5's
  blocked status. Full record: `VALIDATION.md` §14.
- **2026-08-18, second** — R24: validated MeaningBERT as a candidate
  second semantic-preservation signal, per the approved C → A → E
  sequence, with an explicit scope limit (14 already-recorded pairs, no
  new corpus, single small model, no long-running sweep). Result: real
  but partial — catches several idiom-adjacent breaks SBERT missed
  badly, but completely misses the single worst-rated case on record,
  the same class of case item 4 (phrase-level tier) targets
  structurally. §3.7's `[GAP]` partially closed; §5 item 6 and §4
  updated. Scope: proceed as a reported-alongside signal, not a
  replacement for SBERT or a substitute for item 4. Engine wiring not
  yet built — validation only. Full record: `VALIDATION.md` §15.
- **2026-08-18, third** — §5 item 4 (phrase-level replacement tier)
  implemented, per the user's own C → A → E → reassess sequencing
  rather than item 3's original gate. `semantic.py` gained
  `idiom_spans()`; `reformulate.py` gained `_try_phrase_replacement()`
  (local-window T5 generation, full-sentence splice and verification,
  safe fallback). Verified with an isolated, controlled before/after
  (`git stash`, not inference from a stale target list): recovered
  exactly one frozen pilot case (pair_01), byte-identical everywhere
  else across three separate corpora. One honest limitation surfaced:
  the recovered output is grammatically thin despite passing every
  automated gate — folded into §2.3 and §2.4's running record, not
  treated as a clean win. Full record: `VALIDATION.md` §16.
- **2026-08-18, fourth** — R26 (§5 item 7, Option E): re-examined the
  pilot's `multi_difficulty` category against the live phrase tier.
  Pure re-analysis, no new code. Result corrects §2.7's own prior
  hypothesis rather than confirming it: only 1 of 3 cases involves an
  idiom span (a mixed case R25 correctly excludes by design); the other
  2 have no idiom span at all and trace to a separate, already-named
  pattern (generic overused replacement words). Factor 2.7 stays open
  as its own problem. §2.7 and §5 item 7 updated. Full record:
  `VALIDATION.md` §17.
