# Codebase Concerns

**Analysis Date:** 2026-04-13

---

## Security Risks

**SQL Injection via f-string ILIKE clauses (CRITICAL):**
- Issue: Disease/keyword input from users is interpolated directly into SQL `LIKE` clauses using Python f-strings with no sanitization or parameterization.
- Files: `Patient Journey/backend/snowflake_client.py` (lines 157–166), `Patient Journey/patient_journey_pipeline/patient_journey_pipeline/tools/snowflake_search.py` (lines 162–174)
- Example: `f"UPPER({col}) LIKE '%{kw.upper()}%'"` where `kw` comes from `disease.split()`. A disease name like `'; DROP TABLE PUBLICATIONS; --` would execute.
- Fix approach: Use parameterized queries with `%s` placeholders and pass keyword list separately, or validate/sanitize `disease` input against an alphanumeric allowlist before splitting into keywords.

**No API Authentication on Any Endpoint:**
- Issue: Every FastAPI and Flask endpoint (`/chat/stream`, `/upload/stream`, `/generate`, `/documents`, `/query`, `/api/ingest`, `/api/record-action`) is completely unauthenticated. Any network-reachable client can upload files, query the vector DB, delete documents, or ingest new records into Snowflake.
- Files: `app.py`, `Patient Journey/backend/main.py`, `ai-platform/api/server.py`
- Impact: Data exfiltration, unauthorized document deletion, unlimited OpenAI API spend, Snowflake compute cost abuse.
- Fix approach: Add an API key header check (simple `X-API-Key` middleware) or integrate with an identity provider. At minimum, require a shared secret env var.

**Hardcoded Fallback Warehouse Name:**
- Issue: The string `'WH_COMMUNICATIONS__EU__DER'` is hardcoded as a fallback in multiple files. If `SNOWFLAKE_WAREHOUSE` env var is missing, every connection will silently use this warehouse without any error.
- Files: `app.py` (line 104), `ai-platform/api/server.py` (lines 289, 361), `etl_local.py` (line 122), `etl_missing.py` (line 127)
- Impact: Silent misconfiguration; queries billing the wrong Snowflake warehouse in multi-tenant environments.
- Fix approach: Remove fallback strings; raise `ValueError` if `SNOWFLAKE_WAREHOUSE` is not set.

**Hardcoded Flask Secret Key:**
- Issue: `Questionnaire/app.py` line 19 contains `app.secret_key = os.environ.get('SECRET_KEY', 'bronchiectasis-unlocked-dev')`. If `SECRET_KEY` is not set in production, session cookies are signed with a public, guessable key, enabling session forgery.
- Files: `Questionnaire/app.py`
- Fix approach: Remove the fallback string entirely; fail at startup if `SECRET_KEY` is absent.

**`b64key.txt` Not in `.gitignore`:**
- Issue: A base64-encoded private key file `b64key.txt` exists at the repo root and is not covered by the root `.gitignore` (which only covers `*.pem` and `*.key` patterns). If committed, the Snowflake private key would be in git history.
- Files: `b64key.txt` (root), `.gitignore`
- Fix approach: Add `b64key.txt` to `.gitignore` immediately. Rotate the private key if it has been committed to any branch.

**`render.env` File Not in `.gitignore`:**
- Issue: `render.env` exists at the repo root (observed in git status as a tracked file). This file likely contains production environment variables including credentials for the Render hosting platform.
- Files: `render.env`
- Fix approach: Add `render.env` to `.gitignore` and use Render's native secret management instead.

**CORS Wildcard Pattern Allows Any Vercel Subdomain:**
- Issue: `Patient Journey/backend/main.py` line 120 sets `allow_origins=["http://localhost:3000", "https://*.vercel.app"]`. Wildcard subdomains in CORS effectively allow any Vercel-hosted site (including attacker-controlled deployments) to make credentialed cross-origin requests to the backend.
- Fix approach: Specify exact production Vercel URL(s) rather than using the wildcard.

**Unsandboxed Code Execution:**
- Issue: `Patient Journey/patient_journey_pipeline/patient_journey_pipeline/tools/code_interpreter.py` executes arbitrary LLM-generated Python code via `subprocess.run(["python", script_path], ...)` with no sandboxing. The `PRODUCTION NOTE` in the file itself acknowledges this is unsafe and requires replacement with E2B, Docker, or OpenAI Assistants.
- Files: `Patient Journey/patient_journey_pipeline/patient_journey_pipeline/tools/code_interpreter.py`
- Impact: If an LLM is manipulated to generate malicious code (prompt injection), it could read arbitrary files, make network calls, or modify the filesystem of the host running the server.
- Fix approach: Replace subprocess execution with a sandboxed environment (E2B, Modal, or Docker) before any production deployment.

---

## Tech Debt

**Duplicate Snowflake Connection Logic Across 7+ Files:**
- Issue: Private key loading, `snowflake.connector.connect()`, and warehouse selection are copy-pasted (with minor variations) in: `app.py`, `etl_local.py`, `ai-platform/api/server.py`, `Patient Journey/backend/snowflake_client.py`, `Patient Journey/.../tools/snowflake_search.py`, `check_snowflake.py`, `list_warehouses.py`, `read_publications.py`, `knowledge_graph_amd.py`, `upload_qc_rules.py`.
- Impact: Bug fixes and credential handling changes must be applied to 10+ locations. The three PEM-parsing strategies (`_parse_env` in `app.py`, raw env var splitting in `snowflake_client.py`, `pem_path` file read in `ai-platform/api/server.py`) already diverge.
- Fix approach: Extract a single `snowflake_utils.py` module at the repo root with `load_private_key()` and `get_connection()` helpers; import everywhere.

**Duplicate Embedding + OpenAI Client Instantiation:**
- Issue: `OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))` is instantiated inside every function that needs it (e.g., `retrieve_context`, `retrieve_qc_rules`, `_generate_with_openai`, `chat_stream`, `chat_qc_stream`). Similarly, embedding calls are duplicated across `app.py`, `snowflake_client.py`, `etl_local.py`, and `ai-platform/api/server.py`.
- Fix approach: Use a module-level singleton with lazy initialization (as partially done in `ai-platform/api/server.py`'s `get_openai_client()`), and share it across endpoints.

**Global Snowflake Connection with Broken Re-use Pattern:**
- Issue: `app.py` uses a module-level `_sf_conn` singleton that pings with `SELECT 1` to check liveness, but FastAPI is async and the Snowflake connector is synchronous. Multiple concurrent requests can race on the same connection object.
- Files: `app.py` (lines 51–105)
- Fix approach: Use a connection pool (e.g., `snowflake.connector`'s built-in pooling or `SQLAlchemy`) or create a fresh connection per request with proper lifecycle management.

**`aiGenerator.ts` Uses Entirely Mock/Hardcoded Responses:**
- Issue: `ai-platform/src/app/utils/aiGenerator.ts` is a mock generator that returns hardcoded template strings with no real AI or API calls. It simulates a 1.5-second delay and returns boilerplate pharmaceutical strategy content regardless of user input.
- Files: `ai-platform/src/app/utils/aiGenerator.ts`
- Impact: The "Content Generator" page (`ai-platform/src/app/pages/ContentGenerator.tsx`) appears functional but produces zero real AI output. Real content generation is never wired up.
- Fix approach: Replace mock generator with a real API call to the backend `/generate` or OpenAI endpoint. This is a significant incomplete feature, not just tech debt.

**`pptx_router.py` Is Missing But Imported:**
- Issue: `app.py` lines 182–183 import and register `pptx_router` from `pptx_router.py`. The git status shows `pptx_router.py` was deleted (`D pptx_router.py`). The server will crash on startup with an `ImportError`.
- Files: `app.py` (line 182), deleted `pptx_router.py`
- Fix approach: Either restore `pptx_router.py` or remove the import and `app.include_router(pptx_router)` lines from `app.py`.

**ETL Pipeline Still Partly Notebook-Based:**
- Issue: `ETL_Code_Dec.ipynb` (the primary ETL pipeline) remains as a Jupyter notebook and has not been converted to a local Python script as noted in `CLAUDE.md`'s TODO list. There are partial replacements (`etl_local.py`, `etl_chroma.py`, `etl_missing.py`) but no single canonical ETL entry point.
- Files: `ETL_Code_Dec.ipynb`, `etl_local.py`, `etl_chroma.py`, `etl_missing.py`
- Impact: Unclear which ETL path is the correct one; `etl_missing.py` hardcodes `WH_COMMUNICATIONS__EU__DER` as a fallback.

---

## Incomplete Features

**AI Content Generation is Fully Mocked:**
- Issue: As described above, `ai-platform/src/app/utils/aiGenerator.ts` generates static template strings. The `ContentGenerator` page never calls any backend.
- Files: `ai-platform/src/app/utils/aiGenerator.ts`, `ai-platform/src/app/pages/ContentGenerator.tsx`
- Status: Non-functional placeholder.

**PPTX Comparator Feature Deleted Mid-Development:**
- Issue: `ai-platform/src/app/pages/PptxComparator.tsx` was deleted (git status shows `D`), the corresponding `pptx_router.py` backend was also deleted, but the import in `app.py` was not cleaned up. The route entry in `ai-platform/src/app/routes.ts` may also still reference it.
- Files: `app.py` (line 182), deleted `pptx_router.py`, deleted `ai-platform/src/app/pages/PptxComparator.tsx`

**Patient Journey Pipeline Falls Back Silently to GPT-4o Hallucination Mode:**
- Issue: `Patient Journey/backend/main.py` has three silent fallback paths (lines 200–206) — if the pipeline returns no phases, or fails to import, or throws any exception, it calls `_generate_with_openai()` which generates a patient journey purely from GPT-4o's internal knowledge with no real evidence, but labels it as if it came from the knowledge base. The user receives no indication that evidence retrieval failed.
- Files: `Patient Journey/backend/main.py` (lines 197–206)
- Fix approach: Return an explicit error or degraded-mode warning in the response payload when falling back to direct generation.

**`CodeInterpreterTool` is Explicitly Marked as a Stub:**
- Issue: The file's own docstring (line 3–7) and inline comment (line 36–40) state "For production: use OpenAI's native code interpreter or a sandboxed environment... This skeleton uses subprocess... Replace with your preferred sandboxing solution."
- Files: `Patient Journey/patient_journey_pipeline/patient_journey_pipeline/tools/code_interpreter.py`

**Knowledge Graph Scripts Are One-Off Exploratory Scripts:**
- Issue: `knowledge_graph.py`, `knowledge_graph_amd.py`, `update_kg_mesh.py`, `extract_mesh.py` exist as standalone scripts with no integration into the main application flow and no shared utility layer.
- Files: `knowledge_graph.py`, `knowledge_graph_amd.py`, `update_kg_mesh.py`, `extract_mesh.py`

---

## Scalability Concerns

**Full Document Text Loaded into Memory on Upload:**
- Issue: In `app.py`'s `/upload/stream` endpoint, the entire uploaded file is read into memory with `contents = await file.read()` before any processing begins. For large PDFs or Excel files, this can exhaust server RAM. FastAPI provides no file size limit.
- Files: `app.py` (line 422–423), `Patient Journey/backend/main.py` (line 153–154), `ai-platform/api/server.py` (line 225)
- Fix approach: Add a `MAX_UPLOAD_BYTES` check immediately after `file.read()`, or stream chunks to disk directly using `SpooledTemporaryFile`.

**Snowflake Vector Search Fetches All Embeddings and Sorts In-DB (No Pagination):**
- Issue: `retrieve_context()` in `app.py` runs a full-table vector similarity scan ordered by score and limits to `top_k`. As the table grows past tens of thousands of chunks, this query will become slow and expensive. There is no pagination on the `/documents` endpoint either.
- Files: `app.py` (lines 107–143), `app.py` (lines 564–594)
- Fix approach: Use Snowflake's ANN (Approximate Nearest Neighbor) index when available, and add `OFFSET`/`LIMIT` pagination to `/documents`.

**No Async Execution for Snowflake or OpenAI calls in FastAPI:**
- Issue: All Snowflake connector calls and OpenAI SDK calls in `app.py` are synchronous, executing in the async event loop and blocking it. Under concurrent load, a single slow query will stall all other requests.
- Files: `app.py` throughout; `Patient Journey/backend/main.py`
- Fix approach: Wrap synchronous calls in `asyncio.get_event_loop().run_in_executor()` or use an async Snowflake client.

**Patient Journey Pipeline Runs Sequentially with No Timeout:**
- Issue: The 4-pass LLM pipeline in `Patient Journey/patient_journey_pipeline/patient_journey_pipeline/orchestrator.py` runs serially, each pass waiting for the previous. A single pass can make up to 60 tool calls (line 66 of `config.py`). With no overall timeout, a hung pipeline will block the FastAPI request indefinitely.
- Files: `Patient Journey/backend/main.py` (lines 187–206), `Patient Journey/patient_journey_pipeline/patient_journey_pipeline/orchestrator.py`
- Fix approach: Wrap pipeline execution in `asyncio.wait_for()` with a timeout (e.g., 300 seconds) and return a partial result or task ID for async polling.

---

## Dependency Risks

**`pptx_router` Import Will Crash Server on Startup:**
- Issue: As noted above, `pptx_router.py` was deleted but `app.py` still imports it at module level. The server cannot start.
- Files: `app.py` line 182
- Priority: Immediate fix required.

**No Lockfile for Python Dependencies:**
- Issue: `requirements.txt` pins exact versions (good), but there is no `pip.lock` or `poetry.lock`. The `ai-platform/api/server.py` server uses different dependencies (Flask, flask-cors, langchain-text-splitters) not listed in the root `requirements.txt`. There is no `requirements.txt` for `ai-platform/api/`.
- Fix approach: Add `requirements.txt` to `ai-platform/api/` and consider using `pip-compile` or `poetry` for reproducible installs.

**`ai-platform/.gitignore` Does Not Cover `.env`:**
- Issue: The `ai-platform/.gitignore` only excludes `node_modules/`, `dist/`, and `.vercel`. If a `.env` file is created in `ai-platform/` for local development, it will not be protected by gitignore and could be committed.
- Files: `ai-platform/.gitignore`
- Fix approach: Add `.env` and `.env.*` to `ai-platform/.gitignore`.

**Questionnaire Dependencies Use Minimum-Version Specifiers:**
- Issue: `Questionnaire/requirements.txt` uses `>=` specifiers (`flask>=2.3.0`, etc.) with no upper bounds. A major-version bump in Flask or psycopg2 could break the app silently on a fresh install.
- Files: `Questionnaire/requirements.txt`
- Fix approach: Pin to exact versions or use `~=` compatible release specifiers.

**Heavy Unused Dependency Bloat in `ai-platform`:**
- Issue: `ai-platform/package.json` includes `@mui/material`, `@mui/icons-material`, `@emotion/react`, `@emotion/styled`, `react-slick`, `react-responsive-masonry`, `react-dnd`, `react-popper` alongside a full Radix UI component suite. These two UI systems (MUI + Radix/shadcn) are duplicative; shipping both adds significant bundle weight.
- Files: `ai-platform/package.json`

---

## Operational Risks

**No Structured Logging — All Output via `print()`:**
- Issue: Every Python backend (`app.py`, `Patient Journey/backend/main.py`, `etl_local.py`, `ai-platform/api/server.py`) uses `print()` for operational output. The `app.py` line 184 sets `logging.basicConfig(level=logging.WARNING)` which suppresses most messages, but the codebase mixes `print()` and `logging` inconsistently. There is no log correlation ID or structured format for log aggregation.
- Files: All Python backends
- Fix approach: Replace `print()` calls with `logging.getLogger(__name__)` throughout; use `structlog` or JSON log format for production.

**Error Messages Leak Stack Traces to API Clients:**
- Issue: `app.py` lines 404–406 yield `_sse("error", message=str(e), detail=traceback.format_exc())` — the full Python traceback is sent to the browser. This reveals internal file paths, library versions, and logic details.
- Files: `app.py` (lines 404–406, 553–555)
- Fix approach: Log the full traceback server-side; return only a sanitized user-facing message to the client.

**Snowflake Connection Not Closed After Requests in `app.py`:**
- Issue: The global `_sf_conn` singleton is never explicitly closed. While the ping/reconnect pattern provides basic liveliness, leaked cursors and connections can exhaust Snowflake's session limit under sustained load.
- Files: `app.py` (lines 86–105)
- Fix approach: Use a context manager pattern or connection pool with explicit release.

**No `.env` Validation at Startup:**
- Issue: Most scripts silently substitute empty strings when environment variables are missing (e.g., `os.getenv("OPENAI_API_KEY", "")`). The server starts successfully with no credentials and only fails when the first request triggers an API call, giving misleading startup health.
- Files: `app.py` (line 45), `Patient Journey/backend/main.py` (line 74), `ai-platform/api/server.py` (line 41)
- Exception: `Patient Journey/patient_journey_pipeline/patient_journey_pipeline/config.py` correctly uses `_require()` to fail fast — this pattern should be adopted everywhere.
- Fix approach: Add a startup validation block in `app.py` that asserts all required env vars are non-empty before binding the server.

**Output Directory Written to Relative CWD:**
- Issue: `Patient Journey/backend/main.py` writes output files to `./output` (line 259) relative to the process working directory, not relative to `__file__`. If the server is started from a different directory, output files are scattered unpredictably.
- Files: `Patient Journey/backend/main.py` (lines 218–220, 256–259)
- Fix approach: Use `Path(__file__).parent / "output"` for a stable, predictable output path.

**Questionnaire SQLite Data Loss on Vercel Restart:**
- Issue: `Questionnaire/app.py` line 14 writes the SQLite database to `/tmp/responses.db` when running on Vercel. Vercel's serverless functions have ephemeral `/tmp` storage; all survey responses are lost on every cold start or deployment.
- Files: `Questionnaire/app.py`
- Impact: Production survey data is not persisted. The `DATABASE_URL` Postgres path exists as a fallback but requires explicit provisioning.
- Fix approach: Provision a persistent Postgres database and ensure `DATABASE_URL` is always set in the Vercel environment.

---

*Concerns audit: 2026-04-13*
