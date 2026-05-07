# Stratergic Mapping

Production-shaped v1 implementation of the 7Cs Disease Intelligence Platform.

The app is built as a portable Docker monorepo:

- `apps/web`: Next.js workspace experience.
- `apps/api`: FastAPI API, orchestration, persistence, validation, and export endpoints.
- `apps/worker`: async worker entrypoint for production job execution.
- `packages/shared`: shared TypeScript constants and API-facing enums.
- `infra/docker`: Docker support files.
- `docs`: implementation notes and architecture documentation.

## Local Development

1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
2. Start the portable stack:

```bash
docker compose up --build
```

3. Open the web app at `http://localhost:3005`.
4. Open the API docs at `http://127.0.0.1:8005/docs`.

## Development Without Docker

Frontend:

```bash
npm install
npm run dev
```

Backend:

```bash
cd apps/api
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8005
```

## Core Rule

Generated output is never shown directly. The workspace and exports read only from validated, published versions.

## Local Vector Store

Uploaded PDF/PPTX files are parsed into overlapping text chunks and indexed into a local
ChromaDB collection at `chroma_db` by default. SQL remains the source of truth for uploaded
files and chunks; Chroma provides semantic cosine search over those chunks during generation.

If `OPENAI_API_KEY` is set, uploads use `OPENAI_EMBEDDING_MODEL` for embeddings. Without an API
key, the backend uses a deterministic local hash embedding so development and tests can run
offline. The Chroma path and collection can be changed with `VECTOR_DB_PATH` and
`VECTOR_COLLECTION_NAME`.

PubMed and PMC also index retrieved NCBI text into the same Chroma collection during generation:

- PubMed uses NCBI E-utilities `esearch` + `efetch` XML to fetch abstracts, metadata, and citations.
- PMC uses NCBI E-utilities `esearch` + `efetch` XML to fetch full article text when available.
- `NCBI_RETMAX` controls how many PubMed/PMC records are pulled per section; default is `100`.
- Put `NCBI_EMAIL` and `NCBI_API_KEY` in `.env` to identify requests and raise the NCBI E-utilities
  request limit from 3 requests/second to 10 requests/second.
- `CLINICAL_TRIALS_PAGE_SIZE` and `WEB_SEARCH_RESULTS_PER_SOURCE` default to `100`, so each
  external source family aims to retrieve 100 records before semantic ranking. `INTERNAL_UPLOAD_TOP_K`
  defaults to `50` uploaded-file chunks.
- `NCBI_REQUEST_DELAY_SECONDS`, `WEB_REQUEST_DELAY_SECONDS`, `EXTERNAL_REQUEST_TIMEOUT_SECONDS`, and
  `EXTERNAL_REQUEST_RETRIES` provide polite pacing and retry/backoff for live connectors.
