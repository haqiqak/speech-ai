# PROPOSAL: A Learned, Profile-Native Reformulation Engine

**Status: superseded by `STAGE_LR_PROPOSAL_REVIEW.md` (2026-08-30). Kept
verbatim (encoding artifacts from the original paste cleaned up only —
em-dashes and § signs, no wording changed) as the historical record of
what was proposed, per this project's discipline of not editing a
record after the fact. Do not treat anything below as the current
Stage LR plan — read the review first.**

Status (original): proposal, not yet built. Grounded directly in
`PROBLEM_FORMULATION.md`'s current schema — this is not a hypothetical
redesign, it targets the actual `DifficultyProfile` object that already
exists in the codebase.

This is a single recommended path, not a menu. The reasoning for
rejecting alternatives is included so the decision doesn't need to be
re-litigated later, but there is one target architecture below.

---

## 1. The one-sentence thesis

**Replace hand-written scoring/ranking rules with a learned reward model
that consumes the `DifficultyProfile` schema directly (sounds, words,
phrases, `problem_phones`) — first as a reranker over existing
candidates, then as the reward signal for RL-training a single
generative model that produces reformulations end-to-end.**

Two models, not three options. Stage 1 produces Stage 2's most critical
ingredient. Nothing built in Stage 1 is thrown away in Stage 2.

---

## 2. Why not go straight to one end-to-end generative model

This has to be addressed first because it's the instinct driving this
whole proposal, and it's *half* right.

The part that's right: hand-written rule stacks don't generalize, and
you've already proven that empirically (the ranking-failure diagnosis).
A single well-trained model should ultimately own generation,
difficulty-awareness, and rephrasing judgment together, rather than
passing partial responsibility between disconnected stages.

The part that needs one correction: phoneme-avoidance is a **hard
constraint**, not a fuzzy preference, and constraints of that kind are
exactly what neural networks are structurally unreliable at satisfying
purely from example pairs — this doesn't improve with more data the way
fuzzy judgment does. Training one model on (sentence, profile) →
(output) pairs and hoping it infers "never reproduce this speaker's
onset-R" from patterns in the training set relocates your original
failure. It doesn't remove it. You'd trade "ranking picks the wrong
candidate" for "the model confidently outputs a sentence that still
violates the profile, with nothing left to catch it."

The fix isn't to avoid end-to-end learning. It's to make sure the model
*receives the constraint as structured input and reward signal*, not as
something it has to reverse-engineer from spelling. That's what makes
Stage 2 below different from a naive fine-tune, and it's why Stage 1 has
to exist — it's where that reward signal gets built and validated before
you bet an RL run on it.

---

## 3. Stage 1 — Profile-conditioned reward/reranking model

### 3.1 What it consumes

This is the concrete engineering win available right now: **the reward
model reads `difficulty_profile` directly — sounds, words, phrases, and
`problem_phones` — instead of going through `stutter_patterns`/
`blocked_words`, the flattened legacy bridge described in §6/§11.2 of
the formulation doc.**

That bridge is documented as lossy on its own terms (the ZH round-trip
bug: `add_sound_from_phones()` building a display string, then
re-deriving ARPAbet from it by spelling guess, failing for phones with
no valid English onset spelling). A model trained against the bridge's
output inherits that lossiness permanently. A model trained against the
schema directly — real ARPAbet sequences, real `problem_phones`
subsets, real per-category structure — never has the bug in the first
place, because it never goes through the spelling-reconstruction step
at all. This is not a side benefit; it's a correctness improvement over
the current production path.

Per-candidate input features, derived straight from the schema:

```
sentence:            original text
candidate:           one reformulation candidate
profile.sounds:      list of onset ARPAbet patterns (global)
profile.words:       list of {value, problem_phones | null}
profile.phrases:     list of declared difficult phrases
allowlist_words:      hard-never-touch list (preferences.allowlist_words)
```

Each candidate word is run through `phonetic.full_pronunciation()`
(already built, CMU-dict-only, `None` for OOV — no fabricated
pronunciations) to get its real ARPAbet sequence, which is checked
against `profile.sounds` (onset match, as the existing engine already
defines "onset" — see §11.1) and against any `problem_phones` on words
in the profile. This reuses existing, tested infrastructure; nothing
here duplicates `phonetic.py`.

### 3.2 What it outputs

A scalar score per candidate, decomposed (not black-boxed) as:

```
score(candidate) = meaning(x, candidate)
                  + naturalness(candidate)
                  − phoneme_difficulty(candidate, profile)
                  − ∞ if candidate touches an allowlisted word
```

The allowlist term is a **hard gate, not a learned weight** — this
mirrors the existing, tested precedent that allowlist always wins over
difficulty flags (`DECISION_LOG.md` 2026-06-08-D). The learned model
should never be given the opportunity to override it; it's applied
outside the network, same as today.

### 3.3 Training data — reuse, don't recollect

You already produce exactly the raw material this needs: every time the
current candidate-generation step ran and a human judged the outputs
("A=bad, B=good, C=bad, D=ok"), that's a labeled preference example. The
task is reformatting, not fresh data collection:

```
(sentence, difficulty_profile snapshot, candidate_A, candidate_B, preferred)
```

Train via **DPO** (Direct Preference Optimization) on these pairs —
one-stage, no separate PPO loop, well-supported (`trl` library
implements it directly). Preference data of this shape is cheap to keep
growing: every future evaluation pass run against the *current* frozen
architecture produces more of it for free, if judgments are captured in
this format going forward rather than as ad hoc notes.

### 3.4 Evaluation — the trap already lived through once

Held-out set must split by **speaker profile**, not by sentence. Testing
on unseen sentences from speakers seen in training tells you the model
memorized that speaker's preferences; it says nothing about
generalization to a new profile, which is the actual product
requirement. This is the same evaluation-dependence failure already
diagnosed in the current architecture — repeating it here would waste
Stage 1 entirely.

### 3.5 Deployment shape at the end of Stage 1

```
Existing candidate generator (unchanged)
        ↓
Learned reward model (new) — scores using difficulty_profile directly
        ↓
Top-ranked candidate
        ↓
Existing deterministic safety gates (NLI, grammar, allowlist) — unchanged
        ↓
Output
```

Only the ranking box changes. Generation and safety stay exactly as
validated. This is deployable and evaluable on its own — it does not
require Stage 2 to ship value, and it de-risks Stage 2 by proving the
reward signal actually works before an RL run is trained against it.

---

## 4. Stage 2 — RL-trained generative model (the "ultimate" model)

### 4.1 What changes from Stage 1

The reward model from Stage 1 stops being a reranker over
externally-generated candidates and becomes the **reward function** for
training a single model (start from a pretrained instruction-tuned
base, LoRA fine-tuned — full from-scratch training is not needed and
not justified by the data volume this project will realistically have)
to generate reformulations directly, via PPO or GRPO rollouts against
that reward.

```
Original sentence + difficulty_profile
                ↓
     Single generative model (LoRA fine-tuned)
                ↓
      Reformulated sentence — no intermediate candidate list
                ↓
  Reward model (Stage 1) used only during training, not at inference
                ↓
  Deterministic safety gates — still present at inference, unchanged
```

This is the model that "understands what to replace and what not to
replace" as a single learned judgment, rather than a two-stage
generate-then-rank pipeline. It's the closest realistic version of the
end-to-end system you described wanting.

### 4.2 Why the safety gates never go away, even here

No stochastic model — however well-trained — ships into an
accessibility tool with zero hard verification downstream. A
well-trained Stage 2 model should hit the safety-gate fallback rarely.
"Rarely triggered" is the sign the training worked; "removed entirely"
is not a milestone, it's a regression. This preserves the one invariant
that must never depend on model behavior: allowlisted words are never
touched, full stop, checked outside the network.

### 4.3 Why Stage 2 depends on Stage 1 existing first, not on skipping it

The reward function above — meaning preservation, naturalness, phoneme
difficulty against the real schema — is exactly what an RL loop needs
to score rollouts. Building it only as a reranker first means it gets
validated cheaply (fast iteration, easy to inspect failures, no
expensive training run) before it's trusted as the thing an entire
generative model gets optimized against. A bad reward function
discovered *after* an RL run is an expensive mistake; the same bug
caught in Stage 1 is a one-line fix.

---

## 5. What this proposal deliberately does not include, and why

- **No full pretraining from scratch.** Not justified by any realistic
  data volume for this task; a pretrained base already knows English.
- **No attempt to have the model infer phonemes from spelling.** CMU
  dict + ARPAbet already exist in this codebase and are more reliable
  than anything a model would learn implicitly from orthography — this
  is giving the model the right representation, not hand-coding the
  decision.
- **No change to `grammar.py`, `engine.py`, `semantic.py`,
  `rewrite/*.py`, `rephrase.py`, or `profiling/profile.py`** in Stage 1.
  Everything in §6 of the formulation doc that currently has zero lines
  changed stays that way until Stage 2 replaces the generation step
  itself.
- **No schema changes.** `problem_phones`, the four-category split, and
  onset-only sound matching are used as-is. This proposal is a new
  consumer of the existing schema (closing the gap named in §11.2 —
  "not yet wired to anything" — with a correct consumer instead of the
  lossy legacy bridge), not a reason to redesign it.

---

## 6. Immediate next actions, in order

1. Reformat existing evaluation judgments (candidate sets + human
   preference) into the `(sentence, profile, candidate_A, candidate_B,
   preferred)` shape.
2. Build the feature extractor that turns a candidate + `difficulty_profile`
   into the phoneme-difficulty score, using `phonetic.full_pronunciation()`
   directly — no dependency on the legacy bridge.
3. Train the DPO reward/reranker model on (1)+(2). Evaluate with a
   held-out-speaker split.
4. If Stage 1 reranking measurably beats the current architecture on
   held-out speakers, proceed to Stage 2 RL training using the same
   reward function. If it doesn't, the reward design is wrong and needs
   fixing before any RL run is attempted — this is the checkpoint that
   prevents an expensive failure later.
