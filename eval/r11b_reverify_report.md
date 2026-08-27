# Phase 11B — categories 4/6/7, and three real bugs caught during verification

Per approved plan mode: the highest-confidence slice of Phase 10B's
remaining categories 4-7 (`C:\Users\BURRAQ LAPTOPS\.claude\plans\
gleaming-swinging-nova.md`). Implemented: (A) dictionary/real-word
validation on generated output (Category 7), (B) a generalizable
number-word preservation check (Category 6, narrow slice), (C) five
more individually-verified `BLOCKED_SUBSTITUTION_PAIRS` entries for
simple substitution-tier Category 4/5 cases. General POS/subject-verb-
agreement on T5 output and antonym/polarity-without-negation-marker
detection were explicitly deferred (need their own new mechanism, not a
rule fix) — see the plan file's "Explicitly deferred" section.

## Three real bugs found and fixed during this phase's own verification

Following the exact discipline Phase 11's re-verification established
(full 398-run harvest, not just targeted cases, before trusting any
number):

1. **`has_unknown_tokens()`'s first version was too aggressive.**
   pyspellchecker's default wordlist doesn't cover this project's own
   technical-domain vocabulary ("nucleosynthesis", "overnutrition" both
   came back "unknown"), which regressed two previously-CLEAN Phase 10
   escalation outputs (`R10-008`, `R10-030`) to a refusal on the first
   re-harvest. Fixed by requiring BOTH pyspellchecker AND an exact
   WordNet-word-list check to fail before flagging a token (WordNet's
   own `wn.synsets()` was separately found to be too *permissive* for
   this — its morphy-based inflection stripping treats "rockyer" as a
   comparative of "rocky" and "dayss" as a plural of "day", exactly the
   garbled forms this check exists to catch — so this uses exact
   membership in WordNet's raw word list instead, plus a common-prefix/
   lemma fallback for compounds like "overnutrition"/"micronutrients").
   `R10-008` recovered to CLEAN; `R10-030` still correctly refuses on
   this run given its actual (nondeterministic) candidate pool — verified
   directly, not assumed, see Limitations.

2. **`is_number_word_mismatch()`'s closed word-set alone missed digit
   and compound forms.** R10-127's actual candidate pool produced
   `"2nd"` and later `"twenty-third"` for `"third"`, neither of which a
   spelled-out-word-only set catches. Extended to recognize digit/
   digit-ordinal tokens (regex) and hyphenated compounds (all parts
   must be number words) — found and fixed via this phase's own
   re-harvest, not assumed complete after the first implementation.

3. **A real, previously-unknown root-cause bug in `grammar.inflect()`.**
   `R10-121`'s `"weekdays"` → `"dayss"` (a literal garbled duplicate-s
   token) traced to `inflect()`'s NNS fallback (`lemma + "s"`)
   unconditionally appending "s" even when the candidate lemma from
   Datamuse was already plural (`"days"`, since `pyinflect.
   getInflection("days", "NNS")` returns `None` for an already-plural
   input). Fixed at the source: the fallback now returns the lemma
   unchanged if it already ends in "s". This is a general pipeline fix,
   not scoped to escalation/phrase-tier output — `has_unknown_tokens()`
   was also wired into `_try_substitution()`'s loop as a result, since
   this specific defect class turned out NOT to be escalation-exclusive
   as the original plan assumed.

## A known, disclosed limit found (not chased further)

Two words — `"third"` (R10-127) and `"single"` (R10-108) — produced a
NEW distinct bad candidate every time the previous one was blocked
(`third`: fourth → 2nd → twenty-third → tertiary; `single`: one → 1 →
one-on-one → several), even after fixing the number-word gap above.
This is the blocklist approach's known convergence limit made concrete:
these two words have unusually large "semantically-near but
contextually-wrong" candidate pools that no amount of one-off pair-
blocking will exhaust. Recorded here as an evidenced limitation
requiring real word-sense disambiguation (Category 4/5's deferred
"needs new mechanism" territory), not continued patched — the specific
bad pairs actually observed are still blocked (real, if incomplete,
progress), but no further pairs were added for these two words.

## Result

Full 398-run harvest (`eval/r11_reverify_harvest.py`, reused as-is)
re-run three times during this phase (once per bug fix above) before
trusting any number; final diff against `eval/r10_raw_results.json`:
**111 runs changed.** Status transitions: 96 `reformulated →
reformulated`, 14 `reformulated → could_not_safely_reformulate` (13 of
14 were previously DEFECTIVE), 1 `could_not_safely_reformulate →
reformulated`.

**97 runs still `reformulated` after the change were blind-judged**
(4 independent parallel subagents, same no-metadata discipline as
Phase 10/Phase 11): **17 CLEAN, 80 DEFECTIVE (61 SEVERE, 19 MINOR).**

Transition against Phase 10's original judgment: **17 DEFECTIVE→CLEAN**
genuine fixes (including `R10-079` ×3, the `everyone`→`entire` fix;
`R10-001` ×3, duplicate-word fixes; `R10-099`, `anyone`→`guy`),
72 DEFECTIVE→DEFECTIVE (changed but still defective), **8 apparent
regressions** (7 CLEAN→DEFECTIVE + 1 CLEAN→refused) — **every one of
which traces to this project's already-documented candidate-pool/T5
nondeterminism** (`R10-024`, `R10-049` ×2, `R10-097` ×3, `R10-123`,
`R10-030`), confirmed by checking that none of the affected words or
mechanisms overlap with anything Phase 11B's new code touches. This is
disclosed plainly, not minimized: it means re-running the same harvest
twice can shuffle a small number of cases either direction on words
none of this phase's code changed, independent of any actual defect fix.

**Overall CLEAN rate among all currently-`reformulated` runs: 71/225
(31.6%)** — up from Phase 10's 26.1% baseline, essentially flat against
Phase 11's own 32.6% (a ~1-point dip, within the noise band the
nondeterminism finding above establishes, not a regression from this
phase's changes). The still-DEFECTIVE population's primary-defect
breakdown (WRONG_WORD_OR_SENSE 42, GRAMMAR 11, FIXED_TERM_OR_IDIOM 6,
NATURALNESS_OR_REGISTER 8, FACTUAL_OR_LOGICAL_REVERSAL 5) still matches
the same shape Phase 11's re-verification found — consistent with the
explicitly-deferred categories (general T5-output grammar/agreement
checking, polarity detection without negation markers) being the
correct next-largest lever, not a new pattern this pass missed.

## Limitations

- Blind judges (this pass's 4, Phase 11's 4, Phase 10's 5) are all
  Claude instances, same epistemic status as every prior labeling pass.
- **New methodological finding this phase**: re-running the identical
  398-run harvest with NO code change between runs can itself change a
  small number of individual outcomes (confirmed directly for `R10-030`,
  `R10-049`, and others) — this project's Datamuse-network-dependent
  and T5-sampling-dependent candidate pools are not perfectly
  deterministic across process launches. Comparing raw CLEAN-rate
  percentages between two separate harvest runs therefore carries
  genuine noise on the order of at least 1 percentage point; treat
  single-run deltas below that as inconclusive, not as evidence of a
  regression or improvement, without checking the underlying cases
  directly (as this report did).
- `"third"`/`"single"`'s unconverged candidate pools (see above) are a
  concrete illustration that the blocklist mechanism has a real ceiling
  for high-collision words — worth keeping in mind when scoping any
  future blocklist-only fix.
