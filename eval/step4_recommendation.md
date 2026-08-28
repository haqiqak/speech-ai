# Architecture Go/No-Go — Step 4: recommendation (pending ratification)

This is a **recommendation**, not a decision. Every prior consequential
step in this arc (Step 1's plan, proceeding to Step 2, proceeding to
Step 3) was ratified by the user before being treated as final; this
follows the same discipline. Nothing here changes production code or
this project's stated direction until the user says so.

## The three options, re-stated as agreed

- **A.** Current architecture is good enough → stabilize, stop
  optimizing.
- **B.** Fundamentally limited → introduce a learned component
  (per Step 2's finding, specifically a learned reranker/scorer).
- **C.** Even a learned augmentation doesn't make sense → freeze the
  current architecture as the maintained/shipped state, with no further
  optimization (not project abandonment — the user's clarified meaning).

## Ruling out A

CLEAN rate on fresh material is 21.4%, meaning roughly 4 in 5 attempted
rewrites carry a real defect a human would notice, and dense/
multi-constraint profiles — plausibly the profiles a person with a more
demanding difficulty profile actually needs — score 0% CLEAN on two
independent corpora six phases apart. That is not "good enough" against
the stated research objective (faithful, speakable rewrites) by any
reading of the evidence in `step3_architecture_assessment.md`. A is not
recommended.

## The real choice: B vs. C

**The case for B** is genuinely strong on its own terms. Step 2
produced the most mechanistically specific finding in this project's
history: 71% of the dominant remaining defect class (WRONG_WORD_OR_SENSE)
are ranking failures, not generation gaps — the right candidate is
usually already in the pool, and `combined_score()`'s fixed 90/10
semantic/frequency blend picks the wrong one when two candidates'
similarity scores are close, with a directly verified mechanism
(`chemical`/`physical` beating `biological` on frequency despite lower
similarity). A learned reranker over an already-generated candidate set
is a scoped, well-motivated fix for a problem this specific — not a
speculative "maybe ML helps" bet.

**The case for C** rests on evidence this project already has, applied
honestly to the B option itself. Two independent findings point the
same direction:

1. **Phase 9B/9C's own precedent**, which the user explicitly required
   as a mandatory bar for any future learned component: a prior learned
   validator, when tested on genuinely held-out data, predicted
   DEFECTIVE 99% of the time — a near-total generalization failure from
   a component that looked reasonable on its own training/tuning data.
2. **This exact fresh-corpus check**, just completed, shows the SAME
   failure pattern in the current rule-based architecture: ~31-34%
   CLEAN on the corpus it was iteratively tuned against, 21.4% on
   material it wasn't. The rule-based system has the advantage of being
   human-designed and individually inspectable case-by-case — every
   gate in it was built, verified, and can be debugged against a
   specific named failure. A learned reranker has none of that
   transparency, and would have to be trained/validated using this same
   project's own evaluation infrastructure: a Claude-judged corpus that,
   by this project's own repeated documentation (Phase 8/8B/50's
   struggle to gather even 20-60 examples for some defect classes), is
   small per defect class and has now been directly shown (this check)
   to support conclusions that don't transfer to fresh material.

Put plainly: **the thing that just failed to generalize (a system tuned
against this project's own limited, Claude-judged evidence) is exactly
the kind of thing a learned reranker would also have to be, tuned
against the same evidence, evaluated the same way.** There is no reason
in hand to expect a learned component to clear a bar the current,
simpler, more inspectable system just failed to clear by a wide margin
— and the Phase 9B/9C precedent shows this isn't a hypothetical concern,
it already happened once in this exact codebase.

## Recommendation: C

Freeze the current architecture as the maintained/shipped state. Do not
pursue a learned reranker or other learned component as a next step,
not because Step 2's diagnosis is wrong — it is the most solid finding
in the project — but because this project's own evidence (Phase 9B/9C
plus this fresh-corpus check) gives a specific, demonstrated reason to
expect a learned component built and validated the way this project
would have to build one to fail the same generalization test the
current architecture just failed, at higher engineering cost and with
less interpretability than what exists today.

Concretely, "freeze" means: stop adding new blocklist entries, gates,
or rule patches in response to individual newly-observed failures
(ending the "Phase 11D/E/F" pattern this arc was explicitly started to
avoid); keep the current 9-gate, phoneme-constrained-generation
architecture as the shipped system; continue normal maintenance
(dependency updates, bug fixes that don't change matching/ranking
behavior); and be explicit with users of this tool, if it has any,
about the current measured failure rate rather than presenting it as
more reliable than the evidence supports.

This does not foreclose reopening the learned-component question later
if the situation changes materially — e.g., a genuinely larger,
independently-collected labeled corpus becomes available, removing the
specific data-scale objection raised above. It is a decision about
what to do with the evidence in hand today, not a permanent architectural
ban.

## What this recommendation is not

It is not a claim that the system is useless — CLEAN rate is not 0%,
`core_word`/single-constraint profiles do meaningfully better (33.3% on
fresh material) than dense profiles, and the safety-refusal mechanism
(criterion 4) is real and working. It is a claim that further
investment in *this style* of engineering — more rules, more gates, or
a learned layer built the same way — is not well-supported by the
evidence as the next move.

**Awaiting the user's ratification of this recommendation (or a
different call) before treating Step 4 as closed.**
