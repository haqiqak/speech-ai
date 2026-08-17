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

## 4. Candidate techniques — feasibility summary

| Technique | Targets | Off-the-shelf? | New model/training? | Rough effort |
|---|---|---|---|---|
| spaCy `PhraseMatcher` + curated idiom list | 2.4, 2.7 | Yes | No | Small |
| `pywsd` Lesk-family sense disambiguation | 2.6 | Yes | No | Small |
| SBERT-gloss WSD (reuse existing SBERT) | 2.6 | Yes | No | Small |
| HF constrained beam search (`force_words_ids`) | 2.8 | Yes | No | Small |
| MeaningBERT as a second verification signal | 2.2 | Yes | No | Small |
| NLI bidirectional-entailment check | 2.2, 2.4 | Yes | No | Small-medium |
| BERTScore/MoverScore as a second signal | 2.2 | Yes | No | Small |
| GECToR-style confidence-threshold abstention | 2.1 | Partial (pattern only) | No (if imitating pattern, not model) | Medium |
| Detect-ambiguity → clarify → proceed control flow | 2.1 | No (pattern only) | No | Medium |
| PMI/statistical collocation detection | 2.4 | Partial (NLTK has the math, not a ready list) | No | Small-medium, but crosses into tuning (needs go-ahead) |
| NeuroLogic Decoding/A*esque | 2.8 (partially — Cause B) | No (no pip package) | No, but requires porting research code | Medium |
| PARSEME-trained MWE tagger | 2.4 | No | Adapting an existing tagger | Medium |
| ACCESS/MUSS-style control-token aggressiveness knob | 2.9 | No | Yes — real fine-tuning infra needed | Large — not currently feasible |

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
2. **Word-sense disambiguation before candidate generation** (§2.6, §3.2) —
   small, concrete, reproducible-twice bug with a solved-in-principle,
   small-effort fix (`pywsd` or SBERT-gloss matching).
3. **Upgrade T5 escalation to HF constrained beam search** (§2.8, §3.3) —
   small effort, same library already in use, addresses the R17-follow-up
   side effect (tighter blocking → lower-similarity survivors) without
   claiming to solve Cause B outright.
4. **Add a second semantic-preservation signal** (§2.2, §3.7) — most
   likely candidate: NLI bidirectional entailment or MeaningBERT, reported
   alongside SBERT (never replacing it silently, per Practice.md §10) —
   directly targets the now-twice-confirmed one-directional SBERT blind
   spot at its root, rather than only patching the specific surface cases
   (idioms) that happen to have been found so far.
5. **Re-examine multi-difficulty interaction after (1)** (§2.7) — n=3 in
   the current pilot is too small to act on alone; re-evaluate specifically
   once the idiom guard exists, since much of the compounding risk may
   already be explained by §2.4 rather than needing its own separate fix.
6. **Input-ambiguity detection + clarification flow** (§2.1, §3.4) — real
   precedent exists for the abstain/ask *pattern*, but this is the largest
   item on this list: it needs a new UX interaction (a clarification
   round-trip), not just an engine change, and deserves its own design pass
   (in the spirit of `PROBLEM_FORMULATION.md`'s treatment of the difficulty
   profile) rather than being bundled into an engine-only sprint.

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
