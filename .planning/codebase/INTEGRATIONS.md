# External Integrations

**Analysis Date:** 2026-04-13

## APIs & External Services

**OpenAI:**
- Used for: text embeddings (`text-embedding-3-small`, 1536 dims), chat completions (`gpt-4o`, `gpt-4o-mini`), vision OCR fallback on scanned PDFs
- SDK: `openai` Python package (v2.26.0 root, v1.35.7 Patient Journey)
- Auth: `OPENAI_API_KEY` environment variable
- Called from: `app.py`, `ai-platform/api/server.py`, `Patient Journey/backend/main.py`, `etl_local.py`, `chart_agent.py`, `fact_checker.py`

**Tavily Search:**
- Used for: web search within the Patient Journey pipeline passes
- SDK: `tavily-python` (>=0.3.3)
- Auth: requires `TAVILY_API_KEY` (not in root `.env` template but imported in pipeline)
- Called from: `Patient Journey/backend/main.py`, `Patient Journey/patient_journey_pipeline/patient_journey_pipeline/`

**Crossref (REST API):**
- Used for: DOI/metadata enrichment during ETL
- Client: raw `requests` library (no dedicated SDK)
- Auth: unauthenticated (public API)
- Called from: ETL pipeline scripts

**Pinecone:**
- Status: present in `Example_Render.env` (`PINECONE_API_KEY`) but disabled in local dev and current `requirements.txt`
- Not actively used in current codebase; referenced only in legacy `.env` template

## Auth

**Snowflake — Private Key Auth:**
- Method: RSA key-pair authentication (no password)
- Key file: `private_key.pem` at project root (used in local dev)
- Cloud fallback: base64-encoded PEM stored as `SNOWFLAKE_PRIVATE_KEY_B64` env var (used on Render)
- Legacy fallback: raw PEM string in `SNOWFLAKE_PRIVATE_KEY` env var
- Passphrase: `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` env var
- Implementation: `cryptography` library parses the PEM; `snowflake-connector-python` connects with the DER-encoded private key bytes
- Auth code: `app.py` (`_load_private_key()`), `ai-platform/api/server.py` (`get_snowflake_conn()`)

**OpenAI:**
- Method: API key via `OPENAI_API_KEY` env var
- No OAuth or user-level auth

**No user-facing auth system detected** — the application has no login, session management, or user identity layer.

## Databases & Storage

**Snowflake (Primary Vector + Relational Store):**
- Role: Vector similarity search via `VECTOR_COSINE_SIMILARITY()` on `VECTOR(FLOAT, 1536)` columns; also stores document chunks and metadata
- Tables: `RAG_DOCUMENTS`, `QC_RULES`, `STRATEGIC_WORKSPACE` (and per-compound variants)
- Connection vars: `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA`
- Client: `snowflake-connector-python`
- Setup scripts: `setup_snowflake.sql`, `setup_snowflake.py`, `setup_strategic_workspace.sql`

**ChromaDB (Local Vector Store — Patient Journey):**
- Role: Alternative/local vector store used by `etl_chroma.py` and the Patient Journey pipeline
- SDK: `chromadb` (>=0.5.0)
- Persistence: local filesystem (no remote server configured)
- Used from: `Patient Journey/patient_journey_pipeline/`, `etl_chroma.py`

**PostgreSQL (Questionnaire App):**
- Role: Survey/questionnaire data storage
- Client: `psycopg2-binary`
- Connection: not exposed via env template in root; scoped to `Questionnaire/`

**Local Filesystem:**
- Document source folder: `documents/` (to be created locally)
- Temp file handling: Python `tempfile` module for uploaded files in `app.py`
- Knowledge graph outputs: `.gexf`, `.json`, `.html` files at project root

## Infrastructure

**Hosting — Backend (RAG API):**
- Platform: Render.com
- Config: `render.yaml` — web service, Python runtime, starts with `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Plan: starter
- Build command: `pip install -r requirements.txt`

**Hosting — Frontend (AI Platform):**
- Platform: Vercel
- Config: `vercel.json` — builds `ai-platform/` with `npm run build`, outputs to `ai-platform/dist/`, SPA rewrite rule
- Build command: `cd ai-platform && npm install && npm run build`

**Local Development:**
- RAG backend: `uvicorn app:app --host 0.0.0.0 --port 8000`
- AI Platform API (Flask): `python api/server.py` on port 5001; Vite proxies `/api/*` there
- RAG Chat frontend: `vite` dev server on port 5173; proxies `/chat`, `/upload`, `/documents`, `/status` to port 8000
- Patient Journey backend: FastAPI on default port; Next.js frontend on port 3000
- No Docker or docker-compose detected

**CI/CD:**
- No CI pipeline configuration detected (no `.github/workflows/`, no CircleCI, no GitLab CI)
- Deployments appear to be manual (push to Vercel/Render via git or CLI)

## Environment Variables

**Required for RAG backend (`app.py` / `render.yaml`):**
- `OPENAI_API_KEY` — OpenAI API authentication
- `SNOWFLAKE_ACCOUNT` — Snowflake account identifier
- `SNOWFLAKE_USER` — Snowflake service account username
- `SNOWFLAKE_WAREHOUSE` — Snowflake compute warehouse name
- `SNOWFLAKE_DATABASE` — Snowflake database name
- `SNOWFLAKE_SCHEMA` — Snowflake schema name
- `SNOWFLAKE_PRIVATE_KEY_B64` — Base64-encoded PEM private key (cloud/Render deployment)
- `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` — Passphrase for the encrypted private key
- `ALLOWED_ORIGINS` — CORS allowed origins (optional; defaults allow all in dev)

**Local dev only (not in render.yaml):**
- `private_key.pem` file at project root (replaces `SNOWFLAKE_PRIVATE_KEY_B64` for local dev)

**Required for AI Platform API (`ai-platform/api/server.py`):**
- `OPENAI_API_KEY`
- `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA`
- `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE`

**Legacy / disabled:**
- `PINECONE_API_KEY` — present in `Example_Render.env`, not used in current code
- `TAVILY_API_KEY` — used in Patient Journey pipeline (not in root env template)

**Secrets location:**
- `.env` file at project root (never commit; listed in `.gitignore`)
- `private_key.pem` at project root (never commit)
- Render dashboard for production secrets

## Webhooks & Callbacks

**Incoming:**
- None detected — no webhook endpoint handlers in `app.py` or other backends

**Outgoing:**
- None detected — all external calls are synchronous request/response

---

*Integration audit: 2026-04-13*
