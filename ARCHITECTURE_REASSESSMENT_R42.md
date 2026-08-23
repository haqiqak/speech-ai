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
