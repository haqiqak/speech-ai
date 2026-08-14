# VALIDATION.md — Living evaluation record

Per Practice.md §16, every real evaluation run belongs here with its
exact config, dataset/profile version, git commit, and timestamp. As of
this review (2026-08-08), **no entry in this file is a completed,
pre-registered (§8) evaluation result** — what follows is an honest
inventory of the evaluation *machinery* that exists, what it currently
covers, and — most importantly per §12 — what it does not.

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
  "outcome" it checks against is `profiling/detect.py`'s own rule-based
  disfluency labels, which are themselves a proxy (a rule-based labeler,
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
