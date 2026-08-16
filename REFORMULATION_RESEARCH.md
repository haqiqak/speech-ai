# REFORMULATION_RESEARCH.md — Stage 5: Researching and Defining the Reformulation Problem

Per Practice.md §19: this is a research pass (steps 1–8), not implementation
(step 9). **Nothing in `grammar.py`, `semantic.py`, `engine.py`, `rewrite/`,
or `rephrase.py` was changed to produce this document.** It builds directly
on `RESEARCH.md` (Stage 3's literature review) and `PROBLEM_FORMULATION.md`
(the Stage 4A profile foundation and its audit) rather than repeating them —
where this document says "see RESEARCH.md §X," that finding still holds and
isn't re-derived here. This document goes where those two didn't: minimal-edit
architectures, phoneme-position/cluster granularity, student-hardware
feasibility, a second close prior system, failure-mode construction, an
explicit objective function, and a ranked architecture recommendation.

**Legend** (same as `RESEARCH.md`, reused for continuity): **[FINDING]**
(literature-supported, cited) / **[INTERPRETATION]** (our reasoning from a
finding) / **[HYPOTHESIS]** (untested claim) / **[LIMITATION]** (named gap)
/ **[FUTURE WORK]** (deferred) / **[RECOMMENDATION]** (proposed, not
decided).

---

## 1. Problem definition

Building directly on `PROBLEM_FORMULATION.md` §1 (which already refined the
original single-profile framing into four explicit categories: global
sound, word, phrase, word-specific pattern), the reformulation engine's
contract is:

> Given transcribed/entered text and a **speaker difficulty profile** (the
> four categories above — a mix of hard-declared facts and, per §11.3 of
> the audit, some acknowledged known-unknowns like which pronunciation
> variant was meant), produce the **minimal sufficient transformation**
> that keeps meaning, entities, and discourse context intact, stays
> grammatical, reads as natural rather than "obviously edited," and
> measurably reduces the speaker-specific articulatory burden of the
> flagged material.

**[INTERPRETATION, refining the task's own framing]** The task's example
("What is the best linguistically natural way to express the same idea
while reducing this speaker's specific difficulty?") is the right question,
but it presupposes a single answer exists per input. It usually doesn't —
"I need to carefully review three reports" is *one* valid reformulation of
the example sentence, not *the* answer. The engine's job is closer to:
**produce a small, ranked set of valid reformulations and let symbolic
verification (not the generator's own confidence) decide which pass**, a
distinction that matters directly for the architecture comparison in §12.

---

## 2. Speech/disfluency/stuttering research

`RESEARCH.md` §2.F already covers Fluent (2021) and the clinical
avoidance/circumlocution tension in depth — not repeated here. New this
pass:

### 2.1 Brown's four factors — the foundational, citable framework

**[FINDING]** Wendell Johnson and Spencer Brown's classic work (1945,
reconfirmed by decades of subsequent research) identifies four linguistic
factors that predict where stuttering occurs in an utterance: **word-initial
phoneme**, **grammatical function** (content vs. function word), **word
position within the sentence**, and **word length**. Modern sources
describe this as still the operative predictive framework: "numerous
studies have confirmed the relationship between Brown's four features... and
the predictability of stuttering events."

**[FINDING]** Direct, quantified support for each factor, from position/
stress/cluster-focused stuttering-loci studies:
- **Word-initial dominance**: "stuttering occurs more on initial position of
  the word than medial or final position" — one study found 97.8% of
  stuttering events on first syllables of words, 76.5% on the first sound
  of syllables specifically; another found 92–100% word-initial/syllable-
  initial occurrence in adults who stutter.
- **Stress**: stuttering loci are higher in stressed syllables than
  unstressed ones, in both word-position categories independently.
- **Content vs. function words**: inflected/content words are stuttered
  more than non-inflected/function words.
- **Consonant clusters**: "latencies were longer for words beginning with
  consonant clusters than for words beginning with a single consonant" —
  clusters "spike stuttering frequency by demanding precise sequencing
  under time pressure," though a re-analysis (Roelofs 2002a) suggests part
  of the cluster effect may actually be a word-length confound, not a pure
  cluster effect — the field itself flags this as unresolved, not settled.
- **Word length**: longer words and longer sentences are stuttered more.
- **Consonants over vowels**: stuttering occurs more on consonant sounds
  than vowel sounds.

**[INTERPRETATION — this is the single most load-bearing finding for §16's
objective function and §8's phoneme-granularity question]** Our existing
difficulty formulas (`phonetic.word_difficulty()`:
`0.4·onset + 0.3·syllables + 0.3·rarity`; `profiling/profile.py`'s
`0.45·onset_risk + 0.25·length + 0.20·frequency + 0.10·grammatical_class`)
already capture **onset** (Brown factor 1, partially — onset *cluster
length*, not onset *phoneme identity* risk directly) and **length**
(factor 4) and, in the profiling variant, **grammatical class** (factor 2,
content vs. function). What neither formula captures at all is **factor 3
— word position within the sentence** — nor does either capture **stress**
(a real, quantified effect above, but not one of Brown's original four).
This is a **[LIMITATION]**, concretely named rather than assumed: our
existing formulas are missing one of the four classic factors entirely and
one well-evidenced factor from the broader loci literature. Both are
realistically addable — sentence position is a trivial token-index
computation, and stress is derivable from CMU dict's stress-digit
annotations (already present in the phones our code strips out via
`re.sub(r"\d", "", p)` in `phonetic.py` — **the information is already
being discarded, not unavailable**).

### 2.2 SpeechAgent (2026) — a second, more recent close prior system

**[FINDING]** "SpeechAgent: An End-to-End Mobile Infrastructure for Speech
Impairment Assistance" (arXiv 2510.20113, 2026) is architecturally the
closest system found to date, closer than Fluent in one respect
(end-to-end pipeline including reformulation) though further in another
(no phoneme-level personalization at all). Four stages: (1) a Transformer
classifier over mel-spectrograms detects impairment **type** (dysarthria /
stuttering / aphasia / healthy, 95.0±2.0% accuracy) — a coarse,
population-class signal, not an individual speaker profile; (2) Whisper
ASR transcribes; (3) an LLM (GPT-4.1, Gemini 2.5, or smaller Qwen3/Gemma3-4B
alternatives tested) rewrites the transcript conditioned on the detected
impairment class, modeled as maximizing `p(I|S') × p(S'|S,Z)` where `Z` is
the LLM's own latent understanding of speaker intent; (4) TTS. Evaluated
with BERTScore/BLEU/cosine-similarity (text) and human clarity ratings +
comparison mean-opinion-score + a **"recovery rate"** metric — re-running
the *same* impairment classifier on the refined speech and checking whether
it now classifies as "healthy." Sub-1-second end-to-end latency achieved
via a cloud-server/edge-device split (heavy models run on a server, not the
device).

**[INTERPRETATION — direct comparison to our system]**

| | SpeechAgent (2026) | This repo |
|---|---|---|
| Difficulty representation | Population-level impairment **class** (one of 4 labels) | Individual, declared, four-category profile (sounds/words/phrases/word-specific patterns) |
| Reformulation model | Large cloud LLM (GPT-4.1/Gemini 2.5) primary; smaller local models (Qwen3, Gemma3-4B) tested as alternatives | WordNet/Datamuse substitution + SBERT gate; optional local T5 |
| Semantic-preservation mechanism | **None explicit** — "relies on the LLM's inherent semantic reasoning," no verification step | Explicit SBERT threshold gate (flagged as single-signal, §RESEARCH.md §2.D) |
| Personalization | **None** — same impairment-class prompt for every speaker in that class; authors name this "passive rather than active" as a limitation themselves | Persistent, per-speaker declared profile; feedback-loop personalization named as future work (`ROADMAP.md` R9), not yet built either |
| Reproducible at student scale? | **No** for the primary configuration (frontier cloud LLMs, human evaluation panel, TORGO/UCLASS/AphasiaBank clinical datasets) — **partially yes** for the smaller local-model variant they also tested (Qwen3/Gemma3-4B), confirming §15's hardware-feasibility numbers apply here too |
| Evaluation idea worth adopting | **"Recovery rate"** — re-score the *output* with the same difficulty measure used to flag the input, and require it to have dropped. Directly analogous to (and already partially present in) our `rewrite/rewriter.py::metrics()`'s `difficulty_before`/`difficulty_after` — this is independent validation that our eval design is already pointed the right way, not a new idea to import. | |

**[FINDING]** SpeechAgent's own stated limitations mirror ours almost
exactly: "occasional hallucinations... can lead to subtle deviations from
the speaker's intention" (their word for what we'd call a semantic-gate
failure) and "passive rather than active... doesn't provide training or
progressive improvement over time" (exactly `ROADMAP.md` R9's gap). Neither
system has solved semantic verification or personalization robustly as of
this research pass — this is genuine evidence the field hasn't solved
these either, not just an artifact of our project's small scale.

---

## 3–5. Lexical substitution, paraphrase generation, sentence simplification

Covered in depth in `RESEARCH.md` §2.A–C — not repeated. Two additions from
this pass:

**[FINDING, refining RESEARCH.md §1.3's readability-vs-speakability
distinction with a citation]** Rubin (1993), discussed in a 2025
readability-to-listenability study, argues explicitly that "readability
formulas are not suitable" for oral-production contexts — "the extent to
which readability and listenability correlate is still not clear," and
spoken and written accessibility research share surface features
(vocabulary, sentence structure) but diverge on factors unique to
orality. **[INTERPRETATION]** This is now a citable, not just
inferred, basis for RESEARCH.md's existing conclusion: simplification's
target metric (reading grade level) should not be borrowed uncritically
for our objective function (§16).

**[FINDING]** GECToR ("Grammatical Error Correction: Tag, Not Rewrite,"
BEA-2020) reframes correction as sequence *tagging* (`KEEP` / `DELETE` /
`APPEND_x` / `REPLACE_x` per token) rather than full generation, and reports
being **up to 10× faster than seq2seq** at comparable quality (F₀.₅ 65.3–
66.5 on CoNLL-2014, 72.4–73.6 on BEA-2019). Directly relevant to §6/§12.

---

## 6. Minimal-edit rewriting — researched in depth, as requested

**[FINDING]** Three converging pieces of evidence that minimal-edit /
tag-based architectures (GECToR, FELIX, LaserTagger — all covered at a
survey level in RESEARCH.md §5.6, now with implementation-level detail):

1. **Feasible on small data.** FELIX "minimizes the amount of required
   training data with three techniques — fine-tuning pre-trained
   checkpoints, learning a small number of edit operations, and an
   insertion task that mimics [BERT's] masked language model task." It
   "outperforms LaserTagger and can be trained on as little as a few
   hundred training examples," and LaserTagger itself "exhibit[s] superior
   performance compared to seq2seq baselines when the amount of training
   data is limited" (demonstrated at 450–4,500 examples).
2. **Fast.** GECToR's tagging approach is ~10× faster than autoregressive
   seq2seq at inference — directly relevant to CPU-only deployment (§15).
3. **The exact mechanism**: GECToR predicts one of a small tag vocabulary
   per input token (`KEEP`, `DELETE`, `APPEND_x`, `REPLACE_x` — a curated
   set, not open vocabulary); FELIX splits the task into a *tagging*
   sub-task (which input tokens to keep, and in what order) and an
   *insertion* sub-task (filling in genuinely new tokens) so the model
   never has to regenerate content it's just copying.

**[LIMITATION — the actual, concrete feasibility blocker, not a hedge]**
All three need **paired training data**: (difficult-input, tagged-or-
rewritten-easier-output) examples, even if only a few hundred. **We do not
have this.** No parallel corpus of "sentence containing this speaker's
flagged material → an easier reformulation for that speaker" exists, and
one specific to *phoneme-avoidance* reformulation (as opposed to grammar
correction, which is what GECToR/FELIX were built and evaluated for)
appears not to exist in the literature at all — consistent with
`RESEARCH.md` §2.F's finding that phoneme-avoidance generation is a
genuinely under-explored niche.

**[INTERPRETATION — the reframing that actually matters for §12]** Our
*existing* `grammar.py`/`rewrite/` architecture is **already,
structurally, a tag-based minimal-edit system** — it just implements the
tagging decision with hand-coded POS-tag rules (`_SUBSTITUTABLE`,
`_STOP`) instead of a *learned* tagger, and reconstructs the sentence by
touching exactly the tagged positions, exactly like GECToR's `REPLACE_x`
tag does. This is a genuinely useful finding: **the shape our system
already has is the field's best-practice shape for this problem** — the
gap is in the *quality of the tagging decision* (rule-based vs. what a
trained model could do) and in *what happens when a position can't be
fixed by simple replacement* (§7 of PROBLEM_FORMULATION.md's audit / R10),
not in the overall architecture pattern. This directly supports the
recommendation in §20.

**[RECOMMENDATION]** Do not attempt to train a GECToR/FELIX-style learned
tagger now — no data exists to train one, and synthesizing training data
from our own rule-based system's outputs would just teach a model to
imitate the rules we already have, at real engineering cost, for no clear
quality gain. **Keep the rule-based tagging decision** (which words/spans
need attention — driven by the difficulty profile, refined per §2.1's
Brown's-factors gap) and focus improvement effort on **candidate quality**
(§4/§12) and **verification** (§9) instead.

---

## 7. Controlled/constrained generation — practical tooling, concretely

`RESEARCH.md` §2.E covers the theory (lexically constrained decoding,
NeuroLogic Decoding, LLM prompt-based unreliability). This pass adds the
concrete toolkit actually available to us:

**[FINDING]** Hugging Face `transformers`' `generate()` API supports
**negative constraints** natively via `bad_words_ids` /
`NoBadWordsLogitsProcessor` (already used by `rephrase.py` — confirmed,
not a new capability), and **positive/disjunctive constraints** via
`force_words_ids` — a plain list forces inclusion, a *nested* list forces
inclusion of *any one of* several token-id variants (`DisjunctiveConstraint`),
and `PhrasalConstraint` forces a specific phrase to appear, all
composable with beam search ("constrained beam search").

**[INTERPRETATION]** This means our existing `bad_words_ids` usage in
`rephrase.py` is already using the correct, standard mechanism (not a
homegrown workaround) — confirmed, not a new finding. What we're **not**
currently using: `force_words_ids`/`DisjunctiveConstraint` to require that
a generated candidate *keep* a protected entity or *use one of* several
acceptable synonym forms — a concrete, low-effort extension point for
§20's recommended architecture's generation-escalation stage.

---

## 8. Phoneme-aware generation — how granular can we realistically get?

**[FINDING, restated from §2.1 with the generation question specifically]**
Brown's four factors plus the loci literature give us a much richer
picture of "difficulty" than a flat onset-cluster-length term: position
within the word (onset dominant), position within the sentence
(unmodeled currently), stress (unmodeled, but derivable — CMU stress
digits already exist in our own phone data and are currently discarded),
content-vs-function word (partially modeled, in the profiling formula
only), consonant clusters specifically (modeled, though the literature
itself flags an unresolved confound with word length).

**[FINDING, direct answer to the task's explicit question]** "Does
`/r/` difficult mean every word containing `/r/` is equally difficult?"
— **No, and the existing loci research explains why not**: difficulty is
conditioned on *position* (onset vs. medial vs. coda), *stress*, and
*cluster membership*, not just phoneme identity. This is exactly what
motivated `PROBLEM_FORMULATION.md`'s word-specific `problem_phones`
feature (a word-scoped override of the global signal) — this research
pass provides the citable evidence that feature was solving a real,
documented phenomenon, not a hypothetical one.

**[LIMITATION, confirmed via direct search, not assumed]** No literature
was found describing **constrained text generation that specifically
avoids a target phoneme or phoneme sequence** as a named task — searches
for "phoneme-aware constrained text generation," "avoid specific sounds
speech production," and similar returned only TTS-phonemization
architecture papers (how to convert text *to* phonemes efficiently for
speech synthesis), not the inverse problem (choosing *which* text to avoid
producing certain phonemes). This confirms `RESEARCH.md`'s earlier finding
that this is a genuinely open research niche, now checked again with fresh,
differently-worded searches rather than assumed unchanged.

**[FINDING — a concrete, available upgrade for OOV pronunciation]**
`g2p_en` is a lightweight, CPU-only, "numpy-based... lightweight" neural
grapheme-to-phoneme library for English, used for words missing from CMU
dict — **more accurate than our current grapheme-rule fallback**
(`phonetic._grapheme_onset()`, a small hand-written digraph/silent-cluster
table) for out-of-vocabulary words. Not proposed for adoption now (§23) —
flagged as an available, low-risk future upgrade for `phonetic.py`'s known
OOV-onset-guessing limitation, not a research gap.

---

## 9. Semantic preservation — concrete, CPU-feasible tooling

`RESEARCH.md` §2.D/§5.3 already established the finding (SBERT misses
negation/antonym drift) and the direction (add NLI as a second signal).
This pass supplies the concrete, checked-feasible model options:

**[FINDING]** Small cross-encoder NLI models exist specifically for this:
`cross-encoder/nli-deberta-v3-xsmall` (DeBERTa-v3-xsmall backbone),
`cross-encoder/nli-deberta-v3-small` (91.65% SNLI-test accuracy, 87.55%
MNLI-mismatched), and a newer `EttinX-nli-s` (68M-parameter, ModernBERT-based,
87.98–88.67% Micro-F1 on MNLI/SNLI) explicitly positioned as "an excellent
candidate for lightweight CPU inference." All output
entailment/contradiction/neutral scores for a sentence pair — directly
usable as the second semantic-preservation gate `RESEARCH.md` R8 already
proposed.

**[INTERPRETATION]** This closes the "is this practical at our scale"
question `RESEARCH.md` left open for R8: yes — these models are
comparable in size/cost to the SBERT model already running in this
project (`all-MiniLM-L6-v2`, ~80MB), not a new category of infrastructure.

---

## 10. Grammaticality and naturalness

**[FINDING]** Perplexity under a language model (classically GPT-2) is the
standard practical fluency proxy — "if a sentence's perplexity score is
low, the sentence is more likely to be grammatically correct," and prior
work found perplexity "correlates with human fluency scores." **[FINDING,
important caveat]** It is not a sufficient check on its own: "a model with
low perplexity might still generate grammatically correct but semantically
nonsensical text" — GPT-2 "prioritizes grammatical structure over semantic
meaning," and perplexity "frequently fails to capture how models behave
when explicitly asked to judge grammaticality" in more careful probing
studies.

**[INTERPRETATION]** Perplexity is a cheap, real signal worth adding as
one input to ranking (§12), but — consistent with the semantic-gate
lesson in §9 — must not be the *only* naturalness check, for the same
reason SBERT alone isn't a sufficient meaning check: a single scalar proxy
reliably misses a specific failure mode (here, fluent-but-nonsensical
output) that a second, differently-shaped signal (our existing rule-based
grammar layer, or LanguageTool, both already in the repo) catches
differently.

---

## 11. Personalization

`RESEARCH.md` §2.G/§5.5 already covers Fluent's active-learning precedent
and names the accept/reject feedback-loop gap (`ROADMAP.md` R9). This pass
adds the current state of the broader field:

**[FINDING]** Current personalization research (2025–2026) is trending
toward **contextual-bandit** framings for online, few-example adaptation —
e.g. "PURPLE" casts profile optimization as a contextual bandit problem;
"UserAlign" achieves "fast personalized alignment with a few user
preference queries" via a logistic-bandit framework. **[INTERPRETATION]**
This is a more principled framing than a naive "just retrain on
accept/reject" loop for a small-data, single-speaker setting like ours —
a contextual bandit over *which onset/word gets flagged risky* (arm =
whether to flag; reward = accepted vs. rejected suggestion) is a
lightweight, well-understood, CPU-trivial algorithm family (no neural
network required at our data scale), not a research risk.

**[LIMITATION, honestly stated]** Essentially all of this literature
targets either large-scale multi-user recommendation systems or LLM
alignment at a scale far beyond a single-speaker, single-laptop research
project. The *algorithms* (contextual bandits specifically) are lightweight
and adaptable; the *systems* they were built for are not comparable to
ours. **[RECOMMENDATION]** If/when R9 is implemented, frame it as a simple
contextual bandit over the existing per-onset risk scores already stored
in `profiling/profile.py` (arms = onset keys, reward = accept/reject),
not as adopting any of the cited papers' full systems.

---

## 12. Candidate-generation + ranking architectures — the requested comparison

| | **A. Direct generation** | **B. Candidate-gen + rank** | **C. Minimal-edit tagging** | **D. Hybrid (tag → candidate-rank → generate-escalation → symbolic verify)** |
|---|---|---|---|---|
| Pipeline | text+profile → one model → output | generate many candidates (multi-source) → filter → semantic verify → difficulty score → fluency score → rank | tag keep/delete/replace per token → fill only tagged spans → reassemble | difficulty-driven tagging (existing) → try substitution-rank first → escalate to constrained generation only where substitution fails → final symbolic phoneme+semantic veto on the actual output |
| Restructuring ability | Best (§7 of RESEARCH.md) | Poor alone — needs T5/LLM candidates mixed in | None beyond learned edit ops (and we can't train them, §6) | Present, but only invoked when needed (§6/§20) |
| Constraint reliability | Unreliable via prompting alone (RESEARCH.md §2.E finding) | High — symbolic filters, not prompted | High for what it was trained to do; N/A here (no training data) | High — symbolic veto is always-final regardless of path |
| Explainability | Low (single opaque model call) | High (each candidate scored, inspectable) | Medium (tag sequence is inspectable, but we can't train the tagger) | High for the common path, medium for the escalation path |
| Buildable without new training data? | Yes, if using a pretrained model as-is | Yes — already mostly built | **No** (§6) | Yes — reuses B for the common case, T5 (already in repo) for escalation |
| Matches existing implementation | No — would replace it | Yes — this is what `grammar.py`/`rewrite/` already approximate | No | Yes — extends what exists rather than replacing it |
| Hardware cost | Depends entirely on model chosen (§15) | Low — WordNet/Datamuse/SBERT already proven to run here | Would require training infra we don't have data to use anyway | Low for common case; moderate (T5, already proven) for escalation |

**[RECOMMENDATION, previewing §20]** D. Detailed in §19–20.

---

## 13–14. Existing systems closest to ours, and model comparison

Fluent (2021) is covered in depth in `RESEARCH.md` §2.F; SpeechAgent (2026)
is covered in depth in §2.2 above. `RESEARCH.md` §3's model table (T5/BART/
BERT-MLM/local-LLM/API-LLM, compared on controllability, semantic
preservation, fluency, restructuring, forbidden-word obedience,
personalization, cost, local feasibility, reproducibility, explainability)
is not repeated — it holds. New this pass, from §15's research:

| Model class | New finding this pass |
|---|---|
| Small NLI cross-encoders (`nli-deberta-v3-xsmall/small`, `EttinX-nli-s`) | Confirmed CPU-feasible, ~similar footprint to the SBERT model already in the repo (§9) |
| Small local LLMs (Qwen2.5/3, Llama-3.2, Phi-3/4-mini, Gemma-4, 1–4B, Q4 GGUF via llama.cpp) | Confirmed runnable CPU-only on a modern laptop at ~12 tok/s for a 7B model (5–30× slower than GPU) — usable for **occasional, non-interactive** generation (our escalation path, §20), not for a tight interactive loop (§15) |
| GECToR/FELIX/LaserTagger | Confirmed small-data-feasible *architecturally*, but blocked by the training-data gap specific to our task (§6) — not by hardware |

---

## 15. Hardware and deployment feasibility

| Component | CPU-only laptop feasible? | GPU (friend's Mac) needed? | Notes |
|---|---|---|---|
| WordNet/Datamuse/wordfreq (existing) | Yes, already proven | No | Zero-cost, already running |
| SBERT `all-MiniLM-L6-v2` (existing) | Yes, already proven | No | ~80MB, already running |
| Small NLI cross-encoder (new, §9) | Yes | No | Comparable size/cost to SBERT |
| T5-small/base fluency rephrase (existing, `rephrase.py`) | Yes, already proven | No | Already validated in this repo's own history (`changes.md` v5.1.0/v6.0.1) |
| Small local LLM (1–4B, Q4 quantized) for the escalation path (§20) | Yes, but slow (~12 tok/s at 7B; faster at smaller sizes) — **acceptable for an occasional fallback call, not a per-keystroke interaction** | Preferred, not required — a GPU would remove the latency concern entirely for iterative experimentation | Only invoked when substitution-ranking fails to find a valid candidate — expected to be a minority of cases, so occasional multi-second latency is tolerable |
| Fine-tuning any model (GECToR/FELIX-style tagger, or fine-tuning T5 further) | **Not attempted** — no training data exists for this task (§6) | Would help if we ever did have data | Named explicitly as not-yet-actionable, not silently dropped |
| Frontier API LLMs (GPT-4.1/Gemini-class, as SpeechAgent's primary configuration used) | N/A — requires network + per-call cost | N/A | **[RECOMMENDATION]** Not adopted as primary — breaks this project's offline/reproducible/free identity (already a stated project value, `README.md`); could be an optional, clearly-labeled experimental comparison point only, never the default path |

**[INTERPRETATION, direct answer to the task's "scientifically ideal vs.
practically implementable" question]** The scientifically strongest single
lever available (a frontier LLM with strong restructuring ability) is
explicitly not the practically right choice here — not because it's
"too advanced," but because it breaks reproducibility (non-deterministic
across API versions, a real cost for a project that wants to report stable
results — `RESEARCH.md` §3 already flagged this) and this project's stated
offline-first identity. The *next* strongest lever (a small local LLM,
1–4B, quantized) is genuinely usable, just not as the primary/always-on
path — exactly matching §20's recommended architecture's escalation-only
role for generation.

---

## 16. Current-system assessment

| Existing component | Evidence supporting it | Problems | Keep? | Replace? | Research needed? |
|---|---|---|---|---|---|
| `grammar.py::sanitize_input()` (rule-based grammar correction) | Deterministic, offline, no training data needed; RESEARCH.md §5.1 found no reason to touch it | POS-tagger misfires on short/broken input (known, documented) | **Keep** | No | No |
| `engine.py` (WordNet+Datamuse candidate retrieval) | POS-gated retrieval already fixes a real cross-POS contamination bug (RESEARCH.md §5.2) | Closed-vocabulary ceiling — can't propose a word WordNet doesn't list as related (RESEARCH.md §2.B/§5.2) | **Keep as one source**, not the only one | **Augment** with MLM-native candidate generation (§4/RESEARCH.md §2.B) | Prototype MLM candidate generation, measure vs. WordNet-only |
| `semantic.py` (SBERT single-signal gate) | SBERT is a legitimate, standard STS tool | Documented negation/antonym blind spot (RESEARCH.md §2.D, confirmed not hypothetical) | **Keep**, not sufficient alone | **Add** small NLI cross-encoder as a second, orthogonal signal (§9, now with specific model names) | Measure whether NLI changes real accept/reject decisions on our candidate distribution |
| `phonetic.py` (onset-cluster-length difficulty formula) | Onset-dominance is real and well-evidenced (§2.1, Brown's factors) | Missing sentence-position and stress factors entirely, though the data (CMU stress digits) is already being discarded, not unavailable (§2.1) | **Keep the onset-veto mechanism**; **revise** the difficulty *formula* | Add position/stress terms; still blocked on real speaker data for weight *fitting* (`ROADMAP.md` R2, unchanged) | Yes — R2, plus a cheap experiment: does adding position/stress change candidate rankings even with unfitted weights? |
| `profiling/profile.py` (learned EWMA onset-risk model) | Sound personalization architecture (RESEARCH.md §5.5); interpretable | Still separate from the new declared profile (`ROADMAP.md` R12, unresolved) | **Keep**, reconcile | Not replace — extend | R12 is a prerequisite, not optional |
| `rewrite/` (soft λ/μ scoring, duplicated logic vs. `grammar.py`) | Continuous scoring is more expressive than a hard onset veto | Duplicates protected-word/POS-filter/inflection logic already in `grammar.py`/`semantic.py` (RESEARCH.md §6) | **Consolidate**, don't keep as a second parallel path | **Replace** the duplication — fold into one substitution-and-rank stage (§20) | The A-vs-B ablation this repo has named since Stage 3 (`ROADMAP.md` R6) is now more clearly answerable: there's no complementary-failure-modes argument for keeping both (RESEARCH.md §6), so consolidation is the evidence-supported direction, pending the ablation actually being run |
| `rephrase.py` (optional T5 constrained paraphrase) | Already uses the correct constraint mechanism (`bad_words_ids`, confirmed standard practice, §7); already proven to run locally | Currently an independent, always-optional toggle rather than the substitution path's fallback | **Keep**, **repurpose its role** | Not replace the model — change *when* it's invoked (§20) | No new research — this is an integration decision, already recommended in RESEARCH.md §8/R10 |
| Two parallel pipelines generally | — | Duplication confirmed, not a complementary design (RESEARCH.md §6) | — | **Consolidate into one** | `ROADMAP.md` R6/R12 |

---

## 17. Failure modes — constructed and walked through

For each, "current system" = today's `grammar.py`/`rewrite/` behavior;
"Architecture D" = §19–20's recommendation.

| Case | Current system | Architecture D |
|---|---|---|
| **Multiple difficult words** ("I thoroughly reviewed three reports") | Each word substituted independently, no interaction modeling (named limitation, `RESEARCH.md` §7) | Same limitation persists — interaction modeling is explicitly named as unaddressed future work (§18), not solved by D |
| **Difficult phoneme in many words** ("The researcher reported the results" — /r/ everywhere) | Would substitute every /r/-onset content word independently, likely producing a heavily-altered, "obviously edited" sentence | The Levenshtein-based naturalness metric (§10/RESEARCH.md R11, now literature-grounded) would flag this as high-edit-count; a future ranking step could prefer restructuring ("Findings from the study were reported") over touching 3+ words individually — **named as a good test case for the escalation path, not solved by this research pass alone** |
| **Negation** ("I did not review the report") | SBERT alone would likely accept a candidate that drops or flips "not" (RESEARCH.md §2.D's exact documented failure mode) | NLI second signal (§9) is specifically the fix for this case — directly testable once added |
| **Ambiguous word** ("I will present the object") | WordNet lookup is POS-gated (`engine.py` v3) but not sense-gated — could pull `present`(verb, give) synonyms contaminated by `present`(noun, gift) senses if POS tagging alone doesn't disambiguate | MLM-native candidate generation (context-conditioned, §4) handles sense ambiguity better than static WordNet lookup by construction (RESEARCH.md §2.B) — a real, testable improvement | 
| **Context-dependent substitution** ("He runs the company" vs. "He runs every morning") | POS tag alone (`VBZ` both times) doesn't disambiguate "runs" (manages) from "runs" (jogs) — same risk as the ambiguous-word case | Same MLM-context fix applies |
| **Proper nouns / technical terms** | Protected via `_STOP`/POS-tag checks (`NNP`) in `grammar.py` and independently in `rewrite/candidates.py`'s `detect_protected_words()` — **already handled, confirmed**, though implemented twice (duplication, §16) | Consolidate the protection logic into one shared mechanism as part of the pipeline merge (§16), not a new capability |
| **Very long transcript / multi-sentence context** | `app.py` already splits into sentences and processes each independently (existing, unchanged) — cross-sentence context (e.g. a pronoun referring back two sentences) is **not** modeled | **Named limitation, not solved by this pass** — full discourse-level context tracking is out of scope for the recommended architecture too (§22/§23) |
| **A case where restructuring beats substitution** | Cannot restructure at all today — reports "no valid synonym," leaves the word untouched (`PROBLEM_FORMULATION.md`'s audit, `RESEARCH.md` §7) | This is exactly what the escalation path (§20) is *for* — the one failure mode this research pass's recommended architecture directly, structurally addresses |

**[INTERPRETATION]** Two failure modes (multi-difficulty interaction,
cross-sentence context) are **not** solved by the recommended architecture
either — stated honestly rather than implied as fixed. Three (negation,
ambiguity/context-dependence, restructuring-needed) are directly,
structurally addressed by specific, already-researched components
(NLI, MLM candidates, escalation path).

---

## 18. Open research questions

1. Does adding an NLI second signal change real accept/reject outcomes on
   our actual candidate distribution, or is the negation/antonym case rare
   enough in practice (given WordNet/Datamuse candidates skew toward true
   synonyms) that it rarely fires? (§9, `ROADMAP.md` R8)
2. Does adding sentence-position and stress terms to the difficulty
   formula change candidate rankings in practice, even before the weights
   are ever fitted to real data? (§2.1, extends `ROADMAP.md` R2)
3. Is the A-vs-B pipeline ablation's answer actually "consolidate," or
   does running it surface a real behavioral difference the
   complementary-failure-modes argument missed? (`ROADMAP.md` R6/R12 — this
   pass argues for consolidation but the ablation itself still hasn't run)
4. How often, in practice, does the escalation path (generation) actually
   get invoked versus substitution succeeding on its own? This determines
   whether the local-LLM latency concern (§15) is a real UX problem or a
   rare-path non-issue — unknown without building and measuring it.
5. Is a contextual-bandit framing (§11) actually simpler to build and more
   effective at our data scale than a naive accept/reject counter, or is
   the added conceptual complexity not worth it for a single-speaker
   system? Untested.

---

## 19. Candidate architectures — ranked

### Architecture D — Hybrid: existing-tagging → candidate-rank → generation-escalation → symbolic verify *(recommended, detailed in §20)*
Conceptual pipeline in §12's table. Expected quality: high for
single-word/localized difficulty (today's strong case), improving for
restructuring-needed cases via escalation. Cost: low for the common path
(reuses proven, cheap components), moderate for escalation (T5, already
proven; optionally a small local LLM later). Complexity: moderate —
mostly consolidation and two additions (NLI, escalation trigger), not a
rewrite. Explainability: high for the common path. Personalization: reuses
existing profile, extensible to R9's feedback loop. Semantic safety:
two independent signals (SBERT+NLI) plus a final symbolic phoneme veto.
Phoneme-awareness: onset-veto today, position/stress-extensible (§2.1).
Evaluation requirements: needs the naturalness-of-intervention metric
(§10) and the A-vs-B ablation (§18) to fully validate. Suitability: high —
buildable incrementally on what exists, no training data required.

### Architecture B — Candidate-gen + rank, without an escalation path
Same as D minus the generation-escalation stage. Simpler to build (no new
model integration decision), but inherits the "cannot restructure" gap
unresolved (§17's clearest failure case). Lower implementation risk, lower
capability ceiling.

### Architecture A — Direct generation (T5 or small local LLM, single model, prompted/constrained)
Best raw restructuring ability, worst constraint reliability (RESEARCH.md
§2.E's LLM-prompting-unreliable finding applies directly) and worst
explainability. Would require building semantic/phoneme verification
*around* it regardless — at which point it has converged most of the way
toward D anyway, without D's cheaper common-case path. Not recommended as
primary, viable as what D's escalation stage effectively *is* in miniature.

### Architecture C — Learned minimal-edit tagger (GECToR/FELIX-style)
Best inference speed and, in principle, best "minimal necessary edit"
behavior — but **not buildable now**: no training data exists for this
specific task (§6), and synthesizing it from our own rule-based outputs
would just teach a model to imitate rules we already have. **Ranked last
not because the architecture is weak, but because it's the one candidate
this research pass could not clear the feasibility bar for.** Worth
revisiting if/when real speaker-reformulation-pair data ever exists
(same blocking condition as `ROADMAP.md` R2).

---

## 20. Recommended architecture

**[RECOMMENDATION]** Architecture D — restated precisely:

```
1. TAGGING (existing, refined):
   Difficulty profile (declared: sounds/words/phrases/patterns;
   learned: profiling/profile.py, reconciled per R12) + a difficulty
   formula extended with sentence-position and stress terms (§2.1)
   flags which spans need attention. This is what grammar.py/rewrite/
   already do — kept, not replaced (§6's reframing: our existing shape
   already matches the field's best-practice pattern).

2. SUBSTITUTION-AND-RANK (consolidates the current two pipelines, R6/R12):
   One candidate-generation step combining WordNet/Datamuse (existing)
   with MLM-native, context-aware candidates (new, §4/RESEARCH.md §2.B) →
   two independent semantic gates, SBERT (existing) + small NLI
   cross-encoder (new, §9) → symbolic phoneme veto (existing, unchanged —
   §7's finding that this is already the safest point on the constrained-
   generation spectrum stands) → single continuous difficulty/frequency/
   fluency-perplexity score (§10) → rank.

3. ESCALATION (new — the one structural capability gap this pass
   confirms is real and addressable, RESEARCH.md R10):
   Only when step 2 produces no candidate passing all gates for a
   flagged span: invoke constrained generation (rephrase.py's existing
   T5 layer, repositioned from "independent optional toggle" to
   "fallback for substitution failure," using force_words_ids/
   DisjunctiveConstraint per §7 to keep protected entities). A small
   local LLM (§15) is a possible later upgrade to this stage
   specifically, not a day-one requirement.

4. FINAL VERIFICATION (new, always-applied, symbolic):
   Whatever path produced the candidate sentence, re-check the ACTUAL
   FINAL OUTPUT (not just each candidate in isolation) against the
   phoneme veto and both semantic gates — SpeechAgent's "recovery rate"
   idea (§2.2), independently arrived at, applied here as a last-mile
   safety net rather than only a per-candidate filter.

5. METRICS (extends what exists, RESEARCH.md §4/§10):
   Meaning preservation, difficulty reduction, and naturalness-of-
   intervention (Levenshtein-based, now literature-grounded, §10)
   reported separately, never blended, exactly as Practice.md §10 and
   this repo's own eval/metrics.py already do.
```

## 21. Why this architecture, specifically

Every major piece is independently justified by a *different* research
finding in this document, not by one overarching preference:
- The tagging stage survives because §6's reframing shows it already
  matches the field's minimal-edit best practice.
- Consolidating the two rewrite paths is justified by §12/§16's finding
  that they don't have complementary failure modes (the literature's own
  test for when multiple components are worth keeping separately).
- The NLI addition is justified by a specific, named, otherwise-uncaught
  failure mode (§9/§17's negation case).
- The escalation stage is justified by the one failure mode (§17's
  restructuring case) that is structurally unsolvable without it, and
  it's buildable today because `rephrase.py` and its constraint mechanism
  already exist and are already proven to run locally.
- The final verification stage is independently validated by a different
  2026 system (SpeechAgent) converging on the same idea from a different
  direction.
- Nothing here requires model training, matching the hard feasibility
  constraint (§6/§15) that ruled out the alternative (Architecture C).

## 22. What should be implemented first

In priority order, each tied to a specific finding:
1. **The A-vs-B ablation** (`ROADMAP.md` R6) — needed to know whether
   consolidation (step 2 above) is actually safe, not just theoretically
   justified.
2. **The naturalness-of-intervention metric** (§10/R11) — needed *before*
   any of the other changes, so their effects can actually be measured
   against a shared baseline rather than judged by feel.
3. **The NLI second signal** (§9/R8) — small, isolated, directly testable
   against the ablation's baseline.
4. **Difficulty formula position/stress terms** (§2.1) — cheap to add,
   directly testable for ranking changes even pre-fitting.

## 23. What should explicitly NOT be implemented yet

- **Any model fine-tuning or training** (§6/§15) — no data exists; this
  is not a "not yet," it's a hard blocker until `ROADMAP.md` R2's data
  dependency (real speaker disfluency data from the Audio Module) is met.
- **The generation-escalation stage itself** (§20 step 3) — sequenced
  *after* items 1–4 above, because escalating to generation before the
  substitution path's own quality is measured would conflate two
  different sources of improvement in any before/after comparison.
- **A local LLM integration** — §15 confirms it's feasible, but nothing
  in this research pass found a reason it's needed *before* the escalation
  stage exists and its actual invocation rate (§18 Q4) is measured; adding
  it earlier would be infrastructure ahead of a demonstrated need.
- **Any API-based frontier LLM as a default path** (§15) — breaks
  reproducibility and offline operation, this project's own stated values;
  not proposed even as a future default, only (at most) as an optional,
  clearly-labeled comparison point.
- **The accept/reject personalization loop** (§11/R9) — real feature,
  correctly sequenced after the core substitution/escalation pipeline
  exists to have something to accept or reject in the first place.

---

## Bibliography (sources newly surfaced this pass, 2026-08-16)

**Stuttering loci / Brown's factors**
- Brown, S. & Johnson, W. (1945, as reconfirmed in modern secondary
  sources) — the four-factor framework (word-initial phoneme, grammatical
  function, sentence position, word length).
- "Linguistic stress, within-word position, and grammatical class in
  relation to early childhood stuttering." https://pubmed.ncbi.nlm.nih.gov/15178127/
- "A STUDY OF THE LOCI OF STUTTERING IN SPONTANEOUS SPEECH." https://dokumen.pub/a-study-of-the-loci-of-stuttering-in-spontaneous-speech.html
- "Stuttering, Stressed Syllables, and Word Onsets." https://pubs.asha.org/doi/abs/10.1044/jslhr.4104.802
- "Stuttering and syllable stress." https://www.sciencedirect.com/science/article/abs/pii/0094730X84900238
- "Gestural overlap in consonant clusters: effects on the fluent speech of
  stuttering and non-stuttering subjects." https://www.sciencedirect.com/science/article/abs/pii/S0094730X03000627
- "The Effect of Syllable Structure on the Frequency of Disfluencies in
  Adults With Stuttering." https://brieflands.com/journals/mejrh/articles/21497
- "A feature analysis of stuttered phonemes." https://www.sciencedirect.com/science/article/abs/pii/0094730X83900244

**Closest systems**
- "SpeechAgent: An End-to-End Mobile Infrastructure for Speech Impairment
  Assistance." https://arxiv.org/abs/2510.20113 / https://arxiv.org/html/2510.20113v1

**Minimal-edit / tagging architectures**
- "GECToR -- Grammatical Error Correction: Tag, Not Rewrite." https://arxiv.org/abs/2005.12592
- GECToR official repo. https://github.com/grammarly/gector
- "FELIX: Flexible Text Editing Through Tagging and Insertion." https://aclanthology.org/2020.findings-emnlp.111.pdf / https://research.google/blog/introducing-felix-flexible-text-editing-through-tagging-and-insertion/

**Constrained generation tooling**
- Hugging Face `transformers` generation docs (bad_words_ids,
  force_words_ids, DisjunctiveConstraint, PhrasalConstraint). https://huggingface.co/docs/transformers/v4.38.0/en/main_classes/text_generation
- "New Hugging Face Feature: Constrained Beam Search." https://towardsdatascience.com/new-hugging-face-feature-constrained-beam-search-with-transformers-7ebcfc2d70e9/

**Semantic preservation (NLI models)**
- `cross-encoder/nli-deberta-v3-xsmall`. https://huggingface.co/cross-encoder/nli-deberta-v3-xsmall
- `cross-encoder/nli-deberta-v3-small`. https://huggingface.co/cross-encoder/nli-deberta-v3-small
- `dleemiller/EttinX-nli-s`. https://huggingface.co/dleemiller/EttinX-nli-s

**Grammaticality/fluency**
- "Comparing BERT and GPT-2 as Language Models to Score the Grammatical
  Correctness of a Sentence." https://www.scribendi.ai/comparing-bert-and-gpt-2-as-language-models-to-score-the-grammatical-correctness-of-a-sentence/
- "Explain-then-Process: Using Grammar Prompting to Enhance Grammatical
  Acceptability Judgments." https://arxiv.org/html/2506.02302

**Personalization**
- "Optimizing User Profiles via Contextual Bandits for Retrieval-Augmented
  LLM Personalization" (PURPLE). https://arxiv.org/html/2601.12078v2
- "Inference-Time Personalized Alignment with a Few User Preference
  Queries" (UserAlign). https://arxiv.org/html/2511.02966

**Readability vs. listenability**
- "Easy Audios: from Readability to Listenability." https://ddd.uab.cat/pub/artpub/2025/3d5f92c3f077/Macuca_JAT_8.1.pdf

**Hardware feasibility**
- "Best CPU-only local LLMs in 2026." https://www.popularai.org/p/best-cpu-only-local-llm-2026
- "CPU-Only LLM 2026: Phi-4 Mini Runs 12 tok/s, No GPU." https://www.promptquorum.com/local-llms/best-cpu-only-llm

**G2P tooling**
- `g2p_en` — lightweight English grapheme-to-phoneme. https://github.com/Kyubyong/g2p

---
---

# Stage 5B — Critical Architecture Review & Implementation Blueprint (2026-08-16)

This is the last planning checkpoint before implementation, not a new research
cycle. Per the task's own instruction, new claims below are verified directly
against this repo's actual code/libraries (a handful of concrete checks), not
sourced from fresh literature search. Where §1–23 above already established a
finding, it's cited, not re-derived.

## 24. Critique — does the Stage 5 architecture survive contact?

### 24.A SBERT + NLI: complementary, but "NLI on every candidate" is unjustified complexity

**[FINDING, re-examined]** SBERT's negation/antonym blind spot (§9) and NLI's
purpose-built sensitivity to contradiction are genuinely complementary in
*what they catch* — this holds. What doesn't survive critique is running a
full bidirectional NLI pass (2 forward passes per candidate — entailment is
directional, so meaning-preservation checking needs both directions) on
*every* candidate, for two reasons: (1) NLI models have their own well-known
failure mode — **hypothesis-only/lexical-overlap artifacts** in the
SNLI/MultiNLI training data mean a cross-encoder can sometimes guess the
label from surface patterns alone, so it is not a strictly-better oracle,
it's a *differently-fallible* signal; (2) it's mostly redundant work for our
actual candidate source. **[FINDING, verified directly against this repo's
own WordNet integration, not assumed]**: `nltk.wordnet`'s `Lemma.antonyms()`
is a direct, zero-cost, zero-model lookup — confirmed by running it against
this repo's live `engine.py` (`happy` → antonym `unhappy`; the current
`get_synonyms('happy')` candidate list does not currently contain it, a
healthy baseline, though not a guarantee for every word via longer
hypernym-chain paths).

**[RECOMMENDATION, revised from Stage 5's flat "add NLI alongside SBERT"]**
A **tiered** semantic-verification stage, not a flat second gate:
1. **WordNet antonym rejection** (free) — for any WordNet/Datamuse-sourced
   candidate, reject immediately if it's a direct antonym of the original
   lemma. Catches the specific, named risk at zero cost.
2. **SBERT threshold** (existing, unchanged) — primary gate for all
   candidates, as today.
3. **NLI bidirectional check** (new) — applied only to (a) candidates from
   sources that lack step 1's safety net (MLM/generation-sourced
   candidates, when/if those exist — §24.B), and (b) WordNet/Datamuse
   candidates whose SBERT score is *borderline* (near the threshold), not
   every candidate. This is a leaner design than "NLI on everything" while
   still closing the documented gap for the cases most likely to need it.
4. **Final-output re-verification** (unchanged from Stage 5's proposal) —
   re-run steps 1–3 on the actual assembled output sentence, not just each
   candidate in isolation, per SpeechAgent's independently-arrived-at
   "recovery rate" idea (§2.2).

### 24.B Candidate generation: MLM is real but unmeasured — defer, don't drop

**[INTERPRETATION, revised from Stage 5's flat recommendation]** The
literature case for MLM-native candidates (§4, RESEARCH.md §2.B) is real —
WordNet's closed-vocabulary ceiling is a documented limitation, not a
hypothetical one. But **we have never measured how often that ceiling is
actually hit** on realistic difficulty-flagged input — no ablation exists
showing "WordNet/Datamuse returns zero usable candidates X% of the time."
Adding a new model (a masked-LM, ~260MB+ even for a small encoder) to solve
an unmeasured problem, before the cheaper fix (§24.A's tiered verification,
consolidating the two existing pipelines) has even shipped, is exactly the
"modern for its own sake" trap the task warned against. **[RECOMMENDATION]**
Defer MLM candidate generation to the *Strong* tier (§27), gated on first
instrumenting and measuring the current `"no synonyms found"` /
`"no valid synonym"` skip-rate on the failure-mode corpus (§29). If that
rate is low, MLM candidates are a nice-to-have, not a blocker; if it's high,
that measurement — not the literature alone — is the actual justification
for building it next.

### 24.C Phoneme granularity (position/stress/clusters): log now, score later — a correction to Stage 5's own §22

**[LIMITATION, self-critique]** Stage 5's own §22 recommended adding
position/stress terms to the difficulty formula as a "cheap, testable"
near-term item. Re-examined against this project's own standing rule
(Practice.md §6, already cited repeatedly in this repo's history —
`DECISION_LOG.md` 2026-06-08-B is the on-record cautionary tale of a
threshold changed by "empirically"-flavored argument rather than measured
data): **adding new *terms* to an already-flagged-as-unfitted formula, with
no data to fit them against and no principled coefficient the literature
actually supplies (it tells us position/stress matter and roughly which
direction, not a number), would compound the exact problem `VALIDATION.md`
already names, not fix it.** This is a real correction, not a restatement —
Stage 5's own recommendation undersold this risk.

**[RECOMMENDATION, revised]** Do **not** add position/stress as *scored*
formula terms in the MVP. Instead: **compute and log them as unscored
metadata** alongside every difficulty decision (sentence-position index,
whether the flagged phoneme is in a stressed syllable per CMU's stress
digit — already present in our own phone data and currently discarded, not
unavailable). This costs almost nothing, changes no existing score or
threshold (satisfying Practice.md §6 without a special exception), and
means that *when* real speaker data eventually arrives (`ROADMAP.md` R2),
the features needed to fit a properly-weighted formula are already being
collected — not something to retrofit later. Consonant-cluster length is
already the dominant term in `phonetic.word_difficulty()`'s existing onset
score; no change needed there.

### 24.D Substitution vs. restructuring: a concrete, missing trigger condition

**[FINDING, from re-reading `grammar.py`'s actual substitution loop]**
Sequential per-word substitution already checks *cumulative* semantic drift
correctly today — `SentenceRewriter.rewrite()` rebuilds candidate sentences
from the *current* (already-partially-substituted) token list, but always
scores SBERT similarity against the *true original* sentence, so a second
substitution compounding a first one's drift is still caught. **What is
not checked, by this mechanism or Stage 5's proposal, is cumulative
*naturalness*** — three individually-valid, semantically-safe substitutions
can still read as "obviously over-edited" as a whole, and nothing currently
measures that.

**[RECOMMENDATION, new, not in Stage 5's original proposal]** Add an
explicit **count-based escalation trigger**, distinct from the existing
per-span "no candidate found" trigger: if a sentence has **more than a
small, configurable number (e.g. 2) of independently flagged content
words**, prefer routing the *whole sentence* to the T5 restructuring stage
over attempting N independent substitutions — on the reasoning (§17's
"difficult phoneme in many words" failure case) that many independent local
optima are more likely to compound into an unnatural whole than one
sentence-level rewrite is. This directly answers "should sentence-level
context influence the process from the beginning": **not always** (single-
or two-word cases are handled well by substitution today), **but yes, past
a measurable threshold** — a concrete, testable rule rather than an
all-or-nothing architecture choice.

### 24.E T5 fallback: a real constraint-mechanism limit, found by checking the code

**[FINDING, verified directly against `rephrase.py`'s actual
`_bad_words_ids()`, not assumed]** `bad_words_ids` blocks specific,
*named* word strings (encoded token-by-token via the tokenizer) — it has
**no mechanism for blocking a phoneme class**. This matters concretely:
blocking every English word containing a common phoneme like /r/ via
`bad_words_ids` is not practically achievable (the blocklist would be
enormous and would cripple the model's ability to produce any normal
sentence) — confirmed by reading the actual implementation, not inferred.

**[INTERPRETATION — this settles several of the task's explicit questions
at once]** Because phoneme-level constraints cannot be enforced *before*
generation with our available tooling, the escalation stage is
**architecturally required to be generate-then-verify, not
constrain-then-generate**, for the phoneme dimension specifically (word-
level `bad_words_ids` remains useful and already works for the small,
explicitly-named `blocked_words` list — that part *can* be constrained
before generation, and should stay that way). T5's role, precisely: propose
several fluent, meaning-preserving full-sentence paraphrases (via the
already-proven `generate_candidates(k=5, blocked_words=...)`), **completely
unaware of phonemes**, then re-run the *exact same* symbolic phoneme veto
and §24.A's tiered semantic checks already used for word substitution — no
new verification machinery, reuse what exists. **[RECOMMENDATION]** Keep
`Vamsi/T5_Paraphrase_Paws` — RESEARCH.md §3 already found no clear winner
among small alternatives (FLAN-T5, BART) to justify a switch, and it's
already proven to load and run locally in this repo's own history — the
finding here is about *when/how* it's invoked and verified, not which
model.

### 24.F Multiple interacting difficulties — resolved case by case, not by a new subsystem

- **Multiple difficult words**: handled by existing cumulative-SBERT-check
  (§24.D) plus the new count-threshold trigger (§24.D) for the
  naturalness half of the problem.
- **Multiple difficult sounds**: already correctly generalizes — the
  phoneme veto checks a candidate against *all* patterns in the profile,
  not just one; no change needed.
- **Substitutions that create a new difficulty**: **[FINDING, confirmed by
  re-reading `grammar.py`'s Gate B]** already handled correctly today —
  `s["phoneme_ok"]` is computed by checking the *candidate's own* onset
  against every pattern, so a replacement can never introduce a fresh
  flagged sound. Verified, not a gap.
- **Substitutions that interfere with each other** (e.g. two independent
  swaps together create awkward repetition): genuinely unhandled, and
  **[LIMITATION, deliberately deferred, not silently dropped]** — the
  planned naturalness/edit-amount metric (§28) would catch *gross* cases
  (a heavily-altered sentence gets flagged) without specifically diagnosing
  *why*; full pairwise-interaction modeling is out of scope for the MVP or
  Strong tier, named explicitly rather than assumed solved.
- **Overlapping difficult phrases containing difficult words**: moot for
  the MVP (phrase-matching itself isn't implemented yet, `ROADMAP.md` R13)
  — **[RECOMMENDATION, for whenever R13 is tackled]** a matched phrase
  should be treated as one unit and suppress independent substitution of
  words inside it, to avoid double-processing the same span two ways.
- **Degenerate/over-restrictive profiles** (e.g. nearly every common onset
  flagged, making most of a sentence "risky"): **[LIMITATION, new,
  identified by this review, not in Stage 5]** neither the original
  architecture nor this revision has a sanity cap for this. **[RECOMMENDATION]**
  Add one defensively: if flagged content words exceed a high fraction of a
  sentence (e.g. >60%), skip exhaustive per-word attempts and go straight
  to the "could not safely reformulate — profile too restrictive for this
  sentence" outcome (§26) rather than producing a heavily mangled result.

---

## 25. The exact system contract

**[RECOMMENDATION]** Reuse the existing `DifficultyProfile` shape directly
as input — inventing a second, flattened representation
(`{global_sounds, difficult_words, ...}`, the task's own example) would
recreate exactly the kind of parallel-representation drift this project's
own history has already been burned by twice (the `phoneme_profile` mirror,
`DECISION_LOG.md` 2026-08-15-C/2026-08-16-A). The engine receives the
profile object (or its `to_dict()` shape) as-is.

```
INPUT
─────
{
  text: str,                     # one sentence or a paragraph (split internally,
                                  # reusing the existing _split_sentences)
  profile: DifficultyProfile,    # the actual object — sounds/words/phrases/
                                  # problem_phones, unchanged shape
  settings: {                    # optional per-call overrides; mirrors the
    sbert_threshold?: float,     # existing rewrite/rewriter.py precedent
    nli_threshold?: float,       # (RewriteSettings dataclass) rather than
    naturalness_budget?: float,  # inventing a new config pattern
    escalation_word_count?: int, # the new count-threshold trigger (§24.D)
  }
}

OUTPUT
──────
{
  original_text: str,
  reformulated_text: str,        # == original_text when status is "unchanged"
  status: "reformulated" | "no_change_needed" | "could_not_safely_reformulate",
  changes: [                     # one entry per span actually changed
    {
      sentence_index, position, span_text, original, replacement,
      source: "substitution" | "restructuring",
      triggered_by: [...],       # which profile entries (sound/word/phrase/
                                  # pattern) caused this span to be flagged
      verification: {
        antonym_check: "pass" | "rejected",
        sbert_sim: float | null,
        nli: "entailment" | "neutral" | "contradiction" | "not_run",
        phoneme_ok: bool,
        difficulty_before: float, difficulty_after: float,
      }
    }
  ],
  skipped: [ {span_text, reason} ],   # existing pattern, kept
  metrics: {                          # never blended, per Practice §10
    meaning_preservation, difficulty_reduction,
    naturalness_edit_amount, substitution_rate,
  },
  final_verification: { passed: bool, details: {...} },  # §24.A step 4
}
```

**[INTERPRETATION]** This contract is deliberately audio-module-agnostic —
nothing about `text`/`profile`/the output shape assumes text came from
typing vs. ASR; a future Audio Module only needs to produce a
`DifficultyProfile`-shaped object and call this same interface, exactly
the decoupling `PROBLEM_FORMULATION.md` §9 already designed the profile
schema for.

---

## 26. Failure handling — explicit outcome states, not silent pass-through

**[RECOMMENDATION]** Three, and only three, top-level `status` values
(§25) — no fourth "partial success" state, to keep the contract simple; a
partially-reformulated sentence still reports `"reformulated"` with some
spans in `skipped`, which already captures the nuance.

| Situation | Handling |
|---|---|
| No safe synonym exists for a flagged word | Marked in `skipped`, contributes to the count-threshold check (§24.D) |
| Every synonym shares the difficult sound | Same as above — Gate B empties the candidate list, already existing behavior, kept |
| Semantic verification fails for all candidates *and* all T5 attempts | That span (or sentence, if escalated) is left unchanged, reported in `skipped` with the specific gate that failed — never a silently-degraded guess |
| T5 produces an unsafe rewrite | Caught by final-output re-verification (§24.A step 4) on *each* of T5's `k` candidates; try the next; if all `k` fail, same clean fallback as above |
| Sentence cannot be safely reformulated at all | `status = "could_not_safely_reformulate"`, `reformulated_text == original_text`, reasons populated — this is literally "I cannot safely reformulate this," not a hidden failure |
| Profile conflicts with natural constraints (degenerate/over-restrictive profile) | The new sanity cap (§24.F) — reported as its own reason, not mangled output |
| Multiple candidates score similarly | Deterministic secondary sort key (combined score, then alphabetical) — reusing `engine.py::_rank()`'s existing tie-break precedent, not introducing nondeterminism |
| Grammatically valid but semantically wrong | This is what §24.A's tiered gate exists to catch — not a separate case |

---

## 27. MVP / Strong / Future

### MVP — implement first
- Consolidate `grammar.py::SentenceRewriter` and `rewrite/rewriter.py::DifficultyAwareRewriter`
  into one substitution-and-rank stage, informed by the (now-run, see §29)
  A-vs-B ablation.
- Tiered semantic verification: WordNet antonym check (free) + existing
  SBERT (unchanged threshold, per §6) — **NLI deferred to Strong** (a new
  model dependency, even a small one, is real integration surface; the
  antonym check covers the highest-confidence, zero-cost part of the same
  risk).
- Naturalness/edit-amount metric (Levenshtein-based, §10/R11) — needed as
  the shared baseline before anything else can be honestly compared.
- Count-threshold escalation trigger (§24.D) and the degenerate-profile
  sanity cap (§24.F) — both pure logic, no new models.
- T5 escalation, repurposing `rephrase.py` exactly as-is (§24.E) — generate
  `k` candidates, re-run the *same* phoneme + SBERT gates already built for
  substitution, no new verification code.
- Position/stress computed and **logged, not scored** (§24.C).
- The failure-mode evaluation corpus (§29) — buildable now, no external
  data needed.

### Strong — add once MVP is measured and works
- Small NLI cross-encoder (`nli-deberta-v3-xsmall`/`-small`), wired into
  the tiered gate's borderline case only (§24.A).
- MLM-native candidate generation — **gated on actually measuring** the
  WordNet/Datamuse skip-rate first (§24.B), not added speculatively.
- Accept/reject feedback loop into the profile (`ROADMAP.md` R9), framed
  as a lightweight contextual bandit per `REFORMULATION_RESEARCH.md` §11.

### Future — explicitly deferred, not silently dropped
- Position/stress as *scored*, fitted formula terms — blocked on real
  speaker data (`ROADMAP.md` R2), unchanged blocking condition.
- Phrase-matching consumption (`ROADMAP.md` R13).
- A learned minimal-edit tagger (GECToR/FELIX-style) — rejected for lack of
  training data (§6), revisit only if that data ever exists.
- A local-LLM upgrade to the escalation stage (§15) — no evidence yet that
  T5's restructuring quality is the bottleneck; premature before the
  escalation stage's actual invocation rate is measured (§18 Q4).
- Any API-based frontier LLM as a default path — still rejected (§15),
  offline/reproducibility values unchanged.
- Cross-substitution interference detection (§24.F) — real gap, small
  expected impact, not worth the modeling cost yet.

---

## 28. Evaluation plan

| Dimension | Automatable now? | Method |
|---|---|---|
| Reformulation effectiveness (did it reduce the flagged pattern) | **Yes, fully** | Deterministic — re-run the same phoneme/difficulty check on the output |
| Naturalness / minimality | **Yes, proxy** | Levenshtein-based edit-amount (§10/R11) — a real metric, not a guess, but still a proxy for *perceived* naturalness |
| Semantic fidelity | **Proxy only** | SBERT + antonym-check (+NLI in Strong) — Practice.md §12's proxy-metric trap applies exactly as already documented in `VALIDATION.md`; stated as a proxy, not equated with true meaning preservation |
| Grammaticality | **Proxy, already exists** | Reuse `grammar.py`'s rule-based checks + optional LanguageTool, unchanged |
| **Speaker suitability** (would *this* speaker actually find it easier) | **No — cannot be automated** | This is the core research claim itself, not a side metric; only a real speaker (or a clinician proxy) can judge it — stated plainly, consistent with `VALIDATION.md`'s existing honesty about this project having no completed human-judgment result yet |

**[RECOMMENDATION]** Build a small, self-constructed **failure-mode
evaluation corpus** now — a `tests/reformulation_eval_corpus.txt`-style
fixture (directly following the precedent already in this repo,
`tests/eval_corpus.txt`), covering §17's ten constructed cases (multiple
difficult words, phoneme-heavy sentence, negation, ambiguous word,
context-dependent substitution, proper nouns, technical terms, long
transcript, multi-sentence context, restructuring-needed), paired with a
handful of synthetic `DifficultyProfile` fixtures. This becomes the
regression baseline for the new engine (mirroring `tests/smoke.py`'s
existing role for the current pipeline) — buildable immediately, requires
no external/real speaker data, and gives §27's MVP something concrete to
be measured against from day one, not just "it ran without crashing."

---

## 29. Architecture comparison — final selection

| | A. Direct generation only | B. Candidate-gen+rank, no escalation | D. Stage 5's original hybrid | **D′. This review's refined hybrid** |
|---|---|---|---|---|
| Quality | High restructuring, unreliable constraints | Good for localized difficulty, can't restructure | Good, some untested assumptions (flat NLI, scored position/stress) | Good, same capability as D with fewer unvalidated assumptions |
| Complexity | Low (one model) but needs verification bolted on anyway | Low–moderate | Moderate–high (new model + new formula terms day one) | Moderate, staged (MVP lean, Strong adds the rest) |
| Compute | Depends on model (§15) | Low, already proven | Low–moderate | Low for MVP, moderate only once Strong's NLI ships |
| Safety | Weak without added verification | Strong (symbolic gates) | Strong | Strong, plus the new degenerate-profile cap (§24.F) and tie-break determinism (§26) |
| Personalization | Same as others (profile-independent) | Reuses existing profile | Reuses existing profile | Reuses existing profile, explicit path to R9's bandit-based feedback loop |
| Recommendation | Rejected (§19, unchanged) | Viable fallback if D′ integration stalls | Superseded by D′ | **Selected** |

**[RECOMMENDATION — final]** **D′.** Every change from D to D′ is justified
by a specific finding from this review (§24.A–F), not a general preference
for caution: tiered verification over flat NLI (cost vs. measured benefit,
§24.A), MLM deferred pending measurement (§24.B), position/stress logged
not scored (Practice.md §6 compliance, §24.C), an explicit count-threshold
trigger (a real gap D didn't have, §24.D), T5's role clarified by a
concrete code-level limitation (§24.E), and two new named edge cases
(interference, degenerate profiles, §24.F) that D was silent on.

---

## 30. Implementation blueprint

**Components** (per §24.E's discard/reuse split — `grammar.py::sanitize_input()`
and `phonetic.py`/`engine.py`/`semantic.py`/`rephrase.py` as *libraries* are
kept; `grammar.py::SentenceRewriter` and `rewrite/rewriter.py::DifficultyAwareRewriter`
as *orchestrators* are discarded, superseded by one new orchestrator):

| Module (proposed) | Responsibility | Built from |
|---|---|---|
| `reformulate.py` (new) | Top-level orchestrator implementing §25's contract | New code; calls the modules below |
| `engine.py`, `phonetic.py`, `semantic.py` | Candidate retrieval, phoneme veto, SBERT — **unchanged** | Existing, reused as-is |
| `semantic.py` (extended) | + WordNet antonym check (§24.A step 1), + NLI wrapper (Strong tier) | Small, additive extension — same pattern as `phonetic.full_pronunciation()`'s additive style in Stage 4A |
| `naturalness.py` (new, small) | Levenshtein-based edit-amount scoring (§10/R11/§28) | New, small, pure-Python |
| `rephrase.py` | T5 escalation — **role changed, code unchanged**: called by `reformulate.py` when substitution's count/failure triggers fire, not as an independent app.py toggle | Existing, reused as-is |
| `difficulty_profile.py`, `profile_store.py` | Unchanged — the stable foundation this stage explicitly preserves | Existing, untouched |
| `grammar.py::sanitize_input()` | Unchanged — pre-processing step, unrelated to substitution | Existing, untouched |

**Data flow**: `app.py` → `sanitize_input()` (unchanged) → `reformulate.py`
(new orchestrator, §25's contract) → internally: tag (existing POS/profile
logic) → substitution-and-rank (consolidated `engine.py`+`semantic.py`+
`phonetic.py`) → count/failure-triggered escalation (`rephrase.py`) →
final verification (§24.A step 4) → §25's output shape → `app.py` renders
`changes`/`skipped`/`metrics` (replacing the current dual rendering of
`grammar.py` and `rewrite/` results with one).

**Algorithms**: unchanged from what's already proven (POS-tag substitution
positions, SBERT cosine similarity, Zipf-frequency ranking, ARPAbet onset
matching) plus two new, small ones: Levenshtein edit-amount scoring, and
the count-threshold/degenerate-profile trigger logic (§24.D/F — simple
arithmetic over already-computed flags, no new algorithmic complexity).

**Models**: SBERT `all-MiniLM-L6-v2` (existing), T5 `Vamsi/T5_Paraphrase_Paws`
(existing) — no new model in the MVP. Strong tier adds one small NLI
cross-encoder (§9's named candidates).

**Dependencies**: none new for the MVP (WordNet antonyms are stdlib-NLTK,
already a dependency; Levenshtein distance is a ~10-line pure-Python
function, no new package needed). Strong tier adds one small model
download (~cross-encoder NLI, comparable footprint to SBERT).

**Interfaces**: §25's exact input/output contract.

**Tests**: unit tests for `reformulate.py`'s each stage (mirroring
`tests/difficulty_profile_test.py`'s per-function style), the new failure-
mode corpus (§28) as an `AppTest`-driven and direct-call regression suite,
and a **byte-identity-style regression check is explicitly NOT the goal
here** — unlike Stages 2/4A/4A-refinement, this *is* the reformulation
engine changing, so `tests/smoke.py`'s existing baseline is expected to
diverge; the new corpus (§28) becomes the new baseline going forward.

**Evaluation**: §28's dimensions, run before/after against the new corpus,
reported separately (never blended, per Practice §10) — old
`grammar.py`/`rewrite/` output vs. new `reformulate.py` output on the same
corpus, as the first real before/after comparison this project will have
produced.

**Migration**: `grammar.py::sanitize_input()`, `engine.py`, `phonetic.py`,
`semantic.py`, `rephrase.py`, `difficulty_profile.py`, `profile_store.py` —
kept, mostly unchanged (semantic.py gets small additive extensions).
`grammar.py::SentenceRewriter`, `rewrite/` package (`rewriter.py`,
`rank.py`, `candidates.py`) — **discarded as orchestrators**, once
`reformulate.py` reaches parity on the new corpus; not deleted blindly on
day one — kept until the new engine is measured to actually be at least as
good, consistent with §9's "be willing to discard, but don't discard
before you've verified the replacement works."

---

## 31. Summary — what survived, what changed

**Survived the critique unchanged:** the four-category difficulty profile
(untouched, confirmed stable per this stage's own instruction); the
symbolic phoneme veto as an always-final gate; SBERT as the primary
semantic signal; T5/`rephrase.py` as the model for the escalation role;
the general shape of tag→substitute→escalate→verify; the "existing
architecture's overall shape already matches best practice" finding from
§6.

**Changed from Stage 5's original recommendation:**
1. NLI: flat "add it" → tiered (antonym-check first, NLI only for
   borderline/generation-sourced cases), and moved from MVP to Strong.
2. MLM candidates: "add them" → deferred to Strong, gated on first
   measuring whether WordNet/Datamuse's ceiling is actually a real
   bottleneck.
3. Position/stress: "add as scored terms" (Stage 5's own §22) → corrected
   to "log as unscored metadata," citing this project's own Practice.md §6
   discipline that Stage 5's recommendation itself under-weighted.
4. A new, previously-missing count-threshold restructuring trigger,
   distinct from the failure-triggered one.
5. T5's constraint mechanism limitation (word-level only, not phoneme-
   level) — found by reading the actual code, not assumed — which settles
   "constrain before or filter after" definitively for the phoneme
   dimension: filter after, always.
6. Two new named edge cases Stage 5 didn't address: cross-substitution
   interference (deferred, named) and degenerate/over-restrictive profiles
   (a new sanity cap added).
7. An explicit, three-state failure-handling contract, including a real
   "I cannot safely reformulate this" outcome, not implied by Stage 5's
   pipeline diagram.

---

# **Architecture is implementation-ready.**
