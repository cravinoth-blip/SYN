# Testing

**Analysis Date:** 2026-04-13

## Test Framework

**Python:**
- No test framework configured. No `pytest`, `unittest`, `nose`, or any equivalent installed in the project root or pipeline package.
- `test_query.py` exists at the root but is a manual smoke-test script, not an automated test suite.
- No `pytest.ini`, `setup.cfg [tool:pytest]`, or `pyproject.toml [tool.pytest]` configuration detected.

**TypeScript/JavaScript:**
- No test runner configured. `ai-platform/package.json` has no `test` script and does not list `vitest`, `jest`, `@testing-library`, or any test dependency.
- `Patient Journey/app/package.json` similarly has no test script or test dependency.
- No `jest.config.*`, `vitest.config.*`, or `playwright.config.*` found.

## Test Coverage

**What is tested (manually):**

- `test_query.py` — manual HTTP smoke test against a running `app.py` instance. Sends a query to `POST /query/` and prints formatted results. Requires the server to be running and Snowflake to be connected. Usage:
  ```bash
  python test_query.py "your query text"
  # or
  python test_query.py  # then enter query at prompt
  ```
  Tests: result count, similarity scores, title/source/text fields in response.

**What is not tested (everything else):**
- ETL pipeline functions (`etl_local.py`, `etl_chroma.py`, `etl_missing.py`)
- PDF text extraction + OCR fallback logic in `Patient Journey/backend/main.py`
- Snowflake connection and vector similarity queries (`app.py`, `Patient Journey/backend/snowflake_client.py`)
- 4-pass pipeline orchestration (`orchestrator.py`, `passes/pass1_generate.py` through `pass4_polish.py`)
- All React/TypeScript UI components — zero component tests
- API endpoints in `ai-platform/api/server.py` (Flask)
- Knowledge graph construction (`knowledge_graph.py`, `knowledge_graph_amd.py`)
- Config validation logic in `Patient Journey/patient_journey_pipeline/patient_journey_pipeline/config.py`

## Test Locations

**Only test-adjacent file:**
- `c:/Users/a287484/OneDrive - Syneos Health/Desktop/RAG/test_query.py` — manual integration smoke test

**No test directories exist:**
- No `tests/`, `test/`, `__tests__/`, or `spec/` directories in the project root or sub-projects.

## Test Patterns

**Only observed pattern — manual HTTP smoke test (`test_query.py`):**
```python
def query(text, top_k=5):
    response = requests.post(API_URL, json={
        "query_text": text,
        "top_k": top_k,
        "table_name": "RAG_TEST"
    })

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        return

    data = response.json()
    results = data.get("context", [])
    # Print formatted results — no assertions, no pass/fail
```

- Pattern: send request, print response. No assertions. Requires manual inspection of output.
- Hardcoded `API_URL = "http://localhost:8000/query/"` and `table_name: "RAG_TEST"`.
- Command-line arg support: `query_text = " ".join(sys.argv[1:])` if args provided.

**Config self-validation pattern (not a test, but catches bad config at startup):**
```python
# config.py — raises ValueError/RuntimeError at import time
if not (0.0 <= TEMPERATURE <= 2.0):
    raise ValueError(f"TEMPERATURE must be between 0 and 2, got {TEMPERATURE}")
```
This provides a form of startup validation but is not a test suite.

## Gaps

**Critical gaps — entire codebase lacks automated testing:**

1. **No unit tests for ETL logic** — chunking, embedding, metadata enrichment, and Snowflake upload in `etl_local.py` and `etl_chroma.py` are untested. A silent regression in chunk size or embedding dimension would go undetected until a production query fails.

2. **No unit tests for PDF extraction** — the OCR fallback path in `Patient Journey/backend/main.py` (`extract_pdf_text()`) has complex branching (PyMuPDF text vs GPT-4o vision) with no coverage.

3. **No pipeline pass tests** — each of the 4 pipeline passes (`pass1_generate.py`, `pass2_verify.py`, `pass3_artifacts.py`, `pass4_polish.py`) constructs complex prompts and parses JSON from OpenAI. Prompt construction is untested; JSON parsing failures are handled silently with fallbacks.

4. **No API endpoint tests** — `app.py` (RAG FastAPI) and `ai-platform/api/server.py` (Flask) have no automated tests. The `/query/` endpoint's Snowflake vector search and the `/api/ingest` chunking/upload flow are fully untested.

5. **No React component tests** — all UI components in `ai-platform/src/app/components/` and `Patient Journey/app/src/` lack tests. State transitions, form validation, and error display are untested.

6. **No CI pipeline** — no `.github/workflows/`, no automated test runs on push or PR. Only `render.yaml` exists for deployment, with no test step.

7. **Manual smoke test has no assertions** — `test_query.py` prints output but never asserts correctness. A broken response format would pass silently.

**Recommended additions (priority order):**
- `pytest` with `httpx` for FastAPI endpoint tests (`app.py`, `Patient Journey/backend/main.py`)
- Unit tests for ETL chunking functions (pure functions, no external deps needed)
- `vitest` + `@testing-library/react` for `ai-platform/` component tests
- Assertions added to `test_query.py` to make it a real smoke test
