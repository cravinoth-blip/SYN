"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [disease, setDisease] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const tables = ["COMPILE_ADD_ON", "PUBMED_DETAILS"];
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string | null>(null);

  const handleFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    setFiles((prev) => {
      const names = new Set(prev.map((f) => f.name));
      return [...prev, ...selected.filter((f) => !names.has(f.name))];
    });
  };

  const removeFile = (name: string) => setFiles((prev) => prev.filter((f) => f.name !== name));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!disease.trim()) return;

    setIsLoading(true);
    setError(null);
    setProgress("Connecting to Snowflake and embedding query...");

    try {
      const formData = new FormData();
      formData.append("disease", disease.trim());
      tables.forEach((t) => formData.append("tables", t));
      files.forEach((f) => formData.append("files", f));

      setProgress("Running 4-pass agentic pipeline (this takes 2–5 minutes)...");

      const resp = await fetch("/api/generate", {
        method: "POST",
        body: formData,
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ error: resp.statusText }));
        throw new Error(err.error || "Generation failed");
      }

      const journeyData = await resp.json();
      sessionStorage.setItem("journeyData", JSON.stringify(journeyData));
      router.push("/journey");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      setIsLoading(false);
      setProgress(null);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "linear-gradient(160deg, #0C1A2E 0%, #0A2540 45%, #0C2233 100%)", display: "flex", flexDirection: "column", fontFamily: "'Figtree','Noto Sans','Segoe UI',sans-serif" }}>
      {/* Header */}
      <div style={{ padding: "20px 40px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 38, height: 38, borderRadius: 10, background: "linear-gradient(135deg, #0891B2, #0E7490)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 4px 16px rgba(8,145,178,0.35)" }}>
            {/* Heart pulse icon */}
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M3 12h3l3-8 4 16 3-8h5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <div style={{ fontSize: 17, fontWeight: 700, color: "#fff", letterSpacing: "-0.01em" }}>Patient Journey Generator</div>
            <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginTop: 1, letterSpacing: "0.02em" }}>Powered by SYN10X · Snowflake + AI</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#10B981" }}/>
          <span style={{ fontSize: 11, color: "rgba(255,255,255,0.35)" }}>Connected</span>
        </div>
      </div>

      {/* Main content */}
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "48px 24px" }}>
        <div style={{ width: "100%", maxWidth: 580 }}>

          {/* Hero */}
          <div style={{ textAlign: "center", marginBottom: 44 }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "5px 14px", borderRadius: 20, background: "rgba(8,145,178,0.12)", border: "1px solid rgba(8,145,178,0.25)", marginBottom: 20 }}>
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="5" fill="#0891B2" opacity="0.8"/>
                <circle cx="8" cy="8" r="2.5" fill="#0891B2"/>
              </svg>
              <span style={{ fontSize: 11, fontWeight: 600, color: "#67E8F9", letterSpacing: "0.05em", textTransform: "uppercase" }}>AI-Powered · Evidence-Grounded</span>
            </div>
            <h1 style={{ margin: 0, fontSize: 38, fontWeight: 700, color: "#fff", letterSpacing: "-0.025em", lineHeight: 1.15 }}>
              Map any patient journey
            </h1>
            <p style={{ margin: "14px 0 0", fontSize: 16, color: "rgba(255,255,255,0.5)", lineHeight: 1.65 }}>
              Enter a disease name and select your evidence sources.<br/>
              The AI generates a multi-phase journey map grounded in clinical evidence.
            </p>
          </div>

          {/* Form card */}
          <form onSubmit={handleSubmit}>
            <div style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.09)", borderRadius: 16, padding: "32px 32px 28px", backdropFilter: "blur(24px)" }}>

              {/* Disease input */}
              <div style={{ marginBottom: 26 }}>
                <label style={{ display: "block", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "rgba(255,255,255,0.45)", marginBottom: 9 }}>
                  Disease / Indication
                </label>
                <input
                  type="text"
                  value={disease}
                  onChange={(e) => setDisease(e.target.value)}
                  placeholder="e.g. Systemic Lupus Erythematosus, Type 2 Diabetes, NSCLC..."
                  required
                  style={{
                    width: "100%", padding: "13px 16px", borderRadius: 10,
                    border: "1.5px solid rgba(255,255,255,0.1)",
                    background: "rgba(255,255,255,0.055)", color: "#fff",
                    fontSize: 15, outline: "none", boxSizing: "border-box",
                    transition: "border-color 0.2s, box-shadow 0.2s",
                    fontFamily: "inherit",
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = "#0891B2";
                    e.target.style.boxShadow = "0 0 0 3px rgba(8,145,178,0.15)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "rgba(255,255,255,0.1)";
                    e.target.style.boxShadow = "none";
                  }}
                />
              </div>

              {/* File upload */}
              <div style={{ marginBottom: 26 }}>
                <label style={{ display: "block", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "rgba(255,255,255,0.45)", marginBottom: 9 }}>
                  Supplemental Files <span style={{ color: "rgba(255,255,255,0.28)", fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>(optional — PDF, Excel / CSV)</span>
                </label>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    const dropped = Array.from(e.dataTransfer.files);
                    setFiles((prev) => {
                      const names = new Set(prev.map((f) => f.name));
                      return [...prev, ...dropped.filter((f) => !names.has(f.name))];
                    });
                  }}
                  style={{
                    border: "1.5px dashed rgba(255,255,255,0.13)", borderRadius: 10, padding: "22px 16px",
                    textAlign: "center", cursor: "pointer", transition: "border-color 0.2s, background 0.2s",
                    background: "rgba(255,255,255,0.02)",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(8,145,178,0.5)";
                    (e.currentTarget as HTMLDivElement).style.background = "rgba(8,145,178,0.04)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(255,255,255,0.13)";
                    (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.02)";
                  }}
                >
                  <input ref={fileInputRef} type="file" accept=".xlsx,.xls,.csv,.pdf" multiple onChange={handleFiles} style={{ display: "none" }} />
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" style={{ marginBottom: 8, opacity: 0.35 }}>
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="white" strokeWidth="1.5" strokeLinejoin="round"/>
                    <polyline points="14,2 14,8 20,8" stroke="white" strokeWidth="1.5" strokeLinejoin="round"/>
                    <line x1="12" y1="18" x2="12" y2="12" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                    <polyline points="9,15 12,12 15,15" stroke="white" strokeWidth="1.5" strokeLinejoin="round"/>
                  </svg>
                  <div style={{ fontSize: 13, color: "rgba(255,255,255,0.38)" }}>Drop files here or click to browse</div>
                  <div style={{ fontSize: 11, color: "rgba(255,255,255,0.22)", marginTop: 4 }}>.pdf · .xlsx · .xls · .csv</div>
                  <div style={{ fontSize: 10, color: "rgba(8,145,178,0.7)", marginTop: 4 }}>PDFs parsed with AI image-to-text (OCR)</div>
                </div>
                {files.length > 0 && (
                  <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
                    {files.map((f) => (
                      <div key={f.name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", background: "rgba(255,255,255,0.05)", borderRadius: 8, border: "1px solid rgba(255,255,255,0.07)" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="rgba(255,255,255,0.45)" strokeWidth="1.5"/></svg>
                          <span style={{ fontSize: 12, color: "rgba(255,255,255,0.65)" }}>{f.name}</span>
                          <span style={{ fontSize: 10, color: "rgba(255,255,255,0.28)" }}>{(f.size / 1024).toFixed(0)} KB</span>
                        </div>
                        <button type="button" onClick={() => removeFile(f.name)} style={{ background: "none", border: "none", color: "rgba(255,255,255,0.3)", cursor: "pointer", fontSize: 18, padding: "0 4px", lineHeight: 1, display: "flex", alignItems: "center" }}>
                          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Error */}
              {error && (
                <div style={{ marginBottom: 18, padding: "12px 16px", background: "rgba(220,38,38,0.12)", border: "1px solid rgba(220,38,38,0.25)", borderRadius: 9, fontSize: 13, color: "#FCA5A5", display: "flex", alignItems: "flex-start", gap: 10 }}>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0, marginTop: 1 }}><circle cx="8" cy="8" r="6" stroke="#FCA5A5" strokeWidth="1.4"/><path d="M8 5v3M8 10v.5" stroke="#FCA5A5" strokeWidth="1.4" strokeLinecap="round"/></svg>
                  {error}
                </div>
              )}

              {/* Progress */}
              {progress && (
                <div style={{ marginBottom: 18, padding: "12px 16px", background: "rgba(8,145,178,0.1)", border: "1px solid rgba(8,145,178,0.22)", borderRadius: 9, fontSize: 13, color: "#67E8F9", display: "flex", alignItems: "center", gap: 10 }}>
                  <Spinner color="#67E8F9" />
                  {progress}
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={isLoading || !disease.trim()}
                style={{
                  width: "100%", padding: "14px", borderRadius: 10, border: "none",
                  background: isLoading || !disease.trim()
                    ? "rgba(5,150,105,0.25)"
                    : "linear-gradient(135deg, #059669, #047857)",
                  color: "#fff", fontSize: 15, fontWeight: 700,
                  cursor: isLoading ? "wait" : !disease.trim() ? "not-allowed" : "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
                  fontFamily: "inherit", transition: "opacity 0.2s, transform 0.1s",
                  opacity: isLoading || !disease.trim() ? 0.55 : 1,
                  boxShadow: !isLoading && disease.trim() ? "0 4px 16px rgba(5,150,105,0.35)" : "none",
                }}
                onMouseEnter={(e) => { if (!isLoading && disease.trim()) (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-1px)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(0)"; }}
              >
                {isLoading ? (
                  <><Spinner color="#fff" /> Generating journey map...</>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <path d="M3 12h3l3-8 4 16 3-8h5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    Generate patient journey
                  </>
                )}
              </button>
            </div>
          </form>

          <p style={{ textAlign: "center", fontSize: 11, color: "rgba(255,255,255,0.18)", marginTop: 20, letterSpacing: "0.02em" }}>
            Pipeline runs locally · Snowflake evidence · GPT-4o generation · Claude refinement
          </p>
        </div>
      </div>
    </div>
  );
}

function Spinner({ color = "currentColor" }: { color?: string }) {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" style={{ animation: "spin 1s linear infinite", flexShrink: 0 }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <circle cx="8" cy="8" r="6" stroke={color} strokeWidth="2" fill="none" strokeDasharray="28" strokeDashoffset="8" strokeLinecap="round"/>
    </svg>
  );
}
