# Stage LR — Closeout Report (as of 2026-09-10)

**Purpose of this document.** A single, complete account of everything
Stage LR did, found, and concluded, so a decision on how to proceed can
be made from one place instead of reconstructed from `DECISION_LOG.md`'s
full append-only history. This document does not replace that log —
every claim below is traceable to a dated entry there — it summarizes it.

**Status: paused, not abandoned.** Neither of Stage LR's two hard gates
(below) has been cleared. This is a deliberate stopping point to decide
next steps with full information, not a failure requiring immediate
action.

---

## 1. What Stage LR was for, and its two hard gates

Stage LR ("LR" = Learned Reformulation) is the container for condition
(2) of `VALIDATION.md` §56's architecture-freeze reopening clause. The
freeze (ratified 2026-08-28, `architecture-freeze-v1`) named exactly two
conditions under which optimization work on the reformulation pipeline
may resume:

1. **A substantially larger, independently collected labeled dataset** —
   not built the same way (same small Claude-judged corpus, same thin
   per-defect-class samples) as the evidence the freeze itself rests on.
2. **A genuinely different modeling approach**, evaluated against this
   project's own held-out generalization bar *before* being trusted over
   the frozen baseline. That bar exists because of a specific precedent:
   Phase 9B/9C trained a learned defect-validator that looked genuinely
   good on its own held-out test set (65% recall, reproducible across
   seeds, Spearman ρ=0.901 ranking stability) — then, run unmodified on a
   fresh, disjoint corpus in Phase 10, collapsed to predicting DEFECTIVE
   99% of the time. That collapse, not the original Phase 9B/9C result,
   is the source of the "held-out generalization" requirement.

`main` stays the frozen, shipped implementation throughout. Stage LR
work happens only on the `stage-lr` branch. Promotion of any Stage LR
result to `main` was always specified as a separate, later, explicitly
ratified decision — never an automatic merge once something looks better
on a training corpus (`LEARNED_REFORMULATION_RESEARCH.md`, "Relationship
to the frozen baseline").

**Neither gate is cleared as of this report.** Section 6 below explains why.

---

## 2. Path (a): synthetic/templated preference data (opened 2026-08-30, closed same day)

The first approach tried: generate candidate reformulation pairs from
researcher-authored sentence templates and difficulty profiles, judge
them (initially by hand-tuned heuristic, `LR.2`), and use that as
training signal.

**What was built:** `stage_lr/generate_pairs.py`, `stage_lr/features.py`
(a 5-term hand-tuned scoring function — similarity, frequency,
naturalness, grammar, NLI-consistency), `stage_lr/judge_pairs.py`
(Claude-as-judge).

**What was found, in order:**
- The initial 4-term `LR.2` scorer, checked against 58 real preference
  pairs, scored barely above chance.
- Adding a grammar term (5th): still not enough.
- Adding an NLI-consistency term: still not meaningfully above chance.
- **Conclusion:** hand-tuning a heuristic scorer had hit a practical
  ceiling with the generation setup available. This mirrors the exact
  pattern that justified the original architecture freeze (Phase 11D/E/F
  — incremental rule-patching plateauing) and was recognized as such
  rather than continued.

**Decision (2026-08-30):** stop hand-tuning path (a)'s scorer. Establish
**Claude-as-judge** as the standard judging method going forward instead
of a hand-built formula — but explicitly, Claude-as-judge does **not**
substitute for path (b) (real human preference data); it's a judging
method, not a data source. Path (a) was run through one more batch
(batch 4, new profile *shapes*, not new sentences) and then declared at
its practical ceiling for the generation setup used. No further path (a)
investment after 2026-08-30.

---

## 3. Path (b): real human participant preference data (opened 2026-08-30, ongoing in reduced form)

The charter's own "concrete, minimal ask": roughly 10-15 items per
person, about 20 minutes total, from real people with real speech
profiles — the thing path (a) could not substitute for.

**What actually happened, honestly:** scope grew well past that minimal
ask over many rounds — dozens of pairs per profile, across four
participants (`friend_1`, `friend_2`, `friend_3`, and the user's own
profile), harvested one batch at a time via manual chat relay (the
researcher manually shuttling sentences to a real person and their
answers back). This was slow and became the acknowledged bottleneck that
triggered the later infrastructure pivot (Section 4).

**Standing privacy discipline, held throughout without exception:** every
real participant's declared words, sentences, and judgments stayed in
`stage_lr/data/private/` and `stage_lr/data/real_human_pairs.json` /
`claude_only_pairs.json` — all gitignored, never committed, never
included in any document, notebook, or artifact. Several near-miss leaks
of individual declared words into tracked docs were caught by
git-diff scans before committing and fixed by genericizing the text.
This rule was never relaxed.

**Dataset growth trajectory across the manual-relay rounds:**

| n (pairs) | Agreement rate | Distinct participants | friend_1 share |
|---|---|---|---|
| 8 | 87.5% | — | 76% |
| 15 | 86.7% | — | — |
| 17 | 88.2% | — | — |
| 21 | 81.0% | — | 62% |
| 39 | 71.8% | 4 | 46% |
| 109 (final, incl. Claude-only) | — | 46 groups | — |

**A real, precisely-measured finding along the way:** one of the
project's disclosed architecture defects — a false-positive NLI
consistency check — was suspected of contributing to the CLEAN-rate
plateau. It was tested directly (`eval/step3_gencheck_nli_isolation.py`,
`eval/r10_nli_isolation.py`), isolating the deterministic substitution
tier and toggling the NLI gate on/off. Result: **null effect** — 23/23
flips across both reference corpora were blind-judged DEFECTIVE
regardless of whether the NLI gate fired. The bug is real (independently
demonstrated) but does not explain the plateau. This is the kind of
result this project's evidence discipline exists to surface rather than
bury — a defect can be real and simultaneously not be the answer you were
hoping it was.

**A genuine self-correction during this arc:** partway through, a
proposal to reopen the previously-closed "disfluency corpus" idea
(FluencyBank/SEP-28k/UCLASS) was floated as newly relevant — and
immediately retracted on the user's correction that this conflated an
unrelated question (audio disfluency *location*) with the actual
question (text-rewrite *preference*). Logged as a caught regression, not
new information.

**The persistent, never-resolved diversity cap:** across every round of
manual relay, the count of distinct real participants never grew past 4.
Concentration among them improved (friend_1's share dropped from 76% to
46%), but the number of *distinct people* — the thing "15-30+ distinct
profiles" was floated as a rough target for (a figure that, on later
audit, does **not** appear sourced anywhere in the tracked project
record — flagged honestly rather than treated as an established number)
— never moved. This is the single fact that both remaining Stage LR
threads (Sections 5 and 6) trace their limitation back to.

---

## 4. The infrastructure pivot (2026-09-05/06)

**Trigger:** explicit user frustration with the pace of one-at-a-time
manual chat relay, and a direct instruction to stop doing that and build
proper tooling instead, using Claude-only judging wherever a human isn't
strictly necessary.

**What was built, all tested, all committed:**
- `stage_lr/human_test_tool.html` — a pure static, offline, local-only
  HTML+JS batch-judging tool (never to be hosted, per the standing
  privacy rule). Loads a pairs-for-review JSON, lets a participant
  click through A/B/tie for a whole batch, exports results.
- `stage_lr/merge_human_test_results.py` — joins the tool's output with
  the original pairs, reconstructs the human-facing sentence, builds a
  Claude-judgeable payload (explicitly excluding the human's own answer
  from what Claude sees), and logs the merged result.
- `stage_lr/claude_only_pairs.py` — a structurally **separate** data
  track for Claude-only judgments (no `human_preferred` field, tagged
  `source: "real_profile_claude_only"`), so Claude-only volume is never
  confusable with real human-agreement data.
- A real bug found and fixed in the process: `tests/
  stage_lr_ingest_real_human_pair_test.py` had been backing up/restoring
  the **live** `real_human_pairs.json` in place for years of accumulated
  real data, silently invalidating its own exact-count assertions. Fixed
  by isolating tests to a temp directory.

This closed the actual bottleneck the user named (manual relay speed)
without touching the diversity-cap problem (Section 3) — a distinction
made explicit at the time and confirmed still true throughout everything
that followed.

---

## 5. The reranker diagnostic (2026-09-08)

**The pivot that reframed everything.** After the infrastructure work,
a direct instruction to stop getting caught up in documentation and
re-derive the actual objective from first principles — "achieving
sentence reformulation using a learned approach" — using available Colab
GPU access. This produced a reframing: the real learned-approach
opportunity is **selection/ranking** among already-available candidates
(generation is comparatively solved via the frozen pipeline's
phoneme-constrained decoding), not generation itself. This is exactly
what the frozen pipeline's own diagnosis said was its dominant remaining
defect class (`WRONG_WORD_OR_SENSE`, a ranking problem).

**What was built:** `notebooks/reranker_diagnostic.ipynb` — a
cross-encoder pairwise reranker, trained with Phase 9B's corrected
recipe (conservative LR 3e-6, gradient clipping, `adam_epsilon=1e-6`,
NaN-abort safety callback) plus the one fix Phase 9B/9C never had:
**held-out-by-speaker splitting** from the first cell, so no
participant/profile appears in more than one of train/val/test — the
direct, specific fix for the exact failure mode that caused Phase 10's
collapse.

**Result of the one real run (109 rows, 46 groups):**
`test_pred_A_rate: 1.0` — the model predicted "A" for all 7 held-out
test rows regardless of input; `test_accuracy` (0.286) landed exactly on
the trivial majority-class baseline. A clean, textbook reproduction of
the Phase 9C collapse, on a dataset that is if anything *smaller* than
Phase 9's own (109 rows/46 groups here vs. 205 rows there).

**How to read this, precisely — not overclaimed either direction:** the
fixes worked as designed. Training did not diverge to NaN; it correctly
hit a hard data-size wall instead. This is **not** evidence the reranker
approach is unworkable. It is evidence there is nowhere near enough data
yet for this specific diagnostic to say anything past that. The
diagnostic did its job: it told the truth about where the real
constraint is (data volume/diversity), rather than either quietly
failing or producing a falsely encouraging number on too little data.

---

## 6. Generation backbone comparison, rounds 1 and 2 (2026-09-08 to 2026-09-10)

**The question:** with GPU access now available, does swapping the
frozen pipeline's generation backbone (currently `Vamsi/T5_Paraphrase_
Paws`) for a larger, more capable open model change the picture —
independent of the reranker question above?

### Round 1 (12 sentences, one open model)

`notebooks/generation_backbone_comparison.ipynb`'s first run compared
the current default, `flan-t5-base`, and `Qwen2.5-3B-Instruct`. Blind
Claude quality-judging (34 items, no backbone identity revealed) found:

| Backbone | CLEAN rate |
|---|---|
| `flan-t5-base` | 8.3% (safety via deleting the risky clause, not genuine rephrasing) |
| Current production default | 36.4% (consistent with the project's own historical 31-34% plateau — a good calibration signal) |
| `Qwen2.5-3B-Instruct` | 54.5% |

Read at the time as a real, promising signal — explicitly **not** a
conclusion, per direct instruction to expand before treating a 12-sentence
sample as settled.

### Round 2 (86 sentences, 6 backbones — the properly-sized follow-up)

This is where round 1's optimistic read did **not** survive contact with
scale. Two real bugs were caught and fixed in the notebook itself before
this round ran cleanly (wrong `flan-t5-base` repo id causing silent
passthrough failures; a leak-counting bug that counted leaking
*candidates* instead of leaking *runs*) — both found and corrected via
direct hand-verification against the actual pipeline's `phonetic.py`,
not assumed.

**Mechanical hard-safety numbers, final, self-verified run:**

| Backbone | no-clean-candidate rate | any-leak rate |
|---|---|---|
| Current production default | 2.3% (2/86) | 9.3% |
| `flan-t5-base` | **0.0%** (0/86) | 3.5% |
| `microsoft/Phi-3.5-mini-instruct` | 8.1% (7/86) | 10.5% |
| `Qwen2.5-7B-Instruct` | 17.4% (15/86) | 24.4% |
| `Qwen2.5-3B-Instruct` | **31.4%** (27/86) | 38.4% |
| `Qwen2.5-1.5B-Instruct` | **41.9%** (36/86) | 51.2% |

Round 1's Qwen2.5-3B number (8.3% no-clean at n=12) became 31.4% at
n=86 — nearly 4x worse, and the second-worst backbone tested. This is
precisely the outcome a properly-sized sample exists to catch.

**Two further failure modes found, neither caught by the mechanical
leak-checker** (which only scans Latin-script text against blocked
patterns) — meaning the true Qwen failure rate is worse than even the
table above states:

1. **Code-switching to dodge a blocked word.** E.g. (Qwen2.5-3B, blocked
   word "button"): *"Tap and keep pressed on the按钮for five seconds..."*
   — passes the mechanical check (no Latin-script violation) while being
   useless for an English-speaking recipient.
2. **Meta-commentary leaking into the answer text.** Same run:
   *"...(Note: The word 'button' has been replaced with 'tap'... but the
   meaning remains the same.)"* — literally shipped as part of the
   "clean" candidate.

A third, separate finding: on the one sentence in the corpus with a
specific date (Alexander Fleming's birth year, 1881), **both T5-family
models preserved it correctly; all three Qwen sizes corrupted it to
1981.** n=1, not generalized from alone, but consistent with the
controllability pattern above.

**A verification-discipline incident, corrected in the open.** When
asked to show verbatim, run-by-run evidence for these findings, a
hand-transcription of ~86 raw JSON records (done to double-check the
notebook's own reported numbers) produced a *different* count than the
notebook's own output (31/86 vs. 27/86 no-clean for Qwen2.5-3B) — not
because the check logic differed, but because manual retyping at that
scale is inherently error-prone. This was surfaced honestly rather than
silently resolved in whichever direction looked more convincing, and
fixed at the tool level: the notebook was upgraded to print and save the
exact run-IDs behind every count directly from its own live data, plus
two new automated checks for the contamination modes above — so no
future audit of this notebook's output should ever require hand
transcription again. A re-run confirmed the numbers hold (one Qwen2.5-7B
run drifted by exactly one count, consistent with ordinary 4-bit
quantization non-determinism) and caught one thing manual review had
missed: Phi-3.5-mini does have a small amount of meta-commentary leakage
too (2/86), not zero as first (incorrectly) reported — a correction
recorded plainly rather than left standing.

**Verdict against the stated bar** (≥70% CLEAN, zero severe factual
reversals, no material contamination — proposed explicitly so
"genuinely usable" meant something more specific than "beats the
default"): **none of the three Qwen sizes clear it.** The hard mechanical
failure rate alone (17-42%) is disqualifying before quality is even
considered, and the newly-found contamination modes make the real
failure rate worse than reported. Phi-3.5-mini is the one open
decoder-only model that fails *safely* under the hardest constraints
(empty output, not garbage) but still trails both T5 options on hard
mechanical safety. **The current production default remains, on this
evidence, the most balanced of the six backbones tested.**

**What this doesn't mean:** it doesn't mean open decoder-only models are
inherently incapable of this task — it means beam search under an
aggressive multi-pattern constraint is a bad interaction with this
specific decoding setup, at these specific model sizes. A different
decoding strategy (no beam search, or a smaller/differently-tuned
constraint) is a real, distinct, untested next question — not something
this round's evidence rules out, simply something it didn't test.

---

## 7. Git state — confirmed, not asserted

`main` is at commit `d7b11ea` (2026-08-31) — two commits past the
freeze-establishing point, both small, disclosed, freeze-permitted
dependency-restoration fixes (missing `language-tool-python`, missing
`pyinflect`/stray `tensorflow` removed) that changed zero reformulation
algorithm/weight/threshold/gate code, verified by their own diff stats
(only `CHANGELOG.md`/`DECISION_LOG.md` touched).

A full diff between `main` and `stage-lr` (46 files) shows **zero
changes to any frozen pipeline file** — no `reformulate.py`, `rephrase.py`,
`semantic.py`, `phonetic.py`, `engine.py`, `app.py`, or the
`combined_score()` formula anywhere in it. Every changed/added file is
either documentation or genuinely new, additive Stage LR infrastructure.
Nothing has been merged from `stage-lr` into `main` at any point. The
production implementation is exactly what it was before Stage LR began.

---

## 8. Where this leaves the two gates

1. **A substantially larger, independently collected labeled dataset —**
   **not cleared.** Volume grew (8 → 109 rows across the session) and
   concentration improved (friend_1's share 76% → 46%), but distinct
   participant *diversity* — the actual gate — never moved past 4 people
   all session. Both remaining open threads (reranker, any future
   backbone-preference comparison using real data) trace their
   limitation directly back to this one fact.
2. **A genuinely different modeling approach that clears the project's
   own held-out generalization bar —** **not cleared.** The reranker
   reproduced the exact Phase 9C collapse this bar was built to catch
   (data-starved, not disproven as an approach). The generation-backbone
   alternative was tested properly at scale and returned a clear,
   well-evidenced negative result against every open-model size tried.

Both findings are informative, honestly measured, and traceable —
exactly what this arc's evidence discipline was for. Neither clears the
bar. This is a legitimate, evidence-based stopping point, not a dead
end reached by giving up early.

---

## 9. What this report is not

This is not a recommendation to abandon Stage LR permanently, and not a
recommendation for any specific next move — that decision is explicitly
left open, per direct instruction, to be made from this complete picture
rather than mid-stream. It also does not authorize or imply any change
to `main`; per Section 7, none has occurred, and per the charter, none
would be automatic even if a future result cleared a gate.
