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

## 7. `eval/study/` infrastructure verification (executed, 2026-08-17)

§1/§2 flagged `eval/study/` as "scaffolding... no confirmed run," without
having actually executed it. This section reports what happens when it's
actually run against synthetic data — not read, run.

**[FINDING] All three modules execute correctly; no bugs found.**
`counterbalance.assign_conditions()` was run against 7 synthetic
participants × 3 passages and produced a perfectly balanced 7/7/7
condition assignment (21 rows, Latin-square rotation working as coded).
`collect.init_collection_csv()` produces the documented 10-column schema.
`stats.friedman()` was run against synthetic per-condition data (scipy
available in this environment) and returned a real statistic/p-value, not
an error or a silent no-op. Nothing here needed fixing — per this task's
own instruction to fix only genuine infrastructure problems, none were
found, so nothing was changed.

**[FINDING] The real gaps are design gaps, not bugs — two of them.**
(1) `collect.py` is a CSV **schema**, not a collection **instrument** —
there is no code anywhere that presents a stimulus to a participant and
records a response; whoever runs a study still needs an entirely
separate mechanism (paper form, external survey tool, a script that
doesn't exist yet) to actually gather data into this format. (2) The
condition labels (`original`/`generic`/`personal`) are specific to the
pre-`reformulate.py` study design (`rewrite/`'s "generic" vs.
profile-aware "personal" rewrite, June 2026) and don't map cleanly onto
the current three-pipeline landscape (`reformulate.py` vs.
`SentenceRewriter` vs. `DifficultyAwareRewriter`) — the code is generic
enough to accept any condition labels, so this isn't a bug, but a study
run today would need to decide new condition names and what's actually
being compared before this machinery is usable as-is.

**[FINDING] The schema's primary metric cannot be produced by this
repository alone.** `disfluency_count` — the field's own headline metric
— requires a participant to read text aloud and someone/something to
count spoken disfluencies. That's audio-domain data collection, and
audio was explicitly moved to `out_of_scope/` in this module's own Stage
2 narrowing. This repository, by itself, cannot run the study its own
scaffolding's headline metric was designed around. The two other
recorded fields — `ease_likert_1_7` (a self-reported "how easy did this
feel") and `forced_choice_preference` (a reading-based preference
judgment) — do **not** require spoken performance or audio capture, and
remain usable for a text-only pilot within this repo's actual scope.

**[INTERPRETATION]** `eval/study/`'s counterbalancing and stats layers
are solid, reusable infrastructure — the honest blocker to running any
human evaluation was never "is the code broken," it's "there's no
collection instrument, no updated condition design, and the flagship
metric needs data this module can't collect on its own." A **realistic**
human evaluation, scoped to what this repository can actually do, would:
use `ease_likert_1_7` and `forced_choice_preference` only (not
`disfluency_count`); compare text output from the systems actually being
studied now (e.g. `reformulate.py` vs. original, or a specific pairwise
comparison, decided deliberately rather than inherited from the old
schema); and reuse `counterbalance.py`/`stats.py` as-is, since neither
needed a fix. Whether this is small-scale/informal or something larger is
a scope decision for whoever can actually recruit readers — not decided
here.

**[LIMITATION]** This is a verification of the *machinery*, run against
synthetic data. It says nothing about whether a real study using it would
produce a meaningful result — that still depends on a study design and
real participants, neither of which exist yet.

## 8. Stage 7 — human-evaluation pilot: design and infrastructure (built 2026-08-17, revised same day per direct user review; results pending real participants)

Following §7's finding (the machinery works, but has no collection
instrument and no updated condition design), this section records the
actual pilot built on top of it — scoped explicitly as a **pilot**, not a
statistically conclusive study, and evaluating `reformulate.py` alone
(the retained legacy pipelines were already compared quantitatively in
§6 and are out of scope here). **This is the v2 design**, revised after
the user tried the v1 pilot directly (an informal preview via the running
app, not a real pilot response) and asked for more varied sentence
length/register; the full delta is in `DECISION_LOG.md` 2026-08-17-D.

### 8.1 Design

4 participants (fixed, anonymous IDs P1-P4, no connection to the app's
own single-profile system), all rating the **same** 20 curated pairs (not
disjoint sets) — 80 total ratings, chosen specifically so results have
real inter-rater replication (n=4 per pair) rather than a single opinion
per item. Four required questions per pair, plus two optional ones,
asked plainly with no internal scores (SBERT similarity, difficulty
formulas, phoneme decisions, trigger types) ever shown:

1. **Meaning preservation** (1-5): "Does the reformulated sentence
   preserve the meaning of the original sentence?"
2. **Naturalness** (1-5): "How natural does the reformulated sentence
   sound, as something a person would normally say?"
3. **Perceived speaking ease** (5-point comparative, -2..+2): "Compared
   with the original sentence, how easy would you expect the
   reformulated sentence to be to say?" — explicitly framed as judging
   the wording, not the participant's own speech.
4. **Preference**: Original / Reformulated / No preference.
5. **Optional diagnostic tag** (single-select, only meaningful when the
   participant didn't prefer the reformulation): Meaning changed / Sounds
   unnatural / Too much changed / Reformulation does not seem easier /
   **Original sentence itself was confusing or ungrammatical** (added in
   v2, so a broken input isn't misattributed as a `reformulate.py`
   failure) / Other.
6. **Optional free-text comment** (added in v2): "Anything else you'd
   like to explain about this pair?" — for participants who want to say
   more than the fixed options allow.

Both sentences are shown labeled ("Original"/"Reformulated" — necessary,
since questions 1-3 are inherently about the relationship between them,
so blind A/B labeling would make them unanswerable), but **presentation
order is counterbalanced, not fixed**: which pair a participant sees at
which point in their 20, and which sentence appears first on screen, are
both deterministically shuffled per participant (seeded on participant
ID) — real order variation, not just a documented intention, verified in
§8.3.

### 8.2 Pair selection — a deliberate mix of register and length, not a random or uniform sample

v1's 20 pairs were nearly all medium-length, hand-constructed declarative
sentences drawn from Stage 6/the escalation-rate corpus — realistic
enough individually, but too uniform as a set. v2 replaces that with an
explicit four-category mix, chosen because it's closer to how people
actually use this kind of tool (quick short messages most of the time,
occasionally a longer or multi-sentence passage):

- **10 short, single, natural-register sentences** (10-12 words, the
  kind someone quickly types — a text, a note, a quick ask): e.g. "Just
  checking in to see how things are going." → "Just **seeing in** to see
  how things are going." (broken); "He said he would call back but never
  did." → "...**phone** back..." (clean).
- **3 long, complex single sentences** (multi-clause, closer to real
  report/essay prose): e.g. "Although the committee had reviewed dozens
  of proposals..." → "...had **examined** dozens of **ideas**..." (a
  fairly natural full-sentence restructuring).
- **6 multi-sentence passages** (2-3 sentences each), to test whether
  meaning/context survives across sentence boundaries, not just within
  one: e.g. "...Students can now stay until midnight on weekdays. Many
  bring their own snacks and coffee." → "...**Pupils** can now
  **remain**... Many bring their own **eatings** and coffee." (a
  fabricated non-word, "eatings," that passed every automated gate).
- **1 real, public-domain speech paragraph** — Lincoln's Gettysburg
  Address (1863; verified public domain and sourced via `WebSearch`/
  `WebFetch` against two independent archival transcripts on 2026-08-17,
  not quoted from memory), given a profile chosen to produce many
  substitutions across its ten sentences at once (7 changes in the
  version actually selected — see §8.4 on why this number isn't fixed
  run to run). This single item is deliberately weighted heavier in
  content than the other 19, not counted as "one pair of twenty" on
  equal footing — the user's own framing for it.

Every (text, profile) combination was interactively tried against the
live `reformulate.py` engine and only kept if it produced a
`"reformulated"` status — `no_change_needed` and
`could_not_safely_reformulate` cases were excluded outright, since there
is no reformulated candidate to rate in either. The mixture deliberately
includes several clearly-flawed outputs found during this search, not
cherry-picked for success — see §8.2's examples above and the full set
in `eval/pilot_pairs.json` (never shown to participants, kept for the
post-hoc analysis in §8.5).

### 8.3 Infrastructure verification (executed, synthetic data)

`eval/pilot_app.py` (a separate, minimal Streamlit app — not part of
`app.py`) and `eval/pilot_analyze.py` were built, then driven end-to-end
through `tests/pilot_app_test.py` using Streamlit's `AppTest` (matching
this project's established testing convention) with two of the real,
app-selectable participant IDs (P1/P2 — the selectbox only accepts
P1-P4, so a synthetic-only ID can't be exercised through the actual
widget) before any real participant touched it, per this stage's explicit
requirement. All checks passed:

- Exactly 20 rows saved per participant, no more, no less.
- All 20 `pair_id`s distinct per participant, and identical *sets* across
  participants (both rated the same 20 pairs).
- Zero cross-contamination — every row in `P1.csv` tagged
  `participant_id=P1` and likewise for `P2.csv`.
- Presentation order differed between P1 and P2 (confirmed unequal), and
  the first-shown sentence position differed on 7/20 pairs — both
  counterbalancing mechanisms verified to actually vary, not just coded
  to.
- Both "original-first" and "reformulated-first" positions occurred.
- All response values round-tripped through the CSV in their expected
  ranges (1-5, 1-5, -2..2, three-way preference, non-empty timestamp).
- `eval/pilot_analyze.py` correctly loaded all 40 synthetic rows,
  produced a 20-row per-pair summary, and each pair showed exactly 2
  ratings (one per synthetic-run participant) — confirming the collected
  data shape is analyzable without further changes.
- (v2 additions) the free-text comment field round-trips through the CSV,
  and the new "Original sentence itself was confusing or ungrammatical"
  diagnostic tag is recorded correctly when selected.

`tests/pilot_app_test.py` snapshots and restores `P1.csv`/`P2.csv` around
its run (the same pattern `tests/app_test.py` already uses for
`users/default.json`), so it can be re-run safely even after real pilot
data exists. Confirmed via `git status` on `eval/pilot_responses/`
showing no diff after the run. (A real, 4-row `P1.csv` from the user's
own informal preview of v1 was found and cleared before v2's pairs were
generated — its `pair_id`s referred to different sentences under v2's
new item set, so keeping it would have caused the app to skip 4 pairs
for P1 during real data collection; flagged to the user, not silently
discarded — `DECISION_LOG.md` 2026-08-17-D.)

### 8.4 A genuine T5 escalation non-determinism, found and worked around

**[FINDING, disclosed]** While verifying each v2 candidate pair's
stability (re-running it across several fresh Python processes before
committing to it), 4 of the initially-chosen (text, profile) combinations
were found to be truly non-deterministic: identical code and identical
input produced a `"reformulated"` result once, then
`could_not_safely_reformulate` on 2-3 immediately-following fresh-process
trials, with nothing changed in between. The clearest repro: "Because the
printer had been broken for nearly a week..." — reformulated successfully
once, then failed 3/3 times in separate `python -c` launches. Every
affected item involved T5 restructuring escalation; plain
substitution-only items showed no such instability across repeated
trials, in this or any earlier stage's testing.

**[INTERPRETATION]** This points to CPU floating-point non-associativity
in T5's beam search — a property of the underlying inference stack
across process/thread scheduling, not a bug in `reformulate.py`'s own
substitution/verification logic (which stayed fully deterministic
throughout). **Not fixed here** — a fix would mean touching
`rephrase.py`'s generation configuration (e.g. forcing single-threaded,
deterministic BLAS operations), which is out of scope for a pilot-design
task and would need its own verification pass, consistent with this
project's standing rule against unreviewed changes to the reformulation
stack.

**[LIMITATION]** The practical consequence: `eval/pilot_select_pairs.py`
should **not** be re-run to "refresh" `eval/pilot_pairs.json` once real
data collection begins — the specific 20 pairs actually used are the
ones frozen in that committed file (each individually reconfirmed stable
across 2-3 fresh-process trials before being kept), not whatever a fresh
regeneration might produce on a different machine or a different day.
This also means Stage 6's and the escalation-rate corpus's own
"reproducibility verified" claims (§6.6, §6.9) should be read as
verified **for the specific runs reported there**, not as a guarantee
that every individual escalation-triggered case is stable indefinitely —
a narrower, more honest claim than originally stated, surfaced here by
this pilot's extra scrutiny rather than assumed away.

### 8.5 Analysis plan (not yet run against real data)

`eval/pilot_analyze.py` computes, per pair, across the 4 participants:
mean meaning-preservation, mean naturalness, mean speaking-ease,
preference counts, and collected diagnostic tags — then merges each
pair's human ratings against its **already-computed automated metrics**
(SBERT similarity, edit-ratio, trigger type, source) from
`eval/pilot_pairs.json`, and flags pairs where the automated proxy and
human judgment disagree by a material margin (`|SBERT similarity −
normalized human meaning rating| >= 0.25`) — the specific, actionable
output this pilot is *for*: not "did people like it," but "where does
the proxy metric mislead us, specifically."

**Deliberately not reused:** `eval/study/stats.py`'s
`condition_summary()`/`friedman()` assume the old three-condition
(`original`/`generic`/`personal`) design (§7) and don't apply to a
single-system pilot with no condition column — `stats.read_rows()` (plain
CSV loading) is reused directly; the aggregation logic is new, in
`eval/pilot_analyze.py`, matching this pilot's actual schema.

### 8.6 What this pilot can and cannot establish

**[LIMITATION, stated in advance]** n=4 participants, n=4 ratings per
pair. This can surface real, concrete disagreements between proxy metrics
and human judgment (as §8.2 already did qualitatively, before a single
real rating exists, just by reading the selected outputs) and can flag
specific pairs/patterns worth investigating further. It cannot produce a
statistically powered claim about `reformulate.py`'s general quality, and
must not be read as evidence about improved stuttering or articulatory
performance — it evaluates the text reformulation itself, exactly as
scoped in the brief for this stage.

**Not yet done:** the actual 4×20 data collection. §8.1-8.5 record the
design, selection, and verified infrastructure; results will be appended
here (not overwriting this section) once real participants complete the
pilot.

### 8.7 What actually happened: P1's real v2 run, and a real UI bug it found

**[FINDING]** The user ran the v2 pilot themselves as P1 and completed
all 20 pairs — the first genuine human-judgment data this project has
collected; every prior evaluation stage (§1-§7) was automated/proxy-based.
Headline: meaning preservation 4.65/5, naturalness 4.70/5, speaking ease
+1.75 (of a possible +2), preference for the reformulated sentence on
19/20 pairs, original preferred on 1/20, zero "no preference." Strongly
positive — but n=1, and see the caveat immediately below before reading
too much into it.

**[FINDING] A real UI labeling bug, found by using the app, not by
re-reading the code.** Several of P1's free-text comments describe a
wording flaw as being in "the input," quoting text that was actually
`reformulate.py`'s *output* — e.g. pair_12's comment complains that
"stopped 'using'" is wrong "as input," but "stopped using" was the
reformulated text; the input said "stopped working." Root cause: v2's
UI labeled the two boxes generically "Sentence 1"/"Sentence 2" and put
the actual Original/Reformulated mapping in a separate caption below —
since display position is randomized per pair, "Sentence 1" meant
Original on some pairs and Reformulated on others, and P1 evidently
anchored on "Sentence 1 = input" as a shortcut. Confirmed directly: for
pair_12, the recorded `shown_first` value is `"reformulated"`, i.e.
Sentence 1 genuinely was the reformulated text. The four numeric ratings
sit directly below the caption (more likely answered correctly than a
narrated comment written after the fact) but this can't be fully ruled
out as a source of noise in them either.

**[LIMITATION]** Because of this, P1's free-text comments should be read
as informative but not perfectly attributed — some describe the
reformulated text as if it were the original, or vice versa. The numeric
ratings and preference counts above are the more trustworthy part of
this run. Full raw data preserved at `eval/archive_v2/P1_v2_responses.csv`
(v2's `pilot_pairs.json` also archived alongside it, so the exact text
each `pair_id` referred to at the time is still reconstructable).

**[RECOMMENDATION, acted on]** Per the user's direct review: narrow the
next pilot to short sentences only (long sentences here only changed a
word or two — too little signal per item to be worth participant time),
fix the labeling bug by putting Original/Reformulated directly on each
box, and explicitly scope future human ratings to meaning/naturalness/
ease/preference only — never profile-match effectiveness, which is
answered separately and automatically. All three are implemented in v3
— §9.

## 9. Stage 7 v3 — single-participant, 30-item pilot (built 2026-08-17; results pending)

Rebuilt per the user's direct instructions after reviewing §8.7: single
participant, ~30 short/natural/everyday sentences only, full profile
traceability, participant ratings strictly scoped to meaning/naturalness/
ease/preference (never profile-match effectiveness), and the labeling
bug fixed. `reformulate.py` untouched — this is an evaluation-only stage.

### 9.1 Design

One participant (fixed ID "P1" internally, no selection screen — v2's
4-participant design is retired), rating **30 pairs**, all short single
sentences in an everyday register (requests, apologies, scheduling,
small talk, complaints — authored directly rather than scraped, for the
same copyright-safety reasoning as v2's public-domain-only sourcing
decision for its one long-form item). Same four required questions as
v2 (meaning preservation 1-5, naturalness 1-5, comparative speaking ease
-2..+2, preference) plus the optional diagnostic tag and free-text
comment — those worked fine in v2 and needed no change.

**The v2 labeling bug is fixed**: each box now says "**Original**" or
"**Reformulated**" directly, no "Sentence 1/2" indirection through a
separate caption. Checked directly in `tests/pilot_app_test.py` (the
literal strings are asserted present/absent), not just asserted fixed by
inspection.

**Explicit methodological scope, per the user's direct instruction**:
the participant is never asked, and the ratings are never used, to judge
whether a reformulation successfully avoided its declared difficulty
profile. That question — "did this pair actually resolve what it was
targeting" — is answered automatically from `reformulate.py`'s own
before/after flagged-word count and reported in `eval/pilot_analyze.py`'s
own clearly-separated section, never merged into the human numbers.

### 9.2 Item composition and profile traceability

30 items, split by category to match what a real, lightly-populated
profile actually produces in practice (`VALIDATION.md` §6.9's own
finding that light/moderate profiles dominate real usage, not dense
multi-difficulty ones):

| Category | n | What it tests |
|---|---|---|
| `global_sound` | 18 | A single declared onset (the most common real scenario) |
| `declared_word` | 5 | A specific declared word, not sound-based |
| `word_pattern` | 4 | A word-specific `problem_phones` pattern — the D′-unique capability |
| `multi_difficulty` | 3 | Two declared sounds active in one sentence at once |

Every item was run through the live `reformulate.py` engine (via
`sanitize_input()` first, matching `app.py`'s real pipeline) and kept
only on a `"reformulated"` status. Every item carries, in
`eval/pilot_pairs.json` (never shown to the participant): the exact
declared `profile_spec`, which `triggered_by` reason(s) fired, the exact
word(s) changed and by what mechanism (substitution/restructuring), and
a `profile_match` block stating whether the declared difficulty was
actually resolved (`flagged_words_before` → `flagged_words_after`,
computed automatically). In this build, **30/30 items resolved their
declared difficulty** — expected, since ineligible/unresolved attempts
were filtered out during selection, not a claim about the engine's
general resolution rate (§6/§6.9 already measured that separately, on a
different, larger corpus).

The set again includes genuine, checkable errors rather than only clean
outputs, found during candidate search, not manufactured: "valuable" →
"worth" ("a worth lesson," ungrammatical), "straightforward" → a
restructured "fairly simple to fix" (clean, in the version actually
kept — see §9.4 on why this can vary), "print" → "create" (wrong
action), "driving me crazy" → "going me crazy" (broken), "was late
again" → "was recently again" (broken), "push...grab" → "force...catch"
(meaning drift on both).

### 9.3 Infrastructure verification (executed, synthetic data)

`tests/pilot_app_test.py` drives a full synthetic 30-pair run via
`AppTest` before any real use. All checks pass: exactly 30 rows saved,
30 distinct `pair_id`s, presentation order shuffled (not file order),
both display positions ("original-first"/"reformulated-first") occur,
all response values round-trip through the CSV in range, the free-text
comment and new diagnostic tag are recorded correctly, and
`eval/pilot_analyze.py` correctly loads and summarizes the data —
including its separate profile-match section, confirmed present and
distinct from the human-rating fields for every pair.

**[FINDING] A second, unrelated bug found and fixed during this
verification — in the test harness, not the pilot app or
`reformulate.py`.** The first version of the synthetic driver reused one
long-lived `AppTest` instance across all 30 submit-and-rerun cycles (the
pattern that worked for v2's 20-pair, 2-participant runs) and reliably
crashed partway through with a `KeyError` against a stale widget ID.
Traced to AppTest's own internal widget-tracking state accumulating
corruption after enough sequential `st.form`-submit-triggered
`st.rerun()` cycles — confirmed not an `eval/pilot_app.py` bug by
verifying that creating a **fresh** `AppTest` instance for each pair
(relying on the app's own disk-based resume logic) completes all 30
pairs cleanly and repeatably. `tests/pilot_app_test.py` now uses that
pattern. v2 apparently stayed under whatever iteration threshold
triggers this; v3's 30-in-one-session run crossed it.

### 9.4 A reminder on the T5 non-determinism (still applies, checked for again)

§8.4's finding — T5 restructuring escalation can produce a different
outcome across separate fresh-process runs of identical code and input —
was checked for again here, not assumed fixed: all 8 restructuring-
sourced items in this set were reconfirmed stable across 2 additional
fresh-process trials before being kept (`eval/pilot_select_pairs.py`'s
`_run_item`/`build_pairs`). As with v2, `eval/pilot_select_pairs.py`
should not be re-run to "refresh" `eval/pilot_pairs.json` once real data
collection begins — the 30 pairs actually used are the ones frozen in
that committed file.

### 9.5 What this pilot can and cannot establish

**[LIMITATION, stated in advance]** n=1 participant. This is explicitly
a deeper look with one focused rater, not a replicated-inter-rater
design like v2's (which called for n=4 specifically for that reason).
It can surface concrete, checkable proxy-vs-human disagreements and
qualitative patterns (as §9.2 already did, from reading the outputs
before a single rating exists) but cannot establish inter-rater
agreement or a statistically powered claim. It must not be read as
evidence about improved stuttering or articulatory performance — same
scope boundary as v2, restated because it matters every time this kind
of result gets discussed.

**Not yet done:** the actual 30-item data collection. §9.1-9.4 record
the design and verified infrastructure only; results will be appended
here once the participant completes the pilot.

### 9.6 What actually happened: P1's real v3 run (executed, 2026-08-17)

The participant (P1) completed all 30 pairs. Raw data:
`eval/pilot_responses/P1.csv`. Automated profile-match/metadata:
`eval/pilot_pairs.json`. Analysis run via `eval/pilot_analyze.py` plus
targeted follow-up queries against the same two files. Per §9.1's
methodological scope, the two evidence sources below are kept
strictly separate throughout — human ratings never used as evidence
of profile-match effectiveness, and vice versa.

**Overall human ratings (n=30, 1 rater):** meaning preservation 4.13/5,
naturalness 4.07/5, speaking ease +1.10 (of -2..+2). Preference:
Reformulated 22/30 (73.3%), Original 8/30 (26.7%), No preference 0/30.

**By category:**

| Category | n | Meaning | Naturalness | Ease |
|---|---|---|---|---|
| `declared_word` | 5 | 5.00 | 5.00 | +2.00 |
| `word_pattern` | 4 | 4.75 | 4.75 | +1.50 |
| `global_sound` | 18 | 4.11 | 3.78 | +0.83 |
| `multi_difficulty` | 3 | 2.00 | 3.33 | +0.67 |

**[FINDING] Plain content-word targets (`declared_word`,
`word_pattern`) scored far better than sound-based targets
(`global_sound`), and `multi_difficulty` was the worst category by a
wide margin.** This is not a small effect — `declared_word` is a
perfect 5/5/+2 across all 5 items, while `multi_difficulty` bottoms
out at 2.00 meaning preservation. §9.7 below traces *why*, rather than
stopping at the aggregate.

**[FINDING] Automated profile-match: 30/30 (100%) resolved.** Every
kept item's declared difficulty was actually removed from the output,
per `reformulate.py`'s own before/after flagged-word count. **This
number is not informative on its own** — by construction, only items
that reached `"reformulated"` status were eligible for the pilot at
all (§9.2), so 100% resolution among *selected* items says nothing
about the resolution rate in general use (that question was already
answered separately, and less favorably, in §6.9: escalation succeeds
~43% of the time it triggers on ordinary text). The two numbers must
not be read together as "the system resolves difficulty 100% of the
time" — that would be exactly the proxy-blending error Practice.md §10
prohibits.

### 9.7 Where the automated signal and the human judgment disagreed

**[FINDING] All 9 material disagreements (|SBERT similarity −
normalized human meaning score| ≥ 0.25) ran in the same direction:
SBERT was more optimistic than the human, never the reverse.** No
pair in this dataset had the human rate meaning preservation higher
than SBERT by a comparable margin — checked explicitly, not assumed.
Ranked by gap size:

| Pair | Case | SBERT | Human meaning | Gap |
|---|---|---|---|---|
| pair_28 | md_running_traffic | 0.912 | 1/5 | +0.91 |
| pair_01 | gs_hows_it_going | 0.910 | 2/5 | +0.66 |
| pair_30 | md_print_report_coffee | 0.890 | 2/5 | +0.64 |
| pair_13 | gs_bus_late | 0.867 | 2/5 | +0.62 |
| pair_11 | gs_driving_crazy | 0.968 | 3/5 | +0.47 |
| pair_06 | gs_doctors_appt | 0.954 | 3/5 | +0.45 |
| pair_15 | gs_need_break | 0.908 | 3/5 | +0.41 |
| pair_29 | md_push_meeting_coffee | 0.901 | 3/5 | +0.40 |
| pair_02 | gs_sleep_well | 0.894 | 3/5 | +0.39 |

**[INTERPRETATION] This is a one-directional proxy failure, not
noise.** SBERT cosine similarity, on this dataset, never
underestimates meaning preservation relative to the human rater — it
only ever overestimates it, and by a wide margin in the worst cases
(pair_28: SBERT would call this a near-perfect paraphrase; the human
rated it 1/5). Given §6.5 already found one such case on a different
corpus, this is now confirmed as a repeatable pattern across two
independent evaluation rounds, not a one-off. **[LIMITATION]** 9 cases
is still not enough to characterize the failure precisely (e.g.
whether it's specific to idiom breakage — see §9.8 — or a broader SBERT
weakness), but the direction (never falsely pessimistic) is a specific,
useful, falsifiable claim future work can test against.

**[FINDING] Six of the nine highest-SBERT-vs-human-gap cases involve
breaking a fixed idiomatic or grammatical construction, not a content
error.** "How's it going" (pair_01, "going"→ awkward substitute
mid-idiom), "drives me crazy" (pair_11, causative construction
broken), "was late" (pair_13, adjective→adverb POS mismatch),
"really need... right now" (pair_15, double break inc. the "right"
sense error below), plus the two `multi_difficulty` cases
(pair_28, pair_29/30) which stack two independent substitutions in
one short sentence. SBERT embeddings evidently capture lexical/topical
closeness well but do not penalize idiom/grammar breakage the way a
human reader does — exactly the mechanism, not just the existence, of
the proxy gap.

### 9.8 Cases where the human accepted output despite a real, findable weakness

**[FINDING] A meaning-changing error the human rated as flawless.**
Pair_19: "The meeting got moved to Thursday." → "The meeting**s** were
moved to Thursday." — a singular-to-plural change that alters meaning
(implies multiple meetings, not one rescheduled meeting). Rated
meaning=5, naturalness=5, ease=+2, no diagnostic tag, no comment.
Neither the human rater nor SBERT (the pair passed the 0.85 gate)
flagged this. This is only visible by reading `changes_made` in
`eval/pilot_pairs.json` directly — i.e., **the profile-match/
traceability metadata caught something both other evidence sources
missed**, which is the concrete justification for keeping that
metadata even when human and automated scores agree.

**[FINDING] Cases where the human noticed and named a real flaw but
still accepted the output.** Pair_04 ("forgot" → "missed about that")
— participant's own comment: *"grammer can be checked here, missed
that would be better"* — still rated meaning=5, naturalness=4,
preferred Reformulated. Pair_24 ("valuable" → "worth") — comment:
*"Must be worthy not worth."* — still meaning=4, naturalness=4,
preferred Reformulated. Pair_29 ("push"→"force", "grab"→"catch") —
comment: *"push and force might mean different..."* — still preferred
Reformulated overall (meaning=3, naturalness=4).

**[INTERPRETATION]** These three are methodologically reassuring in
one specific sense (the participant is visibly using the free-text
field to register a real concern rather than defaulting to top marks —
naturalness dipped where grammar was the complaint, not meaning,
showing the axes are being used as designed) but they also show a
**tolerance ceiling**: a single, nameable grammatical defect does not
reliably drag preference to "Original" if the sentence is still
readable and the ease gain is present. Combined with pair_19 above,
the practical implication is that human spot-checking in a pilot of
this size will **undercount** real defects, not just fail to catch
proxy blind spots — a second, independent reason (beyond n=1) to treat
"73% preferred Reformulated" as an upper bound on quality, not a
settled figure.

### 9.9 Recurring failure patterns

**[FINDING] A reproducible word-sense-disambiguation bug: "right now"
(the temporal/immediate sense of "right") is twice substituted using
the wrong WordNet sense.** Pair_15: "right" → "justly" (the
correct/fair sense). Pair_28: "right" → "properly" (also the
correct/fair sense). Both should have used the "immediately" sense.
Found independently in two different sentences under two different
profiles, i.e. not a one-off input quirk — a systematic gap in how
sense is selected for a common, highly polysemous function word.

**[FINDING] A frequency-bias pattern in candidate ranking: generic,
high-frequency verbs are reused as replacements across unrelated
source words, at the expense of fit.** "take" was selected as the
replacement 3 times across different source words in different
sentences (pair_16 "grab"→"take", pair_17 "grab"→"take", pair_30
"grab"→"take"); "going" was selected twice, once as a mediocre
target-word substitute (pair_01) and once as a poor fit for a
causative construction (pair_11, "driving"→"going", breaking "drives
me crazy"). This is consistent with a ranking formula that rewards
high corpus frequency without enough weight on idiomatic/syntactic
fit — the same generic word keeps winning regardless of the specific
sentence it's dropped into.

**[FINDING] The idiom/fixed-construction pattern already named in
§9.7 is the single largest identifiable driver of `global_sound`'s
worse-than-`declared_word`/`word_pattern` category scores.**
`declared_word`/`word_pattern` targets in this set (meeting,
struggling, valuable, comfortable, particular, ridiculous, nice,
instructions) are ordinary content-word slots; `global_sound` targets
are onset-matched regardless of whether the matched word sits inside
an idiom, phrasal verb, or fixed collocation. The onset-based flagging
mechanism has no way to detect "this word is load-bearing for a fixed
expression" versus "this word is a free content slot" — which this
pilot's category-level score gap makes directly visible for the first
time, rather than only a theoretical concern.

### 9.10 An unexpected finding: restructuring outperformed substitution

**[FINDING] Restructuring-escalation-sourced items (n=8) scored higher
than plain substitution-only items (n=22) on every human axis:**
meaning 4.75 vs. 3.91, naturalness 4.50 vs. 3.91, ease +1.50 vs.
+0.95, preference-for-reformulated 87.5% (7/8) vs. 68% (15/22). This
is the opposite of the framing that has held since Stage 6/§6.7 and
`REFORMULATION_RESEARCH.md`, where escalation was treated as the
riskier, harder-to-verify fallback path (correctly, on the metrics
available at the time — 0/4 success on the adversarial Stage 6 corpus,
then ~43% success on ordinary text per §6.9).

**[INTERPRETATION, tentative — small n]** A plausible mechanism: T5
restructuring rewrites the *whole* sentence toward a paraphrase and
must pass a full-sentence SBERT gate, whereas single-word substitution
swaps one slot without any check on whether that word is
idiomatically load-bearing (§9.7/§9.9) — so restructuring's failure
mode (reject and leave unchanged, per §6.3's Cause B) may be
systematically *safer for the cases that do ship* than substitution's
failure mode (ship a locally-valid but idiom-breaking single-word
swap). **[LIMITATION]** n=8 restructuring items is too small to treat
this as settled, and every item in this pilot was pre-filtered to
`"reformulated"` status (§9.2) — this cannot speak to restructuring's
*overall* success rate, which §6.9 already measured separately and
lower (~43%). What it does say: **among restructuring attempts that
succeed**, the output quality bar looks higher than substitution's, on
this data. That is a narrower and more surprising claim than "use
restructuring more," and is flagged as a specific hypothesis worth
testing, not a conclusion.

**[FINDING, secondary] The comparative-ease scale was never used
negative, even for flatly rejected pairs.** Ease values observed:
{+1: 13, +2: 10, 0: 7, -1: 0, -2: 0}. Pairs the participant rated
lowest on meaning/naturalness and preferred "Original" (e.g. pair_15,
pair_28) still received ease=0, not a negative value — the participant
apparently reserved negative ease for "actively harder to say than the
original," a higher bar than "this reformulation is bad." **[LIMITATION]**
This may be a genuine ceiling-avoidance pattern worth asking about
directly in a future pilot's instructions, or may simply reflect that
none of these 30 pre-filtered items were actually harder to say than
the original even when otherwise flawed — the data as collected cannot
distinguish between those two explanations.

### 9.11 Assessment: what this evidence supports doing next, and why

Per this stage's own scope (analysis only, no implementation), this is
a **[RECOMMENDATION — proposed, not applied]**, ranked by how directly
the evidence above supports it:

1. **Idiom/fixed-expression detection for `global_sound` substitution
   is the best-evidenced next target.** §9.7 and §9.9 independently
   converge on the same mechanism from two directions (largest
   proxy-vs-human gaps; largest category-score gap), and it is a
   substitution-only problem — `declared_word`/`word_pattern` targets
   don't show it because they're rarely idiom components. This is a
   substitution-ranking/candidate-filtering change, not a model
   swap.
2. **The "right now" sense-disambiguation bug (§9.9) is small,
   concrete, and reproducible twice — a plausible low-risk fix in the
   same spirit as R17**, but should be verified against more than 2
   cases before being treated as a general "right" bug rather than a
   coincidence of this corpus's phrasing.
3. **R18 (escalation model/strategy) should be re-weighted, not
   dropped.** §9.10's finding — restructuring outperforms substitution
   *conditional on succeeding* — is a genuinely new data point that
   complicates §6.9's "lower priority than other items" framing:
   escalation's success *rate* is still the ~43% bottleneck measured
   in §6.9, but its output *quality when it does succeed* now looks
   better than the alternative, which raises the value of improving
   the success rate rather than deprioritizing it.
4. **SBERT similarity should not be trusted as a standalone acceptance
   gate for idiom-adjacent substitutions**, per §9.7's one-directional
   finding replicated across two independent corpora (§6.5, here).
   This doesn't yet point to a specific replacement metric — only that
   the current one has a now twice-confirmed, specific blind spot.
5. **`multi_difficulty` (stacking 2+ substitutions in one short
   sentence) needs its own investigation before scaling it up** — n=3
   is too small to generalize from, but 2.00/5 meaning preservation is
   low enough, and mechanistically explainable (§9.7's idiom pattern
   compounds when two substitutions land in one short sentence), to
   flag rather than ignore.

**[LIMITATION, restated]** All of the above is drawn from n=1
participant × 30 pre-filtered, "successfully reformulated" items. It
is a rich source of *specific, checkable* failure mechanisms (which is
what a small, deeply-instrumented pilot is good for) and not a
statistically powered claim about `reformulate.py`'s general quality
or about real speaker outcomes — restated because every prior section
of this document makes the same point and it would be inconsistent to
drop it here.

## 10. Idiom/fixed-expression guard — implemented and verified (2026-08-17)

`REFORMULATION_PROBLEM_MAP.md` §5 item 1, the highest-evidence item in
that document's implementation plan. Per the user's explicit sequencing
("test it properly on the existing pilot/evaluation corpus and see
whether the human-proxy failures actually decrease" before moving to
item 2), this section reports the implementation and its verification
against real evidence, not just unit tests.

### 10.1 What was built

`semantic.py`: two new curated lists — `IDIOM_PHRASES` (exact multi-word
matches: "how 's it going", "what 's going on", "right now", "right
away", "right here") and `IDIOM_PHRASE_PATTERNS` (a small pronoun-
wildcard mechanism for "drives/driving/drove/drive {pron} crazy",
matching a fixed set of object pronouns). A new `idiom_protected_positions()`
returns just this subset; `protected_positions()` (already the mechanism
`reformulate.py` uses to block substitution at a position — this is not
new machinery, it's the same one `PROTECTED_PHRASES`/stop-words already
used) now includes it. `reformulate.py::_flagged_positions` already
excluded any protected position from being substitutable — that part
required no change.

**A follow-up correctness issue found and fixed while testing the guard
itself, not assumed away:** the first version silently excluded
idiom-protected words from `flagged_words_before`/`flagged_words_after`
entirely, the same way stop words always have been. For a stop word
that's correct — "the"/"is" were never real difficulty candidates. But
an idiom-locked *content* word (e.g. "going" in "how's it going") can
genuinely match a declared sound, and silently excluding it made
`difficulty_resolved: true` misleading — the metric would report success
on a sentence where the speaker's declared difficulty is still sitting
in the output, unaddressed, just no longer visible to the count. Fixed
via a new `_idiom_protected_matches()` in `reformulate.py`: these
positions are still excluded from substitution (correct, unchanged) but
now counted in `flagged_words_before`/`after` and reported in the
`skipped` list with reason `"part of a fixed expression — left unchanged
to avoid breaking it"`, and the sentence's status becomes
`could_not_safely_reformulate` rather than the misleading
`no_change_needed` when the idiom-locked word was the only match.

### 10.2 Verification

**Unit level** (`tests/semantic_test.py`, 12 new tests, no model loading
required): confirms the new idiom lists protect exactly the intended
spans, that pre-existing `PROTECTED_PHRASES`/stop-word behavior is
unaffected, that the pronoun wildcard matches all six pronouns tested and
nothing outside that set, and that none of "going"/"right"/"crazy" are
protected *outside* their specific idiom context (i.e. this is not a
blanket ban on those words).

**Integration level** (`tests/reformulate_test.py`, 3 new tests in
`IdiomGuardTest`, using the exact real pilot sentences, not synthetic
restatements): "how's it going" and "drives me crazy" are left
byte-identical to the original input; "right now" survives even when a
sibling word in the same sentence ("really") is still correctly
substituted — confirming the guard is scoped to the idiom span, not the
whole sentence.

**Full regression suite, run twice — before and after the follow-up
metrics fix**: `tests/reformulate_test.py` (20/20), `tests/semantic_test.py`
(12/12), `tests/app_test.py` (all scenarios), `tests/difficulty_profile_test.py`
(50/50), `tests/roadmap_test.py` (3/3) all pass. `tests/smoke.py` diffed
against both committed baselines (`tests/baseline_sbert.txt`,
`tests/baseline.txt`) — **exactly one intended, isolated change** in each
(a "she is run right now" test sentence's "right"→"properly"/"now"→"today"
substitutions no longer fire, correctly), nothing else shifted; both
baselines regenerated and committed to reflect the new correct behavior.
`eval/reformulation_eval.py` re-run against Stage 6's exact 18-case
corpus — **byte-identical output**, since none of that corpus's text
contains any of the new guard's trigger phrases (confirmed by direct
grep before assuming it, not inferred) — Stage 6's §6.2 numbers stand
unchanged.

### 10.3 Did the human-proxy failures actually decrease? (the diagnostic the user asked for)

New script `eval/idiom_guard_recheck.py` — reads the **frozen** v3 pilot
corpus (`eval/pilot_pairs.json`, never overwritten) read-only, rebuilds
each pair's exact profile from its recorded `profile_spec`, and re-runs
`reformulate()` on the exact original text through the current engine,
diffing against what P1 actually rated. This is a diagnostic re-run, not
a new pilot — `eval/pilot_pairs.json`/`eval/pilot_responses/` are
untouched, consistent with §8.4/§9.4's rule against regenerating a frozen,
already-rated corpus.

**[FINDING] All four pairs the guard targets changed, all in the
intended direction; the other 26 pairs are byte-identical to the frozen
record — zero collateral change.**

| Pair | Case | Old (what P1 rated) | New | Old SBERT | New SBERT |
|---|---|---|---|---|---|
| pair_01 | gs_hows_it_going | "Hey, how's it **taking** today?" | "Hey, how's it going today?" (unchanged) | 0.910 | 1.0 |
| pair_11 | gs_driving_crazy | "The kids are **going** me crazy today." | "The kids are driving me crazy today." (unchanged) | 0.968 | 1.0 |
| pair_15 | gs_need_break | "I very need a break **justly** now." | "I very need a break right now." | 0.909 | 0.965 |
| pair_28 | md_running_traffic | "...stuck in traffic **properly** now." | "...stuck in traffic right now." | 0.912 | 0.937 |

Two of these three pairs from §9.7's worst-9 SBERT-vs-human disagreement
table are now non-issues: pair_01 (was the single largest gap after
pair_28 among global_sound cases at the time, human meaning=2/5) and
pair_11 (human meaning=3/5) no longer produce a broken idiom at all —
the exact wrong output P1 actually rated poorly does not recur. pair_15
and pair_28 (both "right now" cases) keep their other, unrelated
substitution but no longer touch "right now" itself, and their SBERT
similarity moved measurably closer to 1.0 as a direct, mechanical
consequence (fewer/safer edits). **[LIMITATION]** This is not a new
human rating — nobody re-rated these four corrected sentences, so "the
proxy-vs-human gap decreased" is inferred (the SBERT gap driver, the
literal broken idiom, no longer exists in the output) rather than
re-measured with a real participant. That would require a genuinely new
pilot round, out of scope for this diagnostic.

**[FINDING, the honest trade-off — not glossed over]** For pair_01 and
pair_11, the declared difficulty is now **not resolved at all**:
`flagged_words_before`/`after` are both 1 (the idiom-locked word is
still there, unaddressed), and `status` is `could_not_safely_reformulate`
rather than `reformulated`. Before this fix, the engine shipped a
broken sentence but reported the difficulty as resolved; after this fix,
it correctly leaves the sentence alone and correctly reports the
difficulty as unresolved. This is the same "never ship a bad guess"
philosophy `reformulate.py` already applies to substitution/escalation
failures (§6.3's Cause B is the same shape of trade-off), extended
consistently to idioms — not a free win, a disclosed trade of "silently
wrong" for "visibly incomplete."

**Two pairs on §9.7's disagreement list were checked and confirmed
*not* addressed by this guard, rather than assumed fixed**: pair_29
("push"→"force"/"grab"→"catch", a word-choice/frequency-bias issue) and
pair_30 ("print"→"create", a wrong-action substitution) came back
byte-identical to the frozen record — neither is an idiom break, and
this guard was never going to touch them. Correctly out of scope for
item 1; still open.

### 10.4 What this does and doesn't establish

**[RECOMMENDATION, per the user's own sequencing]** This clears the way
to item 2 (word-sense disambiguation) as planned. Note the overlap
already realized: "right now" was on both item 1's (fixed-expression)
and item 2's (word-sense) target lists, and is already fixed here for
its own literal phrase — item 2 should still proceed for the *general*
word-sense problem (any polysemous word, not just "right"), since only
one specific two-instance case has been observed so far
(`REFORMULATION_PROBLEM_MAP.md` §6).

**[LIMITATION]** This section confirms the intended idiom breaks no
longer occur and nothing else regressed — it does not re-establish
`VALIDATION.md` §9's category-level numbers (`global_sound` 4.11/3.78/+0.83
etc.), which would require a new pilot round with fresh human ratings,
not yet run.

## 11. Word-sense disambiguation for candidate generation — implemented, then corrected against real regressions (2026-08-17)

`REFORMULATION_PROBLEM_MAP.md` §5 item 2, the fix for the reproducible
"right" → "justly"/"properly" bug (§9.9). This section is longer than
§10's because the first version, while it fixed the targeted bug,
**introduced two real regressions when tested against Stage 6's
corpus** — caught by exactly the "re-run the evaluation corpus" step
the user asked for, not shipped and found later.

### 11.1 What was built (v1)

`engine.py::_wordnet_synonyms()` crawled every same-POS WordNet synset
for a word and unioned their synonyms — confirmed directly:
`wn.synsets("right", pos=wn.ADV)` returns 9 senses, including
`right.r.02` ("immediately," the correct sense for "right now") mixed
in with `properly.r.01`, `justly.r.02`, `correctly.r.01`,
`mighty.r.01` — no sense selection at all, just POS filtering. Fix:
`semantic.py::disambiguate_synset(word, wn_pos, sentence)` — embeds the
sentence and every candidate synset's WordNet gloss with the SBERT
model already loaded for everything else here (no new dependency, the
small-effort option `REFORMULATION_PROBLEM_MAP.md` §3.2/§4 ranked over
`pywsd`), picks the closest, and `engine.py` gained a `restrict_synsets`
parameter so candidate generation pulls from only that one sense.
Verified directly against real sentences before wiring it in: "He'll be
right over to help." correctly resolves to `right.r.02` ("immediately")
via general context, not the literal "right now" phrase — confirming
this fixes the general word-sense problem, not just one idiom.

### 11.2 Two regressions found by re-running Stage 6's corpus — not assumed away

Per the user's explicit instruction ("re-run the evaluation corpus +
targeted tests"), `eval/reformulation_eval.py` was re-run against the
same 18-case Stage 6 corpus before calling this done. Aggregate numbers
moved in the wrong direction: `avg_flagged_after` 0.9444 → **1.0** (a
declared difficulty that used to get resolved, now sometimes doesn't),
`avg_meaning_preservation` 0.9785 → 0.9703. Diffing the raw per-case
CSV against the pre-change committed file (not just reading the
aggregate) found two distinct, root-caused mechanisms — not one:

**[FINDING] Regression 1 — a candidate can itself be another declared
difficulty.** `fm_multiple_difficult_words` (profile declares both
"reviewed" and "examined" as difficult words, in one sentence): the
old, sense-mixed candidate pool for "reviewed" never ranked "examined"
highly; the new, sense-correct pool did (they're genuinely close
synonyms in the "inspect closely" sense) — and nothing in
`_try_substitution`'s acceptance loop checked whether a candidate
matches one of the profile's *other* declared words. Output:
"reviewed" → "examined", silently reintroducing a declared difficulty
via the replacement itself (`flagged_words_after` 0 → 1). This is
`REFORMULATION_RESEARCH.md` §17's "no interaction modeling" limitation
— already named, now concretely reproduced for the first time, exactly
as this corpus case's own notes predicted ("checks whether the two
substitutions are still handled independently"). Root cause: making
candidate ranking *more* semantically precise made it more likely to
land exactly on another flagged word, not less — a real, counter-
intuitive interaction between item 1/2's fixes and factor 2.7.

**[FINDING] Regression 2 — whole-sentence context can't disambiguate
two occurrences of the same word in one sentence.** `fm_context_dependent_
substitution` ("He runs the company every morning before he runs three
miles.") — `disambiguate_synset` was called with the full sentence as
context for *both* occurrences of "runs," so both got the identical
sense and the identical replacement: "He **passes** the company...
before he **passes** three miles." (SBERT similarity dropped from the
old 0.9475 to 0.8739 — measurably worse than before, on an
already-known-hard case, not a wash). Confirmed by direct debugging
(calling `disambiguate_synset` with each occurrence's actual full-
sentence context showed both resolving to `run.v.29`, "cover by
running").

### 11.3 Fixes, verified independently before re-measuring the corpus

**Fix 1:** `_try_substitution`'s acceptance loop now also rejects a
candidate if `profile.find_word(candidate)` matches — a candidate must
never be one of the profile's *other* declared-difficult words, not
just checked against the global-sound phoneme veto (which it already
was). Verified directly: the exact `fm_multiple_difficult_words`
sentence now produces "reviewed"→"analysed", "examined"→"investigated",
`flagged_words_after` back to 0.

**Fix 2:** `disambiguate_synset` is now called with a small local token
window (`_local_context_window()`, ±6 tokens around the target word's
own position) instead of the whole sentence. Verified directly: the two
occurrences of "runs" now resolve to different synsets
(`run.v.32`/`run.v.29`) and produce different replacements
("accompanies"/"passes"). **[LIMITATION, disclosed rather than
oversold]** "accompanies the company" is still not a great fit for
"manages/runs a company" — WordNet has 40+ verb senses for "run," and
gloss-embedding similarity over a short window doesn't reliably find
the single best one for every case. What this fix demonstrably repairs
is the *structural* bug (both occurrences forced identical), not full
correctness for this already-documented hard case
(`REFORMULATION_RESEARCH.md` §17 row 5, `VALIDATION.md` §6.4) — which
remains open, exactly as previously disclosed, not newly broken.

### 11.4 Re-measured after both fixes

`eval/reformulation_eval.py` re-run again: `avg_flagged_after` back to
**0.9444** (full parity with the pre-WSD baseline — Regression 1 fully
resolved), `avg_difficulty_reduction_pct` back to **55.5556%** (full
parity), `reformulation_rate` and the status distribution unchanged
throughout every version of this work. `avg_meaning_preservation`
settled at **0.9652** — still below the original 0.9785, and this
residual gap is a **[LIMITATION, real and disclosed, not a bug]**: a
handful of remaining cases (e.g. "strong decision" → "forceful" instead
of the old "powerful," "data structures" → the grammatically awkward
"data knowledges" instead of "constructions") are the direct,
mechanical cost of a single-sense candidate pool sometimes being
smaller and lower-scoring than the old sense-mixed pool, even when the
sense selection itself is correct — the same shape of trade-off
§10.3 already disclosed for the idiom guard (Cause B's "blocking more
narrows the search space" finding, §6.8, is the same mechanism again).
Not chased further with additional heuristics in this pass, per this
project's standing rule against tuning without a separate go-ahead.

Full regression suite re-run after both fixes: `tests/reformulate_test.py`
grew from 20 to 23 tests (3 new: general-context "right" sense,
candidate-collision, repeated-word-different-senses — using the exact
corpus sentences that found each bug, not synthetic restatements), one
pre-existing test (`FeedbackTargetsTest`'s sound-attribution case)
updated to use a sentence that reliably still produces a substitution
rather than the now-correctly-escalating "strong decision" one — all
23 pass. `tests/semantic_test.py` (12/12), `tests/app_test.py`,
`tests/difficulty_profile_test.py` (50/50), `tests/roadmap_test.py`
(3/3), `tests/rephrase_test.py` (8/8) all pass. `tests/smoke.py` diffed
against both committed baselines — **byte-identical, zero diff** (none
of that corpus's sentences happen to be sense-ambiguous in a way that
changes the final chosen candidate).

### 11.5 Re-checked against the real pilot corpus, not just Stage 6

`eval/idiom_guard_recheck.py` re-run again (same frozen
`eval/pilot_pairs.json`, still never overwritten) — now 13/30 pairs
differ from the frozen record (up from 4 with the idiom guard alone,
since WSD's effect isn't limited to idiom spans). Read individually
against what `VALIDATION.md` §9.8/§9.9 already documented as human-
identified flaws in this exact data, not just re-measured in aggregate:

**[FINDING] Two of P1's own explicitly-articulated grammar complaints
are now directly fixed.** pair_24: "valuable" → "worth" ("a worth
lesson," which P1's own comment said should have been "worthy") now
produces "worthy" — resolving via the WSD-narrowed candidate pool
finding a synonym the old mixed pool ranked lower. pair_04: "forgot" →
"missed about that" (P1's comment: "missed that would be better") is
now left completely unchanged (`could_not_safely_reformulate`) — the
sense-correct candidate pool for "forgot" in this context has no
member that clears the SBERT gate, so it correctly refuses instead of
shipping the ungrammatical guess.

**[FINDING] The "generic overused replacement" pattern (`VALIDATION.md`
§9.9) partially improved.** pair_17 "grab coffee" → "take coffee" (one
of three "take" instances flagged as a frequency-bias pattern) is now
"get coffee" — more idiomatic. pair_30's second clause similarly moved
"take" → "get." Not a targeted fix for that pattern — a side effect of
sense-correct ranking surfacing a better-fitting word.

**[FINDING] Not everything is fixed, and this section says so
explicitly.** pair_13 ("was late" → "was recently," an adjective-for-
adverb POS mismatch — `VALIDATION.md` §9.9's idiom-adjacent pattern,
not a sense problem) is still broken ("was belatedly" now — different
wrong output, same underlying bug, unaffected by WSD, exactly as
expected since this is a different failure class). pair_29 ("push the
meeting" → "urge the meeting") remains a poor fit — "push [a meeting]"
meaning "postpone" is itself a phrasal-verb idiom, the same general
class of problem as §10's idiom guard but not on that guard's curated
list (verb+object idioms weren't in scope for the specific phrases
found in the pilot). pair_30's first clause ("print" → "copy") is still
a wrong-action substitution, not resolved.

### 11.6 What this does and doesn't establish

**[RECOMMENDATION]** Per the user's own sequencing, this clears the way
to deciding on item 3 (T5 constrained generation) based on whether
remaining failures justify it — §10.3/§11.5 together suggest the
higher-leverage remaining gaps are: idiom classes not on the curated
list (phrasal-verb objects like "push the meeting"), and POS-mismatch
substitutions (pair_13's class) — neither of which item 3 (constrained
generation for T5 escalation specifically) directly addresses, since
both occur in the *substitution* path. Worth naming plainly rather than
assuming item 3 is next just because it's next on the original list.

**[LIMITATION]** Same caveat as every pilot-adjacent section in this
document: `eval/idiom_guard_recheck.py`'s comparisons are against
already-collected human ratings for the *old* outputs, not new ratings
of the corrected ones — "this looks better" is this project's own
judgment reading the text, not a re-measured human score. A new pilot
round would be needed to confirm these corrections actually move the
`VALIDATION.md` §9 category numbers, not assumed here.

### 11.7 The candidate-pool-shrinkage cost, confirmed at scale (not just Stage 6's 18 cases)

§6.9's 210-case ordinary-text/realistic-profile corpus
(`eval/reformulation_escalation_rate.py`) was re-run after both WSD
fixes, to check whether §11.4's "smaller candidate pools" cost is a
Stage-6-corpus artifact or a real, general effect. **It's general.**

**[FINDING] WSD measurably increases how often substitution needs to
escalate, at the same downstream escalation-success rate.** Sentences
where escalation triggered: 28/270 (10.4%, §6.9's original number) →
**38/270 (14.1%)**. Escalation success rate once triggered: 42.9% →
42.1% (essentially unchanged — escalation itself wasn't touched by this
work). 20 of the 210 (text, profile) cases changed outcome, all in the
same direction confirmed at the individual-case level (diffed the raw
CSV, not just the aggregate): a sentence that previously resolved via
plain substitution now needs escalation, because the sense-correct
candidate pool for the flagged word no longer contains a synonym that
clears the SBERT gate on its own (the exact "strong decision" →
"forceful" mechanism from §11.4, now observed to recur across many
different words/sentences at this larger scale, not a one-off).

**[INTERPRETATION]** This directly strengthens §11.6's recommendation:
correcting word sense (item 2) shifts more of the real workload onto
the escalation path, whose *success rate* (still ~42%, unimproved by
this work) is now the more consequential bottleneck than it was before
item 2 existed. Item 3 (T5 constrained generation) is better-justified
now than it would have looked before this measurement — not because
item 2 made anything worse in an absolute sense (the individual
substitutions that do complete are more often sense-correct now), but
because more sentences are passing through the path whose reliability
hasn't been improved yet.

**[LIMITATION]** This is still a proxy-metric comparison (SBERT/phoneme
gates, not human judgment) on a corpus built for realistic-profile
coverage, not statistical power — the exact percentage-point shift
(10.4%→14.1%) should be read as "a real, confirmed direction," not as
a precise number that would replicate exactly on a different sentence
set.

## 12. Diagnostic experiment — does a promptable model with the constraint's reason beat blocklist-only escalation? (executed 2026-08-17)

`REFORMULATION_PROBLEM_MAP.md` §5 item 3 (renumbered from the earlier
draft's item 3 — the item both parallel research passes converged on).
Per the user's explicit instruction: run this diagnostic on the
currently-failing cases, measure success/meaning/naturalness/difficulty-
avoidance/runtime/failure-modes against the baseline, **do not replace
the current engine**, and only proceed to the phrase-level tier if the
result shows a meaningful improvement.

### 12.1 Method

New script `eval/escalation_model_comparison.py`. Failing-case set: every
sentence from the committed 210-case ordinary-text corpus
(`eval/reformulation_escalation_rate.py`) where escalation triggered and
failed in production — **22 real sentences, re-derived directly from
`reformulate.reformulate()`, not hand-picked.** For each: the current
production baseline (`rephrase.generate_candidates`, `bad_words_ids`
only) is compared against `google/flan-t5-base` (247.6M params — chosen
to be comparable in size to the current model, 222.9M params, so any
difference isn't just "a bigger model won") prompted with the flagged
words **and** a natural-language reason derived from the profile (e.g.
*"The speaker stutters on words that start with the sound(s) s, so
those must not appear in the rewrite."*), with no `bad_words_ids` at
all — isolating the effect of explanation from hard blocking. A third,
hybrid condition (flan-t5-base with **both** the reason prompt **and**
`bad_words_ids`) was added after the first result, to test whether the
two mechanisms combine. Every candidate from every condition is scored
by the **exact same three checks** `reformulate.py::_try_escalation`
already applies (SBERT similarity ≥ threshold, `negation_consistent`,
and a post-hoc scan for the flagged sound/words in every content word of
the output) — this is the whole fairness contract of the experiment; no
new or different verification logic was invented for the new model.

### 12.2 Result: a real, robust trade-off — not a clean win, not a dead end

| Condition | Pass rate (n=22) | Avg. best-candidate SBERT sim | Avg. time/case |
|---|---|---|---|
| Baseline (current production) | 0/22 (0%) | 0.8650 | 2.11s |
| flan-t5-base + reason, no `bad_words_ids` | 1/22 (4.5%) | **0.9504** | 2.59s |
| flan-t5-base + reason + `bad_words_ids` (hybrid) | 2/22 (9.1%) | 0.8116 | 2.70s |

Failure-reason breakdown (per-case, best candidate):

| Condition | Leaked the flagged sound | Below SBERT threshold | Passed |
|---|---|---|---|
| Baseline | 14 | 8 | 0 |
| Reason-only | 20 | 1 | 1 |
| Hybrid | 10 | 10 | 2 |

**[FINDING] Reason-based prompting robustly and substantially improves
meaning preservation — this part of the hypothesis is confirmed, not
marginal.** Average similarity jumped from 0.865 to 0.950, and this held
across nearly all 22 individual cases, not a couple of outliers (e.g.
"My friend brought fresh bread to breakfast" → baseline candidate
scored 0.6166, flan-t5's scored 0.9927 for the same sentence). This is
exactly what the literature review (`REFORMULATION_PROBLEM_MAP.md` §3.9)
predicted: not being straitjacketed by token-level blocking lets the
model paraphrase far more naturally.

**[FINDING] That improvement does not translate into passing full
verification, because constraint satisfaction — not meaning
preservation — is the actual bottleneck, and explaining the reason in
prose does not reliably fix it.** Reason-only's failure mode inverted
from the baseline's (mostly low-similarity failures) to almost
entirely leaks (20/22) — a 247M-parameter instruction-following model,
told in a sentence why to avoid certain sounds, mostly does not
reliably apply that as a phonological rule; it produces a fluent,
faithful paraphrase that still contains the flagged sound.

**[FINDING] The hybrid condition doesn't cleanly get the best of both
worlds.** Adding `bad_words_ids` back on top of the reason prompt
recovered some leaks (10 vs baseline's 14) and produced the best raw
pass count (2/22) — but at a similarity cost worse than baseline itself
(0.8116 vs 0.8650). Read together with §6.8's R17-follow-up finding
(tighter blocking pushes the *current* model toward lower-similarity
candidates too), this looks like the same mechanism recurring on a
different, less paraphrase-specialized base model — and flan-t5-base,
despite broader instruction-following training, is not fine-tuned for
paraphrase generation the way `Vamsi/T5_Paraphrase_Paws` is, so it
likely has less headroom to absorb a hard constraint gracefully.

**[FINDING, a genuinely new failure mode, not present in the baseline]**
On the case with the most flagged words in one sentence (4 flagged
words — a dense/degenerate profile case), the hybrid condition produced
`"The speaker stuttered on words that start with s."` — the model
echoed a fragment of its own *instruction prompt* back as if it were
the rewritten sentence, rather than paraphrasing the input at all. This
never happens in the baseline (which has no natural-language prompt to
echo). A concrete, disclosed risk of prompt-based approaches that
blocklist-only approaches don't share.

**[FINDING] A common blind spot across every condition, not just the
new ones.** For several cases (e.g. "researcher measured the **sample**",
"my **sister** started"), every condition — baseline included —
produced only a trivial morphological variant of the flagged word
(singular↔plural), which trivially still shares the flagged onset. None
of the three approaches has any mechanism for recognizing "this word
has few or no real synonyms, morphological variation won't help" and
either refusing cleanly or reaching for a genuinely different word
choice (e.g. dropping the word, restructuring around it). This is a
shared limitation, not evidence for or against the new approach.

### 12.3 Robustness check: is model capacity the limiting factor?

Before drawing a final conclusion, the same reason-only and hybrid
conditions were re-run with **`google/flan-t5-large` (783.2M params —
3.5× larger)** on a stratified 8-case subset (reduced beam width for
tractable CPU runtime — this was a robustness check, not a claim of
equivalent statistical power to the full 22-case run).

| Condition | Pass rate (n=8) | Avg. best-candidate SBERT sim | Avg. time/case |
|---|---|---|---|
| Baseline | 0/8 (0%) | 0.8606 | 2.44s |
| flan-t5-**large** + reason, no `bad_words_ids` | 0/8 (0%) | **0.9815** | 8.02s |
| flan-t5-**large** + reason + `bad_words_ids` (hybrid) | 1/8 (12.5%) | 0.8372 | 8.43s |

**[FINDING] The qualitative picture is unchanged at 3.5× the parameter
count, and meaning preservation improved even further.** Reason-only's
average similarity rose to 0.9815 (higher than the base model's 0.9504)
— stronger evidence still for the "prompting helps meaning preservation"
finding — but the pass rate on this sample stayed at 0/8, and the
hybrid pass rate (12.5%) is statistically indistinguishable from the
base model's (9.1%) on samples this small. **This rules out "the model
was just too small to understand the instruction" as the explanation**
for the low pass rate — the constraint-satisfaction gap persists across
a 3.5× capacity range. Runtime cost scaled roughly with parameter count
(≈3.1× slower per case), a real, disclosed resource cost of going
bigger for no corresponding gain in the metric that actually matters
(pass rate).

### 12.4 Verdict: does this clear the "meaningful improvement" bar?

**[RECOMMENDATION, the honest answer, not the hoped-for one]** No.
Neither model, at either size, in either configuration (reason-only or
hybrid), reaches a pass rate anywhere close to usable — 0% to 12.5% on
small samples, against a baseline of 0%. This does not meet the bar the
user set for proceeding to the phrase-level tier investigation, and
that step is correctly **not** started as a result — the plan's own
conditional gate was not met, and this is reported as such rather than
proceeding anyway.

What the experiment *did* establish, and why it wasn't wasted effort:
reason-based prompting has a real, robust, twice-confirmed (at two
model sizes) positive effect on meaning preservation specifically — the
bottleneck is squarely constraint satisfaction, not fluency or fidelity.
That reframes the next planned step (`REFORMULATION_PROBLEM_MAP.md` §5,
constrained beam search / `force_words_ids`) usefully: it should be
evaluated **on the current model first** (as already planned), and if
it meaningfully improves constraint satisfaction there, it is also
worth testing *combined with* reason-based prompting rather than
assuming blocklist-only is the ceiling — this experiment is evidence
that the two mechanisms are not redundant with each other, just that
neither alone (nor the naive combination tested here) is sufficient.

**[LIMITATION]** 22 cases (8 for the large-model check) is enough to
find and characterize failure mechanisms clearly, not enough to
establish a precise pass-rate percentage that would replicate on a
different corpus — consistent with how every other diagnostic corpus in
this document has been scoped and read. Only two model families
(T5-base-scale generic paraphrase vs. Flan-T5 instruction-tuned, both
still T5 architecture) were tested; a decoder-only instruction-tuned
model was not tried and remains an open question, not ruled out by this
result specifically.

## 13. Constrained beam search (`force_words_ids`) — blocked by a dependency issue, not evaluated (found 2026-08-17)

Per the plan's next step after §12 (regardless of §12's own result, this
item was independently justified). `REFORMULATION_PROBLEM_MAP.md` §3.3
described this, based on published HuggingFace documentation, as "small
effort, same library already in use, no new dependency." **That claim
does not hold for this project's actual installed environment, found by
directly testing it, not assumed from documentation.**

**[FINDING] `transformers==5.10.2` (this project's pinned/installed
version) no longer supports constrained beam search through the
standard `model.generate(force_words_ids=...)` call.** A minimal smoke
test (`model.generate(..., force_words_ids=[[...]])`) raised:
`ValueError: Constrained Beam Search requires trust_remote_code=True...
it loads https://hf.co/transformers-community/constrained-beam-search`
— the feature has been moved out of the core library into a
community-maintained "custom_generate" repo, loaded dynamically from
the Hub at call time. Retrying with `trust_remote_code=True` (accepting
the new risk that implies — arbitrary code fetched from the Hub at
runtime, a category of risk no other model call in this project takes
on) failed differently: `OSError: transformers-community/constrained-
beam-search does not contain a custom_generate subdirectory with a
generate.py file, can't load the custom generate function` — **the
replacement repo itself does not currently provide a loadable
implementation.** Checked whether the underlying constraint classes
(`DisjunctiveConstraint`/`PhrasalConstraint`) are still directly
importable as a lower-level fallback: they are not present in
`transformers.generation` in this version either — fully removed, not
just hidden behind the new API.

**[LIMITATION]** This is not evidence that constrained beam search is a
bad idea, or that it wouldn't help — nothing about its actual behavior
was measured. It is evidence that **the specific, cheap implementation
path this project's own research pass assumed** (call an existing
`transformers` API, no new dependency) **does not currently exist** in
the installed environment. Making it work would now require one of:
(a) pinning an older `transformers` version that still has this built
in — a real dependency-version decision affecting every other model
call in this project (SBERT, both T5 checkpoints), not evaluated here
for compatibility risk; (b) accepting `trust_remote_code=True` and
waiting for/contributing to the community repo being fixed; (c) hand-
implementing disjunctive constrained decoding directly — a materially
larger effort than "small," closer to the NeuroLogic Decoding route
`REFORMULATION_PROBLEM_MAP.md` §3.3 already separately flagged as
medium-effort with no maintained package.

**[RECOMMENDATION, not decided here]** This item's feasibility rating
(§4's table: "Small") needs to be corrected to reflect this — done in
`REFORMULATION_PROBLEM_MAP.md`. Whether to pursue (a), (b), or (c), or
deprioritize this item, is a real decision with dependency-risk
implications beyond a single diagnostic script's scope — surfaced to
the user rather than decided unilaterally.

## 14. R23 — decoder-only instruction-tuned models vs. the T5 baseline (executed 2026-08-18)

Per direct instruction, after R21 (prompting a comparable-size
encoder-decoder model) and R22 (constrained beam search, blocked): does
a small, decoder-only instruction-tuned model — a genuinely different
architecture family, not just a different checkpoint — do better than
the current T5 escalation path? Explicit constraints, honored
throughout: no change to the installed `transformers` version, no
`trust_remote_code`, no new heavy dependency (plain `transformers` +
`torch`, already installed).

### 14.1 Candidate selection — verified against this environment, not assumed

Two models were chosen and confirmed to actually work here before any
benchmarking: **Qwen2.5-0.5B-Instruct** (494.0M params) and
**Qwen2.5-1.5B-Instruct** (1543.7M params). Both load via
`AutoModelForCausalLM.from_pretrained()` with no `trust_remote_code`
and no authentication — confirmed directly (a plain load-and-count-
parameters smoke test succeeded for both, no gating error, matching
Qwen's own model-card claim that the architecture is upstreamed into
core `transformers`). Other realistic-sounding candidates surfaced by
a web search (Gemma, Llama 3.2) were **not** tested — both families are
gated on Hugging Face (require an accepted license + an authenticated
token), and this project makes unauthenticated requests only; they were
excluded on that basis, not for lack of interest. SmolLM2 was also not
tested, on the strength of a secondary source suggesting it needs
`trust_remote_code` — not independently re-verified, since the two
Qwen sizes already gave a clear, consistent enough signal (§14.3) to
not need a fourth candidate.

### 14.2 Method

New script `eval/escalation_model_comparison_decoder.py`, reusing
R21's case-finding, profile-reason, and verification functions directly
(imported, not reimplemented) — same 22 real currently-failing
escalation cases, same three checks (SBERT similarity threshold,
negation consistency, a post-hoc phoneme/blocked-word leak scan).
Decoder-only models need a different prompting mechanism than T5's
plain text-to-text prefix: a chat-template prompt (system message +
user turn) via `tokenizer.apply_chat_template()`, with the flagged
words and the profile's reason given the same way as R21. A grammar
check via this project's existing (already-optional) LanguageTool
integration was added as a fourth signal, since the user asked for
grammar specifically — **[LIMITATION]** LanguageTool is not available
in this running environment (`grammar._get_lt_tool()` returns `None`,
most likely because Java isn't installed) — every `grammar_issues`
field in the result CSVs is `None`/"n/a," reported honestly rather than
faked or silently omitted from the schema.

**[FINDING] Generation strategy had to be recalibrated for this model
family — beam search and multi-candidate sampling were measured, not
assumed, to be too expensive to use.** A timing probe found `num_beams=4`
took ~106s for one call and `num_beams=2` took ~60s, versus flan-t5-base's
~2.6s/case in R21 — and the resulting candidates, whether from beam
search or temperature sampling, clustered tightly around the same output
regardless of decoding strategy (all still failed the same way). Beam/
sampling search wasn't buying meaningfully different outcomes at this
model's scale, only ~3x the CPU cost, so **greedy decoding (one
candidate) became the default** — a real, disclosed methodological
difference from R21's beam=10-12/k=5 approach, not an oversight.

**[FINDING, a real bug caught before trusting any result]** The first
greedy-decoding pass produced severely degenerate output — the model
repeated fragments of its own instruction prompt in a loop ("The
speaker stutters on words that start with the sound(s) s, so those must
not appear in the rewrite. The speaker stutters on words that start
with the sound(s) s, so...") rather than attempting the task at all.
Root cause: switching from beam search to greedy decoding had dropped
`no_repeat_ngram_size`, a parameter beam search doesn't strictly need
but greedy decoding does to avoid this exact failure mode. Fixed
(`no_repeat_ngram_size=3` plus `repetition_penalty=1.3` added to the
greedy path) and reconfirmed before any result below was recorded — a
methodology bug, not a finding about the model.

### 14.3 Results

**Qwen2.5-0.5B-Instruct (n=8, stratified sample, full run completed):**

| Condition | Pass rate | Avg. SBERT sim | Avg. time/case |
|---|---|---|---|
| Baseline (current T5) | 0/8 (0%) | 0.8606 | 2.39s |
| Qwen2.5-0.5B + reason (no `bad_words_ids`) | 0/8 (0%) | **0.6630** | 30.44s |
| Qwen2.5-0.5B + reason + `bad_words_ids` (hybrid) | 0/8 (0%) | 0.5712 | 31.04s |

Failure-reason breakdown: baseline 5 leaked / 3 below-threshold;
decoder-reason-only 1 leaked / **7 below-threshold**; hybrid 0 leaked /
**8 below-threshold**. **[FINDING] This is the opposite failure pattern
from R21's flan-t5-base result.** Flan-t5 mostly stayed faithful to the
original sentence but leaked the constraint (20/22 leaked, only 1
below-threshold, §12.2). Qwen2.5-0.5B does the reverse: `bad_words_ids`
does successfully suppress literal leaks (0/8 leaked in the hybrid
condition — the mechanism itself works on this tokenizer too), but the
model's own paraphrases drift far enough from the original meaning that
almost every case fails on similarity instead. The bottleneck moved
from "constraint satisfaction" (R21) to "basic faithfulness" (R23) —
a materially different, and worse, failure mode.

**[FINDING] At this size, the model frequently doesn't perform the
requested task at all.** Concrete examples, not paraphrased summaries:
for "The student practiced the speech before class," the model produced
*"The teacher corrected the pronunciation errors made by one of her
students during practice for their presentation at school"* — an
invented scene with a different subject, not a rewrite of the input
(sim 0.506). For "The pilot checked the landing procedure," it produced
*"The speaker stuttered when reading 'pilot' because they were unsure
if there was an 'b' or 's'. So all letters starting with 'p', including
'B,' should be removed"* — confused, self-referential meta-commentary
about the task itself, not an attempt at the sentence (sim 0.446).

**Qwen2.5-1.5B-Instruct (n=2, pilot only — not completed to n=8;
session-length constraints, per direct instruction not to re-run this
experiment further):**

| Condition | Pass rate | Avg. SBERT sim | Avg. time/case |
|---|---|---|---|
| Baseline (current T5) | 0/2 (0%) | 0.8360 | 2.62s |
| Qwen2.5-1.5B + reason (no `bad_words_ids`) | 0/2 (0%) | 0.5682 | **96.69s** |
| Qwen2.5-1.5B + reason + `bad_words_ids` (hybrid) | 0/2 (0%) | 0.5682 | 96.62s |

**[FINDING] 3.1x the parameters bought better task-following but worse
fluency, and much worse runtime — a real trend, even at n=2, not a
coin flip.** Unlike 0.5B, 1.5B did attempt genuine rewrites of the
actual input sentences: *"The person rehearsed their remarks prior to
lecture time"* (for "The student practiced the speech before class")
and *"The person made an unbaked treat to eat at noon"* (for "The baker
prepared a fresh pastry for lunch"). Both avoid the flagged words, but
both read as stilted, over-literal thesaurus-swaps rather than natural
paraphrase — and the second is **factually wrong**, not just awkward: a
"pastry" is baked; calling it "unbaked" changes what the sentence
claims, a meaning error, not a style issue. Runtime rose to ~97s/case,
roughly 3x the 0.5B model's ~31s/case, tracking parameter count.

### 14.4 Verdict

**[RECOMMENDATION]** Decoder-only, at least this family and these two
sizes, is not a better-suited architecture for this task within this
project's actual constraints. It loses to the current T5 baseline *and*
to R21's flan-t5-base candidate on meaning preservation, loses on task-
reliability at the smaller size, and loses badly on runtime at every
size tested (10-40x slower per case than the T5 family for comparable
or smaller parameter counts). This is not primarily a "wrong model"
finding — it points at something structural: causal, autoregressive
decoder-only generation via plain `transformers` on CPU (no
quantization, no `llama.cpp`/GGUF-style optimized runtime) is
substantially more expensive per useful output token than T5's
encoder-decoder path, a toolchain gap this project's own constraints
(no new heavy dependency) don't currently allow closing. A bigger
decoder-only model might narrow the quality gap further (1.5B already
showed that direction relative to 0.5B) but would predictably make the
runtime gap worse, not better — there is no obviously-better size to
try next inside these constraints.

**[LIMITATION]** Only one model family (Qwen2.5) at two sizes was
tested; Gemma and Llama were excluded for being gated, not evaluated
and found wanting. The 1.5B result is n=2, informative for the trend
it shows but not to the same statistical weight as the completed n=8
0.5B run or R21's n=22 run. Neither limitation is expected to reverse
the direction of the verdict, given how large and consistent the
observed gaps are (this is the same read applied to every diagnostic
corpus in this document: enough to characterize a failure mode
clearly, not enough to certify a precise percentage).

**[RECOMMENDATION, not decided here]** The one lever that could
plausibly change this verdict — an optimized, quantized local-inference
runtime (`llama.cpp`/GGUF or similar) instead of plain `transformers`
CPU inference — is a new-dependency decision in the same category as
R22's `transformers`-version question, not a "try another model"
question. Not pursued here; surfaced as a separate, explicit decision
for later, same as R22.
