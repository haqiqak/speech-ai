# Architecture Research Archive — R42/R43/R43-A

**Status: historical/archival record, consolidated 2026-08-26. Not part
of the standard CLAUDE.md reading chain (see CLAUDE.md's numbered
reading order) — read this only if you need the full original
reasoning behind a decision already summarized in `VALIDATION.md`/
`DECISION_LOG.md`.**

This file merges three previously separate, now-superseded documents
that were scattered in the repo root and never integrated into the
project's standard documentation chain:

1. `ARCHITECTURE_REASSESSMENT_R42.md` — the original "current architecture
   vs. complete new model?" research pass (R42): diagnosis, failure
   taxonomy, architecture comparison (A–D), and a recommended target
   architecture.
2. `ARCHITECTURE_TRANSITION_R43.md` — R43's instrumented analysis of the
   T5 escalation path specifically, refining R42's taxonomy and
   architecture comparison with direct evidence.
3. `ARCHITECTURE_TRANSITION_R43A_RESULTS.md` — R43-A's bounded
   experiment results (A1 inflected-form blocking, A2 generate-verify-
   regenerate, A3 NLI logical-consistency, A4 grammar re-test, A5
   stacked combination), plus the v5 human-rating corpus.

**What happened to their recommendations:** every actionable
recommendation in these three documents was later carried out and is
documented, with results, in `VALIDATION.md` §35 onward (R44 human
eval) through §46 (Phase 10) — most directly, R45's "two bounded
prototypes" decision (validator + phoneme-aware decoding), built in R46
and evaluated through Phase 9/9B/9C/10. **These three documents are the
reasoning that led there, not a live plan** — if you want to know
*what was decided and what actually happened*, read `VALIDATION.md`/
`DECISION_LOG.md`/`ROADMAP.md` first; come here only for the original,
fuller research argument behind those decisions.

The three documents below are reproduced in full, unedited, in their
original chronological order (R42 → R43 → R43-A), separated by rules.

---

# Part 1 of 3 — R42: Architecture Reassessment

# ARCHITECTURE_REASSESSMENT_R42.md — R42: From Candidate Substitution to Reliable Speaker-Specific Reformulation

**Status: investigation only. No production code, threshold, gate, model, or
config was changed to produce this report.** Written per direct instruction
after R41, reading the actual implementation (`reformulate.py`, `semantic.py`,
`engine.py`, `rephrase.py`, `phonetic.py`, `difficulty_profile.py`) and the
project's own prior architecture research (`REFORMULATION_RESEARCH.md`,
`REFORMULATION_PROBLEM_MAP.md`) rather than relying on summarized memory of
either. Every claim below is evidence-tagged (Practice.md §5): **[FACT]**
(directly verified against code or a completed measurement), **[FINDING]**
(a completed diagnostic result, already on record), **[INTERPRETATION]**
(a reading of facts/findings that could be wrong), **[HYPOTHESIS]** (not yet
tested), **[RECOMMENDATION]** (a proposal, not a decision — nothing here is
authorized for implementation).

---

## A. Executive conclusion

**Case 2, with a specific correction to what "generation-centered" should
mean here.** The architecture is directionally correct — the tagging stage,
the phoneme veto, and the tiered-verification concept are sound and should
stay. But the evidence does **not** support either extreme the user offered
as bookends:

- It does **not** support Case 1 ("just patch the current substitution
  engine") — several of R40's dominant failure classes are structural, not
  patchable by another special case, and one of them (constraint-satisfaction
  failure in the escalation tier) has already been attacked with "improve
  the model" twice (R12/R21's reason-prompting experiment, R14/R23's
  decoder-only-model experiment) and failed both times, for principled,
  now-understood reasons — not from lack of trying.
- It does **not** support Case 3 ("fine-tune a custom model now") either.
  The project's own prior research (`REFORMULATION_PROBLEM_MAP.md` §3.9,
  written before any of R28–R41 existed) already established that no
  phoneme-conditioned fine-tuning precedent exists, that PEFT fine-tuning
  needs a GPU this project doesn't have, and that a training dataset of the
  required shape does not exist and has no defined collection pipeline.
  Nothing in R28–R41 changes that — if anything, R40/R41 shows the dominant
  defects are **verification gaps and an unsolved constraint-representation
  problem**, not a raw generation-quality ceiling that a bigger or
  fine-tuned model would obviously fix.

What the evidence *does* support: the two-tier design (substitution-first,
generation-as-escalation) should be kept, but three concrete gaps — one
already designed and never built, one never tested in the specific form that
would actually test it, and one genuinely new — should be closed **before**
either "patch more special cases" or "start a fine-tuning program" is
considered again. §J gives the ordered next steps.

---

## B. Current architecture diagnosis

### B.1 What it actually is, read from the code

`reformulate.py` (Architecture D′, per `REFORMULATION_RESEARCH.md` §29) runs,
per sentence:

1. **Tag** (`_flagged_positions`, `_idiom_protected_matches`) — POS-tag the
   sentence, mark which content-word positions the profile flags (declared
   word / declared word-specific `problem_phones` / global sound onset via
   `phonetic.matches_any`), excluding stop words and protected/idiom spans.
2. **Pre-escalation decision** (`reformulate.py:630-635`) — if more than
   `escalation_word_count` (default 2) content words are flagged, or the
   flagged fraction exceeds `degenerate_fraction` (default 0.6), skip
   substitution entirely and go straight to step 4.
3. **Substitute-and-rank, all-or-nothing** (`_try_substitution`) — for every
   flagged position: `engine.get_synonyms()` pulls candidates from WordNet
   (same-POS synsets' own lemmas **and hypernym lemmas**, `engine.py:113-117`)
   and Datamuse (`rel_syn`/`ml`), optionally sense-restricted by
   `semantic.disambiguate_synset()` (an SBERT-gloss match against a local
   context window). Each candidate is inflected (`grammar.inflect`), scored
   by `semantic.rank_candidates_contextually()` (SBERT similarity ≥
   threshold, weighted 90/10 against log-normalized Zipf frequency), then
   gated by `is_known_antonym()` (WordNet antonym lookup), a phoneme
   re-check on the candidate itself, and a check that the candidate isn't
   itself another profile-declared-difficult word. **If any one flagged
   position has no candidate that clears every gate, the whole sentence's
   substitution attempt is discarded** (`_try_substitution` returns `None`)
   — no partial patchwork ships.
4. **Escalate** (`_try_escalation`) — only reached if step 2 pre-triggered or
   step 3 returned `None`. `rephrase.generate_candidates()` (T5,
   `Vamsi/T5_Paraphrase_Paws`, beam search, `bad_words_ids` blocking the
   literal flagged words) proposes up to `t5_candidates` (default 5)
   whole-sentence paraphrases. Each is checked against SBERT similarity,
   `negation_consistent()` (a negation-marker-count parity check, not true
   NLI), and a post-hoc scan for the flagged sound/words in every content
   word of the candidate. Best-by-similarity wins; if none pass, the
   sentence is left unchanged and reported as `could_not_safely_reformulate`.
5. **Final verification** — re-run the flagged-word count on the whole
   assembled output and require it to have dropped; report overall SBERT
   similarity. **[FACT]** this does *not* re-run the antonym check or a
   tiered semantic re-verification on the assembled output, despite
   `REFORMULATION_RESEARCH.md` §24.A step 4 explicitly designing for that —
   only the flagged-word count and one SBERT number are re-checked.
6. **Metrics, reported never blended** — SBERT similarity, MeaningBERT
   (`semantic.meaningbert_score`), difficulty-reduction %, edit ratio.
   `contextual_fit_score()` (DistilBERT masked-LM word-probability, R37) is
   computed per substitution-sourced change and attached to `verification`,
   reported-only, never gating (`reformulate.py:645-656`).

A phrase-level tier (`_try_phrase_replacement`) handles the case where the
*only* difficulty in a sentence sits inside an idiom span — replaces a local
window around the idiom via the same T5 call, verified the same way.

### B.2 What it's good at

- **Zero-training-data operation.** Everything above runs on off-the-shelf
  resources (WordNet, Datamuse, a pretrained SBERT, a pretrained T5
  checkpoint) — no supervised reformulation data was ever required to build
  it, which is exactly right for a project that (§H below) still doesn't
  have that data.
- **Hard safety gates that measurably work.** The phoneme veto, the
  antonym check, and the "never reintroduce another declared-difficult
  word" check are symbolic and 100% reliable within their narrow scope — not
  probabilistic. R40's 112-change audit found **zero** cases where a
  substitution reintroduced the flagged sound or a declared word.
- **Single/low-density cases.** R40's `light_single_sound` profile (one
  sound, "str") produced 3 substitutions, all correct, natural, and safe.
  Where the flagged surface is small, the architecture works as intended.

### B.3 Where it structurally fails — not a list of bugs, a list of missing mechanisms

1. **No signal in the pipeline checks propositional/factual/logical
   correctness.** SBERT and MeaningBERT both measure *embedding* similarity;
   contextual_fit measures *local fluency*. None of the three asks "is this
   still true, or does it still mean the same thing at the level of the
   claim being made." "pre-industrial"→"palaeolithic" and "slower"→"easier"
   both read fluently and score well on every existing signal precisely
   because fluency is not the problem with them (§C, §D).
2. **No re-inflection/agreement check on the assembled sentence.**
   Candidates are inflected for the *original* word's slot in isolation;
   nothing re-verifies that a dependent elsewhere in the sentence (a verb's
   number agreement, a determiner's fit) is still correct after the swap.
   This is the same mechanism R32 already found and named ("wrong
   grammatical form landing in the wrong slot") — R40 supplies many more
   instances of it.
3. **The escalation tier cannot express a phoneme-class constraint to the
   generator, and no attempted workaround has succeeded.** T5's
   `bad_words_ids` blocks named words, not sound classes
   (`REFORMULATION_RESEARCH.md` §24.E, verified again directly this pass).
   Two different fixes for this have already been tried and both failed in
   different, informative ways (§C.6).
4. **Candidate-source quality is uneven and not independently graded.**
   WordNet's hypernym-inclusion (`engine.py:113-117`) and Datamuse's
   `ml=` results occasionally surface a cross-POS-adjacent or
   ill-fitting candidate that clears SBERT anyway (a single garbled word in
   an otherwise-similar sentence rarely drops sentence-embedding similarity
   below 0.85).
5. **A curated (not general) fixed-expression list.** `IDIOM_PHRASES` is a
   literal, hand-maintained list. It works precisely for what's on it and
   not at all for what isn't — a known, disclosed design choice
   (`REFORMULATION_PROBLEM_MAP.md` §3.1), not a bug, but its cost is larger
   in practice than previously demonstrated (§C.5).

---

## C. Evidence from R17–R41

### C.1 R29/R31 — the genericness signal: a real mechanism, an unconfirmed consequence

R29 found a genuine, reproducible structural signal: WordNet-hypernym
candidates (`engine.py`'s `for hyper in synset.hypernyms()`) are
structurally *more generic* than the original word, and a combined
`depth_delta` + `zipf_delta` rule cleanly separated "take" (flagged, both
conditions fire) from "seize"/"clutch" (not flagged — rarer, not
anomalously popular) across 3 independent "grab" contexts. R31 then tested
this against **real human ratings** and found it **directly contradicted
twice**: "grab"→"take" was rated 5/5/5 by the actual pilot participant in
both cases R29's signal would have blocked. **[INTERPRETATION, unchanged
from R31]** genericness and naturalness are separate axes; a structurally
generic candidate can still be a perfectly natural, preferred word choice.
Not promoted. **Relevance to R42:** this is direct, first-hand evidence that
adding *more* automated rejection signals to the current architecture, on
intuition alone, is not free — R29's signal looked promising on 4 cases and
was wrong on the cases that mattered most once checked against real human
judgment. Any new gate proposed in §F/§J needs the same discipline: validate
against real judgment before trusting it, exactly as R41 just did for
contextual_fit and found the same shape of problem (real signal, unsafe as a
standalone gate).

### C.2 R32 — multi-substitution interaction ruled out, but a real failure class named

Traced the code directly (`_try_substitution` scores every candidate against
the *true original* sentence, never a partially-substituted one — cumulative
drift is already caught) and tested 5 real+constructed multi-substitution
cases. **[FINDING]** 5/5 traced to exactly one bad substitution each, never
to interaction between two. **[FINDING, the one still relevant]** two of the
constructed cases failed via **wrong grammatical form in the wrong slot** —
"sleep"→"asleep" after "more" (wrong word class for a noun slot),
"start"→"starting" in a finite-verb slot (wrong inflection). This is the
same mechanism as R40's "programs"→"softwares", "Speech"→"Words", and the
four "was"→"were" cases — R32 found and named this failure class first, on
2 cases; R40's systematic 112-change audit found it repeatedly, unselected,
at real scale. **This is not a new discovery in R40 — it's R32's named gap,
now measured.**

### C.3 R33–R36 — the contextual_fit signal: validated as real, never gated

GPT-2 sentence perplexity was tested and rejected (didn't correlate with
known-bad cases). DistilBERT masked-LM word-probability (contextual_fit)
was validated across R33→R36's escalating scrutiny: 16/16 on known-bad
cases, human-confirmed 17/18 (R35), a named "belated"/register blind spot
confirmed real but not universal (2/5 stress cases, R36), inflection/
word-class confirmed as a *complementary* catch (not a strict superset of
what fluency alone catches) — directly consistent with §C.2/§B.3.2's
finding that inflection mismatches are their own mechanism. Wired in R37 as
**Option A: reported-only, never gating.**

### C.4 R37–R39 — deployment, system-level evaluation, and the first honest current-state read

R37 shipped contextual_fit as a diagnostic field, zero collateral change
(131 tests, byte-identical regression baseline). R38's system-level
evaluation, retroactively scoring the frozen pilot corpus, found 2 *new*
contextual_fit false positives beyond the known "rest" quirk — the
blind-spot rate on real data was already higher than the lab corpus alone
suggested. R39's n=1 current-state human evaluation (Group A matched-pair
retest, Group B fresh) found a real, live regression ("sleep"→"nap",
candidate-pool drift, not a code change) and confirmed R30's POS fix works
structurally but exposed a *separate*, still-open candidate-quality problem
for "late". **[LIMITATION, carried forward]** R39 is n=1 — directional, not
a validated study; nothing in R42 treats it as more than that.

### C.5 R40 — the ceiling probe and the 112-change audit: the largest, least-selected evidence base this project has

Two parts, both against real sentences pulled from four live Wikipedia
articles, live Datamuse, no cherry-picking:

- **192 sentence×profile pairs, 4 densities.** 21/192 (11%) failed both
  tiers, concentrated in dense profiles (`heavy_dense` 31%). T5 restructuring
  succeeded in **2/192 runs — the same single sentence** — despite being
  invoked, by the code path itself, every time substitution failed or was
  pre-escalated. It is not currently functioning as a fallback in any
  practical sense.
- **112 individual substitutions, all rated, not a curated worst-of list.**
  8/112 (7%) CLEAN, 21/112 (19%) MINOR, **83/112 (74%) SEVERE.** The SEVERE
  class decomposes cleanly into the mechanisms named in §B.3: nonsense/
  duplicate tokens ("gas gases", "s dioxide emissions" — candidate-source
  quality), wrong sense ("space"→"place", "range"→"place" — no
  propositional-correctness check), grammatical corruption ("softwares",
  "Words patterns", four "was"→"were" cases — no re-inflection/agreement
  check), fixed-term erosion ("small talk"→"little talk" ×6, "search
  engines"→"research engines" — curated-list idiom guard's known cost, at
  real scale), and one case ("slower"→"easier") that inverts its own
  sentence's logic while `antonym_check` recorded `"pass"` — confirmed by
  direct reproduction that "slower"/"easier" are not each other's WordNet
  antonym, so the check structurally cannot see this class.

  A separate, independently confirmed finding: `sanitize_input()`'s
  spellchecker (not the reformulation engine) corrupts "optimises" into the
  noun "optimists" via edit-distance correction — a different subsystem, on
  a different code path, run *before* reformulation ever starts. Cited here
  because it is easy to mistakenly fold into "the reformulation model is
  bad" when it isn't the reformulation model at all.

### C.6 R41 — contextual_fit as a gate: real signal, not a safe binary threshold

Validated against R40's 112 labeled changes. Real separation (CLEAN median
0.0078, SEVERE median 0.00004 — ~200×) but heavy distributional overlap: at
threshold 0.01, 94% of severe defects would be caught **but so would 62% of
substitutions that were actually fine.** Structurally blind to the corpus's
most damaging defects — the "palaeolithic" and "half-century" factual/
logical errors score 0.6–0.999 because they read fluently, which is exactly
what the signal measures. **This is the sharpest piece of evidence in the
whole R17–R41 arc for §D's core claim: fluency, semantic correctness, and
speaker-pronounceability are different objectives, and this project has
built a strong signal for exactly one of them.**

### C.7 Prior, already-completed model-swap experiments (R12/R21, R14/R23) — directly answering §11's "model problem vs. architecture problem" question

Two separate attempts to fix the escalation tier by changing what generates
the candidates, both already run, both informative failures:

- **R12/R21** (`VALIDATION.md` §12): prompted `flan-t5-base`/`-large` with
  the flagged words *and* a natural-language reason ("the speaker stutters
  on words starting with s..."), no `bad_words_ids`. **Meaning preservation
  improved substantially and reproducibly** (avg. SBERT similarity 0.865 →
  0.950, holding across nearly all 22 cases, and rising further to 0.9815 at
  3.5× model size). **Constraint satisfaction did not improve** — 20/22
  leaked the flagged sound anyway, at *both* model sizes tested. The model
  understood the sentence; it did not reliably apply "avoid this
  phonological class" as a rule from a prose explanation.
- **R14/R23** (`VALIDATION.md` §14): tried the opposite lever — a
  genuinely different architecture family, decoder-only instruction-tuned
  models (Qwen2.5-0.5B/1.5B), with `bad_words_ids` this time. The
  block **mechanically worked** (0/8 leaks in the hybrid condition) but
  **meaning preservation collapsed** (avg. similarity as low as 0.57,
  against baseline's 0.86) — and runtime was 10–40× worse than T5 on CPU,
  worsening with model size, not improving.

**[INTERPRETATION]** Two structurally different fixes for the same tier,
tested at three model sizes total, produced a *consistent inverse
trade-off* — explain-and-hope preserves meaning but doesn't enforce the
constraint; block-and-hope enforces the constraint but wrecks meaning — and
neither direction of "try a different/bigger model" closed the gap. This is
first-hand evidence, not inference, that the escalation tier's problem is
**how the constraint is represented to the generator**, not model capability
in general. §F.2/§F.3 return to this directly.

---

## D. Failure taxonomy

| Failure class | Example (from R40) | Current detector | Current response | Root cause | Architectural implication |
|---|---|---|---|---|---|
| Nonsense/duplicate token | "greenhouse"→"gas" → "gas gases" | None | Ships (SBERT 0.928, unaffected by one duplicate word) | Candidate accepted without checking local coherence against its own new neighbors | Needs a cheap local-coherence check (adjacent-duplicate/n-gram sanity), independent of sentence-level embedding similarity |
| Wrong word sense (fluent) | "space"→"place" | SBERT (0.972, passes) | Ships | WSD via SBERT-gloss-match is context-*window*-based, not exhaustive; sentence embedding tolerates one wrong-sense word | This is exactly what NLI was designed to catch in the original architecture and was deferred, not dropped (§F.1) |
| Grammatical corruption (agreement/inflection) | "gases was"→"gases were"; "programs"→"softwares" | None | Ships | No re-inflection/agreement re-check on the assembled sentence; candidate inflected for its own slot in isolation | Needs a real grammaticality re-check on the *final* sentence, not per-candidate — R28's LanguageTool result doesn't settle this, since R28 tested a different error class (§F.4) |
| Fixed-term erosion | "small talk"→"little talk" ×6 | `IDIOM_PHRASES` (curated list only) | Ships if not on the list | Deliberately curated, precision-over-recall design (`REFORMULATION_PROBLEM_MAP.md` §3.1) | Known, disclosed tradeoff — cost is real and larger than previously demonstrated at scale, not a new problem |
| Collocation mismatch | "serves"→"helps" ("It helps many functions") | SBERT (0.967, passes) | Ships | No collocation/idiomaticity signal exists at all | Named gap in `REFORMULATION_PROBLEM_MAP.md` §2.4/§4 (PMI/collocation detection rated "small-medium, crosses into tuning"); still unbuilt |
| Factual/logical drift (fluent) | "pre-industrial"→"palaeolithic"; "slower"→"easier" | None — `antonym_check` passed the second case | Ships | No signal in the pipeline checks propositional correctness; WordNet antonym lookup only catches *lexical* antonym pairs, not context-specific logical inversion | The clearest evidence for a genuinely new verification stage (§F.1) — not fixable by tuning fluency/similarity thresholds |
| Antonym-check blind spot | "slower"→"easier" (`antonym_check: pass`) | `is_known_antonym()` (WordNet direct antonym only) | Ships | "slower"/"easier" are not each other's WordNet antonym — the check is narrow by design (§semantic.py comment: "not general 'too different' drift") | Confirms the check is working as designed, not broken — the gap is the absence of a *contextual* consistency check above it |
| contextual_fit false positive/negative | False negative: "palaeolithic" scores 0.999; false positive risk: many CLEAN substitutions score <0.01 (R41) | `contextual_fit_score()` (reported-only) | N/A — never gates | Measures local fluency, not correctness; distributions overlap too much for a binary threshold (R41) | Real signal, not a safe standalone gate — combine with something orthogonal, don't threshold alone (§F.1) |
| Speaker-profile constraint (candidate reintroduces the difficulty) | — | Phoneme veto + "not another declared word" check | Blocks correctly | N/A | **Working as designed** — 0/112 violations in the full audit; this part of the architecture is not in question |
| Substitution failure → escalation failure | 21/192 sentences, both tiers fail | Pre-escalation trigger + `_try_escalation`'s 3 checks | Refuses (`could_not_safely_reformulate`) | `bad_words_ids` blocks named words only, not a sound class (§B.3.3); two independent model-swap fixes already tried and failed (§C.7) | The escalation tier needs a different constraint mechanism, not a different model (§F.2/§F.3) |

---

## E. Architecture comparison

### E.1 Current substitution-centered system (D′, as implemented)

- **Strengths:** zero training data required; symbolic safety gates that
  measurably work (0/112 phoneme/profile-collision violations); cheap and
  fast for the common case; fully explainable per-change (`triggered_by`,
  `verification` fields already exist).
- **Weaknesses:** no propositional-correctness or agreement/inflection
  re-check (§B.3.1/2); escalation tier non-functional in practice (2/192);
  candidate-source quality uneven; curated-list idiom protection.
- **Data requirements:** none, today. A grammaticality/NLI addition needs no
  new *training* data, only inference-time model calls.
- **Engineering complexity:** low-to-moderate to close the two verification
  gaps (§F.1) — both are additive, don't touch existing gates, same pattern
  already used for MeaningBERT/contextual_fit.
- **Research value:** low as a research direction (nothing novel), but that
  isn't the current bottleneck — see the taxonomy: most SEVERE defects trace
  to *missing checks*, not to the substitution mechanism being wrong in
  principle.
- **Likely ceiling:** the 7% CLEAN rate is a real ceiling for the current
  verification stack specifically — **[HYPOTHESIS]** closing the NLI and
  grammaticality gaps would raise this meaningfully (both target the two
  largest SEVERE sub-classes), but by how much is untested.
- **Fit to objective:** good for the "avoid this sound/word, minimal
  necessary change" half of the objective; weak on "genuinely easier to say
  when local substitution can't do it" — the escalation half.

### E.2 Improved hybrid (current design + closed verification gaps, no primary-mechanism change)

- **Strengths:** everything in E.1, plus closes the two largest measured gap
  classes (propositional correctness, grammatical agreement) using
  components already proven to work in this codebase's own style
  (SBERT-adjacent model calls, reported-then-optionally-gated, same pattern
  as R37).
- **Weaknesses:** does not touch the escalation tier's actual problem
  (constraint representation) — would still fail dense/heavy profiles at a
  similar rate.
- **Data requirements:** none for NLI (off-the-shelf entailment models
  exist, `REFORMULATION_PROBLEM_MAP.md` §4 already scoped this
  "small-medium" effort). A grammaticality check needs no data either — it's
  inference-time, not training.
- **Engineering complexity:** low-moderate, additive only.
- **Research value:** low, but highest confidence-to-effort ratio of any
  option here, because it is closing *named, already-diagnosed* gaps, not
  speculative work.
- **Likely ceiling:** still bounded by the escalation tier's near-total
  failure on dense profiles — this option does not fix R40's `heavy_dense`
  31% failure rate on its own.
- **Fit to objective:** meaningfully better on "preserve meaning/grammar,"
  no better on "still produce something when substitution can't."

### E.3 Generation-centered system (constrained generation first, verification after)

- **Strengths:** in principle, the right shape for "how should this whole
  proposition be expressed differently," which local substitution
  structurally cannot do (§B.1 step 3's all-or-nothing substitution logic
  has no notion of restructuring).
- **Weaknesses, evidenced not assumed:** the two most directly relevant
  experiments this project has already run (§C.7) both failed to make
  *any* tested generation approach reliably satisfy a phonological
  constraint while preserving meaning, across three model sizes and two
  architecture families. Making generation *primary* rather than a rare
  fallback means every sentence — not just the 11% substitution can't
  handle — inherits whichever failure mode (leaks, or meaning-drift) the
  chosen generation approach has. Nothing tested clears that bar today.
- **Data requirements:** none to try prompting-based approaches (already
  tried); real profile-conditioned constrained decoding (phoneme-class-aware
  blocking, §F.2) needs no training data either — it's an inference-time
  mechanism change, not a model swap.
- **Engineering complexity:** moderate for a better constraint mechanism
  (§F.2); would be high if it also meant replacing the verification stack,
  which nothing here argues for.
- **Research value:** the phoneme-class-aware constrained-decoding idea in
  §F.2 is, per this project's own literature review, unattempted and
  potentially genuinely novel for this specific problem shape — real
  research value if it works.
- **Likely ceiling:** unknown without building and testing it — this is the
  honest answer, not a guess dressed as one.
- **Fit to objective:** best fit *in principle* for the restructuring half of
  the objective; **not currently supported as ready to become primary** — no
  tested generation approach here beats substitution's demonstrated (if
  imperfect) success rate.

### E.4 Fine-tuned custom model

- **Strengths:** the only option that could, in principle, learn a joint
  `(text, profile) → reformulation` mapping directly, matching the user's
  own framing of the deeper problem (§5 of the request) most closely.
- **Weaknesses:** every precondition §12 of the request lists as required
  before recommending this is currently unmet (§G).
- **Data requirements:** a supervised dataset of (original text, structured
  profile, accepted reformulation, plus preferably rejected alternatives and
  reasons) that **does not exist today** — this project's entire human-rated
  corpus across all pilot rounds (R35, R39) totals on the order of a few
  dozen rated pairs from a single participant, several orders of magnitude
  below even a proof-of-concept fine-tune (§H).
- **Engineering complexity:** high — GPU access (not currently available;
  this project is CPU-only per `REFORMULATION_PROBLEM_MAP.md` §3.9), a
  labeling/collection pipeline, an evaluation harness that doesn't yet
  exist in the needed form.
- **Research value:** high *if and when* the data problem is solved —
  `REFORMULATION_PROBLEM_MAP.md` §3.9 already correctly identifies this as a
  genuine, first-of-kind research contribution (no phoneme-conditioned
  precedent exists), not a template-following exercise.
- **Likely ceiling:** unknown, and unknowable until the prerequisites in §G
  are met — recommending a ceiling estimate here would be exactly the kind
  of overclaim the request explicitly warns against.
- **Fit to objective:** best fit *in the limit*, worst-supported by current
  evidence for *now* — nothing in R17–R41 demonstrates that the current
  failures are caused by "the model wasn't trained for this task" as opposed
  to "the pipeline is missing two checks and one constraint mechanism,"
  which is a materially cheaper and faster hypothesis to test first.

---

## F. Recommended target architecture

**Not a replacement pipeline — the same D′ shape, with two additive
verification stages and one redesigned constraint mechanism.** No
implementation here; conceptual only, per explicit instruction.

```text
Original text
      +
Speaker difficulty profile
      |
      v
TAG (unchanged) — flagged positions, idiom/protected spans
      |
      v
Pre-escalation density check (unchanged: >2 flagged, or >60% of
content words flagged -> skip to escalation)
      |
      v
SUBSTITUTE-AND-RANK (unchanged mechanism, F.4's grammaticality
re-check added at the END of this stage, not inside the per-
candidate loop)
      |         \
      | (all     \ (any position has no
      |  clear)    no candidate that clears
      v            every gate)
  [candidate       v
   sentence]   ESCALATE — same trigger logic, NEW constraint
      |        mechanism (F.2): phoneme-CLASS-aware candidate
      |        blocking, not literal-word-only bad_words_ids;
      |        same T5 call, same verification checks reused
      |             |
      |             v
      |        [candidate sentence, or refusal]
      |             |
      v             v
   FINAL VERIFICATION on the ASSEMBLED sentence (existing flagged-
   count + SBERT re-check, PLUS the two new stages, run on the
   final output, not just per-candidate):
     - NLI / logical-consistency check (F.1) — catches propositional/
       factual drift that reads fluently (the "palaeolithic"/"slower->
       easier" class)
     - Grammaticality re-check on the assembled sentence (F.4) —
       catches agreement/inflection breaks introduced by substitution
      |
      v
   METRICS (unchanged: SBERT, MeaningBERT, contextual_fit, difficulty,
   edit-ratio — all reported, never blended) — contextual_fit's role
   stays reported-only per R41's finding that it isn't a safe
   standalone gate; the NEW NLI/grammaticality checks are proposed as
   the actual gates, contextual_fit remains a supporting/reported
   signal alongside them, not replaced by them
```

### F.1 The NLI/logical-consistency stage

This is not new work — it is `REFORMULATION_RESEARCH.md` §24.A's own
**tiered verification** design (WordNet antonym → SBERT → NLI on borderline/
ungated cases → final-output re-verification), scoped exactly as that
document recommended (not "NLI on every candidate," which §24.A itself
already rejected as unjustified complexity) and never built. R40's
"palaeolithic"/"slower→easier" cases are close to a textbook instance of the
gap this stage was designed to close. **[RECOMMENDATION, not decided here]**
this should be the first thing actually measured, not assumed effective —
the same discipline R41 just applied to contextual_fit.

### F.2 A redesigned escalation constraint mechanism

**[HYPOTHESIS, not tested]** `REFORMULATION_PROBLEM_MAP.md` §24.E correctly
ruled out blocking *every* word matching a sound class via `bad_words_ids`
(the blocklist would be enormous, crippling generation) — but that finding
was about the extreme case. A **bounded** version — block the N most common
words (by Zipf frequency) matching the profile's flagged onset(s), rather
than either "one named word" (today) or "the entire English vocabulary
matching that sound" (ruled out) — sits in a middle ground this project has
not tried. This is distinct from, and untested by, both already-failed
experiments in §C.7: R12/R21 tried explaining the constraint in prose
(worked for meaning, not constraint-satisfaction); R14/R23 tried a different
model family with the *same* word-only blocking mechanism (worked for
constraint-satisfaction, not meaning). Neither tried widening *what* gets
blocked while keeping the mechanism (`bad_words_ids`) and model (T5,
already proven fast and locally-run) the same. This is a genuinely open,
moderate-effort, no-new-dependency experiment.

### F.3 What this recommendation deliberately does not include

No model replacement. No fine-tuning. No change to the phoneme veto, the
antonym check, the substitution-first ordering, or any existing threshold.
`contextual_fit`'s role is unchanged from R41's finding (reported, not a
standalone gate) — it becomes one input alongside the new NLI/grammaticality
checks in a design decision this document does not make, consistent with
Practice.md §6.

### F.4 The grammaticality re-check is a genuinely re-openable question, not a settled negative

**[INTERPRETATION]** R28 tested LanguageTool against a specific failure
corpus and found a decisive 0/7 negative — but R28's own interpretation was
explicit: that corpus was "syntactically well-formed sentences built from
the wrong word," a *different* class from what R40 found (subject-verb
agreement breaks, non-standard plurals, a noun used as a verb — literal
surface grammar errors, the exact class LanguageTool's sanity probe in R28
*did* catch: `"She go to the store."` → `HE_VERB_AGR`). **[RECOMMENDATION,
not decided here]** re-testing LanguageTool (or an equivalent) specifically
against R40's grammar-corruption class, rather than assuming R28's negative
result generalizes, is a small, cheap, already-scoped next step — R28 also
already found and left unfixed a live attribute-name bug
(`grammar.py::_correct_with_languagetool()`) that would need fixing first.

---

## G. Fine-tuning decision

**No, not now.** Walking through the request's own five preconditions (§12):

1. **Is the task formulation correct?** Partially answerable, not fully —
   R40/R41 shows several of the dominant failure classes (propositional
   drift, grammatical agreement) are *verification* gaps, not evidence that
   `(text, profile) → reformulation` as a learned mapping is the right unit
   of fix for them. A grammaticality checker doesn't need to be learned
   jointly with reformulation; an NLI check doesn't either. Fine-tuning would
   be solving a broader problem than the evidence currently isolates.
2. **Is the input/output representation defined?** Partially — the
   `DifficultyProfile` schema (§8 of the request, confirmed against
   `difficulty_profile.py`: sounds/words/phrases/word-specific
   `problem_phones`, `source`, `meta`) already exists and is reusable
   as-is, per `REFORMULATION_RESEARCH.md` §25's own contract design (reuse
   the object, don't invent a parallel representation). This precondition is
   the closest to met.
3. **Can the failure modes reasonably be solved through architecture/
   ranking/verification instead?** Not established either way for the
   *escalation-tier* failure specifically — §F.2's constraint-mechanism idea
   is untested, and §C.7's two prior model-swap attempts don't yet rule out
   "a different constraint mechanism, same model" the way they rule out "a
   different model, same mechanism." For the *substitution-tier* failures,
   yes — §F.1/§F.4 directly target the two largest SEVERE sub-classes without
   touching generation at all.
4. **Can sufficient training data be obtained?** No — see §H. Nothing close
   to fine-tuning scale exists today, and no collection pipeline exists.
5. **Is there a credible evaluation protocol?** Partially — this project has
   real evaluation infrastructure (`eval/pilot_app.py`, the R40/R41 audit
   methodology) that could extend to a fine-tuned model's output, but it has
   never been run at more than n=1 human rater, far short of what a
   fine-tuning *decision* (not just a demo) would need to trust.

Given 2/5 preconditions are unmet and a 3rd is only partially established,
fine-tuning is not justified now. **What should happen first is §F's two
verification additions and the §F.2 constraint-mechanism experiment**,
measured with the same rigor R40/R41 just demonstrated — and, in parallel
and independent of whether §F's changes are approved, beginning the data
strategy in §H, since building that dataset is itself a long-lead-time
project that gains nothing by waiting.

---

## H. Data strategy (if/when custom learning is eventually pursued)

**No dataset of this shape exists in this repository today — stated
plainly, not implied.** What would be needed:

### H.1 What a label needs to contain

Per the request's own list, and consistent with what this project's
evaluation infrastructure already partially collects (`eval/pilot_app.py`'s
rating schema): original sentence, the structured `DifficultyProfile` it was
paired with, one or more accepted reformulations, a meaning-preservation
rating, a naturalness rating, an ease-of-saying rating (ideally from a real
person who actually has the declared difficulty, not a proxy — the project's
own evaluation-plan table, §28 of `REFORMULATION_RESEARCH.md`, already names
"speaker suitability" as **not automatable, the core research claim itself**),
a preference judgment, and — critically, since R40/R41 shows *rejected*
candidates are as informative as accepted ones — rejected alternatives with
a reason.

### H.2 Realistic scale, explicitly labeled as estimates, not measured

- **Proof-of-concept** (enough to see if a LoRA fine-tune moves at all):
  **estimate, low hundreds** of labeled (text, profile, reformulation)
  triples — enough to detect a gross signal, not enough to trust a
  deployment decision.
- **Useful fine-tune:** **estimate, low thousands**, spanning multiple
  distinct profiles (different sounds/words/phrases combinations) and
  registers (this project's own R40 corpus already shows register matters —
  technical/scientific text failed far more than conversational text) —
  matching the general scale ParaDetox used (~10K pairs) for a *simpler*
  (word/topic-level, not phoneme-level) avoidance task
  (`REFORMULATION_PROBLEM_MAP.md` §3.9).
- **Robust research model:** **estimate, tens of thousands**, with real
  multi-speaker profile diversity — this project currently has one
  effective profile-tester (the single pilot participant across R35/R39),
  several orders of magnitude short of this.

### H.3 How examples could realistically be collected

- **Bootstrap from the existing rule-based engine's *successes*** (the 7%
  CLEAN + 19% MINOR classes R40 already identified) as weak positive
  labels, with the SEVERE class as weak negative labels with a
  machine-derived reason (which gate should have caught it) — this reuses
  work already done, not a new collection effort, though it inherits
  whatever biases the current engine has.
- **Expand the pilot program** beyond n=1 — real people with real,
  self-declared difficulty profiles rating real sentences, the same
  mechanism `eval/pilot_app.py` already implements, just run at larger
  scale and with more participants. This is the only source of genuine
  "ease of saying" labels per §28's own "not automatable" finding.
- **LLM-in-the-loop distillation for the harder cases**, following
  ParaDeHate's precedent (`REFORMULATION_PROBLEM_MAP.md` §3.9) — a capable
  model generates candidate reformulations for review/correction by a human
  rater, rather than a human writing every example from scratch. Faster,
  but introduces a different model's biases into the training data, which
  would need its own disclosure.

### H.4 Fabrication warning

No portion of §H.2's numbers is measured — they are order-of-magnitude
estimates from adjacent literature (ParaDetox's ~10K), explicitly labeled as
such, per the request's own instruction not to invent false precision.

---

## I. Evaluation strategy

**Human evaluation stays central — nothing here proposes replacing it.**
R41 just demonstrated, again, that even the best available automated signal
(contextual_fit) cannot be trusted as a standalone correctness oracle; §C.6
is the sharpest version of a finding this project has now made three times
(R24 for MeaningBERT/SBERT disagreement, R28 for LanguageTool, R41 for
contextual_fit).

A genuinely better architecture (any of E.2/E.3/E.4) needs to be measured on
all eight dimensions the request names, split by what's automatable now vs.
not, extending `REFORMULATION_RESEARCH.md` §28's own table with what R40/R41
add:

| Dimension | Automatable? | Method | What R40/R41 adds |
|---|---|---|---|
| Difficulty avoidance | Yes, fully | Deterministic re-check (existing) | Unchanged — 0/112 violations in the audit, this dimension is not in question |
| Meaning preservation | Proxy only | SBERT + MeaningBERT + **new NLI** | R40/R41: SBERT/MeaningBERT both miss propositional drift that reads fluently; NLI is the proposed, untested answer |
| Naturalness/fluency | Proxy, real | Edit-ratio + contextual_fit | R41: contextual_fit has real signal but is not a safe standalone gate; keep as reported/supporting, not sole arbiter |
| Grammar | Proxy, contested | LanguageTool (R28 negative on a *different* corpus) | R40: a re-test against the agreement/inflection class specifically is a genuinely open question (§F.4), not settled |
| Speaker-specific ease | **No — not automatable** | Real speaker rating only | Unchanged from `REFORMULATION_RESEARCH.md` §28 — still the core, unautomatable claim |
| Preference | No | Real rater, forced-choice | R39: current-state number exists (n=1, directional) — needs scale, not a new method |
| Safety (never reintroduce the difficulty) | Yes, fully | Existing phoneme/profile-collision checks | R40 confirms these work — not where evaluation effort is needed |
| Unnecessary rewriting | Yes, proxy | Edit-ratio / substitution-rate (existing) | Not specifically probed by R40/R41 — a gap in *this* investigation, not the architecture |

**[RECOMMENDATION, not decided here]** Before any of E.2/E.3's proposed
additions are built, extend R40/R41's own methodology (real, unselected
sentences; a labeled, index-matched ground truth; a threshold/behavior
sweep against that ground truth) to whichever new stage is added — the same
discipline, not a new one, applied to the next component.

---

## J. Immediate next steps

In order, each directly justified by a specific finding above:

1. **Instrument, don't yet fix, the escalation tier.** Add per-candidate
   rejection-reason logging to `_try_escalation` (leak / below-SBERT-
   threshold / negation-inconsistent) — R40 §33's own still-open
   limitation. This is prerequisite to §F.2 being testable at all, and it's
   the same "measure before guessing" step R41 just modeled.
2. **Test the NLI/logical-consistency stage (§F.1) against R40's 112-change
   ground truth**, the same way R41 just validated contextual_fit — does it
   separate the "palaeolithic"/"slower→easier" class from the CLEAN/MINOR
   cases, and at what false-positive cost? No implementation into
   `reformulate.py` until this is measured.
3. **Re-test a grammaticality checker (LanguageTool or equivalent) against
   R40's grammar-corruption cases specifically** (§F.4) — a different
   question than R28 answered, cheap to test, and R28's own left-unfixed
   attribute-name bug needs fixing first regardless of the outcome.
4. **Build and test the bounded phoneme-class blocking experiment (§F.2)**
   on the same `heavy_dense`/`single_common_sound` cases R40 already showed
   fail — this is the one genuinely new, untested idea in this report, and
   the cheapest way to find out whether the escalation tier's problem is
   fixable within the current model/mechanism before concluding it isn't.
5. **Start the data-collection conversation now, in parallel** (§H.2) —
   expanding the pilot program past n=1 has a long lead time regardless of
   what §1–4 find, and nothing about starting it commits this project to
   fine-tuning later.

No production code, threshold, or model changes in this report. Waiting for
review before any of the above is scoped further or started.

---

# Part 2 of 3 — R43: Architecture Transition Investigation

# ARCHITECTURE_TRANSITION_R43.md — R43: Instrumented Escalation Analysis and Transition Decision

**Status: investigation only.** No production code, threshold, gate, or model
was changed. This document extends `ARCHITECTURE_REASSESSMENT_R42.md` — it
does not repeat R42's full code walkthrough or R17–R41 recap verbatim;
where content is unchanged from R42 it is cited, not re-derived. What's new
here: (1) R43's instrumentation of the T5 escalation path — an actual
measurement, not a hypothesis, of *why* it fails; (2) a refined, 7-category
failure taxonomy; (3) the four architectures reframed exactly as specified
for this pass, with Architecture D (hybrid constrained generation) given the
deep treatment requested; (4) a corrected mechanism-level answer to "how
should difficulty be represented to a generator," which changes one of
R42's own proposals. Evidence tags per Practice.md §5 throughout.

---

## A. Current architecture

Unchanged from `ARCHITECTURE_REASSESSMENT_R42.md` §B.1 — re-verified against
`reformulate.py`/`semantic.py`/`engine.py`/`rephrase.py`/`phonetic.py` again
this pass, no discrepancy found. Restated in one paragraph: tag flagged
positions → if too many are flagged at once (>2 words or >60% of content
words), skip straight to escalation → otherwise attempt substitution
all-or-nothing (every flagged position needs a candidate clearing SBERT +
antonym + phoneme + profile-collision gates, or the whole sentence
escalates) → escalation calls T5 (`Vamsi/T5_Paraphrase_Paws`) for up to 5
whole-sentence paraphrases, each gated by SBERT similarity, a negation-
marker-count parity check, and a post-hoc scan for the flagged sound/words
in every content word of the candidate → best-by-similarity wins, or the
sentence ships unchanged and is reported as `could_not_safely_reformulate`.
**Substitution is primary; generation is a rarely-reached fallback** — this
characterization, given in the task prompt, is confirmed accurate by the
code, not merely assumed.

---

## B. Evidence from R17–R42 (cited, not re-derived — full detail in R42 §C)

The load-bearing findings, in one line each: R29/R31 — a real structural
signal (candidate genericness) whose assumed consequence was directly
contradicted by human evidence twice; not promoted. R32 — multi-substitution
"interaction" isn't real (5/5 cases trace to one bad substitution), but
named a genuine mechanism: wrong grammatical form landing in the wrong slot.
R33–R37 — `contextual_fit` validated as a real fluency signal, shipped
reported-only. R40 — 192 real sentence×profile pairs; 74% of 112 individual
substitutions have a real defect; T5 escalation succeeded in 2/192 runs (one
sentence). R41 — `contextual_fit` has real signal (~200× median separation)
but no threshold safely gates on it (0.01 catches 94% of defects, wrongly
rejects 62% of good output); structurally blind to fluent-but-wrong
factual/logical errors. R12/R21, R14/R23 — two independent attempts to fix
T5's escalation output by changing the *model* (reason-prompted flan-t5;
decoder-only Qwen) both failed, in opposite ways (meaning vs. constraint
satisfaction), at up to 3.5× and 3.1× model scale respectively.

**[INTERPRETATION, carried from R42, now sharpened by R43]** R12/R21 and
R14/R23 already showed that changing *what generates* the candidate doesn't
close the gap. R43 (§C below) answers the question those two experiments
left open: *why not* — down to the mechanism, not just the outcome.

---

## C. R43 results — instrumenting the T5 escalation path

### C.1 Method

Per instruction: reuse R40's existing 192-case corpus, no new sentences. Of
the 192 (sentence, profile) pairs, exactly **23** ever invoked
`_try_escalation` (21 ended `could_not_safely_reformulate`, 2 succeeded —
both the same sentence, confirmed independently, matching R40's finding
exactly). New script `eval/r43_escalation_instrumentation.py` calls the
same library functions production code calls
(`rephrase.generate_candidates`, `semantic.semantic_similarity`,
`semantic.negation_consistent`, `phonetic.matches_any`) — `reformulate.py`
and `rephrase.py` are not modified — but logs **every individual T5
candidate's fate**, not just the single best one `_try_escalation` keeps.
Every one of T5's 5 candidates per case was independently checked against
all three gates (not short-circuited on first failure), so a candidate's
*complete* gate profile is visible, not just which gate happened to reject
it first.

### C.2 The headline number: it is not fluency, and it is not meaning

**[FACT]** Across 23 cases, T5 generated 115 candidates (5/case). 92 (80%)
were non-duplicates of the input (T5 is not simply refusing/returning the
input — it is actively trying). Of those 92:

| Gate | Pass rate |
|---|---|
| SBERT similarity ≥ 0.85 | **76% (70/92)** |
| Negation-marker parity | **100% (92/92)** |
| Leak-free (no flagged sound/word in any content word) | **4% (4/92)** |
| **Accepted (all three)** | **2% (2/92)** |

**[FINDING]** T5 is, on this evidence, a reasonably competent local
paraphraser — three-quarters of its candidates preserve enough meaning to
clear a strict 0.85 SBERT floor, and negation is never the problem. **The
escalation tier's near-total failure (2/192 across the full R40 corpus, 2/92
non-duplicate candidates here) is overwhelmingly a constraint-satisfaction
failure, not a generation-quality failure.** This directly answers §5 of the
task's list of candidate causes: not (1) generation quality, not (5) SBERT
being too restrictive (it's the least-limiting gate here), not (6)
negation. It is (3)/(4): how the constraint is represented and enforced.

### C.3 The mechanism, read directly from the leaked candidates

**[FINDING, corrects R42's own hypothesis]** R42 §F.2 hypothesized the
leak mechanism was "T5 is free to use *other* common words that happen to
share the flagged sound." Reading the actual 92 candidates and classifying
every leaked word:

| Leak type | Count | Share |
|---|---|---|
| The exact blocked word, appearing **verbatim** | 14 | 9% |
| A **morphological/orthographic variant** of a blocked word (different case, hyphenation, or inflection) | 87 | 59% |
| A genuinely **unrelated** word merely sharing the flagged sound | 48 | 32% |

Concrete examples of the dominant pattern (blocked = `["pre-trained"]`, all
four T5 candidates for the same sentence):
`"pretrained"`, `"pre-training"`, `"pre-trainers"` — three different
respellings/re-inflections of the **same blocked root**, none a genuinely
different word. Blocked = `["reasoning", "such", "systems"]`: the word
**"reasoning" appears verbatim** in multiple candidates despite being
explicitly blocked — `rephrase.py::_bad_words_ids()`'s own docstring already
documents a precedent for this exact class of leak (case/spacing variants
producing different token-ID sequences than the one encoded and blocked,
`VALIDATION.md` §6.3 Cause A) — **this is that same class of leak,
recurring at the escalation-tier level specifically, not fully closed by
the existing fix.**

**[INTERPRETATION]** T5, as a paraphrase-tuned model, is trained to stay
close to its input. When a word is blocked, the path of least resistance is
not "find a different concept" — it's "keep using essentially the same
word in a form that technically isn't the one blocked." This is a different,
more specific, and cheaper-to-fix problem than R42's original hypothesis:
the fix isn't primarily "block a wider vocabulary of same-sound words" (that
addresses only the 32% "unrelated word" category) — it's primarily "block
the flagged word more robustly across its own inflections/spellings," which
addresses the 59%+9%=68% majority.

### C.4 What happens when T5 *does* try harder to avoid the word (the SBERT-failing cases)

**[FINDING]** In the cases where none of T5's candidates cleared SBERT (4
of 23), reading the actual text shows T5 reaching for a genuinely different
word — and landing on the **same defect classes R40 already found in
WordNet/Datamuse substitution**: "surface"→"topography" (wrong technical
term — the same failure shape as R40's "surface"→"layer"/"open"/"rise"),
"steaming"→"soaking" (a different, incompatible cooking process — a
meaning-breaking substitution, not a style change), "small"→"Klein" (a
hallucinated proper noun where a plain adjective was needed), "strategy"→
"strategic" (wrong word class — the exact "wrong grammatical form in the
wrong slot" mechanism R32 already named). **[INTERPRETATION]** This is
strong, direct evidence that the *quality* problem in R40's substitution
audit and the *quality* problem visible here inside T5's own generation are
the **same underlying gap** — no signal anywhere in this pipeline checks
propositional correctness or grammatical fit, regardless of whether the
candidate came from WordNet, Datamuse, or T5. Swapping which component
*generates* the candidate does not touch this gap, because the gap is in
what happens *after* generation, identically for both sources.

### C.5 The one working case, re-examined

**[FACT, revising a small overclaim in R42]** The 2 accepted candidates
(both the same sentence) are "Long-chain sugars **like glucose** tend to
break down into more digestible sugars," replacing "such as starch." R42
§33.6 already flagged this as scientifically backwards on manual review
(glucose is the simple sugar starch breaks *into*, not an example of a
long-chain sugar). **This pass's aggregate confirms it more starkly: the
escalation tier's only success in 92 candidates is itself a quality-
questionable output.** Not one candidate across the full instrumented set
is an unambiguously clean win.

---

## D. Failure taxonomy (refined, per the 7-category structure requested)

| Category | Example | Origin, now precisely located |
|---|---|---|
| **A. Surface/candidate corruption** | `sulfur→s`; `gas gases`; `optimises→optimists` | Mixed origins, now separated: `optimises→optimists` is `sanitize_input()`'s spellchecker (`grammar.py`), confirmed by direct reproduction (R40 §33.6) — **not** the reformulation engine at all. `sulfur→s`/`gas gases` are substitution-tier candidate-ranking failures (a low-information candidate cleared SBERT because a one-word change rarely moves sentence-embedding similarity enough to reject) |
| **B. Grammatical failure** | `programs→softwares`; four `was→were` cases; T5's `strategy→strategic` (C.4) | No re-inflection/agreement check on the assembled sentence, in *either* substitution or escalation output (C.4 confirms this is not substitution-specific) — a missing verification stage, not a candidate-source-specific bug |
| **C. Contextual/collocational failure** | `small talk→little talk`; `serves→helps` | The curated `IDIOM_PHRASES` list only protects what's on it (a disclosed, deliberate tradeoff, `REFORMULATION_PROBLEM_MAP.md` §3.1); collocation has no detector at all (§4's own feasibility table already names this, unbuilt) |
| **D. Semantic/sense failure** | `space→place`; `surface→topography` (T5, C.4) | SBERT/MeaningBERT both measure embedding similarity, which one wrong-sense word in an otherwise-similar sentence rarely moves enough to fail; occurs identically in substitution and escalation output |
| **E. Logical/factual relation failure** | `slower→easier` (substitution); `pre-industrial→palaeolithic` | No signal anywhere checks propositional/factual correctness; `is_known_antonym()` only catches *lexical* antonym pairs, not context-specific inversion — confirmed by direct reproduction that `antonym_check` recorded `"pass"` |
| **F. Constraint-satisfaction failure** | 96% of T5's non-duplicate candidates leak (C.2/C.3) | **Now precisely measured, not inferred**: 68% of leaks are the blocked word (or a variant of it) surviving `bad_words_ids`; 32% are a different word sharing the sound. `bad_words_ids` operates on exact tokenized strings, is not morphology-aware, and (per the existing case-variant precedent in `rephrase.py`'s own docstring) is not fully robust to tokenization-context differences either |
| **G. Dense-profile failure** | `heavy_dense` 31% both-tiers-failure rate (R40) | Compounds B/D/F: more flagged positions means more chances for one substitution to fail, and pre-escalation routes dense sentences to the tier F shows is the weakest link — not a separate mechanism, an amplifier of the others |

**[INTERPRETATION]** Categories B and D are now confirmed, by C.4's direct
reading, to occur identically whether the candidate comes from WordNet/
Datamuse or from T5. This is the single most important structural fact this
pass adds: **the bottleneck is not which component generates the candidate,
it is the absence of two verification stages (propositional/logical
correctness, and grammatical re-check on the assembled sentence) that would
catch these regardless of source.**

---

## E. Ceiling analysis — what exactly is the ceiling

Per §4 of the task: separate bad candidate generation, bad constraint
representation, inadequate verification, inadequate sentence-level
generation, or a combination.

**[RECOMMENDATION, the honest read of C+D together]** It is a combination,
but not an equal one — **inadequate verification is the dominant,
common-mode cause**, present in both substitution and escalation output
identically (categories B, D, E). **Constraint representation is the
dominant cause specifically within the escalation tier** (category F,
now measured at 96% failure and mechanistically explained in §C.3).
**Generation quality itself — T5's raw ability to produce a fluent,
meaning-preserving paraphrase — is not the bottleneck**: 76% of its
candidates clear a strict SBERT floor, and two independent prior
experiments (R12/R21, R14/R23) already showed that neither a differently-
prompted nor a differently-architected model closes the gap, because
the gap isn't there.

What the current architecture is genuinely good at, restated precisely
from R42 §B.2 and reconfirmed here: hard safety gates (0/112 phoneme/
profile-collision violations across the full R40 audit), zero-training-
data operation, and the light-profile case (R40's `light_single_sound`:
3/3 correct). What it fundamentally struggles with — restated with C.4's
addition — is **exactly the shape of problem the task names**: generating
or selecting a sentence that simultaneously satisfies an arbitrary,
speaker-specific avoidance constraint while preserving meaning, logic,
grammar, and naturalness, **regardless of whether that sentence comes from
local substitution or whole-sentence generation.** Adding more synonym
sources will not fix categories B/D/E — they occur after candidate
generation, at the verification stage, identically for any source.

---

## F. Architecture comparison (A/B/C/D as specified for this pass)

### Architecture A — Current candidate substitution (unmodified baseline)

Strengths/weaknesses unchanged from R42 §E.1. **New in this pass:** C.4's
finding that T5 output has the *same* quality problems as substitution
output means Architecture A's core weakness (missing propositional/
grammatical verification) is not a substitution-specific defect that a
different generation source would sidestep — it would need fixing
regardless of which architecture is chosen. **Ceiling: the 7% CLEAN rate
from R40, bounded above by the missing verification stages, not by the
substitution mechanism itself.**

### Architecture B — Stronger substitution (A + NLI + grammar check + better ranking, escalation unchanged)

This is R42 §E.2, unchanged in substance. **New in this pass:** because
categories B/D/E occur identically in escalation output, adding NLI and a
grammaticality re-check to the *final assembled output* (not just
substitution's per-candidate loop) would catch these defects **regardless
of whether the sentence came from substitution or from T5** — meaning
Architecture B's verification additions are not wasted even if the
escalation mechanism is later redesigned; they sit downstream of both.
**This is the highest confidence-to-effort option of the four**, precisely
because C.4 shows it targets the common-mode cause, not a source-specific
one. **Does not address category F** (the escalation tier's near-total
practical failure) — `heavy_dense`'s 31% failure rate would not
meaningfully improve from B alone.

### Architecture C — Generator-first (generation becomes primary, not fallback)

**[RECOMMENDATION, directly evidenced]** Not supported as a standalone
change. Making generation primary means *every* sentence, not just the 11%
substitution can't handle today, would be exposed to category F's 96%
constraint-leak rate. Flipping the order without also fixing how the
constraint is represented and enforced would very likely be a regression,
not an improvement — R43's own numbers show this precisely: only 2% of
T5's candidates currently pass every gate, dramatically below substitution's
demonstrated (if imperfect, 26% CLEAN+MINOR) success rate. **Architecture C
only becomes viable paired with Architecture D's constraint-mechanism
fix** — as a standalone reordering, it is not recommended.

### Architecture D — Hybrid constrained generation (generation + independent multi-signal verification) — the option most wanted for this pass

This is the architecture worth building toward, but §C.3's finding changes
*what the generation side needs*, compared to R42's original proposal.

**[RECOMMENDATION]** Two candidate fixes for the constraint-representation
problem, now ranked by C.3's actual leak-composition data rather than
assumption:

1. **Robust morphological/orthographic blocking of the named flagged
   words** (addresses the 68% majority of leaks — literal-word and
   morphological-variant leaks combined). Concretely: encode every
   inflected form of each blocked word (not just case/spacing variants,
   which `_bad_words_ids()` already handles) before calling
   `generate_candidates`. **Lower effort than R42's original proposal**,
   because it targets a precisely-measured majority cause with a narrow,
   well-scoped fix — generate the inflected forms via the same
   `grammar.inflect()`/lemmatization machinery `reformulate.py` already
   uses for substitution, no new dependency.
2. **Generate → verify → regenerate with targeted feedback**, instead of a
   static pre-generation blocklist: when a candidate leaks, tell the model
   *specifically which word leaked* and ask for a genuine alternative,
   rather than silently trying a fixed beam-search budget and giving up.
   This directly targets the *behavioral* pattern C.3 observed (T5's
   default move is a minimal edit that dodges the letter of the block, not
   the spirit of it) by making the failure explicit in the next prompt
   rather than implicit in a blocklist it can route around.
3. Sound-class-aware blocking (R42's original proposal) remains worth
   doing but is now correctly sized as addressing the smaller, 32%
   minority of leaks — a secondary improvement, not the primary fix.

Layered on top, per R42 §F.1/F.4 (unchanged by this pass): an NLI/logical-
consistency check and a grammaticality re-check on the assembled output,
run identically regardless of candidate source, per §E's finding that
categories B/D/E are source-agnostic.

**Strengths:** directly targets the two dominant, now-measured cause
classes (verification gaps, constraint-representation mechanism) rather
than a source swap. **Weaknesses:** more moving pieces than B; the
generate-verify-regenerate loop (item 2) adds latency (multiple T5 calls
per sentence in the worst case) not yet measured. **Data requirements:**
none for items 1/2/3 above or the verification additions — all inference-
time mechanism changes, no training. **Engineering complexity:**
moderate — item 1 is small (reuses existing inflection code); item 2 is a
real control-flow change to `_try_escalation`; item 3 is small. **Research
value:** item 2 (targeted regeneration) is, per this project's own prior
literature review, not templated anywhere found — a genuine, if modest,
contribution. **Likely ceiling:** unknown without building it — stated
honestly, not guessed. **Fit to objective:** the best fit of the four,
*because* it's now aimed at measured causes rather than a hypothesized one.

---

## G. Fine-tuning decision

**Not yet — and R43 strengthens, not weakens, this conclusion.** R42 §G
already found 2 of 5 preconditions unmet (no training data, no collection
pipeline). R43 adds a sharper reason specific to the escalation tier: fine-
tuning implicitly assumes the *model* is the limiting factor. C.2 shows
T5's raw output quality (76% clear a strict meaning-similarity floor) is
**not** the limiting factor — the limiting factor is a **mechanism**
(how the constraint is enforced) that a fine-tuned model driven through the
*same* `bad_words_ids`-based application would inherit unchanged. Fine-
tuning a model without first fixing the constraint-application mechanism
would very plausibly reproduce the same 96% leak rate on a better-sounding
model — an expensive way to not fix the actual problem. **Fix the mechanism
first (§F.3's items 1–2); only reconsider fine-tuning if a mechanism fix,
properly measured, still leaves a gap that looks like a generation-capacity
problem rather than a constraint-representation one.**

---

## H. Data strategy

Unchanged from R42 §H — no new data-scale claims are made or needed by
R43's findings, since none of §F.3's recommended next steps require
training data. Restated once: no dataset of the required shape exists
today; realistic scale estimates (low hundreds for proof-of-concept, low
thousands for a useful fine-tune, tens of thousands for a robust research
model) remain explicitly labeled as literature-derived estimates, not
measurements, per R42 §H.4's own fabrication warning.

---

## I. Next bounded experiments

Only what's needed to resolve remaining architectural uncertainty, in
order:

1. **Implement and test §F.3 item 1 (robust inflected-form blocking) as an
   isolated diagnostic, not production code** — re-run against the same 23
   escalation-invoked cases from this pass. If the 68%-majority leak class
   drops substantially, this is strong, cheap, evidence-based grounds to
   propose it for production (a separate, future decision). If it doesn't
   move the number much, that itself is important — it would mean the
   leak-composition read in §C.3 needs revisiting.
2. **Prototype §F.3 item 2 (generate-verify-regenerate with targeted
   feedback) as a standalone script**, same 23-case corpus, measuring
   acceptance rate and latency — both currently unmeasured for this
   specific mechanism.
3. **Test an NLI check against R40's 112-change labeled ground truth**
   (unchanged from R42 §J item 2) — still not done, still the right next
   step for category E.
4. **Re-test a grammaticality checker against R40's specific grammar-
   corruption cases** (unchanged from R42 §J item 3) — for category B,
   which C.4 confirms also occurs in escalation output, so this check's
   value is not substitution-specific.

Each of these is a diagnostic script against existing corpora — no new
large uncontrolled corpus, no production change, matching the constraint
given for this phase.

---

## J. Final recommendation

**Begin building a bounded, separate research prototype around the
constraint-representation fixes in §F.3 (items 1–2) and the two missing
verification stages (NLI, grammaticality re-check), evaluated against the
existing R40/R43 corpora — without replacing or modifying the current
production substitution-first system, which continues serving as the
baseline, safety fallback, and source of both training-adjacent examples
(§H) and regression tests.** This is a hybrid-transition strategy, not a
full swap: Architecture A stays in production; Architecture D's specific,
now-evidenced components are prototyped and measured against it, in
isolation, before any of them is proposed for production integration. Fine-
tuning remains explicitly not started, and not justified by anything found
in this pass — if anything, R43 makes the case *against* fine-tuning as the
next step slightly stronger, by showing the dominant escalation-tier
failure is a fixable mechanism problem, not a raw model-capability one.

---

# Part 3 of 3 — R43-A: Bounded Experiment Results

# ARCHITECTURE_TRANSITION_R43A_RESULTS.md — R43-A: Bounded Experiment Results (A1–A4) + Track C

**Status: diagnostic scripts only, run against existing corpora (R40's 23
escalation cases / 79 audited sentences). No production code, threshold,
or gate was changed.** This is the evidence you asked for before making
the extend-hybrid / redesign-generation-tier / begin-fine-tuning-prep
decision. Each of A1–A4 tests one candidate fix named in
`ARCHITECTURE_TRANSITION_R43.md` §F.3/§I; Track C builds the next human-
rating corpus, stratified directly against R40's own severity labels.

---

## A1 — Robust inflected-form blocking

**What it tests:** §F.3 item 1 — block every inflected/orthographic form
of each flagged word (via `pyinflect.getAllInflections`, reused
`grammar.inflect`-adjacent machinery) instead of just the literal string
`_bad_words_ids()` already handles. Same 23 escalation cases, same T5
call, only the `blocked_words` argument is richer (avg. 7.7× more entries
per case).

| | Baseline (R43) | A1 (expanded blocking) |
|---|---|---|
| Non-duplicate candidates | 92 | 92 |
| SBERT pass | 76% (70/92) | 75% (69/92) — unchanged, as expected |
| **Leak-free** | **4% (4/92)** | **11% (10/92)** |
| **Accepted (all gates)** | **2% (2/92)** | **9% (8/92)** |
| Cases with ≥1 accepted candidate | 2/23 (9%) | 3/23 (13%) |

**Reading it straight:** real improvement, same direction R43 §C.3
predicted (68% of leaks were the blocked word or a variant of it) — but
smaller than that 68% figure might suggest. Expanding the blocklist wins
back roughly a third of the gap, not most of it. **[INTERPRETATION]**
T5 still has other escape routes even with a much larger blocklist —
consistent with §C.4's separate finding that a good chunk of failures are
T5 reaching for a *different* word that's simply a poor choice, not a
blocking-mechanism gap at all. This fix is worth doing (cheap, no
downside found), but it is not sufficient alone.

---

## A2 — Generate → verify → regenerate with targeted feedback

**What it tests:** §F.3 item 2 — instead of a static blocklist, generate
5 candidates, and if none pass, tell the model *specifically which word
leaked* and regenerate, up to 4 rounds. Same 23 cases.

| | Baseline | A2 (regenerate loop) |
|---|---|---|
| **Accepted** | 2/23 (9%) | **6/23 (26%)** |
| Avg. rounds used | 1 | 2.5 / 4 max |
| **Avg. time/case** | ~2.5s | **~15.1s (≈6×)** |

**The bigger win of the four — with a real cost and a real caveat.**
26% is the best raw acceptance rate of anything tested here. But reading
the 6 accepted outputs directly (not just trusting the gate-pass count,
the same discipline R40 applied everywhere):

- 2 are genuinely clean ("problems"→"issues", "grow"→"develop"; "release"→"emit").
- 1 has a real wrong-word error inside an otherwise fine sentence:
  *"the destroyed trees... are not **displaced** by new trees"* — should
  be "replaced"; "displaced" changes the meaning (physically moved, not
  substituted).
- 1 has a subtler drift: *"less heat is emitted into **the universe**"*
  for "radiating into space" — overstated/wrong register, not nonsense
  but not right either.
- 2 are the same already-known "glucose" (scientifically backwards
  restructuring) and "little talk" cases from R40.

**[FINDING]** More rounds mechanically gets more candidates through the
*existing* gates, but the existing gates still don't check propositional
correctness — so a meaningful share of the "wins" here are wins only in
the narrow sense of "passed SBERT/negation/leak," not in the sense of
"actually good." This is the same throughline as A1: fixing the
constraint-application mechanism helps, but doesn't substitute for the
missing verification layer.

---

## A3 — NLI as a logical-consistency check

**What it tests:** whether `cross-encoder/nli-deberta-v3-xsmall`, run
bidirectionally (premise=original / hypothesis=reformulated, and the
reverse), flags R40's SEVERE cases as `contradiction` more than it flags
CLEAN/MINOR cases — the same validation discipline R41 applied to
`contextual_fit`. All 79 R40 audited sentences.

*(Model note: `nli-deberta-v3-small` failed 3 separate download attempts
— `httpcore.RemoteProtocolError`, the connection resetting consistently
around 50–60MB regardless of file size, not a timeout. Switched to the
smaller `xsmall` variant and downloaded file-by-file with a resume-retry
loop; loaded successfully. Named as a real environment constraint, not
glossed over.)*

| Verdict | n | Flagged as contradiction (either direction) |
|---|---|---|
| CLEAN | 5 | **0% (0/5)** |
| MINOR | 9 | 22% (2/9) |
| SEVERE | 65 | **18% (12/65)** |

**[FINDING] Low recall, but the recall it has is precisely targeted at
the category it was proposed for — and nothing else.** What it *catches*:
"pre-industrial"→"palaeolithic" (correctly flagged, both directions,
confirming the smoke-test result), the "slower"→"easier" logical
inversion, the "glucose" restructuring case, and a few others. **What it
misses, almost entirely:** grammar corruption ("softwares", "Words
patterns" — 0 caught), nonsense/duplicate tokens ("gas gases", "lot of
objects, telling" — 0 caught), and fixed-term erosion ("small talk"→
"little talk" — 0/8 occurrences caught, in either direction, across the
whole corpus). **[INTERPRETATION]** This is not an NLI failure — it's
confirmation that NLI answers a narrow question (does the hypothesis
logically contradict the premise) and R40's taxonomy has several defect
classes that aren't logical contradictions at all, just corrupted or
malformed language. NLI is a precise complement to the missing
grammaticality/nonsense checks, not a replacement for them.

**[FINDING] A real false-positive cost exists too**: 22% of MINOR cases
(2/9) — "proteins"→"peptides" and "step-by-step"→"detailed" — were
flagged as contradiction despite being acceptable simplifications. Small
absolute numbers (n=9), but not zero.

**[FINDING, incidental, worth flagging on its own]** One SEVERE case NLI
flagged turned out not to be a reformulation-engine defect at all:
*"chatbots"→"**chariots**"* appears in the corpus's own base text,
confirmed present regardless of which profile/reformulation is applied —
the same class of bug as R40 §33.6's "optimises"→"optimists"
(`sanitize_input()`'s spellchecker corrupting a word before reformulation
ever runs), now a **third** independently-found instance. Not counted
against the reformulation engine's own numbers; flagged here so it isn't
mistakenly folded into "NLI validates the reformulation engine's defect
rate" — it validates the *pipeline's* defect rate, which includes at
least two subsystems.

---

## A4 — Re-testing grammaticality (LanguageTool) against R40's specific class

**What it tests:** §F.4 — R28 found LanguageTool 0/7 against a *different*
error class ("syntactically well-formed sentences built from the wrong
word"). Re-tested here against R40's actual grammar-corruption cases —
5 SEVERE-grammar sentences, the "was"/"were" pair (correct vs. corrupted,
side by side), and 6 CLEAN sentences as a false-positive check.

| Case | Result |
|---|---|
| "study of **softwares**" | **Caught** — `SOFTWARES` rule, correct and specific |
| "practices **device** greenhouse gases" (noun-as-verb) | Flagged, but for the *wrong* reason (`POSSESSIVE_APOSTROPHE`, unrelated to the actual defect) — not a real catch |
| "quiets between two people" | Missed |
| "Words patterns between women" | Missed |
| "gases **was**" (correct) vs. "gases **were**" (corrupted) | **Both** return 0 matches — cannot distinguish grammatical from ungrammatical here at all |
| 5 of 6 CLEAN sentences | Correctly silent |
| 1 of 6 CLEAN sentences (`"( AI )"` spacing) | A benign false positive — parenthesis-spacing, pre-existing in the base text, unrelated to any substitution |

**[FINDING]** A real, if narrow, positive this time — not R28's clean
negative. LanguageTool catches the one case that's a *textbook* rule
violation (uncountable-noun pluralization) but misses the subject-verb
agreement case entirely (the attractor-noun pattern — "gases" sitting
between the true singular subject and the verb — is a documented hard
case for rule-based checkers generally, not specific to this tool) and
both non-standard-plural cases. **Recall on R40's actual grammar-
corruption class: 1/5 clean, 1/5 wrong-reason, 3/5 missed — roughly 20%
real recall.** Confirms R42 §F.4's read: worth having as a supplementary
check, not sufficient alone, and not free of false positives either.

---

## Track C — v5 human-rating corpus, built and ready

New `eval/pilot_select_pairs_v5.py`: 20 sentences selected directly from
R40's frozen output (no new `reformulate()` run — the exact captured
text is reused), stratified 4 CLEAN / 4 MINOR / 12 SEVERE across all 4
profile densities, spanning every named defect class (nonsense/duplicate,
wrong-sense/factual, grammar corruption, fixed-term erosion, the
"slower→easier" logical inversion, the scientifically-backwards
restructuring case, and more). Written to `eval/pilot_pairs.json`
(v4's data archived to `eval/archive_v4/` first, untouched, mirroring the
v3→v4 precedent). `eval/pilot_app.py` needs no changes — it already
reads `pair_id`/`original_text`/`reformulated_text` generically.

**What this buys, once rated:** the first independent human check of
whether R40's CLEAN/MINOR/SEVERE classification (the evidentiary basis
for R42/R43's entire architecture argument) matches real human judgment,
not just Claude's own reading. `claude_audit_verdict` is stored as
metadata for POST-HOC comparison only — never shown to the rater, never
blended into their scores, same discipline as `profile_match` in every
prior pilot round. **Not yet rated — needs a human session**, same as
every pilot round before it.

---

## Synthesis — what A1–A4 collectively say

Four different, independent fixes, each targeting a different named gap:

| Fix | Targets | Result |
|---|---|---|
| A1: expanded blocking | Constraint-application mechanism (the 68% majority leak cause) | Leak-free 4%→11%, accepted 2%→9%. Real, partial. |
| A2: regenerate loop | Same mechanism, different approach | Accepted 9%→26%, but ~6× slower, and ~half the "wins" still carry real defects on direct reading. |
| A3: NLI | Missing logical-consistency check | Catches 18% of SEVERE (precisely the logical/factual class), 0% FP on CLEAN, some FP on MINOR. Narrow but real, no overlap with A1/A2's target. |
| A4: LanguageTool | Missing grammaticality check | ~20% real recall on the grammar-corruption class specifically, one clean genuine catch, real misses on the harder agreement cases. Narrow but real, no overlap with A1/A2/A3. |

**[INTERPRETATION, direct]** No single fix here is close to sufficient on
its own — none reaches even 30% on the dimension it targets. But they
target **different, non-overlapping** failure classes (§D's taxonomy),
and none of the four showed evidence of *hurting* anything else measured.
This is consistent with — and now measured evidence for — R42/R43's
standing read: the current architecture's problems are a **set of
specific, addressable gaps**, not one root cause a single change would
close. Stacking A1+A3+A4 (mechanism fix + logical check + grammar check)
would plausibly compound rather than substitute for each other, since
they don't overlap in what they catch — but that compounding has not
been measured, only argued; the honest next step, if you want that number
before deciding, would be running all three together on the same 23/79
cases rather than assuming additivity.

**What this does not do:** none of A1–A4 individually demonstrated
recovering anywhere near 74%→low-defect-rate territory on this evidence.
Whether stacking them closes enough of that gap is answered directly
below, not left open.

---

## A5 — The stacked experiment: A1 (expanded blocking) + A3 (NLI) + A4 (grammar), together

**What it tests:** exactly the open question above. Same 23 escalation
cases, generation uses A1's expanded blocking, and every candidate must
now clear five checks instead of three: SBERT, negation, phoneme/word
leak (unchanged), **plus** NLI (neither direction predicts contradiction)
**plus** LanguageTool (zero matches). A2's iterative regeneration is
deliberately excluded — a different kind of change (control-flow, not a
filter), tested separately so this measures the filter-stack question
cleanly.

| | Baseline | A1 alone | **A5 (A1+A3+A4 stacked)** |
|---|---|---|---|
| Non-duplicate candidates | 92 | 92 | 92 |
| Accepted | 2 (2%) | 8 (9%) | **4 (4%)** |
| **Cases with ≥1 accepted candidate** | 2/23 (9%) | 3/23 (13%) | **1/23 (4%)** |

**[FINDING, the decisive number]** Stacking more checks *lowered* the
acceptance rate relative to A1 alone — mechanically expected (each added
gate is a stricter AND, so it can only hold or shrink the pool) — but
this is the honest ceiling, not a regression to explain away. NLI alone
rejected 29 of the 92 candidates and grammar rejected 13, on top of what
SBERT/negation/leak already rejected — real, additional problems the
three original gates were letting through, now caught. **Only 1 of the 23
hard, dense-profile sentences produced any candidate that survives a
genuinely comprehensive check.** Read directly, its 4 surviving
candidates are actually clean:

> "Many of these algorithms were insufficient for solving large reasoning
> **issues** because they experienced a combinatorial explosion,
> **that**/**which** means they become exponentially slower as the
> **issues** **develop**/**increase**." (sbert ≈ 0.984)

That single success is a genuine, trustworthy win — but it is 1 sentence
out of 23. **[INTERPRETATION]** This is the clearest single data point in
the whole R42–R43A arc for the architecture decision: even after
implementing every validated fix together — better constraint blocking,
a logical-consistency check, a grammar check — the escalation tier still
fails on 96% of the dense-profile cases it's meant to rescue. The
ceiling isn't being missed because the checks aren't strict enough; it's
that **T5's candidate pool for these sentences rarely contains a
genuinely good option to begin with**. Verification can filter a bad
pool down to a trustworthy remainder, but it cannot make a bad pool
larger. That points specifically at the *generation* side of the
escalation tier — not the verification side — as the actual ceiling,
which bears directly on whether "add more checks to the current hybrid"
(Architecture B/E.2) has room left to close this gap, versus needing a
different generation mechanism (Architecture C/D) to have a real pool to
verify against in the first place.

---

Whether this residual gap is large enough to justify the generation-tier
redesign or fine-tuning-prep track — versus accepting the current
architecture's ceiling on dense profiles as a known, documented
limitation and shipping the cheaper fixes (A1/A4, and NLI for the
substitution tier) as incremental improvement — is the actual decision in
front of you. This document supplies the numbers, not the call.
