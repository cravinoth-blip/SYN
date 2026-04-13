# Architecture

**Analysis Date:** 2026-04-13

## System Overview

This repository is a multi-product AI platform for Syneos Health, built around a shared Snowflake vector database and OpenAI APIs. It contains four distinct sub-systems that share infrastructure (Snowflake, OpenAI, a local `.venv`, and a root `.env`):

1. **RAG Chat API** (`app.py`) — the primary FastAPI service; ChatGPT-like interface with streaming, document upload, QC rules search, and a legacy Custom GPT `/query` endpoint.
2. **Patient Journey** (`Patient Journey/`) — Next.js frontend + FastAPI backend that orchestrates a 4-pass LLM pipeline to generate evidence-backed patient journey maps for a given disease.
3. **AI Platform** (`ai-platform/`) — React/Vite SPA for AI content generation from pharma strategy templates; separate Flask API (`api/server.py`) handles ingestion into a `STRATEGIC_WORKSPACE` Snowflake table.
4. **Questionnaire** (`Questionnaire/`) — standalone Flask app collecting advisory board questionnaire responses; stores responses in SQLite locally and PostgreSQL on Vercel.

Standalone utility scripts at the root serve additional purposes: `fact_checker.py` (FastAPI, port 8001), `chart_agent.py` (FastAPI LangGraph, port 8001), `knowledge_graph.py` and `knowledge_graph_amd.py` (offline graph builders), `etl_local.py` (local ETL helper shared by `app.py`), and `extract_mesh.py` / `read_publications.py` (Snowflake data utilities).

---

## Components

### 1. RAG Chat API — `app.py`

**Role:** Central knowledge-base service. Embeds queries, runs `VECTOR_COSINE_SIMILARITY()` on Snowflake, and streams GPT-4o-mini answers back to callers.

**Key responsibilities:**
- Lazy singleton Snowflake connection via private-key auth (`get_sf_conn()`)
- `retrieve_context()` — embed query → cosine similarity search against `RAG_DOCUMENTS`
- `retrieve_qc_rules()` — same pattern against `QC_RULES` (ASUNDEXIAN style guide)
- `/chat/stream` — SSE streaming chat with document library context
- `/chat/qc/stream` — SSE streaming chat with QC style-guide context
- `/chat/analyze` — upload a file, extract text via `etl_local.extract_file()`, cross-reference with Snowflake, stream analysis
- `/upload/stream` — full ETL ingest pipeline (extract → chunk → embed → insert into Snowflake) over SSE
- `/documents` (GET/DELETE) — document library CRUD
- `/query` — legacy JSON endpoint for OpenAI Custom GPT Actions
- `/status` — health/count check
- Serves a self-contained chat HTML UI (`HTML` string, rendered at `GET /`)
- Mounts `pptx_router` from `pptx_router.py` (deleted in latest git state, referenced via `from pptx_router import router`)

**Dependencies:** `etl_local.py` (imported inline), Snowflake connector, OpenAI SDK, FastAPI, uvicorn.

**Port:** 8000 (local), deployed to Render.

---

### 2. ETL Pipeline — `etl_local.py` + `ETL_Code_Dec.ipynb`

**Role:** Converts raw documents (PDF, DOCX, XLSX, JSON, TXT) into embedding vectors and inserts them into Snowflake.

**Pipeline steps:**
1. `extract_file()` — PyMuPDF for PDF, python-docx for DOCX, openpyxl for Excel
2. `chunk_text()` — `RecursiveCharacterTextSplitter` (1000–1500 chars, 100 overlap)
3. `extract_doi_from_pdf()` + `fetch_crossref_metadata()` — DOI lookup for academic papers
4. `extract_title_from_text()` / `generate_summary()` — gpt-4o-mini for AI-generated metadata
5. `client.embeddings.create()` — `text-embedding-3-small`, 1536 dims
6. Insert into Snowflake `RAG_DOCUMENTS` with `PARSE_JSON(%s)::VECTOR(FLOAT, 1536)`

`etl_local.py` is also imported at runtime by `app.py`'s `/upload/stream` and `/chat/analyze` endpoints.

---

### 3. Patient Journey Sub-System

**Components:**

| File | Role |
|------|------|
| `Patient Journey/app/` | Next.js 14 frontend (App Router) |
| `Patient Journey/app/src/app/page.tsx` | Input form: disease name + file uploads |
| `Patient Journey/app/src/app/journey/page.tsx` | Renders the journey map from `sessionStorage` |
| `Patient Journey/app/src/components/PatientJourneyMap.tsx` | Main visualization component |
| `Patient Journey/app/src/app/api/generate/route.ts` | Next.js Route Handler — proxies to Python backend at `BACKEND_URL` (default `http://localhost:8002`) |
| `Patient Journey/app/src/app/api/refine/route.ts` | Next.js Route Handler — proxies to Python backend for section regeneration |
| `Patient Journey/backend/main.py` | FastAPI app (port 8002) — file ingestion, Snowflake pre-fetch, pipeline dispatch |
| `Patient Journey/patient_journey_pipeline/` | 4-pass LLM pipeline package |

**4-Pass Pipeline (`orchestrator.py`):**

| Pass | Model | Output |
|------|-------|--------|
| Pass 1: Deep Generation | gpt-4o | `pass1_json` — all journey phases |
| Pass 2: Verification & Deepening | gpt-4o | `pass2_json` — confidence levels assigned |
| Pass 3: Artifact Construction | gpt-4o | `pass3_json` — Excel/CSV artifacts |
| Pass 4: Editorial Polish | gpt-4o | polished Markdown → `.docx` |

**Tools available to the pipeline (via `ToolHarness`):**
- `SnowflakeSearchTool` — keyword search against `COMPILE_ADD_ON.PUBMED_DETAILS.PUBLICATIONS`
- `SpineSearchTool` — ChromaDB local vector store (`data/chroma_spine/`)
- `WebSearchTool` — Tavily API
- `ClinicalTrialsTool` — ClinicalTrials.gov API (free)
- `FDALabellingTool` — openFDA API (free)
- `CodeInterpreterTool` — sandboxed Python exec
- `CISupplementsTool` — searches registered CI supplement files

---

### 4. AI Platform — `ai-platform/`

**Role:** React/Vite SPA for generating pharma strategy documents from 16 built-in templates. Manages compound portfolios and ingests strategy documents into a `STRATEGIC_WORKSPACE` Snowflake table.

**Frontend routes:**
- `/` → `TemplateLibrary` — browse 16 strategy templates
- `/generate/:templateId` → `ContentGenerator` — fill template fields, generate content (currently mock via `aiGenerator.ts`)
- `/knowledge` → `CompoundSelection` — pick a compound
- `/knowledge/:compoundId` → `KnowledgeBase` — upload and manage documents per compound
- `/integrations` → `SystemIntegrations` — manage external integration toggles

**Backend (`api/server.py`):** Flask app (port 5001), Vite dev server proxies `/api/*` to it.
- `POST /api/ingest` — extract, chunk (1500 chars/100 overlap), embed, upload to `STRATEGIC_WORKSPACE` Snowflake table
- Imports `etl_local.py` helpers from root RAG directory via `sys.path` manipulation

**Compound state:** Stored in `localStorage` via `src/app/data/compounds.ts`. Integration selections stored in `localStorage` via `src/app/data/integrations.ts`.

**Content generation:** `src/app/utils/aiGenerator.ts` is currently a local mock (no API call). All template outputs are hardcoded template strings. No backend call is wired up yet.

---

### 5. Questionnaire — `Questionnaire/`

**Role:** Flask web app for collecting advisory board survey responses.

**Stack:** Flask + Jinja2 templates, SQLite (local) / PostgreSQL (Vercel), deployed to Vercel via `vercel.json`.

**Entry point:** `Questionnaire/app.py`

---

### 6. Standalone Utility Scripts

| Script | Purpose | Port |
|--------|---------|------|
| `fact_checker.py` | FastAPI SSE app — extract claims from a document, verify each against ChromaDB, produce annotated PDF | 8001 |
| `chart_agent.py` | FastAPI + LangGraph — extract charts from PDF via PyMuPDF, analyze with GPT-4o vision, return structured insights | 8001 |
| `knowledge_graph.py` | Offline — load `output/embeddings.csv`, compute cosine similarity, produce D3.js HTML + GEXF | — |
| `knowledge_graph_amd.py` | Same as above, scoped to AMD (age-related macular degeneration) dataset | — |
| `extract_mesh.py` | Fetch MeSH ontology terms for Snowflake documents | — |
| `setup_snowflake.py` | One-time Snowflake schema setup | — |
| `upload_qc_rules.py` | ETL specifically for the `QC_RULES` table (ASU style guide CSV) | — |
| `check_snowflake.py` / `list_warehouses.py` | Snowflake diagnostic utilities | — |

---

## Data Flow

### RAG Query Flow (primary)

```
User → Browser/ChatGPT
  → POST /chat/stream (app.py, port 8000)
    → OpenAI text-embedding-3-small (embed query)
    → Snowflake VECTOR_COSINE_SIMILARITY() on RAG_DOCUMENTS
    → Retrieve top-k chunks (id, text, title, authors, doi, summary, similarity)
    → Build messages list with context
    → OpenAI gpt-4o-mini streaming completions
  ← SSE stream: {type: "sources"} then {type: "chunk", text} then {type: "done"}
← Browser renders streamed answer + citations
```

### Document Ingestion Flow

```
User → POST /upload/stream (multipart)
  → etl_local.extract_file() (PyMuPDF / python-docx / openpyxl)
  → etl_local.chunk_text() (RecursiveCharacterTextSplitter)
  → CrossRef API (DOI lookup if PDF)
  → gpt-4o-mini (title + summary generation)
  → OpenAI text-embedding-3-small (per chunk)
  → Snowflake INSERT with PARSE_JSON()::VECTOR(FLOAT, 1536)
← SSE progress events + final done event
```

### Patient Journey Generation Flow

```
User → Next.js page.tsx (disease + optional PDFs)
  → POST /api/generate (Next.js Route Handler)
    → POST http://localhost:8002/generate (Patient Journey backend)
      → extract_pdf_text() with GPT-4o Vision OCR fallback
      → ingest_spine() → ChromaDB local store
      → query_snowflake_tables() pre-fetch (fallback path)
      → PatientJourneyPipeline.run()
        → Pass 1: gpt-4o + ToolHarness (Snowflake/ChromaDB/Web/ClinicalTrials/FDA)
        → Pass 2: gpt-4o verification + confidence scoring
        → Pass 3: gpt-4o artifact construction (Excel/CSV)
        → Pass 4: gpt-4o editorial polish → .docx
      → _load_pipeline_result() → pass2_json preferred
  ← JSONResponse {disease, summary, phases[]}
← sessionStorage.setItem("journeyData", ...) → router.push("/journey")
← journey/page.tsx reads sessionStorage → renders PatientJourneyMap
```

### AI Platform Ingestion Flow

```
User → KnowledgeBase.tsx → FileUploadZone
  → POST /api/ingest (Flask, port 5001)
    → extract_text() (pymupdf / docx / openpyxl)
    → chunk_segments() (langchain RecursiveCharacterTextSplitter, 1500/100)
    → ai_title() + ai_summary() via gpt-4o-mini
    → embed() via text-embedding-3-small
    → Snowflake INSERT into STRATEGIC_WORKSPACE table
  ← JSON {chunks_uploaded, doc_id, title, ...}
```

---

## API Contracts

### `app.py` — RAG Chat API (port 8000)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/chat/stream` | `{message: str, history: [{role, content}], top_k: int=8}` | SSE: `{type:"sources", sources:[...]}` → `{type:"chunk", text}` → `{type:"done"}` |
| POST | `/chat/qc/stream` | Same as above | SSE same shape; sources are QC rules |
| POST | `/chat/analyze` | multipart: `file`, `message`, `history` (JSON str), `top_k` | SSE: `{type:"sources"}` → `{type:"chunk"}` → `{type:"done"}` |
| POST | `/upload/stream` | multipart: `file` | SSE: `{type:"progress", step, message, pct}` → `{type:"done", chunks_added, total_chunks, ...}` |
| GET | `/documents` | — | `{documents: [{source_file, title, authors, published, doi, summary, file_type, chunk_count}]}` |
| DELETE | `/documents/{source_file}` | path param | `{deleted: int, source_file, total_chunks}` |
| POST | `/query` | `{query_text: str, top_k: int=15}` | `{answer: str, context: [...]}` |
| GET | `/status` | — | `{status, chunks, vectors, table}` |
| GET | `/` | — | HTML (self-contained chat UI) |

### `Patient Journey/backend/main.py` — Patient Journey API (port 8002)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET | `/health` | — | `{status: "ok"}` |
| POST | `/generate` | multipart: `disease: str`, `tables: list[str]`, `files: list[UploadFile]` | `{disease, summary, phases: [{phase_id, headline, feelings, moment, mindset, pain_points, evidence_claims, unmet_needs, confidence, verification_notes, gaps}]}` |

### `ai-platform/api/server.py` — Strategy Tool API (port 5001)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/api/ingest` | multipart: `file`, `compound_id`, `compound_name`, `compound_generic_name`, `therapeutic_area`, `indication`, `compound_stage`, `category`, `subcategory`, `tags` | `{chunks_uploaded: int, doc_id, title, summary, ...}` |

### Next.js Route Handlers (`Patient Journey/app/src/app/api/`)

| Path | Purpose |
|------|---------|
| `POST /api/generate` | Thin proxy to `http://localhost:8002/generate` |
| `POST /api/refine` | Thin proxy to `http://localhost:8002/refine` for section-level regeneration |

---

## Key Design Decisions

**Single vector DB for all RAG:** Snowflake with `VECTOR(FLOAT, 1536)` column. `VECTOR_COSINE_SIMILARITY()` runs inside Snowflake SQL — no separate vector-DB service (Pinecone disabled, Chroma used only as a secondary local spine in the Patient Journey pipeline). This makes local development impossible without Snowflake credentials.

**SSE everywhere for long-running ops:** All document ingestion and chat endpoints in `app.py` return `StreamingResponse` with `text/event-stream` so the browser gets progress feedback during expensive embedding loops. The event shape is `{type: "progress"|"sources"|"chunk"|"done"|"error", ...}`.

**Multi-port microservice layout:** Each sub-product runs on its own port (8000 RAG, 8002 Patient Journey, 5001 AI Platform strategy, 8001 Fact Checker / Chart Agent). No API gateway or service mesh; frontends hardcode or env-configure the backend URLs.

**Private key auth for Snowflake:** All services use PEM private key (`private_key.pem` at root) rather than password auth. Three fallback paths: local file, base64 env var (`SNOWFLAKE_PRIVATE_KEY_B64`), raw PEM env var. This is re-implemented independently in each service.

**4-pass pipeline over tool-calling:** The Patient Journey pipeline uses OpenAI tool-calling (function calling) iteratively across four passes rather than a single agentic loop. Each pass has a bounded `MAX_TOOL_CALLS` and a dedicated system prompt and JSON schema.

**Content generation is mocked in AI Platform:** `ai-platform/src/app/utils/aiGenerator.ts` returns hardcoded template strings after a simulated 1500ms delay. The backend ingestion pipeline (`api/server.py`) is real and writes to Snowflake, but the generation step has no backend integration yet.

**Shared `etl_local.py` across services:** Both `app.py` and `ai-platform/api/server.py` reuse extraction and chunking logic from `etl_local.py` at the repository root. The AI Platform server adds the root to `sys.path` explicitly.

**Compound state in localStorage:** The AI Platform manages its compound portfolio entirely client-side via `localStorage`. There is no server-side user or session concept.
