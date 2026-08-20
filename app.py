"""
Speech AI — Streamlit UI v8

Redesigned around the consolidated reformulation engine (reformulate.py,
Architecture D', REFORMULATION_RESEARCH.md SS24-31). Replaces the old
dual-pipeline UI (word-picker dropdowns, separate word/sentence/multi-
sentence modes, profile-rewrite card, rephrase card, allowlist panel) with
a single linear workflow:

    enter/paste text -> view your difficulty profile -> Reformulate ->
    review changes, skipped spans, and verification

grammar.py::SentenceRewriter and rewrite/rewriter.py::DifficultyAwareRewriter
are kept in the repo (not deleted — see REFORMULATION_RESEARCH.md SS30's
migration plan) but are no longer imported here. The learned, session-based
SpeakerDifficultyProfile chart is also dropped from this UI: with the
audio/ASR pipeline out of scope (out_of_scope/), onset_observations never
receives real data, so that chart was silently just re-displaying the same
declared sounds already shown in the Speaker Difficulty Profile panel below
— duplicate, not learned, and worth removing rather than keeping as
decoration.
"""

import paths  # noqa: F401
import html
import re

import streamlit as st
from nltk import word_tokenize

from grammar import sanitize_input, _detokenize
import semantic as sem
import phonetic as ph
from difficulty_profile import DifficultyProfile, extract_candidate_words, record_feedback, undo_feedback
import profile_store
import reformulate

st.set_page_config(
    page_title="Speech AI",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="expanded",
)

CURRENT_PROFILE = profile_store.DEFAULT_PROFILE


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt(text: object) -> str:
    return html.escape(str(text or ""))


def _difficulty_profile() -> DifficultyProfile:
    """Load (once per session, cached) the persistent, user-declared
    difficulty profile — sounds/words/phrases, kept explicitly independent
    of the reformulation engine's internals."""
    cached = st.session_state.get("difficulty_profile")
    if cached is not None and getattr(cached, "profile_name", None) == CURRENT_PROFILE:
        return cached
    profile = DifficultyProfile.load(CURRENT_PROFILE)
    st.session_state.difficulty_profile = profile
    return profile


def _save_difficulty_profile(profile: DifficultyProfile) -> None:
    profile.save()


_DIFFICULTY_ADDERS = {
    "sound": lambda p, t, s: p.add_sound(t, s),
    "word": lambda p, t, s: p.add_word(t, s),
    "phrase": lambda p, t, s: p.add_phrase(t, s),
}


def _feedback_badge(entry) -> str:
    """Small, visible readout of ROADMAP.md R9's accumulated Keep/Revert
    counts for one entry — empty string if the entry has never triggered
    a change the user has toggled. Kept transparent rather than silent:
    the data exists in the profile file either way, so hiding it from the
    UI would make it unverifiable, not just unused."""
    fb = entry.meta.get("feedback")
    if not fb or not (fb.get("kept") or fb.get("reverted")):
        return ""
    return (
        f' <span style="opacity:.6;font-size:.74rem" '
        f'title="How often changes tied to this entry have been kept vs. reverted">'
        f'(✓{fb.get("kept", 0)} ↺{fb.get("reverted", 0)})</span>'
    )


def _render_difficulty_category(
    profile: DifficultyProfile,
    category: str,
    entries: list,
    add_placeholder: str,
    add_help: str,
    key_prefix: str,
) -> None:
    """Render one category (sounds / words / phrases): existing entries with
    a remove button each, then an add text-input + button."""
    if entries:
        for entry in entries:
            col_item, col_rm = st.columns([4, 1])
            with col_item:
                extra = ""
                if category == "word" and entry.pronunciation:
                    extra = f' <span style="opacity:.55;font-size:.78rem">/{" ".join(entry.pronunciation)}/</span>'
                elif category == "sound" and entry.normalized:
                    extra = f' <span style="opacity:.55;font-size:.78rem">/{entry.normalized.replace(" ", "")}/</span>'
                if category == "sound" and entry.meta.get("legacy_bridge_unreliable"):
                    extra += (
                        ' <span style="opacity:.85;font-size:.74rem;color:#b3541e" '
                        'title="This exact sound may not be fully enforced by the current '
                        'engine yet — a known limitation, not a bug in your entry.">'
                        '⚠️ not fully enforced yet</span>'
                    )
                extra += _feedback_badge(entry)
                st.markdown(
                    f'<span class="blocklist-item">🚫 {_fmt(entry.value)}</span>{extra}',
                    unsafe_allow_html=True,
                )
            with col_rm:
                if st.button("✕", key=f"{key_prefix}_rm_{entry.normalized}", type="secondary",
                             help=f"Remove \"{entry.value}\""):
                    profile.remove(category, entry.normalized)
                    _save_difficulty_profile(profile)
                    st.rerun()
    else:
        st.caption("None yet.")

    add_text = st.text_input(
        f"Add {category}",
        key=f"{key_prefix}_add_input",
        placeholder=add_placeholder,
        help=add_help,
        label_visibility="collapsed",
    )
    if st.button("Add", key=f"{key_prefix}_add_btn", type="secondary"):
        entry, status = _DIFFICULTY_ADDERS[category](profile, add_text, "user_typed")
        if status == "added":
            _save_difficulty_profile(profile)
            st.success(f'Added "{entry.value}" to your difficult {category}s.')
            st.rerun()
        elif status == "duplicate":
            st.info(f'"{add_text.strip()}" is already in your difficult {category}s.')
        else:
            st.warning("Enter something first.")


def _render_words_category(profile: DifficultyProfile) -> None:
    """Words column: same add/remove pattern as sounds/phrases, plus a
    per-entry 'what's specifically difficult about this word?' toggle.

    Flagging a word never implies every sound in it is difficult — the
    toggle lets the user optionally narrow down to a specific sound/pattern
    *within this word*, scoped to the word, never auto-promoted to a global
    sound difficulty unless explicitly checked.
    """
    for entry in profile.words:
        col_item, col_pattern, col_rm = st.columns([3, 1, 1])
        with col_item:
            extra = ""
            if entry.pronunciation:
                extra = f' <span style="opacity:.55;font-size:.78rem">/{" ".join(entry.pronunciation)}/</span>'
            if entry.problem_phones:
                extra += (
                    f' <span style="opacity:.8;font-size:.76rem;color:#c2660f">'
                    f'— specifically: {_fmt(", ".join(entry.problem_phones))}</span>'
                )
            if entry.meta.get("has_alternate_pronunciations"):
                extra += (
                    ' <span style="opacity:.85;font-size:.74rem;color:#b3541e" '
                    'title="This word has more than one pronunciation (e.g. different tenses or senses). '
                    'The sounds shown are for the most common one and may not match what you meant.">'
                    '⚠️ has multiple pronunciations</span>'
                )
            extra += _feedback_badge(entry)
            st.markdown(
                f'<span class="blocklist-item">🚫 {_fmt(entry.value)}</span>{extra}',
                unsafe_allow_html=True,
            )
        with col_pattern:
            pattern_disabled = not entry.pronunciation
            if st.button(
                "🔍", key=f"dp_word_pattern_toggle_{entry.normalized}", type="secondary",
                disabled=pattern_disabled,
                help=("What's specifically difficult about this word?" if not pattern_disabled
                      else "Pronunciation unknown for this word — can't pick a specific sound."),
            ):
                current = st.session_state.get("dp_pattern_target")
                st.session_state["dp_pattern_target"] = None if current == entry.normalized else entry.normalized
                st.rerun()
        with col_rm:
            if st.button("✕", key=f"dp_word_rm_{entry.normalized}", type="secondary",
                         help=f'Remove "{entry.value}"'):
                profile.remove("word", entry.normalized)
                _save_difficulty_profile(profile)
                if st.session_state.get("dp_pattern_target") == entry.normalized:
                    st.session_state["dp_pattern_target"] = None
                st.rerun()
    if not profile.words:
        st.caption("None yet.")

    add_text = st.text_input(
        "Add word", key="dp_word_add_input",
        placeholder="e.g. particular",
        help="A specific word that's difficult for you — regardless of whether "
             "its sounds are individually flagged above.",
        label_visibility="collapsed",
    )
    if st.button("Add", key="dp_word_add_btn", type="secondary"):
        entry, status = profile.add_word(add_text, "user_typed")
        if status == "added":
            _save_difficulty_profile(profile)
            st.session_state["dp_pattern_target"] = entry.normalized
            st.success(f'Added "{entry.value}" to your difficult words.')
            st.rerun()
        elif status == "duplicate":
            st.info(f'"{add_text.strip()}" is already in your difficult words.')
        else:
            st.warning("Enter something first.")


def _render_pattern_editor(profile: DifficultyProfile, entry) -> None:
    """Full-width, inline 'what's difficult about this word?' panel.

    Deliberately NOT st.dialog: Streamlit's AppTest has a documented, open
    bug where button clicks inside an st.dialog never execute during
    testing (streamlit/streamlit#9786) — this project tests every shipped
    interaction, so a plain inline panel toggled by session state is used
    instead.
    """
    if not entry.pronunciation:
        st.info(f'Pronunciation unknown for "{entry.value}" — can\'t pick a specific sound.')
        return

    st.markdown(
        f'<div class="pattern-editor">'
        f'<div style="font-size:.85rem;font-weight:700;color:#8a5a12">'
        f'🔍 What\'s difficult about "{_fmt(entry.value)}"?</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Optional — leave nothing selected to keep this as a whole-word "
        "difficulty. Check only the sound(s) that are specifically the problem."
    )
    if len(set(entry.pronunciation)) != len(entry.pronunciation):
        st.caption(
            "This word repeats a sound — checking one occurrence marks that "
            "sound as the problem *anywhere it appears in this word*, not "
            "just that one spot."
        )

    already = set(entry.problem_phones or ())
    selected: list[str] = []
    for i, phone in enumerate(entry.pronunciation):
        checked = st.checkbox(
            ph.friendly_phone_label(phone),
            value=phone in already,
            key=f"dp_pattern_phone_{entry.normalized}_{i}",
        )
        if checked:
            selected.append(phone)

    promote = st.checkbox(
        "Also add the selected sound(s) as a difficulty everywhere "
        "(a GLOBAL sound, not just for this word)",
        value=False,
        key=f"dp_pattern_promote_{entry.normalized}",
        disabled=not selected,
    )

    col_save, col_clear, col_close = st.columns(3)
    with col_save:
        if st.button("Save", key=f"dp_pattern_save_{entry.normalized}",
                      type="primary", disabled=not selected):
            if profile.set_word_pattern(entry.normalized, selected):
                if promote:
                    profile.add_sound_from_phones(selected, source="user_typed")
                _save_difficulty_profile(profile)
                st.session_state["dp_pattern_target"] = None
                st.success(
                    f'Saved — "{entry.value}" is specifically difficult because of '
                    f'{", ".join(selected)}.'
                )
                st.rerun()
    with col_clear:
        if st.button("Clear pattern", key=f"dp_pattern_clear_{entry.normalized}",
                      type="secondary", disabled=entry.problem_phones is None):
            profile.clear_word_pattern(entry.normalized)
            _save_difficulty_profile(profile)
            st.rerun()
    with col_close:
        if st.button("Close", key=f"dp_pattern_close_{entry.normalized}", type="secondary"):
            st.session_state["dp_pattern_target"] = None
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _risk_preview(text: str, profile: DifficultyProfile) -> str:
    """Cheap, regex-tokenized (no POS tagging) preview of which words in
    the current text are flagged by the profile right now — shown before
    Reformulate is clicked so the workflow's step 2 -> step 3 connection is
    visible, not just implied."""
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    if not words:
        return ""
    sounds = profile.sound_values()
    blocked = set(profile.word_values())
    chips = []
    for w in words:
        flagged = (w.lower() in blocked) or ph.matches_any(w, sounds)
        cls = "risk-hi" if flagged else "risk-lo"
        chips.append(f'<span class="risk-chip {cls}">{_fmt(w)}</span>')
    return '<div class="pill-wrap">' + "".join(chips) + "</div>"


def _apply_change_choices(result: dict, choices: dict[int, bool]) -> str:
    """Rebuild the final text from result['original_text'], honoring which
    changes the user has kept vs. reverted. `choices[i]` is True (keep,
    the default) or False (revert this one change to its original)."""
    sentences = reformulate.split_sentences(result["original_text"])
    by_sentence: dict[int, list[tuple[int, dict]]] = {}
    for i, change in enumerate(result["changes"]):
        by_sentence.setdefault(change["sentence_index"], []).append((i, change))

    rebuilt = []
    for sid, original_sentence in enumerate(sentences):
        sentence_changes = by_sentence.get(sid)
        if not sentence_changes:
            rebuilt.append(original_sentence)
            continue
        if sentence_changes[0][1]["source"] in ("restructuring", "phrase"):
            # Both are sentence-scoped changes (original/replacement are
            # full sentences, not a single token) -- phrase-tier changes
            # (§5 item 4) replace only part of the sentence internally,
            # but revert/keep still operates at the whole-sentence level,
            # same as restructuring.
            i, change = sentence_changes[0]
            keep = choices.get(i, True)
            rebuilt.append(change["replacement"] if keep else change["original"])
            continue
        tokens = word_tokenize(original_sentence)
        for i, change in sentence_changes:
            if choices.get(i, True):
                tokens[change["position"]] = change["replacement"]
        rebuilt.append(_detokenize(tokens))
    return " ".join(rebuilt)


def _record_change_feedback(profile: DifficultyProfile, change: dict, new_keep: bool, change_index: int) -> None:
    """Wire a Keep/Revert toggle into the declared entries responsible for
    it (ROADMAP.md R9's feedback loop — recording only; nothing in
    reformulate.py reads this yet). Undoes any prior vote for this same
    change first, so re-toggling reflects the user's current choice, not
    a running click count. A no-op for changes reformulate.feedback_targets
    can't attribute to a specific entry (e.g. restructuring)."""
    targets = reformulate.feedback_targets(change, profile)
    if not targets:
        return
    prior = st.session_state.recorded_feedback.get(change_index)
    if prior is not None:
        for t in targets:
            undo_feedback(t, kept=prior)
    for t in targets:
        record_feedback(t, kept=new_keep)
    st.session_state.recorded_feedback[change_index] = new_keep
    _save_difficulty_profile(profile)


# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

html,body,[class*="css"]{font-family:'DM Sans',sans-serif;background:#f7fbff;color:#1a2740}
.block-container{padding-top:1.5rem;padding-bottom:4rem;max-width:820px}

.hero{text-align:center;padding:1.6rem 1rem .9rem}
.hero h1{font-family:'DM Serif Display',serif;font-size:2.5rem;color:#1a2740;letter-spacing:-.5px;margin-bottom:.1rem}
.hero h1 span{color:#f57c2b}
.hero p{font-size:.95rem;color:#5a7096;font-weight:300;margin-top:.15rem}

.step-kicker{font-size:.68rem;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:#4b91dc;margin:1.1rem 0 .45rem}

div[data-testid="stTextInput"] input{border:2px solid #c3daf7!important;border-radius:14px!important;background:#fff!important;font-family:'DM Sans',sans-serif!important;font-size:1.05rem!important;padding:.66rem 1rem!important;color:#1a2740!important;box-shadow:0 2px 10px rgba(75,145,220,.07)!important}
div[data-testid="stTextInput"] input:focus{border-color:#4b91dc!important}
div[data-testid="stTextInput"] label{font-size:.82rem!important;font-weight:600!important;color:#3d6ea8!important}
div[data-testid="stTextArea"] textarea{min-height:130px!important;border:2px solid #c3daf7!important;border-radius:16px!important;background:#fff!important;font-family:'DM Sans',sans-serif!important;font-size:1.06rem!important;line-height:1.6!important;padding:.9rem 1rem!important;color:#1a2740!important;box-shadow:0 2px 12px rgba(75,145,220,.08)!important}
div[data-testid="stTextArea"] textarea:focus{border-color:#4b91dc!important}
div[data-testid="stTextArea"] label{font-size:.82rem!important;font-weight:600!important;color:#3d6ea8!important}
div[data-testid="stSlider"] label{font-size:.82rem!important;color:#3d6ea8!important;font-weight:600!important}

div.stButton>button{background:linear-gradient(135deg,#f57c2b,#f4a461)!important;color:#fff!important;border:none!important;border-radius:12px!important;font-family:'DM Sans',sans-serif!important;font-size:1rem!important;font-weight:600!important;padding:.6rem 2rem!important;box-shadow:0 4px 14px rgba(245,124,43,.22)!important;transition:transform .15s,box-shadow .15s!important}
div.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 6px 20px rgba(245,124,43,.33)!important}
div.stButton>button[kind="secondary"]{background:#f0f4f8!important;color:#5a7096!important;box-shadow:none!important;font-size:.85rem!important;padding:.4rem 1rem!important}
div.stButton>button[kind="secondary"]:hover{background:#e4eaf2!important;transform:none!important}

.profile-panel{background:#fff;border:1.5px solid #d4e8f8;border-radius:16px;padding:1rem 1.2rem .85rem;margin:.55rem 0 .9rem;box-shadow:0 2px 12px rgba(75,145,220,.05)}
.pipe-label{font-size:.68rem;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:#4b91dc;margin-bottom:.38rem}

.pill-wrap{display:flex;flex-wrap:wrap;gap:.35rem}
.risk-chip{display:inline-block;padding:.22rem .7rem;border-radius:20px;font-size:.85rem;font-weight:500;cursor:default}
.risk-hi{background:#fef2f2;color:#9b1c1c;border:1.4px solid #f3b4b4}
.risk-lo{background:#edfaf2;color:#1a6b3c;border:1.4px solid #b6e6c9}

.blocklist-item{display:inline-flex;align-items:center;gap:.3rem;background:#fff2e8;border:1.2px solid #f7c49a;border-radius:20px;padding:.2rem .65rem;font-size:.85rem;color:#c85d14;margin:.15rem}
.pattern-editor{background:#fbf6ec;border:1.4px solid #f0dcae;border-radius:12px;padding:.7rem .9rem;margin:.5rem 0}

.status-banner{border-radius:12px;padding:.75rem 1rem;font-size:.92rem;margin:.6rem 0;font-weight:500}
.status-ok{background:#edfaf2;border:1.4px solid #7ddba5;color:#1a6b3c}
.status-warn{background:#fff8ed;border:1.4px solid #f7c49a;color:#a06030}
.status-error{background:#fef2f2;border:1.4px solid #fca5a5;color:#991b1b}

.output-box{background:linear-gradient(135deg,#fff8f2,#f0f7ff);border:2px solid #f0c090;border-radius:16px;padding:1.05rem 1.35rem;font-size:1.12rem;color:#1a2740;line-height:1.75;font-family:'DM Serif Display',serif}

.change-card{background:#fff;border:1.5px solid #d4e8f8;border-radius:14px;padding:.8rem 1rem;margin-bottom:.6rem}
.change-arrow{display:flex;align-items:center;gap:.5rem;font-size:1.02rem;flex-wrap:wrap}
.change-before{color:#9b1c1c;text-decoration:line-through;opacity:.7}
.change-after{color:#1a6b3c;font-weight:600}
.change-tag{font-size:.68rem;font-weight:700;letter-spacing:.4px;text-transform:uppercase;padding:.14rem .5rem;border-radius:12px;background:#e8f2fc;color:#2d6aab}
.change-tag.restructuring{background:#fff2e8;color:#c85d14}
.change-tag.phrase{background:#f3ecfb;color:#6b3fa0}

.skip-chip{display:inline-flex;align-items:center;gap:.35rem;background:#fdf7f3;border:1.2px dashed #f7c49a;border-radius:9px;padding:.3rem .7rem;font-size:.85rem;color:#a06030;margin:.15rem 0}

.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.6rem;margin-top:.5rem}
.metric-box{background:#f8fbff;border:1.4px solid #d4e8f8;border-radius:12px;padding:.6rem .8rem;text-align:center}
.metric-num{font-family:'DM Serif Display',serif;font-size:1.35rem;color:#1a2740}
.metric-label{font-size:.72rem;color:#5a7096;text-transform:uppercase;letter-spacing:.4px;margin-top:.1rem}

.sbert-on{background:#edfaf2;border:1.4px solid #7ddba5;border-radius:11px;padding:.55rem .9rem;color:#1a6b3c;font-size:.88rem;margin-bottom:.6rem}
.sbert-off{background:#fff8ed;border:1.4px solid #f7c49a;border-radius:11px;padding:.55rem .9rem;color:#a06030;font-size:.88rem;margin-bottom:.6rem}

.copy-box{background:#f8fbff;border:1.5px solid #b8d9f5;border-radius:12px;padding:.75rem 1rem;font-size:1rem;color:#1a2740;line-height:1.7;font-family:'DM Serif Display',serif;margin-top:.4rem}

hr{border:none;border-top:1.5px solid #deeaf7;margin:1.2rem 0}
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>Speech <span>AI</span></h1>
  <p>Rewrites your text to be easier for you to say — without changing what it means</p>
</div>
""", unsafe_allow_html=True)

# ── SBERT init ─────────────────────────────────────────────────────────────────
@st.cache_resource
def init_sbert():
    sem.load_sbert()
    return sem.sbert_status()

sbert_ok, sbert_msg = init_sbert()

# ── Session state defaults ──────────────────────────────────────────────────
for key, default in [
    ("query_input", ""), ("reformulate_result", None),
    ("reformulate_source_text", None), ("change_choices", {}),
    ("grammar_fixes", []), ("session_history", []),
    ("recorded_feedback", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙ Settings")
    if sbert_ok:
        st.markdown("""<div class="sbert-on"><strong>🧠 Meaning screen active</strong><br>
<span style="font-size:.82rem">Every change is screened for meaning drift with SBERT similarity — an
automated estimate, not a guarantee. It can still miss changes that break an
idiom or pick the wrong sense of a word; review the Changes list yourself.</span></div>""",
            unsafe_allow_html=True)
    else:
        st.markdown("""<div class="sbert-off"><strong>⚠ Meaning screen offline</strong><br>
<span style="font-size:.82rem">SBERT unavailable — changes aren't screened for meaning drift right now.</span></div>""",
            unsafe_allow_html=True)

    with st.expander("Advanced", expanded=False):
        sem_threshold = st.slider(
            "Meaning-preservation strictness", min_value=0.60, max_value=0.95,
            value=0.85, step=0.01, disabled=not sbert_ok,
            help="How similar a reformulation must stay to your original meaning, "
                 "by an automated SBERT estimate — not a human judgment. Lower this "
                 "if changes seem too conservative; raising it doesn't guarantee "
                 "catching an idiom or phrase-level meaning change.",
        )
        top_k = st.slider(
            "Candidates considered per word", min_value=5, max_value=20, value=10, step=1,
        )

    st.markdown("---")
    st.markdown("""<div style="font-size:.75rem;color:#6f87a6">
<strong style="color:#4b91dc">How it works</strong><br>
Words and sounds you've flagged get replaced with easier alternatives that
keep your meaning (checked with SBERT) and avoid antonyms (checked with
WordNet). If a sentence has too many flagged spots to patch word-by-word,
the whole sentence is reworded instead and re-checked the same way. If
nothing passes verification, that part is left unchanged rather than
guessed at.
<br><br>
<strong style="color:#4b91dc">Known limits</strong><br>
The meaning check can still miss it when a change breaks a fixed
expression (e.g. "how's it going") or a common phrase like "right now"
picks the wrong sense of a word. Multiple changes in one short sentence
are more likely to interact and read oddly together than a single
change. Treat the result as a strong first draft, not a final check.
</div>""", unsafe_allow_html=True)

# ── Step 1: text entry ───────────────────────────────────────────────────────
st.markdown('<div class="step-kicker">Step 1 · Your text</div>', unsafe_allow_html=True)
query = st.text_area(
    "Enter or paste text",
    value=st.session_state.get("query_input", ""),
    placeholder="Type a sentence or paste a paragraph — Speech AI handles both.",
    key="query_input",
    label_visibility="collapsed",
)

# ── Step 2: difficulty profile ───────────────────────────────────────────────
st.markdown('<div class="step-kicker">Step 2 · Your difficulty profile</div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="profile-panel">', unsafe_allow_html=True)
    st.caption(
        "What's difficult for you, declared once and reused every time. Sounds, "
        "words, and phrases are tracked **separately** — flagging a word doesn't "
        "assume every sound in it is difficult too."
    )
    difficulty_profile = _difficulty_profile()

    dp_sounds, dp_words, dp_phrases = st.columns(3)
    with dp_sounds:
        st.markdown("**🔊 Sounds** *(starting sound)*")
        _render_difficulty_category(
            difficulty_profile, "sound", difficulty_profile.sounds,
            add_placeholder="e.g. str, pr, b",
            add_help="A starting-sound cue, not a whole word — matched by "
                     "pronunciation, not spelling ('c' and 'k' count the same).",
            key_prefix="dp_sound",
        )
    with dp_words:
        st.markdown("**📝 Words** *(specific words)*")
        _render_words_category(difficulty_profile)
        _candidates = extract_candidate_words(query)
        if _candidates:
            st.caption("Or pick a word from your text:")
            _pick_col, _btn_col = st.columns([3, 1])
            with _pick_col:
                _picked = st.selectbox(
                    "Pick from text", options=_candidates,
                    key="dp_word_pick", label_visibility="collapsed",
                )
            with _btn_col:
                if st.button("Flag", key="dp_word_pick_btn"):
                    entry, status = difficulty_profile.add_word(_picked, source="user_selected_from_text")
                    if status == "added":
                        _save_difficulty_profile(difficulty_profile)
                        st.session_state["dp_pattern_target"] = entry.normalized
                        st.success(f'Added "{entry.value}" from your text.')
                        st.rerun()
                    elif status == "duplicate":
                        st.info(f'"{_picked}" is already flagged.')
    with dp_phrases:
        st.markdown("**💬 Phrases** *(multi-word)*")
        _render_difficulty_category(
            difficulty_profile, "phrase", difficulty_profile.phrases,
            add_placeholder="e.g. through the research",
            add_help="A multi-word phrase that's difficult as a whole, even if "
                     "no single word in it is individually flagged.",
            key_prefix="dp_phrase",
        )

    _pattern_target = st.session_state.get("dp_pattern_target")
    if _pattern_target:
        _pattern_entry = difficulty_profile.find_word(_pattern_target)
        if _pattern_entry is not None:
            _render_pattern_editor(difficulty_profile, _pattern_entry)
        else:
            st.session_state["dp_pattern_target"] = None

    if query.strip():
        preview_html = _risk_preview(query, difficulty_profile)
        if preview_html:
            st.markdown(
                '<div class="pipe-label" style="margin-top:.7rem">In your text right now</div>'
                + preview_html,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

# ── Step 3: reformulate ──────────────────────────────────────────────────────
st.markdown('<div class="step-kicker">Step 3 · Reformulate</div>', unsafe_allow_html=True)
_, col1, _ = st.columns([1, 2, 1])
with col1:
    reformulate_clicked = st.button("Reformulate", use_container_width=True)

if reformulate_clicked and not query.strip():
    st.warning("Enter some text first.")

if reformulate_clicked and query.strip():
    sem.MIN_SEMANTIC = sem_threshold
    corrected_text, grammar_fixes = sanitize_input(query.strip())
    settings = reformulate.ReformulateSettings(
        sbert_threshold=sem_threshold, top_k=top_k,
    )
    with st.spinner("Reformulating…"):
        result = reformulate.reformulate(corrected_text, difficulty_profile, settings)
    st.session_state.reformulate_result = result
    st.session_state.reformulate_source_text = query.strip()
    st.session_state.grammar_fixes = [
        f for f in grammar_fixes if f.get("original") != f.get("corrected")
    ]
    st.session_state.change_choices = {}
    st.session_state.recorded_feedback = {}
    st.rerun()

# ── Step 4: review ────────────────────────────────────────────────────────────
result = st.session_state.get("reformulate_result")
if result is not None:
    st.markdown('<div class="step-kicker">Step 4 · Review</div>', unsafe_allow_html=True)

    if query.strip() != st.session_state.get("reformulate_source_text"):
        st.markdown(
            '<div class="status-banner status-warn">Your text has changed since this '
            'result was generated — click Reformulate again to update it.</div>',
            unsafe_allow_html=True,
        )

    if st.session_state.grammar_fixes:
        with st.expander(f"✏️ Spelling/grammar fixes applied ({len(st.session_state.grammar_fixes)})",
                          expanded=False):
            for fix in st.session_state.grammar_fixes:
                st.markdown(
                    f'<span style="text-decoration:line-through;opacity:.55">{_fmt(fix.get("original"))}</span> '
                    f'&rarr; <strong>{_fmt(fix.get("corrected"))}</strong> '
                    f'<span style="opacity:.6;font-size:.82rem">— {_fmt(fix.get("reason") or fix.get("description") or "")}</span>',
                    unsafe_allow_html=True,
                )

    status = result["status"]
    if status == "no_change_needed":
        st.markdown(
            '<div class="status-banner status-ok">✓ Nothing in this text matched your '
            'difficulty profile — no changes needed.</div>', unsafe_allow_html=True,
        )
    elif status == "reformulated":
        st.markdown(
            '<div class="status-banner status-ok">✓ Reformulated — review the changes below.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-banner status-error">⚠ Some parts of this text matched your '
            'difficulty profile, but no change could be made without risking the meaning. '
            'Those parts were left as written — see "Left unchanged" below.</div>',
            unsafe_allow_html=True,
        )

    final_text = _apply_change_choices(result, st.session_state.change_choices) if result["changes"] else result["reformulated_text"]

    st.markdown(f'<div class="output-box">{_fmt(final_text)}</div>', unsafe_allow_html=True)
    st.caption("📋 Copy:")
    st.code(final_text, language=None)

    if result["changes"]:
        st.markdown("#### Changes")
        for i, change in enumerate(result["changes"]):
            keep = st.session_state.change_choices.get(i, True)
            tag_cls = change["source"] if change["source"] in ("restructuring", "phrase") else ""
            col_text, col_toggle = st.columns([5, 1])
            with col_text:
                st.markdown(
                    f'<div class="change-card">'
                    f'<span class="change-tag {tag_cls}">{change["source"]}</span> '
                    f'<div class="change-arrow">'
                    f'<span class="change-before">{_fmt(change["original"])}</span>'
                    f'<span>&rarr;</span>'
                    f'<span class="change-after">{_fmt(change["replacement"])}</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            with col_toggle:
                new_keep = st.checkbox("Keep", value=keep, key=f"change_keep_{i}")
                if new_keep != keep:
                    st.session_state.change_choices[i] = new_keep
                    _record_change_feedback(difficulty_profile, change, new_keep, i)
                    st.rerun()

            v = change["verification"]
            fit = v.get("contextual_fit")
            fit_line = (
                f"\n- Contextual fit (word naturalness, diagnostic only): **{fit:.4f}**"
                if fit is not None else ""
            )
            with st.expander("Why this change / verification", expanded=False):
                st.markdown(
                    f"- Triggered by: **{', '.join(change['triggered_by'])}**\n"
                    f"- Meaning similarity (SBERT): **{v['sbert_sim'] if v['sbert_sim'] is not None else 'n/a'}**\n"
                    f"- Antonym check: **{v['antonym_check']}**\n"
                    f"- Difficulty score: **{v['difficulty_before']} → {v['difficulty_after']}**"
                    f"{fit_line}"
                )

    if result["skipped"]:
        st.markdown("#### Left unchanged")
        for s in result["skipped"]:
            st.markdown(
                f'<div class="skip-chip">⊘ <strong>{_fmt(s["word"])}</strong>'
                f'<span style="opacity:.75"> — {_fmt(s["reason"])}</span></div>',
                unsafe_allow_html=True,
            )

    m = result["metrics"]
    fv = result["final_verification"]
    st.markdown("#### Verification")
    mp = m["meaning_preservation"]
    mb = m.get("meaning_preservation_meaningbert")
    st.markdown(f"""
<div class="metric-grid">
  <div class="metric-box">
    <div class="metric-num">{f"{mp:.0%}" if mp is not None else "n/a"}</div>
    <div class="metric-label">Meaning similarity (SBERT)</div>
  </div>
  <div class="metric-box">
    <div class="metric-num">{f"{mb:.0f}/100" if mb is not None else "n/a"}</div>
    <div class="metric-label">Meaning similarity (MeaningBERT)</div>
  </div>
  <div class="metric-box">
    <div class="metric-num">{m['difficulty_reduction_pct']:.0f}%</div>
    <div class="metric-label">Difficulty reduced</div>
  </div>
  <div class="metric-box">
    <div class="metric-num">{m['naturalness_edit_ratio']:.0%}</div>
    <div class="metric-label">Text changed</div>
  </div>
  <div class="metric-box">
    <div class="metric-num">{"✓" if fv["passed"] else "⚠"}</div>
    <div class="metric-label">Final check</div>
  </div>
</div>""", unsafe_allow_html=True)
    st.caption(
        "These are automated estimates (SBERT similarity, edit distance, and — "
        "since 2026-08-19 — MeaningBERT, a second, independently-trained meaning "
        "signal), not a human judgment of quality. The two meaning-similarity "
        "scores can disagree — validated to each catch some breaks the other "
        "misses, not one strictly better than the other — so treat a "
        "disagreement between them as a reason to read the result yourself, not "
        "as a tie needing a winner."
    )

    if st.button("💾 Save to session history", key="save_hist", type="secondary"):
        st.session_state.session_history.append({
            "original": result["original_text"],
            "reformulated": final_text,
        })
        st.success("Saved!")

# ── Session history ────────────────────────────────────────────────────────
if st.session_state.get("session_history"):
    st.markdown("---")
    with st.expander(f"🕘 Session history ({len(st.session_state.session_history)} saved)",
                     expanded=False):
        for idx, entry in enumerate(reversed(st.session_state.session_history)):
            num = len(st.session_state.session_history) - idx
            st.markdown(f"**#{num}**")
            col_a, col_b = st.columns(2)
            with col_a:
                st.caption("Original")
                st.markdown(f'<div class="copy-box">{_fmt(entry["original"])}</div>',
                            unsafe_allow_html=True)
            with col_b:
                st.caption("Reformulated")
                st.markdown(f'<div class="copy-box">{_fmt(entry["reformulated"])}</div>',
                            unsafe_allow_html=True)
            st.markdown("---")
        if st.button("🗑 Clear history", key="clear_hist", type="secondary"):
            st.session_state.session_history = []
            st.rerun()

# ── Footer ─────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;font-size:.74rem;color:#6f87a6;margin-top:2.5rem">
  Powered by
  <strong style="color:#4b91dc">SBERT all-MiniLM-L6-v2</strong> ·
  <strong style="color:#4b91dc">WordNet</strong> ·
  <strong style="color:#4b91dc">Datamuse</strong> ·
  <strong style="color:#4b91dc">wordfreq</strong> ·
  <strong style="color:#4b91dc">pyinflect</strong> ·
  <strong style="color:#4b91dc">T5 (Vamsi/T5_Paraphrase_Paws)</strong> ·
  <strong style="color:#a855f7">pyspellchecker</strong> ·
  <strong style="color:#3b82f6">LanguageTool</strong>
</div>
""", unsafe_allow_html=True)
