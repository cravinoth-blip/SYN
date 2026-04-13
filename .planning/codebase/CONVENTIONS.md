# Code Conventions

**Analysis Date:** 2026-04-13

## Naming Conventions

**Python files and modules:**
- `snake_case` for all files: `etl_local.py`, `etl_chroma.py`, `fact_checker.py`, `knowledge_graph.py`
- `snake_case` for functions: `extract_pdf_text()`, `get_sf_conn()`, `_load_private_key()`, `_parse_env()`
- Private/internal helpers prefixed with underscore: `_sf_conn`, `_parse_env()`, `_load_pipeline_result()`, `_generate_with_openai()`
- Module-level constants in `UPPER_SNAKE_CASE`: `TABLE_NAME`, `QC_RULES_TABLE`, `OPENAI_API_KEY`, `CHROMA_PERSIST_DIR`
- Config variables in `UPPER_SNAKE_CASE` throughout `config.py`: `MODEL_GENERATION`, `MAX_TOKENS_PER_PASS`, `TOP_K_RESULTS`

**TypeScript/React files:**
- `PascalCase` for component files and component names: `PatientJourneyMap.tsx`, `Navigation.tsx`, `ContentGenerator.tsx`
- `camelCase` for utility files: `routes.ts`, `compounds.ts`, `integrations.ts`
- `camelCase` for hooks and handlers: `handleSubmit`, `handleGenerate`, `handleFiles`, `removeFile`
- `PascalCase` for interfaces and types: `KnowledgeFile`, `KnowledgeCategory`, `PainPoint`, `EvidenceClaim`, `Phase`, `JourneyData`
- Named exports for utility components (`export function Navigation()`); default exports for pages (`export default function ContentGenerator()`)

**Snowflake schema:**
- Table names: `UPPER_SNAKE_CASE` — `RAG_DOCUMENTS`, `QC_RULES`, `COMPILE_ADD_ON`, `PUBMED_DETAILS`
- Column names: `UPPER_SNAKE_CASE` — `SIMILARITY`, `TITLE`, `SOURCE_FILE`, `PAGE_REFERENCE`

## Code Style

**Python:**
- No linting config files detected (no `.flake8`, `pyproject.toml`, `setup.cfg` in root)
- Multi-import lines used in some scripts: `import os, json, re, csv, logging, time` (`etl_local.py`)
- Standard library imports grouped, then third-party, but not always separated by blank line
- Module-level docstrings are common in all FastAPI files (`app.py`, `Patient Journey/backend/main.py`, pipeline modules)
- Type hints used consistently in newer pipeline code: `list[str]`, `dict`, `Optional`, `-> str`, `-> dict`
- f-strings used exclusively for string formatting (no `.format()` or `%`)

**TypeScript/React:**
- No `.eslintrc`, no Prettier config detected — no enforced formatting toolchain
- `"use client"` directive at top of Next.js client components (`page.tsx`, `PatientJourneyMap.tsx`)
- Strict TypeScript enabled in Next.js tsconfig: `"strict": true`
- Path alias `@` maps to `./src` in both Next.js and Vite configs
- Tailwind CSS 4 used for styling in `ai-platform/`; inline style objects used in `PatientJourneyMap.tsx`
- `useState` and `useEffect` are the primary hooks; no Redux or Zustand detected
- React Router v7 (`react-router`) used in `ai-platform/`; Next.js App Router in `Patient Journey/app/`

**Vite config (`ai-platform/vite.config.ts`):**
- Proxy: `/api` → `http://localhost:5001`
- Asset include: `**/*.svg`, `**/*.csv`
- Path alias: `@` → `./src`

## Patterns Used

**Python — FastAPI pattern:**
- Module-level singleton connection variables with lazy initialisation: `_sf_conn = None` then `get_sf_conn()` checks and reconnects
- Try/except around heavy optional imports at module top, with `AVAILABLE` boolean flags: `CRYPTO_AVAILABLE`, `SNOWFLAKE_AVAILABLE`, `PANDAS_AVAILABLE`
- Endpoint functions use `async def` for I/O-bound routes; helper functions use `def`
- `try/finally` blocks to guarantee cleanup of temp directories: `finally: shutil.rmtree(tmp_dir, ignore_errors=True)`
- Fallback chain pattern: pipeline → pass2_json → pass1_json → direct OpenAI generation

**Python — Pipeline pattern (Patient Journey):**
- `@dataclass` for result containers: `PipelineResult` in `orchestrator.py`
- Config module validates itself at import time — raises `ValueError`/`RuntimeError` on bad config (`config.py`)
- `_require(name)` / `_optional(name, default)` pattern for env var access
- Numbered comment banners for major code sections: `# ── 1. Save uploaded files ───`, `# ── 2. Ingest...`

**TypeScript — React pattern:**
- Local component state only; no global state management library
- `sessionStorage` used for cross-page data transfer (`journeyData` passed from home to journey page)
- Form submission via `fetch` with `FormData` (multipart); JSON APIs for other endpoints
- Error handling via `try/catch` with state updates: `setError(msg)`
- Constants defined as `Record<string, ...>` objects at module top: `PHASE_COLORS`, `PHASE_LABELS`, `CONFIDENCE_BADGE`

**Module organisation in `ai-platform/`:**
- `src/app/pages/` — full page components (one per route)
- `src/app/components/` — shared UI components; `src/app/components/ui/` — shadcn/ui primitives
- `src/app/data/` — static data and mock data: `compounds.ts`, `templates`, `integrations.ts`
- `src/app/types/` — TypeScript interfaces: `knowledge.ts`, `template.ts`
- `src/app/utils/` — utility functions: `aiGenerator`

## Error Handling

**Python:**
- `try/except Exception as e` with `print(f"WARNING: ...")` or `print(f"INFO: ...")` for non-fatal errors — no structured logging in ETL scripts
- `logging` module used in `ai-platform/api/server.py`: `logging.basicConfig(level=logging.INFO)` + `log = logging.getLogger(__name__)`
- FastAPI endpoints return `JSONResponse` for success; raise `HTTPException` in `app.py` for 4xx errors
- Pipeline passes catch `ImportError` and generic `Exception` separately and fall back gracefully — never crash the endpoint
- `_require()` in `config.py` raises `RuntimeError` at import time for missing env vars (fail-fast on startup)

**TypeScript:**
- `try/catch` with `err instanceof Error ? err.message : String(err)` pattern for type-safe error messages
- `toast.error(...)` / `toast.success(...)` via `sonner` for user-facing feedback
- `response.ok` check before parsing JSON; fallback: `.catch(() => ({ error: resp.statusText }))`
- No global error boundary component detected

## Comments and Documentation

**Python docstrings:**
- Module-level triple-quoted docstrings describe the file's purpose and usage in all backend files
- Function docstrings use plain prose (no NumPy/Google/Sphinx style enforced): `"""Extract text from a PDF file.\n\nStrategy:\n1. ..."""`
- `Args:` / `Returns:` blocks used in newer pipeline code (`orchestrator.py`); absent in older ETL scripts
- Inline `# ── Section name ──` divider comments using em-dashes for visual separation of major sections

**TypeScript:**
- Section comments use `/* ═══ TYPES ═══ */` box-style dividers (PatientJourneyMap.tsx)
- Minimal inline comments; JSDoc not used
- Vite config has inline explanatory comments for non-obvious settings: `// Never add .css, .tsx, or .ts files to this.`

**General:**
- No auto-generated API docs (no Swagger customisation beyond FastAPI defaults)
- `# TODO` comments present in `CLAUDE.md` as a checklist, not inline in code
