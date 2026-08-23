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

**What this does not do:** none of A1–A4 individually or in combination
demonstrated recovering anywhere near 74%→low-defect-rate territory on
this evidence. Whether the combined effect gets close enough to justify
staying with the current hybrid, or whether the residual gap after
stacking all three still looks large enough to justify the generation-tier
redesign or fine-tuning-prep track, is the actual decision in front of
you — this document supplies the numbers, not the call.
