# STAGE_LR_PROPOSAL_REVIEW.md — critical review of `PROPOSAL_LEARNED_REFORMULATION_ENGINE.md`

**Status: the corrections and revised plan below are the current Stage
LR working plan, superseding the original proposal.** Kept as its own
file rather than folded into `LEARNED_REFORMULATION_RESEARCH.md` —
this is a correction of the founding proposal, including a hard blocker
that changes what's plannable next, not a refinement of one already-
settled matter. `LEARNED_REFORMULATION_RESEARCH.md`'s scope section
points here for the "why."

Every claim below was checked directly against the live repository
(`reformulate.py`, `difficulty_profile.py`, `users/default.json`,
installed packages, `ROADMAP.md`/`DECISION_LOG.md`), not evaluated from
the proposal's own prose. Findings tagged per Practice.md §5.

## 1. What the proposal gets right

**[ASSESSMENT]**
- **The core thesis is correct and aimed at the right target.** The
  frozen architecture's dominant defect (WRONG_WORD_OR_SENSE) was
  diagnosed as a *ranking* problem, not a generation problem
  (`VALIDATION.md` §53). A learned reward/reranking layer targets
  exactly that, not the generator — the right response to this
  project's own diagnosis, not a generic "add ML" instinct.
- **The reward decomposition reuses already-validated components**,
  not new infrastructure, for three of its four terms: `meaning()` can
  draw on SBERT + MeaningBERT (`semantic.py`) plus the NLI/grammar
  checks from Architecture Gate Step 1; `naturalness()` maps onto
  `contextual_fit_score()` (R33–R37, already wired as a reported
  diagnostic); `phoneme_difficulty()` maps onto `phonetic.py` plus
  Stage LR's Matter 1 decisions (`LEARNED_REFORMULATION_RESEARCH.md`).
- **"Reranker before RL" is the right sequencing** — cheap to validate,
  an expensive mistake caught early rather than after a training run.
  Matches this project's own discipline of gating expensive work behind
  cheap checks (e.g. R21/R22/R23's staged, cost-ordered model
  comparisons before commitment).

## 2. Factual corrections — checked against current code, not the proposal's own citations

The proposal cites `PROBLEM_FORMULATION.md`, which predates Architecture
D′ (2026-08-16) and the UI rewrite. Three claims don't describe the
system as it exists today.

### 2.1 The allowlist claim is false for the live pipeline, not just stale

**[FACT, verified directly]** `grep -n allowlist reformulate.py` — zero
matches. The concept exists only in `grammar.py::SentenceRewriter`, the
comparison-baseline pipeline `app.py` has not called since Architecture
D′ (`DOCS.md`). `users/default.json`'s `difficulty_profile` has exactly
three keys — `sounds`, `words`, `phrases` — confirmed by direct
inspection. No allowlist field exists in the live schema. `DOCS.md`
explains why: the old `preferences`/`custom_replacements` fields were
dropped in the 2026-08-16 refinement once their last UI consumer was
removed.

**[CORRECTION]** §3.2's hard-gate term is not "mirroring an existing
precedent... applied outside the network, same as today." It requires
designing and adding a new schema field that does not currently exist.
Not a blocker, but it must be scoped as new work, not reuse.

### 2.2 `problem_phones` already has a consumer; the proposal's citation is stale

**[FACT]** `PROBLEM_FORMULATION.md` §11.2's "not yet wired to anything"
was true when written; `reformulate.py::_flagged_positions`/
`_trigger_reasons` became a real consumer in the 2026-08-16 refinement.
`phrases`/`phrase_values()` is still genuinely unconsumed
(`ROADMAP.md` R13, still open) — one of the two claims is stale, not
both.

### 2.3 The phrase feature is named but never specified

**[GAP]** §3.1 lists `profile.phrases` as an input but never states how
it becomes a numeric feature. `LEARNED_REFORMULATION_RESEARCH.md`'s
Matter 1 already closed this: concatenated per-word
`full_pronunciation()` sequences, scoped so the resulting phone sequence
never auto-generalizes into a per-word or per-phone claim. Stage LR's
feature extractor must consume that decision directly, not re-open it.

## 3. The load-bearing gap: the data claim does not survive a check

**[FACT, this is the consequential finding]** §3.3 claims: *"You already
produce exactly the raw material this needs... reformatting, not fresh
data collection."* Checked directly against what exists in this repo:

| Source | Shape | Size | Checked |
|---|---|---|---|
| `eval/pilot_responses/P1.csv` | Whole-sentence Likert ratings + preference, **one participant** | 20 rated items | `wc -l` |
| `eval/r50_dataset/labeled_dataset.json` | Single-output CLEAN/DEFECTIVE verdicts, **Claude-as-judge**, not human, not pairwise | 135 records | direct read |
| Internal word-substitution candidate pool | Real pairwise candidates, but ranked by `combined_score()` itself | N/A | — |

None of these is `(candidate_A, candidate_B, preferred)` pairwise
preference data at the scale DPO needs. Using the internal candidate
pool's own ranking as ground truth doesn't train a replacement for the
ranking — it distills the current ranking (already diagnosed, §53's
own finding, as the actual source of the WRONG_WORD_OR_SENSE bias) into
a neural net, which cannot clear the freeze's bar by construction.

**[INTERPRETATION]** None of the three sources is "a substantially
larger, independently collected labeled dataset" — the freeze's own
reopening condition (1), `VALIDATION.md` §56. Stage LR is condition
(2)'s work, but its proposed fuel is condition (1)'s exact unmet gap.
"Reformatting, not fresh collection" does not hold against what this
repo actually contains.

**[FACT]** This also breaks §3.4's own evaluation plan before it can
run: *"held-out set must split by speaker profile."* There is currently
**one** profile (`profile_store.py`'s single-default design, multi-user
auth removed 2026-08-16) and **one** pilot participant. The methodology
is correct; the data to run it on does not exist yet.

### 3.1 Directly relevant precedent this project already ran

**[FACT]** Phase 9B/9C (`DECISION_LOG.md` 2026-08-25-B/C) trained a
70M-parameter classifier on a similarly small, similarly-sourced
dataset (51 test records, 6-example CLEAN validation split). On fresh
material (Phase 10): one seed variant predicted DEFECTIVE 99% of the
time (non-functional); the other's CLEAN retention collapsed from 62%
to 34%. This is this project's own, already-measured answer to "what
happens when a learned component this size is tested on genuinely new
material." The proposal does not address this precedent, despite it
being the direct empirical basis for the freeze's own generalization
bar (`VALIDATION.md` §55-56).

## 4. Hardware feasibility — checked, not assumed

**[FACT, verified directly on this machine]**
- `python -c "import torch; torch.cuda.is_available()"` → **False**.
  CPU-only.
- `trl` (the library named for DPO) — **not installed**, not in
  `requirements.txt`.
- `ROADMAP.md` R23 already ran the closest real precedent to Stage 2's
  approach: small decoder-only instruction-tuned models (Qwen2.5-0.5B/
  1.5B) tested against the T5 baseline on this exact CPU-only setup.
  Result: **10–40× slower** than T5 (31–97s/case vs. 2.6s/case) and
  *worse* output quality. That was single-shot inference, not training.
  An RL loop (LoRA fine-tune + PPO/GRPO rollouts — many forward+backward
  passes per update) is categorically more expensive again.

**[INTERPRETATION]** Stage 2 as scoped is very likely not executable on
this hardware in any reasonable timeframe. The proposal does not cost
this out or mention the R23 precedent, which is the project's own
directly relevant data point.

## 5. Revised plan

Keeps what §1 confirmed is right; fixes the gaps §2–§4 found.

### Stage LR.1 — Data reality check (new, hard prerequisite)

Before any training: quantify exactly what pairwise-preference-shaped
data could realistically be produced —
- Reformat Phase 8/8B/9/10/11 corpora into forced-choice pairs via a
  *second* Claude pass judging A vs. B (not reusing single-output
  verdicts as if they were pairs).
- Separately, design a cheap way to collect real multi-profile
  preference data (more than one declared `DifficultyProfile`, more
  than one participant) — §3.4's evaluation plan needs this and it does
  not exist yet.

Output is a number, not a guess — how many real pairwise examples would
exist, from how many distinct profiles. If still small, say so before
training anything, per this project's own disclosure standard
(`VALIDATION.md` §55 named its own thin-sample-size limitation rather
than smoothing over it).

### Stage LR.2 — Feature extractor (buildable now, low risk)

Build the profile-conditioned feature extractor per §3.1, corrected:
SBERT + MeaningBERT + NLI (`semantic.py`) for `meaning()`,
`contextual_fit_score()` for `naturalness()`, `phonetic.py` + Matter 1's
phrase/pronunciation-noise decisions for `phoneme_difficulty()`. No
allowlist term yet — either design it as new schema work with its own
justification, or drop it from v1 and rely on the existing hard NLI/
grammar checks. Produces an inspectable scoring function, not a trained
model — reuses only validated components, testable against Matter 1's
guardrails directly. Not gated on LR.1's result.

### Stage LR.3 — Reranker validation

Only if LR.1 finds enough real pairwise, multi-profile data to make a
held-out-by-speaker split meaningful. If not (the likely outcome given
§3's findings), name this explicitly blocked on data — the same honest
move this project already made for `word_difficulty()`'s weights
(`ROADMAP.md` R2) — rather than training on what's available and
risking a repeat of §3.1's Phase 9B/9C outcome.

### Stage 2 (generative RL) — on hold, not rejected

Not scoped in detail until either (a) GPU access exists, or (b) a
cheaper proxy is validated first — e.g. whether a *frozen*, non-fine-
tuned small model can be steered by the LR.2 reward at inference time
(rerank/rescore only, no training) before committing to a training run
this hardware cannot obviously run.

## 6. Where the original proposal's author agreed, verbatim reasoning kept for the record

Per Practice.md §5's discipline of recording reasoning, not just
conclusions: the proposal's own author, on reviewing this document,
confirmed the allowlist and data claims were stated as settled fact
without checking the live code first, agreed the Phase 9B/9C precedent
was the most important miss, and endorsed the revised plan's structure
(LR.1 as a hard prerequisite that converts the false data claim into a
measurement; LR.2 as low-risk and worth doing regardless of LR.1's
result; Stage 2 genuinely on hold rather than quietly scoped around the
hardware gap) — recorded here so this isn't read as a one-sided
critique the original proposal never had a chance to respond to.
