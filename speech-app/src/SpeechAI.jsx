import { useState, useRef, useEffect } from "react";
import GrammarPanel from "./GrammarPanel";
// ─────────────────────────────────────────────────────────────────────────────
// SpeechAI v3  —  Premium Light-Blue Reskin
// ALL v3 mechanics unchanged: single-pass transform, spike tokens,
// conditional Gemini re-rank, server-driven token model, fallback tokenizer.
// Only styles, layout, palette, and micro-popover visuals are updated.
// ─────────────────────────────────────────────────────────────────────────────

const API = "http://localhost:8000";

// ── Pure helpers (zero changes) ───────────────────────────────────────────────
function clientTokenize(text) {
  const tokens = [];
  const re = /(\w+|[^\w\s]|\s+)/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    const v = m[0];
    if (/^\s+$/.test(v))  tokens.push({ type: "space", value: v, id: tokens.length });
    else if (/^\w+$/.test(v)) tokens.push({ type: "word", value: v, id: tokens.length, original: v });
    else tokens.push({ type: "punct", value: v, id: tokens.length });
  }
  return tokens;
}

function serverTokensToEditorTokens(serverTokens) {
  return serverTokens.map((t, i) => ({
    id: i,
    type: t.is_word ? "word" : (t.text.trim() === "" ? "space" : "punct"),
    value: t.text,
    original: t.text,
    risk_level: t.risk_level,
    risk_score: t.risk_score ?? 0,
    blocked: t.blocked ?? false,
    synonyms: t.synonyms ?? [],
  }));
}

function getSentenceFor(tokens, wordId) {
  const wt = tokens.filter(t => t.type === "word");
  const idx = wt.findIndex(t => t.id === wordId);
  if (idx === -1) return "";
  let s = idx, e = idx;
  while (s > 0 && !/[.!?]/.test(wt[s - 1]?.value || "")) s--;
  while (e < wt.length - 1 && !/[.!?]/.test(wt[e]?.value || "")) e++;
  return wt.slice(s, e + 1).map(t => t.value).join(" ");
}

function getFullText(tokens) { return tokens.map(t => t.value).join(""); }

async function apiFetch(path, body, signal) {
  try {
    const r = await fetch(`${API}${path}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body), signal,
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  } catch (err) {
    if (err.name === "AbortError") throw err;
    console.error(`[StammAI] ${path} failed:`, err.message);
    throw err;
  }
}

// ── Design system — premium light-blue ───────────────────────────────────────
// Hardcoded palette so it renders identically inside any host (no CSS-var deps
// for brand colours). Semantic states (danger/warning/success) still use the
// host vars so they theme correctly in dark mode.
const C = {
  // Surfaces
  pageBg:    "#EFF6FF",          // very light blue-white page wash
  white:     "#FFFFFF",
  panelBg:   "#F0F7FF",          // faint blue tint for secondary surfaces
  inputBg:   "#F7FBFF",

  // Brand blue ramp
  blue50:    "#EFF6FF",
  blue100:   "#DBEAFE",
  blue200:   "#BFDBFE",
  blue300:   "#93C5FD",
  blue400:   "#60A5FA",
  blue500:   "#3B82F6",
  blue600:   "#2563EB",
  blue700:   "#1D4ED8",

  // Text
  ink:       "#0F172A",          // near-black
  inkMid:    "#334155",
  inkFaint:  "#64748B",
  inkGhost:  "#94A3B8",

  // Borders
  rimLight:  "#BFDBFE",          // blue-tinted border
  rimMid:    "#93C5FD",
  rimHard:   "#3B82F6",

  // Semantic — keep host vars for auto dark-mode
  dangerBg:    "var(--color-background-danger)",
  dangerText:  "var(--color-text-danger)",
  dangerRim:   "var(--color-border-danger)",
  warnBg:      "var(--color-background-warning)",
  warnText:    "var(--color-text-warning)",
  warnRim:     "var(--color-border-warning)",
  okBg:        "var(--color-background-success)",
  okText:      "var(--color-text-success)",
  okRim:       "var(--color-border-success)",
};

// Risk chip colours — hard blue-family for high/medium, softer for low/safe
const RISK = {
  high:   { bg: "#FEE2E2", text: "#991B1B", rim: "#FCA5A5", label: "Blocked onset" },
  medium: { bg: "#FEF9C3", text: "#92400E", rim: "#FDE68A", label: "At-risk" },
  low:    { bg: "#DBEAFE", text: "#1E40AF", rim: "#93C5FD", label: "Low risk"  },
  safe:   { bg: "transparent", text: C.ink, rim: "transparent", label: "Safe" },
};

// Button presets
const B = {
  base: {
    display: "inline-flex", alignItems: "center", cursor: "pointer",
    border: `1px solid ${C.rimLight}`,
    borderRadius: 8, padding: "6px 14px",
    fontSize: 13, fontWeight: 500,
    background: C.white, color: C.inkMid,
    transition: "all 0.15s",
    fontFamily: "inherit",
  },
  primary: {
    background: C.blue600, color: "#fff",
    border: "none",
    boxShadow: `0 1px 3px rgba(37,99,235,0.35)`,
  },
  ghost: {
    background: "transparent", color: C.blue600,
    border: `1px solid ${C.rimMid}`,
  },
  sm: { padding: "4px 11px", fontSize: 12, borderRadius: 7 },
  xs: { padding: "3px 9px", fontSize: 11, borderRadius: 6 },
};

// Card shell
const card = (extra = {}) => ({
  background: C.white,
  border: `1px solid ${C.rimLight}`,
  borderRadius: 14,
  padding: "18px 22px",
  ...extra,
});

// Divider rule
const rule = { borderTop: `1px solid ${C.rimLight}`, margin: "14px 0" };

// ── Micro-components ─────────────────────────────────────────────────────────

function Pill({ label, color = C.blue600, bg = C.blue50, rim = C.rimLight, onRemove }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      background: bg, color, border: `1px solid ${rim}`,
      borderRadius: 20, padding: "3px 11px",
      fontSize: 12, fontWeight: 600, letterSpacing: "0.03em",
    }}>
      {label}
      {onRemove && (
        <button onClick={onRemove} aria-label={`Remove ${label}`} style={{
          background: "none", border: "none", cursor: "pointer",
          color, padding: 0, lineHeight: 1, fontSize: 15, opacity: 0.6,
        }}>×</button>
      )}
    </span>
  );
}

function Chip({ children, variant = "blue" }) {
  const map = {
    blue:   { bg: C.blue100, text: C.blue700, rim: C.blue200 },
    red:    { bg: "#FEE2E2", text: "#991B1B", rim: "#FCA5A5" },
    amber:  { bg: "#FEF9C3", text: "#92400E", rim: "#FDE68A" },
    green:  { bg: "#DCFCE7", text: "#166534", rim: "#86EFAC" },
    slate:  { bg: "#F1F5F9", text: C.inkFaint, rim: C.rimLight },
  };
  const s = map[variant] || map.blue;
  return (
    <span style={{
      background: s.bg, color: s.text, border: `1px solid ${s.rim}`,
      borderRadius: 6, padding: "2px 9px", fontSize: 11, fontWeight: 600,
      letterSpacing: "0.04em",
    }}>
      {children}
    </span>
  );
}

function Spinner({ size = 14 }) {
  return (
    <i className="ti ti-loader-2 stamm-spin" style={{ fontSize: size }} />
  );
}

function EngineTag({ method }) {
  if (!method) return null;
  const isCloud = /gemini/i.test(method);
  const isEmbed = /embed/i.test(method);
  const col   = isCloud ? "#D97706" : isEmbed ? C.blue600 : C.inkFaint;
  const icon  = isCloud ? "ti-cloud" : isEmbed ? "ti-brain" : "ti-cpu";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 10, color: col, fontWeight: 500 }}>
      <i className={`ti ${icon}`} style={{ fontSize: 10 }} />
      {method}
    </span>
  );
}

function ConfidenceBadge({ score }) {
  const pct = Math.max(0, Math.min(100, Math.round(score)));
  const col = pct >= 80 ? "#16A34A" : pct >= 55 ? "#D97706" : "#DC2626";
  return <span style={{ fontSize: 11, fontWeight: 700, color: col }}>{pct}%</span>;
}

// Thin section label above cards
function SectionLabel({ children }) {
  return (
    <div style={{
      fontSize: 10, fontWeight: 700, color: C.inkGhost,
      textTransform: "uppercase", letterSpacing: "0.1em",
      marginBottom: 8,
    }}>{children}</div>
  );
}

// Stat card
function StatCard({ label, value, accent }) {
  return (
    <div style={{
      background: C.white, border: `1px solid ${C.rimLight}`,
      borderRadius: 12, padding: "14px 18px",
    }}>
      <div style={{ fontSize: 26, fontWeight: 700, color: accent || C.ink, lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 11, color: C.inkFaint, marginTop: 5, fontWeight: 500, letterSpacing: "0.04em", textTransform: "uppercase" }}>{label}</div>
    </div>
  );
}

// ── QuickAltsPopover  (logic 100% unchanged, visuals reskinned) ──────────────
function QuickAltsPopover({ alternatives, onQuickApply, children }) {
  const [state, setState]   = useState("idle");
  const containerRef        = useRef(null);
  const enterTimer          = useRef(null);
  const leaveTimer          = useRef(null);

  function handleMouseEnter() {
    clearTimeout(leaveTimer.current);
    if (state === "idle") enterTimer.current = setTimeout(() => setState("hovering"), 120);
  }
  function handleMouseLeave() {
    clearTimeout(enterTimer.current);
    if (state !== "pinned") leaveTimer.current = setTimeout(() => setState("idle"), 80);
  }
  function handleWordClick(e) {
    e.stopPropagation();
    if (state === "hovering") { setState("pinned"); return; }
    if (state === "pinned")   { setState("idle");   return; }
  }
  function handleAltClick(alt, e) {
    e.stopPropagation(); onQuickApply(alt); setState("idle");
  }

  useEffect(() => {
    if (state !== "pinned") return;
    const handler = e => {
      if (containerRef.current && !containerRef.current.contains(e.target)) setState("idle");
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [state]);

  const visible     = state === "hovering" || state === "pinned";
  const interactive = state === "pinned";
  const alts        = alternatives?.slice(0, 4) || [];

  return (
    <div
      ref={containerRef}
      style={{ position: "relative", display: "inline-block" }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleWordClick}
    >
      {children}
      {visible && alts.length > 0 && (
        <div style={{
          position: "absolute",
          bottom: "calc(100% + 10px)",
          left: "50%",
          transform: "translateX(-50%)",
          background: C.white,
          border: `1.5px solid ${interactive ? C.blue400 : C.rimLight}`,
          borderRadius: 12,
          padding: "7px 5px 6px",
          zIndex: 300,
          whiteSpace: "nowrap",
          pointerEvents: interactive ? "auto" : "none",
          boxShadow: interactive
            ? `0 8px 28px rgba(37,99,235,0.18), 0 2px 8px rgba(0,0,0,0.07)`
            : `0 4px 16px rgba(0,0,0,0.10)`,
          minWidth: 136,
          animation: "stammFadeIn 0.12s ease",
        }}
          onMouseEnter={() => clearTimeout(leaveTimer.current)}
          onMouseLeave={() => { if (state === "pinned") return; setState("idle"); }}
        >
          {/* Header strip */}
          <div style={{
            fontSize: 9, color: C.inkGhost, textTransform: "uppercase",
            letterSpacing: "0.09em", padding: "0 10px 6px",
            borderBottom: `1px solid ${C.rimLight}`, marginBottom: 4,
            display: "flex", alignItems: "center", justifyContent: "space-between",
          }}>
            <span style={{ fontWeight: 700 }}>Quick replace</span>
            {!interactive && <span style={{ opacity: 0.55 }}>click to pin</span>}
          </div>

          {alts.map((alt, i) => (
            <button key={alt} onClick={e => handleAltClick(alt, e)} style={{
              display: "block", width: "100%",
              background: i === 0 && interactive ? C.blue50 : "transparent",
              color: i === 0 ? C.blue700 : C.inkMid,
              border: "none",
              borderRadius: 7,
              padding: "5px 12px",
              textAlign: "left",
              fontSize: 12.5, fontWeight: i === 0 ? 600 : 400,
              cursor: interactive ? "pointer" : "default",
              fontFamily: "inherit",
              opacity: interactive ? 1 : 0.82,
              transition: "background 0.1s",
              letterSpacing: "0.01em",
            }}
              onMouseOver={e => { if (interactive) e.currentTarget.style.background = C.blue100; }}
              onMouseOut={e => { e.currentTarget.style.background = i === 0 && interactive ? C.blue50 : "transparent"; }}
            >
              {i === 0
                ? <><span style={{ marginRight: 5, fontSize: 10 }}>★</span>{alt}</>
                : <><span style={{ marginRight: 6, color: C.rimMid }}>·</span>{alt}</>}
            </button>
          ))}

          {!interactive && (
            <div style={{ fontSize: 9, color: C.inkGhost, padding: "5px 10px 1px", textAlign: "center" }}>
              Click word to interact
            </div>
          )}

          {/* Caret */}
          <div style={{
            position: "absolute", bottom: -6, left: "50%",
            transform: "translateX(-50%) rotate(45deg)",
            width: 10, height: 10,
            background: C.white,
            border: `1.5px solid ${interactive ? C.blue400 : C.rimLight}`,
            borderTop: "none", borderLeft: "none",
          }} />
        </div>
      )}
    </div>
  );
}

// ── WordToken  (logic unchanged, styles reskinned) ────────────────────────────
function WordToken({ tok, isSelected, wasModified, riskStyle, alternatives, onClick, onQuickApply }) {
  let bg, color, border, shadow = "none";

  if (isSelected) {
    bg = C.blue600; color = "#fff";
    border = `1.5px solid ${C.blue600}`;
    shadow = `0 2px 8px rgba(37,99,235,0.30)`;
  } else if (wasModified) {
    bg = "#DCFCE7"; color = "#166534";
    border = `1px solid #86EFAC`;
  } else if (riskStyle && riskStyle.bg !== "transparent") {
    bg = riskStyle.bg; color = riskStyle.text;
    border = `1px solid ${riskStyle.rim}`;
  } else {
    bg = "transparent"; color = C.ink;
    border = "1px solid transparent";
  }

  const hasAlts = !wasModified && !isSelected && alternatives?.length > 0;

  const wordBtn = (
    <button onClick={onClick} style={{
      background: bg, color, border,
      borderRadius: 7,
      padding: "2px 8px",
      cursor: "pointer",
      fontSize: 15.5,
      fontFamily: "inherit",
      fontWeight: wasModified ? 500 : 400,
      boxShadow: shadow,
      transition: "all 0.13s",
      margin: "2px 1px",
      lineHeight: 1.6,
    }}
      title={riskStyle?.label || (wasModified ? `Replaced — was: ${tok.original || tok.value}` : "Click to adapt")}
    >
      {tok.value}
    </button>
  );

  if (hasAlts && onQuickApply) {
    return <QuickAltsPopover alternatives={alternatives} onQuickApply={onQuickApply}>{wordBtn}</QuickAltsPopover>;
  }
  return <span style={{ display: "inline-block" }}>{wordBtn}</span>;
}

// ── ROOT (all v3 state logic preserved exactly) ───────────────────────────────
export default function SpeechAI() {
  const [phase,           setPhase]           = useState("input");
  const [rawText,         setRawText]         = useState("");
  const [tokens,          setTokens]          = useState([]);
  const [synonymsMap,     setSynonymsMap]     = useState({});
  const [changeHistory,   setChangeHistory]   = useState([]);
  const [semanticCheck,   setSemanticCheck]   = useState(null);
  const [semanticLoading, setSemanticLoading] = useState(false);
  const [blockProfile,    setBlockProfile]    = useState(["S","P","ST","SP","PR","TR"]);
  const [newBlock,        setNewBlock]        = useState("");
  const [activePanel,     setActivePanel]     = useState("synonyms");
  const [rephraseLoading, setRephraseLoading] = useState(false);
  const [rephraseOptions, setRephraseOptions] = useState(null);
  const [selectedId,      setSelectedId]      = useState(null);
  const [transformLoading,setTransformLoading]= useState(false);
  const [transformError,  setTransformError]  = useState(null);
  const [spikeLoading,    setSpikeLoading]    = useState(false);
  const [spikeHistory,    setSpikeHistory]    = useState([]);
  const abortRef = useRef(null);

  // Deriving active working string directly from current token streams safely
  const currentOutputText = tokens.map(t => t.value).join("");

  const selectedToken = tokens.find(t => t.id === selectedId && t.type === "word");
  const deepFetched   = selectedId != null ? synonymsMap[selectedId] : null;
  const synonymData   = deepFetched || (selectedToken
    ? { synonyms: selectedToken.synonyms || [], note: "Pre-fetched by server", engine: "embedding", confidence: null }
    : null);

  // ── StammAI GrammarGuard States ──
  const [grammarReport,    setGrammarReport]    = useState(null);
  const [grammarLoading,   setGrammarLoading]   = useState(false);
  const [grammarAutoApply, setGrammarAutoApply] = useState(false);

  // Core API validation worker
  async function runGrammarCheck(explicitModifiedText) {
    setGrammarLoading(true); 
    setGrammarReport(null);
    
    // Target fallback sequence safely using current rendering outputs
    const textToVerify = explicitModifiedText || currentOutputText;
    
    try {
      const data = await apiFetch("/api/grammar-check", {
        original_text: rawText,
        modified_text: textToVerify,
      });
      setGrammarReport(data);
      
      // If Auto-apply is active, pipeline structural corrections down to re-tokenization
      if (data.corrected_text && data.corrected_text !== textToVerify) {
        if (grammarAutoApply) {
          await runTransform(data.corrected_text, blockProfile);
        }
      }
    } catch(e) { 
      console.error("[StammAI] grammar-check execution failed:", e); 
    } finally { 
      setGrammarLoading(false); 
    }
  }

  // v3: single-pass transform engine
  async function runTransform(textToUse, profileToUse) {
    const text    = textToUse    ?? rawText;
    const profile = profileToUse ?? blockProfile;
    if (!text.trim()) return;
    
    setTransformLoading(true); 
    setTransformError(null); 
    setSynonymsMap({});
    
    try {
      const data = await apiFetch("/api/transform-paragraph", {
        text, 
        block_profile: profile, 
        risk_threshold: 0.65, 
        top_n: 5,
      });
      setTokens(serverTokensToEditorTokens(data.tokens));
      setPhase("editor"); 
      setSelectedId(null);
      setChangeHistory([]); 
      setSemanticCheck(null);
    } catch (e) {
      if (e.name !== "AbortError") {
        setTransformError("Backend unreachable — client tokenizer active, no risk data.");
        setTokens(clientTokenize(text));
        setPhase("editor"); 
        setSelectedId(null); 
        setChangeHistory([]);
      }
    } finally { 
      setTransformLoading(false); 
    }
  }
  
  // v3: spike reporting
  async function reportSpike(word) {
    setSpikeLoading(true);
    try {
      const data = await apiFetch("/api/user/report-spike", { word: word.toLowerCase(), multiplier: 1.5 });
      setSpikeHistory(h => [...h, { word, onset: data.onset_registered }]);
      await runTransform(getFullText(tokens), blockProfile);
    } catch (e) { console.error("[StammAI] report-spike failed:", e); }
    finally { setSpikeLoading(false); }
  }

  // v3: optional deep Gemini re-rank
  async function deepFetchSynonyms(token) {
    if (synonymsMap[token.id]?.synonyms) return;
    setSynonymsMap(m => ({ ...m, [token.id]: { loading: true } }));
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();
    try {
      const data = await apiFetch("/api/synonyms", {
        word: token.value, sentence_context: getSentenceFor(tokens, token.id),
        block_profile: blockProfile, n: 6,
      }, abortRef.current.signal);
      setSynonymsMap(m => ({ ...m, [token.id]: {
        loading: false, synonyms: data.synonyms || [],
        note: data.context_note || "", engine: data.engine || null, confidence: data.confidence ?? null,
      }}));
    } catch (error) {
      if (error.name !== "AbortError")
        setSynonymsMap(m => ({ ...m, [token.id]: { loading: false, synonyms: token.synonyms || [], error: true } }));
    }
  }

  function handleWordClick(token) {
    if (selectedId === token.id) { setSelectedId(null); setActivePanel("synonyms"); return; }
    setSelectedId(token.id); setActivePanel("synonyms"); setRephraseOptions(null);
  }
  function handleQuickApply(token, alt) { applyReplacement(token.id, alt); }

  function applyReplacement(wordId, newWord) {
    const old = tokens.find(t => t.id === wordId); if (!old) return;
    const cased = /[A-Z]/.test(old.value[0]) ? newWord[0].toUpperCase() + newWord.slice(1) : newWord;
    setTokens(ts => ts.map(t => t.id === wordId ? { ...t, value: cased, risk_level: "safe", synonyms: [] } : t));
    setChangeHistory(h => [...h, { wordId, from: old.value, to: cased, type: "word" }]);
    setSynonymsMap(m => { const n = { ...m }; delete n[wordId]; return n; });
    setSelectedId(null); setSemanticCheck(null);
  }

  function undoLast() {
    if (!changeHistory.length) return;
    const last = changeHistory[changeHistory.length - 1];
    if (last.wordId === -1) {
      runTransform(getFullText(tokens).replace(last.to, last.from), blockProfile);
    } else {
      setTokens(ts => ts.map(t => t.id === last.wordId ? { ...t, value: last.from } : t));
    }
    setChangeHistory(h => h.slice(0, -1)); setSemanticCheck(null);
  }

  async function checkSemantics() {
    setSemanticLoading(true); setSemanticCheck(null);
    try {
      const data = await apiFetch("/api/check-semantics", { original_text: rawText, modified_text: getFullText(tokens) });
      setSemanticCheck(data);
    } catch (e) { console.error("Semantics error:", e); }
    finally { setSemanticLoading(false); }
  }

  async function fetchRephrase() {
    if (!selectedToken) return;
    setRephraseLoading(true); setRephraseOptions(null);
    try {
      const data = await apiFetch("/api/rephrase", { sentence: getSentenceFor(tokens, selectedToken.id), block_profile: blockProfile, n: 3 });
      setRephraseOptions(data.rephrased || []);
    } catch (e) { console.error("Rephrase error:", e); }
    finally { setRephraseLoading(false); }
  }

  function applyRephrase(newSentence) {
    const sentence = getSentenceFor(tokens, selectedToken.id);
    runTransform(getFullText(tokens).replace(sentence, newSentence), blockProfile);
    setChangeHistory(h => [...h, { wordId: -1, from: sentence, to: newSentence, type: "sentence" }]);
    setSelectedId(null); setRephraseOptions(null); setSemanticCheck(null);
  }

  function resetAll() {
    setPhase("input"); setTokens([]); setSelectedId(null);
    setSynonymsMap({}); setChangeHistory([]); setSemanticCheck(null);
    setRephraseOptions(null); setSpikeHistory([]); setTransformError(null);
  }

  const changed   = changeHistory.length > 0;
  const outputText = getFullText(tokens);
  const wordTokens = tokens.filter(t => t.type === "word");
  const highRisk   = wordTokens.filter(t => t.risk_level === "high").length;
  const medRisk    = wordTokens.filter(t => t.risk_level === "medium").length;
  const modifiedIds = new Set(changeHistory.map(c => c.wordId).filter(id => id >= 0));

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        @keyframes stammFadeIn {
          from { opacity:0; transform:translateX(-50%) translateY(6px); }
          to   { opacity:1; transform:translateX(-50%) translateY(0);   }
        }
        @keyframes stammSpin { to { transform:rotate(360deg); } }
        .stamm-spin  { animation:stammSpin .75s linear infinite; display:inline-block; }
        .stamm-ghost { transition:background .14s, box-shadow .14s; }
        .stamm-ghost:hover { background:${C.blue50} !important; }
        .stamm-row-hover:hover { background:${C.panelBg}; }
        textarea:focus, input:focus { outline:none; border-color:${C.blue400} !important;
          box-shadow:0 0 0 3px rgba(96,165,250,0.20); }
      `}</style>

      <div style={{ fontFamily: "'Inter', sans-serif", color: C.ink, minHeight: "100vh", padding: "0 0 3rem" }}>
        <h2 className="sr-only">StammAI — Fluency Adaptation Editor</h2>

        {/* ── Top bar ─────────────────────────────────────────────────────── */}
        <div style={{
          background: C.white,
          borderBottom: `1px solid ${C.rimLight}`,
          padding: "14px 28px",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          position: "sticky", top: 0, zIndex: 100,
          boxShadow: `0 1px 6px rgba(37,99,235,0.07)`,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: `linear-gradient(135deg, ${C.blue500}, ${C.blue700})`,
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: `0 2px 8px rgba(37,99,235,0.35)`,
            }}>
              <i className="ti ti-microphone" style={{ fontSize: 18, color: "#fff" }} />
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 700, color: C.ink, letterSpacing: "-0.01em" }}>StammAI</div>
              <div style={{ fontSize: 11, color: C.inkFaint, fontWeight: 500 }}>Fluency Adaptation Engine</div>
            </div>
          </div>

          {phase === "editor" && (
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {changed && (
                <button onClick={undoLast} className="stamm-ghost" style={{ ...B.base, ...B.sm }}>
                  <i className="ti ti-arrow-back-up" style={{ fontSize: 13, marginRight: 5 }} />Undo
                </button>
              )}
              <button
                onClick={() => runTransform(getFullText(tokens), blockProfile)}
                disabled={transformLoading}
                className="stamm-ghost"
                style={{ ...B.base, ...B.sm, opacity: transformLoading ? 0.6 : 1 }}
              >
                {transformLoading
                  ? <><Spinner /> <span style={{ marginLeft: 6 }}>Analysing…</span></>
                  : <><i className="ti ti-scan" style={{ fontSize: 13, marginRight: 5 }} />Re-analyse</>}
              </button>
              <button onClick={resetAll} className="stamm-ghost" style={{ ...B.base, ...B.sm }}>
                <i className="ti ti-refresh" style={{ fontSize: 13, marginRight: 5 }} />Reset
              </button>
            </div>
          )}
        </div>

        {/* ── Body ────────────────────────────────────────────────────────── */}
        <div style={{ maxWidth: 820, margin: "0 auto", padding: "28px 24px 0" }}>

          {/* Page title row (below topbar) */}
          <div style={{ marginBottom: 24 }}>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: C.ink, letterSpacing: "-0.02em", margin: "0 0 4px" }}>
              {phase === "input" ? "Prepare your speech" : "Adapt your text"}
            </h1>
            <p style={{ fontSize: 14, color: C.inkFaint, margin: 0 }}>
              {phase === "input"
                ? "Paste your text, configure your blocked phoneme profile, then click Adapt."
                : "Highlighted words carry fluency risk. Click any word for alternatives or rephrase the whole sentence."}
            </p>
          </div>

          {/* Error banner */}
          {transformError && (
            <div style={{
              background: "#FEF2F2", border: "1px solid #FCA5A5",
              borderRadius: 10, padding: "10px 16px",
              fontSize: 13, color: "#991B1B",
              display: "flex", alignItems: "center", gap: 8, marginBottom: 20,
            }}>
              <i className="ti ti-alert-triangle" style={{ fontSize: 15 }} />
              {transformError}
            </div>
          )}

          {phase === "input"
            ? <InputPhase {...{ rawText, setRawText, blockProfile, setBlockProfile, newBlock, setNewBlock }}
                onStart={() => runTransform(rawText, blockProfile)} loading={transformLoading} />
            : <EditorPhase {...{
                tokens, selectedId, selectedToken, synonymData,
                deepFetchSynonyms: () => selectedToken && deepFetchSynonyms(selectedToken),
                onWordClick: handleWordClick,
                onApplyReplacement: applyReplacement,
                onQuickApply: handleQuickApply,
                changed, changeHistory, outputText,
                semanticCheck, semanticLoading, onCheckSemantics: checkSemantics,
                activePanel, setActivePanel,
                onFetchRephrase: fetchRephrase,
                rephraseLoading, rephraseOptions, onApplyRephrase: applyRephrase,
                blockProfile, highRisk, medRisk, modifiedIds, wordTokens,
                spikeLoading, spikeHistory,
                onReportSpike: () => selectedToken && reportSpike(selectedToken.value),
                
                // ── NEW GRAMMAR PROPS PASSED DOWN ────────────────────────────────────────
                grammarReport, grammarLoading, grammarAutoApply,
                onToggleAutoApply: () => setGrammarAutoApply(prev => !prev),
                onCheckGrammar: () => runGrammarCheck(currentOutputText),
                onApplyGrammarCorrection: (correctedText) => runTransform(correctedText, blockProfile)
              }} />
          }
        </div>
      </div>
    </>
  );
}

// ── InputPhase ────────────────────────────────────────────────────────────────
function InputPhase({ rawText, setRawText, blockProfile, setBlockProfile, newBlock, setNewBlock, onStart, loading }) {
  function addBlock() {
    const v = newBlock.trim().toUpperCase();
    if (v && !blockProfile.includes(v)) setBlockProfile(p => [...p, v]);
    setNewBlock("");
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>

      {/* Text input card */}
      <div style={card()}>
        <SectionLabel>Your text</SectionLabel>
        <textarea
          value={rawText} onChange={e => setRawText(e.target.value)} autoFocus
          placeholder="Paste or type the speech you want to prepare…"
          style={{
            width: "100%", minHeight: 160, resize: "vertical",
            border: `1px solid ${C.rimLight}`, borderRadius: 10,
            background: C.inputBg, color: C.ink,
            padding: "12px 14px", fontSize: 15, lineHeight: 1.75,
            fontFamily: "inherit", boxSizing: "border-box",
            transition: "border-color 0.15s, box-shadow 0.15s",
          }}
        />
        {rawText.trim() && (
          <div style={{ fontSize: 11, color: C.inkGhost, marginTop: 6, textAlign: "right", fontWeight: 500 }}>
            {rawText.trim().split(/\s+/).length} words
          </div>
        )}
      </div>

      {/* Block profile card */}
      <div style={card()}>
        <SectionLabel>Blocked phoneme onsets</SectionLabel>
        <p style={{ fontSize: 13, color: C.inkFaint, margin: "0 0 14px", lineHeight: 1.6 }}>
          Words beginning with these consonant sounds will be flagged as high-risk and prioritised for replacement.
        </p>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 7, marginBottom: 16 }}>
          {blockProfile.map(ph => (
            <Pill key={ph} label={ph} color={C.blue700} bg={C.blue100} rim={C.blue200}
              onRemove={() => setBlockProfile(p => p.filter(x => x !== ph))} />
          ))}
          {blockProfile.length === 0 && (
            <span style={{ fontSize: 13, color: C.inkGhost, fontStyle: "italic" }}>No onsets blocked</span>
          )}
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={newBlock} onChange={e => setNewBlock(e.target.value)}
            onKeyDown={e => e.key === "Enter" && addBlock()}
            placeholder="Add onset  e.g. ST, FR, BL"
            style={{
              flex: 1, border: `1px solid ${C.rimLight}`, borderRadius: 9,
              background: C.inputBg, color: C.ink,
              padding: "8px 12px", fontSize: 13, fontFamily: "inherit",
              transition: "border-color 0.15s, box-shadow 0.15s",
            }}
          />
          <button onClick={addBlock} className="stamm-ghost" style={{ ...B.base, ...B.sm, border: `1px solid ${C.rimMid}` }}>
            <i className="ti ti-plus" style={{ fontSize: 13, marginRight: 4 }} />Add
          </button>
        </div>
      </div>

      {/* CTA */}
      <button
        onClick={onStart}
        disabled={!rawText.trim() || loading}
        style={{
          ...B.base, ...B.primary,
          padding: "12px 28px", fontSize: 14, borderRadius: 10,
          opacity: rawText.trim() && !loading ? 1 : 0.5,
          cursor: rawText.trim() && !loading ? "pointer" : "not-allowed",
          alignSelf: "flex-start",
        }}
      >
        {loading
          ? <><Spinner size={15} /><span style={{ marginLeft: 8 }}>Analysing…</span></>
          : <><i className="ti ti-wand" style={{ fontSize: 15, marginRight: 8 }} />Adapt text</>}
      </button>
    </div>
  );
}

// ── EditorPhase ───────────────────────────────────────────────────────────────
function EditorPhase({
  tokens, selectedId, selectedToken, synonymData, deepFetchSynonyms,
  onWordClick, onApplyReplacement, onQuickApply,
  changed, changeHistory, outputText,
  semanticCheck, semanticLoading, onCheckSemantics,
  activePanel, setActivePanel,
  onFetchRephrase, rephraseLoading, rephraseOptions, onApplyRephrase,
  blockProfile, highRisk, medRisk, modifiedIds, wordTokens,
  spikeLoading, spikeHistory, onReportSpike, grammarReport,
  grammarLoading,
  grammarAutoApply,
  onToggleAutoApply,
  onCheckGrammar,
  onApplyGrammarCorrection
}) {
  const [copied,      setCopied]      = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  function copy() {
    navigator.clipboard.writeText(outputText);
    setCopied(true); setTimeout(() => setCopied(false), 1600);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>

      {/* Stat row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(115px, 1fr))", gap: 12 }}>
        <StatCard label="Total words"    value={wordTokens.length} />
        <StatCard label="Blocked"        value={highRisk} accent={highRisk  > 0 ? "#DC2626" : undefined} />
        <StatCard label="At-risk"        value={medRisk}  accent={medRisk   > 0 ? "#D97706" : undefined} />
        <StatCard label="Replaced"       value={modifiedIds.size} accent={modifiedIds.size > 0 ? "#16A34A" : undefined} />
        <StatCard label="Spikes flagged" value={spikeHistory.length} accent={spikeHistory.length > 0 ? C.blue600 : undefined} />
      </div>

      {/* Risk summary pill row */}
      {(highRisk + medRisk) > 0 && (
        <div style={{
          ...card({ padding: "12px 18px" }),
          display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10,
        }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: C.inkMid }}>Risk overview</span>
          {highRisk > 0  && <Chip variant="red">{highRisk} blocked</Chip>}
          {medRisk  > 0  && <Chip variant="amber">{medRisk} at-risk</Chip>}
          <span style={{ marginLeft: "auto", fontSize: 12, color: C.inkFaint }}>
            Synonyms pre-loaded · hover any word, or click to open panel
          </span>
        </div>
      )}

      {/* Spike session ribbon */}
      {spikeHistory.length > 0 && (
        <div style={{
          background: "#FFFBEB", border: "1px solid #FDE68A",
          borderRadius: 12, padding: "11px 18px",
          fontSize: 12, color: "#92400E",
          display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap",
        }}>
          <i className="ti ti-bolt" style={{ fontSize: 14, color: "#D97706" }} />
          <span style={{ fontWeight: 600 }}>Session spikes:</span>
          {spikeHistory.map((s, i) => (
            <Chip key={i} variant="amber">
              {s.word}{s.onset ? ` · ${s.onset}` : ""}
            </Chip>
          ))}
          <span style={{ marginLeft: "auto", opacity: 0.7 }}>Onset-cluster risk updated</span>
        </div>
      )}

      {/* ── Token canvas card ──────────────────────────────────────────────── */}
      <div style={card({ padding: "20px 22px" })}>
        {/* Canvas toolbar */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: C.inkMid, letterSpacing: "0.01em" }}>
            Click any word to adapt
            <span style={{ fontWeight: 400, color: C.inkGhost }}> — hover a highlighted word for quick replace</span>
          </div>
          {/* Risk legend */}
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            {[["high","Blocked","#FEE2E2","#FCA5A5"],["medium","At-risk","#FEF9C3","#FDE68A"],["low","Low risk",C.blue100,C.blue200]].map(([lvl, lbl, bg, rim]) => (
              <span key={lvl} style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, color: C.inkFaint, fontWeight: 500 }}>
                <span style={{ width: 10, height: 10, borderRadius: 3, background: bg, border: `1px solid ${rim}`, flexShrink: 0 }} />
                {lbl}
              </span>
            ))}
          </div>
        </div>

        {/* Tokens */}
        <div style={{
          minHeight: 80,
          lineHeight: 2.2,
          display: "flex", flexWrap: "wrap", gap: "0 1px",
          padding: "8px 4px",
          background: C.inputBg,
          borderRadius: 10,
          border: `1px solid ${C.rimLight}`,
        }}>
          {tokens.map(tok => {
            if (tok.type !== "word") return (
              <span key={tok.id} style={{ fontSize: 15.5, color: C.inkMid }}>{tok.value}</span>
            );
            const isSelected  = tok.id === selectedId;
            const wasModified = modifiedIds.has(tok.id);
            const riskLevel   = (!wasModified && !isSelected) ? (tok.risk_level || null) : null;
            const riskStyle   = riskLevel ? RISK[riskLevel] : null;
            const alts        = tok.synonyms || [];
            return (
              <WordToken key={tok.id} tok={tok}
                isSelected={isSelected} wasModified={wasModified}
                riskStyle={riskStyle} alternatives={alts}
                onClick={() => onWordClick(tok)}
                onQuickApply={alts.length ? alt => onQuickApply(tok, alt) : null}
              />
            );
          })}
        </div>
      </div>

      {/* ── Word adaptation panel (shown when a word is selected) ─────────── */}
      {selectedToken && (
        <WordPanel
          token={selectedToken}
          synonymData={synonymData}
          onApply={newWord => onApplyReplacement(selectedToken.id, newWord)}
          onDeepFetch={deepFetchSynonyms}
          activePanel={activePanel}
          setActivePanel={setActivePanel}
          onFetchRephrase={onFetchRephrase}
          rephraseLoading={rephraseLoading}
          rephraseOptions={rephraseOptions}
          onApplyRephrase={onApplyRephrase}
          spikeLoading={spikeLoading}
          onReportSpike={onReportSpike}
        />
      )}

      {/* ── Semantic integrity card ────────────────────────────────────────── */}
      {changed && (
        <div style={card({ padding: "16px 22px" })}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: C.ink, marginBottom: 2 }}>
                <i className="ti ti-shield-check" style={{ fontSize: 14, marginRight: 7, color: C.blue500 }} />
                Semantic integrity
              </div>
              <div style={{ fontSize: 12, color: C.inkFaint }}>Verify your swaps preserved the original meaning</div>
            </div>
            <button onClick={onCheckSemantics} disabled={semanticLoading}
              className="stamm-ghost" style={{ ...B.base, ...B.sm }}>
              {semanticLoading ? <><Spinner /><span style={{ marginLeft: 6 }}>Checking…</span></> : "Check now"}
            </button>
          </div>

          {semanticCheck && (
            <div style={{
              marginTop: 14,
              background: semanticCheck.preserved ? "#F0FDF4" : "#FFFBEB",
              border: `1px solid ${semanticCheck.preserved ? "#86EFAC" : "#FDE68A"}`,
              borderRadius: 10, padding: "12px 16px",
              color: semanticCheck.preserved ? "#166534" : "#92400E",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: semanticCheck.issues?.length ? 8 : 0 }}>
                <i className={`ti ${semanticCheck.preserved ? "ti-circle-check" : "ti-alert-triangle"}`} style={{ fontSize: 15 }} />
                <span style={{ fontWeight: 600, fontSize: 13 }}>
                  {semanticCheck.preserved ? "Meaning preserved" : "Meaning may have shifted"}
                  {" — "}<ConfidenceBadge score={semanticCheck.score} />
                </span>
                {semanticCheck.method && <span style={{ marginLeft: "auto" }}><EngineTag method={semanticCheck.method} /></span>}
              </div>
              {semanticCheck.issues?.map((issue, i) => (
                <div key={i} style={{ fontSize: 12, marginTop: 4, paddingLeft: 22 }}>• {issue}</div>
              ))}
              {semanticCheck.suggestion && (
                <div style={{ marginTop: 8, fontSize: 12, paddingLeft: 22 }}>
                  <span style={{ fontWeight: 600 }}>Suggestion:</span> {semanticCheck.suggestion}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── NEW: STAMMAI GRAMMARGUARD SHIELD INTEGRATION ────────────────────── */}
      <GrammarPanel
        report={grammarReport}
        loading={grammarLoading}
        autoApply={grammarAutoApply}
        onToggleAutoApply={onToggleAutoApply}
        onCheck={onCheckGrammar}
        onApplyCorrection={onApplyGrammarCorrection}
        changed={changed}
      />

      {/* ── Output card ───────────────────────────────────────────────────── */}
      <div style={card({ padding: "16px 22px" })}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <SectionLabel>Final output</SectionLabel>
          <div style={{ display: "flex", gap: 7 }}>
            {changed && (
              <button onClick={() => setShowHistory(h => !h)}
                className="stamm-ghost" style={{ ...B.base, ...B.xs }}>
                <i className="ti ti-history" style={{ fontSize: 12, marginRight: 4 }} />
                {showHistory ? "Hide" : "History"} ({changeHistory.length})
              </button>
            )}
            <button onClick={copy} className="stamm-ghost" style={{
              ...B.base, ...B.xs,
              ...(copied ? { background: "#DCFCE7", borderColor: "#86EFAC", color: "#166534" } : {}),
            }}>
              <i className={`ti ${copied ? "ti-check" : "ti-copy"}`} style={{ fontSize: 12, marginRight: 4 }} />
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        </div>

        <div style={{
          background: C.inputBg, border: `1px solid ${C.rimLight}`,
          borderRadius: 10, padding: "14px 16px",
          fontSize: 15.5, lineHeight: 1.8, minHeight: 48,
          color: C.ink,
        }}>
          {outputText}
        </div>

        {showHistory && changeHistory.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <div style={rule} />
            <SectionLabel>Change history</SectionLabel>
            {changeHistory.map((c, i) => (
              <div key={i} className="stamm-row-hover" style={{
                display: "flex", alignItems: "flex-start", gap: 10,
                padding: "7px 10px", borderRadius: 8,
                fontSize: 13, marginBottom: 2,
              }}>
                <span style={{ fontSize: 10, color: C.inkGhost, marginTop: 2, flexShrink: 0, fontWeight: 600 }}>
                  {c.type === "sentence" ? "¶" : "#"}
                </span>
                <span style={{ color: "#DC2626", textDecoration: "line-through", fontWeight: 500, wordBreak: "break-word" }}>{c.from}</span>
                <i className="ti ti-arrow-right" style={{ fontSize: 12, color: C.inkGhost, flexShrink: 0, marginTop: 2 }} />
                <span style={{ color: "#16A34A", fontWeight: 500, wordBreak: "break-word" }}>{c.to}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── WordPanel ─────────────────────────────────────────────────────────────────
function WordPanel({ token, synonymData, onApply, onDeepFetch, activePanel, setActivePanel, onFetchRephrase, rephraseLoading, rephraseOptions, onApplyRephrase, spikeLoading, onReportSpike }) {
  const rs = RISK[token.risk_level] || RISK.safe;

  return (
    <div style={{
      background: C.white,
      border: `1.5px solid ${C.blue300}`,
      borderRadius: 14,
      overflow: "hidden",
      boxShadow: `0 4px 20px rgba(37,99,235,0.10)`,
    }}>
      {/* Panel header */}
      <div style={{
        background: C.blue50,
        borderBottom: `1px solid ${C.rimLight}`,
        padding: "14px 20px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        flexWrap: "wrap", gap: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 13, color: C.inkFaint, fontWeight: 500 }}>Adapting</span>
          <span style={{
            fontSize: 16, fontWeight: 700, color: C.ink,
            background: C.white, border: `1px solid ${C.rimLight}`,
            borderRadius: 8, padding: "3px 12px",
            letterSpacing: "0.01em",
          }}>
            {token.value}
          </span>
          {token.risk_level && token.risk_level !== "safe" && (
            <span style={{
              background: rs.bg, color: rs.text,
              border: `1px solid ${rs.rim}`,
              borderRadius: 20, padding: "2px 10px",
              fontSize: 11, fontWeight: 600,
            }}>{rs.label}</span>
          )}

          {/* Spike flag button */}
          <button onClick={onReportSpike} disabled={spikeLoading}
            className="stamm-ghost"
            style={{ ...B.base, ...B.xs, color: "#D97706", borderColor: "#FDE68A", background: "#FFFBEB", opacity: spikeLoading ? 0.5 : 1 }}
            title="Flag as live stutter spike — engine adapts onset risk for this session"
          >
            {spikeLoading
              ? <Spinner size={11} />
              : <><i className="ti ti-bolt" style={{ fontSize: 11, marginRight: 4 }} />Flag spike</>}
          </button>
        </div>

        {/* Tab switcher */}
        <div style={{
          display: "flex",
          background: C.white, border: `1px solid ${C.rimLight}`,
          borderRadius: 9, padding: 3, gap: 2,
        }}>
          {[
            { key: "synonyms", icon: "ti-replace", label: "Alternatives", action: () => setActivePanel("synonyms") },
            { key: "rephrase", icon: "ti-rotate-2", label: "Rephrase", action: () => { setActivePanel("rephrase"); onFetchRephrase(); } },
          ].map(({ key, icon, label, action }) => (
            <button key={key} onClick={action} style={{
              ...B.base, ...B.xs,
              border: "none",
              background: activePanel === key ? C.blue600 : "transparent",
              color: activePanel === key ? "#fff" : C.inkFaint,
              borderRadius: 7, fontWeight: 500,
              boxShadow: activePanel === key ? `0 1px 4px rgba(37,99,235,0.3)` : "none",
            }}>
              <i className={`ti ${icon}`} style={{ fontSize: 12, marginRight: 5 }} />{label}
            </button>
          ))}
        </div>
      </div>

      {/* Panel body */}
      <div style={{ padding: "18px 20px" }}>
        {activePanel === "synonyms" && <SynonymsPanel synonymData={synonymData} onApply={onApply} onDeepFetch={onDeepFetch} />}
        {activePanel === "rephrase" && <RephrasePanel loading={rephraseLoading} options={rephraseOptions} onApply={onApplyRephrase} />}
      </div>
    </div>
  );
}

// ── SynonymsPanel ─────────────────────────────────────────────────────────────
function SynonymsPanel({ synonymData, onApply, onDeepFetch }) {
  const [customWord, setCustomWord] = useState("");
  const [deepDone,   setDeepDone]   = useState(false);

  if (!synonymData) return <div style={{ color: C.inkFaint, fontSize: 13 }}>Loading…</div>;
  if (synonymData.loading) return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, color: C.inkFaint, fontSize: 13 }}>
      <Spinner /> Finding fluency-safe alternatives…
    </div>
  );
  if (synonymData.error && !synonymData.synonyms?.length) return (
    <div style={{ color: "#DC2626", fontSize: 13, display: "flex", alignItems: "center", gap: 7 }}>
      <i className="ti ti-alert-circle" style={{ fontSize: 14 }} />
      Backend unavailable. Type a custom replacement below.
    </div>
  );

  return (
    <div>
      {/* Engine / confidence row */}
      {(synonymData.engine || synonymData.confidence != null) && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          {synonymData.engine && <EngineTag method={synonymData.engine} />}
          {synonymData.confidence != null && (
            <span style={{ fontSize: 11, color: C.inkGhost }}>
              Confidence: <ConfidenceBadge score={synonymData.confidence * 100} />
            </span>
          )}
          {synonymData.note && (
            <span style={{ fontSize: 11, color: C.inkGhost, fontStyle: "italic" }}>{synonymData.note}</span>
          )}
        </div>
      )}

      <SectionLabel>Fluency-safe alternatives</SectionLabel>

      {synonymData.synonyms?.length ? (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
          {synonymData.synonyms.map((syn, i) => (
            <button key={syn + i} onClick={() => onApply(syn)}
              className="stamm-ghost"
              style={{
                ...B.base,
                padding: "6px 16px", fontSize: 13,
                background: i === 0 ? C.blue600 : C.white,
                color:      i === 0 ? "#fff"    : C.inkMid,
                border:     i === 0 ? "none"    : `1px solid ${C.rimLight}`,
                boxShadow:  i === 0 ? `0 2px 8px rgba(37,99,235,0.30)` : "none",
                borderRadius: 9,
              }}
              title={i === 0 ? "Best semantic match" : "Alternative"}
            >
              {i === 0 && <i className="ti ti-star" style={{ fontSize: 11, marginRight: 6 }} />}
              {syn}
            </button>
          ))}
        </div>
      ) : (
        <p style={{ fontSize: 13, color: C.inkGhost, marginBottom: 14 }}>No pre-fetched alternatives for this word.</p>
      )}

      {/* Deep-fetch / Gemini re-rank */}
      {!deepDone && (
        <button onClick={() => { onDeepFetch(); setDeepDone(true); }}
          className="stamm-ghost"
          style={{ ...B.base, ...B.xs, marginBottom: 16, color: C.blue600, borderColor: C.rimMid }}>
          <i className="ti ti-sparkles" style={{ fontSize: 11, marginRight: 5 }} />Fetch more · Gemini re-rank
        </button>
      )}

      {/* Divider */}
      <div style={rule} />

      {/* Custom input */}
      <SectionLabel>Or type your own</SectionLabel>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={customWord} onChange={e => setCustomWord(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && customWord.trim()) { onApply(customWord.trim()); setCustomWord(""); } }}
          placeholder="Custom replacement word…"
          style={{
            flex: 1, border: `1px solid ${C.rimLight}`, borderRadius: 9,
            background: C.inputBg, color: C.ink,
            padding: "8px 12px", fontSize: 13, fontFamily: "inherit",
            transition: "border-color 0.15s, box-shadow 0.15s",
          }}
        />
        <button onClick={() => { if (customWord.trim()) { onApply(customWord.trim()); setCustomWord(""); } }}
          disabled={!customWord.trim()}
          className="stamm-ghost"
          style={{ ...B.base, ...B.sm, opacity: customWord.trim() ? 1 : 0.45 }}>
          Apply
        </button>
      </div>
    </div>
  );
}

// ── RephrasePanel ─────────────────────────────────────────────────────────────
function RephrasePanel({ loading, options, onApply }) {
  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, color: C.inkFaint, fontSize: 13 }}>
      <Spinner /> Generating fluency-adapted rephrases…
    </div>
  );
  if (!options) return (
    <p style={{ fontSize: 13, color: C.inkFaint }}>Click "Rephrase" to generate sentence alternatives.</p>
  );
  if (!options.length) return (
    <p style={{ fontSize: 13, color: C.inkFaint }}>No rephrasing options found. Try the Alternatives tab.</p>
  );

  return (
    <div>
      <SectionLabel>Choose a rephrasing — same meaning, easier to say</SectionLabel>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {options.map((opt, i) => (
          <button key={i} onClick={() => onApply(opt)}
            className="stamm-ghost"
            style={{
              ...B.base,
              textAlign: "left", padding: "12px 16px",
              fontSize: 14, lineHeight: 1.65, width: "100%",
              background:   i === 0 ? C.blue50  : C.white,
              color:        i === 0 ? C.blue700  : C.ink,
              border:       i === 0 ? `1.5px solid ${C.blue200}` : `1px solid ${C.rimLight}`,
              borderRadius: 10,
            }}>
            {i === 0 && <i className="ti ti-sparkles" style={{ fontSize: 13, marginRight: 7, color: C.blue500 }} />}
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}
