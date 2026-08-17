# CHANGELOG.md — Fast-scan index

One line per change, reverse-chronological, backfilled from `git log`
(2026-08-08). Each line points into `DECISION_LOG.md` where a fuller
entry exists; most commits below have no decision-log entry because they
were routine/incremental — per Practice.md §14, the changelog is the fast
index, the decision log is the full record, and not every line needs both.

- **2026-08-17** feat: Stage 7 v3 — P1 actually completed v2's 20-pair
  pilot (first real human-judgment data collected: meaning 4.65/5,
  naturalness 4.70/5, ease +1.75, preferred reformulated 19/20). That
  real use found a genuine UI bug — boxes labeled "Sentence 1/2" plus a
  separate caption meant P1's free-text comments sometimes described the
  reformulated text as if it were the input. Rebuilt as v3 per direct
  user review: single participant, 30 short/natural/everyday sentences
  only (18 global-sound / 5 declared-word / 4 word-pattern / 3
  multi-difficulty), Original/Reformulated labeled directly on each box,
  full per-item profile-traceability metadata, and human ratings now
  explicitly scoped to meaning/naturalness/ease/preference only —
  profile-match effectiveness is automated and reported separately,
  never asked of the participant. A second bug (an `AppTest` test-
  harness fragility across many sequential form-submits, not the pilot
  app) found and fixed while verifying the new 30-pair flow end-to-end
  with synthetic data. v2's real P1 data and pair set archived at
  `eval/archive_v2/`, not deleted. Zero `reformulate.py` changes — full
  suite (78 tests) + `tests/smoke.py` re-confirmed. →
  `DECISION_LOG.md` 2026-08-17-E/F; `VALIDATION.md` §8.7, §9;
  `ROADMAP.md` R4.
- **2026-08-17** feat: Stage 7 — built and verified (synthetic data) a
  human-evaluation pilot for `reformulate.py`: `eval/pilot_select_pairs.py`
  (deliberate, non-random 20-pair selection from a 69-case eligible pool,
  including known-weak Stage-6 cases and two newly-found genuine errors),
  `eval/pilot_app.py` (minimal Streamlit collection instrument,
  counterbalanced), `eval/pilot_analyze.py` (per-pair summaries +
  proxy-vs-human disagreement flagging). Full workflow driven end-to-end
  with synthetic responses via `AppTest` before any real participant —
  all checks passed. Real 4x20 data collection not yet run. Zero changes
  to `reformulate.py` — confirmed via full suite (78 tests) +
  `tests/smoke.py`. → `DECISION_LOG.md` 2026-08-17-C; `VALIDATION.md` §8;
  `ROADMAP.md` R4.
- **2026-08-17** feat: R9 — Keep/Revert toggles now record a feedback
  signal (kept/reverted counts) against the declared word/sound entry
  responsible for each substitution, stored in that entry's existing
  `meta` field and shown as a small badge in the profile panel.
  Prototype scope only — nothing reads this field back into
  `reformulate.py`'s ranking yet, by design. New:
  `reformulate.feedback_targets()`,
  `difficulty_profile.record_feedback()`/`undo_feedback()`. 11 new
  tests; full suite (78) and `tests/smoke.py` confirm the reformulation
  engine itself is unaffected. → `DECISION_LOG.md` 2026-08-17-A;
  `ROADMAP.md` R9.
- **2026-08-16** eval: Stage 6 — ran `reformulate.py` against both
  retained legacy pipelines on a new 18-case failure-mode corpus
  (`tests/reformulation_eval_corpus.json`, `eval/reformulation_eval.py`).
  New engine: highest meaning preservation (0.979) and smallest edits
  (0.068), but lowest reformulation rate (0.556 vs. 0.889/0.833) — fully
  explained by a 0/4 T5-restructuring-escalation success rate, root-caused
  into a fixable case-sensitivity bug in `rephrase.py::_bad_words_ids()`
  (`ROADMAP.md` R17) and a deeper paraphrase-model/phoneme-avoidance
  mismatch (`ROADMAP.md` R18, confirms `REFORMULATION_RESEARCH.md` §24.E
  with evidence for the first time). Also found: a pre-existing
  `SentenceRewriter` inflection bug, the context-dependent-substitution
  failure mode persisting in all three systems, and a directly-observed
  case where SBERT scored a redundant rewrite at 0.965 — concrete evidence
  for the proxy-metric warning, not just a restatement. Measurement only,
  nothing tuned. → `VALIDATION.md` §6; `DECISION_LOG.md` 2026-08-16-G;
  `ROADMAP.md` R6 (superseded)/R17/R18.
- **2026-08-16** chore: pre-evaluation cleanup pass — removed dead surface
  the D′/UI redesign left behind: `run_app.ps1` (broken paths, described
  a removed ASR feature), `profile_store.py`'s `load_preferences`/
  `save_preferences` and the on-disk `preferences`/`custom_replacements`
  fields (zero live consumers — traced every caller before removing),
  `tests/persistence_test.py` (tested only that now-removed round-trip),
  `freq.py::active_wordlist()` (zero call sites), two unused imports in
  `reformulate.py`, `torchvision` from `requirements.txt` (flagged unused
  and deferred back in 2026-08-15-A, now actually removed), and a stale
  `.gitignore` line. `grammar.py::SentenceRewriter`, `rewrite/`,
  `profiling/`, `eval/`, `config.yaml`, `scripts/` all investigated and
  kept — confirmed still genuinely exercised (by `smoke.py`/
  `threshold_sweep.py`/`evaluate.py`/`roadmap_test.py`/`eval/metrics.py`)
  and load-bearing for the upcoming evaluation-stage comparison. `README.md`
  rewritten where it still described the removed v7 UI as current. No
  reformulation behavior changed — `tests/smoke.py` byte-identical to
  baseline; 56 unittest cases + 2 script suites all pass. →
  `DECISION_LOG.md` 2026-08-16-F.
- **2026-08-16** feat: implement Architecture D′ (`reformulate.py`) and
  redesign `app.py` (v7 → v8) around it — one linear workflow (text →
  difficulty profile → Reformulate → changes/skipped/verification review
  with per-change Keep/revert) replacing the old dual-pipeline UI (word
  pickers, separate word/sentence/multi-sentence modes, profile-rewrite
  card, rephrase card, allowlist panel, the onset-risk chart, which was
  quietly re-displaying declared sounds as if learned from sessions that
  no longer exist in this module's scope). New `naturalness.py`
  (edit-ratio metric, R11). `semantic.py` extended additively
  (`is_known_antonym`, `negation_consistent`). Two real bugs found via
  live smoke tests, not unit tests, and fixed before shipping: escalation
  wrongly rejected everything when SBERT was offline (contradicted
  `semantic.py`'s own documented fallback); escalation's word-block set
  included non-substitutable words (numerals), guaranteeing failure
  whenever one was present. `grammar.py::SentenceRewriter` and
  `rewrite/rewriter.py::DifficultyAwareRewriter` untouched, just no longer
  called. `tests/smoke.py` byte-identical to `baseline_sbert.txt`. New
  `tests/reformulate_test.py` (12 tests); `tests/app_test.py` rewritten
  for the new UI (all scenarios pass). → `DECISION_LOG.md` 2026-08-16-E;
  `ROADMAP.md` R5/R6/R9/R10/R11/R12/R13.
- **2026-08-16** docs: append Stage 5B critical review (§24–31) to
  `REFORMULATION_RESEARCH.md` — challenged and revised Stage 5's
  recommendation (tiered semantic verification instead of flat NLI, MLM
  candidates deferred pending measurement, position/stress corrected to
  logged-not-scored per this project's own Practice.md §6 discipline, a
  new count-threshold restructuring trigger, T5's constraint-mechanism
  limit found by reading `rephrase.py`'s actual code), then produced the
  exact input/output contract, MVP/Strong/Future split, evaluation plan,
  failure-handling states, and implementation blueprint. Architecture
  declared implementation-ready. Zero reformulation code changed. →
  `DECISION_LOG.md` 2026-08-16-D.
- **2026-08-16** docs: add `REFORMULATION_RESEARCH.md` — Stage 5 deep
  research pass on the reformulation-engine architecture itself: Brown's
  four stuttering-loci factors, a second close prior system (SpeechAgent,
  2026), minimal-edit tagging architectures (GECToR/FELIX, researched and
  found infeasible here for lack of training data, not hardware), concrete
  CPU-feasible NLI/constrained-decoding tooling, ten constructed failure
  modes, and a ranked architecture recommendation (candidate-gen+rank with
  a generation escalation path and symbolic final verification). Pure
  research — zero lines changed in `grammar.py`/`semantic.py`/`engine.py`/
  `rewrite/`/`rephrase.py`. → `DECISION_LOG.md` 2026-08-16-C; updates to
  `ROADMAP.md` R2/R6/R8/R9/R10/R11.
- **2026-08-16** fix: foundation audit found and fixed two real ambiguities,
  verified against live CMU data — heteronym words (`"read"`, `"the"`, etc.)
  silently used only the first CMU pronunciation variant, now flagged
  (`has_alternate_pronunciations`); `add_sound_from_phones()`'s promoted
  entries could silently fail to round-trip through the legacy matching
  bridge for phones with no natural English spelling (e.g. ZH), now flagged
  (`legacy_bridge_unreliable`). Both surfaced as UI warnings, not silent
  gaps. `tests/difficulty_profile_test.py` 38→44, `tests/app_test.py`
  6→7 scenarios. → `DECISION_LOG.md` 2026-08-16-B; `PROBLEM_FORMULATION.md`
  §11; `ROADMAP.md` R15/R16.
- **2026-08-16** feat: word-specific sound patterns (`problem_phones` on word
  entries — "three" difficult ≠ "TH"/"R" globally difficult, unless
  explicitly promoted) via a new inline pattern-editor panel in `app.py`,
  phone display via a new `phonetic.friendly_phone_label()` respelling
  table. Multi-user system removed: `auth.py`/`user_store.py` deleted, new
  `profile_store.py` loads one default profile automatically (no login),
  keeping a `profile_name` parameter throughout for future extensibility.
  `users/bobcat.json` deleted; `users/default.json` rewritten with no
  `password_hash`/`phoneme_profile` fields. Zero changes to
  `grammar.py`/`engine.py`/`semantic.py`/`rewrite/`/`rephrase.py`/
  `profiling/profile.py` — `tests/smoke.py` byte-identical to baseline.
  Tests: `tests/difficulty_profile_test.py` 38/38 (12 new);
  `tests/app_test.py` extended to 6 scenarios; `tests/persistence_test.py`
  rewritten against `profile_store.py`. → `DECISION_LOG.md` 2026-08-16-A;
  `PROBLEM_FORMULATION.md` (rewritten in place); `ROADMAP.md` R0/R12/R13.
- **2026-08-15** feat: add `difficulty_profile.py` — persistent, user-declared
  speaker difficulty profile (sounds/words/phrases, kept explicitly
  independent). New `app.py` "Speaker Difficulty Profile" panel replaces the
  old Phoneme-Profile panel and absorbs the redundant Blocklist column.
  Additive-only to the reformulation pipeline: `phonetic.py` gains one new
  informational function, `user_store.py` gains a difficulty-profile store
  that auto-mirrors the legacy `phoneme_profile` fields. Zero changes to
  `grammar.py`/`engine.py`/`semantic.py`/`rewrite/`/`rephrase.py`/
  `profiling/profile.py` — verified via `tests/smoke.py` being
  byte-identical to baseline. New tests: `tests/difficulty_profile_test.py`
  (26 tests); `tests/app_test.py` extended with a live-widget scenario.
  Full design record in `PROBLEM_FORMULATION.md`. → `DECISION_LOG.md`
  2026-08-15-C; `ROADMAP.md` R12–R14.
- **2026-08-15** docs: add `RESEARCH.md` — literature/technical-approach
  review across paraphrase generation, lexical substitution, simplification,
  semantic-preservation evaluation, controlled generation, phoneme-aware
  NLP/speech accessibility, and personalization, plus a component-by-
  component critical assessment of this repo's implementation against it.
  Closes `ROADMAP.md` R3; adds R8–R11. No implementation changed. →
  `DECISION_LOG.md` 2026-08-15-B.
- **2026-08-15** repo: narrow scope to the text reformulation module —
  move `voice.py`, `profiling/asr.py`, `profiling/detect.py`,
  `sample_stutter.json` to `out_of_scope/`; strip the corresponding UI from
  `app.py`; split `tests/roadmap_test.py`; fix README's stale `0.65/0.35`
  semantic-weight description. No rewrite algorithm/threshold/weight
  changed. → `DECISION_LOG.md` 2026-08-15-A.
- **2026-06-13** `11ef678` test: add `sample_stutter.json` fixture for
  profile-update testing without CrisperWhisper.
- **2026-06-13** `7abfe97` docs: v6.0.1 changelog (model-loading
  reliability + low-RAM support). → see `DECISION_LOG.md` 2026-06-08-E.
- **2026-06-13** `d292cfb` feat: fluency rephrase + mic profiling fixes,
  low-RAM model loading. → `DECISION_LOG.md` 2026-06-08-E.
- **2026-06-13** `043b331` merge: resolve conflicts from remote main.
- **2026-06-13** `3c1b5a1` merge: `feature/roadmap-implementation`.
- **2026-06-13** `daba899` docs: README + changes.md for v6.0.0 fluency
  rewrite roadmap.
- **2026-06-13** `fc8bece` feat(eval): add eval harness and roadmap
  regression tests. → `VALIDATION.md` §1.
- **2026-06-13** `8d7cb04` feat(ui): integrate profile-aware rewrite card
  and fluency profile chart into Streamlit app.
- **2026-06-13** `f238e88` feat(prefs): add `profile_rewrite_enabled`
  preference, default true.
- **2026-06-13** `277a205` feat(config): add `config.yaml`, update
  gitignore/requirements for profiling stack.
- **2026-06-13** `09610be` feat(rewrite): add profile-aware rewrite
  engine. → `DOCS.md` (`rewrite/` module), `ROADMAP.md` R5.
- **2026-06-13** `a0b632e` feat(profiling): add fluency profiling, ASR,
  and disfluency detection.
- **2026-06-12** `5648765` Implement roadmap PDF: voice uploads,
  profile-aware rewrites, evaluation harness.
- **2026-06-09** `f0ac889` Optional model added in comments.
- **2026-06-09** `f58ff6d` docs: README update — voice input/output
  support.
- **2026-06-09** `0d2cf0e` Add voice integration and speech improvements.
  → `ROADMAP.md` H1 (unverified `st.iframe` usage).
- **2026-06-09** `0f793b1` Make rephraser clone-and-run: add
  sentencepiece+tiktoken, disable hf-xet to prevent download hangs,
  document teammate setup.
- **2026-06-08** `1855813` Task K: rephrase fine-tuning scaffolding.
- **2026-06-08** `a53eb6b` Task J: deterministic evaluation harness.
  → `VALIDATION.md` §1.
- **2026-06-08** `74d7338` Task I: persist allowlist and rephrase
  preference.
- **2026-06-08** `bdbe6c9` Task H: wire optional fluency rephrase UI.
- **2026-06-08** `2e1a189` Task G: add optional rephrase module
  (`rephrase.py`).
- **2026-06-08** `b0280e1` Task F: repair Streamlit `AppTest` harness.
- **2026-06-08** `b7593f0` Task E: add `tests/threshold_sweep.py`
  diagnostic — recommends `MIN_SEMANTIC~0.80` vs. current `0.85`; default
  left unchanged. → **`DECISION_LOG.md` 2026-06-08-A** (unresolved finding
  — see `ROADMAP.md` R1).
- **2026-06-08** `02b54c4` Task D: smoke WORD MODE mirrors app behavior;
  regenerate `baseline.txt` / `baseline_sbert.txt`.
- **2026-06-08** `b1b71ad` Task C: fix paragraph rebuild off-by-one.
- **2026-06-08** `b04a4a6` Task B: allowlist locks words in place. →
  **`DECISION_LOG.md` 2026-06-08-D**.
- **2026-06-08** `5c8b149` Task A: strip edge punctuation/case in engine
  token split (fixes word-mode "No synonyms found" for trailing-punct
  input).
- **2026-06-08** `39c1d78` Pre-flight: fix `requirements.txt` line
  endings; capture behavior baseline.
- **2026-06-08** `0fecf23` Fix adjective overcorrection, remove double
  `sanitize_input` call, add custom-word phoneme checks, harden word-mode
  renderer. → notable: this is the commit era where the semantic-scoring
  re-weighting (`DECISION_LOG.md` 2026-06-08-B) also happened.
- **2026-06-08** `4904ba2` Upgrade grammar engine: spelling correction +
  LanguageTool integration.
- **2026-06-08** `902c0a8` docs: update `AUTH_README.md`. → contains the
  `.gitignore` claim later found stale, see `DECISION_LOG.md` 2026-06-13-A.
- **2026-06-08** `b0a5c03` docs: update README.
- **2026-06-07** `50f5d18` docs: update README.
- **2026-06-07** `249f107` remove previous preference backup files.
- **2026-06-07** `a465f3c` feat: multi-user architecture, grammar
  rewriting, UI enhancements, semantic rules update. → introduces
  `user_store.py`/`auth.py`, see `DECISION_LOG.md` 2026-06-07-A.
- **2026-06-07** `fc66876` Grammar integration and UI validation fixes.
- **2026-06-07** `cb78157` chore: requirements update.
- **2026-06-07** `fbe9254` feat: stutter-assistance feature, smarter
  grammar, UI polish & fixes.
- **2026-06-07** `bb4afd0` docs: update README.
- **2026-06-07** `f0ca322` chore: add project files.
- **2026-06-06** `8a4498c` Replace project with new content.
- **2026-06-06** `59a4215` docs: update README.
- **2026-06-05** `9361294`, `25af484`, `32624a1`, `d50ad22`, `a5317b7`,
  `31646c3` — bootstrap: initial commit, README, `.gitignore`,
  `requirements.txt`. → `DECISION_LOG.md` 2026-06-05.

---

*This changelog was generated in one backfilling pass on 2026-08-08 from
`git log`. Going forward, per Practice.md §14, new entries should be added
here at commit time, one line per change, pointing to a `DECISION_LOG.md`
entry whenever the change represents a non-trivial decision, result, bug,
or finding rather than routine maintenance.*
