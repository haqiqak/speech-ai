# VALIDATION.md — Living evaluation record

Per Practice.md §16, every real evaluation run belongs here with its
exact config, dataset/profile version, git commit, and timestamp. As of
the original review (2026-08-08), no entry in this file was a completed,
pre-registered (§8) evaluation result — §1-5 below is that original,
honest inventory of the evaluation *machinery* that existed, what it
covered, and — most importantly per §12 — what it did not. **§6
(2026-08-16) is the first entry in this file reporting an actually-
executed evaluation run** — read it for what has genuinely been
measured; read §1-5 for what still hasn't.

## 1. What evaluation machinery currently exists

| Component | What it measures | Nature |
|---|---|---|
| `eval/metrics.py` | Meaning preservation, difficulty-onset reduction, substitution rate, λ trade-offs | Computed entirely from SBERT similarity, Zipf frequency, and the hand-picked difficulty formula |
| `eval/profile_eval.py` | AUC comparison: self-report-only vs. observed-only vs. fused difficulty profile | Uses the profile's own onset-risk scores as both the model and (implicitly) the target — see §2 below |
| `eval/study/collect.py`, `counterbalance.py`, `stats.py` | Scaffolding for a counterbalanced, three-condition **human** study | This is the one piece of machinery in the repo aimed at the *real* outcome (§12) rather than a proxy. **Observation, not confirmed**: this review found no evidence in the repo of this harness having been run against real participants — the files exist as scaffolding. This should be verified directly with whoever owns the study, not assumed either way. |
| `tests/smoke.py` | Behavioral regression diff against committed baselines (`tests/baseline*.txt`) | Explicitly documented in its own docstring as a regression net, not an evaluation |
| `tests/threshold_sweep.py` | Sweeps `MIN_SEMANTIC` and reports effect on acceptance | Diagnostic; produced the finding in `DECISION_LOG.md` 2026-06-08-A |
| `tests/evaluate.py`, `tests/roadmap_test.py`, `tests/persistence_test.py` | Various regression/behavioral checks | Not individually audited line-by-line in this pass |
| `tests/app_test.py` | Headless Streamlit UI smoke test | Confirms the app runs end-to-end; not a quality measurement |
| `eval/reformulation_eval.py` + `tests/reformulation_eval_corpus.json` | Three-way comparison: `reformulate.py` vs. `SentenceRewriter` vs. `DifficultyAwareRewriter`, uniform metrics | **Actually run** — see §6. The only entry in this table with an executed, reported result as of this pass. |

## 2. The proxy-metric trap, applied concretely to this repository (§12)

Practice.md §12 names this as the single most important risk in the
methodology, and states the operating rule plainly: **whenever a change
here is validated only against a fast/cheap/offline metric, that must be
stated as an explicit, named limitation — not folded silently into
"improved quality."** Applying that rule to what actually exists today:

- **SBERT cosine similarity** (`semantic.py`) is used as the proxy for
  "meaning/intent preserved." It is not validated against human judgment
  anywhere in this repository, as far as this review found. This is a
  **limitation**, not a settled fact: SBERT similarity between two
  sentences is not the same claim as "a human reader agrees the meaning
  and intent are preserved," and the gap between those two has not been
  measured here.
- **The difficulty formula** (`phonetic.word_difficulty()`:
  `0.4·onset + 0.3·syllables + 0.3·rarity`, plus a plosive bonus; and
  separately, `profiling/profile.py`'s weighted variant:
  `0.45·onset_risk + 0.25·length + 0.20·frequency + 0.10·grammatical_class`)
  is the proxy for "easier for this speaker to say." Neither formula's
  weights have been fitted or validated against real speaker-reported or
  observed disfluency data, as far as this review found — they read as
  engineering defaults, and the `config.yaml` comments do not cite a
  source for them. This is a **named limitation**, exactly of the kind
  §6 asks to be stated precisely rather than swept into "known issues."
- **`eval/profile_eval.py`'s AUC comparison** is the closest thing in the
  repo to validating the profile itself against an outcome — but the
  "outcome" it checks against is (the now-archived) `out_of_scope/profiling/
  detect.py`'s own rule-based disfluency labels, which are themselves a proxy
  (a rule-based labeler,
  not ground-truth clinician or self-report data at the event level for
  most of the pipeline's real users). This is a second-order instance of
  the same trap: the profile is validated against a proxy for the thing
  the profile is trying to predict, not against the thing itself.
- **The one component that does aim at the real outcome** —
  `eval/study/` — is exactly the piece with no confirmed run in the repo
  (see table above). That is the gap Practice.md §12 would flag as
  highest-leverage to close: *"has anything shipped and validated on the
  cheap metric actually been re-checked against the expensive, realistic
  one recently?"* Applied here, the honest answer as of this review is:
  **not that this review could find evidence of.**

## 3. Two axes that must never be collapsed (§10)

Per §10, meaning/intent preservation and difficulty reduction must always
be reported separately, never blended into one "quality" number. Nothing
in the current codebase blends them into a single figure — `eval/metrics.py`
reports meaning preservation and difficulty-onset reduction as distinct
fields, which is consistent with §10's requirement. This is a genuine
**observation in the codebase's favor**, noted so it isn't lost among the
gaps above: the eventual harness's structure is already shaped correctly
for this rule, even though no populated result exists yet.

## 4. Ablation status (§11)

No ablation has been run, as far as this review found. Practice.md §11
names two specific, cheap candidates for this repository once a real
benchmark exists:

1. Does the phoneme-onset gate actually change which candidates get
   accepted, holding the SBERT filter and frequency ranking fixed?
2. Does removing the frequency term from the ranking formula measurably
   change output quality, or is SBERT similarity alone already doing most
   of the discriminating work?

Both remain open (**future work**, §5) — see `ROADMAP.md`.

## 5. Explicit non-findings from this review

To be precise about what this pass *did* and *did not* establish (§13's
discipline applies to a documentation pass too — a null finding is still
a finding):

- This review did **not** run any of the existing eval/test scripts. It
  read them and the code they exercise; it did not execute
  `tests/smoke.py`, `tests/threshold_sweep.py`, or `eval/metrics.py`
  against live data. Any claim above about what these scripts *would*
  report if run is inference from reading the code, not a reported
  result — and is stated as such.
- This review did **not** perform the literature pass called for in §7.
  The specific question §7 names — whether fixed phoneme-onset matching
  is actually the dominant predictor of spoken difficulty for this
  population, versus syllable structure, word length, semantic load, or
  sentence position — remains open and unanswered here. That gap is
  carried forward explicitly in `ROADMAP.md` rather than silently
  dropped.

## 6. Stage 6 — `reformulate.py` evaluation (executed, 2026-08-16)

Unlike every entry above (§1-5, the original 2026-08-08 review, which
explicitly ran nothing), this section reports a **completed, executed**
evaluation run, per §8's pre-registration spirit as closely as a
self-constructed corpus allows: the corpus and methodology were fixed
*before* looking at results (§28's plan, written during Stage 5B, before
`reformulate.py` existed), and every number below comes from one actual
run, not from reading code and inferring what it would do.

**Exact config**, per Practice.md §16: git commit `6360d39`, run
2026-08-16, `DISABLE_DATAMUSE=1`, SBERT `all-MiniLM-L6-v2` (loaded
successfully), T5 `Vamsi/T5_Paraphrase_Paws` (loaded successfully),
`MIN_SEMANTIC=0.85` (default, unchanged). Corpus:
`tests/reformulation_eval_corpus.json` (18 cases). Harness:
`eval/reformulation_eval.py`. Raw output: `eval/reformulation_eval_results.csv`
(54 rows — 18 cases × 3 systems).

### 6.1 Methodology

The corpus covers `REFORMULATION_RESEARCH.md` §17's eight constructed
failure-mode cases (`fm_*`, one split into a two-sentence-sense pair) plus
ten control cases (`ctl_*`): no-flag, single-clean-substitution, a
very-short edge case, a deliberately dense/degenerate profile, a
word-specific-`problem_phones`-only case, a mixed flagged/unflagged
multi-sentence input, a phrase-only profile, a direct antonym-guard probe,
and an informal/misspelled-input case. Every onset/shared-sound claim used
to construct a case (e.g. "researcher/reported/results all onset R") was
verified against `phonetic.onset()`'s live CMU-backed output before being
written into the corpus, not assumed from spelling — see the corpus
file's own `notes` field per case.

`grammar.py::sanitize_input()` ran once per case before all three
systems, exactly as `app.py` does, so all three received identical input
text. Each case's `DifficultyProfile` was translated to each legacy
system's own input shape on a **best-effort-equivalent, not identical**
basis: `sounds` → `stutter_patterns` (`SentenceRewriter`) /
`SpeakerDifficultyProfile.onboarding()` (`DifficultyAwareRewriter`);
`words` → `blocked_words` / `always_replace`. **Phrases and
word-specific `problem_phones` have no equivalent in either legacy
system** — this is a structural capability gap in what those systems can
even be told, not a scoring difference, and one control case
(`ctl_word_specific_pattern_only`) exists specifically to surface it.
`DifficultyAwareRewriter`'s difficulty gating is a **continuous, cold-start-blended**
score (`profiling/coldstart.py::fused_cold_start()`), not a hard
declared-sound veto like the other two systems — seeding it from the same
declared sounds is not guaranteed to produce equally strict behavior, and
this is a real architectural difference between the systems being
compared, not a bug in the translation.

**All three systems were scored with the same metric functions**
(`semantic.semantic_similarity`, a shared flagged-word recovery count via
`reformulate._flagged_word_count`, `naturalness.edit_ratio`) applied
uniformly to each system's own `(input, output)` pair — not each system's
own internal, differently-defined metrics — so differences reflect the
systems, not differing metric definitions.

**[LIMITATION]** Every metric below is an automatable **proxy**
(§28's table, restated): SBERT cosine similarity is not human-judged
meaning preservation; the flagged-word recovery count is not a claim
about what a real speaker would find easier to say; the edit-ratio is not
a claim about perceived naturalness. §6.6 below gives a concrete,
observed case where trusting the proxy would have been actively
misleading — this is not a hypothetical caveat.

### 6.2 Measured results

| System | n | Reformulation rate | Avg. meaning preservation (SBERT) | Avg. difficulty reduction % | Avg. naturalness edit-ratio | Avg. flagged words remaining |
|---|---|---|---|---|---|---|
| `reformulate.py` | 18 | **0.556** | **0.9785** | 55.56% | **0.0682** | 0.944 |
| `SentenceRewriter` | 18 | 0.889 | 0.9381 | **66.30%** | 0.1471 | 0.500 |
| `DifficultyAwareRewriter` | 18 | 0.833 | 0.9292 | 65.56% | 0.1427 | **0.444** |

`reformulate.py` status distribution: `reformulated` 10, `could_not_safely_reformulate` 4, `no_change_needed` 4.

**[FINDING]** `reformulate.py` makes fewer, smaller, safer-by-SBERT
changes than either legacy pipeline: highest meaning preservation (0.979
vs. 0.938/0.929), smallest edits (0.068 vs. 0.147/0.143), but the lowest
reformulation rate (0.556 vs. 0.889/0.833) and the most content words left
flagged on average (0.944 vs. 0.500/0.444). This is a real precision/
recall-style trade-off, not a strict improvement — stated plainly rather
than as "the new engine is better."

**[FINDING]** The category breakdown (failure-mode cases vs. control
cases) shows the same pattern in both subsets (`reformulate.py` avg. sim
0.980 failure-mode / 0.977 control; legacy pipelines 0.92–0.94 in both) —
this is not an artifact of one category dominating the aggregate.

### 6.3 Failure analysis — the four `could_not_safely_reformulate` cases

All four cases where `reformulate.py` reported
`could_not_safely_reformulate` are exactly the four cases that triggered
the T5 restructuring-escalation path (`fm_phoneme_in_many_words`,
`fm_negation_forces_escalation`, `fm_restructuring_needed`,
`ctl_degenerate_dense_profile`) — every substitution-only case in the
corpus succeeded. **[FINDING]** On this corpus, the escalation path's
success rate is 0/4 (0%), not a partial-degradation number — every
triggered escalation produced zero usable candidate and left the sentence
unchanged.

Direct debugging (`_model.generate()` called manually with the exact
`bad_words_ids` `reformulate.py` computes, output token IDs inspected
directly) found **two distinct, separable causes**, not one:

**[FINDING] Cause A — a real, previously undocumented bug: `rephrase.py::_bad_words_ids()`
is case-sensitive, but the words it's given are not.** T5's tokenizer
assigns *different* token IDs to `"researcher"` (id 18658) and
`"Researcher"` (id 3440-class capitalized form) — confirmed directly by
tokenizing both. `_bad_words_ids()` (`rephrase.py:104-120`) only encodes
the word exactly as given (`reformulate.py` passes it lowercased) and a
leading-space variant — never a capitalized form. A controlled repro
(`_model.generate()` called directly with `bad_words_ids` computed from
`{"researcher","reported","results"}`) confirmed the lowercase token never
appears in any of 6 beam outputs, while the capitalized form appears in 5
of 6 — i.e. blocking is real and effective, but only for the exact case
given. This affected 2 of the 4 failing cases
(`fm_phoneme_in_many_words`, `ctl_degenerate_dense_profile`), where
5 of 6 leaked flagged words in the top candidate for
`ctl_degenerate_dense_profile` were exact (case-insensitive) matches to
literally blocked words reappearing capitalized (`Manager`, `Meeting`,
`Morning`, `Printed`, `Report`).

**[FINDING] Cause B — confirms an already-documented limitation
(`REFORMULATION_RESEARCH.md` §24.E) with concrete evidence for the first
time.** `bad_words_ids` can only block exact, named word strings — never
a phoneme class. In `fm_restructuring_needed` and
`fm_negation_forces_escalation`, none of the literally-blocked words
(`struggling`, `strongly`, `stressed`, `stressful`, `strategy`) reappeared
verbatim — `bad_words_ids` worked correctly — but T5's paraphrase
candidates reintroduced the same STR onset via **unblocked, semantically-
related synonyms and inflections** never named in the block list:
`struggling`→`struggled`, `stressful`→`stress`/`stress-stressed`,
`strategy`→`strategies`. This happened because the flagged sound cluster
(STR) is semantically central to the sentence's content — "struggle,"
"stress," and "strategy" are near-synonyms of each other, so *any*
paraphrase that stays close to the original meaning tends to stay close
to that vocabulary too. The phoneme veto correctly rejected every one of
these candidates (this is the safety gate working as designed, not
failing) — the system's behavior (refuse and leave unchanged, rather than
ship a candidate that still contains the flagged sound) was **correct and
safe**, just **not useful** for this class of case.

**[INTERPRETATION]** Cause A is a small, mechanical, low-risk fix (encode
capitalized/title-case variants too). Cause B is not a bug — it's a
structural mismatch between the escalation model's training objective
(preserve meaning, PAWS-style) and this task's actual requirement (avoid
a specific phonetic class while preserving meaning), and is unlikely to
be fully solved by a better implementation of the same blocking
mechanism. Both are stated as findings, not fixed here, per this stage's
explicit no-tuning instruction.

### 6.4 Other observed divergences (not escalation-related)

**[FINDING] Proper-noun protection holds under direct pressure.**
`fm_proper_nouns_technical_terms` explicitly flagged `"johnson"` as a
word and `"t"` as a sound (matching `TensorFlow`'s onset) — all three
systems left `Sarah Johnson`/`TensorFlow` completely untouched, confirmed
by identical output across all three. The `_SUBSTITUTABLE` POS-tag gate
(excludes `NNP`) holds even when the profile actively targets a proper
noun, not just by default indifference.

**[FINDING] The context-dependent-substitution failure mode (§17 row 5)
is empirically confirmed to persist in all three systems, including the
new one.** `fm_context_dependent_substitution` ("He runs the company
every morning before he runs three miles") has two senses of "runs" with
identical POS tags. `reformulate.py`/`SentenceRewriter` produced "He
**works** the company every morning before he **goes** three miles" (two
different picks, since each occurrence is scored as an independent slot —
"works the company" is a somewhat awkward substitute for "manages/runs a
company", though not clearly wrong); `DifficultyAwareRewriter` produced
"He **works** the company ... before he **works** three miles" (the
identical word for both senses — "works three miles" doesn't parse as a
sensible phrase). None of the three systems use sentence context to
disambiguate; this matches `REFORMULATION_RESEARCH.md` §17/§18's own
prediction that this failure mode is **not** solved by Architecture D′,
now with a concrete example rather than a predicted one.

**[FINDING] A pre-existing inflection bug in the retained `grammar.py`
code, surfaced (not introduced) by this evaluation.** In
`fm_multi_sentence_transcript`, `SentenceRewriter` produced "data
**constructionss**" (double-s) substituting for "structures", while
`reformulate.py` — which reuses `grammar.py`'s own `inflect()`/
`_preserve_case()` functions, not a reimplementation — produced the
correctly-inflected "constructions" for the same underlying candidate.
This is an existing defect in `SentenceRewriter`'s own candidate-surfacing
path (not reformulate.py's), found because this is the first time the two
pipelines have been run side-by-side on the same input. Not
investigated further or fixed here — out of scope for a measurement-only
stage — but recorded so it isn't lost.

**[LIMITATION — null result, stated honestly]** `ctl_antonym_guard` did
not actually exercise `semantic.is_known_antonym()`'s rejection path: all
three systems' **top-ranked** candidate for "happy" was "glad" (not an
antonym) in every system, so the guard's presence or absence produced no
observable difference in final output. This corpus case does not
demonstrate the antonym guard doing anything — it demonstrates that, for
this specific word and sentence, no system's top candidate needed
rejecting. A case that actually forces an antonym to the top of the
ranking (not just present in the candidate pool) would be needed to
observe the guard in action; this one doesn't achieve that, and this
report says so rather than implying otherwise.

### 6.5 Verifying the proxy-metric concern directly, not just naming it

**[FINDING] A concrete, observed case where the SBERT proxy would
mislead if treated as ground truth.** `fm_ambiguous_word_noun_sense`
("The gift was a wonderful present.") — all three systems correctly
identified the noun sense (no verb-sense contamination) and all three
substituted "present" → "gift", producing **"The gift was a wonderful
gift."** — a redundant, arguably worse sentence than the original, since
it now repeats "gift" as both subject and complement. SBERT scored this
**0.965** — one of the highest similarity scores in the entire corpus,
across all three systems identically. Nothing in this evaluation's
automated metrics flags this case as worse than the clean cases; a human
reader almost certainly would. This is `REFORMULATION_RESEARCH.md`
§28's "semantic fidelity is a proxy, not a claim" line, and this
project's own Practice.md §12 proxy-metric trap, demonstrated with an
actual corpus result rather than argued abstractly.

**[LIMITATION, restated with evidence]** Nothing in this evaluation
measures **speaker suitability** — whether a real speaker who stutters on
these sounds would find any of these outputs actually easier to say.
Per §28's own table, this is stated as categorically unautomatable, not
as a gap this stage's corpus size or design could have closed. No claim
in this section should be read as evidence toward that question.

### 6.6 Reproducibility

The corpus (`tests/reformulation_eval_corpus.json`) and harness
(`eval/reformulation_eval.py`) are both committed, deterministic given
`DISABLE_DATAMUSE=1` (no live Datamuse network calls) and the pinned
model names above, and produce the same `eval/reformulation_eval_results.csv`
on re-run — verified by running the harness twice and diffing the output
CSV byte-for-byte before writing this section. `SynonymEngine`,
`SentenceRewriter`, and `DifficultyAwareRewriter` instances are created
once and reused across all 18 cases (not per-case), matching how `app.py`
itself caches them, so the comparison reflects realistic warm-instance
behavior rather than fresh-instance startup cost. No profile in this
evaluation is ever `.save()`d — all `DifficultyProfile`/
`SpeakerDifficultyProfile` instances are constructed in-memory only and
never touch `users/`.

### 6.7 What these results tell us — and what they don't

**[INTERPRETATION]** The new architecture's substitution-and-verify path
is working as designed: high meaning preservation, small edits, correct
proper-noun protection, a demonstrated (if narrowly-tested) antonym
guard. The escalation path — the one capability gap Architecture D′ was
specifically built to close (§17's "restructuring beats substitution"
row) — has a 0/4 success rate on this corpus, for two separable reasons,
one a small fixable bug (Cause A) and one a deeper model-choice mismatch
(Cause B). The lower reformulation rate and higher flagged-words-
remaining numbers versus the legacy pipelines are the direct, measured
consequence of this: `reformulate.py` correctly refuses to guess when it
can't verify a change, which is safer but, on this corpus, less
effective than pipelines that don't have (and therefore can't fail) an
escalation stage.

**[LIMITATION]** 18 cases is enough to find and root-cause specific
failure mechanisms, not enough to produce a statistically reliable rate
for how often escalation fails in general usage — the corpus was built to
contain failure-mode-dense cases by design (§17's list), so the 0/4 rate
above should not be read as "the escalation path fails most of the time
in typical use." A corpus of ordinary, non-adversarially-constructed text
would be needed to estimate a realistic escalation-trigger rate and
success rate separately.

**[RECOMMENDATION — proposed, not applied]** Two independent next steps,
consistent with this stage's no-tuning boundary: (1) fix Cause A
(`_bad_words_ids()` case-insensitivity) as a small, low-risk, well-
evidenced bug fix, separate from any architecture change; (2) treat Cause
B as an open research question for the escalation model choice
specifically — `Vamsi/T5_Paraphrase_Paws` was selected in Stage 5 for
being "already proven to run locally," not evaluated against this exact
requirement (avoid a phonetic class while preserving meaning) until now.
Neither is implemented in this stage.

### 6.8 R17 fix verification (executed, 2026-08-16, follow-up)

`ROADMAP.md` R17 (Cause A — `rephrase.py::_bad_words_ids()`'s case-
sensitivity gap) was fixed: the function now encodes each blocked word's
lowercase and capitalized forms (each with and without a leading space),
not just the form passed in. Full record: `DECISION_LOG.md` 2026-08-16-H.

**[FINDING] The fix works correctly at the unit level, confirmed by both
regression tests and a live re-run of the exact repro that found the
bug.** 8 new tests in `tests/rephrase_test.py` (all pass): `_bad_words_ids`
now returns both the lowercase and capitalized token sequences for a word
verified to tokenize differently by case; a leading-space variant of both
forms is still included (no regression there); an already-mixed-case
input word (e.g. `"TensorFlow"`) still has its exact form blocked; two
end-to-end generation tests (`generate_candidates`) confirm a blocked
word does not leak in either a mid-sentence lowercase context or a
sentence-initial capitalized context, for words verified not to have the
alternate-tokenization escape below. The original repro (`"manager"`
sentence, `_model.generate()` called directly) that previously produced
5/6 capitalized-form leaks now produces zero literal leaks of any case,
with genuinely different vocabulary (`"supervisor"`, `"management"`,
`"inspected"`) instead of the flagged words reappearing capitalized.

**[FINDING] The fix did NOT recover any of the 4 `could_not_safely_reformulate`
cases end-to-end.** Re-ran the identical `eval/reformulation_eval.py` /
`tests/reformulation_eval_corpus.json` corpus after the fix. Every
aggregate number is unchanged: `reformulate.py` reformulation rate still
0.556, status distribution still `{reformulated: 10,
could_not_safely_reformulate: 4, no_change_needed: 4}` — the same four
cases (`fm_phoneme_in_many_words`, `fm_negation_forces_escalation`,
`fm_restructuring_needed`, `ctl_degenerate_dense_profile`), byte-identical
final output to the pre-fix run.

**[INTERPRETATION] Why the recovery didn't happen, traced directly, not
guessed:** re-running `rephrase.generate_candidates()` on the
`ctl_degenerate_dense_profile` sentence with the *post-fix* blocking
confirmed zero literal word leaks (matching the isolated repro above) —
but every remaining candidate still failed for one of two other reasons:
(a) the candidate still contained a *different* word sharing the same
flagged phoneme class (`"management"`, `"matinee"` both onset M — Cause
B, unchanged, exactly as predicted), or (b) blocking more of the model's
preferred token paths pushed beam search toward substantially different,
**lower-similarity** paraphrases (observed SBERT similarity 0.49-0.61 on
the post-fix candidates, vs. 0.81-0.91 pre-fix) that now fail the
semantic gate instead of — or in addition to — the phoneme gate. This is
a genuinely new observation, not predicted in Stage 6: **blocking more
token forms doesn't just close the literal-word leak, it also shrinks the
model's usable search space, and the paraphrases that survive the tighter
constraint tend to drift further from the original meaning.** Net effect
on this corpus: the specific failure reason shifted (literal-word-leak →
phoneme-class-match and/or low-similarity), but the outcome (no usable
candidate, sentence left unchanged) did not.

**[LIMITATION]** This means Cause A, while a real and now-fixed bug, was
not the dominant contributor to escalation failures on this corpus — Cause
B (and this newly-observed similarity-narrowing side effect) accounts for
the entire remaining 4/4 failure rate. The R18 (`ROADMAP.md`) research
question — whether a different escalation model or strategy is needed —
remains fully open and, if anything, is now better evidenced: a cleaner
implementation of word-level blocking alone cannot solve this class of
case.

**[RECOMMENDATION — proposed, not applied]** R17 should still be kept —
it is a correct, tested, low-risk fix that closes a real leak and may
matter more on corpora with less phonetically-entangled vocabulary than
this one. But it should not be treated as progress on the escalation
success rate itself; R18 remains the open question that actually gates
further improvement here, and this fix's side effect (tighter blocking →
lower-similarity candidates) is worth keeping in mind if R18 is pursued
by adding still more blocked terms rather than changing the model/
strategy.

**Reproducibility of this follow-up:** same corpus, same harness, same
`DISABLE_DATAMUSE=1`/model versions as §6.1's exact config, run against
the `rephrase.py` fix described in `DECISION_LOG.md` 2026-08-16-H. No
profile touched disk during this run (verified via `git status` on
`users/`).

### 6.9 Escalation-trigger rate on ordinary text (executed, 2026-08-16, follow-up)

§6.7's own limitation said the 0/4 escalation success rate "should not be
read as the escalation path fails most of the time in typical use," since
Stage 6's corpus was built failure-mode-dense by design. This subsection
answers that directly rather than leaving it as a caveat.

**Methodology:** a new corpus, `tests/reformulation_ordinary_corpus.json`
— 36 already-committed, unmodified sentences from `tests/eval_corpus.txt`
(ordinary, not written for this evaluation) plus 6 ordinary multi-sentence
paragraphs (weather, a new job, a recipe, a work report, a museum visit,
a hobby — written for this corpus but not tailored to hit any profile),
crossed against 5 **realistic** profiles designed to represent what a
speaker might plausibly declare — not engineered around any specific
sentence: a light single-sound profile (`/s/`), a moderate two-plosive
profile (`/p/,/b/`), a consonant-cluster profile (`str/pr/bl`), a
words-only profile (five ordinary workplace words), and a mixed profile
modeled directly on the shape of this repo's own real
`users/default.json` (one sound, two words, one phrase). 210
(text × profile) cases, harness `eval/reformulation_escalation_rate.py`,
`reformulate.py` only (the retained legacy pipelines have no escalation
concept, so this question doesn't apply to them).

**[FINDING] Escalation is not rare in ordinary use, and its success rate
there is far higher than Stage 6's corpus suggested.** 72/210 cases
(34.3%) had at least one flagged word under a realistic profile. Of those
72, 44 (61%) were resolved by substitution alone — escalation was never
needed. Of the 270 total sentences processed, escalation triggered for
28 (10.4%) — **and succeeded for 12 of those 28 (42.9%)**, not 0%.

| Profile | Escalations triggered | Escalations succeeded |
|---|---|---|
| `moderate_two_plosive` | 13 | 5 |
| `light_single_sound` | 8 | 2 |
| `consonant_clusters` | 4 | 2 |
| `words_only` | 3 | 3 |
| `typical_mixed` (real-profile-shaped) | 0 | 0 |

**[FINDING] The most realistic profile (modeled on this repo's own real
user data) never reached escalation at all across all 42 texts.** This is
consistent with — and helps explain — Stage 6's result: escalation is
disproportionately triggered by profiles with several onsets or several
declared words at once, which a lightly-populated real profile mostly
isn't, on ordinary (non-adversarial) sentences.

**[FINDING] Concrete examples of both outcomes, for texture beyond the
aggregate:** `"The manager confirmed the schedule this morning."`
(sound=`/s/`) → `"The manager confirmed the **time** this morning."`
(escalation succeeded — clean, natural). `"The chef cooked pasta for the
family."` (sounds=`/p/,/b/`) → `"The chef cooked **spaghetti** for the
family."` (succeeded). `"The student practiced the speech before class."`
(sound=`/s/`) → unchanged, `could_not_safely_reformulate` (two `/s/`-onset
words — `student`, `speech` — and no candidate T5 produced cleared both
the phoneme veto and the semantic gate). `"The company prepared a
practical project plan."` (sounds=`/p/,/b/`) → unchanged, "profile too
restrictive for this sentence" (four `/p/`-onset words in one short
sentence: `prepared`, `practical`, `project`, `plan`).

**[INTERPRETATION]** Stage 6's 0/4 was a real, correctly-measured result
on the corpus it used, but that corpus was constructed specifically to
stress-test the escalation path (§17's failure modes), and this follow-up
confirms it does not generalize to ordinary usage. On ordinary text with
realistic profiles, escalation is a real but secondary path (triggered
for roughly 1 in 10 sentences that reach `reformulate.py` under a
moderately-populated profile, essentially never under a lightly-populated
one) and it succeeds close to half the time it's reached — a materially
different picture than "the escalation path doesn't work."

**[LIMITATION]** This still isn't a claim about speaker suitability, and
5 profiles × 42 texts is a sample, not a census — a different set of
realistic profiles or a different sentence source could shift these
percentages. It also doesn't resolve R18 (Cause B): the 12 successes are
still just successes at clearing the SBERT/phoneme gates, not evidence
that a real speaker would find the restructured sentence easier to say.
What it does establish is that Cause B, while real (`fm_restructuring_needed`
and `fm_negation_forces_escalation` in Stage 6's corpus remain genuine,
reproducible failures), is not universal — it dominates specifically when
several instances of the same onset are semantically load-bearing in one
sentence, a real but not typical condition in ordinary text.

**[RECOMMENDATION — proposed, not applied]** R18 is still worth
investigating (the failure mode it names is real and reproducible), but
this result lowers its urgency relative to other open items —
`ROADMAP.md` R9 (wiring the review UI's keep/revert signal into the
profile) or the still-never-run human-judgment study are no longer
obviously lower priority than R18 by comparison. That prioritization
call is left to the next planning step, not decided here.
