import { useState, useRef, useEffect, useCallback } from "react";

/* ═══════════════════════════════════════════════════════════════
   SAMPLE DATA — Replace with live Pass 2 JSON from orchestrator
   ═══════════════════════════════════════════════════════════════ */
const INITIAL_DATA = {
  disease: "Systemic Lupus Erythematosus (SLE)",
  summary: "SLE patients face an average 6-year diagnostic odyssey marked by emotional volatility, treatment complexity, and persistent unmet needs in care coordination.",
  phases: [
    {
      phase_id: "presentation",
      headline: "The invisible struggle begins",
      feelings: ["Confusion", "Anxiety", "Frustration", "Self-doubt"],
      moment: { title: "Something isn't right", description: "Persistent joint pain, fatigue, and a butterfly rash appear. Symptoms are vague and episodic, dismissed as stress or aging.", emotional_arc: "falling" },
      mindset: "\"I know something is wrong with me, but no one believes me. Maybe it's all in my head.\"",
      pain_points: [
        { description: "Symptoms dismissed by PCPs as stress or psychosomatic", stakeholder: "PCP", severity: "critical" },
        { description: "Average 4+ physician visits before referral to rheumatology", stakeholder: "Health System", severity: "high" }
      ],
      evidence_claims: [
        { claim: "Mean time from symptom onset to SLE diagnosis is 6.3 years", source: "Lupus Foundation of America", source_type: "web" },
        { claim: "73% of patients report being told symptoms were psychosomatic", source: "Patient survey 2023", source_type: "spine" }
      ],
      unmet_needs: ["Earlier recognition of multi-system symptom patterns", "PCP education on lupus red flags"],
      confidence: "HIGH", verification_notes: "Well-supported by multiple independent sources.", gaps: []
    },
    {
      phase_id: "diagnosis",
      headline: "Relief meets overwhelm",
      feelings: ["Shock", "Relief", "Grief", "Hope"],
      moment: { title: "Finally, a name for this", description: "After years of searching, a rheumatologist confirms SLE. The diagnosis brings validation but also fear about what lies ahead.", emotional_arc: "volatile" },
      mindset: "\"I finally have an answer. But what does this mean for my life? Will I ever feel normal again?\"",
      pain_points: [
        { description: "Diagnosis often delivered without adequate counseling or resources", stakeholder: "Specialist", severity: "high" },
        { description: "Patients overwhelmed by complex treatment regimen information", stakeholder: "Pharma", severity: "moderate" }
      ],
      evidence_claims: [
        { claim: "SLE requires meeting 4 of 11 ACR classification criteria", source: "ACR Guidelines", source_type: "web" },
        { claim: "62% of patients felt unprepared for life after diagnosis", source: "Patient interviews", source_type: "spine" }
      ],
      unmet_needs: ["Structured onboarding program post-diagnosis", "Peer mentorship connections"],
      confidence: "HIGH", verification_notes: "ACR criteria well-established.", gaps: []
    },
    {
      phase_id: "treatment",
      headline: "The trial-and-error marathon",
      feelings: ["Hope", "Impatience", "Side-effect fatigue", "Determination"],
      moment: { title: "Finding what works", description: "Cycling through hydroxychloroquine, corticosteroids, and immunosuppressants. Each adjustment requires weeks to evaluate.", emotional_arc: "volatile" },
      mindset: "\"Every new medication is a gamble. I'm tired of being a science experiment, but I have to keep trying.\"",
      pain_points: [
        { description: "Average 3-4 treatment changes in first 2 years", stakeholder: "Specialist", severity: "high" },
        { description: "Corticosteroid side effects poorly managed", stakeholder: "PCP", severity: "critical" },
        { description: "Insurance prior auth delays of 2-6 weeks for biologics", stakeholder: "Insurer", severity: "critical" }
      ],
      evidence_claims: [
        { claim: "Belimumab approved as first biologic for SLE in 2011", source: "FDA Label", source_type: "fda_label" },
        { claim: "52% of SLE patients report medication non-adherence due to side effects", source: "JAMA Rheumatology 2022", source_type: "web" }
      ],
      unmet_needs: ["Better predictive biomarkers for treatment response", "Streamlined prior auth pathways"],
      confidence: "MEDIUM", verification_notes: "Treatment patterns well-documented. Adherence stats vary (42-62%).", gaps: ["Need more data on real-world biologic sequencing"]
    },
    {
      phase_id: "re_diagnosis",
      headline: "The goalposts move",
      feelings: ["Frustration", "Betrayal", "Exhaustion", "Anger"],
      moment: { title: "It's not just lupus", description: "New symptoms emerge — nephritis, antiphospholipid syndrome, or CNS involvement. The disease is reclassified.", emotional_arc: "falling" },
      mindset: "\"I thought I understood my disease. Now it's something worse. How many more surprises?\"",
      pain_points: [
        { description: "Lupus nephritis affects 50% of patients, often requiring complete treatment change", stakeholder: "Specialist", severity: "critical" },
        { description: "Care fragmentation across rheumatology, nephrology, and neurology", stakeholder: "Health System", severity: "high" }
      ],
      evidence_claims: [
        { claim: "Lupus nephritis develops within 5 years of diagnosis in ~50% of SLE patients", source: "NIH NIDDK", source_type: "web" },
        { claim: "15 active trials for lupus nephritis on ClinicalTrials.gov", source: "ClinicalTrials.gov", source_type: "clinical_trial" }
      ],
      unmet_needs: ["Integrated multi-specialty care coordination", "Proactive organ monitoring protocols"],
      confidence: "MEDIUM", verification_notes: "Nephritis prevalence well-documented. Care fragmentation needs more quantitative support.", gaps: ["Limited data on patient experience during reclassification"]
    },
    {
      phase_id: "tx_adaptation",
      headline: "Rebuilding the playbook",
      feelings: ["Guilt", "Resignation", "Cautious hope", "Weariness"],
      moment: { title: "Starting over — again", description: "New specialists, new medications, new side effects. The patient becomes an expert navigator of their own care by necessity.", emotional_arc: "rising" },
      mindset: "\"I've learned more about my disease than most doctors know. I have to be my own advocate.\"",
      pain_points: [
        { description: "Patients bear coordination burden across 3+ specialists", stakeholder: "Health System", severity: "high" },
        { description: "Limited access to lupus-specialized centers outside major metros", stakeholder: "Health System", severity: "high" }
      ],
      evidence_claims: [
        { claim: "Only 38% of US counties have a practicing rheumatologist", source: "ACR Workforce Study", source_type: "web" },
        { claim: "Voclosporin approved for lupus nephritis in 2021", source: "FDA Label", source_type: "fda_label" }
      ],
      unmet_needs: ["Telehealth-enabled specialty access", "Patient-reported outcome tools"],
      confidence: "LOW", verification_notes: "Workforce data is strong. Patient self-advocacy claims are largely inferential.", gaps: ["Need quantitative data on care coordination failures", "Limited evidence on telehealth effectiveness for SLE"]
    },
    {
      phase_id: "living_with",
      headline: "The new normal is never normal",
      feelings: ["Insecurity", "Resilience", "Isolation", "Acceptance"],
      moment: { title: "Every day is a negotiation", description: "Managing flares, medication schedules, work limitations, and invisible disability. The disease is managed but never gone.", emotional_arc: "stable" },
      mindset: "\"I've accepted that this is my life now. Some days are good. I've stopped waiting to be cured.\"",
      pain_points: [
        { description: "Workplace discrimination and disability claim complexity", stakeholder: "Employer/Insurer", severity: "high" },
        { description: "Mental health comorbidities undertreated (depression in 25-40%)", stakeholder: "PCP", severity: "critical" }
      ],
      evidence_claims: [
        { claim: "Depression prevalence in SLE estimated at 25-40%", source: "Rheumatology International 2023", source_type: "web" },
        { claim: "SLE patients report mean FACIT-Fatigue score of 28.6 vs 43.6 general population", source: "Quality of Life Research", source_type: "spine" }
      ],
      unmet_needs: ["Integrated mental health screening in rheumatology", "Better fatigue management tools"],
      confidence: "HIGH", verification_notes: "Quality of life and mental health data well-supported.", gaps: []
    }
  ],
  assumptions: ["US-centric healthcare system", "Adult-onset SLE", "Patient has insurance coverage"]
};

/* ═══════════════════════════════════════════════════════════════
   CONSTANTS
   ═══════════════════════════════════════════════════════════════ */
const PHASE_COLORS = {
  presentation: { bg: "#4CAF50", light: "#E8F5E9", text: "#1B5E20", mid: "#81C784" },
  diagnosis:    { bg: "#FFC107", light: "#FFF8E1", text: "#F57F17", mid: "#FFD54F" },
  treatment:    { bg: "#FF9800", light: "#FFF3E0", text: "#E65100", mid: "#FFB74D" },
  re_diagnosis: { bg: "#F44336", light: "#FFEBEE", text: "#B71C1C", mid: "#E57373" },
  tx_adaptation:{ bg: "#D32F2F", light: "#FFCDD2", text: "#B71C1C", mid: "#EF5350" },
  living_with:  { bg: "#B71C1C", light: "#FFCDD2", text: "#7F0000", mid: "#E53935" },
};
const PHASE_LABELS = { presentation:"Presentation", diagnosis:"Diagnosis", treatment:"Treatment", re_diagnosis:"Re-Diagnosis", tx_adaptation:"Tx Adaptation", living_with:"Living With" };
const CONFIDENCE_BADGE = { HIGH:{color:"#1B5E20",bg:"#C8E6C9",label:"High"}, MEDIUM:{color:"#E65100",bg:"#FFE0B2",label:"Medium"}, LOW:{color:"#B71C1C",bg:"#FFCDD2",label:"Low"}, UNSUPPORTED:{color:"#4A148C",bg:"#E1BEE7",label:"Unsupported"} };
const SEVERITY_DOT = { critical:"#D32F2F", high:"#FF9800", moderate:"#FFC107", low:"#4CAF50" };
const SECTION_KEYS = ["headline","feelings","moment","mindset","pain_points","evidence_claims","unmet_needs"];
const SECTION_LABELS = { headline:"Headline", feelings:"Feelings", moment:"Patient moment", mindset:"Mindset", pain_points:"Pain points", evidence_claims:"Evidence claims", unmet_needs:"Unmet needs" };

/* ═══════════════════════════════════════════════════════════════
   LLM REGENERATION ENGINE
   ═══════════════════════════════════════════════════════════════ */
async function regenerateSection(disease, phase, sectionKey, feedback, fullJourney) {
  const sysPrompt = `You are an expert patient journey analyst. The user is refining a patient journey map for ${disease}.

You are looking at the "${PHASE_LABELS[phase.phase_id]}" phase, specifically the "${SECTION_LABELS[sectionKey]}" section.

## YOUR TASK
The user has reviewed this section and provided feedback on what is correct and what needs fixing. Regenerate ONLY this section incorporating their feedback.

## RULES
1. KEEP everything the user marked as correct — do not remove or weaken it
2. FIX everything the user marked as incorrect — replace, correct, or remove it
3. APPLY any additional instructions the user provided
4. MAINTAIN the same JSON structure as the original
5. If the section is "evidence_claims", every claim must have a source_type (spine, web, clinical_trial, fda_label, ci_supplement, or model_inference)
6. If the section is "pain_points", each must have description, stakeholder, and severity (critical/high/moderate/low)
7. Search the web for additional evidence if the user says something is factually wrong
8. After regenerating, provide a brief "change_summary" explaining what you changed and why
9. Also provide an updated "confidence" rating for this phase given the changes

## CURRENT FULL PHASE DATA (for context)
${JSON.stringify(phase, null, 2)}

## ADJACENT PHASES (for consistency)
${JSON.stringify(fullJourney.phases.filter(p => p.phase_id !== phase.phase_id).map(p => ({ phase_id: p.phase_id, headline: p.headline })))}

Return ONLY valid JSON with this structure:
{
  "regenerated_section": <the new content for "${sectionKey}" matching its original data type>,
  "change_summary": "Brief explanation of changes",
  "confidence": "HIGH|MEDIUM|LOW",
  "verification_note": "Brief note on evidence quality of the regenerated content"
}`;

  const userMsg = `Current "${SECTION_LABELS[sectionKey]}" content:
${JSON.stringify(phase[sectionKey], null, 2)}

USER FEEDBACK:
What is correct: ${feedback.correct || "No specific feedback on correct items."}
What is incorrect: ${feedback.incorrect || "No specific feedback on incorrect items."}
Additional instructions: ${feedback.instructions || "None."}

Regenerate this section now. Return only JSON.`;

  try {
    const resp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "claude-sonnet-4-20250514",
        max_tokens: 2000,
        tools: [{ type: "web_search_20250305", name: "web_search" }],
        system: sysPrompt,
        messages: [{ role: "user", content: userMsg }],
      }),
    });
    const data = await resp.json();
    const text = data.content?.filter(b => b.type === "text").map(b => b.text).join("\n") || "";
    const clean = text.replace(/```json\s?/g, "").replace(/```/g, "").trim();
    const start = clean.indexOf("{");
    const end = clean.lastIndexOf("}");
    if (start >= 0 && end > start) return JSON.parse(clean.slice(start, end + 1));
    return { error: "Could not parse LLM response", raw: text };
  } catch (err) {
    return { error: err.message };
  }
}

/* ═══════════════════════════════════════════════════════════════
   SMALL UI COMPONENTS
   ═══════════════════════════════════════════════════════════════ */
const Badge = ({ bg, color, children, style: sx }) => (
  <span style={{ display:"inline-block", padding:"2px 8px", borderRadius:10, fontSize:10, fontWeight:600, background:bg, color, letterSpacing:"0.03em", ...sx }}>{children}</span>
);

const ConfBadge = ({ level }) => { const c = CONFIDENCE_BADGE[level]||CONFIDENCE_BADGE.MEDIUM; return <Badge bg={c.bg} color={c.color}>{c.label}</Badge>; };

const Pill = ({ text, color }) => (
  <span style={{ display:"inline-block", padding:"3px 10px", borderRadius:12, border:`1.5px solid ${color}`, fontSize:11, fontWeight:500, color, margin:"2px 3px", whiteSpace:"nowrap" }}>{text}</span>
);

const SrcBadge = ({ type }) => {
  const m = { spine:["#E3F2FD","#1565C0"], web:["#F3E5F5","#6A1B9A"], fda_label:["#FFF3E0","#E65100"], clinical_trial:["#E8F5E9","#2E7D32"], ci_supplement:["#FFF8E1","#F57F17"], model_inference:["#F5F5F5","#616161"] };
  const [bg,c] = m[type]||m.model_inference;
  return <Badge bg={bg} color={c} style={{ fontSize:9, textTransform:"uppercase", letterSpacing:"0.04em" }}>{type?.replace("_"," ")}</Badge>;
};

const PhaseArrow = ({ color, label, isFirst, hasChanges, onClick }) => (
  <div style={{ display:"flex", alignItems:"center", flex:1, minWidth:0, cursor:"pointer", position:"relative" }} onClick={onClick}>
    {hasChanges && <div style={{ position:"absolute", top:-4, right:8, width:10, height:10, borderRadius:"50%", background:"#7C4DFF", border:"2px solid #fff", zIndex:2 }} />}
    <div style={{
      background:color, color:"#fff", padding:"10px 20px 10px 28px", fontWeight:600, fontSize:12,
      letterSpacing:"0.05em", textTransform:"uppercase", lineHeight:1.3, whiteSpace:"nowrap", textAlign:"center", width:"100%",
      clipPath: isFirst ? "polygon(0 0,calc(100% - 14px) 0,100% 50%,calc(100% - 14px) 100%,0 100%)" : "polygon(0 0,calc(100% - 14px) 0,100% 50%,calc(100% - 14px) 100%,0 100%,14px 50%)",
    }}>{label}</div>
  </div>
);

const RefineBtn = ({ onClick, small, label }) => (
  <button onClick={e => { e.stopPropagation(); onClick(); }} style={{
    background:"none", border:"1.5px solid #7C4DFF", color:"#7C4DFF", borderRadius:6,
    padding: small ? "3px 10px" : "5px 14px", fontSize: small ? 10 : 11, fontWeight:600, cursor:"pointer",
    display:"inline-flex", alignItems:"center", gap:4, transition:"all 0.15s",
  }} onMouseEnter={e=>{e.target.style.background="#7C4DFF";e.target.style.color="#fff"}} onMouseLeave={e=>{e.target.style.background="none";e.target.style.color="#7C4DFF"}}>
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M13.5 2.5a2.12 2.12 0 00-3 0L3.7 9.3a1 1 0 00-.26.44l-.9 3.2a.5.5 0 00.62.62l3.2-.9a1 1 0 00.44-.26l6.8-6.8a2.12 2.12 0 000-3z" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
    {label || "Refine"}
  </button>
);

/* ═══════════════════════════════════════════════════════════════
   EMOTIONAL ARC SVG
   ═══════════════════════════════════════════════════════════════ */
function EmotionalArcSVG({ phases }) {
  const w=900, h=90;
  const arcV = { rising:0.3, falling:0.75, stable:0.5, volatile:0.5 };
  const pw = w / phases.length;
  const pts = phases.map((p,i) => ({ x:pw*i+pw/2, y:h*0.1+(h*0.8)*(arcV[p.moment?.emotional_arc]||0.5) }));
  let d = `M ${pts[0].x} ${pts[0].y}`;
  for (let i=1;i<pts.length;i++) { const p=pts[i-1],c=pts[i]; d += ` C ${p.x+(c.x-p.x)*0.4} ${p.y}, ${p.x+(c.x-p.x)*0.6} ${c.y}, ${c.x} ${c.y}`; }
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width:"100%", height:70 }}>
      <defs><linearGradient id="ag" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#4CAF50"/><stop offset="50%" stopColor="#FF9800"/><stop offset="100%" stopColor="#B71C1C"/></linearGradient></defs>
      <path d={d} fill="none" stroke="url(#ag)" strokeWidth="2.5" strokeLinecap="round"/>
      {pts.map((p,i) => <circle key={i} cx={p.x} cy={p.y} r="4" fill={PHASE_COLORS[phases[i].phase_id].bg} stroke="#fff" strokeWidth="1.5"/>)}
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════════════
   FEEDBACK / REFINEMENT MODAL
   ═══════════════════════════════════════════════════════════════ */
function RefineModal({ phase, sectionKey, currentContent, onClose, onRegenerate, isLoading }) {
  const [correct, setCorrect] = useState("");
  const [incorrect, setIncorrect] = useState("");
  const [instructions, setInstructions] = useState("");
  const colors = PHASE_COLORS[phase.phase_id];

  const renderCurrentContent = () => {
    const v = currentContent;
    if (typeof v === "string") return <div style={{ fontSize:12, color:"#444", fontStyle:"italic", lineHeight:1.5 }}>{v}</div>;
    if (Array.isArray(v)) {
      if (typeof v[0] === "string") return v.map((s,i) => <div key={i} style={{ fontSize:12, color:"#444", marginBottom:3 }}>• {s}</div>);
      return v.map((item,i) => <div key={i} style={{ fontSize:11, color:"#555", marginBottom:6, padding:"6px 8px", background:"#F9F9F9", borderRadius:4 }}>{item.claim || item.description || JSON.stringify(item)}{item.source && <span style={{ color:"#999", marginLeft:6 }}>— {item.source}</span>}</div>);
    }
    if (v && typeof v === "object") return <div style={{ fontSize:12, color:"#444" }}><strong>{v.title}</strong><br/>{v.description}</div>;
    return <div style={{ fontSize:12, color:"#888" }}>{JSON.stringify(v)}</div>;
  };

  return (
    <div style={{ position:"fixed", inset:0, zIndex:2000, display:"flex", alignItems:"center", justifyContent:"center" }}>
      <div style={{ position:"absolute", inset:0, background:"rgba(0,0,0,0.45)" }} onClick={onClose}/>
      <div style={{ position:"relative", width:580, maxHeight:"85vh", background:"#fff", borderRadius:12, boxShadow:"0 20px 60px rgba(0,0,0,0.2)", overflow:"hidden", display:"flex", flexDirection:"column" }}>
        {/* Header */}
        <div style={{ background:colors.bg, padding:"18px 24px", color:"#fff", flexShrink:0 }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <div>
              <div style={{ fontSize:10, fontWeight:700, textTransform:"uppercase", opacity:0.8, letterSpacing:"0.1em" }}>Refine section</div>
              <div style={{ fontSize:18, fontWeight:700, marginTop:2 }}>{PHASE_LABELS[phase.phase_id]} — {SECTION_LABELS[sectionKey]}</div>
            </div>
            <button onClick={onClose} style={{ background:"rgba(255,255,255,0.2)", border:"none", color:"#fff", width:32, height:32, borderRadius:"50%", cursor:"pointer", fontSize:18 }}>×</button>
          </div>
        </div>

        <div style={{ padding:"20px 24px", overflowY:"auto", flex:1 }}>
          {/* Current content display */}
          <div style={{ marginBottom:20 }}>
            <label style={{ display:"block", fontSize:10, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.1em", color:"#999", marginBottom:6 }}>Current content</label>
            <div style={{ background:"#F8F8F8", borderRadius:8, padding:14, border:"1px solid #EEE", maxHeight:140, overflowY:"auto" }}>
              {renderCurrentContent()}
            </div>
          </div>

          {/* Correct feedback */}
          <div style={{ marginBottom:16 }}>
            <label style={{ display:"flex", alignItems:"center", gap:6, fontSize:11, fontWeight:700, color:"#2E7D32", marginBottom:6 }}>
              <svg width="14" height="14" viewBox="0 0 16 16"><path d="M13.5 4.5l-7 7L3 8" stroke="#2E7D32" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/></svg>
              What is correct? Keep these elements.
            </label>
            <textarea value={correct} onChange={e=>setCorrect(e.target.value)} placeholder='e.g. "The 6.3 year diagnosis delay stat is accurate. The feelings listed are on point."' style={{ width:"100%", minHeight:70, padding:12, borderRadius:8, border:"1.5px solid #C8E6C9", fontSize:12, fontFamily:"inherit", resize:"vertical", lineHeight:1.5, boxSizing:"border-box", outline:"none" }} onFocus={e=>e.target.style.borderColor="#4CAF50"} onBlur={e=>e.target.style.borderColor="#C8E6C9"} />
          </div>

          {/* Incorrect feedback */}
          <div style={{ marginBottom:16 }}>
            <label style={{ display:"flex", alignItems:"center", gap:6, fontSize:11, fontWeight:700, color:"#C62828", marginBottom:6 }}>
              <svg width="14" height="14" viewBox="0 0 16 16"><path d="M4 4l8 8M12 4l-8 8" stroke="#C62828" strokeWidth="2" strokeLinecap="round" fill="none"/></svg>
              What is incorrect? Fix or remove these.
            </label>
            <textarea value={incorrect} onChange={e=>setIncorrect(e.target.value)} placeholder='e.g. "The psychosomatic stat seems too high — I think it is closer to 50%. Also missing the rash as a key early symptom."' style={{ width:"100%", minHeight:70, padding:12, borderRadius:8, border:"1.5px solid #FFCDD2", fontSize:12, fontFamily:"inherit", resize:"vertical", lineHeight:1.5, boxSizing:"border-box", outline:"none" }} onFocus={e=>e.target.style.borderColor="#EF5350"} onBlur={e=>e.target.style.borderColor="#FFCDD2"} />
          </div>

          {/* Additional instructions */}
          <div style={{ marginBottom:16 }}>
            <label style={{ display:"flex", alignItems:"center", gap:6, fontSize:11, fontWeight:700, color:"#5C6BC0", marginBottom:6 }}>
              <svg width="14" height="14" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" stroke="#5C6BC0" strokeWidth="1.5" fill="none"/><path d="M8 5v3M8 10v.5" stroke="#5C6BC0" strokeWidth="1.5" strokeLinecap="round"/></svg>
              Additional instructions (optional)
            </label>
            <textarea value={instructions} onChange={e=>setInstructions(e.target.value)} placeholder='e.g. "Focus more on the emotional impact. Include data from the UK as well, not just US. Add a pain point about insurance denials."' style={{ width:"100%", minHeight:55, padding:12, borderRadius:8, border:"1.5px solid #C5CAE9", fontSize:12, fontFamily:"inherit", resize:"vertical", lineHeight:1.5, boxSizing:"border-box", outline:"none" }} onFocus={e=>e.target.style.borderColor="#5C6BC0"} onBlur={e=>e.target.style.borderColor="#C5CAE9"} />
          </div>
        </div>

        {/* Footer */}
        <div style={{ padding:"14px 24px", borderTop:"1px solid #EEE", display:"flex", justifyContent:"space-between", alignItems:"center", flexShrink:0, background:"#FAFAFA" }}>
          <button onClick={onClose} style={{ background:"none", border:"1px solid #DDD", color:"#777", borderRadius:8, padding:"8px 20px", fontSize:12, fontWeight:600, cursor:"pointer" }}>Cancel</button>
          <button onClick={() => onRegenerate({ correct, incorrect, instructions })} disabled={isLoading || (!correct && !incorrect && !instructions)} style={{
            background: isLoading ? "#B39DDB" : (!correct && !incorrect && !instructions) ? "#E0E0E0" : "#7C4DFF",
            border:"none", color:"#fff", borderRadius:8, padding:"8px 24px", fontSize:12, fontWeight:700, cursor: isLoading ? "wait" : "pointer",
            display:"flex", alignItems:"center", gap:8, opacity: (!correct && !incorrect && !instructions) ? 0.5 : 1,
          }}>
            {isLoading ? <><Spinner /> Regenerating...</> : <><svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 8a6 6 0 0111.5-2.3M14 8A6 6 0 012.5 10.3" stroke="#fff" strokeWidth="1.5" strokeLinecap="round"/><path d="M13.5 2v3.7h-3.7M2.5 14v-3.7h3.7" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg> Regenerate section</>}
          </button>
        </div>
      </div>
    </div>
  );
}

const Spinner = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" style={{ animation:"spin 1s linear infinite" }}>
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    <circle cx="8" cy="8" r="6" stroke="#fff" strokeWidth="2" fill="none" strokeDasharray="28" strokeDashoffset="8" strokeLinecap="round"/>
  </svg>
);

/* ═══════════════════════════════════════════════════════════════
   CHANGES REVIEW PANEL (shows diff after regeneration)
   ═══════════════════════════════════════════════════════════════ */
function ChangesPanel({ change, onAccept, onReject, onClose }) {
  if (!change) return null;
  const colors = PHASE_COLORS[change.phaseId];

  const renderVal = (v) => {
    if (typeof v === "string") return <span style={{ fontSize:12 }}>{v}</span>;
    if (Array.isArray(v)) return v.map((x,i) => <div key={i} style={{ fontSize:11, marginBottom:2 }}>• {typeof x === "string" ? x : (x.claim || x.description || x.title || JSON.stringify(x))}</div>);
    if (v && typeof v === "object") return <div style={{ fontSize:12 }}><strong>{v.title}</strong> — {v.description}</div>;
    return <span style={{ fontSize:12 }}>{JSON.stringify(v)}</span>;
  };

  return (
    <div style={{ position:"fixed", inset:0, zIndex:2000, display:"flex", alignItems:"center", justifyContent:"center" }}>
      <div style={{ position:"absolute", inset:0, background:"rgba(0,0,0,0.4)" }} onClick={onClose}/>
      <div style={{ position:"relative", width:620, maxHeight:"80vh", background:"#fff", borderRadius:12, boxShadow:"0 20px 60px rgba(0,0,0,0.2)", overflow:"hidden", display:"flex", flexDirection:"column" }}>
        <div style={{ background:"#7C4DFF", padding:"16px 24px", color:"#fff" }}>
          <div style={{ fontSize:10, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.1em", opacity:0.8 }}>Review changes</div>
          <div style={{ fontSize:16, fontWeight:700, marginTop:2 }}>{PHASE_LABELS[change.phaseId]} — {SECTION_LABELS[change.sectionKey]}</div>
        </div>
        <div style={{ padding:"20px 24px", overflowY:"auto", flex:1 }}>
          {/* Before */}
          <div style={{ marginBottom:16 }}>
            <div style={{ fontSize:10, fontWeight:700, textTransform:"uppercase", color:"#C62828", marginBottom:6, letterSpacing:"0.08em" }}>Before</div>
            <div style={{ background:"#FFF5F5", border:"1px solid #FFCDD2", borderRadius:8, padding:14 }}>{renderVal(change.oldValue)}</div>
          </div>
          {/* After */}
          <div style={{ marginBottom:16 }}>
            <div style={{ fontSize:10, fontWeight:700, textTransform:"uppercase", color:"#2E7D32", marginBottom:6, letterSpacing:"0.08em" }}>After</div>
            <div style={{ background:"#F1F8E9", border:"1px solid #C8E6C9", borderRadius:8, padding:14 }}>{renderVal(change.newValue)}</div>
          </div>
          {/* Change summary */}
          {change.summary && (
            <div style={{ background:"#F5F5F5", borderRadius:8, padding:14, marginBottom:16 }}>
              <div style={{ fontSize:10, fontWeight:700, textTransform:"uppercase", color:"#777", marginBottom:4, letterSpacing:"0.08em" }}>Change summary</div>
              <div style={{ fontSize:12, color:"#444", lineHeight:1.5 }}>{change.summary}</div>
            </div>
          )}
          {change.confidence && (
            <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:12 }}>
              <span style={{ fontSize:11, color:"#777" }}>Updated confidence:</span><ConfBadge level={change.confidence} />
            </div>
          )}
        </div>
        <div style={{ padding:"14px 24px", borderTop:"1px solid #EEE", display:"flex", justifyContent:"flex-end", gap:10, flexShrink:0, background:"#FAFAFA" }}>
          <button onClick={onReject} style={{ background:"none", border:"1px solid #FFCDD2", color:"#C62828", borderRadius:8, padding:"8px 20px", fontSize:12, fontWeight:600, cursor:"pointer" }}>Reject</button>
          <button onClick={onAccept} style={{ background:"#4CAF50", border:"none", color:"#fff", borderRadius:8, padding:"8px 24px", fontSize:12, fontWeight:700, cursor:"pointer" }}>Accept changes</button>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   REVISION HISTORY SIDEBAR
   ═══════════════════════════════════════════════════════════════ */
function RevisionHistory({ history, onRevert, onClose }) {
  return (
    <div style={{ position:"fixed", top:0, right:0, bottom:0, width:380, background:"#fff", boxShadow:"-4px 0 24px rgba(0,0,0,0.12)", zIndex:1500, display:"flex", flexDirection:"column", animation:"slideIn 0.2s ease-out" }}>
      <style>{`@keyframes slideIn { from { transform:translateX(100%); } to { transform:translateX(0); } }`}</style>
      <div style={{ padding:"20px 24px", borderBottom:"1px solid #EEE", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <div>
          <div style={{ fontSize:16, fontWeight:700, color:"#1A1A1A" }}>Revision history</div>
          <div style={{ fontSize:11, color:"#999", marginTop:2 }}>{history.length} revision{history.length!==1?"s":""}</div>
        </div>
        <button onClick={onClose} style={{ background:"#F5F5F5", border:"none", width:32, height:32, borderRadius:"50%", cursor:"pointer", fontSize:16, color:"#666" }}>×</button>
      </div>
      <div style={{ flex:1, overflowY:"auto", padding:"12px 24px" }}>
        {history.length === 0 && <div style={{ padding:20, textAlign:"center", color:"#AAA", fontSize:13 }}>No revisions yet. Refine a section to see changes here.</div>}
        {history.map((h,i) => (
          <div key={i} style={{ padding:14, border:"1px solid #EEE", borderRadius:8, marginBottom:10, background: h.status === "accepted" ? "#FAFFF8" : h.status === "rejected" ? "#FFF8F8" : "#F8F8FF" }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:6 }}>
              <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                <Badge bg={PHASE_COLORS[h.phaseId]?.bg||"#999"} color="#fff">{PHASE_LABELS[h.phaseId]}</Badge>
                <span style={{ fontSize:10, color:"#999" }}>{SECTION_LABELS[h.sectionKey]}</span>
              </div>
              <Badge bg={h.status==="accepted"?"#C8E6C9":h.status==="rejected"?"#FFCDD2":"#E0E0E0"} color={h.status==="accepted"?"#2E7D32":h.status==="rejected"?"#C62828":"#666"} style={{ fontSize:9 }}>{h.status}</Badge>
            </div>
            <div style={{ fontSize:11, color:"#555", lineHeight:1.4, marginBottom:8 }}>{h.summary}</div>
            <div style={{ display:"flex", gap:6, alignItems:"center", justifyContent:"space-between" }}>
              <span style={{ fontSize:9, color:"#BBB" }}>{new Date(h.timestamp).toLocaleTimeString()}</span>
              {h.status === "accepted" && <button onClick={()=>onRevert(i)} style={{ background:"none", border:"1px solid #FFCDD2", color:"#C62828", borderRadius:4, padding:"2px 8px", fontSize:10, fontWeight:600, cursor:"pointer" }}>Revert</button>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   DETAIL PANEL (per-phase deep dive with per-section refine)
   ═══════════════════════════════════════════════════════════════ */
function DetailPanel({ phase, onClose, onRefine, changedSections }) {
  const colors = PHASE_COLORS[phase.phase_id];
  const isChanged = (key) => changedSections?.has(`${phase.phase_id}:${key}`);

  const Section = ({ sKey, children }) => (
    <div style={{ marginBottom:20, position:"relative", background: isChanged(sKey) ? "#F3F0FF" : "transparent", borderRadius:8, padding: isChanged(sKey) ? "10px 12px" : 0, border: isChanged(sKey) ? "1px solid #D1C4E9" : "none", transition:"all 0.3s" }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
        <div style={{ display:"flex", alignItems:"center", gap:6 }}>
          <span style={{ fontSize:10, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.1em", color:"#999" }}>{SECTION_LABELS[sKey]}</span>
          {isChanged(sKey) && <Badge bg="#EDE7F6" color="#7C4DFF" style={{ fontSize:8 }}>Updated</Badge>}
        </div>
        <RefineBtn small onClick={()=>onRefine(phase, sKey)} />
      </div>
      {children}
    </div>
  );

  return (
    <div style={{ position:"fixed", top:0, right:0, bottom:0, width:440, background:"#fff", boxShadow:"-4px 0 24px rgba(0,0,0,0.12)", zIndex:1000, overflowY:"auto", animation:"slideIn 0.2s ease-out" }}>
      <style>{`@keyframes slideIn { from { transform:translateX(100%); } to { transform:translateX(0); } }`}</style>
      <div style={{ background:colors.bg, padding:"22px 24px", color:"#fff" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
          <div>
            <div style={{ fontSize:10, fontWeight:700, textTransform:"uppercase", opacity:0.85, letterSpacing:"0.08em" }}>{PHASE_LABELS[phase.phase_id]}</div>
            <div style={{ fontSize:18, fontWeight:700, marginTop:4 }}>{phase.headline}</div>
          </div>
          <button onClick={onClose} style={{ background:"rgba(255,255,255,0.2)", border:"none", color:"#fff", width:32, height:32, borderRadius:"50%", cursor:"pointer", fontSize:18 }}>×</button>
        </div>
        <div style={{ marginTop:8, display:"flex", gap:8 }}><ConfBadge level={phase.confidence} /></div>
      </div>
      <div style={{ padding:"20px 24px" }}>
        <Section sKey="headline"><div style={{ fontSize:16, fontWeight:700, color:"#333" }}>{phase.headline}</div></Section>
        <Section sKey="feelings"><div style={{ display:"flex", flexWrap:"wrap", gap:4 }}>{phase.feelings.map(f=><Pill key={f} text={f} color={colors.text}/>)}</div></Section>
        <Section sKey="moment">
          <div style={{ background:colors.light, borderRadius:8, padding:14, borderLeft:`3px solid ${colors.bg}` }}>
            <div style={{ fontWeight:600, fontSize:14, color:"#333", marginBottom:4 }}>{phase.moment.title}</div>
            <div style={{ fontSize:12, color:"#555", lineHeight:1.5 }}>{phase.moment.description}</div>
          </div>
        </Section>
        <Section sKey="mindset"><div style={{ fontStyle:"italic", fontSize:13, color:"#444", lineHeight:1.6, borderLeft:`2px solid ${colors.mid}`, paddingLeft:12 }}>{phase.mindset}</div></Section>
        <Section sKey="pain_points">
          {phase.pain_points.map((pp,j) => (
            <div key={j} style={{ display:"flex", alignItems:"flex-start", gap:6, marginBottom:6 }}>
              <div style={{ width:8, height:8, borderRadius:"50%", background:SEVERITY_DOT[pp.severity]||"#999", marginTop:4, flexShrink:0 }}/>
              <div style={{ fontSize:11, lineHeight:1.4 }}><span style={{ color:"#333" }}>{pp.description}</span>{pp.stakeholder && <Badge bg="#F5F5F5" color="#777" style={{ marginLeft:6, fontSize:9, textTransform:"uppercase" }}>{pp.stakeholder}</Badge>}</div>
            </div>
          ))}
        </Section>
        <Section sKey="evidence_claims">
          {phase.evidence_claims?.map((c,i) => (
            <div key={i} style={{ marginBottom:8, fontSize:12, lineHeight:1.5 }}>
              <div style={{ color:"#333" }}>{c.claim}</div>
              <div style={{ marginTop:2 }}><SrcBadge type={c.source_type}/><span style={{ marginLeft:6, fontSize:11, color:"#888" }}>{c.source}</span></div>
            </div>
          ))}
        </Section>
        <Section sKey="unmet_needs">
          {phase.unmet_needs?.map((n,i) => <div key={i} style={{ fontSize:12, color:"#444", marginBottom:4, paddingLeft:12, position:"relative" }}><span style={{ position:"absolute", left:0, color:colors.bg }}>▸</span>{n}</div>)}
        </Section>
        {phase.gaps?.length > 0 && (
          <div style={{ marginBottom:20 }}>
            <div style={{ fontSize:10, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.1em", color:"#C62828", marginBottom:6 }}>Evidence gaps</div>
            {phase.gaps.map((g,i) => <div key={i} style={{ fontSize:12, color:"#B71C1C", marginBottom:4 }}>⚠ {g}</div>)}
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   ROW LABEL
   ═══════════════════════════════════════════════════════════════ */
const RowLabel = ({ label, color }) => (
  <div style={{ writingMode:"vertical-rl", textOrientation:"mixed", transform:"rotate(180deg)", background:color||"#455A64", color:"#fff", padding:"12px 6px", fontWeight:700, fontSize:10, letterSpacing:"0.08em", textTransform:"uppercase", borderRadius:"6px 0 0 6px", display:"flex", alignItems:"center", justifyContent:"center", minHeight:70, width:30 }}>{label}</div>
);

/* ═══════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════════════════ */
export default function PatientJourneyMap() {
  const [data, setData] = useState(INITIAL_DATA);
  const [selectedPhase, setSelectedPhase] = useState(null);
  const [refineTarget, setRefineTarget] = useState(null);
  const [pendingChange, setPendingChange] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [changedSections, setChangedSections] = useState(new Set());
  const [toast, setToast] = useState(null);

  const showToast = (msg, type="success") => { setToast({msg,type}); setTimeout(()=>setToast(null), 3000); };

  const handleOpenRefine = (phase, sectionKey) => {
    setRefineTarget({ phase, sectionKey });
    setSelectedPhase(null);
  };

  const handleRegenerate = async (feedback) => {
    if (!refineTarget) return;
    setIsLoading(true);
    const { phase, sectionKey } = refineTarget;
    const result = await regenerateSection(data.disease, phase, sectionKey, feedback, data);
    setIsLoading(false);

    if (result.error) {
      showToast(`Regeneration failed: ${result.error}`, "error");
      return;
    }

    setPendingChange({
      phaseId: phase.phase_id,
      sectionKey,
      oldValue: phase[sectionKey],
      newValue: result.regenerated_section,
      summary: result.change_summary,
      confidence: result.confidence,
      verification: result.verification_note,
      feedback,
    });
    setRefineTarget(null);
  };

  const handleAcceptChange = () => {
    if (!pendingChange) return;
    const { phaseId, sectionKey, newValue, confidence, summary, feedback } = pendingChange;

    setData(prev => {
      const updated = JSON.parse(JSON.stringify(prev));
      const phase = updated.phases.find(p => p.phase_id === phaseId);
      if (phase) {
        phase[sectionKey] = newValue;
        if (confidence) phase.confidence = confidence;
      }
      return updated;
    });

    setChangedSections(prev => new Set([...prev, `${phaseId}:${sectionKey}`]));
    setHistory(prev => [{ phaseId, sectionKey, oldValue: pendingChange.oldValue, newValue, summary, confidence, feedback, status:"accepted", timestamp: Date.now() }, ...prev]);
    setPendingChange(null);
    showToast("Changes applied successfully");
  };

  const handleRejectChange = () => {
    if (!pendingChange) return;
    setHistory(prev => [{ phaseId:pendingChange.phaseId, sectionKey:pendingChange.sectionKey, summary:pendingChange.summary, status:"rejected", timestamp:Date.now() }, ...prev]);
    setPendingChange(null);
    showToast("Changes rejected", "info");
  };

  const handleRevert = (historyIdx) => {
    const entry = history[historyIdx];
    if (!entry || entry.status !== "accepted") return;
    setData(prev => {
      const updated = JSON.parse(JSON.stringify(prev));
      const phase = updated.phases.find(p => p.phase_id === entry.phaseId);
      if (phase) phase[entry.sectionKey] = entry.oldValue;
      return updated;
    });
    setChangedSections(prev => { const n = new Set(prev); n.delete(`${entry.phaseId}:${entry.sectionKey}`); return n; });
    const updatedHist = [...history];
    updatedHist[historyIdx] = { ...entry, status: "reverted" };
    setHistory(updatedHist);
    showToast("Change reverted");
  };

  const phases = data.phases;
  const phaseHasChanges = (pid) => [...changedSections].some(k => k.startsWith(pid + ":"));

  return (
    <div style={{ fontFamily:"'DM Sans','Segoe UI',sans-serif", background:"#FAFAFA", minHeight:"100vh", padding:"0 0 40px" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet"/>

      {/* Toast */}
      {toast && (
        <div style={{ position:"fixed", top:16, left:"50%", transform:"translateX(-50%)", zIndex:9999, padding:"10px 24px", borderRadius:8, fontSize:13, fontWeight:600, color:"#fff", boxShadow:"0 4px 20px rgba(0,0,0,0.15)", animation:"fadeIn 0.2s", background: toast.type==="error" ? "#D32F2F" : toast.type==="info" ? "#5C6BC0" : "#4CAF50" }}>
          <style>{`@keyframes fadeIn { from { opacity:0; transform:translateX(-50%) translateY(-8px); } to { opacity:1; transform:translateX(-50%) translateY(0); } }`}</style>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div style={{ background:"#fff", borderBottom:"1px solid #E0E0E0", padding:"24px 32px 18px" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
          <div>
            <h1 style={{ margin:0, fontSize:24, fontWeight:700, color:"#1A1A1A" }}>Patient journey mapping</h1>
            <p style={{ margin:"4px 0 0", fontSize:13, color:"#888" }}>Understanding patient realities to reveal unmet needs</p>
          </div>
          <div style={{ display:"flex", gap:8 }}>
            <button onClick={()=>setShowHistory(true)} style={{ background:"#F5F5F5", border:"1px solid #E0E0E0", borderRadius:8, padding:"8px 16px", fontSize:12, fontWeight:600, cursor:"pointer", color:"#555", display:"flex", alignItems:"center", gap:6 }}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="#666" strokeWidth="1.3"/><path d="M8 5v3.5l2.5 1.5" stroke="#666" strokeWidth="1.3" strokeLinecap="round"/></svg>
              History {history.length > 0 && <Badge bg="#7C4DFF" color="#fff">{history.length}</Badge>}
            </button>
          </div>
        </div>
        <div style={{ marginTop:10, display:"flex", alignItems:"center", gap:10 }}>
          <Badge bg="#E3F2FD" color="#1565C0" style={{ padding:"4px 14px", fontSize:13, borderRadius:14 }}>{data.disease}</Badge>
          <span style={{ fontSize:11, color:"#999" }}>{phases.length} phases · {phases.reduce((a,p)=>a+(p.evidence_claims?.length||0),0)} claims · {changedSections.size} refinement{changedSections.size!==1?"s":""}</span>
        </div>
      </div>

      {/* Phase arrows */}
      <div style={{ padding:"14px 32px 0", overflowX:"auto" }}>
        <div style={{ display:"flex", gap:0, minWidth:800 }}>
          {phases.map((p,i) => <PhaseArrow key={p.phase_id} color={PHASE_COLORS[p.phase_id].bg} label={PHASE_LABELS[p.phase_id]} isFirst={i===0} hasChanges={phaseHasChanges(p.phase_id)} onClick={()=>setSelectedPhase(p)} />)}
        </div>

        {/* Headlines + confidence */}
        <div style={{ display:"flex", minWidth:800, marginTop:8 }}>
          {phases.map(p => (
            <div key={p.phase_id} style={{ flex:1, textAlign:"center", padding:"4px 6px", cursor:"pointer" }} onClick={()=>setSelectedPhase(p)}>
              <div style={{ fontSize:11, fontWeight:600, color:PHASE_COLORS[p.phase_id].text, lineHeight:1.3 }}>{p.headline}</div>
              <div style={{ marginTop:4, display:"flex", justifyContent:"center", gap:4 }}>
                <ConfBadge level={p.confidence}/>
                {phaseHasChanges(p.phase_id) && <Badge bg="#EDE7F6" color="#7C4DFF" style={{ fontSize:8 }}>Refined</Badge>}
              </div>
            </div>
          ))}
        </div>

        {/* Feelings row */}
        <GridRow label="Feelings" color="#0288D1" phases={phases} changedSections={changedSections} sectionKey="feelings" onClickPhase={setSelectedPhase} renderCell={p => (
          <div style={{ display:"flex", flexWrap:"wrap", gap:2 }}>{p.feelings.map(f=><Pill key={f} text={f} color={PHASE_COLORS[p.phase_id].text}/>)}</div>
        )} />

        {/* Emotional arc */}
        <div style={{ display:"flex", marginTop:8, minWidth:800 }}>
          <RowLabel label="Moment" color="#F57C00"/>
          <div style={{ flex:1, background:"#fff", border:"1px solid #E8E8E8", borderRadius:"0 6px 6px 0", padding:"6px 0" }}>
            <EmotionalArcSVG phases={phases}/>
            <div style={{ display:"flex" }}>
              {phases.map((p,i) => (
                <div key={p.phase_id} style={{ flex:1, textAlign:"center", padding:"4px 6px", borderRight:i<phases.length-1?"1px solid #F0F0F0":"none", cursor:"pointer" }} onClick={()=>setSelectedPhase(p)}>
                  <div style={{ fontSize:10, fontWeight:600, color:"#333" }}>{p.moment.title}</div>
                  <div style={{ fontSize:9, color:"#999", marginTop:2 }}>{p.moment.description.slice(0,50)}…</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Mindset row */}
        <GridRow label="Mindset" color="#5C6BC0" phases={phases} changedSections={changedSections} sectionKey="mindset" onClickPhase={setSelectedPhase} renderCell={p => (
          <div style={{ fontStyle:"italic", fontSize:11, color:"#555", lineHeight:1.4, borderLeft:`2px solid ${PHASE_COLORS[p.phase_id].mid}`, paddingLeft:8 }}>{p.mindset}</div>
        )} />

        {/* Pain points row */}
        <GridRow label="Pain points" color="#C62828" phases={phases} changedSections={changedSections} sectionKey="pain_points" onClickPhase={setSelectedPhase} renderCell={p => (
          p.pain_points.map((pp,j) => (
            <div key={j} style={{ display:"flex", alignItems:"flex-start", gap:5, marginBottom:4 }}>
              <div style={{ width:7, height:7, borderRadius:"50%", background:SEVERITY_DOT[pp.severity]||"#999", marginTop:4, flexShrink:0 }}/>
              <div style={{ fontSize:10, lineHeight:1.3, color:"#444" }}>{pp.description}</div>
            </div>
          ))
        )} />

        {/* Evidence row */}
        <GridRow label="Evidence" color="#37474F" phases={phases} changedSections={changedSections} sectionKey="evidence_claims" onClickPhase={setSelectedPhase} renderCell={p => (
          <>
            <div style={{ display:"flex", gap:3, flexWrap:"wrap", marginBottom:4 }}>
              {[...new Set(p.evidence_claims?.map(c=>c.source_type))].map(t => <SrcBadge key={t} type={t}/>)}
            </div>
            <div style={{ fontSize:10, color:"#888" }}>
              {p.evidence_claims?.length||0} claims
              {p.gaps?.length > 0 && <span style={{ color:"#D32F2F", marginLeft:4 }}>· {p.gaps.length} gap{p.gaps.length>1?"s":""}</span>}
            </div>
          </>
        )} />
      </div>

      {/* Legend */}
      <div style={{ padding:"20px 32px 0", display:"flex", gap:16, flexWrap:"wrap" }}>
        <LegendBox title="Severity">
          <div style={{ display:"flex", gap:12 }}>
            {Object.entries(SEVERITY_DOT).map(([k,v]) => <div key={k} style={{ display:"flex", alignItems:"center", gap:4 }}><div style={{ width:8, height:8, borderRadius:"50%", background:v }}/><span style={{ fontSize:10, color:"#777", textTransform:"capitalize" }}>{k}</span></div>)}
          </div>
        </LegendBox>
        <LegendBox title="Sources">
          <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
            {["spine","web","fda_label","clinical_trial"].map(t => <SrcBadge key={t} type={t}/>)}
          </div>
        </LegendBox>
        <LegendBox title="Tip">
          <div style={{ fontSize:11, color:"#666" }}>Click any phase to view details. Use the <span style={{ color:"#7C4DFF", fontWeight:600 }}>Refine</span> button on any section to provide feedback and regenerate with AI.</div>
        </LegendBox>
      </div>

      {/* Panels and modals */}
      {selectedPhase && (
        <>
          <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.25)", zIndex:999 }} onClick={()=>setSelectedPhase(null)}/>
          <DetailPanel phase={selectedPhase} onClose={()=>setSelectedPhase(null)} onRefine={handleOpenRefine} changedSections={changedSections} />
        </>
      )}
      {refineTarget && (
        <RefineModal phase={refineTarget.phase} sectionKey={refineTarget.sectionKey} currentContent={refineTarget.phase[refineTarget.sectionKey]} onClose={()=>setRefineTarget(null)} onRegenerate={handleRegenerate} isLoading={isLoading} />
      )}
      {pendingChange && (
        <ChangesPanel change={pendingChange} onAccept={handleAcceptChange} onReject={handleRejectChange} onClose={()=>setPendingChange(null)} />
      )}
      {showHistory && (
        <>
          <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.2)", zIndex:1499 }} onClick={()=>setShowHistory(false)}/>
          <RevisionHistory history={history} onRevert={handleRevert} onClose={()=>setShowHistory(false)} />
        </>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   REUSABLE GRID ROW
   ═══════════════════════════════════════════════════════════════ */
function GridRow({ label, color, phases, changedSections, sectionKey, onClickPhase, renderCell }) {
  return (
    <div style={{ display:"flex", marginTop:8, minWidth:800 }}>
      <RowLabel label={label} color={color}/>
      <div style={{ display:"flex", flex:1, background:"#fff", border:"1px solid #E8E8E8", borderRadius:"0 6px 6px 0" }}>
        {phases.map((p,i) => {
          const changed = changedSections.has(`${p.phase_id}:${sectionKey}`);
          return (
            <div key={p.phase_id} style={{
              flex:1, padding:"10px 8px", borderRight:i<phases.length-1?"1px solid #F0F0F0":"none",
              cursor:"pointer", background: changed ? "#F8F4FF" : "transparent", transition:"background 0.3s",
              position:"relative",
            }} onClick={()=>onClickPhase(p)}>
              {changed && <div style={{ position:"absolute", top:4, right:4, width:6, height:6, borderRadius:"50%", background:"#7C4DFF" }}/>}
              {renderCell(p)}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function LegendBox({ title, children }) {
  return (
    <div style={{ flex:1, minWidth:160 }}>
      <div style={{ fontSize:10, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.1em", color:"#999", marginBottom:6 }}>{title}</div>
      <div style={{ background:"#fff", border:"1px solid #E8E8E8", borderRadius:8, padding:12 }}>{children}</div>
    </div>
  );
}
