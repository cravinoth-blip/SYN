"use client";

import { useState, useRef } from "react";

/* ═══════════════════════════════════════════════════════════════
   TYPES
   ═══════════════════════════════════════════════════════════════ */
interface PainPoint { description: string; stakeholder: string; severity: "critical" | "high" | "moderate" | "low"; }
interface EvidenceClaim { claim: string; source: string; source_type: string; }
interface Moment { title: string; description: string; emotional_arc: "rising" | "falling" | "stable" | "volatile"; }
interface Phase {
  phase_id: string; headline: string; feelings: string[];
  moment: Moment; mindset: string; pain_points: PainPoint[];
  evidence_claims: EvidenceClaim[]; unmet_needs: string[];
  confidence: "HIGH" | "MEDIUM" | "LOW" | "UNSUPPORTED";
  verification_notes: string; gaps: string[];
}
export interface JourneyData { disease: string; summary: string; phases: Phase[]; assumptions: string[]; }

/* ═══════════════════════════════════════════════════════════════
   CONSTANTS
   ═══════════════════════════════════════════════════════════════ */
const PHASE_COLORS: Record<string, { bg: string; light: string; text: string; mid: string }> = {
  presentation: { bg: "#4CAF50", light: "#E8F5E9", text: "#1B5E20", mid: "#81C784" },
  diagnosis:    { bg: "#FFC107", light: "#FFF8E1", text: "#F57F17", mid: "#FFD54F" },
  treatment:    { bg: "#FF9800", light: "#FFF3E0", text: "#E65100", mid: "#FFB74D" },
  re_diagnosis: { bg: "#F44336", light: "#FFEBEE", text: "#B71C1C", mid: "#E57373" },
  tx_adaptation:{ bg: "#D32F2F", light: "#FFCDD2", text: "#B71C1C", mid: "#EF5350" },
  living_with:  { bg: "#B71C1C", light: "#FFCDD2", text: "#7F0000", mid: "#E53935" },
};
const PHASE_LABELS: Record<string, string> = {
  presentation: "Presentation", diagnosis: "Diagnosis", treatment: "Treatment",
  re_diagnosis: "Re-Diagnosis", tx_adaptation: "Tx Adaptation", living_with: "Living With",
};
const CONFIDENCE_BADGE: Record<string, { color: string; bg: string; label: string }> = {
  HIGH: { color: "#1B5E20", bg: "#C8E6C9", label: "High" },
  MEDIUM: { color: "#E65100", bg: "#FFE0B2", label: "Medium" },
  LOW: { color: "#B71C1C", bg: "#FFCDD2", label: "Low" },
  UNSUPPORTED: { color: "#4A148C", bg: "#E1BEE7", label: "Unsupported" },
};
const SEVERITY_DOT: Record<string, string> = { critical: "#D32F2F", high: "#FF9800", moderate: "#FFC107", low: "#4CAF50" };
const SECTION_KEYS = ["headline", "feelings", "moment", "mindset", "pain_points", "evidence_claims", "unmet_needs"];
const SECTION_LABELS: Record<string, string> = {
  headline: "Headline", feelings: "Feelings", moment: "Patient moment",
  mindset: "Mindset", pain_points: "Pain points", evidence_claims: "Evidence claims", unmet_needs: "Unmet needs",
};

/* ═══════════════════════════════════════════════════════════════
   LLM REGENERATION (via /api/refine — server-side proxy)
   ═══════════════════════════════════════════════════════════════ */
async function regenerateSection(
  disease: string,
  phase: Phase,
  sectionKey: string,
  feedback: { correct: string; incorrect: string; instructions: string },
  fullJourney: JourneyData
) {
  try {
    const resp = await fetch("/api/refine", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ disease, phase, sectionKey, feedback, fullJourney }),
    });
    if (!resp.ok) throw new Error(await resp.text());
    return await resp.json();
  } catch (err: unknown) {
    return { error: err instanceof Error ? err.message : String(err) };
  }
}

/* ═══════════════════════════════════════════════════════════════
   SMALL UI COMPONENTS
   ═══════════════════════════════════════════════════════════════ */
const Badge = ({ bg, color, children, style: sx }: { bg: string; color: string; children: React.ReactNode; style?: React.CSSProperties }) => (
  <span style={{ display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 10, fontWeight: 600, background: bg, color, letterSpacing: "0.03em", ...sx }}>{children}</span>
);

const ConfBadge = ({ level }: { level: string }) => {
  const c = CONFIDENCE_BADGE[level] || CONFIDENCE_BADGE.MEDIUM;
  return <Badge bg={c.bg} color={c.color}>{c.label}</Badge>;
};

const Pill = ({ text, color }: { text: string; color: string }) => (
  <span style={{ display: "inline-block", padding: "3px 10px", borderRadius: 12, border: `1.5px solid ${color}`, fontSize: 11, fontWeight: 500, color, margin: "2px 3px", whiteSpace: "nowrap" }}>{text}</span>
);

const SrcBadge = ({ type }: { type: string }) => {
  const m: Record<string, [string, string]> = { pubmed: ["#E3F2FD", "#1565C0"], spine: ["#E3F2FD", "#1565C0"], web: ["#F3E5F5", "#6A1B9A"], fda_label: ["#FFF3E0", "#E65100"], clinical_trial: ["#E8F5E9", "#2E7D32"], ci_supplement: ["#FFF8E1", "#F57F17"], model_inference: ["#F5F5F5", "#616161"] };
  const label = type === "pubmed" ? "PubMed" : type?.replace("_", " ");
  const [bg, c] = m[type] || m.model_inference;
  return <Badge bg={bg} color={c} style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</Badge>;
};

const Spinner = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" style={{ animation: "spin 1s linear infinite" }}>
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    <circle cx="8" cy="8" r="6" stroke="#fff" strokeWidth="2" fill="none" strokeDasharray="28" strokeDashoffset="8" strokeLinecap="round"/>
  </svg>
);

const PhaseArrow = ({ color, label, isFirst, hasChanges, onClick }: { color: string; label: string; isFirst: boolean; hasChanges: boolean; onClick: () => void }) => (
  <div style={{ display: "flex", alignItems: "center", flex: 1, minWidth: 0, cursor: "pointer", position: "relative" }} onClick={onClick}>
    {hasChanges && <div style={{ position: "absolute", top: -4, right: 8, width: 10, height: 10, borderRadius: "50%", background: "#0891B2", border: "2px solid #fff", zIndex: 2 }} />}
    <div style={{
      background: color, color: "#fff", padding: "10px 20px 10px 28px", fontWeight: 600, fontSize: 12,
      letterSpacing: "0.05em", textTransform: "uppercase", lineHeight: 1.3, whiteSpace: "nowrap", textAlign: "center", width: "100%",
      clipPath: isFirst ? "polygon(0 0,calc(100% - 14px) 0,100% 50%,calc(100% - 14px) 100%,0 100%)" : "polygon(0 0,calc(100% - 14px) 0,100% 50%,calc(100% - 14px) 100%,0 100%,14px 50%)",
    }}>{label}</div>
  </div>
);

const RefineBtn = ({ onClick, small, label }: { onClick: () => void; small?: boolean; label?: string }) => (
  <button onClick={(e) => { e.stopPropagation(); onClick(); }} style={{
    background: "none", border: "1.5px solid #0891B2", color: "#0891B2", borderRadius: 6,
    padding: small ? "3px 10px" : "5px 14px", fontSize: small ? 10 : 11, fontWeight: 600, cursor: "pointer",
    display: "inline-flex", alignItems: "center", gap: 4, transition: "all 0.15s", fontFamily: "inherit",
  }}
    onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "#0891B2"; (e.currentTarget as HTMLButtonElement).style.color = "#fff"; }}
    onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "none"; (e.currentTarget as HTMLButtonElement).style.color = "#0891B2"; }}>
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M13.5 2.5a2.12 2.12 0 00-3 0L3.7 9.3a1 1 0 00-.26.44l-.9 3.2a.5.5 0 00.62.62l3.2-.9a1 1 0 00.44-.26l6.8-6.8a2.12 2.12 0 000-3z" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
    {label || "Refine"}
  </button>
);

/* ═══════════════════════════════════════════════════════════════
   EMOTIONAL ARC SVG
   ═══════════════════════════════════════════════════════════════ */
function EmotionalArcSVG({ phases }: { phases: Phase[] }) {
  const w = 900, h = 90;
  if (!phases || phases.length === 0) return null;
  const arcV: Record<string, number> = { rising: 0.3, falling: 0.75, stable: 0.5, volatile: 0.5 };
  const pw = w / phases.length;
  const pts = phases.map((p, i) => ({ x: pw * i + pw / 2, y: h * 0.1 + (h * 0.8) * (arcV[p.moment?.emotional_arc] || 0.5) }));
  let d = `M ${pts[0].x} ${pts[0].y}`;
  for (let i = 1; i < pts.length; i++) { const p = pts[i - 1], c = pts[i]; d += ` C ${p.x + (c.x - p.x) * 0.4} ${p.y}, ${p.x + (c.x - p.x) * 0.6} ${c.y}, ${c.x} ${c.y}`; }
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ width: "100%", height: 70 }}>
      <defs><linearGradient id="ag" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#4CAF50"/><stop offset="50%" stopColor="#FF9800"/><stop offset="100%" stopColor="#B71C1C"/></linearGradient></defs>
      <path d={d} fill="none" stroke="url(#ag)" strokeWidth="2.5" strokeLinecap="round"/>
      {pts.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r="4" fill={PHASE_COLORS[phases[i].phase_id]?.bg || "#999"} stroke="#fff" strokeWidth="1.5"/>)}
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════════════
   REFINE MODAL
   ═══════════════════════════════════════════════════════════════ */
function RefineModal({ phase, sectionKey, currentContent, onClose, onRegenerate, isLoading }: {
  phase: Phase; sectionKey: string; currentContent: unknown;
  onClose: () => void; onRegenerate: (f: { correct: string; incorrect: string; instructions: string }) => void; isLoading: boolean;
}) {
  const [correct, setCorrect] = useState("");
  const [incorrect, setIncorrect] = useState("");
  const [instructions, setInstructions] = useState("");
  const colors = PHASE_COLORS[phase.phase_id] || PHASE_COLORS.presentation;

  const renderCurrentContent = () => {
    const v = currentContent;
    if (typeof v === "string") return <div style={{ fontSize: 12, color: "#444", fontStyle: "italic", lineHeight: 1.5 }}>{v}</div>;
    if (Array.isArray(v)) {
      if (typeof v[0] === "string") return (v as string[]).map((s, i) => <div key={i} style={{ fontSize: 12, color: "#444", marginBottom: 3 }}>• {s}</div>);
      return (v as Record<string, string>[]).map((item, i) => <div key={i} style={{ fontSize: 11, color: "#555", marginBottom: 6, padding: "6px 8px", background: "#F9F9F9", borderRadius: 4 }}>{item.claim || item.description || JSON.stringify(item)}{item.source && <span style={{ color: "#999", marginLeft: 6 }}>— {item.source}</span>}</div>);
    }
    if (v && typeof v === "object") { const o = v as Record<string, string>; return <div style={{ fontSize: 12, color: "#444" }}><strong>{o.title}</strong><br/>{o.description}</div>; }
    return <div style={{ fontSize: 12, color: "#888" }}>{JSON.stringify(v)}</div>;
  };

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 2000, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.45)" }} onClick={onClose}/>
      <div style={{ position: "relative", width: 580, maxHeight: "85vh", background: "#fff", borderRadius: 12, boxShadow: "0 20px 60px rgba(0,0,0,0.2)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <div style={{ background: colors.bg, padding: "18px 24px", color: "#fff", flexShrink: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", opacity: 0.8, letterSpacing: "0.1em" }}>Refine section</div>
              <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2 }}>{PHASE_LABELS[phase.phase_id]} — {SECTION_LABELS[sectionKey]}</div>
            </div>
            <button onClick={onClose} style={{ background: "rgba(255,255,255,0.2)", border: "none", color: "#fff", width: 32, height: 32, borderRadius: "50%", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="white" strokeWidth="1.5" strokeLinecap="round"/></svg>
            </button>
          </div>
        </div>
        <div style={{ padding: "20px 24px", overflowY: "auto", flex: 1 }}>
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: "block", fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "#999", marginBottom: 6 }}>Current content</label>
            <div style={{ background: "#F8FAFC", borderRadius: 8, padding: 14, border: "1px solid #E2E8F0", maxHeight: 140, overflowY: "auto" }}>{renderCurrentContent()}</div>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, fontWeight: 700, color: "#2E7D32", marginBottom: 6 }}>
              <svg width="14" height="14" viewBox="0 0 16 16"><path d="M13.5 4.5l-7 7L3 8" stroke="#2E7D32" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/></svg>
              What is correct? Keep these elements.
            </label>
            <textarea value={correct} onChange={(e) => setCorrect(e.target.value)} placeholder='e.g. "The 6.3 year diagnosis delay stat is accurate."' style={{ width: "100%", minHeight: 70, padding: 12, borderRadius: 8, border: "1.5px solid #C8E6C9", fontSize: 12, fontFamily: "inherit", resize: "vertical", lineHeight: 1.5, boxSizing: "border-box", outline: "none" }} onFocus={(e) => (e.target.style.borderColor = "#4CAF50")} onBlur={(e) => (e.target.style.borderColor = "#C8E6C9")}/>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, fontWeight: 700, color: "#C62828", marginBottom: 6 }}>
              <svg width="14" height="14" viewBox="0 0 16 16"><path d="M4 4l8 8M12 4l-8 8" stroke="#C62828" strokeWidth="2" strokeLinecap="round" fill="none"/></svg>
              What is incorrect? Fix or remove these.
            </label>
            <textarea value={incorrect} onChange={(e) => setIncorrect(e.target.value)} placeholder='e.g. "The psychosomatic stat seems too high."' style={{ width: "100%", minHeight: 70, padding: 12, borderRadius: 8, border: "1.5px solid #FFCDD2", fontSize: 12, fontFamily: "inherit", resize: "vertical", lineHeight: 1.5, boxSizing: "border-box", outline: "none" }} onFocus={(e) => (e.target.style.borderColor = "#EF5350")} onBlur={(e) => (e.target.style.borderColor = "#FFCDD2")}/>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, fontWeight: 700, color: "#5C6BC0", marginBottom: 6 }}>
              <svg width="14" height="14" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" stroke="#5C6BC0" strokeWidth="1.5" fill="none"/><path d="M8 5v3M8 10v.5" stroke="#5C6BC0" strokeWidth="1.5" strokeLinecap="round"/></svg>
              Additional instructions (optional)
            </label>
            <textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} placeholder='e.g. "Focus more on emotional impact. Add UK data."' style={{ width: "100%", minHeight: 55, padding: 12, borderRadius: 8, border: "1.5px solid #C5CAE9", fontSize: 12, fontFamily: "inherit", resize: "vertical", lineHeight: 1.5, boxSizing: "border-box", outline: "none" }} onFocus={(e) => (e.target.style.borderColor = "#5C6BC0")} onBlur={(e) => (e.target.style.borderColor = "#C5CAE9")}/>
          </div>
        </div>
        <div style={{ padding: "14px 24px", borderTop: "1px solid #E2F4FA", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0, background: "#F8FAFC" }}>
          <button onClick={onClose} style={{ background: "none", border: "1px solid #E2E8F0", color: "#64748B", borderRadius: 8, padding: "8px 20px", fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>Cancel</button>
          <button onClick={() => onRegenerate({ correct, incorrect, instructions })} disabled={isLoading || (!correct && !incorrect && !instructions)} style={{
            background: isLoading ? "#67C2D8" : (!correct && !incorrect && !instructions) ? "#CBD5E1" : "#059669",
            border: "none", color: "#fff", borderRadius: 8, padding: "8px 24px", fontSize: 12, fontWeight: 700,
            cursor: isLoading ? "wait" : "pointer", display: "flex", alignItems: "center", gap: 8, fontFamily: "inherit",
            opacity: (!correct && !incorrect && !instructions) ? 0.6 : 1,
          }}>
            {isLoading ? <><Spinner /> Regenerating...</> : <>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 8a6 6 0 0111.5-2.3M14 8A6 6 0 012.5 10.3" stroke="#fff" strokeWidth="1.5" strokeLinecap="round"/><path d="M13.5 2v3.7h-3.7M2.5 14v-3.7h3.7" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
              Regenerate section
            </>}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   CHANGES PANEL
   ═══════════════════════════════════════════════════════════════ */
function ChangesPanel({ change, onAccept, onReject, onClose }: {
  change: { phaseId: string; sectionKey: string; oldValue: unknown; newValue: unknown; summary: string; confidence: string; } | null;
  onAccept: () => void; onReject: () => void; onClose: () => void;
}) {
  if (!change) return null;
  const colors = PHASE_COLORS[change.phaseId] || PHASE_COLORS.presentation;
  const renderVal = (v: unknown) => {
    if (typeof v === "string") return <span style={{ fontSize: 12 }}>{v}</span>;
    if (Array.isArray(v)) return (v as unknown[]).map((x, i) => <div key={i} style={{ fontSize: 11, marginBottom: 2 }}>• {typeof x === "string" ? x : ((x as Record<string, string>).claim || (x as Record<string, string>).description || JSON.stringify(x))}</div>);
    if (v && typeof v === "object") { const o = v as Record<string, string>; return <div style={{ fontSize: 12 }}><strong>{o.title}</strong> — {o.description}</div>; }
    return <span style={{ fontSize: 12 }}>{JSON.stringify(v)}</span>;
  };
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 2000, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.4)" }} onClick={onClose}/>
      <div style={{ position: "relative", width: 620, maxHeight: "80vh", background: "#fff", borderRadius: 12, boxShadow: "0 20px 60px rgba(0,0,0,0.2)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <div style={{ background: "#0891B2", padding: "16px 24px", color: "#fff" }}>
          <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", opacity: 0.8 }}>Review changes</div>
          <div style={{ fontSize: 16, fontWeight: 700, marginTop: 2 }}>{PHASE_LABELS[change.phaseId]} — {SECTION_LABELS[change.sectionKey]}</div>
        </div>
        <div style={{ padding: "20px 24px", overflowY: "auto", flex: 1 }}>
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "#C62828", marginBottom: 6, letterSpacing: "0.08em" }}>Before</div>
            <div style={{ background: "#FFF5F5", border: "1px solid #FFCDD2", borderRadius: 8, padding: 14 }}>{renderVal(change.oldValue)}</div>
          </div>
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "#2E7D32", marginBottom: 6, letterSpacing: "0.08em" }}>After</div>
            <div style={{ background: "#F1F8E9", border: "1px solid #C8E6C9", borderRadius: 8, padding: 14 }}>{renderVal(change.newValue)}</div>
          </div>
          {change.summary && (
            <div style={{ background: "#F8FAFC", borderRadius: 8, padding: 14, marginBottom: 16, border: "1px solid #E2E8F0" }}>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "#777", marginBottom: 4, letterSpacing: "0.08em" }}>Change summary</div>
              <div style={{ fontSize: 12, color: "#444", lineHeight: 1.5 }}>{change.summary}</div>
            </div>
          )}
          {change.confidence && <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}><span style={{ fontSize: 11, color: "#777" }}>Updated confidence:</span><ConfBadge level={change.confidence}/></div>}
        </div>
        <div style={{ padding: "14px 24px", borderTop: "1px solid #E2F4FA", display: "flex", justifyContent: "flex-end", gap: 10, flexShrink: 0, background: "#F8FAFC" }}>
          <button onClick={onReject} style={{ background: "none", border: "1px solid #FECACA", color: "#B91C1C", borderRadius: 8, padding: "8px 20px", fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>Reject</button>
          <button onClick={onAccept} style={{ background: "#059669", border: "none", color: "#fff", borderRadius: 8, padding: "8px 24px", fontSize: 12, fontWeight: 700, cursor: "pointer", fontFamily: "inherit" }}>Accept changes</button>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   REVISION HISTORY SIDEBAR
   ═══════════════════════════════════════════════════════════════ */
interface HistoryEntry { phaseId: string; sectionKey: string; oldValue?: unknown; newValue?: unknown; summary: string; confidence?: string; status: string; timestamp: number; }

function RevisionHistory({ history, onRevert, onClose }: { history: HistoryEntry[]; onRevert: (i: number) => void; onClose: () => void }) {
  return (
    <div style={{ position: "fixed", top: 0, right: 0, bottom: 0, width: 380, background: "#fff", boxShadow: "-4px 0 24px rgba(0,0,0,0.12)", zIndex: 1500, display: "flex", flexDirection: "column", animation: "slideIn 0.2s ease-out" }}>
      <style>{`@keyframes slideIn { from { transform:translateX(100%); } to { transform:translateX(0); } }`}</style>
      <div style={{ padding: "18px 24px", borderBottom: "1px solid #E2F4FA", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: "#0C4A6E" }}>Revision history</div>
          <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 2 }}>{history.length} revision{history.length !== 1 ? "s" : ""}</div>
        </div>
        <button onClick={onClose} style={{ background: "#F0F9FF", border: "1px solid #E2F4FA", width: 32, height: 32, borderRadius: "50%", cursor: "pointer", color: "#0891B2", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
        </button>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: "12px 24px" }}>
        {history.length === 0 && <div style={{ padding: 24, textAlign: "center", color: "#94A3B8", fontSize: 13 }}>No revisions yet.</div>}
        {history.map((h, i) => (
          <div key={i} style={{ padding: 14, border: "1px solid #E2F4FA", borderRadius: 8, marginBottom: 10, background: h.status === "accepted" ? "#F0FDF4" : h.status === "rejected" ? "#FFF1F2" : "#F0F9FF" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Badge bg={PHASE_COLORS[h.phaseId]?.bg || "#999"} color="#fff">{PHASE_LABELS[h.phaseId]}</Badge>
                <span style={{ fontSize: 10, color: "#999" }}>{SECTION_LABELS[h.sectionKey]}</span>
              </div>
              <Badge bg={h.status === "accepted" ? "#C8E6C9" : h.status === "rejected" ? "#FFCDD2" : "#E0E0E0"} color={h.status === "accepted" ? "#2E7D32" : h.status === "rejected" ? "#C62828" : "#666"} style={{ fontSize: 9 }}>{h.status}</Badge>
            </div>
            <div style={{ fontSize: 11, color: "#555", lineHeight: 1.4, marginBottom: 8 }}>{h.summary}</div>
            <div style={{ display: "flex", gap: 6, alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: 9, color: "#BBB" }}>{new Date(h.timestamp).toLocaleTimeString()}</span>
              {h.status === "accepted" && <button onClick={() => onRevert(i)} style={{ background: "none", border: "1px solid #FFCDD2", color: "#C62828", borderRadius: 4, padding: "2px 8px", fontSize: 10, fontWeight: 600, cursor: "pointer" }}>Revert</button>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   DETAIL PANEL
   ═══════════════════════════════════════════════════════════════ */
function DetailPanel({ phase, onClose, onRefine, changedSections }: {
  phase: Phase; onClose: () => void;
  onRefine: (phase: Phase, sectionKey: string) => void; changedSections: Set<string>;
}) {
  const colors = PHASE_COLORS[phase.phase_id] || PHASE_COLORS.presentation;
  const isChanged = (key: string) => changedSections?.has(`${phase.phase_id}:${key}`);

  const Section = ({ sKey, children }: { sKey: string; children: React.ReactNode }) => (
    <div style={{ marginBottom: 20, position: "relative", background: isChanged(sKey) ? "#F0F9FF" : "transparent", borderRadius: 8, padding: isChanged(sKey) ? "10px 12px" : 0, border: isChanged(sKey) ? "1px solid #BAE6FD" : "none", transition: "all 0.3s" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "#64748B" }}>{SECTION_LABELS[sKey]}</span>
          {isChanged(sKey) && <Badge bg="#E0F2FE" color="#0369A1" style={{ fontSize: 8 }}>Updated</Badge>}
        </div>
        <RefineBtn small onClick={() => onRefine(phase, sKey)} />
      </div>
      {children}
    </div>
  );

  return (
    <div style={{ position: "fixed", top: 0, right: 0, bottom: 0, width: 440, background: "#fff", boxShadow: "-4px 0 24px rgba(0,0,0,0.12)", zIndex: 1000, overflowY: "auto", animation: "slideIn 0.2s ease-out" }}>
      <div style={{ background: colors.bg, padding: "22px 24px", color: "#fff" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", opacity: 0.85, letterSpacing: "0.08em" }}>{PHASE_LABELS[phase.phase_id]}</div>
            <div style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}>{phase.headline}</div>
          </div>
          <button onClick={onClose} style={{ background: "rgba(255,255,255,0.2)", border: "none", color: "#fff", width: 32, height: 32, borderRadius: "50%", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="white" strokeWidth="1.5" strokeLinecap="round"/></svg>
          </button>
        </div>
        <div style={{ marginTop: 8, display: "flex", gap: 8 }}><ConfBadge level={phase.confidence}/></div>
      </div>
      <div style={{ padding: "20px 24px" }}>
        <Section sKey="headline"><div style={{ fontSize: 16, fontWeight: 700, color: "#333" }}>{phase.headline}</div></Section>
        <Section sKey="feelings"><div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>{phase.feelings.map((f) => <Pill key={f} text={f} color={colors.text}/>)}</div></Section>
        <Section sKey="moment">
          <div style={{ background: colors.light, borderRadius: 8, padding: 14, borderLeft: `3px solid ${colors.bg}` }}>
            <div style={{ fontWeight: 600, fontSize: 14, color: "#333", marginBottom: 4 }}>{phase.moment.title}</div>
            <div style={{ fontSize: 12, color: "#555", lineHeight: 1.5 }}>{phase.moment.description}</div>
          </div>
        </Section>
        <Section sKey="mindset"><div style={{ fontStyle: "italic", fontSize: 13, color: "#444", lineHeight: 1.6, borderLeft: `2px solid ${colors.mid}`, paddingLeft: 12 }}>{phase.mindset}</div></Section>
        <Section sKey="pain_points">
          {phase.pain_points.map((pp, j) => (
            <div key={j} style={{ display: "flex", alignItems: "flex-start", gap: 6, marginBottom: 6 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: SEVERITY_DOT[pp.severity] || "#999", marginTop: 4, flexShrink: 0 }}/>
              <div style={{ fontSize: 11, lineHeight: 1.4 }}><span style={{ color: "#333" }}>{pp.description}</span>{pp.stakeholder && <Badge bg="#F5F5F5" color="#777" style={{ marginLeft: 6, fontSize: 9, textTransform: "uppercase" }}>{pp.stakeholder}</Badge>}</div>
            </div>
          ))}
        </Section>
        <Section sKey="evidence_claims">
          {phase.evidence_claims?.map((c, i) => (
            <div key={i} style={{ marginBottom: 8, fontSize: 12, lineHeight: 1.5 }}>
              <div style={{ color: "#333" }}>{c.claim}</div>
              <div style={{ marginTop: 2 }}><SrcBadge type={c.source_type}/><span style={{ marginLeft: 6, fontSize: 11, color: "#888" }}>{c.source}</span></div>
            </div>
          ))}
        </Section>
        <Section sKey="unmet_needs">
          {phase.unmet_needs?.map((n, i) => (
            <div key={i} style={{ fontSize: 12, color: "#334155", marginBottom: 5, paddingLeft: 14, position: "relative", lineHeight: 1.5 }}>
              <svg width="8" height="8" viewBox="0 0 8 8" style={{ position: "absolute", left: 0, top: 4 }} fill={colors.bg}><polygon points="0,0 8,4 0,8"/></svg>
              {n}
            </div>
          ))}
        </Section>
        {phase.gaps?.length > 0 && (
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "#B91C1C", marginBottom: 6 }}>Evidence gaps</div>
            {phase.gaps.map((g, i) => (
              <div key={i} style={{ fontSize: 12, color: "#B91C1C", marginBottom: 5, display: "flex", alignItems: "flex-start", gap: 6, lineHeight: 1.5 }}>
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0, marginTop: 1 }}><path d="M8 2L14.9 14H1.1L8 2z" stroke="#B91C1C" strokeWidth="1.4" strokeLinejoin="round"/><path d="M8 6v3M8 11v.5" stroke="#B91C1C" strokeWidth="1.4" strokeLinecap="round"/></svg>
                {g}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   GRID ROW + LEGEND
   ═══════════════════════════════════════════════════════════════ */
function GridRow({ label, color, phases, changedSections, sectionKey, onClickPhase, renderCell }: {
  label: string; color: string; phases: Phase[]; changedSections: Set<string>;
  sectionKey: string; onClickPhase: (p: Phase) => void; renderCell: (p: Phase) => React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", marginTop: 8, minWidth: 800 }}>
      <RowLabel label={label} color={color}/>
      <div style={{ display: "flex", flex: 1, background: "#fff", border: "1px solid #E2F4FA", borderRadius: "0 6px 6px 0" }}>
        {phases.map((p, i) => {
          const changed = changedSections.has(`${p.phase_id}:${sectionKey}`);
          return (
            <div key={p.phase_id} style={{ flex: 1, padding: "10px 8px", borderRight: i < phases.length - 1 ? "1px solid #F1F5F9" : "none", cursor: "pointer", background: changed ? "#E0F2FE" : "transparent", transition: "background 0.3s", position: "relative" }} onClick={() => onClickPhase(p)}>
              {changed && <div style={{ position: "absolute", top: 4, right: 4, width: 6, height: 6, borderRadius: "50%", background: "#0891B2" }}/>}
              {renderCell(p)}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const RowLabel = ({ label, color }: { label: string; color: string }) => (
  <div style={{ writingMode: "vertical-rl", textOrientation: "mixed", transform: "rotate(180deg)", background: color || "#455A64", color: "#fff", padding: "12px 6px", fontWeight: 700, fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", borderRadius: "6px 0 0 6px", display: "flex", alignItems: "center", justifyContent: "center", minHeight: 70, width: 30 }}>{label}</div>
);

function LegendBox({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ flex: 1, minWidth: 160 }}>
      <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "#999", marginBottom: 6 }}>{title}</div>
      <div style={{ background: "#fff", border: "1px solid #E2F4FA", borderRadius: 8, padding: 12 }}>{children}</div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════════════════ */
export default function PatientJourneyMap({ initialData }: { initialData: JourneyData }) {
  const [data, setData] = useState<JourneyData>(initialData);
  const [selectedPhase, setSelectedPhase] = useState<Phase | null>(null);
  const [refineTarget, setRefineTarget] = useState<{ phase: Phase; sectionKey: string } | null>(null);
  const [pendingChange, setPendingChange] = useState<{ phaseId: string; sectionKey: string; oldValue: unknown; newValue: unknown; summary: string; confidence: string; verification: string; feedback: object } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [changedSections, setChangedSections] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<{ msg: string; type: string } | null>(null);
  const exportRef = useRef<HTMLDivElement>(null);

  const showToast = (msg: string, type = "success") => { setToast({ msg, type }); setTimeout(() => setToast(null), 3000); };

  const exportPDF = async () => {
    if (!exportRef.current || isExporting) return;
    setIsExporting(true);
    showToast("Preparing PDF — please wait…", "info");
    try {
      const { default: html2canvas } = await import("html2canvas");
      const { jsPDF } = await import("jspdf");

      const el = exportRef.current;

      // Expand all overflow-x:auto children so full grid width is captured
      const expanded: Array<{ node: HTMLElement; prevOverflow: string; prevWidth: string }> = [];
      el.querySelectorAll<HTMLElement>("*").forEach((child) => {
        const cs = window.getComputedStyle(child);
        if (cs.overflowX === "auto" || cs.overflowX === "scroll") {
          expanded.push({ node: child, prevOverflow: child.style.overflowX, prevWidth: child.style.width });
          child.style.overflowX = "visible";
          child.style.width = child.scrollWidth + "px";
        }
      });

      const canvas = await html2canvas(el, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: "#F0F9FF",
        width: el.scrollWidth,
        windowWidth: el.scrollWidth,
      });

      // Restore original styles
      expanded.forEach(({ node, prevOverflow, prevWidth }) => {
        node.style.overflowX = prevOverflow;
        node.style.width = prevWidth;
      });

      // Build PDF sized to content (landscape orientation)
      const imgData = canvas.toDataURL("image/jpeg", 0.97);
      const pxW = canvas.width;
      const pxH = canvas.height;
      // Use 150 DPI: 1 mm = 150/25.4 px
      const DPI = 150;
      const mmW = (pxW / DPI) * 25.4;
      const mmH = (pxH / DPI) * 25.4;

      const pdf = new jsPDF({
        orientation: mmW > mmH ? "landscape" : "portrait",
        unit: "mm",
        format: [mmW, mmH],
      });

      pdf.addImage(imgData, "JPEG", 0, 0, mmW, mmH, undefined, "FAST");

      const slug = data.disease.replace(/[^a-z0-9]/gi, "_").slice(0, 40);
      pdf.save(`patient_journey_${slug}_${new Date().toISOString().slice(0, 10)}.pdf`);

      showToast("PDF exported successfully");
    } catch (err) {
      console.error("PDF export error:", err);
      showToast("PDF export failed — see console for details.", "error");
    } finally {
      setIsExporting(false);
    }
  };

  const handleOpenRefine = (phase: Phase, sectionKey: string) => { setRefineTarget({ phase, sectionKey }); setSelectedPhase(null); };

  const handleRegenerate = async (feedback: { correct: string; incorrect: string; instructions: string }) => {
    if (!refineTarget) return;
    setIsLoading(true);
    const { phase, sectionKey } = refineTarget;
    const result = await regenerateSection(data.disease, phase, sectionKey, feedback, data);
    setIsLoading(false);
    if (result.error) { showToast(`Regeneration failed: ${result.error}`, "error"); return; }
    setPendingChange({ phaseId: phase.phase_id, sectionKey, oldValue: (phase as Record<string, unknown>)[sectionKey], newValue: result.regenerated_section, summary: result.change_summary, confidence: result.confidence, verification: result.verification_note, feedback });
    setRefineTarget(null);
  };

  const handleAcceptChange = () => {
    if (!pendingChange) return;
    const { phaseId, sectionKey, newValue, confidence, summary, feedback } = pendingChange;
    setData((prev) => {
      const updated = JSON.parse(JSON.stringify(prev)) as JourneyData;
      const phase = updated.phases.find((p) => p.phase_id === phaseId);
      if (phase) { (phase as Record<string, unknown>)[sectionKey] = newValue; if (confidence) phase.confidence = confidence as Phase["confidence"]; }
      return updated;
    });
    setChangedSections((prev) => new Set([...prev, `${phaseId}:${sectionKey}`]));
    setHistory((prev) => [{ phaseId, sectionKey, oldValue: pendingChange.oldValue, newValue, summary, confidence, feedback, status: "accepted", timestamp: Date.now() }, ...prev]);
    setPendingChange(null);
    showToast("Changes applied successfully");
  };

  const handleRejectChange = () => {
    if (!pendingChange) return;
    setHistory((prev) => [{ phaseId: pendingChange.phaseId, sectionKey: pendingChange.sectionKey, summary: pendingChange.summary, status: "rejected", timestamp: Date.now() }, ...prev]);
    setPendingChange(null);
    showToast("Changes rejected", "info");
  };

  const handleRevert = (historyIdx: number) => {
    const entry = history[historyIdx];
    if (!entry || entry.status !== "accepted") return;
    setData((prev) => {
      const updated = JSON.parse(JSON.stringify(prev)) as JourneyData;
      const phase = updated.phases.find((p) => p.phase_id === entry.phaseId);
      if (phase) (phase as Record<string, unknown>)[entry.sectionKey] = entry.oldValue;
      return updated;
    });
    setChangedSections((prev) => { const n = new Set(prev); n.delete(`${entry.phaseId}:${entry.sectionKey}`); return n; });
    const updatedHist = [...history];
    updatedHist[historyIdx] = { ...entry, status: "reverted" };
    setHistory(updatedHist);
    showToast("Change reverted");
  };

  const phases = data.phases;
  const phaseHasChanges = (pid: string) => [...changedSections].some((k) => k.startsWith(pid + ":"));

  return (
    <div ref={exportRef} style={{ fontFamily: "'Figtree','Noto Sans','Segoe UI',sans-serif", background: "#F0F9FF", minHeight: "100vh", padding: "0 0 40px" }}>
      {toast && (
        <div style={{ position: "fixed", top: 16, left: "50%", transform: "translateX(-50%)", zIndex: 9999, padding: "10px 24px", borderRadius: 8, fontSize: 13, fontWeight: 600, color: "#fff", boxShadow: "0 4px 20px rgba(0,0,0,0.15)", background: toast.type === "error" ? "#D32F2F" : toast.type === "info" ? "#0891B2" : "#4CAF50" }}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div style={{ background: "#fff", borderBottom: "1px solid #E2F4FA", padding: "18px 32px 16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ width: 36, height: 36, borderRadius: 9, background: "linear-gradient(135deg, #0891B2, #0E7490)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M3 12h3l3-8 4 16 3-8h5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: "#0C4A6E", letterSpacing: "-0.01em" }}>Patient Journey Mapping</h1>
              <p style={{ margin: "2px 0 0", fontSize: 12, color: "#64748B" }}>Understanding patient realities to reveal unmet needs · Powered by SYN10X</p>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <a href="/" style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 8, padding: "7px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer", color: "#475569", textDecoration: "none", display: "flex", alignItems: "center", gap: 6, transition: "all 0.15s" }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLAnchorElement).style.borderColor = "#0891B2"; (e.currentTarget as HTMLAnchorElement).style.color = "#0891B2"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLAnchorElement).style.borderColor = "#E2E8F0"; (e.currentTarget as HTMLAnchorElement).style.color = "#475569"; }}>
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
              New journey
            </a>
            <button
              onClick={exportPDF}
              disabled={isExporting}
              style={{ background: isExporting ? "#E0F2FE" : "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 8, padding: "7px 14px", fontSize: 12, fontWeight: 600, cursor: isExporting ? "not-allowed" : "pointer", color: isExporting ? "#0891B2" : "#475569", display: "flex", alignItems: "center", gap: 6, transition: "all 0.15s", opacity: isExporting ? 0.75 : 1 }}
              onMouseEnter={(e) => { if (!isExporting) { (e.currentTarget as HTMLButtonElement).style.borderColor = "#0891B2"; (e.currentTarget as HTMLButtonElement).style.color = "#0891B2"; } }}
              onMouseLeave={(e) => { if (!isExporting) { (e.currentTarget as HTMLButtonElement).style.borderColor = "#E2E8F0"; (e.currentTarget as HTMLButtonElement).style.color = "#475569"; } }}>
              {isExporting
                ? <><svg width="13" height="13" viewBox="0 0 16 16" style={{ animation: "spin 1s linear infinite" }}><style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" fill="none" strokeDasharray="24" strokeDashoffset="6"/></svg> Exporting…</>
                : <><svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 2v8M5 7l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/><path d="M3 12h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg> Export PDF</>
              }
            </button>
            <button onClick={() => setShowHistory(true)} style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 8, padding: "7px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer", color: "#475569", display: "flex", alignItems: "center", gap: 6, transition: "all 0.15s" }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "#0891B2"; (e.currentTarget as HTMLButtonElement).style.color = "#0891B2"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "#E2E8F0"; (e.currentTarget as HTMLButtonElement).style.color = "#475569"; }}>
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3"/><path d="M8 5v3.5l2.5 1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
              History {history.length > 0 && <Badge bg="#0891B2" color="#fff">{history.length}</Badge>}
            </button>
          </div>
        </div>
        <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <Badge bg="#E0F2FE" color="#0369A1" style={{ padding: "4px 14px", fontSize: 13, borderRadius: 14, fontWeight: 600 }}>{data.disease}</Badge>
          <span style={{ fontSize: 11, color: "#94A3B8" }}>{phases.length} phases · {phases.reduce((a, p) => a + (p.evidence_claims?.length || 0), 0)} evidence claims · {changedSections.size} refinement{changedSections.size !== 1 ? "s" : ""}</span>
        </div>
        {data.summary && <p style={{ margin: "10px 0 0", fontSize: 13, color: "#475569", lineHeight: 1.65, maxWidth: 900 }}>{data.summary}</p>}
      </div>

      {/* Phase arrows */}
      <div style={{ padding: "16px 32px 0", overflowX: "auto" }}>
        <div style={{ display: "flex", gap: 0, minWidth: 800 }}>
          <div style={{ width: 30, flexShrink: 0 }}/>
          {phases.map((p, i) => <PhaseArrow key={p.phase_id} color={PHASE_COLORS[p.phase_id]?.bg || "#888"} label={PHASE_LABELS[p.phase_id] || p.phase_id} isFirst={i === 0} hasChanges={phaseHasChanges(p.phase_id)} onClick={() => setSelectedPhase(p)}/>)}
        </div>

        {/* Headlines + confidence */}
        <div style={{ display: "flex", minWidth: 800, marginTop: 8 }}>
          <div style={{ width: 30, flexShrink: 0 }}/>
          {phases.map((p) => (
            <div key={p.phase_id} style={{ flex: 1, textAlign: "center", padding: "4px 6px", cursor: "pointer" }} onClick={() => setSelectedPhase(p)}>
              <div style={{ fontSize: 11, fontWeight: 600, color: PHASE_COLORS[p.phase_id]?.text || "#1E293B", lineHeight: 1.3 }}>{p.headline}</div>
              <div style={{ marginTop: 4, display: "flex", justifyContent: "center", gap: 4 }}>
                <ConfBadge level={p.confidence}/>
                {phaseHasChanges(p.phase_id) && <Badge bg="#E0F2FE" color="#0369A1" style={{ fontSize: 8 }}>Refined</Badge>}
              </div>
            </div>
          ))}
        </div>

        {/* Feelings row */}
        <GridRow label="Feelings" color="#0891B2" phases={phases} changedSections={changedSections} sectionKey="feelings" onClickPhase={setSelectedPhase} renderCell={(p) => (
          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>{p.feelings.map((f) => (
            <span key={f} style={{ display: "block", padding: "3px 8px", borderRadius: 8, border: `1.5px solid ${PHASE_COLORS[p.phase_id]?.text || "#333"}`, fontSize: 10, fontWeight: 500, color: PHASE_COLORS[p.phase_id]?.text || "#333", lineHeight: 1.4, wordBreak: "break-word" }}>{f}</span>
          ))}</div>
        )}/>

        {/* Emotional arc */}
        <div style={{ display: "flex", marginTop: 8, minWidth: 800 }}>
          <RowLabel label="Moment" color="#D97706"/>
          <div style={{ flex: 1, background: "#fff", border: "1px solid #E2F4FA", borderRadius: "0 6px 6px 0", padding: "6px 0" }}>
            <EmotionalArcSVG phases={phases}/>
            <div style={{ display: "flex" }}>
              {phases.map((p, i) => (
                <div key={p.phase_id} style={{ flex: 1, textAlign: "left", padding: "6px 10px", borderRight: i < phases.length - 1 ? "1px solid #F1F5F9" : "none", cursor: "pointer" }} onClick={() => setSelectedPhase(p)}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "#1E293B", marginBottom: 3 }}>{p.moment.title}</div>
                  <div style={{ fontSize: 10, color: "#475569", lineHeight: 1.45 }}>{p.moment.description.slice(0, 160)}{p.moment.description.length > 160 ? "…" : ""}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Mindset row */}
        <GridRow label="Mindset" color="#4F46E5" phases={phases} changedSections={changedSections} sectionKey="mindset" onClickPhase={setSelectedPhase} renderCell={(p) => (
          <div style={{ fontStyle: "italic", fontSize: 11, color: "#475569", lineHeight: 1.4, borderLeft: `2px solid ${PHASE_COLORS[p.phase_id]?.mid || "#999"}`, paddingLeft: 8 }}>{p.mindset}</div>
        )}/>

        {/* Pain points row */}
        <GridRow label="Pain points" color="#DC2626" phases={phases} changedSections={changedSections} sectionKey="pain_points" onClickPhase={setSelectedPhase} renderCell={(p) => (
          <>{p.pain_points.map((pp, j) => (
            <div key={j} style={{ display: "flex", alignItems: "flex-start", gap: 5, marginBottom: 4 }}>
              <div style={{ width: 7, height: 7, borderRadius: "50%", background: SEVERITY_DOT[pp.severity] || "#999", marginTop: 4, flexShrink: 0 }}/>
              <div style={{ fontSize: 10, lineHeight: 1.3, color: "#334155" }}>{pp.description}</div>
            </div>
          ))}</>
        )}/>

        {/* Unmet needs row */}
        <GridRow label="Unmet needs" color="#6D28D9" phases={phases} changedSections={changedSections} sectionKey="unmet_needs" onClickPhase={setSelectedPhase} renderCell={(p) => (
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {p.unmet_needs?.map((n, i) => (
              <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 5 }}>
                <svg width="8" height="8" viewBox="0 0 8 8" style={{ flexShrink: 0, marginTop: 3 }} fill="#6D28D9"><polygon points="0,0 8,4 0,8"/></svg>
                <div style={{ fontSize: 10, color: "#4C1D95", lineHeight: 1.4 }}>{n}</div>
              </div>
            ))}
          </div>
        )}/>

        {/* Evidence gaps row */}
        <GridRow label="Gaps" color="#B91C1C" phases={phases} changedSections={changedSections} sectionKey="gaps" onClickPhase={setSelectedPhase} renderCell={(p) => (
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {p.gaps?.length > 0 ? p.gaps.map((g, i) => (
              <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 5 }}>
                <svg width="11" height="11" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0, marginTop: 2 }}>
                  <path d="M8 2L14.9 14H1.1L8 2z" stroke="#B91C1C" strokeWidth="1.4" strokeLinejoin="round"/>
                  <path d="M8 6v3M8 11v.5" stroke="#B91C1C" strokeWidth="1.4" strokeLinecap="round"/>
                </svg>
                <div style={{ fontSize: 10, color: "#B91C1C", lineHeight: 1.4 }}>{g}</div>
              </div>
            )) : <div style={{ fontSize: 10, color: "#94A3B8" }}>No gaps identified</div>}
          </div>
        )}/>

        {/* Evidence row — last */}
        <GridRow label="Evidence" color="#1E293B" phases={phases} changedSections={changedSections} sectionKey="evidence_claims" onClickPhase={setSelectedPhase} renderCell={(p) => (
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            {p.evidence_claims?.map((c, i) => {
              const doiMatch = c.source?.match(/doi:(10\.\S+)/i);
              const doi = doiMatch ? doiMatch[1].replace(/[.,;)]+$/, "") : null;
              const href = doi ? `https://doi.org/${doi}` : (c.source_type === "pubmed" || c.source_type === "spine") ? `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(c.source)}` : null;
              return (
                <div key={i} style={{ fontSize: 10, lineHeight: 1.4 }}>
                  <div style={{ color: "#1E293B", marginBottom: 2 }}>{c.claim}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
                    <SrcBadge type={c.source_type}/>
                    {href ? (
                      <a href={href} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} style={{ fontSize: 9, color: "#1565C0", textDecoration: "underline" }}>{doi ? `doi:${doi}` : c.source}</a>
                    ) : (
                      <span style={{ fontSize: 9, color: "#94A3B8" }}>{c.source}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}/>
      </div>

      {/* Legend */}
      <div style={{ padding: "20px 32px 0", display: "flex", gap: 14, flexWrap: "wrap" }}>
        <LegendBox title="Severity">
          <div style={{ display: "flex", gap: 14 }}>
            {Object.entries(SEVERITY_DOT).map(([k, v]) => <div key={k} style={{ display: "flex", alignItems: "center", gap: 5 }}><div style={{ width: 8, height: 8, borderRadius: "50%", background: v }}/><span style={{ fontSize: 10, color: "#64748B", textTransform: "capitalize" }}>{k}</span></div>)}
          </div>
        </LegendBox>
        <LegendBox title="Sources">
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {["spine", "web", "fda_label", "clinical_trial"].map((t) => <SrcBadge key={t} type={t}/>)}
          </div>
        </LegendBox>
        <LegendBox title="Tip">
          <div style={{ fontSize: 11, color: "#64748B", lineHeight: 1.5 }}>Click any phase to view details. Use the <span style={{ color: "#0891B2", fontWeight: 600 }}>Refine</span> button on any section to provide AI feedback and regenerate.</div>
        </LegendBox>
      </div>

      {/* Panels and modals */}
      {selectedPhase && (
        <>
          <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.25)", zIndex: 999 }} onClick={() => setSelectedPhase(null)}/>
          <DetailPanel phase={selectedPhase} onClose={() => setSelectedPhase(null)} onRefine={handleOpenRefine} changedSections={changedSections}/>
        </>
      )}
      {refineTarget && (
        <RefineModal phase={refineTarget.phase} sectionKey={refineTarget.sectionKey} currentContent={(refineTarget.phase as Record<string, unknown>)[refineTarget.sectionKey]} onClose={() => setRefineTarget(null)} onRegenerate={handleRegenerate} isLoading={isLoading}/>
      )}
      {pendingChange && (
        <ChangesPanel change={pendingChange} onAccept={handleAcceptChange} onReject={handleRejectChange} onClose={() => setPendingChange(null)}/>
      )}
      {showHistory && (
        <>
          <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.2)", zIndex: 1499 }} onClick={() => setShowHistory(false)}/>
          <RevisionHistory history={history} onRevert={handleRevert} onClose={() => setShowHistory(false)}/>
        </>
      )}
    </div>
  );
}
