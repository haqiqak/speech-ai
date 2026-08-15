# DOCS.md — File map

One line per file/module: what it's for, who reads it, how often it
should change, and — per Practice.md §5/§7 — an explicit flag where a
doc is already known to have drifted from the code it describes.

**Scope note (Stage 2, this pass):** the repository was narrowed to the text
reformulation module. `voice.py`, `profiling/asr.py`, and `profiling/detect.py`
moved to `out_of_scope/` (audio/ASR/voice-UI code that belongs to the separate
Audio Module, not this repo) — see `out_of_scope/README.md`. This was a pure
move/removal-from-the-live-path pass: no reformulation algorithm, threshold,
weight, or scoring method was changed. See `DECISION_LOG.md` for the entry
recording this decision.

## Documentation (reader: humans, new contributors, future Claude instances)

| File | Purpose | Update cadence | Drift status |
|---|---|---|---|
| `README.md` | Explains the overall Speech-AI project, where this repo fits, and this module's product description, setup, feature list, "Architecture Notes" | On every user-visible feature/behavior change | **Drift fixed, this pass**: previously described the synonym-ranking split as `0.65 sim / 0.35 freq`; now matches `semantic.py`'s actual constants (`SEMANTIC_W=0.90`, `FREQUENCY_W=0.10`, `MIN_SEMANTIC=0.85`). Also rewritten to state project-vs-module scope explicitly and to drop the voice/mic feature descriptions (moved to `out_of_scope/`). |
| `AUTH_README.md` | Auth/user-storage design note, bcrypt/DB upgrade paths | On auth-layer changes | **Known drift**: states `users/` is "never committed to version control (add to `.gitignore`)". The actual `.gitignore` only excludes `users/*.fluency_profile.json`; `users/default.json` and `users/bobcat.json` (including password hashes) are committed. See `DECISION_LOG.md` entry 2026-06-13-A. |
| `changes.md` | Version history / changelog narrative | On release | Not cross-checked line-by-line in this pass; treat as a narrative summary, not a source of truth for current behavior — verify against code per §5. |
| `scripts/README.md` | How to use `build_rephrase_dataset.py` / `train_rephrase.py` | On scripts changes | Not reviewed in this pass. |
| `Practice.md` (external, uploaded) | Governing research/engineering methodology for this module | Amended per its own §20 (dated addenda only) | N/A — this is the standard everything else is checked against. |
| `CLAUDE.md` | Orientation, points elsewhere | Rarely | New, this pass. |
| `HANDOFF.md` | Curated onboarding, proven-vs-hypothesis, pitfalls | Every session that learns something a future session needs | New, this pass — currently a one-time backfill, not yet a live log. |
| `DECISION_LOG.md` | Append-only, four-part decision record | Every non-trivial decision, at the time it's made | New, this pass — backfilled from git history/comments (see caveat in `CLAUDE.md`). Going forward this should be appended to live, not regenerated. |
| `VALIDATION.md` | Pre-registered protocols, results, ablations, named limitations | Every real evaluation run | New, this pass — currently documents *what evaluation machinery exists*, not a completed pre-registered result, because none exists yet (see §12 proxy-metric warning inside the file). |
| `ROADMAP.md` | Priority-ordered, evidence-linked forward plan | As evidence changes priorities | New, this pass — seeded from README's existing "Roadmap" section plus gaps this review surfaced. |
| `CHANGELOG.md` | One line per change, reverse-chronological, points into decision log | Every commit that closes a decision-log entry | New, this pass — backfilled from `git log`. |

## Live application path (the app depends on these; keep lean)

| File | Purpose | Notes |
|---|---|---|
| `app.py` | Streamlit UI + orchestration: auth gate → sanitize → rewrite → render. ~1,700 lines. | Largest single file; mixes UI, session-state management, and light business logic (e.g. `_risk_chips`, `_rebuild_sentence`). Candidate for splitting if it keeps growing — not a finding, an observation. |
| `auth.py` | Login/register screen; calls into `user_store.py`; gates all of `app.py` via `require_auth()` + `st.stop()`. | |
| `user_store.py` | File-based per-user JSON store; thin public API intentionally designed to be swappable for SQLite/Postgres. | SHA-256 password hashing — see `DECISION_LOG.md` 2026-06-07-A. |
| `paths.py` | Must be imported **first**, before nltk/torch/wordfreq, in every entry module. Redirects caches into `./.cache/`, caps BLAS/OpenMP thread counts. | Load-bearing side-effect module; import-order is a real pitfall — see `HANDOFF.md`. |
| `grammar.py` | `sanitize_input()` (grammar correction, ~10 layers) + `SentenceRewriter` (the core substitution loop: POS-tag → protect → candidates → SBERT rank → phoneme gate → inflect → rebuild). Largest logic file (~1,600 lines). | |
| `engine.py` | `SynonymEngine` — WordNet (POS-filtered) + Datamuse candidate retrieval, Zipf-frequency ranking. | |
| `semantic.py` | SBERT loading, cosine similarity, protected-phrase/stop-word registry, combined semantic+frequency scoring. | Owns the `MIN_SEMANTIC`/`SEMANTIC_W`/`FREQUENCY_W` constants that `README.md` describes inaccurately (see drift note above). `sem.MIN_SEMANTIC` is mutated at runtime from the UI slider — see `HANDOFF.md` pitfalls. |
| `phonetic.py` | ARPAbet onset extraction (CMU dict + grapheme fallback), the hard-coded `word_difficulty()` heuristic. | Standalone by design (imports only `paths`/nltk/wordfreq); the difficulty formula's weights are un-validated — see `DECISION_LOG.md` and `VALIDATION.md`. |
| `freq.py` | Single choke-point for `wordfreq.zipf_frequency`, with an irreversible `MemoryError` downgrade to the small wordlist. | Global mutable state (`_active`) — see `HANDOFF.md` pitfalls. |
| `config.yaml` | Profiling/rewrite/eval knobs (`ewma_alpha`, profiling weights, `lambda`/`mu`/`tau`, detection thresholds). | These weights are the same class of un-validated, hand-picked numbers flagged by Practice.md §6/§7. The `profiling.detection` sub-block (repetition/prolongation/block/filler thresholds) is now only consumed by the archived `out_of_scope/profiling/detect.py` — left in place rather than pruned, since editing `config.yaml`'s structure was out of scope for a pure narrowing pass; flagged here as a loose end. |
| `rephrase.py` | Optional T5 paraphrase layer. Never imported by `grammar.py`/`engine.py`; degrades to passthrough. | Cleanly isolated — good separation between live-path-required and optional-heavy code. |
| `profiling/profile.py` | `SpeakerDifficultyProfile` — persistent, multi-factor, EWMA-updated per-speaker difficulty model. | |
| `profiling/coldstart.py` | Population-prior + self-report blending for new profiles. | |
| `profiling/config.py` | Loads `config.yaml`. | |
| `rewrite/rewriter.py`, `rewrite/rank.py`, `rewrite/candidates.py` | The "soft" profile-aware rewrite path (`similarity - λ·difficulty + μ·frequency`), parallel to `SentenceRewriter` in `grammar.py`. | Meaningfully duplicates protected-word/POS-filtering/inflection logic already in `grammar.py`/`semantic.py` — flagged as an observation with maintenance-risk implications; see `DECISION_LOG.md` and `ROADMAP.md`. |
| `users/` | Per-user JSON (credentials + phoneme profile + preferences). | **`default.json` and `bobcat.json` are committed to the repo** despite docs claiming otherwise — treat as sensitive, see `DECISION_LOG.md` 2026-06-13-A. Untouched by this pass — that's a separate remediation, not a scope-narrowing question (see `ROADMAP.md` R0). |
| `out_of_scope/voice.py`, `out_of_scope/profiling/asr.py`, `out_of_scope/profiling/detect.py` | **Moved out of the live app, this pass.** Browser STT/TTS UI, the CrisperWhisper ASR wrapper, and the rule-based ASR-timing disfluency detector. Audio Module concerns, not text reformulation. | See `out_of_scope/README.md`. Not imported by `app.py`/`profiling/__init__.py` anymore; preserved standalone with a duplicated `config.py` so they still run/test in isolation. |

## Research / evaluation path (should not be imported by the live app)

| File | Purpose | Notes |
|---|---|---|
| `eval/metrics.py` | Meaning-preservation, difficulty-onset reduction, substitution-rate, λ-tradeoff computations. | Computed entirely from SBERT/frequency/formula signals — see the proxy-metric caveat in `VALIDATION.md`. |
| `eval/profile_eval.py` | Compares self-report-only vs. observed-only vs. fused profile AUC. | |
| `eval/study/collect.py`, `counterbalance.py`, `stats.py` | Scaffolding for a counterbalanced three-condition user study. | Not yet run against real participants, as far as this review can tell from the repo alone (observation, not confirmed either way — see `VALIDATION.md`). |
| `scripts/build_rephrase_dataset.py`, `scripts/train_rephrase.py` | Offline dataset-building / fine-tuning scaffolding for the T5 rephrase model. | |
| `tests/smoke.py` | Behavioral baseline/regression diff tool (not a real evaluation — a regression net, per its own docstring). | Requires `DISABLE_DATAMUSE=1` for determinism. |
| `tests/app_test.py` | Headless Streamlit `AppTest` UI smoke test. | |
| `tests/threshold_sweep.py` | Diagnostic sweep of `MIN_SEMANTIC`. **Already produced a documented, unactioned finding** — see `DECISION_LOG.md` 2026-06-08-A and `VALIDATION.md`. |
| `tests/evaluate.py`, `tests/roadmap_test.py`, `tests/persistence_test.py` | Additional regression/eval scripts. | `roadmap_test.py` was split this pass: its `SpeakerDifficultyProfile`/`DifficultyAwareRewriter` tests stayed here; its CrisperWhisper/detector tests moved to `out_of_scope/tests/roadmap_test_audio.py` alongside the code they exercise. Re-ran both halves after the split — all pass, no behavior change. |
| `tests/baseline*.txt`, `tests/eval_corpus.txt`, `tests/eval_results.csv` | Committed reference outputs for the regression-diff tests. | These are regression fixtures, not pre-registered (§8) evaluation results. `tests/smoke.py` output is byte-identical to `baseline_sbert.txt` after this pass's `app.py` edits, confirming the rewrite pipeline itself was untouched. |
