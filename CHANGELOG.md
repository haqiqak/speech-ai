# CHANGELOG.md — Fast-scan index

One line per change, reverse-chronological, backfilled from `git log`
(2026-08-08). Each line points into `DECISION_LOG.md` where a fuller
entry exists; most commits below have no decision-log entry because they
were routine/incremental — per Practice.md §14, the changelog is the fast
index, the decision log is the full record, and not every line needs both.

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
