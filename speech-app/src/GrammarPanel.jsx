/**
 * GrammarPanel.jsx — StammAI GrammarGuard frontend component
 * ══════════════════════════════════════════════════════════════
 * Drop-in panel that plugs into SpeechAI_v3_blue.jsx.
 *
 * HOW TO INTEGRATE (3 changes to SpeechAI_v3_blue.jsx):
 *
 * 1. Import at the top:
 *      import GrammarPanel from "./GrammarPanel";
 *
 * 2. Add grammar state inside the SpeechAI root component:
 *      const [grammarReport,    setGrammarReport]    = useState(null);
 *      const [grammarLoading,   setGrammarLoading]   = useState(false);
 *      const [grammarAutoApply, setGrammarAutoApply] = useState(false);
 *
 *    Add the runGrammarCheck function:
 *      async function runGrammarCheck(modifiedText) {
 *        setGrammarLoading(true); setGrammarReport(null);
 *        try {
 *          const data = await apiFetch("/api/grammar-check", {
 *            original_text: rawText,
 *            modified_text: modifiedText || outputText,
 *          });
 *          setGrammarReport(data);
 *          if (data.corrected_text && data.corrected_text !== (modifiedText || outputText)) {
 *            // Auto-apply correction: re-run transform on corrected text
 *            if (grammarAutoApply) {
 *              await runTransform(data.corrected_text, blockProfile);
 *            }
 *          }
 *        } catch(e) { console.error("[StammAI] grammar-check failed:", e); }
 *        finally { setGrammarLoading(false); }
 *      }
 *
 * 3. Add the panel inside EditorPhase, after the semantic check card:
 *      <GrammarPanel
 *        report={grammarReport}
 *        loading={grammarLoading}
 *        autoApply={grammarAutoApply}
 *        onToggleAutoApply={() => setGrammarAutoApply(a => !a)}
 *        onCheck={() => runGrammarCheck(outputText)}
 *        onApplyCorrection={(corrected) => runTransform(corrected, blockProfile)}
 *        changed={changed}
 *        hasOutput={!!outputText}
 *      />
 *
 * That's it. The panel is completely self-contained and renders nothing
 * until the user clicks "Grammar check" or changed > 0 triggers auto-check.
 */

import { useState } from "react";

// ── Design tokens (same as SpeechAI_v3_blue) ─────────────────────────────────
const C = {
  white: "#FFFFFF", pageBg: "#EFF6FF", inputBg: "#F7FBFF",
  blue50: "#EFF6FF", blue100: "#DBEAFE", blue200: "#BFDBFE",
  blue300: "#93C5FD", blue500: "#3B82F6", blue600: "#2563EB", blue700: "#1D4ED8",
  ink: "#0F172A", inkMid: "#334155", inkFaint: "#64748B", inkGhost: "#94A3B8",
  rimLight: "#BFDBFE", rimMid: "#93C5FD",
};

const B = {
  base: { display:"inline-flex", alignItems:"center", cursor:"pointer", border:`1px solid ${C.rimLight}`, borderRadius:8, padding:"6px 14px", fontSize:13, fontWeight:500, background:C.white, color:C.inkMid, transition:"all .14s", fontFamily:"inherit" },
  primary: { background:C.blue600, color:"#fff", border:"none", boxShadow:"0 1px 4px rgba(37,99,235,0.35)" },
  ghost: { background:"transparent", color:C.blue600, border:`1px solid ${C.rimMid}` },
  sm: { padding:"4px 11px", fontSize:12, borderRadius:7 },
  xs: { padding:"3px 9px", fontSize:11, borderRadius:6 },
};

function SectionLabel({ children }) {
  return <div style={{ fontSize:10, fontWeight:700, color:C.inkGhost, textTransform:"uppercase", letterSpacing:".1em", marginBottom:8 }}>{children}</div>;
}

function ScoreBadge({ score }) {
  const color = score >= 85 ? "#16A34A" : score >= 65 ? "#D97706" : "#DC2626";
  const bg    = score >= 85 ? "#F0FDF4" : score >= 65 ? "#FFFBEB" : "#FEF2F2";
  const rim   = score >= 85 ? "#86EFAC" : score >= 65 ? "#FDE68A" : "#FCA5A5";
  return (
    <span style={{ background:bg, color, border:`1px solid ${rim}`, borderRadius:20, padding:"3px 12px", fontSize:13, fontWeight:700 }}>
      {score}/100
    </span>
  );
}

function TenseBadge({ tense }) {
  const map = {
    past:    { bg:"#FEF9C3", color:"#92400E" },
    present: { bg:C.blue100, color:C.blue700 },
    modal:   { bg:"#F5F3FF", color:"#5B21B6" },
    base:    { bg:"#F1F5F9", color:C.inkFaint },
    mixed:   { bg:"#FEE2E2", color:"#991B1B" },
    unknown: { bg:"#F1F5F9", color:C.inkGhost },
  };
  const s = map[tense] || map.unknown;
  return (
    <span style={{ background:s.bg, color:s.color, border:`1px solid ${s.color}22`, borderRadius:6, padding:"2px 9px", fontSize:11, fontWeight:600 }}>
      {tense}
    </span>
  );
}

function LayerRow({ icon, label, ok, detail }) {
  return (
    <div style={{ display:"flex", alignItems:"flex-start", gap:10, padding:"9px 0", borderBottom:`1px solid ${C.rimLight}` }}>
      <div style={{ width:22, height:22, borderRadius:6, display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0, marginTop:1, background: ok ? "#DCFCE7" : "#FEE2E2" }}>
        <i className={`ti ${ok ? "ti-check" : "ti-x"}`} style={{ fontSize:11, color: ok ? "#16A34A" : "#DC2626" }} />
      </div>
      <div style={{ flex:1 }}>
        <div style={{ fontSize:12, fontWeight:600, color:C.ink, marginBottom:detail ? 3 : 0 }}>{icon} {label}</div>
        {detail && <div style={{ fontSize:11, color:C.inkFaint, lineHeight:1.5 }}>{detail}</div>}
      </div>
    </div>
  );
}

function DiffRow({ entry, index }) {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:8, padding:"6px 10px", background: index % 2 === 0 ? C.blue50 : C.white, borderRadius:7, fontSize:13, marginBottom:2 }}>
      <span style={{ fontFamily:"monospace", background:"#FEE2E2", color:"#991B1B", padding:"1px 6px", borderRadius:4, textDecoration:"line-through", fontWeight:500 }}>{entry.original_word}</span>
      <i className="ti ti-arrow-right" style={{ fontSize:11, color:C.inkGhost }} />
      <span style={{ fontFamily:"monospace", background:"#DCFCE7", color:"#166534", padding:"1px 6px", borderRadius:4, fontWeight:500 }}>{entry.corrected_word}</span>
      <span style={{ marginLeft:"auto", fontSize:11, color:C.inkFaint, fontStyle:"italic" }}>{entry.reason}</span>
    </div>
  );
}

function FactViolationRow({ v }) {
  return (
    <div style={{ display:"flex", alignItems:"flex-start", gap:10, padding:"8px 12px", background:"#FEF2F2", border:"1px solid #FCA5A5", borderRadius:8, marginBottom:6 }}>
      <i className="ti ti-alert-circle" style={{ fontSize:14, color:"#DC2626", flexShrink:0, marginTop:1 }} />
      <div>
        <div style={{ fontSize:12, fontWeight:600, color:"#991B1B" }}>
          Fact anchor altered: <span style={{ fontFamily:"monospace" }}>"{v.anchor_text}"</span>
          <span style={{ marginLeft:6, fontSize:10, background:"#FEE2E2", border:"1px solid #FCA5A5", borderRadius:4, padding:"1px 6px" }}>{v.anchor_type}</span>
        </div>
        <div style={{ fontSize:11, color:"#7F1D1D", marginTop:2 }}>
          Was <span style={{ fontWeight:600 }}>"{v.original_form}"</span>
          {" → "}
          became <span style={{ fontWeight:600 }}>"{v.modified_form}"</span> in the modified text.
          This word is a real-world reference and must not be changed.
        </div>
      </div>
    </div>
  );
}

export default function GrammarPanel({ report, loading, autoApply, onToggleAutoApply, onCheck, onApplyCorrection, changed, hasOutput }) {
  const [expanded, setExpanded] = useState(true);

  const hasCorrected = report && report.corrected_text &&
    report.corrected_text !== report.modified_text;

  return (
    <div style={{ background:C.white, border:`1.5px solid ${C.rimLight}`, borderRadius:14, overflow:"hidden", boxShadow:"0 2px 12px rgba(37,99,235,0.07)", marginTop:14 }}>

      {/* ── Header ── */}
      <div style={{ background:C.blue50, borderBottom:`1px solid ${C.rimLight}`, padding:"13px 20px", display:"flex", alignItems:"center", justifyContent:"space-between", flexWrap:"wrap", gap:10 }}>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <div style={{ width:30, height:30, borderRadius:8, background:`linear-gradient(135deg, ${C.blue500}, ${C.blue700})`, display:"flex", alignItems:"center", justifyContent:"center", boxShadow:"0 1px 6px rgba(37,99,235,.3)" }}>
            <i className="ti ti-shield-check" style={{ fontSize:14, color:"#fff" }} />
          </div>
          <div>
            <div style={{ fontSize:14, fontWeight:700, color:C.ink }}>GrammarGuard</div>
            <div style={{ fontSize:11, color:C.inkFaint }}>5-layer grammar · tense · fact integrity checker</div>
          </div>
          {report && <ScoreBadge score={report.overall_score} />}
        </div>

        <div style={{ display:"flex", alignItems:"center", gap:8, flexWrap:"wrap" }}>
          {/* Auto-apply toggle */}
          <label style={{ display:"flex", alignItems:"center", gap:6, cursor:"pointer", fontSize:12, color:C.inkFaint, userSelect:"none" }}>
            <div
              onClick={onToggleAutoApply}
              style={{ width:32, height:18, borderRadius:9, border:`1px solid ${autoApply ? C.blue500 : C.rimLight}`, background: autoApply ? C.blue500 : C.white, position:"relative", cursor:"pointer", transition:"all .15s", flexShrink:0 }}
            >
              <div style={{ position:"absolute", top:2, left: autoApply ? 15 : 2, width:12, height:12, borderRadius:"50%", background: autoApply ? "#fff" : C.rimMid, transition:"left .15s" }} />
            </div>
            Auto-apply corrections
          </label>

          <button
            onClick={onCheck}
            disabled={loading || (!changed && !hasOutput)}
            style={{ ...B.base, ...B.sm, ...(!loading && (changed || hasOutput) ? {} : { opacity:.5 }), background: C.blue600, color:"#fff", border:"none" }}
          >
            {loading
              ? <><i className="ti ti-loader-2 stamm-spin" style={{ fontSize:13, marginRight:5 }} />Checking…</>
              : <><i className="ti ti-scan" style={{ fontSize:13, marginRight:5 }} />Grammar check</>}
          </button>

          <button onClick={() => setExpanded(e => !e)} style={{ ...B.base, ...B.xs, ...B.ghost }}>
            <i className={`ti ${expanded ? "ti-chevron-up" : "ti-chevron-down"}`} style={{ fontSize:12 }} />
          </button>
        </div>
      </div>

      {/* ── Body ── */}
      {expanded && (
        <div style={{ padding:"18px 20px" }}>
          {!report && !loading && (
            <div style={{ textAlign:"center", padding:"24px 0", color:C.inkGhost, fontSize:13 }}>
              <i className="ti ti-shield" style={{ fontSize:28, display:"block", marginBottom:8, opacity:.4 }} />
              Make word substitutions, then click <strong>Grammar check</strong> to verify grammar,
              tense, and fact integrity across your changes.
            </div>
          )}

          {loading && (
            <div style={{ display:"flex", alignItems:"center", gap:10, padding:"16px 0", color:C.inkFaint, fontSize:13 }}>
              <i className="ti ti-loader-2 stamm-spin" style={{ fontSize:16, color:C.blue500 }} />
              Running 5-layer grammar analysis…
            </div>
          )}

          {report && (
            <div>
              {/* ── Method + engine ── */}
              <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:16, fontSize:11, color:C.inkGhost }}>
                <i className="ti ti-cpu" style={{ fontSize:11 }} />
                <span>Engine: <span style={{ fontWeight:600, color:C.inkFaint }}>{report.method}</span></span>
                {report.gemini_triggered && (
                  <span style={{ background:"#FEF9C3", color:"#92400E", border:"1px solid #FDE68A", borderRadius:5, padding:"1px 7px", fontWeight:600 }}>
                    Gemini verified
                  </span>
                )}
              </div>

              {/* ── Layer-by-layer status ── */}
              <SectionLabel>Layer results</SectionLabel>
              <div style={{ marginBottom:16 }}>
                <LayerRow
                  icon="🔒" label="Fact anchors"
                  ok={report.facts_preserved}
                  detail={report.facts_preserved
                    ? "All named entities, numbers, and publications preserved."
                    : `${report.fact_violations.length} anchor(s) were altered — see violations below.`}
                />
                <LayerRow
                  icon="⏱" label="Tense consistency"
                  ok={report.tense_ok}
                  detail={
                    report.tense_ok
                      ? <span>Tense frame consistent: <TenseBadge tense={report.original_tense} /></span>
                      : <span>
                          Original: <TenseBadge tense={report.original_tense} />
                          {" → "}Modified: <TenseBadge tense={report.modified_tense} />
                          {" "}Correction available below.
                        </span>
                  }
                />
                <LayerRow
                  icon="📐" label="Subject-verb agreement"
                  ok={report.agreement_ok}
                  detail={report.agreement_ok
                    ? "No agreement errors detected."
                    : report.agreement_issues.join("; ")}
                />
                <LayerRow
                  icon="📋" label="LanguageTool grammar"
                  ok={report.lt_ok}
                  detail={report.lt_ok
                    ? (report.lt_issues.length === 0 ? "No grammar issues found." : "LanguageTool not installed — layer skipped.")
                    : report.lt_issues.slice(0,3).join("; ")}
                />
                <LayerRow
                  icon="🧠" label="Semantic similarity"
                  ok={report.embedding_ok}
                  detail={`Embedding cosine similarity: ${Math.round(report.embedding_score * 100)}% ${report.embedding_ok ? "— meaning well preserved." : "— semantic drift detected."}`}
                />
                {report.gemini_triggered && (
                  <LayerRow
                    icon="✨" label="Gemini deep check"
                    ok={report.gemini_score >= 80}
                    detail={report.gemini_verdict || `Score: ${report.gemini_score}/100`}
                  />
                )}
              </div>

              {/* ── Fact violations ── */}
              {report.fact_violations.length > 0 && (
                <>
                  <SectionLabel>Fact anchor violations</SectionLabel>
                  <div style={{ marginBottom:16 }}>
                    {report.fact_violations.map((v, i) => (
                      <FactViolationRow key={i} v={v} />
                    ))}
                  </div>
                </>
              )}

              {/* ── Gemini issues ── */}
              {report.gemini_issues.length > 0 && (
                <>
                  <SectionLabel>Gemini findings</SectionLabel>
                  <div style={{ background:"#FFFBEB", border:"1px solid #FDE68A", borderRadius:10, padding:"12px 14px", marginBottom:16 }}>
                    {report.gemini_issues.map((issue, i) => (
                      <div key={i} style={{ fontSize:13, color:"#92400E", marginBottom: i < report.gemini_issues.length-1 ? 4 : 0 }}>
                        <i className="ti ti-point" style={{ fontSize:10, marginRight:5 }} />{issue}
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* ── Corrected text + diff ── */}
              {hasCorrected && (
                <>
                  <SectionLabel>Suggested correction</SectionLabel>
                  <div style={{ background:C.blue50, border:`1.5px solid ${C.blue200}`, borderRadius:10, padding:"14px 16px", marginBottom:12, fontSize:15, lineHeight:1.8, color:C.ink }}>
                    {report.corrected_text}
                  </div>

                  {report.diff.length > 0 && (
                    <div style={{ marginBottom:14 }}>
                      <SectionLabel>Corrections applied</SectionLabel>
                      {report.diff.map((d, i) => (
                        <DiffRow key={i} entry={d} index={i} />
                      ))}
                    </div>
                  )}

                  <div style={{ display:"flex", gap:8 }}>
                    <button
                      onClick={() => onApplyCorrection(report.corrected_text)}
                      style={{ ...B.base, ...B.primary, borderRadius:9, padding:"8px 20px", fontSize:13 }}
                    >
                      <i className="ti ti-circle-check" style={{ fontSize:14, marginRight:6 }} />
                      Apply correction
                    </button>
                    <button style={{ ...B.base, ...B.ghost, ...B.sm, fontSize:13 }}>
                      <i className="ti ti-x" style={{ fontSize:12, marginRight:5 }} />
                      Dismiss
                    </button>
                  </div>
                </>
              )}

              {!hasCorrected && report.overall_score >= 85 && (
                <div style={{ background:"#F0FDF4", border:"1px solid #86EFAC", borderRadius:10, padding:"12px 16px", display:"flex", alignItems:"center", gap:10 }}>
                  <i className="ti ti-circle-check" style={{ fontSize:18, color:"#16A34A" }} />
                  <div>
                    <div style={{ fontSize:13, fontWeight:600, color:"#166534" }}>All checks passed</div>
                    <div style={{ fontSize:12, color:"#15803D" }}>Grammar, tense, fact integrity, and semantic similarity are all within acceptable bounds.</div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
