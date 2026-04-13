# Technology Stack

**Analysis Date:** 2026-04-13

## Languages

**Primary:**
- Python 3.11 - All backend services, ETL pipeline, utility scripts (declared in `runtime.txt`)
- TypeScript 5.x - AI platform frontend (`ai-platform/`), Patient Journey Next.js app (`Patient Journey/app/`)

**Secondary:**
- JavaScript (ES Module) - Vite config files, minor scripts
- SQL - Snowflake DDL/setup scripts (`setup_snowflake.sql`, `setup_strategic_workspace.sql`)

## Runtime

**Environment:**
- Python 3.11.0 (pinned in `runtime.txt`)
- Node.js (version not pinned; compatible with Vite 6 and Next.js 14)

**Package Manager:**
- Python: pip (no lockfile at project root; `requirements.txt` pins versions)
- Node: npm (lockfile present at `ai-platform/package-lock.json`; Patient Journey app uses npm)
- AI platform also supports pnpm overrides (declared in `ai-platform/package.json` under `pnpm.overrides`)

## Frameworks

**Backend — RAG Middleware:**
- FastAPI 0.135.1 - Main RAG API (`app.py`), served via `uvicorn 0.41.0`
- Pydantic 2.12.5 - Request/response validation in `app.py`

**Backend — AI Platform API:**
- Flask (version not pinned) + flask-cors - Local dev API server (`ai-platform/api/server.py`)
- Proxied to by Vite dev server on port 5001

**Backend — Patient Journey:**
- FastAPI 0.111.0 + uvicorn 0.30.1 - Patient Journey backend (`Patient Journey/backend/main.py`)

**Backend — Questionnaire:**
- Flask (>=2.3.0) - Questionnaire app (`Questionnaire/`)

**Frontend — AI Platform:**
- React 18.3.1 + React Router 7.13.0 - SPA (`ai-platform/src/`)
- Vite 6.3.5 - Build tool and dev server
- Tailwind CSS 4.1.12 - Utility-first styling via `@tailwindcss/vite` plugin
- MUI (Material UI) 7.3.5 + Emotion - Component library
- Radix UI (full suite, ~25 primitives) - Headless accessible components
- shadcn/ui patterns - Component composition on top of Radix

**Frontend — Patient Journey App:**
- Next.js 14.2.5 + React 18 - SSR/SSG app (`Patient Journey/app/`)
- TypeScript 5.x

**Frontend — RAG Chat UI (frontend/):**
- React 18.3.1 + React Router 7.13.0 - SPA (`frontend/src/`)
- Vite 6.3.5 - Build tool
- Tailwind CSS 4.1.12

## Key Libraries

**AI / Embeddings:**
- `openai==2.26.0` (root RAG) / `openai==1.35.7` (Patient Journey backend) - Embeddings (`text-embedding-3-small`) and chat completions (`gpt-4o`, `gpt-4o-mini`)
- `langchain-text-splitters==1.1.1` - Document chunking in ETL pipeline
- `langgraph>=0.2.0` + `langchain>=0.3.0` + `langchain-openai>=0.2.0` - Chart agent (`chart_agent.py`, `chart_requirements.txt`)
- `tiktoken>=0.7.0` - Token counting in Patient Journey pipeline

**Vector / Knowledge:**
- `chromadb>=0.5.0` - Local vector store (Patient Journey pipeline, `etl_chroma.py`)
- Snowflake `VECTOR(FLOAT, 1536)` - Primary vector store for RAG (cloud, not replaceable locally)

**Document Extraction:**
- `pymupdf==1.27.1` (root) / `PyMuPDF==1.24.5` (Patient Journey) - PDF text extraction + vision OCR fallback
- `python-docx==1.2.0` - DOCX extraction
- `openpyxl==3.1.5` - Excel extraction
- `python-pptx==1.0.2` - PowerPoint extraction

**Data:**
- `pandas==2.3.3` - Data manipulation in ETL and query scripts
- `requests==2.32.5` - HTTP calls (Crossref DOI enrichment, Tavily search)
- `tavily-python==0.3.3` - Web search tool for Patient Journey pipeline

**Snowflake:**
- `snowflake-connector-python==4.3.0` - Snowflake client
- `cryptography==46.0.5` - PEM private key parsing for Snowflake key-pair auth

**Questionnaire:**
- `psycopg2-binary>=2.9.0` - PostgreSQL client
- `reportlab>=4.0.0` - PDF report generation

**Frontend UI:**
- `recharts 2.15.2` - Charts in React UIs
- `lucide-react 0.487.0` - Icon library
- `motion 12.23.24` - Animation
- `react-hook-form 7.55.0` - Form state management
- `jspdf 4.2.1` + `html2canvas 1.4.1` - PDF export in Patient Journey app
- `jszip 3.10.1` - ZIP file creation
- `react-dnd 16.0.1` - Drag-and-drop
- `date-fns 3.6.0` - Date utilities

## Build & Dev Tools

**Bundler:**
- Vite 6.3.5 (`ai-platform/`, `frontend/`) - with `@vitejs/plugin-react`
- Next.js 14.2.5 build pipeline (`Patient Journey/app/`)

**Type Checking:**
- TypeScript 5.8.3 (`frontend/`) / TypeScript ^5 (`Patient Journey/app/`)

**Linting:**
- `next lint` available in Patient Journey app (Next.js ESLint preset)
- No ESLint or Prettier config detected at root or in `ai-platform/`

**Python Environment:**
- `.venv/` virtual environments present at root and in `Patient Journey/backend/`
- Dependencies managed via `requirements.txt` files (no Poetry or Pipenv)

**Notebook:**
- Jupyter (`ETL_Code_Dec.ipynb`) - Original ETL pipeline, originally written for Google Colab

## Package Managers

**Python:**
- pip — lock via pinned versions in `requirements.txt` files
- No `Pipfile` or `pyproject.toml` at project level

**Node:**
- npm — `ai-platform/package-lock.json` present (committed)
- pnpm override support declared in `ai-platform/package.json` but npm is primary

---

*Stack analysis: 2026-04-13*
