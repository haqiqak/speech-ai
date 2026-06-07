"""
Speech AI — Streamlit UI v5
Multi-user edition: Login / Register screen guards the full application.
Pipeline: Sanitize → SBERT Semantic Firewall → Inflect → User Picks → Output
"""

import paths  # noqa: F401  — must precede nltk/SBERT imports; redirects caches into ./.cache
import html
import re
from pathlib import Path
import streamlit as st
from nltk import word_tokenize
from engine import SynonymEngine
from grammar import sanitize_input, is_sentence, SentenceRewriter, inflect, _preserve_case
import semantic as sem
import phonetic as ph
import freq

# ── Storage / auth imports ────────────────────────────────────────────────────
from user_store import save_profile, migrate_legacy_prefs
from auth import require_auth

# ── One-time migration of the legacy user_prefs.json (no-op if already done) ─
_LEGACY_PREFS = Path(__file__).resolve().parent / "user_prefs.json"
migrate_legacy_prefs(_LEGACY_PREFS)

# ── Page config (MUST come before any other st calls) ────────────────────────
st.set_page_config(
    page_title="Speech AI",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Authentication gate — nothing below this line renders until login ─────────
require_auth()

# ─────────────────────────────────────────────────────────────────────────────
# Everything below is only reached after successful authentication.
# st.session_state.current_user  is set.
# st.session_state.stutter_patterns / blocked_words are pre-loaded.
# ─────────────────────────────────────────────────────────────────────────────


def _save_current_user_prefs(patterns: list[str], blocked: list[str]) -> None:
    """Persist phoneme profile back to the logged-in user's JSON file."""
    user = st.session_state.get("current_user")
    if user:
        save_profile(
            user,
            patterns=patterns,
            blocked=blocked,
            custom_replacements=st.session_state.get("custom_replacements", {}),
            preferences=st.session_state.get("preferences", {}),
        )


def _parse_tokens(raw: str) -> list[str]:
    """Split a comma/space separated field into a clean, de-duplicated list."""
    out, seen = [], set()
    for t in re.split(r"[\s,]+", raw.strip().lower()):
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _content_words(sentence: str) -> list[str]:
    return [t for t in word_tokenize(sentence) if re.search(r"[a-z]", t.lower())]


def _risk_chips(sentence: str, patterns: list[str], blocked: set[str]) -> str:
    """HTML chips colouring each content word by stutter risk."""
    chips = []
    for tok in _content_words(sentence):
        low = tok.lower()
        on_pattern = (low in blocked) or ph.matches_any(tok, patterns)
        diff = ph.word_difficulty(tok)
        if on_pattern:
            cls = "risk-hi"
        elif diff >= 0.55:
            cls = "risk-mid"
        else:
            cls = "risk-lo"
        onset = "".join(ph.onset(tok)) or "—"
        chips.append(f'<span class="risk-chip {cls}" title="onset {onset} · '
                     f'difficulty {diff:.2f}">{tok}</span>')
    return '<div class="pill-wrap">' + "".join(chips) + "</div>"


def _fmt(text: object) -> str:
    """Escape dynamic text before placing it inside custom HTML."""
    return html.escape(str(text or ""))


def _current_rebuilt_sentence() -> str | None:
    if not st.session_state.get("sentence_mode") or st.session_state.get("result") is None:
        return None
    sanitized = st.session_state.get("sanitized") or ""
    substitutions = st.session_state.result.get("substitutions", [])
    rebuilt = rewriter.rebuild_with_choices(
        sanitized,
        substitutions,
        st.session_state.get("user_choices", {}),
    )
    return rebuilt


def _grammar_explanation() -> str:
    fixes = st.session_state.get("grammar_fixes_applied", []) + st.session_state.get("fixes", [])
    if not fixes:
        if st.session_state.get("last_query"):
            return "Grammar check passed. No automatic correction was needed before speech profiling."
        return "Run the speech profile to correct grammar before synonym analysis."

    rows = []
    seen = set()
    for fix in fixes:
        original = fix.get("original", "") or "(missing)"
        corrected = fix.get("corrected", "")
        reason = fix.get("reason") or fix.get("description") or "Grammar cleanup"
        sig = (original, corrected, reason)
        if sig in seen:
            continue
        seen.add(sig)
        rows.append(
            f'<div class="fix-row {fix.get("type", "spacing")}">'
            f'<span class="fix-before">{_fmt(original)}</span><span>&rarr;</span>'
            f'<span class="fix-after">{_fmt(corrected)}</span>'
            f'<span style="opacity:.62;font-size:.8rem">{_fmt(reason)}</span></div>'
        )
    return "".join(rows)


# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family:'DM Sans',sans-serif; background:#f7fbff; color:#1a2740; }
.block-container { padding-top:1.5rem; padding-bottom:4rem; max-width:800px; }

.hero { text-align:center; padding:1.6rem 1rem .9rem; }
.hero h1 { font-family:'DM Serif Display',serif; font-size:2.5rem; color:#1a2740; letter-spacing:-.5px; margin-bottom:.1rem; }
.hero h1 span { color:#f57c2b; }
.hero p { font-size:.95rem; color:#5a7096; font-weight:300; margin-top:.15rem; }

/* user badge */
.user-badge {
    display:inline-flex; align-items:center; gap:.42rem;
    background:#e8f2fc; border:1.4px solid #b8d9f5; border-radius:30px;
    padding:.28rem .85rem; font-size:.8rem; font-weight:600; color:#2d6aab;
    margin-bottom:.6rem;
}

/* inputs */
div[data-testid="stTextInput"] input {
    border:2px solid #c3daf7 !important; border-radius:14px !important;
    background:#fff !important; font-family:'DM Sans',sans-serif !important;
    font-size:1.05rem !important; padding:.66rem 1rem !important; color:#1a2740 !important;
    box-shadow:0 2px 10px rgba(75,145,220,.07) !important;
}
div[data-testid="stTextInput"] input:focus { border-color:#4b91dc !important; }
div[data-testid="stTextInput"] label { font-size:.82rem !important; font-weight:600 !important; color:#3d6ea8 !important; }
div[data-testid="stTextArea"] textarea {
    min-height:150px !important; border:2px solid #c3daf7 !important; border-radius:16px !important;
    background:#fff !important; font-family:'DM Sans',sans-serif !important;
    font-size:1.06rem !important; line-height:1.6 !important; padding:.9rem 1rem !important;
    color:#1a2740 !important; box-shadow:0 2px 12px rgba(75,145,220,.08) !important;
}
div[data-testid="stTextArea"] textarea:focus { border-color:#4b91dc !important; }
div[data-testid="stTextArea"] label { font-size:.82rem !important; font-weight:600 !important; color:#3d6ea8 !important; }
div[data-testid="stSlider"] label { font-size:.82rem !important; color:#3d6ea8 !important; font-weight:600 !important; }
div[data-testid="stSelectbox"] label { font-size:.76rem !important; font-weight:600 !important; color:#3d6ea8 !important; }
div[data-testid="stSelectbox"] > div > div { border:1.5px solid #c3daf7 !important; border-radius:10px !important; background:#fff !important; font-size:.9rem !important; }

/* button */
div.stButton > button {
    background:linear-gradient(135deg,#f57c2b,#f4a461) !important; color:#fff !important;
    border:none !important; border-radius:12px !important; font-family:'DM Sans',sans-serif !important;
    font-size:1rem !important; font-weight:600 !important; padding:.6rem 2rem !important;
    box-shadow:0 4px 14px rgba(245,124,43,.22) !important; transition:transform .15s,box-shadow .15s !important;
}
div.stButton > button:hover { transform:translateY(-2px) !important; box-shadow:0 6px 20px rgba(245,124,43,.33) !important; }

/* logout button override — subtle */
div.stButton > button[kind="secondary"] {
    background:#f0f4f8 !important; color:#5a7096 !important;
    box-shadow:none !important; font-size:.85rem !important; padding:.4rem 1rem !important;
}
div.stButton > button[kind="secondary"]:hover { background:#e4eaf2 !important; transform:none !important; }

/* cards */
.word-card { background:#fff; border:1.5px solid #d4e8f8; border-radius:16px; padding:1rem 1.3rem .9rem; margin-bottom:.75rem; box-shadow:0 2px 12px rgba(75,145,220,.06); }
.profile-panel { background:#fff; border:1.5px solid #d4e8f8; border-radius:16px; padding:1rem 1.2rem .85rem; margin:.55rem 0 .9rem; box-shadow:0 2px 12px rgba(75,145,220,.05); }
.analysis-note { background:#f8fbff; border:1.4px solid #d4e8f8; border-radius:12px; padding:.72rem .9rem; margin:.35rem 0 1rem; color:#2a3d58; font-size:.88rem; }
.syn-grid-card { background:#fff; border:1.5px solid #d4e8f8; border-radius:14px; padding:.85rem .95rem .8rem; margin-bottom:.75rem; min-height:170px; box-shadow:0 2px 10px rgba(75,145,220,.05); }
.syn-grid-card .pill-wrap { margin:.42rem 0 .55rem; }
.section-kicker { font-size:.68rem; font-weight:700; letter-spacing:.8px; text-transform:uppercase; color:#4b91dc; margin:.9rem 0 .45rem; }
.word-card-header { display:flex; align-items:center; gap:.5rem; margin-bottom:.5rem; }
.word-title { font-family:'DM Serif Display',serif; font-size:1.2rem; color:#1a2740; }
.badge { font-size:.67rem; font-weight:600; padding:.15rem .5rem; border-radius:20px; }
.badge-blue  { color:#2d6aab; background:#e8f2fc; }
.badge-warn  { color:#b06030; background:#fff2e8; }
.badge-green { color:#1a6b3c; background:#edfaf2; }
.badge-gray  { color:#5a7096; background:#f0f4f8; }
.badge-red   { color:#9b1c1c; background:#fef2f2; }

.pill-wrap { display:flex; flex-wrap:wrap; gap:.35rem; }
.pill { display:inline-block; padding:.25rem .75rem; border-radius:20px; font-size:.85rem; font-weight:500; transition:transform .12s; }
.pill:hover { transform:translateY(-2px); }
.pill.top { background:#fff2e8; color:#c85d14; border:1.4px solid #f7c49a; }
.pill.mid { background:#ebf4fd; color:#2d6aab; border:1.4px solid #b8d9f5; }

.no-syn-chip { display:inline-flex; align-items:center; gap:.4rem; background:#fdf7f3; border:1.2px dashed #f7c49a; border-radius:9px; padding:.24rem .68rem; font-size:.85rem; color:#a06030; margin:.12rem; }

/* stutter risk chips */
.risk-chip { display:inline-block; padding:.22rem .7rem; border-radius:20px; font-size:.85rem; font-weight:500; cursor:default; }
.risk-hi  { background:#fef2f2; color:#9b1c1c; border:1.4px solid #f3b4b4; }
.risk-mid { background:#fff8ed; color:#a06030; border:1.4px solid #f7c49a; }
.risk-lo  { background:#edfaf2; color:#1a6b3c; border:1.4px solid #b6e6c9; }

/* difficulty meter */
.diff-meter { display:flex; align-items:center; gap:.7rem; margin-top:.35rem; }
.diff-num { font-family:'DM Serif Display',serif; font-size:1.25rem; }
.diff-track { flex:1; background:#eef4fb; border-radius:6px; height:10px; position:relative; overflow:hidden; }
.diff-bar { height:10px; border-radius:6px; }
.diff-down { color:#1a6b3c; } .diff-up { color:#9b1c1c; } .diff-same { color:#5a7096; }

/* pipeline cards */
.pipe-card { background:#fff; border:1.5px solid #d4e8f8; border-radius:16px; padding:.95rem 1.3rem .9rem; margin-bottom:.75rem; box-shadow:0 2px 12px rgba(75,145,220,.05); }
.pipe-label { font-size:.68rem; font-weight:700; letter-spacing:.8px; text-transform:uppercase; color:#4b91dc; margin-bottom:.38rem; }

/* sanitizer */
.fix-row { display:flex; align-items:center; gap:.48rem; font-size:.87rem; padding:.28rem .48rem; border-radius:8px; margin-bottom:.22rem; }
.fix-row.contraction { background:#fff8f0; color:#c85d14; }
.fix-row.capitalization,.fix-row.pronoun_case { background:#f0f8ff; color:#2d6aab; }
.fix-row.punctuation { background:#f0fdf4; color:#1a6b3c; }
.fix-row.spacing { background:#fafafa; color:#5a7096; }
.fix-row.tense { background:#fdf4ff; color:#7c3aaa; }
.fix-row.subject_verb_agreement { background:#fff7ed; color:#b45309; }
.fix-row.auxiliary_form { background:#f0f9ff; color:#0369a1; }
.fix-row.negation_agreement { background:#fef2f2; color:#991b1b; }
.fix-row.informal_word { background:#fefce8; color:#854d0e; }
.fix-before { text-decoration:line-through; opacity:.55; font-style:italic; }
.fix-after  { font-weight:600; }
.corrected-sentence { font-size:1.02rem; color:#1a2740; background:#f0fdf6; border:1.4px solid #7ddba5; border-radius:11px; padding:.65rem .95rem; margin-top:.45rem; }
.clean-sentence { font-size:1.02rem; color:#1a6b3c; background:#f0fdf6; border:1.4px solid #7ddba5; border-radius:11px; padding:.65rem .95rem; margin-top:.45rem; }

/* SBERT status banner */
.sbert-on  { background:#edfaf2; border:1.4px solid #7ddba5; border-radius:11px; padding:.55rem .9rem; color:#1a6b3c; font-size:.88rem; margin-bottom:.6rem; }
.sbert-off { background:#fff8ed; border:1.4px solid #f7c49a; border-radius:11px; padding:.55rem .9rem; color:#a06030; font-size:.88rem; margin-bottom:.6rem; }

/* Scoring table */
.score-table { width:100%; border-collapse:collapse; font-size:.83rem; margin-top:.4rem; }
.score-table th { text-align:left; font-weight:600; color:#4b91dc; padding:.28rem .45rem; border-bottom:1.5px solid #e4f0fb; font-size:.75rem; letter-spacing:.3px; text-transform:uppercase; }
.score-table td { padding:.28rem .45rem; border-bottom:1px solid #f0f5fc; color:#2a3d58; }
.score-table tr:last-child td { border-bottom:none; }
.score-table tr.rejected td { color:#a3afc2; }
.score-table tr.chosen-row td { background:#fff8f2; }
.bar-wrap { width:70px; display:inline-block; background:#eaf2fc; border-radius:4px; height:7px; vertical-align:middle; }
.bar-fill { height:7px; border-radius:4px; background:linear-gradient(90deg,#4b91dc,#7ab8f0); display:block; }
.bar-fill.orange { background:linear-gradient(90deg,#f57c2b,#f4a461); }
.sim-tag { font-size:.7rem; padding:.08rem .35rem; border-radius:5px; font-weight:600; }
.sim-accept { background:#edfaf2; color:#1a6b3c; }
.sim-reject { background:#fef2f2; color:#9b1c1c; }
.tag-chip { font-size:.69rem; background:#f0f5fc; color:#3d6ea8; border-radius:5px; padding:.07rem .33rem; font-family:monospace; }

/* picker */
.picker-word-label { font-size:.8rem; font-weight:600; color:#1a2740; margin-bottom:.06rem; }

/* grammar / diff / output */
.grammar-ok    { background:#edfaf2; border:1.4px solid #7ddba5; border-radius:11px; padding:.55rem .9rem; color:#1a6b3c; font-size:.88rem; }
.grammar-warn  { background:#fff8ed; border:1.4px solid #f7c49a; border-radius:11px; padding:.55rem .9rem; color:#a06030; font-size:.88rem; }
.grammar-error { background:#fef2f2; border:1.4px solid #fca5a5; border-radius:11px; padding:.55rem .9rem; color:#991b1b; font-size:.88rem; }
.diff-text { font-size:1.03rem; color:#1a2740; line-height:1.75; }
.orig-word { color:#b0c4d8; text-decoration:line-through; font-size:.87rem; margin-right:.08rem; }
.new-word  { color:#f57c2b; font-weight:600; }
.output-box { background:linear-gradient(135deg,#fff8f2,#f0f7ff); border:2px solid #f0c090; border-radius:16px; padding:1.05rem 1.35rem; font-size:1.12rem; color:#1a2740; line-height:1.75; font-family:'DM Serif Display',serif; }

.mode-tag { display:inline-flex; align-items:center; gap:.28rem; font-size:.73rem; font-weight:700; letter-spacing:.5px; text-transform:uppercase; padding:.26rem .78rem; border-radius:20px; margin-bottom:.8rem; }
.mode-word     { background:#e8f2fc; color:#2d6aab; }
.mode-sentence { background:#fff2e8; color:#c85d14; }

hr { border:none; border-top:1.5px solid #deeaf7; margin:1.2rem 0; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
current_user = st.session_state.get("current_user", "")
st.markdown(f"""
<div class="hero">
  <h1>Speech <span>AI</span></h1>
  <p>Grammar correction · SBERT semantic firewall · Stutter assistance · Contextual synonym ranking</p>
</div>
""", unsafe_allow_html=True)

# ── Engine & SBERT init ───────────────────────────────────────────────────────
@st.cache_resource
def load_engine():
    return SynonymEngine()

@st.cache_resource
def load_rewriter(_engine):
    return SentenceRewriter(_engine)

@st.cache_resource
def init_sbert():
    """Load SBERT once and cache. Returns (success, message)."""
    ok = sem.load_sbert()
    return sem.sbert_status()

engine   = load_engine()
rewriter = load_rewriter(engine)
sbert_ok, sbert_msg = init_sbert()

# ── Initialize session state (must be done before any access) ────────────────
for key, default in [
    ("result", None), ("sanitized", None), ("fixes", []),
    ("user_choices", {}), ("last_query", ""), ("sentence_mode", False),
    ("grammar_fixes_applied", []), ("correction_map", {}),
    ("original_query", ""), ("corrected_query", ""), ("query_input", ""),
    ("stutter_patterns", []), ("blocked_words", []),
    ("custom_replacements", {}), ("preferences", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar: user info + logout + SBERT status + settings ────────────────────
with st.sidebar:
    # ── User info + logout ────────────────────────────────────────────────────
    st.markdown(
        f'<div class="user-badge">👤 {current_user}</div>',
        unsafe_allow_html=True,
    )
    if st.button("Logout", key="logout_btn", type="secondary"):
        # Clear auth state; preserve cache_resource (engine/SBERT)
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.markdown("---")
    st.markdown("### ⚙ Settings")

    if sbert_ok:
        st.markdown(f"""
<div class="sbert-on">
  <strong>🧠 SBERT Active</strong><br>
  <span style="font-size:.82rem">Semantic filtering ON · model: all-MiniLM-L6-v2</span>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div class="sbert-off">
  <strong>⚠ SBERT Offline</strong><br>
  <span style="font-size:.82rem">Running frequency-only mode.<br>
  Run once with internet to download the model (~80 MB).</span>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    sem_threshold = st.slider(
        "Semantic threshold",
        min_value=0.60, max_value=0.95, value=0.85, step=0.01,
        help="Candidates below this similarity score are rejected. Higher = stricter (only excellent matches). "
             "Recommended: 0.85 for meaning preservation.",
        disabled=not sbert_ok,
    )
    st.caption("Only active when SBERT is loaded. **New default: 0.85** (stricter semantic gating).")
    st.caption("💡 Not seeing synonyms for some words? The threshold may be too strict — try lowering it.")

    st.markdown("---")
    show_scores = st.toggle("Show scoring details", value=True,
        help="Show SBERT similarity scores and ranking for each word.")

    st.caption(f"Frequency wordlist: **{freq.active_wordlist()}**")

    st.markdown("---")
    st.markdown("""
<div style="font-size:.75rem;color:#6f87a6">
<strong style="color:#4b91dc">Pipeline</strong><br>
① Sanitize input grammar<br>
② Get synonym candidates<br>
③ SBERT semantic filter<br>
④ Combined score ranking<br>
⑤ Phoneme firewall (stutter)<br>
⑥ Inflect + user picks<br>
⑦ Rebuild sentence
</div>""", unsafe_allow_html=True)

# ── Controls ──────────────────────────────────────────────────────────────────
rebuilt_preview = _current_rebuilt_sentence()

# Always show the editable original input
query = st.text_area(
    "Your sentence",
    value=st.session_state.get("query_input", ""),
    placeholder="e.g. I have a special presentation today.",
    height=130,
    key="query_input",
    help="Enter a word, a list of words, or a full sentence.",
)
lookup_source = query

# When a result exists, show the toggle + modified box below the input
show_modified = False
if rebuilt_preview:
    show_modified = st.toggle(
        "▲ Show modified sentence",
        value=True,
        key="show_modified_toggle",
        help="Toggle to compare original input with the grammar-corrected + synonym-replaced sentence.",
    )
    if show_modified:
        orig_text = st.session_state.get("original_query") or st.session_state.get("last_query", "")
        col_orig, col_mod = st.columns(2)
        with col_orig:
            st.markdown(
                '<div style="font-size:.75rem;font-weight:700;color:#5a7096;'
                'letter-spacing:.5px;text-transform:uppercase;margin-bottom:.3rem">'
                '📄 Original</div>',
                unsafe_allow_html=True,
            )
            st.text_area(
                "original_display",
                value=orig_text,
                height=110,
                disabled=True,
                key="orig_display_box",
                label_visibility="collapsed",
            )
        with col_mod:
            st.markdown(
                '<div style="font-size:.75rem;font-weight:700;color:#f57c2b;'
                'letter-spacing:.5px;text-transform:uppercase;margin-bottom:.3rem">'
                '✦ Modified</div>',
                unsafe_allow_html=True,
            )
            st.text_area(
                "modified_display",
                value=rebuilt_preview,
                height=110,
                disabled=True,
                key="mod_display_box",
                label_visibility="collapsed",
            )

top_k = st.slider(
    "Synonyms / word", min_value=5, max_value=20, value=10, step=1,
    help="How many synonym candidates to fetch and rank for each word "
         "(higher = more options in the dropdown, slightly slower).",
)

# ── Stutter assistance (the core feature — kept front-and-centre) ──────────────
_has_stutter = bool(st.session_state.stutter_patterns or st.session_state.blocked_words)
with st.container():
    st.markdown('<div class="profile-panel">', unsafe_allow_html=True)
    st.markdown('<div class="pipe-label">Phoneme Profile for Stuttering Patterns</div>', unsafe_allow_html=True)
    st.caption("Enter the **starting sounds** you stutter on (e.g. `str, pr, b`). "
               "Suggestions are then offered only for words with those sounds, and "
               "never replace them with a word that starts the same way.")
    sc1, sc2 = st.columns(2)
    with sc1:
        patterns_raw = st.text_input(
            "Stutter sounds",
            value=", ".join(st.session_state.stutter_patterns),
            placeholder="e.g.  str, pr, b",
            help="Comma/space separated. 'bo' means the B sound; 'str' the /str/ cluster.",
        )
    with sc2:
        blocked_raw = st.text_input(
            "Words to always avoid",
            value=", ".join(st.session_state.blocked_words),
            placeholder="e.g.  particular, statistics",
            help="Specific words you struggle with — flagged risky and never suggested.",
        )
    _new_patterns = _parse_tokens(patterns_raw)
    _new_blocked  = _parse_tokens(blocked_raw)
    if (_new_patterns != st.session_state.stutter_patterns
            or _new_blocked != st.session_state.blocked_words):
        st.session_state.stutter_patterns = _new_patterns
        st.session_state.blocked_words    = _new_blocked
        # ← save to THIS user's file (not a global prefs file)
        _save_current_user_prefs(_new_patterns, _new_blocked)

    if st.session_state.stutter_patterns:
        onset_preview = " · ".join(
            f"{p} → /{''.join(ph.normalize_pattern(p)) or '?'}/"
            for p in st.session_state.stutter_patterns
        )
        st.markdown(
            f'<div style="font-size:.8rem;color:#2d6aab;margin-top:.2rem">'
            f'🔊 Active onsets: <strong>{onset_preview}</strong></div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)
_, col1, _ = st.columns([1, 2, 1])
with col1:
    search_clicked = st.button("Run speech profile", use_container_width=True)

# Auto-clear results when the user types a new sentence
if lookup_source.strip() and lookup_source.strip() != st.session_state.get("last_query", ""):
    if not search_clicked:
        st.session_state.result = None
        st.session_state.sanitized = None
        st.session_state.fixes = []
        st.session_state.user_choices = {}
        st.session_state.grammar_fixes_applied = []
        st.session_state.correction_map = {}
        st.session_state._word_results = None


# ── Process on button click ───────────────────────────────────────────────────
source_text = lookup_source.strip()
if search_clicked and source_text:
    st.session_state.user_choices = {}
    st.session_state.result = None
    st.session_state.sanitized = None
    st.session_state.fixes = []
    st.session_state.grammar_fixes_applied = []
    st.session_state.correction_map = {}
    st.session_state._word_results = None

    st.session_state.last_query   = source_text
    st.session_state.sentence_mode = is_sentence(source_text)

    corrected_query, grammar_fixes = sanitize_input(source_text)
    st.session_state.grammar_fixes_applied = grammar_fixes
    st.session_state.original_query = source_text
    st.session_state.corrected_query = corrected_query

    correction_map = {}
    for fix in grammar_fixes:
        orig = fix.get("original", "")
        corr = fix.get("corrected", "")
        if orig and corr:
            correction_map[corr.lower()] = orig
    st.session_state.correction_map = correction_map

    lookup_query = corrected_query

    patterns = list(st.session_state.stutter_patterns)
    blocked  = set(st.session_state.blocked_words)

    if not st.session_state.sentence_mode:
        with st.spinner("Looking up synonyms…"):
            st.session_state._word_results = engine.get_synonyms(lookup_query, top_k=top_k)
    else:
        sanitized, fixes = sanitize_input(lookup_query)
        st.session_state.sanitized = sanitized
        st.session_state.fixes     = fixes
        with st.spinner("Analysing sentence, running semantic filter…"):
            sem.MIN_SEMANTIC = sem_threshold
            result = rewriter.rewrite(
                sanitized, top_k=top_k,
                stutter_patterns=patterns,
                blocked_words=blocked,
            )
        st.session_state.result = result
    st.rerun()

elif search_clicked and not source_text:
    st.warning("Please enter a word or sentence.")

if st.session_state.last_query.strip():
    corrected = st.session_state.get("sanitized") or st.session_state.get("corrected_query", "")
    if corrected and corrected != st.session_state.last_query.strip():
        st.markdown(f"""
<div class="analysis-note">
  <strong style="color:#1a6b3c">Grammar corrected in the input box:</strong>
  <span>{_fmt(corrected)}</span>
  <div style="margin-top:.45rem">{_grammar_explanation()}</div>
</div>""", unsafe_allow_html=True)

# ── Word mode results ─────────────────────────────────────────────────────────
if not st.session_state.sentence_mode and st.session_state.get("_word_results"):
    word_results = st.session_state._word_results
    patterns = list(st.session_state.stutter_patterns)
    blocked  = set(st.session_state.blocked_words)

    st.markdown(
        f'<span class="mode-tag mode-word">🔤 Word / Multi-word Mode</span>',
        unsafe_allow_html=True,
    )

    for word, data in word_results.items():
        syns = data.get("synonyms") or []
        tag  = data.get("pos", "?")
        diff = ph.word_difficulty(word)
        onset_str = "/".join(ph.onset(word)) or "—"
        on_pat    = (word.lower() in blocked) or ph.matches_any(word, patterns)
        tag_color = "badge-warn" if on_pat else "badge-blue"

        st.markdown(f"""
<div class="word-card">
  <div class="word-card-header">
    <span class="word-title">{_fmt(word)}</span>
    <span class="badge badge-gray">{tag}</span>
    <span class="badge {tag_color}">onset /{onset_str}/</span>
    <span class="badge badge-gray">diff {diff:.2f}</span>
    {"<span class='badge badge-red'>⚠ stutter risk</span>" if on_pat else ""}
  </div>""", unsafe_allow_html=True)

        if syns:
            top_syns  = [s for s in syns[:3]]
            rest_syns = [s for s in syns[3:8]]

            st.markdown('<div class="pill-wrap">', unsafe_allow_html=True)
            for s in top_syns:
                infl = inflect(s["lemma"], tag)
                phon_ok = not ph.matches_any(s["lemma"], patterns) and s["lemma"].lower() not in blocked
                cls = "top" if phon_ok else "mid"
                freq_val = s.get("freq_score", 0)
                st.markdown(
                    f'<span class="pill {cls}" title="freq {freq_val:.2f}">'
                    f'{_fmt(infl)}</span>',
                    unsafe_allow_html=True,
                )
            for s in rest_syns:
                infl = inflect(s["lemma"], tag)
                phon_ok = not ph.matches_any(s["lemma"], patterns) and s["lemma"].lower() not in blocked
                cls = "mid"
                freq_val = s.get("freq_score", 0)
                st.markdown(
                    f'<span class="pill {cls}" title="freq {freq_val:.2f}">'
                    f'{_fmt(infl)}</span>',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                '<span class="badge badge-gray">No synonyms found</span>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

# ── Sentence mode results ─────────────────────────────────────────────────────
if st.session_state.sentence_mode and st.session_state.result is not None:
    result    = st.session_state.result
    sanitized = st.session_state.sanitized or st.session_state.last_query
    patterns  = list(st.session_state.stutter_patterns)
    blocked   = set(st.session_state.blocked_words)

    st.markdown(
        f'<span class="mode-tag mode-sentence">📝 Sentence Mode</span>',
        unsafe_allow_html=True,
    )

    # ── Card ①: Risk analysis ─────────────────────────────────────────────────
    chips_html = _risk_chips(sanitized, patterns, blocked)
    st.markdown(f"""
<div class="pipe-card">
  <div class="pipe-label">① Word Risk Analysis</div>
  {chips_html}
  <div style="font-size:.75rem;color:#6f87a6;margin-top:.42rem">
    <span class="risk-chip risk-hi" style="font-size:.72rem;padding:.15rem .5rem">high</span> onset match / blocked &nbsp;
    <span class="risk-chip risk-mid" style="font-size:.72rem;padding:.15rem .5rem">medium</span> difficulty ≥ 0.55 &nbsp;
    <span class="risk-chip risk-lo" style="font-size:.72rem;padding:.15rem .5rem">low</span> clear onset
  </div>
</div>""", unsafe_allow_html=True)

    # ── Card ②: Synonym pickers ───────────────────────────────────────────────
    if result["substitutions"]:
        st.markdown("""
<div class="pipe-card">
  <div class="pipe-label">② Synonym Candidates</div>""", unsafe_allow_html=True)

        if "user_choices" not in st.session_state:
            st.session_state.user_choices = {}

        for sub in result["substitutions"]:
            word     = sub["original_word"]
            tag      = sub["tag"]
            pos_key  = sub["position"]
            on_pat   = (word.lower() in blocked) or ph.matches_any(word, patterns)
            diff     = ph.word_difficulty(word)
            onset_str = "/".join(ph.onset(word)) or "—"

            tag_cls  = "badge-warn" if on_pat else "badge-blue"
            tag_warn = "<span class='badge badge-red'>⚠ stutter risk</span>" if on_pat else ""

            accepted_syns = [
                s for s in sub.get("scored", [])
                if s["accepted"] and s.get("phoneme_ok", True)
            ]
            # ── auto-pick: best accepted synonym or original ──────────────────
            if accepted_syns:
                best_lemma = accepted_syns[0]["lemma"]
                best_infl  = accepted_syns[0]["inflected"]
            else:
                best_lemma = word.lower()
                best_infl  = word

            auto_lemma = best_lemma

            # build dropdown options
            options = [word]
            for s in accepted_syns[:8]:
                if s["inflected"] not in options:
                    options.append(s["inflected"])

            # default = first accepted synonym (not the original word) if available
            default_idx = 1 if len(options) > 1 else 0

            # if user already made a choice, honour it
            prior = st.session_state.user_choices.get(pos_key)
            if prior and prior in options:
                default_idx = options.index(prior)
            elif prior and prior not in options:
                options.append(prior)
                default_idx = len(options) - 1

            st.markdown(f"""
<div class="syn-grid-card">
  <div class="word-card-header">
    <span class="word-title">{_fmt(word)}</span>
    <span class="badge badge-gray">{tag}</span>
    <span class="badge {tag_cls}">onset /{onset_str}/</span>
    <span class="badge badge-gray">diff {diff:.2f}</span>
    {tag_warn}
  </div>""", unsafe_allow_html=True)

            # pill preview
            pill_html = '<div class="pill-wrap">'
            for s in accepted_syns[:5]:
                is_best = s["lemma"] == auto_lemma
                cls = "top" if is_best else "mid"
                sim_val = s.get("semantic_sim") or 0
                freq_val = s["freq_score"]
                pill_html += (
                    f'<span class="pill {cls}" '
                    f'title="sim {sim_val:.2f} · freq {freq_val:.2f}">'
                    f'{_fmt(s["inflected"])}</span>'
                )
            pill_html += "</div>"
            st.markdown(pill_html, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # dropdown picker
            st.markdown(f'<div class="picker-word-label">Pick replacement for <em>{word}</em>:</div>', unsafe_allow_html=True)
            chosen = st.selectbox(
                f"Replace '{word}'",
                options=options,
                index=default_idx,
                key=f"pick_{pos_key}",
                label_visibility="collapsed",
            )
            st.session_state.user_choices[pos_key] = chosen

            # custom word input
            custom_word = st.text_input(
                f"Or type your own word for '{word}':",
                key=f"custom_{pos_key}",
                placeholder="Type any word…",
                label_visibility="visible",
            )

            if custom_word.strip():
                cw = custom_word.strip()
                # Simple inline validation: non-empty alphabetic word
                if re.match(r"^[a-zA-Z\-']+$", cw):
                    st.caption(f"✓ Using custom word: {cw}")
                    st.session_state.user_choices[sub["position"]] = cw
                else:
                    st.caption("⚠ Custom word should contain only letters.", help="Check spelling or try a different word.")

            # Scoring table (collapsible per word)
            if show_scores and sub.get("scored"):
                with st.expander(f"📊 Scores for '{sub['original_word']}'", expanded=False):
                    header = "Candidate · Semantic · Freq · Score · Status" if sbert_ok else "Candidate · Freq · Status"
                    rows_html = ""
                    for sc in sub["scored"][:8]:
                        is_chosen = sc["lemma"] == auto_lemma
                        phon_ok   = sc.get("phoneme_ok", True)
                        dimmed    = (not sc["accepted"]) or (not phon_ok)
                        row_cls   = "chosen-row" if is_chosen else ("rejected" if dimmed else "")
                        star      = "★ " if is_chosen else ""
                        if not sc["accepted"]:
                            status_cell = '✗ sem'
                        elif not phon_ok:
                            status_cell = '✗ onset'
                        else:
                            status_cell = '✓'

                        if sbert_ok and sc["semantic_sim"] is not None:
                            sim_val = sc["semantic_sim"]
                            sim_cls = "sim-accept" if sc["accepted"] else "sim-reject"
                            bar_w   = int(sim_val * 60)
                            sem_cell = (
                                f'<span class="sim-tag {sim_cls}">{sim_val:.2f}</span>'
                                f'<span class="bar-wrap"><span class="bar-fill orange" style="width:{bar_w}px"></span></span>'
                            )
                            freq_bar = int(sc["freq_score"] * 60)
                            freq_cell = (
                                f'{sc["freq_score"]:.2f}'
                                f'<span class="bar-wrap" style="margin-left:4px"><span class="bar-fill" style="width:{freq_bar}px"></span></span>'
                            )
                            combined_cell = f'<strong>{sc["combined"]:.3f}</strong>'
                            rows_html += f'<tr class="{row_cls}"><td>{star}{sc["inflected"]}</td><td>{sem_cell}</td><td>{freq_cell}</td><td>{combined_cell}</td><td>{status_cell}</td></tr>'
                        else:
                            freq_bar = int(sc["freq_score"] * 60)
                            freq_cell = f'{sc["freq_score"]:.2f}<span class="bar-wrap" style="margin-left:4px"><span class="bar-fill" style="width:{freq_bar}px"></span></span>'
                            rows_html += f'<tr class="{row_cls}"><td>{star}{sc["inflected"]}</td><td>{freq_cell}</td><td>{status_cell}</td></tr>'

                    if sbert_ok:
                        th = "<tr><th>Candidate</th><th>Semantic</th><th>Frequency</th><th>Combined</th><th></th></tr>"
                    else:
                        th = "<tr><th>Candidate</th><th>Frequency</th><th></th></tr>"
                    st.markdown(f'<table class="score-table"><thead>{th}</thead><tbody>{rows_html}</tbody></table>', unsafe_allow_html=True)

        if result["skipped"]:
            sk_html = " ".join(
                f'<span class="no-syn-chip">⊘ <strong>{s["word"]}</strong>'
                f'<span style="opacity:.7"> — {s["reason"]}</span></span>'
                for s in result["skipped"]
            )
            st.markdown(f'<div style="margin-top:.5rem;font-size:.82rem;color:#6f87a6">Kept unchanged: {sk_html}</div>', unsafe_allow_html=True)

    else:
        st.markdown("""
<div class="pipe-card">
  <div class="pipe-label">② Synonym Candidates</div>
  <div style="color:#6f87a6;font-size:.9rem">No substitutable content words found in this sentence.</div>
</div>""", unsafe_allow_html=True)

    # ── Rebuild with current user choices ─────────────────────────────────────
    user_choices = st.session_state.user_choices
    rebuilt = rewriter.rebuild_with_choices(
        sanitized, result["substitutions"], user_choices
    )
    # Run grammar validation on the rebuilt sentence for post-check
    post_issues = []
    try:
        from nltk import pos_tag, word_tokenize as _wt
        _rb_tokens = _wt(rebuilt)
        _rb_tags = pos_tag(_rb_tokens)
        # Check for obvious SVA issues: 3rd-person singular pronoun + base verb
        _THIRD = {"he", "she", "it"}
        for _idx, (_w, _t) in enumerate(_rb_tags):
            if _w.lower() in _THIRD and _idx + 1 < len(_rb_tags):
                _nw, _nt = _rb_tags[_idx + 1]
                if _nt == "VBP":  # non-3rd present = agreement mismatch
                    post_issues.append(
                        f'Possible agreement issue: "{_w} {_nw}" — check verb form.'
                    )
    except Exception:
        pass

    # ── Card ③: Grammar check ─────────────────────────────────────────────────
    pipeline_notes = [n for n in result.get("grammar_notes", []) if "passed" not in n.lower()]

    if post_issues:
        items = "".join(f"<li>{_fmt(i)}</li>" for i in post_issues)
        grammar_html = (
            f'<div class="grammar-error">'
            f'⚠ <strong>Grammar issues in rebuilt sentence:</strong>'
            f'<ul style="margin:.3rem 0 0 1rem;padding:0">{items}</ul>'
            f'</div>'
        )
    elif pipeline_notes:
        items = "".join(f"<li>{_fmt(n)}</li>" for n in pipeline_notes)
        grammar_html = (
            f'<div class="grammar-warn">'
            f'⚠ Notes:<ul style="margin:.28rem 0 0 1rem;padding:0">{items}</ul>'
            f'</div>'
        )
    else:
        grammar_html = '<div class="grammar-ok">✓ Grammar check passed — rebuilt sentence is grammatically valid.</div>'

    st.markdown(f"""
<div class="pipe-card">
  <div class="pipe-label">③ Grammar Check</div>
  {grammar_html}
</div>""", unsafe_allow_html=True)

    # ── Card ④: Highlighted diff ──────────────────────────────────────────────
    orig_tok  = word_tokenize(sanitized)
    reblt_tok = word_tokenize(rebuilt)
    diff_parts = []
    for ot, rt in zip(orig_tok, reblt_tok):
        if ot.lower() != rt.lower() and re.match(r"[a-zA-Z]", ot):
            diff_parts.append(f'<span class="orig-word">{ot}</span><span class="new-word">{rt}</span>')
        else:
            diff_parts.append(rt)
    highlighted = " ".join(diff_parts)

    st.markdown(f"""
<div class="pipe-card">
  <div class="pipe-label">④ Highlighted Changes</div>
  <div class="diff-text">{highlighted}</div>
</div>""", unsafe_allow_html=True)

    # ── Card ⑤: Final output + stutter-difficulty before/after ────────────────
    diff_before = ph.sentence_difficulty(_content_words(sanitized))
    diff_after  = ph.sentence_difficulty(_content_words(rebuilt))
    delta = diff_after - diff_before
    if delta < -0.005:
        d_cls, d_word, arrow, bar_col = "diff-down", "easier", "↓", "#7ddba5"
    elif delta > 0.005:
        d_cls, d_word, arrow, bar_col = "diff-up", "harder", "↑", "#f3b4b4"
    else:
        d_cls, d_word, arrow, bar_col = "diff-same", "no change", "→", "#b8d9f5"

    st.markdown(f"""
<div class="pipe-card" style="border-color:#f0c090">
  <div class="pipe-label" style="color:#f57c2b">⑤ Final Sentence</div>
  <div class="output-box">{rebuilt}</div>
  <div class="diff-meter">
    <span class="diff-num {d_cls}">{diff_after:.2f}</span>
    <div class="diff-track">
      <div class="diff-bar" style="width:{int(diff_after*100)}%;background:{bar_col}"></div>
    </div>
  </div>
  <div style="font-size:.78rem;color:#5a7096;margin-top:.2rem">
    Stutter difficulty: <strong>{diff_before:.2f} → {diff_after:.2f}</strong>
    <span class="{d_cls}">({arrow} {d_word})</span>
  </div>
</div>""", unsafe_allow_html=True)

    st.caption("📋 Copy your sentence:")
    st.code(rebuilt, language=None)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;font-size:.74rem;color:#6f87a6;margin-top:2.5rem">
  Powered by
  <strong style="color:#4b91dc">SBERT all-MiniLM-L6-v2</strong> ·
  <strong style="color:#4b91dc">WordNet</strong> ·
  <strong style="color:#4b91dc">Datamuse</strong> ·
  <strong style="color:#4b91dc">wordfreq</strong> ·
  <strong style="color:#4b91dc">pyinflect</strong> ·
  <strong style="color:#4b91dc">NLTK</strong>
</div>
""", unsafe_allow_html=True)
