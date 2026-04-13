"""
Patient Journey Pipeline — FastAPI backend
Handles: file ingestion → Snowflake evidence retrieval → 4-pass generation → JSON output
"""

import os
import sys
import io
import json
import base64
import tempfile
import shutil
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

# Force UTF-8 stdout/stderr so pipeline unicode output doesn't crash on Windows
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add pipeline package to path
PIPELINE_DIR = Path(__file__).parent.parent / "patient_journey_pipeline" / "patient_journey_pipeline"
sys.path.insert(0, str(PIPELINE_DIR))

from snowflake_client import query_snowflake_tables

# Minimum characters of extracted text per page before falling back to vision OCR
_OCR_THRESHOLD = 80


def extract_pdf_text(pdf_path: str) -> str:
    """
    Extract text from a PDF file.

    Strategy:
    1. Use PyMuPDF to extract embedded text from each page (fast, free).
    2. If a page yields fewer than _OCR_THRESHOLD characters (scanned/image page),
       render it to a PNG image and send it to GPT-4o Vision to extract the text.
    3. Return all page texts joined by newlines.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("WARNING: PyMuPDF not installed — PDF text extraction unavailable.")
        return ""

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"WARNING: Could not open PDF {pdf_path}: {e}")
        return ""

    openai_client = None
    page_texts: list[str] = []

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text().strip()

        if len(text) >= _OCR_THRESHOLD:
            page_texts.append(text)
        else:
            # Scanned or image-heavy page — fall back to GPT-4o Vision
            try:
                if openai_client is None:
                    from openai import OpenAI
                    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

                # Render page at 150 DPI to PNG bytes
                mat = fitz.Matrix(150 / 72, 150 / 72)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                img_b64 = base64.b64encode(img_bytes).decode()

                resp = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "Extract all text from this document page exactly as it appears. "
                                        "Preserve headings, bullet points, and table content. "
                                        "Return only the extracted text with no commentary."
                                    ),
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                                },
                            ],
                        }
                    ],
                    max_tokens=2000,
                )
                ocr_text = (resp.choices[0].message.content or "").strip()
                if ocr_text:
                    page_texts.append(f"[Page {page_num} — OCR]\n{ocr_text}")
                else:
                    print(f"INFO: GPT-4o Vision returned no text for page {page_num} of {pdf_path}")
            except Exception as e:
                print(f"WARNING: Vision OCR failed for page {page_num} of {pdf_path}: {e}")

    doc.close()
    return "\n\n".join(page_texts)

app = FastAPI(title="Patient Journey API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate")
async def generate_journey(
    disease: str = Form(...),
    tables: list[str] = Form(default=["COMPILE_ADD_ON", "PUBMED_DETAILS"]),
    files: list[UploadFile] = File(default=[]),
):
    """
    Main generation endpoint.
    1. Save uploaded files to a temp dir
    2. Ingest files into ChromaDB spine (via pipeline's spine_search tool)
    3. Query Snowflake tables for disease-relevant evidence
    4. Run 4-pass pipeline
    5. Return JSON
    """
    tmp_dir = tempfile.mkdtemp(prefix="pj_")
    try:
        # ── 1. Save uploaded files ───────────────────────────────────
        saved_files = []
        for upload in files:
            if not upload.filename:
                continue
            dest = Path(tmp_dir) / upload.filename
            content = await upload.read()
            dest.write_bytes(content)

            if upload.filename.lower().endswith(".pdf"):
                # Extract text (with GPT-4o Vision OCR fallback for scanned pages)
                print(f"Extracting text from PDF: {upload.filename}")
                pdf_text = extract_pdf_text(str(dest))
                if pdf_text.strip():
                    txt_path = dest.with_suffix(".txt")
                    txt_path.write_text(pdf_text, encoding="utf-8")
                    saved_files.append(str(txt_path))
                    print(f"  → Extracted {len(pdf_text)} chars, saved as {txt_path.name}")
                else:
                    print(f"  → No text extracted from {upload.filename}, skipping.")
            else:
                saved_files.append(str(dest))

        # ── 2. Ingest uploaded files into ChromaDB spine (optional supplements)
        if saved_files:
            try:
                from tools.spine_search import ingest_spine
                ingest_spine(saved_files)
            except Exception as e:
                print(f"WARNING: Spine ingestion failed: {e}")

        # ── 3. Pre-fetch Snowflake passages for fallback generation only ─────
        # The pipeline's SnowflakeSearchTool queries Snowflake directly during
        # each pass; this pre-fetch is kept only for the GPT-4o fallback path.
        snowflake_passages = query_snowflake_tables(disease, tables, top_k=30)
        if snowflake_passages:
            print(f"Pre-fetched {len(snowflake_passages)} Snowflake passages for fallback.")

        # ── 4. Run the 4-pass pipeline ───────────────────────────────
        try:
            from orchestrator import PatientJourneyPipeline
            pipeline = PatientJourneyPipeline()
            result = pipeline.run(
                disease=disease,
                supplements=saved_files,
            )

            # Load the generated JSON from the deliverable or use result directly
            journey_json = _load_pipeline_result(result, disease)
            # If pipeline produced no phases, fall back to direct GPT-4o generation
            if not journey_json.get("phases"):
                print("Pipeline returned no phases. Falling back to direct generation.")
                journey_json = await _generate_with_openai(disease, snowflake_passages)
        except ImportError as e:
            print(f"Pipeline import failed: {e}. Falling back to direct generation.")
            journey_json = await _generate_with_openai(disease, snowflake_passages)
        except Exception as e:
            print(f"Pipeline execution failed: {e}. Falling back to direct generation.")
            journey_json = await _generate_with_openai(disease, snowflake_passages)

        return JSONResponse(content=journey_json)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _load_pipeline_result(result, disease: str) -> dict:
    """Extract JSON from the pipeline result object."""
    # The pipeline returns a result with .deliverable (docx path) and .artifacts
    # The Pass 2 output (verify pass) is the structured JSON we want
    output_dir = Path("./output")

    # Look for a pass2 JSON file
    for json_file in sorted(output_dir.glob("**/*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(json_file.read_text())
            if "phases" in data:
                return data
        except Exception:
            pass

    # Fallback — build minimal structure from result
    return {
        "disease": disease,
        "summary": "Pipeline completed. See downloadable report.",
        "phases": [],
        "assumptions": [],
    }


async def _generate_with_openai(disease: str, passages: list[dict]) -> dict:
    """
    Direct GPT-4o generation fallback (when pipeline is not fully configured).
    Generates a structured patient journey JSON from Snowflake evidence.
    """
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

    evidence_text = "\n\n".join(
        f"[{p['source']}] {p['text'][:800]}" for p in passages[:25]
    ) or "No specific evidence retrieved. Generate based on clinical knowledge."

    system_prompt = """You are an expert patient journey analyst for pharmaceutical strategy with 20+ years of experience in oncology, immunology, and rare disease.

Generate a deeply detailed, evidence-grounded patient journey map as structured JSON. This deliverable is used by medical affairs and commercial teams at top-10 pharma companies — it must be specific, nuanced, and clinically rich.

CRITICAL DEPTH REQUIREMENTS — do NOT produce shallow content:

1. **headline**: A single sharp insight that a pharma executive would find surprising or actionable. Not generic.

2. **feelings**: 5–7 distinct emotions with brief context (e.g. "Denial — patients often minimise early symptoms as stress-related"). Not just emotion words.

3. **moment**: A vivid, specific narrative of 4–5 sentences. Name the clinical setting, the conversation, the turning point. Include a specific quote in the description that captures the emotional reality.

4. **mindset**: 3–4 sentences of internal monologue. Should feel like a real patient voice — specific fears, questions, coping strategies. Not generic.

5. **pain_points**: 5–7 pain points per phase. Each must be:
   - Highly specific (not "lack of support" — say exactly what is missing, who should provide it, and what the consequence is)
   - Stakeholder-attributed (PCP, Specialist, Insurer, Pharma, Health System, Caregiver)
   - Severity-rated: critical / high / moderate / low

6. **evidence_claims**: 5–7 evidence-backed claims per phase with specific statistics, trial names, registry data, or guideline references. Include actual numbers where possible (e.g. "Median time to diagnosis is 4.7 years — NORD 2022"). Never vague.

7. **unmet_needs**: 5–6 strategic unmet needs per phase framed as opportunity statements for pharma/health system intervention.

8. **gaps**: 3–4 specific evidence gaps that a real-world evidence team or medical affairs function should address.

9. **verification_notes**: 2–3 sentences assessing the evidence quality for this phase — what is robust, what is thin.

The JSON must have this exact structure:
{
  "disease": "<disease name>",
  "summary": "<4-5 sentence strategic overview covering the defining experience of each phase and the most critical intervention opportunity>",
  "phases": [
    {
      "phase_id": "presentation|diagnosis|treatment|re_diagnosis|tx_adaptation|living_with",
      "headline": "<sharp, specific, insight-driven headline>",
      "feelings": ["<emotion — context>", ...],
      "moment": {
        "title": "<vivid moment title>",
        "description": "<4-5 sentence immersive narrative with specific clinical detail and a patient quote>",
        "emotional_arc": "rising|falling|stable|volatile"
      },
      "mindset": "<3-4 sentences of authentic internal monologue>",
      "pain_points": [
        {"description": "<specific, actionable pain point>", "stakeholder": "<who must act>", "severity": "critical|high|moderate|low"}
      ],
      "evidence_claims": [
        {"claim": "<specific stat/finding with numbers>", "source": "<source name>", "source_type": "web|spine|fda_label|clinical_trial|model_inference"}
      ],
      "unmet_needs": ["<strategic opportunity statement>", ...],
      "confidence": "HIGH|MEDIUM|LOW",
      "verification_notes": "<2-3 sentences on evidence quality>",
      "gaps": ["<specific RWE or primary research gap>", ...]
    }
  ],
  "assumptions": ["<explicit assumption with reasoning>", ...]
}

Include all 6 phases in order: presentation, diagnosis, treatment, re_diagnosis, tx_adaptation, living_with.
Tag evidence_claims from the provided passages as source_type "pubmed". For each pubmed claim, include the DOI in the source field if known (format: "Author et al. YYYY — doi:10.XXXX/XXXXX"). Use "web" for external epidemiology/guidelines, "model_inference" only as last resort."""

    user_msg = f"""Generate a deeply detailed patient journey for: **{disease}**

Evidence retrieved from the knowledge base (use these as primary sources — tag as source_type "pubmed", include DOI in source field where known):
{evidence_text}

Supplement with your clinical knowledge for epidemiology, guidelines, and treatment standards (tag as "web" or "clinical_trial").

Return ONLY valid JSON matching the schema above. Be specific. Be detailed. Do not generalise."""

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=16000,
        temperature=0.4,
        response_format={"type": "json_object"},
    )

    raw = resp.choices[0].message.content or "{}"
    return json.loads(raw)
