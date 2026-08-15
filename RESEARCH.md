# RESEARCH.md — Stage 3: The Actual Problem, and What the Field Knows About It

Per Practice.md §19, this is a **research pass** (steps 1–8: read, study literature,
identify assumptions, sort what needs validation). It is explicitly **not**
step 9 — nothing in this document authorizes or performs an implementation
change. No algorithm, threshold, weight, or model in the repository was
touched while producing this file. That restriction is enforced by the user's
own Stage 3 instructions, not just by Practice.md.

## Legend — read this before trusting any claim below

Per Practice.md §5, and per this stage's explicit instruction not to present
an untested recommendation as fact, every substantive claim below is tagged:

| Tag | Meaning |
|---|---|
| **[FINDING]** | Something the cited literature actually reports. Has a source. |
| **[INTERPRETATION]** | Our reasoning about what a finding implies for *this* system. Not itself measured — a judgment call, argued from findings. |
| **[HYPOTHESIS]** | An untested claim about our system, proposed here for future validation. |
| **[LIMITATION]** | A known gap or weakness, stated precisely per §5/§6 rather than swept into "known issues." |
| **[FUTURE WORK]** | Something actionable that isn't done and isn't being started here. |
| **[RECOMMENDATION]** | A forward-looking architecture proposal for Stage 4. Explicitly **not a decision** — Stage 4 is where decisions get made, with the user, against this evidence. |

A citation with a URL means a web search actually surfaced that source during
this pass (2026-08-15) — titles/authors are taken from search results and
abstract pages, not invented. Where a claim couldn't be traced to a specific
paper, it's marked **[INTERPRETATION]** or **[HYPOTHESIS]**, not presented as
a finding with a fake citation.

---

## 1. Problem definition — refined

### 1.1 The definition as given

> Given already-transcribed/entered text plus information about problematic
> phonemes, words, or linguistic patterns for a specific speaker, produce an
> alternative formulation that preserves meaning, intent, relevant context,
> and grammatical correctness, while being easier for that speaker to
> articulate.

This is a reasonable starting point, but three refinements matter enough to
state explicitly before doing anything else.

### 1.2 Refinement 1 — "easier to articulate" is not one thing

**[FINDING]** Psycholinguistic research on speech production separates
**lexical access** (retrieving the right word from the mental lexicon — the
process that word-frequency effects influence) from **articulatory motor
execution** (the physical production of the phoneme sequence). Word-frequency
effects on production speed arise "at the lexical access stage, before the
actual speech motor execution of a word" — the frequency effect is
well-documented for *retrieval* speed, with more limited and contested
evidence for *execution* itself (RTF/QJEP, "Does word frequency affect
lexical selection in speech production?").

**[INTERPRETATION]** Stuttering is clinically understood primarily as a
disruption in the **motor execution / initiation** of speech at specific
sound sequences (onsets), not primarily a word-finding/retrieval disorder
(that's closer to anomia/aphasia). This means "make the word more frequent"
and "make the word easier to say" are not obviously the same intervention
for *this population* — frequency is a well-evidenced proxy for a different
mechanism (retrieval ease) than the one stuttering primarily affects (motor
initiation on a sound). Our `phonetic.word_difficulty()` formula weights
onset-cluster-length and syllable count at 0.4+0.3 and frequency-derived
rarity at only 0.3 — which is at least *directionally* consistent with this
finding (onset gets the most weight), but the *profiling* formula
(`profiling/profile.py`) weights frequency at 0.20 vs. onset at 0.45 — same
direction, unclear if the ratio is right, and **[LIMITATION]** neither ratio
is fitted to actual speaker data (already flagged in `VALIDATION.md`).

### 1.3 Refinement 2 — the target is "easier to say," not "easier to read"

**[FINDING]** Sentence-simplification research (readability/Newsela-style
work) explicitly optimizes for **comprehension** — reading grade level,
Flesch-Kincaid, Dale-Chall — not articulation
("Automated Text Simplification: A Survey," ACM Computing Surveys 54(2);
"Controllable Text Simplification," Scarton & Specia 2018 lineage). Separately,
speech-output research distinguishes **"speakability"** from readability
explicitly: text can be perfectly readable and still be a poor candidate for
being *spoken* (markdown artifacts, run-on structure, TTS-unfriendly
formatting are the concrete examples found, but the underlying point
generalizes: readability and speakability are measured differently and can
diverge) ("EVA-Bench," "Improving Readability for Automatic Speech
Recognition Transcription," Microsoft Research).

**[INTERPRETATION]** Our problem is neither of these exactly. It's not
comprehension-simplification (a "big" word isn't hard for a listener to
understand, it might be hard for *this specific speaker* to physically say).
It's not general speakability (TTS-friendliness is about the text being
speakable *by a machine*; ours is about the text being speakable *by one
human with a specific, idiosyncratic difficulty profile*). The closest
existing frame is closer to **AAC (augmentative and alternative
communication)** and **assistive accessibility writing tools**, not
readability research — see §2.F.

### 1.4 Refinement 3 — "easier to say" itself has a genuine tension in the clinical literature that our problem statement is silent on

**[FINDING]** Word substitution/avoidance is a real, named clinical
phenomenon in stuttering: **circumlocution** ("speaking around" a word) and
**word substitution** are documented coping strategies (SAGE Encyclopedia of
Human Communication Sciences and Disorders; Medbridge; ASHA Practice Portal).
But the same literature is explicit that avoidance is a **double-edged
sword**: it can reduce audible stuttering in the moment, but "may also
increase the speaker's cognitive load," and *chronic* avoidance is associated
with "reduced self-esteem, increased stress," and speech that "feels more
effortful, less comfortable, and less authentic" over time. ASHA and SLP
sources describe avoidance as a pattern that "is not... encouraged" as a
long-term therapeutic strategy, even though it's a real short-term coping
behavior.

**[INTERPRETATION]** This is a genuine, unresolved tension for the *research
objective itself*, not just an implementation detail: a tool that always
substitutes away from a speaker's difficult sounds is mechanizing
circumlocution/avoidance — the exact behavior SLP literature is ambivalent
about, useful in a high-stakes single moment (a presentation, an interview)
but potentially reinforcing avoidance if used as a default, everyday crutch.
**[HYPOTHESIS]** The tool is more clearly justified for **occasional,
high-stakes use** (prepared scripts, presentations — which is also exactly
how the closest prior system, `Fluent`, positions itself; see §2.F) than as
an always-on rewriting layer for all speech. This has architectural
implications (a "how much should the tool touch" dial matters, not just
"can it find a valid substitute") and is worth surfacing to whoever designs
Stage 4, but is **not** something this research pass is deciding.

### 1.5 Refined problem statement

**[RECOMMENDATION — proposed refinement, not a decision]**

> Given text and a *representation* of what's difficult for one speaker
> (which may be phoneme-level, word-level, or eventually pattern-level),
> produce the **minimal sufficient transformation** — substitution, phrase
> change, or restructuring, whichever is actually necessary — that keeps
> meaning, entities, and discourse context intact, stays grammatical, reads
> as natural output (not as "obviously edited"), and measurably reduces the
> *speaker-specific* articulatory burden of the difficult material — while
> remaining an occasional tool a speaker chooses to use for specific
> utterances, not a system that silently rewrites everything.

The important additions relative to the original statement: **minimal
sufficient** (not maximal substitution — see §5.6/§7 on FELIX/LaserTagger and
"naturalness of intervention"), and the explicit acknowledgment that this is
assistive technology sitting inside a clinical context with known
countervailing considerations, not a pure NLP optimization problem.

---

## 2. Literature review by area

### 2.A Paraphrase generation

**[FINDING]** The standard modern architecture is Transformer encoder-decoder
paraphrase generation, evolved from earlier seq2seq/LSTM approaches (Prakash
et al. 2016) — "Paraphrase Generation: A Survey of the State of the Art"
(Zhou & Bhat, EMNLP 2021) is the most direct survey found and frames the
field exactly this way: a "gradual shift to neural methods."

**[FINDING]** A major, actively-researched sub-problem is **controllability**
— plain paraphrase generation produces *a* valid paraphrase, not necessarily
one satisfying a constraint you care about. "Controllable Paraphrase
Generation with a Syntactic Exemplar" (Chen et al., ACL 2019) and "Syntax-
Guided Controlled Paraphraser" (SGCP, 2020) both control paraphrase *syntax*
via an exemplar sentence — different problem from ours (we want to control
*phoneme content*, not syntax-matching), but the pattern — condition
generation on an explicit side-constraint rather than hope the model infers
it — is directly relevant to §2.E/§6 below.

**[INTERPRETATION]** Nothing in mainstream paraphrase-generation research
targets *phonological* constraints — the field's controllability work is
almost entirely about syntax, formality, or length, not sound. This is a
genuine gap, not an oversight on our part — see §2.F.

### 2.B Lexical substitution

**[FINDING]** Contextual lexical substitution moved from WordNet-only
methods to masked-language-model approaches after BERT: mask the target word
(or apply "dropout" to its embedding) and let BERT's MLM head propose
substitutes conditioned on the *whole sentence*, not just the word in
isolation ("BERT-based Lexical Substitution," Zhou et al.; "A Comparative
Study of Lexical Substitution Approaches based on Neural Language Models").
State-of-the-art systems (**LexSubCon**, Michalopoulos et al. 2021/2022;
**ParaLS**, 2023) now *combine* MLM probability with structured lexical
knowledge (WordNet) and sentence-level embedding similarity, rather than
picking one source — LexSubCon reports "at least 2% over all official lexical
substitution metrics" versus prior state of the art by combining these
signals.

**[FINDING] — the core distinction that matters most for us:** a
**dictionary synonym** is a word with overlapping *sense* in WordNet's static
taxonomy; a **contextually appropriate substitute** is a word that fits
*this specific sentence's* meaning, register, and collocational pattern.
"stress" (noun, psychological) and "stress" (verb, emphasize) are the same
lemma but different senses — WordNet-only lookup without a POS/context gate
can leak across them (this is a documented and *already fixed* problem in
our own `engine.py`'s v3 comment, which independently arrived at the same
conclusion the field's MLM-based approaches formalize: use context, not just
the dictionary, to pick the sense).

**[INTERPRETATION]** Our current architecture (`engine.py` WordNet+Datamuse
→ `semantic.py` SBERT-filters the *candidate sentence*) is structurally the
right shape for this distinction — it generates dictionary-adjacent
candidates, then uses a context-aware model to gate them — but it is a
**two-stage retrieval-then-filter** pipeline where the state-of-the-art
(LexSubCon-style) is a **single scoring model that natively combines
contextual and lexical-resource signals**, rather than a hard-cascaded
lookup → hard-threshold gate. The practical difference: an MLM can *propose*
context-fit words WordNet never would (WordNet is closed-vocabulary,
sense-only); our system can only re-rank/reject what WordNet+Datamuse already
proposed. This is a real, literature-grounded weakness — see §5.

### 2.C Sentence simplification

**[FINDING]** Simplification operates at three levels: lexical (word
replacement), syntactic (sentence splitting, active/passive conversion,
clause reordering), and discourse ("Automated Text Simplification: A
Survey," ACM Computing Surveys 54(2); "A Survey on Text Simplification,"
Sikka 2020). Most simplification systems learn all three jointly from
parallel corpora (e.g., Newsela), and "most studies have concentrated on
lexical and syntactic simplification" specifically, per the survey.

**[FINDING]** Modern controllable simplification conditions generation on
an explicit target attribute (reading grade, compression ratio, or discrete
"control tokens" encoding low-level edit operations) rather than producing
one fixed simplicity level ("Controllable Text Simplification with Explicit
Paraphrasing," NAACL 2021; "Taming CATS," 2026).

**[INTERPRETATION — what transfers, what doesn't]**
- *Transfers:* the three-level decomposition (lexical / syntactic / discourse)
  is a genuinely useful frame for our problem too — our system currently only
  operates at the lexical level (word-for-word substitution). If a
  problematic *phrase* or sentence structure is the issue (not a single
  word), nothing in the current pipeline can restructure a clause — see §7.
- *Transfers:* control-token-style explicit conditioning (§2.E) is a better
  pattern than a hard post-hoc threshold for injecting our phoneme
  constraint into a future generative model.
- *Does not transfer:* the simplification field's target metric (reading
  grade level / comprehension) is the wrong optimization target for us — see
  §1.3. A simpler/shorter/more common word is not necessarily easier to
  *articulate* for a person who stutters; a rare polysyllabic word with an
  easy onset can be more speakable than a common monosyllabic word with a
  hard plosive onset. Simplification's frequency-driven lexical-simplicity
  metrics should not be borrowed uncritically.

### 2.D Semantic preservation & how it's actually measured

**[FINDING]** The dominant automated proxy is **Semantic Textual Similarity
(STS)** via sentence embeddings (SBERT and successors), benchmarked on
STS-B: humans rate sentence pairs 0–5 for "meaning equivalence," models are
scored by Pearson correlation to those ratings. **[FINDING]** A
known, specific failure mode: "sentence embeddings are not capturing
negation in sentences, and negations don't seem to affect sentence
similarity scores" — SBERT-family embeddings "fail to reliably distinguish
antonym replacement or word order shuffling," attributed to a lexical-overlap
bias: high surface word overlap between two sentences suppresses the
similarity score's sensitivity to the one word that actually flipped the
meaning ("SBERT studies Meaning Representations," AACL 2022; "Sentence
Smith: Controllable Edits for Evaluating Text Embeddings," 2026).

**[FINDING]** The complementary automated approach is **Natural Language
Inference / bidirectional entailment**: a paraphrase can be modeled as *T
entails H* AND *H entails T* — a strictly different signal from cosine
similarity, because NLI models are trained to detect exactly the
negation/contradiction cases that embedding similarity misses.

**[INTERPRETATION — directly relevant to our system]** Our entire semantic
gate is single-metric cosine similarity (`semantic.py`'s `MIN_SEMANTIC` on
SBERT `all-MiniLM-L6-v2`). Given the negation/antonym finding above, this is
a **[LIMITATION]**, not a hypothetical one: our system has no mechanism to
catch the specific failure mode the literature calls out by name. Concretely,
if the synonym engine ever proposed an antonym-adjacent candidate for a
low-content-word position (rare in our current WordNet+Datamuse pipeline,
which biases toward true synonyms, but not structurally impossible,
especially once any generative component is introduced), SBERT similarity
alone would not reliably reject it. An NLI-based bidirectional-entailment
check is the literature's answer to exactly this gap, and it is a
**[FUTURE WORK]** item worth prototyping as a second, orthogonal semantic
signal — not a replacement for SBERT, an addition, because the two catch
different failure modes.

**[FINDING]** On the human-evaluation side, the standard dimensions are
**fluency** (grammatical, natural-sounding) and **adequacy** (meaning
preserved) as independent axes, sometimes with a third, **coherence**. The
literature is consistent that automated metrics correlate imperfectly with
human judgment and that BLEU-style overlap metrics in particular "does not
suffice to correlate strongly with actual qualitative results." A 2023
survey of text-style-transfer evaluation found 21 of 89 papers used *only*
automated evaluation and 33 used at least one metric that was never
validated against human judgment ("A Call for Standardization and Validation
of Text Style Transfer Evaluation," 2026) — the exact failure mode
`VALIDATION.md` already flags for our own repo (§12's proxy-metric trap,
independently).

### 2.E Controlled/constrained generation

**[FINDING]** **Lexically constrained decoding** is an established
NMT/generation technique: specify tokens that must or must not appear, and
modify beam search (or use gradient-guided / energy-based decoding) to
satisfy the constraint. **Negative constraints** (forbidden tokens) are
explicitly supported, typically by driving banned-token logits toward
−∞, though recent work notes this can distort the model's probability
distribution when the banned token carries real probability mass
("A Simple Recipe for Lexically Constrained Text Generation," INLG 2024;
"(G)I-DLE," 2025). **NeuroLogic Decoding** and its successor **NeuroLogic
A\*esque** generalize this to arbitrary predicate-logic constraints
(conjunctions/disjunctions of word inclusion/exclusion) enforced during beam
search with a lookahead heuristic (NAACL 2022).

**[FINDING]** For instruction-tuned LLMs specifically, **prompt-based**
control ("avoid the word X") is now common but has documented reliability
problems: LLMs show "position bias" (constraints stated in certain positions
are honored more reliably), "low responsiveness to decoding parameters," and
particular difficulty with compound/multi-part constraints ("Controllable
Text Generation for Large Language Models: A Survey," 2408.12599).

**[INTERPRETATION — directly relevant]** Our "phoneme firewall" (Gate A/B in
`grammar.py`'s `SentenceRewriter.rewrite()`) is a **negative constraint over
a fixed candidate set**, not constrained *decoding* — it doesn't generate
under the constraint, it filters candidates already generated without regard
to the constraint. This is actually the *simplest and most reliable* point
on the constrained-generation spectrum (a filter over a closed, enumerable
candidate list can never "leak" a forbidden pattern the way a decoding-time
soft penalty can), and the literature's warning about LLM prompt-based
avoidance being unreliable is, if anything, an argument *for* keeping a
hard, symbolic, post-hoc filter somewhere in the architecture even if a
generative component is added later — not an argument for abandoning our
approach. Where our system currently falls short of the *generation-time*
techniques (NeuroLogic-style constrained decoding) is that we cannot
constrain *restructuring* — if avoiding a phoneme requires a different
clause structure rather than a drop-in word swap, filtering a candidate list
of single-word substitutes cannot find that solution at all. That's a
generation-side gap, not a filtering-side gap — see §7.

`rephrase.py`'s T5 layer partially closes this gap already: it applies a
negative constraint via `bad_words_ids` at generation time (a real,
literature-aligned technique), then re-filters with the same kind of
post-hoc scoring. **[OBSERVATION]** This makes `rephrase.py`, architecturally,
already closer to the "generate-under-constraint, then verify" pattern the
literature treats as state of the art than the main `grammar.py` pipeline is
— worth noting for §6.

### 2.F Phoneme-aware / pronunciation-aware NLP and speech accessibility — the crux of this problem

This is the area where a truly close prior system exists, so it gets the
most space.

**[FINDING] — closest known prior art:** **"Fluent: An AI Augmented Writing
Tool for People who Stutter"** (Ghai, Stony Brook University; ACM ASSETS
2021 / SIGACCESS; also on arXiv 2108.09918, GitHub `bhavyaghai/Fluent`).
Its problem framing is explicitly the same clinical starting point as ours:
"People who stutter often employ word substitution strategies to avoid
stigmatized speech patterns, creating additional cognitive burden," and the
tool is positioned for high-stakes situations (presentations, public
speaking) — matching the §1.4 finding almost exactly. Its architecture:

1. **Difficult-word identification via active learning**, not fixed rules.
   Instead of a hand-coded phoneme-onset heuristic, it asks the *user* to
   label ~5 words "easy"/"difficult," trains a classifier from that signal,
   and *continues learning from ongoing accept/reject interactions*. Reported
   result: ">80% accuracy identifying difficult words in under 20
   interactions," improving with more feedback.
2. **Alternative suggestion** — semantically similar, easier-to-articulate
   words surfaced on hover.
3. **Continuously personalized classifier**, not a static profile.

**[INTERPRETATION] — direct comparison to our system:**

| | Fluent (2021) | This repo |
|---|---|---|
| Difficulty model | **Learned** classifier from user-labeled examples, updated continuously | **Rule-based** ARPAbet onset-cluster heuristic (`phonetic.word_difficulty`) *and*, separately, an **EWMA-updated learned profile** (`profiling/profile.py`) — we actually have both a rule-based and a learned path, split across two pipelines |
| Alternative generation | Semantically-similar word suggestion (method not detailed in the abstract-level sources found) | WordNet + Datamuse retrieval, SBERT-filtered |
| Personalization mechanism | Active learning loop, explicit user feedback signal from labeling | Self-report seed (`coldstart.py`) + EWMA update from disfluency *events* (would come from the Audio Module) — no explicit "was this suggestion good?" feedback loop in either pipeline |
| Scope framing | Explicitly positioned for occasional, high-stakes prepared speech | Not scoped this way in current docs — treated as general-purpose |

**[HYPOTHESIS]** The single most transferable idea from Fluent that our
system currently lacks is **using the accept/reject signal on suggested
substitutions as training data for the difficulty model itself**, rather
than only using it to render a card. `profiling/profile.py`'s `update()`
already accepts arbitrary disfluency events — architecturally it *could*
consume "user rejected this suggestion" as a signal, but nothing in
`app.py`/`rewrite/` currently wires the UI's accept/reject clicks back into
`profile.update()`. This is the concrete gap Fluent's active-learning loop
would close, and it's compatible with (not a replacement for) our profile
architecture.

**[FINDING] — the rest of the phoneme-aware NLP landscape is thin.**
Beyond Fluent, searches for phoneme-aware *generation* mostly surfaced
adjacent-but-different work: **PANCETTA** (tongue-twister generation via
phoneme-aware completion — the opposite goal, maximizing phonetic difficulty
for entertainment), stutter-aware **ASR** (detecting/transcribing stuttered
speech, e.g. SEP-28k dataset, "ASTER" accessibility-testing for ASR on
dysfluent speech), and stutter-aware **TTS** (synthesizing stuttered voices
for training data, "Stutter-TTS"). **[INTERPRETATION]** None of these attack
*text generation that avoids a phoneme for a specific speaker* — that
sub-problem is small enough in the literature that Fluent is close to the
only close match found, which is itself informative: **[OBSERVATION]** this
is a genuinely under-explored research niche, not a solved problem we're
failing to use — a real opportunity, but also a real absence of established
best practice to lean on.

**[FINDING]** Grapheme-to-phoneme (G2P) conversion itself is mature —
neural (LSTM/Transformer, pretrained "GBERT" grapheme models) G2P now
outperforms rule-based systems on out-of-vocabulary words ("A Survey of
Grapheme-to-Phoneme Conversion Methods," 2024). **[INTERPRETATION]** Our
`phonetic.py` uses CMU dict + a small hand-written grapheme fallback table —
adequate for common English but will degrade on OOV/unusual words in a way
a neural G2P model would not; this is a plausible, bounded upgrade path, not
an urgent one (CMU dict covers the large majority of everyday English
vocabulary).

**[FINDING]** Speech-motor-control literature grounds articulatory
difficulty in **coordination complexity across articulators** (jaw, lips,
tongue) and specific **phonological error patterns** (cluster reduction,
final consonant deletion linked to jaw/labial/lingual control limits) —
richer than a single "onset cluster length" number
("The articulatory basis of phonological error patterns in childhood speech
sound disorders," Frontiers 2025; "The difficulty of articulatory
complexity," Cognitive Neuropsychology 34(7)). **[INTERPRETATION]** This is
mostly speech-sound-disorder (child articulation) literature, not stuttering
specifically, and the mechanisms differ — but it supports the general point
that "onset cluster length" is a coarse proxy for a richer articulatory
phenomenon, and syllable-internal structure (not just the onset) plausibly
matters. **[LIMITATION, restated with citation support]** `VALIDATION.md`
already flags the difficulty formula's weights as unfitted; this section
adds that even the *formula's shape* (onset + syllables + rarity, linearly
combined) is a simplification relative to what the speech-motor-control
literature suggests actually drives articulatory difficulty.

### 2.G Personalized language generation

**[FINDING]** Current personalization research for generation splits into
(a) **preference-conditioning**: store a compact user-preference summary or
history and condition generation on it as context (PLUS framework — "Learning
to summarize user information for personalized RLHF," reports 72% win rate
vs. default responses when conditioned on a learned preference summary), and
(b) **latent variable / variational** approaches that infer a per-user latent
without needing explicit per-user fine-tuning ("Personalizing RLHF with
Variational Preference Learning," 2408.10075) — motivated explicitly by the
finding that standard RLHF "cannot account for naturally occurring
differences in individual human preferences" and "simply averag[es] over
differences."

**[INTERPRETATION]** Our `SpeakerDifficultyProfile` is architecturally a
simple, interpretable version of preference-conditioning: a per-user
dictionary of per-onset risk scores, updated by EWMA, read at scoring time.
This is **[OBSERVATION]** a reasonable, explainable choice for a system this
size — the "latent variable" approaches from RLHF research assume a scale of
training data and infrastructure (per-user reward models) that doesn't fit
a project like this, and an explainable per-onset score is arguably *better*
for this specific application than a learned latent, because a speaker or
clinician can actually read `top_onsets()` and understand why a word was
flagged — interpretability is a real requirement here (users need to trust
and potentially correct the profile), not just an implementation nicety.
**[LIMITATION]** What's missing relative to the PLUS-style approach is any
mechanism that learns from *accepted vs. rejected suggestions specifically*
(see §2.F's Fluent comparison) — the current profile only updates from
disfluency *events*, not from the rewrite tool's own suggestion outcomes.

---

## 3. Modern model landscape — comparison for this task

**[FINDING] — direct comparison found:** "Comparative analysis of
paraphrasing performance of ChatGPT, GPT-3, and T5 language models... ParaGPT"
(Pehlivanoğlu, *Expert Systems*, 2024) and "VTechAGP" (2024, comparing BART,
T5, FLAN-T5, ChatGPT, Claude2, LLaMA2 on academic-to-general-audience
paraphrase) are the most directly relevant comparative studies found.
**[FINDING]** Counter-intuitively, "FLAN-T5 has not been shown to be better
than T5 for fine-tuning on new datasets... T5 outperforms FLAN-T5 for 12 out
of 16 cases" in one such comparison, despite FLAN-T5's stronger zero/few-shot
performance generally — i.e., instruction-tuning helps zero-shot use, not
necessarily task-specific fine-tuning quality.

| Model family | Controllability | Semantic preservation | Fluency | Restructuring ability | Forbidden-word obedience | Personalization potential | Inference cost / latency | Local feasibility | Reproducibility | Data/fine-tune needs | Fit for a student/research project | Explainability |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **T5 / FLAN-T5 (small–base, fine-tuned)** — *what `rephrase.py` already uses* | Moderate — prefix conditioning, `bad_words_ids` at decode time | Good after fine-tuning on paraphrase data (PAWS-based) | Good | Limited — mostly local rewording unless fine-tuned specifically on restructuring pairs | Reliable (hard decode-time constraint, not prompted) | Needs per-user fine-tuning or conditioning tricks — not built in | Low–moderate on CPU for small variants (~220M params, already validated to run locally in this repo per `changes.md`) | **High** — already running here | High — deterministic given weights+seed | Needs a paraphrase corpus (PAWS exists; a stutter-specific corpus does not) | **Good fit** — small, offline, explainable failure modes | Moderate — score-and-threshold pipeline around it is legible even if the model itself is a black box |
| **BART (fine-tuned)** | Similar profile to T5 | Comparable, sometimes stronger on summarization-adjacent rewriting | Good | Similar limits to T5 unless fine-tuned for it | Same decode-time constraint options as T5 | Same as T5 | Similar to T5-base | High | High | Similar to T5 | Good fit, interchangeable with T5 for this use case | Moderate |
| **Encoder-only + MLM lexical substitution (BERT/LexSubCon-style)** | High *for single-word substitution specifically* — that's the whole task | Good at the word level; doesn't address sentence-level restructuring at all | N/A (not a full generator) | **None** — single-word task by design | Trivial to add as a post-filter (same pattern we already use) | Low on its own; would need to be paired with our profile at ranking time | Low latency, small models | High | High | Needs no fine-tuning for a reasonable baseline (LexSubCon-style pipelines exist pretrained) | **Good fit for the substitution half of the problem specifically** | High — candidate list + score is fully inspectable |
| **Instruction-tuned local LLM (e.g. small open-weight chat models)** | Prompt-based — literature-documented reliability problems with position bias and multi-constraint prompts (§2.E) | Depends heavily on prompt/model; no built-in guarantee | Usually strong | **Best restructuring ability of any option** — can rewrite whole clauses | **Unreliable via prompting alone** per §2.E findings; would need a post-hoc verifier regardless | Prompt-based profile injection is easy to try, unclear reliability | Higher than T5-small; local feasibility depends heavily on model size chosen | Possible but heavier — needs a capable enough local model to be worth it over T5 | Lower — sampling variance, prompt sensitivity | No fine-tuning required to start, but needs careful prompt+verification engineering | Reasonable fit **only if paired with a hard post-hoc verifier**, given §2.E's reliability findings | Lower — harder to explain *why* a specific output was chosen |
| **API-based frontier LLM** | Best raw restructuring + instruction-following capability | Strong, but still needs verification per §2.D/§2.E (hallucination risk is a documented, named failure mode — "faithfulness hallucination") | Best | Best | Same prompting caveats as above, at higher capability | Prompt-based, same caveats | Network-dependent latency, per-call cost | **Low** — requires network + API key, breaks the project's current "runs fully offline" property (README) | Non-deterministic across API versions — a real reproducibility cost for a research project that wants to report stable results | None | **Poor fit as the *only* pipeline** for a project whose current identity is offline/reproducible/free; reasonable as an optional/experimental layer only | Lower |

**[INTERPRETATION]** No single row in this table is "the" answer. The
literature and the constraints of this specific project point toward a
**hybrid**, not a single-model swap — see §6.

---

## 4. Evaluation methodology — what should actually be measured

Per Practice.md §10 (already honored by our `eval/metrics.py`, which reports
meaning-preservation and difficulty-reduction as separate fields, not one
blended score) and per this stage's explicit ask, evaluation needs more axes
than embedding similarity.

| Dimension | What it asks | Best available automated proxy | What automated metrics miss **[FINDING/INTERPRETATION]** |
|---|---|---|---|
| Semantic fidelity | Same meaning? | SBERT cosine sim; NLI/bidirectional entailment (§2.D) | Negation/antonym insensitivity (documented, §2.D); doesn't catch subtle scope/quantifier shifts |
| Context preservation | Entities, relationships, facts, discourse intent intact? | Named-entity match, coreference consistency checks | **[LIMITATION]** No automated metric for this exists in our current `eval/` — NER-preservation research (§2.D-adjacent, "PANER," entity-masking approaches) targets NER *training data augmentation*, not this kind of live user-facing check; would need to be adapted |
| Fluency | Reads naturally? | Perplexity under a language model; grammar-checker pass rate (we already have LanguageTool available) | Perplexity rewards "safe"/generic phrasing, penalizes legitimate register/style choices |
| Grammaticality | Linguistically valid? | Grammar-checker (LanguageTool), our own rule-based checks | Rule-based checkers have known blind spots (already documented in our own `README.md`'s Known Limitations) |
| Reformulation effectiveness | Did it actually avoid the flagged phoneme/word? | Deterministic — this one *can* be fully automated (re-run `phonetic.matches_any`/onset check on the output) | Nothing — this is the one dimension our system can check with certainty, and does |
| Speech difficulty reduction | Genuinely easier for *this* speaker? | Our difficulty formula, before/after | **[LIMITATION, restated]** The formula itself is unvalidated (per `VALIDATION.md`) — so "automated" here means "automated according to an unvalidated model," which is a materially weaker claim than the other rows |
| Naturalness of intervention | Minimal, non-gratuitous edits? | Edit distance / substitution rate (we already compute this — `metrics()`'s `substitution_rate`) | Edit distance doesn't distinguish a *necessary* edit from a *gratuitous* one — a system could make exactly one edit and have it still be the wrong one, or make many necessary edits and score "worse" by this metric despite being correct |

**[FINDING]** The literature is consistent (§2.D) that **human evaluation
along fluency/adequacy/coherence axes remains necessary** — no automated
metric substitutes for it, and using unvalidated automated metrics as if
they were validated is a documented, named problem in adjacent fields
(style-transfer evaluation, 21/89 papers found to rely solely on automated
metrics). Our own `VALIDATION.md` already states this as the central,
unresolved gap for this repository (§12's proxy-metric trap): the one
component aimed at the *real* outcome — `eval/study/`, a counterbalanced
three-condition human study — has no confirmed run.

**[RECOMMENDATION — not a decision]** If a human study does run (per
`ROADMAP.md` R4), it should score **semantic fidelity/context/fluency/
grammaticality separately from difficulty reduction** (already the plan,
per §10), **and separately from "naturalness of intervention"** — a
condition that changes fewer words but changes the wrong ones is a
different failure from one that changes many words correctly. Collapsing
these would repeat exactly the trap Practice.md §10 warns against.

---

## 5. Critical analysis of the current implementation, component by component

For each component: what problem it solves, whether that formulation is
sound, whether the method is appropriate, what evidence exists, what the
literature suggests instead, likely failure modes, redundancy, and a
keep/reconsider judgment. **No code changes are implied or made here.**

### 5.1 `grammar.py::sanitize_input()` — rule-based grammar correction

- **Problem:** Fix contractions/tense/agreement/spelling before substitution.
- **Sound formulation?** Yes — grammatical correctness is explicitly part of
  the research objective (Practice.md §1), and doing it *before* substitution
  (so the rewriter operates on clean input) is the right order.
- **Method appropriate?** A hand-written rule cascade is a defensible choice
  for a well-scoped, common-error set (contractions, basic SVA) — this is
  exactly the kind of problem rule systems still do well on, and it's fully
  offline/deterministic/explainable, which the project's other design
  choices (no API keys, offline-first) already value.
- **Evidence:** None cited in-repo beyond "it passes the smoke tests" — but
  this is lower-risk than the scoring/threshold components, since grammar
  rules are either right or wrong on a given input, not a calibration
  question.
- **Literature suggests instead:** LanguageTool (already integrated as an
  optional deep-check layer) or a neural grammar-error-correction model
  (GECToR-style tagging models are the modern standard) — but the rule
  cascade + optional LanguageTool fallback we already have is a reasonable,
  literature-consistent hybrid (rules for common/cheap cases, a heavier model
  for the rest), not a naive approach.
- **Failure modes:** Documented already in `README.md`'s Known Limitations
  (POS-tagger misfires on short/broken sentences; SVA looks left for nearest
  subject, fails on relative clauses).
- **Redundant?** No.
- **Keep?** **Yes** — this component is not where this project's real risk
  lives.

### 5.2 `engine.py::SynonymEngine` — WordNet + Datamuse candidate retrieval

- **Problem:** Generate candidate substitute words for a target word.
- **Sound formulation?** Partially. Per §2.B, "dictionary synonym" ≠
  "contextually appropriate substitute" — generating candidates from
  WordNet/Datamuse *without* context, then filtering with context downstream
  (SBERT), is a defensible two-stage design, but it inherits a structural
  ceiling: **the candidate set is closed and context-blind at generation
  time.** If the ideal substitute for a word, in this sentence, is a word
  WordNet doesn't list as a synonym of it, this pipeline can never propose
  it — no amount of downstream filtering fixes a missing candidate.
- **Method appropriate?** Reasonable for a first-generation system;
  literature has moved toward MLM-based candidate generation (§2.B) precisely
  because it removes this ceiling — an MLM proposes words that fit *this
  context*, not words that share a WordNet sense.
- **Evidence:** The v3 docstring's own reasoning (POS-gating fixed a
  documented cross-POS contamination bug) is sound engineering, verified by
  this project's own examples — a real, in-repo instance of the exact
  problem §2.B's literature describes.
- **Literature suggests instead:** MLM-based (BERT-family) candidate
  generation, optionally still combined with WordNet as one signal among
  several (LexSubCon's approach) rather than WordNet/Datamuse as the sole
  source.
- **Failure modes:** Silently produces zero candidates for words WordNet
  doesn't cover well (rarer words, or words whose best substitute isn't a
  "synonym" in the dictionary sense but is contextually apt) — this fails
  *silently* as "no synonyms found," which is safe (no bad substitution) but
  under-delivers on the objective.
- **Redundant?** Reimplemented independently (with drift risk) in
  `rewrite/candidates.py` — see §6.
- **Keep?** **Reconsider, not discard** — a real architectural ceiling exists
  here per the literature; whether to raise it is a Stage-4 decision, not
  something to act on now.

### 5.3 `semantic.py` — SBERT threshold gate

- **Problem:** Reject candidates that drift from the original meaning.
- **Sound formulation?** Yes, meaning-preservation absolutely needs a gate —
  but per §2.D, cosine similarity on sentence embeddings is a **[FINDING]**-
  documented incomplete proxy specifically for negation/antonym drift.
- **Method appropriate?** SBERT is a legitimate, standard choice (§2.D) —
  the *specific* weakness is not "wrong model," it's "single-signal gate
  where the literature suggests a second, orthogonal signal (NLI) catches a
  known blind spot the first one has."
- **Evidence:** `DECISION_LOG.md` already documents that our own
  `MIN_SEMANTIC=0.85` threshold was raised by argument/example (not a
  dataset-level measurement), and that a later diagnostic sweep recommended
  ~0.80 without the recommendation being applied or the conflict resolved —
  this project's own evidence trail already flags this as unsettled, and
  the literature (§2.D's STS-benchmark limitations) supports treating it as
  genuinely unsettled rather than assuming 0.85 is correct.
- **Literature suggests instead:** NLI/bidirectional-entailment as a second
  gate, not a replacement; possibly per-POS thresholds (the sweep's own
  unactioned recommendation lines up with per-POS calibration being a known
  good idea in embedding-similarity literature generally, where different
  POS classes have different baseline similarity distributions).
- **Failure modes:** Antonym/negation leakage (rare given WordNet-sourced
  candidates bias toward true synonyms, but not structurally prevented);
  over-rejection of legitimately good candidates near the threshold, with no
  mechanism to learn from consistent near-threshold rejections.
- **Redundant?** Reimplemented with a *different* accept rule in
  `rewrite/rank.py` (hard `sim >= tau` only when SBERT is available; silently
  accepts everything when it's not) — a real, literature-unrelated
  consistency risk. See §6.
- **Keep?** **Yes, but add a second signal** is where the evidence points —
  not a redesign of this component, an addition alongside it.

### 5.4 `phonetic.py::word_difficulty()` — rule-based articulatory difficulty

- **Problem:** Score how hard a word is to say for *this population*.
- **Sound formulation?** Reasonable starting point (onset cluster, syllable
  count, rarity, plosive bonus) but per §1.2/§2.F, articulatory difficulty in
  the speech-motor-control literature is richer than a linear combination of
  these three factors — coordination complexity, syllable-internal structure,
  and (per §1.2) frequency's *actual* mechanism (lexical access, not motor
  execution) are all more nuanced than the current formula captures.
- **Method appropriate?** A hand-picked linear formula is a legitimate,
  interpretable starting point for a research prototype — the concern isn't
  the functional form, it's that the weights are unfitted (already flagged
  in `VALIDATION.md`) and now, per §2.F, that the *inputs* themselves are a
  simplification of what the clinical literature measures.
- **Evidence:** None beyond engineering intuition, by the project's own
  admission (`VALIDATION.md`).
- **Literature suggests instead:** Either (a) fit these weights against real
  speaker data once available (already `ROADMAP.md` R2, correctly
  identified and correctly marked as blocked on data), or (b) replace the
  hand-picked formula with **Fluent's approach**: a learned classifier from
  user-labeled difficult/easy examples, which sidesteps the need to
  hand-derive the "correct" formula at all.
- **Failure modes:** Systematically mis-ranks difficulty for any speaker
  whose actual difficulty pattern doesn't match onset-cluster-length +
  syllable-count + rarity (e.g., a speaker whose blocks are triggered by
  specific vowel-onset words, or by sentence-initial position rather than
  the word's phonetic content at all — position-in-utterance effects are not
  modeled anywhere in this formula).
- **Redundant?** A *second*, differently-weighted formula exists in
  `profiling/profile.py` — see §5.5/§6.
- **Keep?** **Reconsider the *architecture* (rule-based fixed formula vs.
  learned), not just the weights.**

### 5.5 `profiling/profile.py` — persistent, EWMA-updated speaker profile

- **Problem:** Represent and update per-speaker difficulty over time.
- **Sound formulation?** Yes — this is the right shape for the
  personalization half of the problem (§2.G), and its interpretability
  (per-onset scores a human can inspect) is a genuine strength relative to
  latent-variable personalization approaches, per §2.G's analysis.
- **Method appropriate?** EWMA update from labeled events is simple,
  standard, and appropriate for this data volume; cold-start blending
  (population prior + self-report, decaying as real data accumulates) is
  sound design, directly mirroring how the personalization literature (§2.G)
  frames the cold-start problem.
- **Evidence:** Internally consistent (tests pass, decay/blend logic is
  correct per `tests/roadmap_test.py`), but the weights it *uses*
  (0.45/0.25/0.20/0.10) share `phonetic.word_difficulty()`'s "unfitted"
  limitation.
- **Literature suggests instead:** Per §2.F's Fluent comparison, the missing
  piece isn't the profile mechanism itself, it's the **feedback loop** —
  wiring the UI's accept/reject signal on suggestions back into
  `profile.update()`, the way Fluent's active-learning loop does.
- **Failure modes:** Currently seeded almost entirely by self-report in this
  repo (the Audio Module's event stream is out of scope, per Stage 2) — so in
  practice, right now, this sophisticated update mechanism is mostly running
  on a static, user-typed seed with little real updating happening. This is
  an honest **[LIMITATION]**, not a flaw in the mechanism.
- **Redundant?** No — this is the one clearly load-bearing, non-duplicated
  personalization component.
- **Keep?** **Yes, and prioritize closing the feedback-loop gap.**

### 5.6 The rewrite loop's shape itself — substitute-in-place vs. edit/restructure

- **Problem (implicit, not explicitly named anywhere in the current code):**
  transform a sentence to reduce difficulty while preserving everything else.
- **Sound formulation?** Both pipelines assume the transformation is always
  a **single-token, same-position substitution**. Per §2.C (simplification
  can split/reorder/passivize) and per §7 below, this is an assumption, not
  a given — and per §2's FELIX/LaserTagger finding, the field has a whole
  architecture family (**text-editing / tag-and-insert models**) built
  specifically around "most of the output is copied from the input, a
  minority is actually changed" — which is *exactly* our situation, and
  which our current architecture approximates only informally (by
  construction — we literally only ever touch one token position — rather
  than by an explicit "decide what to keep, what to change" model).
- **[INTERPRETATION]** This is arguably the single most important framing
  finding of this whole research pass: **our system already behaves like a
  minimal-edit / tag-based system in spirit** (grammar.py touches individual
  tokens, leaves everything else untouched) **but implements it as a
  hand-coded loop rather than as a principled model of "what needs to
  change."** The FELIX/LaserTagger family exists precisely to formalize this
  pattern (tag tokens to keep/delete/reorder, insert only what's new) and to
  do it *fast* (non-autoregressive, "two orders of magnitude faster than
  comparable seq2seq models") — both properties (minimal-edit philosophy,
  speed) that our project's constraints (offline, low-RAM, research
  prototype) would value. See §6/§8.

---

## 6. The two-pipeline question, and the T5 layer, examined against the literature

**Pipeline A** (`grammar.py`): hard SBERT threshold + phoneme-onset filter,
single best-candidate substitution per word, gated *only* when the user has
declared patterns/blocked words.

**Pipeline B** (`rewrite/`): continuous soft-difficulty scoring
(`similarity − λ·difficulty + μ·frequency`), driven by the profile, applied
per-sentence, independent of whether the user typed explicit patterns.

**Layer C** (`rephrase.py`): T5 generation with `bad_words_ids`, re-scored
by a fourth, differently-weighted formula
(`w_sim·sim − w_diff·diff − w_viol·violations − w_edit·edit`).

**[FINDING] — is there a principled reason in the literature to run multiple
approaches?** Yes, but not for *this specific reason* (two independently-
maintained implementations of the same idea). The literature's actual
argument for hybrid architectures is **complementary failure modes**:
generate-then-verify pairs a component with high recall/creativity
(a generator that might propose something invalid) with a component that
has high precision (a verifier/filter that catches invalid outputs) —
exactly the neuro-symbolic "generator + symbolic verifier" pattern found in
§2.E's search results, and exactly what `rephrase.py`'s
generate-with-constraint-then-rescore already does internally.

**[INTERPRETATION]** Pipeline A and Pipeline B are **not** complementary in
this sense — they attack the *same* sub-problem (single-word substitution)
with the *same* candidate source (`engine.py`, imported by both) and the
*same* general scoring shape (similarity combined with a difficulty/frequency
term), differing mainly in **whether the difficulty signal is binary
(onset match / no match) or continuous (profile score)** and in **whether
gating is manual (user must type patterns) or automatic (profile-driven,
runs by default)**. This is duplication of implementation, not
principled architectural diversity — `DOCS.md`/`ROADMAP.md` R5 already
correctly identifies this as an observation requiring a comparison before
consolidating, and this research pass agrees with that framing rather than
overriding it: **the honest answer is "we don't yet know which produces
better output," and that's an empirical question (R6/R7), not one literature
alone resolves.**

**[RECOMMENDATION — not a decision]** What the literature *does* support is
collapsing the **binary-vs-continuous difficulty signal** into one
continuous signal (Pipeline B's shape is more expressive and literature-
aligned — a hard onset match/no-match is a special case of a continuous
risk score, not a different kind of thing), while keeping something like
Pipeline A's **explicit, symbolic, always-final phoneme veto** as a hard
safety filter layered *after* the continuous ranking — mirroring exactly the
generate/rank-then-symbolically-verify pattern §2.E and §6's neuro-symbolic
finding both describe as the state of the art, rather than maintaining two
parallel end-to-end pipelines that each do generation-and-filtering
internally.

`rephrase.py` is, by this framing, **already the closest thing in the repo
to the literature's preferred pattern** — generate under a constraint, then
score/verify — it just currently sits as an optional *third* layer on top
of whichever of A/B ran first, rather than being the architecture the other
two are built around.

---

## 7. Fundamental conceptual weaknesses — direct answers to the Stage 3 questions

- **Are we treating a sentence-level problem as independent word
  substitution?** **[FINDING via §2.C/§5.6]** Yes, structurally. Both
  pipelines score one substitution at a time; nothing models interaction
  between two substitutions in the same sentence (see next bullet).
- **Is phoneme avoidance at the word level sufficient?** **[INTERPRETATION]**
  Sufficient for the common case (a single problem word with a good
  same-meaning alternative), insufficient whenever the difficulty is
  positional (sentence-initial word, regardless of content) or structural
  (the *only* natural phrasing puts a hard sound at a stressed position) —
  neither case is representable by "substitute this token."
- **Does onset matching actually measure articulation difficulty?**
  **[FINDING, §1.2/§2.F]** Partially — it captures one real, clinically
  relevant factor (onset phoneme class) but the speech-motor-control
  literature indicates real articulatory difficulty is multi-factorial in
  ways our linear formula doesn't represent (§5.4).
- **Can semantic similarity guarantee meaning preservation?** **[FINDING,
  §2.D]** No — documented negation/antonym blind spot. "Guarantee" is too
  strong a claim for any single automated metric found in this research
  pass.
- **Is sentence-level cosine similarity sufficient for semantic
  equivalence?** **[FINDING, §2.D]** No, per the same evidence — it's a
  useful, cheap, imperfect proxy, not a sufficient condition on its own.
- **Can frequency be treated as a proxy for ease of speech?**
  **[FINDING, §1.2]** Frequency is a well-evidenced proxy for *lexical
  access* ease. It is a *weaker*, less-established proxy specifically for
  *articulatory/motor* ease, which is the mechanism most relevant to
  stuttering. Using it as one input among several (as both our formulas do,
  at modest weight) is more defensible than using it as the primary signal
  — which is consistent with how both our current formulas already weight
  it (not primary) — this is one place our existing design already reflects
  the right instinct, even without having the citation for it.
- **Does simplifying vocabulary necessarily make speech easier?**
  **[FINDING, §1.3]** No — this is the readability-vs-speakability gap
  named explicitly. A simpler/more common word is not necessarily easier to
  say for a specific speaker's specific difficulty profile.
- **Should the system rewrite only problematic regions or potentially
  restructure the whole sentence?** **[INTERPRETATION, §5.6/§6]** The
  literature (simplification's syntactic-restructuring tools, FELIX/
  LaserTagger's tag-and-insert framing, constrained-decoding's inability to
  restructure) collectively suggests: **default to minimal, localized edits;
  escalate to restructuring only when localized substitution provably fails**
  (no candidate exists / no candidate passes the semantic+phoneme gates) —
  not restructure-by-default, and not never-restructure either.
- **How should multiple problematic words interact?** **[LIMITATION]**
  Genuinely unaddressed in the current architecture and, as far as this
  research pass found, thinly addressed in the literature specifically for
  this compounding case (most constrained-generation work handles multiple
  *simultaneous* constraints within one generation call — §2.E's NeuroLogic
  conjunctive-constraint framing is the closest applicable idea — but our
  current substitute-one-token-at-a-time loop doesn't model interaction
  between changes at all, e.g., whether fixing word 3 makes word 7 easier
  or harder to phrase).
- **What happens when avoiding a phoneme requires restructuring rather than
  substitution?** **[LIMITATION, restated]** Currently: nothing — the system
  reports "no synonyms found" / "no valid synonym" and leaves the word
  untouched. This is the single clearest capability gap surfaced by this
  research pass, and it's exactly where generation-based approaches (T5,
  LLM, or a text-editing model) would need to take over from pure
  substitution.
- **How should the system handle proper nouns, technical terms, numbers,
  names, or context-dependent expressions?** **[FINDING, §2.D-adjacent]**
  The literature's answer for paraphrase/simplification systems generally is
  **entity masking/protection before generation** (mask named entities as
  placeholders, generate around them, restore afterward) — our current
  system does something structurally similar but *ad hoc*: `_STOP`/
  `_PROTECTED_SINGLE` lists and NNP/NNPS POS-tag checks in
  `rewrite/candidates.py`'s `detect_protected_words()`. This is
  literature-consistent in spirit but implemented as a second, independent
  protection list rather than a single shared mechanism — another instance
  of the §6 duplication pattern.
- **How can we distinguish a genuinely helpful reformulation from an
  unnecessary paraphrase?** **[LIMITATION, §4]** This is the "naturalness of
  intervention" evaluation gap named in §4 — no existing component or
  metric in this repo, or found in the literature search, cleanly answers
  "was this specific edit necessary," as distinct from "was this edit
  correct." Edit-count/substitution-rate is the closest proxy we have, and
  it's a weak one (§4's table).

---

## 8. Research-backed verdict

### What's good about the current system
- The **offline-first, low-RAM-aware, fully local architecture** is a real,
  non-obvious strength relative to almost every "modern" alternative in §3's
  table — most literature assumes GPU/API access this project deliberately
  doesn't require.
- **Separating meaning-preservation and difficulty-reduction as distinct,
  never-blended metrics** (`eval/metrics.py`) is already exactly right per
  Practice.md §10 and per the style-transfer evaluation literature's own
  complaint about collapsed metrics.
- **POS-gating WordNet lookups** (`engine.py` v3) independently arrived at
  a fix the lexical-substitution literature treats as foundational
  (context/POS-aware candidate retrieval, not blind dictionary lookup).
- **The phoneme filter as a hard, symbolic, post-hoc veto** is, per §2.E,
  architecturally the *safest* point on the constrained-generation spectrum,
  not a naive one — worth keeping as a component even under a redesign.
- **The speaker-profile design** (interpretable per-onset scores, EWMA
  update, cold-start blending) is sound personalization architecture per
  §2.G, and more explainable than the field's more sophisticated
  latent-variable alternatives — a genuine fit for this application's need
  for user trust and inspectability.

### Technically sound ideas
- Two-stage generate-then-filter for lexical substitution (§2.B).
- SBERT as *a* semantic signal (not *the only* one it should be — see below).
- Rule-based grammar correction as a fast, deterministic first pass with an
  optional heavier fallback (LanguageTool) — a legitimate hybrid, not a
  compromise.
- `bad_words_ids`-based negative constraints in `rephrase.py` — a real,
  literature-supported technique, correctly applied.

### Promising but insufficiently validated
- The difficulty formula's weights and even its functional form (§5.4) —
  already flagged in `VALIDATION.md`, reinforced here with clinical-
  literature grounding for *why* it's likely too coarse, not just "unfitted
  numbers."
- The `0.85` SBERT threshold specifically (§5.3) — this research pass adds
  literature-level support to `DECISION_LOG.md`'s existing, unresolved
  finding that this number was never properly validated.
- Whether Pipeline A or B produces better output — genuinely unknown, and
  literature doesn't resolve an empirical question about *this* system;
  needs the ablation `ROADMAP.md` R5/R6/R7 already call for.

### Fundamentally weak or poorly matched to the problem
- **Maintaining two independently-implemented, non-complementary pipelines**
  for the same sub-problem (§6) — not because either pipeline is bad, but
  because the literature's actual argument for multi-component architectures
  (complementary failure modes) doesn't apply to two components that fail
  the same way.
- **No restructuring capability at all** (§5.6/§7) — the largest capability
  gap relative to what the problem statement (§1) actually promises
  ("syntactic restructuring... clause restructuring... sentence-level
  paraphrasing" were named in the user's own problem framing, and nothing in
  the current implementation does any of them).
- **Single-signal semantic gating** (§2.D/§5.3) with a literature-documented,
  specific blind spot (negation/antonym) that nothing in the system catches.

### What should probably survive into the next design
Per the analysis above: the offline/low-RAM design constraint itself, the
speaker-profile mechanism (with a feedback-loop addition), POS-aware
candidate retrieval, the phoneme filter as a hard final veto, SBERT as one
of (not the only) semantic signals, and the general shape of
"generate-candidates → score → filter" for the substitution sub-problem.

### What should probably be discarded (as a *hypothesis for Stage 4*, not a decision made here)
Maintaining Pipeline A and Pipeline B as two full, separately-coded,
end-to-end paths going forward — not because one is "wrong," but because the
literature gives no principled reason to keep both once one is proven better
via the ablation this repo's own roadmap already calls for.

### What requires experimentation before deciding
Everything under "promising but insufficiently validated" above, plus: does
adding an NLI-based second semantic signal change acceptance rates or
quality in practice; does a text-editing/tag-based model actually outperform
the current substitute-in-place loop on this specific task, where "most of
the sentence stays the same" is true by construction, not just in general
text-editing tasks.

### Important capabilities missing entirely
1. Any restructuring capability beyond single-word substitution.
2. A feedback loop from accept/reject decisions into the difficulty model
   (the clearest, most directly transferable gap relative to Fluent).
3. A second semantic-preservation signal (NLI) beyond SBERT cosine
   similarity.
4. Any automated or human-validated measurement of "naturalness of
   intervention" as distinct from raw edit count.
5. Interaction modeling between multiple substitutions in the same sentence.

### How the current implementation compares conceptually to modern approaches
It sits at roughly the **2019–2021 generation of lexical-substitution/
paraphrase research** (WordNet+embedding-filter pipelines, single-signal
semantic gates, hand-tuned formulas) — solid, explainable, and honestly not
far from where a genuinely close prior system (Fluent, also 2021) landed
independently, which is reassuring evidence the overall approach isn't
misguided. It has not yet incorporated the subsequent generation of ideas
(MLM-native candidate generation, NLI-augmented semantic gating, tag-based
minimal-edit generation, constrained decoding for restructuring) that would
close its most concrete gaps.

### If we were starting this module from scratch today — architecture recommendation

**[RECOMMENDATION — explicitly not a decision, for Stage 4 to evaluate]**

A three-layer, generate-then-verify architecture, collapsing the current
two-pipeline duplication into one:

1. **Candidate/edit proposal layer** — for the common case (single
   problematic word, good substitute exists), keep something like the
   current MLM-augmented-by-lexical-resource approach (§2.B's LexSubCon
   pattern: combine contextual model + WordNet/Datamuse, not WordNet alone).
   For the case current substitution can't solve (no valid single-word
   candidate, or the difficulty is structural/positional), escalate to a
   constrained generative pass (T5-class model, as `rephrase.py` already
   does) — i.e., `rephrase.py`'s role changes from "optional final polish
   layer" to "fallback when substitution provably fails," which is a more
   literature-aligned division of labor than running it as an independent
   optional toggle.
2. **Continuous difficulty scoring, one profile, one formula** — merge the
   binary onset-match gate and the continuous profile-difficulty score into
   a single continuous signal (§6), informed by both the psycholinguistic
   nuance in §1.2 and, eventually, fitted weights per `ROADMAP.md` R2.
3. **A hard, symbolic, always-final verification layer** — combining (a) the
   phoneme/onset veto (kept exactly as it is — it's already the right
   pattern per §2.E) and (b) a second semantic-preservation check (NLI/
   bidirectional entailment) alongside the existing SBERT gate, not
   replacing it — mirroring the generate-then-symbolically-verify pattern
   §2.E/§6 both point to as state of the art.

This explicitly does **not** mean "replace WordNet with an LLM" or "throw
away the phoneme filter" — per Practice.md §3, nothing here is preservation-
or novelty-biased. It means: keep the components the evidence supports
(profile design, hard phoneme veto, POS-aware retrieval, offline-first
constraint), stop maintaining duplicate implementations of the same idea,
and close the two gaps the literature most clearly identifies (no
restructuring path, single-signal semantic gate).

---

## 9. Open questions for Stage 4 (not resolved by literature alone)

1. Is the ablation (Pipeline A vs. B, `ROADMAP.md` R6/R7) run *before* or
   *as part of* deciding the unified architecture in §8? Literature can't
   answer this — it's a project-planning decision.
2. What's the actual latency/RAM budget for adding an NLI model as a second
   semantic gate, given this project's low-RAM constraint (§3's table
   flags this as a real trade-off, not resolved here)?
3. Is a fitted difficulty formula (blocked on real speaker data per R2) or a
   learned classifier (Fluent's approach, needs no real speaker data, just
   in-session labeling) the better near-term path, given that real speaker
   data is explicitly not available yet?
4. Should the "occasional, high-stakes use" framing from §1.4's clinical
   tension become an explicit product/UX decision (e.g., framing, not just
   architecture) — this research pass surfaces the tension but the resolution
   is a product decision informed by, not dictated by, the literature.
5. How much of the restructuring gap (§7) is worth closing given the
   project's scope as a research prototype vs. a production clinical tool?

---

## 10. Bibliography (sources actually surfaced during this pass, 2026-08-15)

**Paraphrase generation**
- Zhou, J. & Bhat, S. "Paraphrase Generation: A Survey of the State of the
  Art." EMNLP 2021. https://aclanthology.org/2021.emnlp-main.414/
- Chen, M. et al. "Controllable Paraphrase Generation with a Syntactic
  Exemplar." ACL 2019. https://aclanthology.org/P19-1599/
- "Syntax-Guided Controlled Generation of Paraphrases" (SGCP).
  https://arxiv.org/html/2005.08417

**Lexical substitution**
- Zhou, W. et al. "BERT-based Lexical Substitution."
  https://www.semanticscholar.org/paper/BERT-based-Lexical-Substitution-Zhou-Ge/40448ec376e3bc6f706f51bfc30a4a4cc0e7b43b
- Michalopoulos, G. et al. "LexSubCon: Integrating Knowledge from Lexical
  Resources into Contextual Embeddings for Lexical Substitution."
  https://arxiv.org/pdf/2107.05132
- "ParaLS: Lexical Substitution via Pretrained Paraphraser."
  https://arxiv.org/pdf/2305.08146
- "A Comparative Study of Lexical Substitution Approaches based on Neural
  Language Models." https://arxiv.org/abs/2006.00031

**Sentence simplification**
- "Data-Driven Sentence Simplification: Survey and Benchmark." MIT Press
  Computational Linguistics. https://direct.mit.edu/coli/article/46/1/135/93384/
- "Automated Text Simplification: A Survey." ACM Computing Surveys 54(2).
  https://dl.acm.org/doi/10.1145/3442695
- "Controllable Text Simplification with Explicit Paraphrasing." NAACL 2021.
  https://aclanthology.org/2021.naacl-main.277/

**Semantic preservation & evaluation**
- "SBERT studies Meaning Representations: Decomposing Sentence Embeddings
  into Explainable Semantic Features." AACL 2022.
  https://aclanthology.org/2022.aacl-main.48/
- "Sentence Smith: Controllable Edits for Evaluating Text Embeddings."
  https://arxiv.org/pdf/2502.14734
- "A Call for Standardization and Validation of Text Style Transfer
  Evaluation." https://arxiv.org/pdf/2306.00539

**Controlled/constrained generation**
- "A Simple Recipe for Lexically Constrained Text Generation." INLG 2024.
  https://aclanthology.org/2024.inlg-main.1.pdf
- Lu, X. et al. "NeuroLogic A*esque Decoding: Constrained Text Generation
  with Lookahead Heuristics." NAACL 2022. https://arxiv.org/abs/2112.08726
- "Controllable Text Generation for Large Language Models: A Survey."
  https://arxiv.org/abs/2408.12599
- Mallinson, J. et al. "FELIX: Flexible Text Editing Through Tagging and
  Insertion." Findings of EMNLP 2020.
  https://aclanthology.org/2020.findings-emnlp.111/

**Phoneme-aware NLP / speech accessibility**
- Ghai, B. "Fluent: An AI Augmented Writing Tool for People who Stutter."
  ACM ASSETS/SIGACCESS 2021. https://arxiv.org/abs/2108.09918 ·
  https://github.com/bhavyaghai/Fluent
- "PANCETTA: Phoneme Aware Neural Completion to Elicit Tongue Twisters
  Automatically." https://arxiv.org/pdf/2209.06275
- "SEP-28k: A Dataset for Stuttering Event Detection From Podcasts With
  People Who Stutter." https://arxiv.org/pdf/2102.12394
- "A Survey of Grapheme-to-Phoneme Conversion Methods."
  https://www.mdpi.com/2076-3417/14/24/11790
- "The articulatory basis of phonological error patterns in childhood
  speech sound disorders." Frontiers in Human Neuroscience, 2025.
  https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2025.1635096/full

**Clinical / speech-language pathology literature on avoidance**
- SAGE Encyclopedia of Human Communication Sciences and Disorders,
  "Circumlocution and Avoidance in Stuttering."
  https://sk.sagepub.com/ency/edvol/the-sage-encyclopedia-of-human-communication-sciences-and-disorders/chpt/circumlocution-avoidance-stuttering
- ASHA Practice Portal, "Stuttering, Cluttering, and Fluency."
  https://www.asha.org/practice-portal/clinical-topics/fluency-disorders/

**Personalized generation**
- "Learning to summarize user information for personalized reinforcement
  learning from human feedback" (PLUS). OpenReview.
  https://openreview.net/forum?id=Ar078WR3um
- "Personalizing Reinforcement Learning from Human Feedback with
  Variational Preference Learning." https://arxiv.org/abs/2408.10075

**Model comparisons**
- Pehlivanoğlu, K. "Comparative analysis of paraphrasing performance of
  ChatGPT, GPT-3, and T5 language models... (ParaGPT)." Expert Systems,
  2024. https://onlinelibrary.wiley.com/doi/10.1111/exsy.13699
- "VTechAGP: An Academic-to-General-Audience Text Paraphrase Dataset and
  Benchmark Models." https://arxiv.org/pdf/2411.04825

**Psycholinguistics of word frequency and speech production**
- "Does word frequency affect lexical selection in speech production?"
  Quarterly Journal of Experimental Psychology 59(10).
  https://www.tandfonline.com/doi/abs/10.1080/17470210600750558
- "Tracking Lexical Access in Speech Production: Electrophysiological
  Correlates of Word Frequency and Cognate Effects."
  https://www.researchgate.net/publication/26740843
