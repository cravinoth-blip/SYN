# Project Structure

**Analysis Date:** 2026-04-13

## Directory Layout

```
RAG/                                         # Repository root
├── app.py                                   # PRIMARY: FastAPI RAG Chat API (port 8000)
├── etl_local.py                             # Shared ETL helpers (imported by app.py + ai-platform)
├── ETL_Code_Dec.ipynb                       # Original Google Colab ETL notebook (reference)
├── requirements.txt                         # Root Python dependencies (app.py + etl)
├── .env                                     # Root secrets (Snowflake, OpenAI) — DO NOT commit
├── private_key.pem                          # Snowflake private key for local dev — DO NOT commit
├── render.yaml                              # Render.com deployment config for app.py
├── vercel.json                              # Vercel config (root-level, for Questionnaire?)
│
├── ai-platform/                             # AI Content Platform (React/Vite SPA)
│   ├── src/app/
│   │   ├── components/                      # Shared React components
│   │   │   ├── ui/                          # shadcn/ui primitives (button, card, badge, etc.)
│   │   │   ├── figma/                       # Figma-exported components
│   │   │   ├── FileCard.tsx                 # Uploaded document card
│   │   │   ├── GeneratedContentDisplay.tsx  # Renders generated template content
│   │   │   ├── Navigation.tsx               # Top nav bar
│   │   │   ├── FileUploadZone.tsx           # Drag-and-drop upload
│   │   │   ├── ParameterControls.tsx        # Tone/length/style pickers
│   │   │   └── ReferencesPanel.tsx          # Citation sidebar
│   │   ├── pages/
│   │   │   ├── Layout.tsx                   # Root layout (wraps all routes)
│   │   │   ├── TemplateLibrary.tsx          # Route: / — template browser
│   │   │   ├── ContentGenerator.tsx         # Route: /generate/:templateId
│   │   │   ├── CompoundSelection.tsx        # Route: /knowledge
│   │   │   ├── KnowledgeBase.tsx            # Route: /knowledge/:compoundId
│   │   │   └── SystemIntegrations.tsx       # Route: /integrations
│   │   ├── data/
│   │   │   ├── compounds.ts                 # Compound registry (localStorage-backed)
│   │   │   ├── integrations.ts              # Integration definitions (localStorage-backed)
│   │   │   ├── templates.ts                 # 16 strategy template definitions
│   │   │   └── knowledgeCategories.ts       # Document category taxonomy
│   │   ├── types/
│   │   │   ├── template.ts                  # Template + GenerationParams types (high-import)
│   │   │   ├── compound.ts                  # Compound type
│   │   │   └── knowledge.ts                 # KnowledgeFile type
│   │   └── utils/
│   │       └── aiGenerator.ts               # Template content generators (currently mocked)
│   ├── routes.ts                            # React Router config
│   ├── api/
│   │   └── server.py                        # Flask API (port 5001) — /api/ingest endpoint
│   ├── guidelines/                          # Content guidelines reference files
│   ├── vite.config.ts                       # Vite config (proxy /api → 5001, alias @→src)
│   ├── package.json                         # Node dependencies
│   └── .env / .gitignore                    # Per-app env and git config
│
├── Patient Journey/                         # Patient Journey Mapping sub-system
│   ├── app/                                 # Next.js 14 frontend
│   │   ├── src/app/
│   │   │   ├── page.tsx                     # Home: disease input + file upload form
│   │   │   ├── layout.tsx                   # Root layout
│   │   │   ├── journey/
│   │   │   │   └── page.tsx                 # Journey map display (reads sessionStorage)
│   │   │   └── api/
│   │   │       ├── generate/route.ts        # Proxy → http://localhost:8002/generate
│   │   │       └── refine/route.ts          # Proxy → http://localhost:8002/refine
│   │   ├── src/components/
│   │   │   └── PatientJourneyMap.tsx        # Main visualization component
│   │   ├── next.config.mjs
│   │   ├── package.json
│   │   └── .env.local / .env.local.example  # BACKEND_URL env var
│   ├── backend/                             # FastAPI Python backend
│   │   ├── main.py                          # FastAPI app (port 8002) — /generate, /health
│   │   └── .env / .env.example              # Backend secrets
│   └── patient_journey_pipeline/            # 4-pass LLM pipeline package
│       └── patient_journey_pipeline/        # Python package root
│           ├── orchestrator.py              # PatientJourneyPipeline class (main entry point)
│           ├── config.py                    # All env var reads + runtime constants
│           ├── audit/
│           │   └── logger.py                # AuditLogger — records all tool calls
│           ├── passes/
│           │   ├── pass1_generate.py        # Pass 1 system prompt + user message builder
│           │   ├── pass2_verify.py          # Pass 2 system prompt + user message builder
│           │   ├── pass3_artifacts.py       # Pass 3 system prompt + user message builder
│           │   └── pass4_polish.py          # Pass 4 system prompt + user message builder
│           ├── tools/
│           │   ├── __init__.py              # build_tool_harness() factory
│           │   ├── base.py                  # BaseTool + ToolHarness classes
│           │   ├── snowflake_search.py      # SnowflakeSearchTool (COMPILE_ADD_ON DB)
│           │   ├── spine_search.py          # SpineSearchTool (ChromaDB local)
│           │   ├── web_search.py            # WebSearchTool (Tavily API)
│           │   ├── clinical_trials.py       # ClinicalTrialsTool (clinicaltrials.gov)
│           │   ├── fda_labelling.py         # FDALabellingTool (openFDA)
│           │   ├── code_interpreter.py      # CodeInterpreterTool (sandboxed exec)
│           │   └── ci_supplements.py        # CISupplementsTool (Excel/CSV supplements)
│           ├── schema/
│           │   └── journey_schema.py        # JSON schema for journey output validation
│           ├── ingest_spine.py              # ChromaDB spine ingestion helper
│           └── quickstart.py               # CLI entrypoint
│
├── Questionnaire/                           # Advisory board questionnaire app
│   ├── app.py                               # Flask app (SQLite/PostgreSQL)
│   ├── templates/                           # Jinja2 HTML templates
│   ├── static/                              # CSS/JS assets
│   ├── api/                                 # Vercel serverless entry
│   ├── requirements.txt
│   └── vercel.json
│
├── fact_checker.py                          # Standalone FastAPI (port 8001) — claim verification
├── chart_agent.py                           # Standalone FastAPI + LangGraph (port 8001)
├── knowledge_graph.py                       # Offline: build D3 graph from embeddings.csv
├── knowledge_graph_amd.py                   # Same, scoped to AMD compound
├── etl_missing.py                           # Re-embed missing/failed documents
├── extract_mesh.py                          # MeSH ontology fetcher
├── upload_qc_rules.py                       # ETL for QC_RULES table
├── upload_to_snowflake.py                   # Generic CSV→Snowflake upload helper
├── setup_snowflake.py                       # One-time schema setup script
├── setup_snowflake.sql                      # Snowflake DDL for RAG_DOCUMENTS + QC_RULES
├── setup_strategic_workspace.sql            # Snowflake DDL for STRATEGIC_WORKSPACE
├── check_snowflake.py                       # Diagnostic: test connection
├── list_warehouses.py                       # Diagnostic: list available warehouses
├── test_query.py                            # Local curl-equivalent test script
├── read_publications.py                     # Read Snowflake publication data
│
├── documents/                               # Source PDFs for ETL ingestion (local, not committed)
├── output/                                  # ETL CSV output + pipeline run artifacts
├── chroma_db/                               # ChromaDB persistent store (fact_checker)
├── frontend/                                # Standalone Vite frontend (chart agent UI)
│
├── knowledge_graph.html/.json/.gexf         # Generated graph outputs (not committed ideally)
├── knowledge_graph_amd.html/.json/.gexf     # AMD graph outputs
├── ASU_StyleGuide_Rules_Final.csv           # Source data for QC_RULES table
├── rag_architecture.html                    # Architecture diagram (static HTML)
├── render.env                               # Render deployment env template
├── Example_Render.env                       # Env var template
├── runtime.txt                              # Python version for Render
│
├── .venv/                                   # Root Python virtual environment
├── .env                                     # Root secrets — never commit
├── private_key.pem                          # Snowflake PEM key — never commit
├── .planning/codebase/                      # GSD planning documents
└── .claude/                                 # Claude Code skills/config
```

---

## Module Boundaries

| Module | Owns | Must NOT touch |
|--------|------|----------------|
| `app.py` | RAG document chat, QC rules chat, document library CRUD, file-in-chat analysis, SSE streaming | Patient Journey pipeline, AI Platform template logic |
| `etl_local.py` | Text extraction, chunking, DOI lookup, title/summary generation, Snowflake insert helpers | No FastAPI concerns; pure functions only |
| `ai-platform/api/server.py` | Strategy document ingestion into `STRATEGIC_WORKSPACE` Snowflake table | RAG_DOCUMENTS table, app.py endpoints |
| `ai-platform/src/` | Compound management (localStorage), template browsing, content display | Direct Snowflake access (all via `/api/ingest`) |
| `Patient Journey/backend/main.py` | Pipeline dispatch, PDF OCR, file staging, Snowflake pre-fetch for fallback | Modifying `RAG_DOCUMENTS` or `STRATEGIC_WORKSPACE` |
| `patient_journey_pipeline/orchestrator.py` | 4-pass pipeline execution, tool coordination, audit logging | HTTP concerns; pure Python pipeline |
| `patient_journey_pipeline/tools/` | Individual tool implementations — each tool is self-contained | Cross-tool dependencies (tools call only `BaseTool` interface) |
| `Questionnaire/app.py` | Survey form rendering and response storage | Any Snowflake or OpenAI access |
| `fact_checker.py` | Claim extraction, ChromaDB lookup, annotated PDF generation | Snowflake (uses ChromaDB only) |
| `chart_agent.py` | PDF chart extraction, GPT-4o vision analysis, LangGraph state | Snowflake, ChromaDB |
| `knowledge_graph.py` | Offline graph computation from `output/embeddings.csv` | Any live API calls |

---

## Entry Points

| Sub-system | Entry Point | How to Run |
|-----------|-------------|-----------|
| RAG Chat API | `app.py` | `uvicorn app:app --host 0.0.0.0 --port 8000` |
| Patient Journey Frontend | `Patient Journey/app/` | `npm run dev` (Next.js, port 3000) |
| Patient Journey Backend | `Patient Journey/backend/main.py` | `uvicorn main:app --port 8002` |
| Patient Journey Pipeline (CLI) | `patient_journey_pipeline/quickstart.py` | `python quickstart.py --disease "..."` |
| AI Platform Frontend | `ai-platform/src/` | `npm run dev` (Vite, port 5173) |
| AI Platform API | `ai-platform/api/server.py` | `python api/server.py` (port 5001) |
| Questionnaire | `Questionnaire/app.py` | `flask run` or Vercel |
| Fact Checker | `fact_checker.py` | `uvicorn fact_checker:app --port 8001` |
| Chart Agent | `chart_agent.py` | `uvicorn chart_agent:app --port 8001` |
| ETL (batch) | `etl_local.py` (run as script) | `python etl_local.py` |
| Knowledge Graph | `knowledge_graph.py` | `python knowledge_graph.py` |
| Snowflake Setup | `setup_snowflake.py` | `python setup_snowflake.py` |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `.env` (root) | Snowflake credentials, OpenAI key — shared by `app.py`, `etl_local.py`, `fact_checker.py`, `chart_agent.py` |
| `private_key.pem` (root) | Snowflake RSA private key for all services that connect to Snowflake |
| `Patient Journey/backend/.env` | Patient Journey backend secrets (copies of root vars + `TAVILY_API_KEY`) |
| `Patient Journey/app/.env.local` | Next.js frontend env — only `BACKEND_URL=http://localhost:8002` |
| `ai-platform/.env` | AI Platform frontend/API secrets |
| `requirements.txt` (root) | Python deps for `app.py`, `etl_local.py`, utility scripts |
| `Patient Journey/backend/.venv/` | Separate venv for the Patient Journey backend |
| `.venv/` (root) | Root venv for app.py and utility scripts |
| `ai-platform/package.json` | Node deps for Vite/React SPA |
| `Patient Journey/app/package.json` | Node deps for Next.js app |
| `ai-platform/vite.config.ts` | Vite config — proxy `/api` → `http://localhost:5001`, alias `@` → `src/` |
| `Patient Journey/app/next.config.mjs` | Next.js config |
| `render.yaml` | Render.com deploy config for `app.py` |
| `Questionnaire/vercel.json` | Vercel deploy config for Questionnaire Flask app |
| `setup_snowflake.sql` | DDL: `RAG_DOCUMENTS` table with `VECTOR(FLOAT, 1536)` column |
| `setup_strategic_workspace.sql` | DDL: `STRATEGIC_WORKSPACE` table |
| `runtime.txt` | Python version pin for Render (`python-3.11.x`) |
| `Example_Render.env` | Template showing all required env vars for Render deployment |

---

## Where to Add New Code

**New RAG endpoint (e.g., a new chat mode):**
- Add handler to `app.py` following the SSE pattern of `/chat/stream`
- Retrieval logic (embedding + Snowflake): add a new `retrieve_*()` function at the top of `app.py`
- System prompt: define as a module-level `*_SYSTEM_PROMPT` constant in `app.py`

**New document type for ETL:**
- Add extraction logic inside `etl_local.extract_file()` in `etl_local.py`
- Add the extension to `ALLOWED_EXTS` in `app.py`

**New pipeline tool for Patient Journey:**
- Create `Patient Journey/patient_journey_pipeline/patient_journey_pipeline/tools/your_tool.py` extending `BaseTool`
- Register it in `tools/__init__.py` inside `build_tool_harness()`

**New AI Platform strategy template:**
- Add template definition to `ai-platform/src/app/data/templates.ts`
- Add corresponding generator function to `ai-platform/src/app/utils/aiGenerator.ts`

**New AI Platform page/route:**
- Add React component to `ai-platform/src/app/pages/`
- Register route in `ai-platform/src/app/routes.ts`
- Add navigation link in `ai-platform/src/app/components/Navigation.tsx`

**New Snowflake table:**
- Add DDL to a new `.sql` file at root
- Add `ALLOWED_TABLES` entry in `app.py` if it should be queryable via `/query`
- Add table registry entry in `Patient Journey/.../tools/snowflake_search.py` if the pipeline should search it

**New utility script:**
- Place at repository root alongside `fact_checker.py`, `knowledge_graph.py`, etc.
- Import shared helpers from `etl_local.py`; load credentials from root `.env`
