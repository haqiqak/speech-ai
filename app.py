"""
Synonym Finder — Streamlit UI v4
Pipeline: Sanitize → SBERT Semantic Firewall → Inflect → User Picks → Output
"""

import re
import streamlit as st
from nltk import word_tokenize
from engine import SynonymEngine
from grammar import sanitize_input, is_sentence, SentenceRewriter, inflect, _preserve_case
import semantic as sem

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Synonym Finder",
    page_icon="🔤",
    layout="centered",
    initial_sidebar_state="collapsed",
)

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

/* inputs */
div[data-testid="stTextInput"] input {
    border:2px solid #c3daf7 !important; border-radius:14px !important;
    background:#fff !important; font-family:'DM Sans',sans-serif !important;
    font-size:1.05rem !important; padding:.66rem 1rem !important; color:#1a2740 !important;
    box-shadow:0 2px 10px rgba(75,145,220,.07) !important;
}
div[data-testid="stTextInput"] input:focus { border-color:#4b91dc !important; }
div[data-testid="stTextInput"] label { font-size:.82rem !important; font-weight:600 !important; color:#3d6ea8 !important; }
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

/* cards */
.word-card { background:#fff; border:1.5px solid #d4e8f8; border-radius:16px; padding:1rem 1.3rem .9rem; margin-bottom:.75rem; box-shadow:0 2px 12px rgba(75,145,220,.06); }
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

/* pipeline cards */
.pipe-card { background:#fff; border:1.5px solid #d4e8f8; border-radius:16px; padding:.95rem 1.3rem .9rem; margin-bottom:.75rem; box-shadow:0 2px 12px rgba(75,145,220,.05); }
.pipe-label { font-size:.68rem; font-weight:700; letter-spacing:.8px; text-transform:uppercase; color:#4b91dc; margin-bottom:.38rem; }

/* sanitizer */
.fix-row { display:flex; align-items:center; gap:.48rem; font-size:.87rem; padding:.28rem .48rem; border-radius:8px; margin-bottom:.22rem; }
.fix-row.contraction { background:#fff8f0; color:#c85d14; }
.fix-row.capitalization,.fix-row.pronoun_case { background:#f0f8ff; color:#2d6aab; }
.fix-row.punctuation { background:#f0fdf4; color:#1a6b3c; }
.fix-row.spacing { background:#fafafa; color:#5a7096; }
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
.score-table tr.rejected td { color:#c0c8d8; }
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
.grammar-ok   { background:#edfaf2; border:1.4px solid #7ddba5; border-radius:11px; padding:.55rem .9rem; color:#1a6b3c; font-size:.88rem; }
.grammar-warn { background:#fff8ed; border:1.4px solid #f7c49a; border-radius:11px; padding:.55rem .9rem; color:#a06030; font-size:.88rem; }
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
st.markdown("""
<div class="hero">
  <h1>Synonym <span>Finder</span></h1>
  <p>Grammar correction · SBERT semantic firewall · Contextual ranking · User-controlled substitution</p>
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

# ── Sidebar: SBERT status + settings ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
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
        min_value=0.60, max_value=0.95, value=0.72, step=0.01,
        help="Candidates below this similarity score are rejected. Lower = more permissive.",
        disabled=not sbert_ok,
    )
    st.caption("Only active when SBERT is loaded.")

    st.markdown("---")
    show_scores = st.toggle("Show scoring details", value=True,
        help="Show SBERT similarity scores and ranking for each word.")
    
    st.markdown("---")
    st.markdown("""
<div style="font-size:.75rem;color:#9bb3cc">
<strong style="color:#4b91dc">Pipeline</strong><br>
① Sanitize input grammar<br>
② Get synonym candidates<br>
③ SBERT semantic filter<br>
④ Combined score ranking<br>
⑤ Inflect + user picks<br>
⑥ Rebuild sentence
</div>""", unsafe_allow_html=True)

# ── Controls ──────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    query = st.text_input(
        "Enter word(s) or a sentence",
        placeholder="e.g.  happy, angry   or   The company is under stress.",
        label_visibility="visible",
    )
with col2:
    top_k = st.slider("Results", min_value=5, max_value=20, value=10, step=1)

_, btn_col, _ = st.columns([1.3, 1, 1.3])
with btn_col:
    search_clicked = st.button("Find Synonyms", use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("result", None), ("sanitized", None), ("fixes", []),
    ("user_choices", {}), ("last_query", ""), ("sentence_mode", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Process on button click ───────────────────────────────────────────────────
if search_clicked and query.strip():
    st.session_state.user_choices = {}
    st.session_state.last_query   = query.strip()
    st.session_state.sentence_mode = is_sentence(query.strip())

    if not st.session_state.sentence_mode:
        # Word mode: just look up synonyms
        st.session_state.result    = None
        st.session_state.sanitized = None
        st.session_state.fixes     = []
        with st.spinner("Looking up synonyms…"):
            st.session_state._word_results = engine.get_synonyms(query.strip(), top_k=top_k)
    else:
        sanitized, fixes = sanitize_input(query.strip())
        st.session_state.sanitized = sanitized
        st.session_state.fixes     = fixes
        with st.spinner("Analysing sentence, running semantic filter…"):
            # Pass threshold from sidebar to semantic module at call time
            sem.MIN_SEMANTIC = sem_threshold
            result = rewriter.rewrite(sanitized, top_k=top_k)
        st.session_state.result = result

elif search_clicked and not query.strip():
    st.warning("Please enter a word or sentence.")

# ── Render word mode ──────────────────────────────────────────────────────────
if not st.session_state.sentence_mode and hasattr(st.session_state, "_word_results") and st.session_state._word_results:
    results = st.session_state._word_results
    st.markdown('<span class="mode-tag mode-word">📝 Word Mode</span>', unsafe_allow_html=True)

    no_syns  = [w for w, s in results.items() if not s]
    has_syns = {w: s for w, s in results.items() if s}

    if no_syns:
        chips = " ".join(
            f'<span class="no-syn-chip">⊘ <strong>{w}</strong> — no synonyms</span>'
            for w in no_syns
        )
        st.markdown(f'<div style="margin-bottom:.7rem">{chips}</div>', unsafe_allow_html=True)

    for word, synonyms in has_syns.items():
        pills = "".join(
            f'<span class="pill {"top" if i < 3 else "mid"}">{s}</span>'
            for i, s in enumerate(synonyms)
        )
        st.markdown(f"""
<div class="word-card">
  <div class="word-card-header">
    <span class="word-title">{word.capitalize()}</span>
    <span class="badge badge-blue">{len(synonyms)} synonyms</span>
  </div>
  <div class="pill-wrap">{pills}</div>
</div>""", unsafe_allow_html=True)

# ── Render sentence mode ──────────────────────────────────────────────────────
if st.session_state.sentence_mode and st.session_state.result is not None:
    result    = st.session_state.result
    sanitized = st.session_state.sanitized
    fixes     = st.session_state.fixes

    st.markdown('<span class="mode-tag mode-sentence">✦ Sentence Mode — Semantic Pipeline</span>', unsafe_allow_html=True)

    # ── SBERT status banner ───────────────────────────────────────────────────
    if sbert_ok:
        st.markdown(f'<div class="sbert-on">🧠 <strong>SBERT active</strong> — candidates ranked by semantic similarity + frequency (threshold: {sem_threshold:.2f})</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="sbert-off">⚠ <strong>SBERT offline</strong> — running frequency-only ranking. Download model (~80 MB) on first internet run.</div>', unsafe_allow_html=True)

    # ── Card ①: Input sanitizer ───────────────────────────────────────────────
    if fixes:
        fix_rows = ""
        icons = {"contraction":"✎","capitalization":"Aa","pronoun_case":"Aa","punctuation":"·","spacing":"⎵"}
        for f in fixes:
            icon = icons.get(f["type"], "✎")
            fix_rows += f'<div class="fix-row {f["type"]}"><span>{icon}</span><span class="fix-before">{f["original"] or "(none)"}</span><span>→</span><span class="fix-after">{f["corrected"]}</span><span style="opacity:.55;font-size:.8rem">— {f["description"]}</span></div>'
        st.markdown(f"""
<div class="pipe-card">
  <div class="pipe-label">① Input Grammar Correction</div>
  {fix_rows}
  <div class="corrected-sentence">✓ Corrected: <strong>{sanitized}</strong></div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div class="pipe-card">
  <div class="pipe-label">① Input Grammar Correction</div>
  <div class="clean-sentence">✓ Input is grammatically clean — no corrections needed.</div>
</div>""", unsafe_allow_html=True)

    # ── Card ②: Semantic scoring table + picker ───────────────────────────────
    if result["substitutions"]:
        st.markdown('<div class="pipe-card">', unsafe_allow_html=True)
        st.markdown('<div class="pipe-label">② Synonym Candidates — Semantic Scores &amp; Your Choice</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:.84rem;color:#5a7096;margin-bottom:.7rem">'
            'The <strong style="color:#f57c2b">orange</strong> row is the auto-selected best match. '
            'Use the dropdown to choose a different synonym for any word.'
            + (' Scores show SBERT cosine similarity vs the original sentence.' if sbert_ok else ' Scores show frequency only (SBERT offline).')
            + '</div>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

        subs = result["substitutions"]
        n_cols = min(len(subs), 3)
        cols   = st.columns(n_cols)

        for idx, sub in enumerate(subs):
            col = cols[idx % n_cols]
            with col:
                auto_lemma = sub["chosen_lemma"]
                accepted   = sub["candidates"]        # accepted lemmas
                all_cands  = sub["all_candidates"]    # all (including rejected)

                # Build display options
                def disp(lemma, tag, orig):
                    inf = inflect(lemma, tag)
                    return _preserve_case(orig, inf)

                options = accepted if accepted else [auto_lemma]
                display_labels = [disp(o, sub["tag"], sub["original_word"]) for o in options]
                label_to_lemma = {display_labels[i]: options[i] for i in range(len(options))}

                st.markdown(
                    f'<div class="picker-word-label">'
                    f'<strong>{sub["original_word"]}</strong>'
                    f'<span class="tag-chip" style="margin-left:.3rem">{sub["tag"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                chosen_display = st.selectbox(
                    label=sub["original_word"],
                    options=display_labels,
                    index=0,
                    key=f"pick_{sub['position']}",
                    label_visibility="collapsed",
                )
                st.session_state.user_choices[sub["position"]] = label_to_lemma[chosen_display]

                # Scoring table (collapsible per word)
                if show_scores and sub.get("scored"):
                    with st.expander(f"📊 Scores for '{sub['original_word']}'", expanded=False):
                        header = "Candidate · Semantic · Freq · Score · Status" if sbert_ok else "Candidate · Freq · Status"
                        rows_html = ""
                        for sc in sub["scored"][:8]:
                            is_chosen = sc["lemma"] == auto_lemma
                            row_cls   = "chosen-row" if is_chosen else ("rejected" if not sc["accepted"] else "")
                            star      = "★ " if is_chosen else ""

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
                                status_cell   = '✓' if sc["accepted"] else '✗'
                                rows_html += f'<tr class="{row_cls}"><td>{star}{sc["inflected"]}</td><td>{sem_cell}</td><td>{freq_cell}</td><td>{combined_cell}</td><td>{status_cell}</td></tr>'
                            else:
                                freq_bar = int(sc["freq_score"] * 60)
                                freq_cell = f'{sc["freq_score"]:.2f}<span class="bar-wrap" style="margin-left:4px"><span class="bar-fill" style="width:{freq_bar}px"></span></span>'
                                rows_html += f'<tr class="{row_cls}"><td>{star}{sc["inflected"]}</td><td>{freq_cell}</td><td>✓</td></tr>'

                        if sbert_ok:
                            th = "<tr><th>Candidate</th><th>Semantic</th><th>Frequency</th><th>Combined</th><th></th></tr>"
                        else:
                            th = "<tr><th>Candidate</th><th>Frequency</th><th></th></tr>"
                        st.markdown(f'<table class="score-table"><thead>{th}</thead><tbody>{rows_html}</tbody></table>', unsafe_allow_html=True)

        if result["skipped"]:
            sk_html = " ".join(f'<span class="no-syn-chip">⊘ <strong>{w}</strong></span>' for w in result["skipped"])
            st.markdown(f'<div style="margin-top:.5rem;font-size:.82rem;color:#9bb3cc">Kept unchanged (no valid synonym found): {sk_html}</div>', unsafe_allow_html=True)

    else:
        st.markdown("""
<div class="pipe-card">
  <div class="pipe-label">② Synonym Candidates</div>
  <div style="color:#9bb3cc;font-size:.9rem">No substitutable content words found in this sentence.</div>
</div>""", unsafe_allow_html=True)

    # ── Rebuild with current user choices ─────────────────────────────────────
    user_choices = st.session_state.user_choices
    rebuilt = rewriter.rebuild_with_choices(sanitized, result["substitutions"], user_choices)

    # ── Card ③: Grammar check ─────────────────────────────────────────────────
    notes = result["grammar_notes"]
    if notes and "passed" in notes[0].lower():
        grammar_html = f'<div class="grammar-ok">✓ {notes[0]}</div>'
    elif notes:
        items = "".join(f"<li>{n}</li>" for n in notes)
        grammar_html = f'<div class="grammar-warn">⚠ Notes:<ul style="margin:.28rem 0 0 1rem;padding:0">{items}</ul></div>'
    else:
        grammar_html = '<div class="grammar-ok">✓ No grammar issues detected.</div>'

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

    # ── Card ⑤: Final output ──────────────────────────────────────────────────
    st.markdown(f"""
<div class="pipe-card" style="border-color:#f0c090">
  <div class="pipe-label" style="color:#f57c2b">⑤ Final Sentence</div>
  <div class="output-box">{rebuilt}</div>
</div>""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;font-size:.74rem;color:#9bb3cc;margin-top:2.5rem">
  Powered by
  <strong style="color:#4b91dc">SBERT all-MiniLM-L6-v2</strong> ·
  <strong style="color:#4b91dc">WordNet</strong> ·
  <strong style="color:#4b91dc">Datamuse</strong> ·
  <strong style="color:#4b91dc">wordfreq</strong> ·
  <strong style="color:#4b91dc">pyinflect</strong> ·
  <strong style="color:#4b91dc">NLTK</strong>
</div>
""", unsafe_allow_html=True)
