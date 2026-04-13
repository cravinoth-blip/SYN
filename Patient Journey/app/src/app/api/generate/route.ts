import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8002";

export async function POST(req: NextRequest) {
  try {
    // Forward the multipart form data directly to the Python backend
    const formData = await req.formData();

    const backendResp = await fetch(`${BACKEND_URL}/generate`, {
      method: "POST",
      body: formData,
      // Do NOT set Content-Type — let fetch set multipart boundary automatically
    });

    if (!backendResp.ok) {
      const text = await backendResp.text();
      return NextResponse.json(
        { error: `Backend error ${backendResp.status}: ${text}` },
        { status: backendResp.status }
      );
    }

    const data = await backendResp.json();
    return NextResponse.json(data);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    // If the backend is not running, give a clear message
    if (msg.includes("ECONNREFUSED") || msg.includes("fetch failed")) {
      return NextResponse.json(
        { error: "Cannot connect to the Python backend. Is it running on port 8002? Run: cd backend && uvicorn main:app --port 8002" },
        { status: 503 }
      );
    }
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
