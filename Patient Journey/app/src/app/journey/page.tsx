"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import PatientJourneyMap, { type JourneyData } from "@/components/PatientJourneyMap";

export default function JourneyPage() {
  const router = useRouter();
  const [data, setData] = useState<JourneyData | null>(null);

  useEffect(() => {
    const stored = sessionStorage.getItem("journeyData");
    if (!stored) {
      router.replace("/");
      return;
    }
    try {
      setData(JSON.parse(stored));
    } catch {
      router.replace("/");
    }
  }, [router]);

  if (!data) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Figtree','Noto Sans','Segoe UI',sans-serif", background: "#F0F9FF" }}>
        <div style={{ textAlign: "center" }}>
          <svg width="32" height="32" viewBox="0 0 16 16" style={{ animation: "spin 1s linear infinite", marginBottom: 12 }}>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            <circle cx="8" cy="8" r="6" stroke="#0891B2" strokeWidth="2" fill="none" strokeDasharray="28" strokeDashoffset="8" strokeLinecap="round"/>
          </svg>
          <div style={{ fontSize: 14, color: "#64748B" }}>Loading journey...</div>
        </div>
      </div>
    );
  }

  return <PatientJourneyMap initialData={data} />;
}
