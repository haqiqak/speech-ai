"""
Speech AI — Streamlit UI v6
Multi-sentence · Copy/revert · Blocklist/allowlist UI · Datamuse POS gate (engine.py v3.1)
"""

import paths  # noqa: F401
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

from user_store import save_profile, migrate_legacy_prefs
from auth import require_auth

_LEGACY_PREFS = Path(__file__).resolve().parent / "user_prefs.json"
migrate_legacy_prefs(_LEGACY_PREFS)

st.set_page_config(
    page_title="Speech AI",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="expanded",
)

require_auth()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _save_prefs(patterns: list[str], blocked: list[str]) -> None:
    user = st.session_state.get("current_user")
    if user:
        preferences = dict(st.session_state.get("preferences", {}))
        preferences["allowlist_words"] = list(st.session_state.get("allowlist_words", []))
        preferences["rephrase_enabled"] = bool(st.session_state.get("rephrase_enabled", False))
        st.session_state.preferences = preferences
        save_profile(
            user,
            patterns=patterns,
            blocked=blocked,
            custom_replacements=st.session_state.get("custom_replacements", {}),
            preferences=preferences,
        )


def _parse_tokens(raw: str) -> list[str]:
    out, seen = [], set()
    for t in re.split(r"[\s,]+", raw.strip().lower()):
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _content_words(sentence: str) -> list[str]:
    return [t for t in word_tokenize(sentence) if re.search(r"[a-z]", t.lower())]


def _risk_chips(sentence: str, patterns: list[str], blocked: set[str]) -> str:
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
        chips.append(
            f'<span class="risk-chip {cls}" title="onset {onset} · difficulty {diff:.2f}">'
            f'{tok}</span>'
        )
    return '<div class="pill-wrap">' + "".join(chips) + "</div>"


def _fmt(text: object) -> str:
    return html.escape(str(text or ""))


def _grammar_explanation(fixes: list[dict]) -> str:
    if not fixes:
        return "Grammar check passed — no corrections needed."
    rows = []
    seen = set()
    for fix in fixes:
        original  = fix.get("original", "") or "(missing)"
        corrected = fix.get("corrected", "")
        reason    = fix.get("reason") or fix.get("description") or "Grammar cleanup"
        sig = (original, corrected, reason)
        if sig in seen:
            continue
        seen.add(sig)
        rows.append(
            f'<div class="fix-row {fix.get("type","spacing")}">'
            f'<span class="fix-before">{_fmt(original)}</span>'
            f'<span>&rarr;</span>'
            f'<span class="fix-after">{_fmt(corrected)}</span>'
            f'<span style="opacity:.62;font-size:.8rem">{_fmt(reason)}</span>'
            f'</div>'
        )
    return "".join(rows)


def _split_sentences(text: str) -> list[str]:
    abbreviations = {
        "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.",
        "Sr.", "Jr.", "vs.", "etc.", "approx.",
        "fig.", "vol.", "no."
    }

    sentences = []
    current = []

    for word in text.split():
        current.append(word)

        if word.endswith((".", "!", "?")) and word not in abbreviations:
            sentences.append(" ".join(current))
            current = []

    if current:
        sentences.append(" ".join(current))

    return sentences


def _rebuild_sentence(sent_result: dict, sid: int) -> str:
    """Rebuild one sentence using current user choices for that sentence."""
    sanitized     = sent_result["sanitized"]
    substitutions = sent_result["result"]["substitutions"]
    choices       = st.session_state.ms_choices.get(sid, {})
    return rewriter.rebuild_with_choices(sanitized, substitutions, choices)


def _full_rebuilt_paragraph() -> str | None:
    """Join all sentences from multi-sentence results into one paragraph."""
    if not st.session_state.get("ms_results"):
        return None
    parts = []
    for sid, sr in enumerate(st.session_state.ms_results):
        if sr.get("is_sentence"):
            parts.append(_rebuild_sentence(sr, sid + 1))
        else:
            parts.append(sr["sanitized"])
    return " ".join(parts)


def _single_rebuilt() -> str | None:
    """Rebuilt sentence for single-sentence mode."""
    if not st.session_state.get("sentence_mode") or st.session_state.get("result") is None:
        return None
    return rewriter.rebuild_with_choices(
        st.session_state.sanitized or "",
        st.session_state.result.get("substitutions", []),
        st.session_state.get("user_choices", {}),
    )


# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

html,body,[class*="css"]{font-family:'DM Sans',sans-serif;background:#f7fbff;color:#1a2740}
.block-container{padding-top:1.5rem;padding-bottom:4rem;max-width:820px}

.hero{text-align:center;padding:1.6rem 1rem .9rem}
.hero h1{font-family:'DM Serif Display',serif;font-size:2.5rem;color:#1a2740;letter-spacing:-.5px;margin-bottom:.1rem}
.hero h1 span{color:#f57c2b}
.hero p{font-size:.95rem;color:#5a7096;font-weight:300;margin-top:.15rem}

.user-badge{display:inline-flex;align-items:center;gap:.42rem;background:#e8f2fc;border:1.4px solid #b8d9f5;border-radius:30px;padding:.28rem .85rem;font-size:.8rem;font-weight:600;color:#2d6aab;margin-bottom:.6rem}

div[data-testid="stTextInput"] input{border:2px solid #c3daf7!important;border-radius:14px!important;background:#fff!important;font-family:'DM Sans',sans-serif!important;font-size:1.05rem!important;padding:.66rem 1rem!important;color:#1a2740!important;box-shadow:0 2px 10px rgba(75,145,220,.07)!important}
div[data-testid="stTextInput"] input:focus{border-color:#4b91dc!important}
div[data-testid="stTextInput"] label{font-size:.82rem!important;font-weight:600!important;color:#3d6ea8!important}
div[data-testid="stTextArea"] textarea{min-height:120px!important;border:2px solid #c3daf7!important;border-radius:16px!important;background:#fff!important;font-family:'DM Sans',sans-serif!important;font-size:1.06rem!important;line-height:1.6!important;padding:.9rem 1rem!important;color:#1a2740!important;box-shadow:0 2px 12px rgba(75,145,220,.08)!important}
div[data-testid="stTextArea"] textarea:focus{border-color:#4b91dc!important}
div[data-testid="stTextArea"] label{font-size:.82rem!important;font-weight:600!important;color:#3d6ea8!important}
div[data-testid="stSlider"] label{font-size:.82rem!important;color:#3d6ea8!important;font-weight:600!important}
div[data-testid="stSelectbox"] label{font-size:.76rem!important;font-weight:600!important;color:#3d6ea8!important}
div[data-testid="stSelectbox"]>div>div{border:1.5px solid #c3daf7!important;border-radius:10px!important;background:#fff!important;font-size:.9rem!important}

div.stButton>button{background:linear-gradient(135deg,#f57c2b,#f4a461)!important;color:#fff!important;border:none!important;border-radius:12px!important;font-family:'DM Sans',sans-serif!important;font-size:1rem!important;font-weight:600!important;padding:.6rem 2rem!important;box-shadow:0 4px 14px rgba(245,124,43,.22)!important;transition:transform .15s,box-shadow .15s!important}
div.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 6px 20px rgba(245,124,43,.33)!important}
div.stButton>button[kind="secondary"]{background:#f0f4f8!important;color:#5a7096!important;box-shadow:none!important;font-size:.85rem!important;padding:.4rem 1rem!important}
div.stButton>button[kind="secondary"]:hover{background:#e4eaf2!important;transform:none!important}

.word-card{background:#fff;border:1.5px solid #d4e8f8;border-radius:16px;padding:1rem 1.3rem .9rem;margin-bottom:.75rem;box-shadow:0 2px 12px rgba(75,145,220,.06)}
.profile-panel{background:#fff;border:1.5px solid #d4e8f8;border-radius:16px;padding:1rem 1.2rem .85rem;margin:.55rem 0 .9rem;box-shadow:0 2px 12px rgba(75,145,220,.05)}
.analysis-note{background:#f8fbff;border:1.4px solid #d4e8f8;border-radius:12px;padding:.72rem .9rem;margin:.35rem 0 1rem;color:#2a3d58;font-size:.88rem}
.syn-grid-card{background:#fff;border:1.5px solid #d4e8f8;border-radius:14px;padding:.85rem .95rem .8rem;margin-bottom:.75rem;min-height:170px;box-shadow:0 2px 10px rgba(75,145,220,.05)}
.section-kicker{font-size:.68rem;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:#4b91dc;margin:.9rem 0 .45rem}
.word-card-header{display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem}
.word-title{font-family:'DM Serif Display',serif;font-size:1.2rem;color:#1a2740}
.badge{font-size:.67rem;font-weight:600;padding:.15rem .5rem;border-radius:20px}
.badge-blue{color:#2d6aab;background:#e8f2fc}
.badge-warn{color:#b06030;background:#fff2e8}
.badge-green{color:#1a6b3c;background:#edfaf2}
.badge-gray{color:#5a7096;background:#f0f4f8}
.badge-red{color:#9b1c1c;background:#fef2f2}

.pill-wrap{display:flex;flex-wrap:wrap;gap:.35rem}
.pill{display:inline-block;padding:.25rem .75rem;border-radius:20px;font-size:.85rem;font-weight:500;transition:transform .12s}
.pill:hover{transform:translateY(-2px)}
.pill.top{background:#fff2e8;color:#c85d14;border:1.4px solid #f7c49a}
.pill.mid{background:#ebf4fd;color:#2d6aab;border:1.4px solid #b8d9f5}

.no-syn-chip{display:inline-flex;align-items:center;gap:.4rem;background:#fdf7f3;border:1.2px dashed #f7c49a;border-radius:9px;padding:.24rem .68rem;font-size:.85rem;color:#a06030;margin:.12rem}

.risk-chip{display:inline-block;padding:.22rem .7rem;border-radius:20px;font-size:.85rem;font-weight:500;cursor:default}
.risk-hi{background:#fef2f2;color:#9b1c1c;border:1.4px solid #f3b4b4}
.risk-mid{background:#fff8ed;color:#a06030;border:1.4px solid #f7c49a}
.risk-lo{background:#edfaf2;color:#1a6b3c;border:1.4px solid #b6e6c9}

.diff-meter{display:flex;align-items:center;gap:.7rem;margin-top:.35rem}
.diff-num{font-family:'DM Serif Display',serif;font-size:1.25rem}
.diff-track{flex:1;background:#eef4fb;border-radius:6px;height:10px;position:relative;overflow:hidden}
.diff-bar{height:10px;border-radius:6px}
.diff-down{color:#1a6b3c}.diff-up{color:#9b1c1c}.diff-same{color:#5a7096}

.pipe-card{background:#fff;border:1.5px solid #d4e8f8;border-radius:16px;padding:.95rem 1.3rem .9rem;margin-bottom:.75rem;box-shadow:0 2px 12px rgba(75,145,220,.05)}
.pipe-label{font-size:.68rem;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:#4b91dc;margin-bottom:.38rem}

/* multi-sentence */
.sent-card{background:#fff;border:1.5px solid #d4e8f8;border-radius:16px;padding:.9rem 1.2rem;margin-bottom:1rem;box-shadow:0 2px 12px rgba(75,145,220,.05)}
.sent-header{display:flex;align-items:center;gap:.55rem;margin-bottom:.6rem}
.sent-num{font-family:'DM Serif Display',serif;font-size:.95rem;color:#4b91dc;font-weight:700;min-width:24px}
.revert-hint{font-size:.74rem;color:#7da4c8;font-style:italic;margin-left:auto}

.fix-row{display:flex;align-items:center;gap:.48rem;font-size:.87rem;padding:.28rem .48rem;border-radius:8px;margin-bottom:.22rem}
.fix-row.contraction{background:#fff8f0;color:#c85d14}
.fix-row.capitalization,.fix-row.pronoun_case{background:#f0f8ff;color:#2d6aab}
.fix-row.punctuation{background:#f0fdf4;color:#1a6b3c}
.fix-row.spacing{background:#fafafa;color:#5a7096}
.fix-row.tense{background:#fdf4ff;color:#7c3aaa}
.fix-row.subject_verb_agreement{background:#fff7ed;color:#b45309}
.fix-row.auxiliary_form{background:#f0f9ff;color:#0369a1}
.fix-row.negation_agreement{background:#fef2f2;color:#991b1b}
.fix-row.informal_word{background:#fefce8;color:#854d0e}
.fix-row.spelling{background:#fdf4ff;color:#6b21a8;border-left:3px solid #a855f7}
.fix-row.article{background:#f0fdf4;color:#166534;border-left:3px solid #22c55e}
.fix-row.languagetool{background:#f0f4ff;color:#1e40af;border-left:3px solid #3b82f6}
.fix-before{text-decoration:line-through;opacity:.55;font-style:italic}
.fix-after{font-weight:600}
.corrected-sentence,.clean-sentence{font-size:1.02rem;color:#1a6b3c;background:#f0fdf6;border:1.4px solid #7ddba5;border-radius:11px;padding:.65rem .95rem;margin-top:.45rem}

.sbert-on{background:#edfaf2;border:1.4px solid #7ddba5;border-radius:11px;padding:.55rem .9rem;color:#1a6b3c;font-size:.88rem;margin-bottom:.6rem}
.sbert-off{background:#fff8ed;border:1.4px solid #f7c49a;border-radius:11px;padding:.55rem .9rem;color:#a06030;font-size:.88rem;margin-bottom:.6rem}

.score-table{width:100%;border-collapse:collapse;font-size:.83rem;margin-top:.4rem}
.score-table th{text-align:left;font-weight:600;color:#4b91dc;padding:.28rem .45rem;border-bottom:1.5px solid #e4f0fb;font-size:.75rem;letter-spacing:.3px;text-transform:uppercase}
.score-table td{padding:.28rem .45rem;border-bottom:1px solid #f0f5fc;color:#2a3d58}
.score-table tr:last-child td{border-bottom:none}
.score-table tr.rejected td{color:#a3afc2}
.score-table tr.chosen-row td{background:#fff8f2}
.bar-wrap{width:70px;display:inline-block;background:#eaf2fc;border-radius:4px;height:7px;vertical-align:middle}
.bar-fill{height:7px;border-radius:4px;background:linear-gradient(90deg,#4b91dc,#7ab8f0);display:block}
.bar-fill.orange{background:linear-gradient(90deg,#f57c2b,#f4a461)}
.sim-tag{font-size:.7rem;padding:.08rem .35rem;border-radius:5px;font-weight:600}
.sim-accept{background:#edfaf2;color:#1a6b3c}
.sim-reject{background:#fef2f2;color:#9b1c1c}

.grammar-ok{background:#edfaf2;border:1.4px solid #7ddba5;border-radius:11px;padding:.55rem .9rem;color:#1a6b3c;font-size:.88rem}
.grammar-warn{background:#fff8ed;border:1.4px solid #f7c49a;border-radius:11px;padding:.55rem .9rem;color:#a06030;font-size:.88rem}
.grammar-error{background:#fef2f2;border:1.4px solid #fca5a5;border-radius:11px;padding:.55rem .9rem;color:#991b1b;font-size:.88rem}
.diff-text{font-size:1.03rem;color:#1a2740;line-height:1.75}
.orig-word{color:#b0c4d8;text-decoration:line-through;font-size:.87rem;margin-right:.08rem}
.new-word{color:#f57c2b;font-weight:600}
.output-box{background:linear-gradient(135deg,#fff8f2,#f0f7ff);border:2px solid #f0c090;border-radius:16px;padding:1.05rem 1.35rem;font-size:1.12rem;color:#1a2740;line-height:1.75;font-family:'DM Serif Display',serif}

.mode-tag{display:inline-flex;align-items:center;gap:.28rem;font-size:.73rem;font-weight:700;letter-spacing:.5px;text-transform:uppercase;padding:.26rem .78rem;border-radius:20px;margin-bottom:.8rem}
.mode-word{background:#e8f2fc;color:#2d6aab}
.mode-sentence{background:#fff2e8;color:#c85d14}
.mode-multi{background:#edfaf2;color:#1a6b3c}

/* blocklist panel */
.blocklist-panel{background:#fffbf7;border:1.4px solid #f7c49a;border-radius:14px;padding:.85rem 1rem;margin:.45rem 0}
.blocklist-item{display:inline-flex;align-items:center;gap:.3rem;background:#fff2e8;border:1.2px solid #f7c49a;border-radius:20px;padding:.2rem .65rem;font-size:.85rem;color:#c85d14;margin:.15rem}
.allowlist-item{display:inline-flex;align-items:center;gap:.3rem;background:#edfaf2;border:1.2px solid #7ddba5;border-radius:20px;padding:.2rem .65rem;font-size:.85rem;color:#1a6b3c;margin:.15rem}

/* copy box */
.copy-box{background:#f8fbff;border:1.5px solid #b8d9f5;border-radius:12px;padding:.75rem 1rem;font-size:1rem;color:#1a2740;line-height:1.7;font-family:'DM Serif Display',serif;margin-top:.4rem}

hr{border:none;border-top:1.5px solid #deeaf7;margin:1.2rem 0}
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
current_user = st.session_state.get("current_user", "")
st.markdown(f"""
<div class="hero">
  <h1>Speech <span>AI</span></h1>
  <p>Spelling &amp; grammar correction · SBERT semantic firewall · Stutter assistance · Contextual synonym ranking</p>
</div>
""", unsafe_allow_html=True)

# ── Engine & SBERT init ────────────────────────────────────────────────────────
@st.cache_resource
def load_engine():
    return SynonymEngine()

@st.cache_resource
def load_rewriter(_engine):
    return SentenceRewriter(_engine)

@st.cache_resource
def init_sbert():
    ok = sem.load_sbert()
    return sem.sbert_status()

engine   = load_engine()
rewriter = load_rewriter(engine)
sbert_ok, sbert_msg = init_sbert()

# ── Session state defaults ─────────────────────────────────────────────────────
for key, default in [
    ("result", None), ("sanitized", None), ("fixes", []),
    ("user_choices", {}), ("last_query", ""), ("sentence_mode", False),
    ("grammar_fixes_applied", []), ("correction_map", {}),
    ("original_query", ""), ("corrected_query", ""), ("query_input", ""),
    ("stutter_patterns", []), ("blocked_words", []),
    ("custom_replacements", {}), ("preferences", {}),
    # multi-sentence
    ("ms_results", []), ("ms_choices", {}), ("multi_mode", False),
    # session history
    ("session_history", []),
    # word mode
    ("_word_results", None),
    # allowlist
    ("allowlist_words", []),
    # optional rephrase layer (default off)
    ("rephrase_enabled", False),
    ("rephrase_single_sig", None), ("rephrase_single_result", None), ("rephrase_single_use", False),
    ("rephrase_paragraph_sig", None), ("rephrase_paragraph_result", None), ("rephrase_paragraph_use", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f'<div class="user-badge">👤 {current_user}</div>', unsafe_allow_html=True)
    if st.button("Logout", key="logout_btn", type="secondary"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.markdown("---")
    st.markdown("### ⚙ Settings")

    if sbert_ok:
        st.markdown("""<div class="sbert-on"><strong>🧠 SBERT Active</strong><br>
<span style="font-size:.82rem">Semantic filtering ON · all-MiniLM-L6-v2</span></div>""",
            unsafe_allow_html=True)
    else:
        st.markdown("""<div class="sbert-off"><strong>⚠ SBERT Offline</strong><br>
<span style="font-size:.82rem">Frequency-only mode. Run once online to download (~80 MB).</span></div>""",
            unsafe_allow_html=True)

    st.markdown("---")
    sem_threshold = st.slider(
        "Semantic threshold", min_value=0.60, max_value=0.95,
        value=0.85, step=0.01, disabled=not sbert_ok,
        help="Candidates below this similarity are rejected. 0.85 = strict. Lower if you see few suggestions.",
    )
    st.caption("💡 Not seeing synonyms? Try lowering the threshold.")

    st.markdown("---")
    show_scores = st.toggle("Show scoring details", value=True,
        help="Show SBERT similarity scores per word.")

    prefs = dict(st.session_state.get("preferences", {}))
    pref_rephrase = bool(prefs.get("rephrase_enabled", False))
    if "rephrase_enabled" not in st.session_state:
        st.session_state.rephrase_enabled = pref_rephrase
    rephrase_enabled = st.toggle(
        "Fluency rephrase (beta)",
        value=bool(st.session_state.get("rephrase_enabled", pref_rephrase)),
        help=(
            "Proposes a more fluent rewrite that still avoids your stutter sounds. "
            "First use downloads a T5 model (~hundreds of MB); CPU inference can take a few seconds."
        ),
    )
    st.session_state.rephrase_enabled = rephrase_enabled
    if prefs.get("rephrase_enabled") != rephrase_enabled:
        prefs["rephrase_enabled"] = rephrase_enabled
        st.session_state.preferences = prefs
        _save_prefs(st.session_state.stutter_patterns, st.session_state.blocked_words)
    if rephrase_enabled:
        import rephrase as _rephrase
        _rp_ok, _rp_msg = _rephrase.rephrase_status()
        st.caption(("🟢 " if _rp_ok else "🟡 ") + _rp_msg)
    else:
        st.caption("Fluency rephrase off.")

    st.caption(f"Frequency wordlist: **{freq.active_wordlist()}**")

    st.markdown("---")
    st.markdown("""<div style="font-size:.75rem;color:#6f87a6">
<strong style="color:#4b91dc">Pipeline</strong><br>
① Grammar correction<br>② Synonym candidates (POS-gated)<br>
③ SBERT semantic filter<br>④ Combined score ranking<br>
⑤ Phoneme firewall<br>⑥ Inflect + user picks<br>⑦ Rebuild sentence
</div>""", unsafe_allow_html=True)

# ── Main controls ──────────────────────────────────────────────────────────────
query = st.text_area(
    "Your sentence or paragraph",
    value=st.session_state.get("query_input", ""),
    placeholder="Type one sentence, or paste a whole paragraph — Speech AI handles both.",
    height=130,
    key="query_input",
    help="Single sentence → full pipeline with dropdown pickers. "
         "Multiple sentences → each processed separately, paragraph rebuilt at the end.",
)
lookup_source = query

top_k = st.slider(
    "Synonyms / word", min_value=5, max_value=20, value=10, step=1,
    help="Number of synonym candidates to fetch per word.",
)

# ── Phoneme profile ────────────────────────────────────────────────────────────
with st.container():
    st.markdown('<div class="profile-panel">', unsafe_allow_html=True)
    st.markdown('<div class="pipe-label">Phoneme Profile — Stuttering Patterns</div>',
                unsafe_allow_html=True)
    st.caption("Enter the **starting sounds** you stutter on (e.g. `str, pr, b`). "
               "Replacements will avoid words that start with those same sounds.")
    sc1, sc2 = st.columns(2)
    with sc1:
        patterns_raw = st.text_input(
            "Stutter sounds",
            value=", ".join(st.session_state.stutter_patterns),
            placeholder="e.g.  str, pr, b",
            help="Comma/space-separated grapheme clusters. Converted to ARPAbet onsets internally.",
        )
    with sc2:
        blocked_raw = st.text_input(
            "Words to always avoid",
            value=", ".join(st.session_state.blocked_words),
            placeholder="e.g.  particular, statistics",
            help="Specific words you struggle with — flagged risky and never suggested as synonyms.",
        )
    _new_patterns = _parse_tokens(patterns_raw)
    _new_blocked  = _parse_tokens(blocked_raw)
    if (_new_patterns != st.session_state.stutter_patterns
            or _new_blocked != st.session_state.blocked_words):
        st.session_state.stutter_patterns = _new_patterns
        st.session_state.blocked_words    = _new_blocked
        _save_prefs(_new_patterns, _new_blocked)

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
    st.markdown("</div>", unsafe_allow_html=True)

# ── Blocklist / Allowlist UI ───────────────────────────────────────────────────
with st.expander("📋 Blocklist & Allowlist — word-level overrides", expanded=False):
    st.caption(
        "**Blocklist** — specific words that will always be flagged and replaced. "
        "**Allowlist** — words that must never be substituted (locked in place)."
    )

    col_bl, col_al = st.columns(2)

    with col_bl:
        st.markdown("**🚫 Blocklist** *(always replace)*")
        bl_input = st.text_input(
            "Add to blocklist",
            key="bl_add_input",
            placeholder="e.g. statistics",
            label_visibility="collapsed",
        )
        if st.button("Add", key="bl_add_btn", type="secondary"):
            word = bl_input.strip().lower()
            if word and word not in st.session_state.blocked_words:
                st.session_state.blocked_words.append(word)
                _save_prefs(st.session_state.stutter_patterns, st.session_state.blocked_words)
                st.rerun()

        if st.session_state.blocked_words:
            st.markdown('<div class="blocklist-panel">', unsafe_allow_html=True)
            for bw in list(st.session_state.blocked_words):
                col_word, col_rm = st.columns([4, 1])
                with col_word:
                    st.markdown(f'<span class="blocklist-item">🚫 {_fmt(bw)}</span>',
                                unsafe_allow_html=True)
                with col_rm:
                    if st.button("✕", key=f"bl_rm_{bw}", type="secondary",
                                 help=f"Remove '{bw}' from blocklist"):
                        st.session_state.blocked_words.remove(bw)
                        _save_prefs(st.session_state.stutter_patterns,
                                    st.session_state.blocked_words)
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.caption("No blocked words yet.")

    with col_al:
        st.markdown("**✅ Allowlist** *(never replace)*")
        al_input = st.text_input(
            "Add to allowlist",
            key="al_add_input",
            placeholder="e.g. conference",
            label_visibility="collapsed",
        )
        if st.button("Add", key="al_add_btn", type="secondary"):
            word = al_input.strip().lower()
            if word and word not in st.session_state.allowlist_words:
                st.session_state.allowlist_words.append(word)
                _save_prefs(st.session_state.stutter_patterns,
                            st.session_state.blocked_words)
                st.rerun()

        if st.session_state.allowlist_words:
            st.markdown('<div class="blocklist-panel">', unsafe_allow_html=True)
            for aw in list(st.session_state.allowlist_words):
                col_word, col_rm = st.columns([4, 1])
                with col_word:
                    st.markdown(f'<span class="allowlist-item">✅ {_fmt(aw)}</span>',
                                unsafe_allow_html=True)
                with col_rm:
                    if st.button("✕", key=f"al_rm_{aw}", type="secondary",
                                 help=f"Remove '{aw}' from allowlist"):
                        st.session_state.allowlist_words.remove(aw)
                        _save_prefs(st.session_state.stutter_patterns,
                                    st.session_state.blocked_words)
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.caption("No allowlisted words yet.")

# ── Run button ─────────────────────────────────────────────────────────────────
_, col1, _ = st.columns([1, 2, 1])
with col1:
    search_clicked = st.button("Run speech profile", use_container_width=True)

# Auto-clear on new input
if lookup_source.strip() and lookup_source.strip() != st.session_state.get("last_query", ""):
    if not search_clicked:
        for k in ("result", "sanitized", "fixes", "user_choices",
                  "grammar_fixes_applied", "correction_map", "_word_results",
                  "ms_results", "ms_choices", "multi_mode",
                  "rephrase_single_sig", "rephrase_single_result", "rephrase_single_use",
                  "rephrase_paragraph_sig", "rephrase_paragraph_result", "rephrase_paragraph_use"):
            st.session_state[k] = {} if "choices" in k else ([] if k in ("fixes","grammar_fixes_applied","ms_results") else None)
        st.session_state.user_choices  = {}
        st.session_state.ms_choices    = {}
        st.session_state.ms_results    = []
        st.session_state.rephrase_single_use = False
        st.session_state.rephrase_paragraph_use = False

# ── Process on click ───────────────────────────────────────────────────────────
source_text = lookup_source.strip()
if search_clicked and source_text:
    # Reset everything
    st.session_state.update({
        "user_choices": {}, "ms_choices": {}, "ms_results": [],
        "result": None, "sanitized": None, "fixes": [],
        "grammar_fixes_applied": [], "correction_map": {},
        "_word_results": None, "last_query": source_text,
        "original_query": source_text, "multi_mode": False,
        "rephrase_single_sig": None, "rephrase_single_result": None, "rephrase_single_use": False,
        "rephrase_paragraph_sig": None, "rephrase_paragraph_result": None, "rephrase_paragraph_use": False,
    })

    sem.MIN_SEMANTIC = sem_threshold
    patterns = list(st.session_state.stutter_patterns)
    blocked  = set(st.session_state.blocked_words)
    # allowlist → treat as protected (we skip substitution on these words in rewrite)
    allowlisted = set(st.session_state.get("allowlist_words", []))

    # ── Detect multi-sentence ──────────────────────────────────────────────────
    sentences = _split_sentences(source_text)
    is_multi  = len(sentences) > 1

    if is_multi:
        st.session_state.multi_mode = True
        ms_results = []
        with st.spinner(f"Processing {len(sentences)} sentence{'s' if len(sentences)>1 else ''}…"):
            for raw_sent in sentences:
                sanitized, fixes = sanitize_input(raw_sent)
                sent_is_sentence = is_sentence(sanitized)
                result = None
                if sent_is_sentence:
                    result = rewriter.rewrite(
                        sanitized, top_k=top_k,
                        stutter_patterns=patterns,
                        blocked_words=blocked, allowlist=allowlisted,  # allowlist locks words
                    )
                ms_results.append({
                    "raw": raw_sent,
                    "sanitized": sanitized,
                    "fixes": fixes,
                    "is_sentence": sent_is_sentence,
                    "result": result,
                })
        st.session_state.ms_results = ms_results

    else:
        # Single sentence / word mode
        corrected_query, grammar_fixes = sanitize_input(source_text)
        st.session_state.grammar_fixes_applied = grammar_fixes
        st.session_state.corrected_query = corrected_query

        correction_map = {}
        for fix in grammar_fixes:
            orig = fix.get("original", "")
            corr = fix.get("corrected", "")
            if orig and corr:
                correction_map[corr.lower()] = orig
        st.session_state.correction_map = correction_map

        st.session_state.sentence_mode = is_sentence(corrected_query)

        if not st.session_state.sentence_mode:
            with st.spinner("Looking up synonyms…"):
                st.session_state._word_results = engine.get_synonyms(
                    corrected_query, top_k=top_k)
        else:
            # Re-use the already-sanitized corrected_query — no second pass needed.
            # sanitize_input was already called above; calling it again on its own
            # output wastes two full POS-tag passes and can produce duplicate fix entries.
            sanitized = corrected_query
            fixes     = grammar_fixes          # same list, already stored above
            st.session_state.sanitized = sanitized
            st.session_state.fixes     = fixes
            with st.spinner("Analysing sentence, running semantic filter…"):
                result = rewriter.rewrite(
                    sanitized, top_k=top_k,
                    stutter_patterns=patterns,
                    blocked_words=blocked, allowlist=allowlisted,
                )
            st.session_state.result = result

    st.rerun()

elif search_clicked and not source_text:
    st.warning("Please enter a word or sentence.")


# ─────────────────────────────────────────────────────────────────────────────
# RENDER HELPERS — shared between single and multi-sentence modes
# ─────────────────────────────────────────────────────────────────────────────

def _render_word_pickers(result: dict, sanitized: str, sid: int,
                         patterns, blocked, sbert_ok, show_scores) -> str:
    """
    Render synonym picker cards for one sentence.
    sid = sentence index (0 for single mode).
    Returns the rebuilt sentence string.
    """
    choices_key = sid  # int key into ms_choices / 0 for single

    for sub in result["substitutions"]:
        word      = sub["original_word"]
        tag       = sub["tag"]
        pos_key   = sub["position"]
        on_pat    = (word.lower() in blocked) or ph.matches_any(word, patterns)
        diff      = ph.word_difficulty(word)
        onset_str = "/".join(ph.onset(word)) or "—"
        tag_warn  = "<span class='badge badge-red'>⚠ stutter risk</span>" if on_pat else ""
        tag_cls   = "badge-warn" if on_pat else "badge-blue"

        accepted_syns = [
            s for s in sub.get("scored", [])
            if s["accepted"] and s.get("phoneme_ok", True)
        ]
        best_lemma = accepted_syns[0]["lemma"]  if accepted_syns else word.lower()
        best_infl  = accepted_syns[0]["inflected"] if accepted_syns else word
        auto_lemma = best_lemma

        options     = [word]
        for s in accepted_syns[:8]:
            if s["inflected"] not in options:
                options.append(s["inflected"])

        default_idx = 1 if len(options) > 1 else 0
        # Per-sentence per-position choices
        if sid == 0:
            choices = st.session_state.user_choices
        else:
            choices = st.session_state.ms_choices.setdefault(sid, {})

        prior = choices.get(pos_key)
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

        pill_html = '<div class="pill-wrap">'
        for s in accepted_syns[:5]:
            is_best  = s["lemma"] == auto_lemma
            cls      = "top" if is_best else "mid"
            sim_val  = s.get("semantic_sim") or 0
            freq_val = s["freq_score"]
            pill_html += (
                f'<span class="pill {cls}" '
                f'title="sim {sim_val:.2f} · freq {freq_val:.2f}">'
                f'{_fmt(s["inflected"])}</span>'
            )
        pill_html += "</div>"
        st.markdown(pill_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Selectbox + revert button on same row
        scol1, scol2 = st.columns([5, 1])
        with scol1:
            st.markdown(
                f'<div class="picker-word-label">Pick replacement for <em>{word}</em>:</div>',
                unsafe_allow_html=True,
            )
            chosen = st.selectbox(
                f"Replace '{word}' (s{sid})",
                options=options,
                index=default_idx,
                key=f"pick_s{sid}_{pos_key}",
                label_visibility="collapsed",
            )
            choices[pos_key] = chosen

        with scol2:
            st.markdown("<div style='padding-top:1.55rem'>", unsafe_allow_html=True)
            if st.button("↺", key=f"revert_s{sid}_{pos_key}", type="secondary",
                         help=f"Revert '{word}' to the original"):
                choices[pos_key] = word
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # Custom word input
        custom_word = st.text_input(
            f"Or type your own word for '{word}':",
            key=f"custom_s{sid}_{pos_key}",
            placeholder="Type any word…",
        )
        if custom_word.strip():
            cw = custom_word.strip()
            if re.match(r"^[a-zA-Z\-']+$", cw):
                # ── Issue 6 fix: phoneme firewall on custom words ──────────────
                # Warn if the custom word starts with one of the user's stutter
                # onsets or is on their blocked list — same check Gate B applies
                # to engine candidates.  We warn but still allow, because the
                # user may be deliberately overriding for a specific reason.
                cw_onset_hit = (cw.lower() in blocked) or ph.matches_any(cw, patterns)
                if cw_onset_hit and patterns:
                    onset_str_cw = "/".join(ph.onset(cw)) or cw[0].upper()
                    st.caption(
                        f"⚠ '{cw}' starts with your stutter onset (/{onset_str_cw}/) "
                        f"— it may be difficult to say. You can still use it."
                    )
                else:
                    st.caption(f"✓ Using custom word: {cw}")
                choices[pos_key] = cw
            else:
                st.caption("⚠ Custom word should contain only letters.")

        # Scoring table
        if show_scores and sub.get("scored"):
            with st.expander(f"📊 Scores for '{sub['original_word']}'", expanded=False):
                rows_html = ""
                for sc in sub["scored"][:8]:
                    is_chosen = sc["lemma"] == auto_lemma
                    phon_ok   = sc.get("phoneme_ok", True)
                    dimmed    = (not sc["accepted"]) or (not phon_ok)
                    row_cls   = "chosen-row" if is_chosen else ("rejected" if dimmed else "")
                    star      = "★ " if is_chosen else ""
                    if not sc["accepted"]:
                        status_cell = "✗ sem"
                    elif not phon_ok:
                        status_cell = "✗ onset"
                    else:
                        status_cell = "✓"

                    if sbert_ok and sc["semantic_sim"] is not None:
                        sim_val  = sc["semantic_sim"]
                        sim_cls  = "sim-accept" if sc["accepted"] else "sim-reject"
                        bar_w    = int(sim_val * 60)
                        freq_bar = int(sc["freq_score"] * 60)
                        rows_html += (
                            f'<tr class="{row_cls}">'
                            f'<td>{star}{sc["inflected"]}</td>'
                            f'<td><span class="sim-tag {sim_cls}">{sim_val:.2f}</span>'
                            f'<span class="bar-wrap"><span class="bar-fill orange" style="width:{bar_w}px"></span></span></td>'
                            f'<td>{sc["freq_score"]:.2f}'
                            f'<span class="bar-wrap" style="margin-left:4px"><span class="bar-fill" style="width:{freq_bar}px"></span></span></td>'
                            f'<td><strong>{sc["combined"]:.3f}</strong></td>'
                            f'<td>{status_cell}</td></tr>'
                        )
                    else:
                        freq_bar = int(sc["freq_score"] * 60)
                        rows_html += (
                            f'<tr class="{row_cls}">'
                            f'<td>{star}{sc["inflected"]}</td>'
                            f'<td>{sc["freq_score"]:.2f}'
                            f'<span class="bar-wrap" style="margin-left:4px"><span class="bar-fill" style="width:{freq_bar}px"></span></span></td>'
                            f'<td>{status_cell}</td></tr>'
                        )

                if sbert_ok:
                    th = "<tr><th>Candidate</th><th>Semantic</th><th>Freq</th><th>Score</th><th></th></tr>"
                else:
                    th = "<tr><th>Candidate</th><th>Freq</th><th></th></tr>"
                st.markdown(
                    f'<table class="score-table"><thead>{th}</thead><tbody>{rows_html}</tbody></table>',
                    unsafe_allow_html=True,
                )

    # skipped words
    if result.get("skipped"):
        sk_html = " ".join(
            f'<span class="no-syn-chip">⊘ <strong>{s["word"]}</strong>'
            f'<span style="opacity:.7"> — {s["reason"]}</span></span>'
            for s in result["skipped"]
        )
        st.markdown(
            f'<div style="margin-top:.5rem;font-size:.82rem;color:#6f87a6">'
            f'Kept unchanged: {sk_html}</div>',
            unsafe_allow_html=True,
        )

    # return the rebuilt sentence with current choices
    if sid == 0:
        return rewriter.rebuild_with_choices(
            sanitized, result["substitutions"], st.session_state.user_choices)
    else:
        return rewriter.rebuild_with_choices(
            sanitized, result["substitutions"],
            st.session_state.ms_choices.get(sid, {}))


def _render_final_card(sanitized: str, rebuilt: str, prefix: str = "⑤") -> None:
    """Render the final output card with difficulty meter + copy area."""
    from nltk import word_tokenize as _wt
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
  <div class="pipe-label" style="color:#f57c2b">{prefix} Final Sentence</div>
  <div class="output-box">{_fmt(rebuilt)}</div>
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

    st.caption("📋 Copy sentence:")
    st.code(rebuilt, language=None)


def _rephrase_signature(original: str, rebuilt: str, patterns, blocked) -> tuple:
    return (
        original,
        rebuilt,
        tuple(patterns or []),
        tuple(sorted(blocked or [])),
    )


def _combine_rephrase_results(original: str, rebuilt: str, rows: list[dict]) -> dict:
    rephrased = " ".join(r.get("rephrased", "") for r in rows).strip() or rebuilt
    sims = [r.get("sim") for r in rows if r.get("sim") is not None]
    sim = round(sum(sims) / len(sims), 4) if sims else None
    return {
        "rephrased": rephrased,
        "applied": any(r.get("applied") for r in rows),
        "sim": sim,
        "violations": sum(int(r.get("violations") or 0) for r in rows),
        "difficulty": ph.sentence_difficulty(_content_words(rephrased)),
        "candidates": [c for r in rows for c in r.get("candidates", [])],
        "original": original,
    }


def _get_rephrase_result(scope: str, original: str, rebuilt: str,
                         patterns, blocked, sentence_pairs=None) -> dict | None:
    if not st.session_state.get("rephrase_enabled"):
        return None
    import rephrase as _rephrase

    sig = _rephrase_signature(original, rebuilt, patterns, blocked)
    sig_key = f"rephrase_{scope}_sig"
    result_key = f"rephrase_{scope}_result"
    use_key = f"rephrase_{scope}_use"

    if st.session_state.get(sig_key) != sig:
        with st.spinner("Preparing optional fluency rephrase..."):
            if sentence_pairs:
                rows = [
                    _rephrase.choose_best(orig, built, patterns, blocked)
                    for orig, built in sentence_pairs
                ]
                result = _combine_rephrase_results(original, rebuilt, rows)
            else:
                result = _rephrase.choose_best(original, rebuilt, patterns, blocked)
        st.session_state[sig_key] = sig
        st.session_state[result_key] = result
        st.session_state[use_key] = False

    return st.session_state.get(result_key)


def _render_rephrase_card(scope: str, original: str, rebuilt: str,
                          patterns, blocked, sentence_pairs=None) -> str:
    result = _get_rephrase_result(scope, original, rebuilt, patterns, blocked, sentence_pairs)
    if result is None:
        return rebuilt

    use_key = f"rephrase_{scope}_use"
    proposed = result.get("rephrased") or rebuilt
    diff_before = ph.sentence_difficulty(_content_words(rebuilt))
    diff_after = result.get("difficulty")
    if diff_after is None:
        diff_after = ph.sentence_difficulty(_content_words(proposed))
    sim_text = "n/a" if result.get("sim") is None else f"{result['sim']:.2f}"
    applied = bool(result.get("applied"))

    note = "" if applied else '<div style="font-size:.86rem;color:#6f87a6;margin-top:.45rem">No rephrase applied.</div>'
    st.markdown(f"""
<div class="pipe-card" style="border-color:#b8d9f5">
  <div class="pipe-label">⑥ Fluency Rephrase (optional)</div>
  <div class="output-box">{_fmt(proposed)}</div>
  <div style="font-size:.78rem;color:#5a7096;margin-top:.55rem">
    Similarity: <strong>{sim_text}</strong> · onset violations:
    <strong>{int(result.get("violations") or 0)}</strong> · difficulty:
    <strong>{diff_before:.2f} → {diff_after:.2f}</strong>
  </div>
  {note}
</div>""", unsafe_allow_html=True)

    if applied:
        col_use, _ = st.columns([1, 2])
        with col_use:
            if st.button("Use this rephrase", key=f"use_rephrase_{scope}", type="secondary"):
                st.session_state[use_key] = True
        if st.session_state.get(use_key):
            st.caption("Using fluency rephrase for the final output.")

    return proposed if st.session_state.get(use_key) else rebuilt


# ─────────────────────────────────────────────────────────────────────────────
# MULTI-SENTENCE RESULTS
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.get("multi_mode") and st.session_state.ms_results:
    ms_results = st.session_state.ms_results
    patterns   = list(st.session_state.stutter_patterns)
    blocked    = set(st.session_state.blocked_words)

    st.markdown(
        '<span class="mode-tag mode-multi">📄 Paragraph Mode — '
        f'{len(ms_results)} sentences</span>',
        unsafe_allow_html=True,
    )

    # Grammar note (all fixes across sentences)
    all_fixes = []
    for sr in ms_results:
        all_fixes.extend(sr.get("fixes", []))
    if all_fixes:
        with st.expander("📝 Grammar corrections applied", expanded=False):
            st.markdown(_grammar_explanation(all_fixes), unsafe_allow_html=True)

    for sid, sr in enumerate(ms_results):
        sent_sanitized = sr["sanitized"]
        sent_result    = sr.get("result")

        st.markdown(
            f'<div class="sent-card">'
            f'<div class="sent-header">'
            f'<span class="sent-num">#{sid + 1}</span>'
            f'<span class="badge badge-gray" style="font-size:.72rem">'
            f'{"sentence" if sr["is_sentence"] else "phrase"}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Risk chips
        chips_html = _risk_chips(sent_sanitized, patterns, blocked)
        st.markdown(
            f'<div style="margin-bottom:.5rem">{chips_html}</div>',
            unsafe_allow_html=True,
        )

        if sr["is_sentence"] and sent_result and sent_result.get("substitutions"):
            st.markdown("**Synonym pickers:**")
            rebuilt_sent = _render_word_pickers(
                sent_result, sent_sanitized, sid + 1,
                patterns, blocked, sbert_ok, show_scores,
            )

            # Diff highlight for this sentence
            from nltk import word_tokenize as _wt
            orig_tok  = _wt(sent_sanitized)
            reblt_tok = _wt(rebuilt_sent)
            diff_parts = []
            for ot, rt in zip(orig_tok, reblt_tok):
                if ot.lower() != rt.lower() and re.match(r"[a-zA-Z]", ot):
                    diff_parts.append(
                        f'<span class="orig-word">{ot}</span>'
                        f'<span class="new-word">{rt}</span>'
                    )
                else:
                    diff_parts.append(rt)
            highlighted = " ".join(diff_parts)
            st.markdown(
                f'<div class="diff-text" style="margin-top:.4rem">{highlighted}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="color:#5a7096;font-size:.9rem">'
                f'{_fmt(sent_sanitized)}'
                f'<span style="opacity:.5;font-size:.8rem"> — no substitutions</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Full paragraph final output ────────────────────────────────────────────
    full_rebuilt = _full_rebuilt_paragraph()
    if full_rebuilt:
        st.markdown("---")
        st.markdown("### ✦ Rebuilt Paragraph")
        rephrase_pairs = []
        for sid, sr in enumerate(ms_results):
            if sr["is_sentence"] and sr.get("result"):
                rb = rewriter.rebuild_with_choices(
                    sr["sanitized"],
                    sr["result"]["substitutions"],
                    st.session_state.ms_choices.get(sid + 1, {}),
                )
            else:
                rb = sr["sanitized"]
            rephrase_pairs.append((sr["sanitized"], rb))
        original_paragraph = " ".join(orig for orig, _ in rephrase_pairs)
        display_rebuilt = _render_rephrase_card(
            "paragraph",
            original_paragraph,
            full_rebuilt,
            patterns,
            blocked,
            sentence_pairs=rephrase_pairs,
        )

        # Difficulty
        all_words_before = []
        all_words_after  = _content_words(display_rebuilt)
        for sid, sr in enumerate(ms_results):
            all_words_before.extend(_content_words(sr["sanitized"]))

        diff_before = ph.sentence_difficulty(all_words_before)
        diff_after  = ph.sentence_difficulty(all_words_after)
        delta = diff_after - diff_before
        if delta < -0.005:
            d_cls, d_word, arrow = "diff-down", "easier", "↓"
        elif delta > 0.005:
            d_cls, d_word, arrow = "diff-up", "harder", "↑"
        else:
            d_cls, d_word, arrow = "diff-same", "no change", "→"

        st.markdown(f"""
<div class="pipe-card" style="border-color:#f0c090">
  <div class="pipe-label" style="color:#f57c2b">📄 Full Paragraph Output</div>
  <div class="output-box">{_fmt(display_rebuilt)}</div>
  <div style="font-size:.78rem;color:#5a7096;margin-top:.55rem">
    Paragraph stutter difficulty: <strong>{diff_before:.2f} → {diff_after:.2f}</strong>
    <span class="{d_cls}">({arrow} {d_word})</span>
  </div>
</div>""", unsafe_allow_html=True)

        st.caption("📋 Copy paragraph:")
        st.code(display_rebuilt, language=None)

        # Add to session history
        if st.button("💾 Save to session history", key="save_ms_hist", type="secondary"):
            st.session_state.session_history.append({
                "original": st.session_state.original_query,
                "rebuilt":  display_rebuilt,
            })
            st.success("Saved to session history.")


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE-SENTENCE RESULTS
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.get("multi_mode"):
    # Grammar correction note
    if st.session_state.last_query.strip():
        corrected = st.session_state.get("sanitized") or st.session_state.get("corrected_query", "")
        if corrected and corrected.strip() != st.session_state.last_query.strip():
            st.markdown(f"""
<div class="analysis-note">
  <strong style="color:#1a6b3c">Grammar corrected:</strong>
  <span>{_fmt(corrected)}</span>
  <div style="margin-top:.45rem">{_grammar_explanation(st.session_state.get("grammar_fixes_applied", []))}</div>
</div>""", unsafe_allow_html=True)

    # ── Word mode ─────────────────────────────────────────────────────────────
    if not st.session_state.sentence_mode and st.session_state.get("_word_results"):
        word_results = st.session_state._word_results
        patterns = list(st.session_state.stutter_patterns)
        blocked  = set(st.session_state.blocked_words)

        st.markdown('<span class="mode-tag mode-word">🔤 Word / Multi-word Mode</span>',
                    unsafe_allow_html=True)

        for word, syns in word_results.items():
            diff      = ph.word_difficulty(word)
            onset_str = "/".join(ph.onset(word)) or "—"
            on_pat    = (word.lower() in blocked) or ph.matches_any(word, patterns)
            tag_color = "badge-warn" if on_pat else "badge-blue"

            # Defensive normalisation: engine.get_synonyms() may return either
            #   flat list  : ["synonym1", "synonym2", ...]          (current shape)
            #   rich dict  : {"pos": "NN", "synonyms": [{...}, ...]} (future shape)
            # Normalise both to a flat list of strings so the renderer never crashes.
            if isinstance(syns, dict):
                raw_syns = syns.get("synonyms", [])
                syn_strings = [
                    s["lemma"] if isinstance(s, dict) else str(s)
                    for s in raw_syns
                ]
            elif isinstance(syns, list):
                syn_strings = [
                    s["lemma"] if isinstance(s, dict) else str(s)
                    for s in syns
                ]
            else:
                syn_strings = []

            st.markdown(f"""
<div class="word-card">
  <div class="word-card-header">
    <span class="word-title">{_fmt(word)}</span>
    <span class="badge {tag_color}">onset /{onset_str}/</span>
    <span class="badge badge-gray">diff {diff:.2f}</span>
    {"<span class='badge badge-red'>⚠ stutter risk</span>" if on_pat else ""}
  </div>""", unsafe_allow_html=True)

            if syn_strings:
                st.markdown('<div class="pill-wrap">', unsafe_allow_html=True)
                for s in syn_strings[:8]:
                    phon_ok = (not ph.matches_any(s, patterns)
                               and s.lower() not in blocked)
                    cls = "top" if phon_ok else "mid"
                    st.markdown(f'<span class="pill {cls}">{_fmt(s)}</span>',
                                unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown('<span class="badge badge-gray">No synonyms found</span>',
                            unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

    # ── Sentence mode ─────────────────────────────────────────────────────────
    if st.session_state.sentence_mode and st.session_state.result is not None:
        result    = st.session_state.result
        sanitized = st.session_state.sanitized or st.session_state.last_query
        patterns  = list(st.session_state.stutter_patterns)
        blocked   = set(st.session_state.blocked_words)

        st.markdown('<span class="mode-tag mode-sentence">📝 Sentence Mode</span>',
                    unsafe_allow_html=True)

        # ① Risk analysis
        chips_html = _risk_chips(sanitized, patterns, blocked)
        st.markdown(f"""
<div class="pipe-card">
  <div class="pipe-label">① Word Risk Analysis</div>
  {chips_html}
  <div style="font-size:.75rem;color:#6f87a6;margin-top:.42rem">
    <span class="risk-chip risk-hi" style="font-size:.72rem;padding:.15rem .5rem">high</span> onset match/blocked &nbsp;
    <span class="risk-chip risk-mid" style="font-size:.72rem;padding:.15rem .5rem">medium</span> difficulty ≥ 0.55 &nbsp;
    <span class="risk-chip risk-lo" style="font-size:.72rem;padding:.15rem .5rem">low</span> clear
  </div>
</div>""", unsafe_allow_html=True)

        # ② Synonym pickers
        if result["substitutions"]:
            st.markdown("""
<div class="pipe-card">
  <div class="pipe-label">② Synonym Candidates</div>""", unsafe_allow_html=True)

            rebuilt = _render_word_pickers(
                result, sanitized, 0,
                patterns, blocked, sbert_ok, show_scores,
            )

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
<div class="pipe-card">
  <div class="pipe-label">② Synonym Candidates</div>
  <div style="color:#6f87a6;font-size:.9rem">No substitutable content words found.</div>
</div>""", unsafe_allow_html=True)
            rebuilt = sanitized

        # ③ Grammar check on rebuilt
        try:
            from nltk import pos_tag as _pt, word_tokenize as _wt
            _rb_tags  = _pt(_wt(rebuilt))
            _THIRD    = {"he", "she", "it"}
            post_issues = []
            for _idx, (_w, _t) in enumerate(_rb_tags):
                if _w.lower() in _THIRD and _idx + 1 < len(_rb_tags):
                    if _rb_tags[_idx + 1][1] == "VBP":
                        post_issues.append(
                            f'Possible agreement issue: "{_w} {_rb_tags[_idx+1][0]}"')
        except Exception:
            post_issues = []

        pipeline_notes = [n for n in result.get("grammar_notes", [])
                          if "passed" not in n.lower()]

        if post_issues:
            items = "".join(f"<li>{_fmt(i)}</li>" for i in post_issues)
            grammar_html = (f'<div class="grammar-error">⚠ <strong>Grammar issues:</strong>'
                            f'<ul style="margin:.3rem 0 0 1rem;padding:0">{items}</ul></div>')
        elif pipeline_notes:
            items = "".join(f"<li>{_fmt(n)}</li>" for n in pipeline_notes)
            grammar_html = (f'<div class="grammar-warn">⚠ Notes:'
                            f'<ul style="margin:.28rem 0 0 1rem;padding:0">{items}</ul></div>')
        else:
            grammar_html = '<div class="grammar-ok">✓ Grammar check passed.</div>'

        st.markdown(f"""
<div class="pipe-card">
  <div class="pipe-label">③ Grammar Check</div>
  {grammar_html}
</div>""", unsafe_allow_html=True)

        # ④ Diff highlight
        from nltk import word_tokenize as _wt
        orig_tok  = _wt(sanitized)
        reblt_tok = _wt(rebuilt)
        diff_parts = []
        for ot, rt in zip(orig_tok, reblt_tok):
            if ot.lower() != rt.lower() and re.match(r"[a-zA-Z]", ot):
                diff_parts.append(
                    f'<span class="orig-word">{ot}</span>'
                    f'<span class="new-word">{rt}</span>'
                )
            else:
                diff_parts.append(rt)
        highlighted = " ".join(diff_parts)
        st.markdown(f"""
<div class="pipe-card">
  <div class="pipe-label">④ Highlighted Changes</div>
  <div class="diff-text">{highlighted}</div>
</div>""", unsafe_allow_html=True)

        final_rebuilt = _render_rephrase_card(
            "single",
            sanitized,
            rebuilt,
            patterns,
            blocked,
        )

        # ⑤ Final output
        _render_final_card(sanitized, final_rebuilt)

        # Save to session history
        if st.button("💾 Save to session history", key="save_single_hist", type="secondary"):
            st.session_state.session_history.append({
                "original": st.session_state.original_query,
                "rebuilt":  final_rebuilt,
            })
            st.success("Saved!")


# ─────────────────────────────────────────────────────────────────────────────
# SESSION HISTORY
# ─────────────────────────────────────────────────────────────────────────────
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
                st.caption("Rebuilt")
                st.markdown(f'<div class="copy-box">{_fmt(entry["rebuilt"])}</div>',
                            unsafe_allow_html=True)
            st.code(entry["rebuilt"], language=None)
            st.markdown("---")

        if st.button("🗑 Clear history", key="clear_hist", type="secondary"):
            st.session_state.session_history = []
            st.rerun()


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;font-size:.74rem;color:#6f87a6;margin-top:2.5rem">
  Powered by
  <strong style="color:#4b91dc">SBERT all-MiniLM-L6-v2</strong> ·
  <strong style="color:#4b91dc">WordNet</strong> ·
  <strong style="color:#4b91dc">Datamuse</strong> ·
  <strong style="color:#4b91dc">wordfreq</strong> ·
  <strong style="color:#4b91dc">pyinflect</strong> ·
  <strong style="color:#4b91dc">NLTK</strong> ·
  <strong style="color:#a855f7">pyspellchecker</strong> ·
  <strong style="color:#3b82f6">LanguageTool</strong>
</div>
""", unsafe_allow_html=True)
