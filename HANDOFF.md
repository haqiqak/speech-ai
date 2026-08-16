# HANDOFF.md — Primary entry point

Written so a new researcher, or a Claude instance with zero conversation
history and no access to any prior chat, can become productive without
reconstructing anything from memory. Read `Practice.md` first (it defines
the vocabulary used below), then this file, then follow its pointers.

## What this module is, in one paragraph

Speech AI takes transcribed text plus a speaker profile and rewrites the
text to be easier for *that specific speaker* to say, while staying
faithful to the original meaning, intent, narrative, and natural flow.
It is the second stage of a two-repository system; the Audio Module
(not this repo) produces the transcription and profile it consumes.
See Practice.md §1 for the precise, citable statement of the research
objective — that sentence is the actual yardstick, not "does the app
work."

**Scope note (added 2026-08-15, Stage 2 narrowing pass):** this repo used to
also contain a CrisperWhisper ASR wrapper, a rule-based ASR-timing disfluency
detector, and a browser voice-input/voice-output UI layer — code that
anticipated the Audio Module rather than being part of it. That code moved to
`out_of_scope/` and is no longer imported by `app.py`. Everything below that
predates this pass may still mention those files by their old location;
where it does, treat `out_of_scope/<old path>` as the current location. No
reformulation algorithm, weight, or threshold changed in this pass — see
`DECISION_LOG.md` for the entry recording exactly what moved and why.

**Scope note (added 2026-08-15, Stage 4A foundation pass):** a new,
persistent, user-declared speaker difficulty profile now exists
(`difficulty_profile.py` — sounds/words/phrases, explicitly independent
categories; full design record in `PROBLEM_FORMULATION.md`). It is **not**
the same thing as the `SpeakerDifficultyProfile` mentioned throughout this
file (`profiling/profile.py`, the learned/EWMA one) — the two are
deliberately separate for now, reconciling them is `ROADMAP.md` R12. The new
profile reaches the existing, unmodified reformulation pipeline only through
an auto-derived mirror into the legacy `phoneme_profile.stutter_patterns`/
`.blocked_words` fields — see `DECISION_LOG.md` 2026-08-15-C. No
reformulation algorithm, weight, or threshold changed in this pass either;
verified via `tests/smoke.py` being byte-identical to baseline.

## What's proven vs. still a hypothesis (read this before trusting a claim elsewhere)

**Proven / fact-level, in the sense of "verifiably true of the code as it
stands"** (verified by reading the code during this review, 2026-08-08):
- The pipeline architecture as described in `DOCS.md` and the earlier
  repo-review summary: `sanitize_input()` → `SentenceRewriter.rewrite()`
  → engine/semantic/phonetic gating → inflect/rebuild, with a parallel
  `rewrite/` "soft" path and an optional `rephrase.py` T5 layer.
- `semantic.py`'s actual constants (`SEMANTIC_W=0.90`, `FREQUENCY_W=0.10`,
  `MIN_SEMANTIC=0.85`) — confirmed against source, **not** against
  README, which is stale here.
- `users/default.json` and `users/bobcat.json` are committed to git
  history with password hashes, despite documentation claiming otherwise.

**Hypothesis / unvalidated** (do not treat as settled):
- That fixed phoneme-onset matching is the right primary predictor of
  spoken difficulty for this population (Practice.md §7's own open
  question). **Update, 2026-08-15:** the literature pass called for by §7
  has now been run — see `RESEARCH.md` §1.2/§5.4. Short answer: onset
  phoneme class is a real, clinically-grounded factor, but not obviously
  the *dominant* one, and the current formula's shape is a simplification
  relative to what speech-motor-control literature suggests actually drives
  articulatory difficulty. This is a literature-grounded reinforcement of
  the existing "unfitted weights" limitation, not a resolution of it — the
  formula still hasn't been validated against real speaker data (blocked on
  the Audio Module, per `ROADMAP.md` R2), which is a separate, still-open
  gap.
- That the difficulty formula's specific coefficients
  (`0.4/0.3/0.3` and the profiling-layer `0.45/0.25/0.20/0.10`) are
  well-calibrated. They are stated in code/config as defaults, not as
  fitted or validated values.
- That the `rewrite/` "soft" path produces better rewrites than
  `grammar.py`'s "hard" onset-gated path, or vice versa — no comparison
  exists (see `ROADMAP.md` R5).
- That SBERT similarity ≥ 0.85 reliably tracks human-judged meaning
  preservation at this repository's specific candidate-sentence
  construction. Plausible, argued by example in `semantic.py`'s
  docstring, not measured against human judgment (see `VALIDATION.md`).

## What the fast, model-free test suite currently covers

- `tests/smoke.py` — regression diff against committed baselines. Requires
  `DISABLE_DATAMUSE=1` for determinism; set `SMOKE_SKIP_SBERT=1` on
  RAM-constrained machines to force frequency-only mode (output stays
  deterministic).
- `tests/app_test.py` — headless Streamlit `AppTest` harness; seeds an
  authenticated session before `.run()` since `auth.require_auth()` gates
  everything.
- `tests/threshold_sweep.py` — diagnostic, not pass/fail; see
  `DECISION_LOG.md` 2026-06-08-A for its one recorded finding.

None of these load SBERT, T5, or CrisperWhisper by default (`smoke.py`
optionally loads SBERT unless `SMOKE_SKIP_SBERT=1`). This matters per
Practice.md §9: the rephrase model (~890 MB) and CrisperWhisper (~3 GB)
are genuinely expensive, so keeping these fast is load-bearing for
development speed, not a nicety.

## Exact commands to reproduce the last validated result

**There is no last validated result to reproduce**, in the Practice.md §8
sense (pre-registered protocol, run, reported) — see `VALIDATION.md` §5
for the explicit statement of this gap. What *can* be reproduced is the
regression baseline:

```bash
DISABLE_DATAMUSE=1 python tests/smoke.py > /tmp/after.txt
diff tests/baseline_sbert.txt /tmp/after.txt   # primary reference (SBERT on)
# or, frequency-only mode:
DISABLE_DATAMUSE=1 SMOKE_SKIP_SBERT=1 python tests/smoke.py > /tmp/after_freq.txt
diff tests/baseline.txt /tmp/after_freq.txt
```

To run the app locally:
```bash
python -m venv venv && source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
streamlit run app.py
```
First run downloads NLTK data (`cmudict`, tagger, `punkt_tab`, `wordnet`)
and the SBERT model (~80 MB) into project-local `.cache/`. Login with
`default` / `speech` (auto-migrated account) or register a new one.

## Pitfalls already hit (concrete, so the next session doesn't rediscover them)

- **Import order matters.** `paths.py` must be imported before `nltk`,
  `sentence_transformers`, `torch`, or `wordfreq` in any entry module —
  it redirects caches and caps BLAS/OpenMP thread counts *before* those
  libraries read the environment. Every core module (`engine.py`,
  `semantic.py`, `phonetic.py`, `freq.py`, `grammar.py`, `rephrase.py`)
  does `import paths  # noqa: F401` as its first real import specifically
  for this reason — don't reorder it "for cleanliness."
- **`sem.MIN_SEMANTIC` is mutated at runtime**, not just read from a
  constant — `app.py` sets `sem.MIN_SEMANTIC = sem_threshold` from the
  sidebar slider before calling `rewriter.rewrite()`. A test or script
  that imports `semantic` and expects the module-level default to hold
  after the app has run in the same process will get the wrong value.
- **`freq.py`'s wordlist downgrade is global and irreversible per
  process.** Once a `MemoryError` triggers the fallback to the "small"
  wordfreq list, every subsequent call in that process uses "small," even
  if memory pressure was transient. Fine for a single Streamlit process;
  would misbehave if this code were ever imported into a longer-lived
  multi-tenant service.
- **`st.iframe` in `voice.py` was unverified against the pinned Streamlit
  version** — see `ROADMAP.md` H1. This is now moot for *this* repo: as of
  the Stage 2 scope-narrowing pass, `voice.py` (and the CrisperWhisper/ASR
  detector code) moved to `out_of_scope/` and is no longer imported by
  `app.py`. The open question still applies to whoever picks the file up
  for the separate Audio Module — see `out_of_scope/README.md`.
- **Documentation drift is real and already happened twice** (README's
  stale scoring numbers, AUTH_README's incorrect `.gitignore` claim) —
  verify against running code before citing a `.md` file's specific
  numbers, per Practice.md §5's rule, applied here concretely rather than
  abstractly.
- **User account JSON is sensitive and already leaked into git history**
  — do not add new real user data to `users/` in this repository without
  first fixing the gitignore/history issue in `DECISION_LOG.md`
  2026-06-13-A; adding more real accounts now would make the existing
  problem worse, not better.
- **The `rewrite/` "soft" path imports from `grammar.py`**
  (`_detokenize`, `_preserve_case`, `inflect`) and `engine.py`
  (`SynonymEngine`) directly — it is not a fully independent module. A
  change to `grammar.py`'s private helpers can silently break `rewrite/`
  without an import error surfacing anywhere obvious; there's no test
  that exercises both paths side by side to catch this today.

## Curated reading order for a first pass on this repo

1. `Practice.md` (methodology)
2. This file
3. `DOCS.md` (file map)
4. `README.md` + `AUTH_README.md` (product-level description — read
   *with* the drift warnings in `DOCS.md` in mind)
5. `app.py` top-to-bottom structurally (it's the orchestrator; everything
   else is a library it calls)
6. `grammar.py` (`sanitize_input`, `SentenceRewriter`) — the core "hard"
   pipeline
7. `semantic.py`, `engine.py`, `phonetic.py`, `freq.py` — the signals the
   core pipeline is built on
8. `profiling/` then `rewrite/` — the persistent-profile "soft" pipeline
9. `rephrase.py` — optional, isolated layer
10. `DECISION_LOG.md`, `VALIDATION.md`, `RESEARCH.md`, `ROADMAP.md` — the
    evidence record, the literature grounding, and what's next

**Not in this reading order:** `out_of_scope/` (archived audio/ASR/voice
code — read `out_of_scope/README.md` only if you're picking up the Audio
Module, not for work on this repository's reformulation pipeline).
