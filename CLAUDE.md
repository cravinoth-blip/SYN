# CLAUDE.md - Project Context for Claude Code

## Project Overview
RAG (Retrieval-Augmented Generation) pipeline for querying proprietary documents via vector similarity search. Based on Syneos Health's EU Innovation team framework, adapted for local development.

## Architecture
- **ETL Pipeline**: Extracts text from documents (PDF/DOCX/Excel/JSON/TXT), chunks (1000-1500 chars), enriches metadata (Crossref DOI, AI-generated titles/summaries), generates embeddings (OpenAI `text-embedding-3-small`, 1536 dims), uploads to Snowflake.
- **Middleware**: FastAPI app (`app.py`) with `/query/` endpoint. Embeds user query, runs `VECTOR_COSINE_SIMILARITY()` on Snowflake, returns top-k document chunks with metadata.
- **Vector DB**: Snowflake with `VECTOR(FLOAT, 1536)` column type. Cannot be easily replaced locally.

## Key Files
- `ETL_Code_Dec.ipynb` - ETL pipeline (originally Google Colab, adapting to local)
- `app.py` - FastAPI middleware (runs locally via uvicorn on port 8000)
- `requirements.txt` - Dependencies for app.py
- `Example_Render.env` - Template for environment variables
- `Action Schema.rtf` - OpenAI Custom GPT action schema (not needed for local dev)
- `Project_Info.md` - Detailed project documentation
- `documents/` - Local folder for source PDFs (to be created)
- `.env` - Local environment variables (to be created, DO NOT commit)

## Development Setup (Local)
- ETL runs as local Python/Jupyter instead of Google Colab
- app.py runs via `uvicorn app:app --host 0.0.0.0 --port 8000`
- Query via curl/test script instead of Custom GPT
- Snowflake remains cloud-based (required for vector search)
- Azure SAS URLs: disabled for local dev
- Pinecone: disabled for local dev

## Environment Variables Required
```
OPENAI_API_KEY=sk-...
SNOWFLAKE_ACCOUNT=...
SNOWFLAKE_USER=...
SNOWFLAKE_WAREHOUSE=...
SNOWFLAKE_DATABASE=...
SNOWFLAKE_SCHEMA=...
SNOWFLAKE_PRIVATE_KEY=...
SNOWFLAKE_PRIVATE_KEY_PASSPHRASE=...
```

## Important Notes
- Embeddings model: `text-embedding-3-small` (1536 dimensions) - used in both ETL and app.py, must match
- Metadata generation uses `gpt-4o-mini` for title extraction and summaries
- Chunk size: 1000-1500 characters (optimal per Syneos evaluation)
- Top-k max: 30 results (context window limits downstream)
- `ALLOWED_TABLES` in app.py must be updated with your actual table name
- Snowflake auth uses private key (PEM format), not password
- The `.env` file and any credentials must never be committed to git

## Conventions
- Table names in Snowflake are UPPERCASE
- Column names in Snowflake are UPPERCASE
- ETL CSV columns must match Snowflake table schema exactly
- Upload modes: "append" (add new), "replace" (drop + recreate), "upsert" (update by ID)

## TODO
- [ ] Get Snowflake credentials from Paul Henderson
- [ ] Purchase OpenAI API key
- [ ] Gather 10-20 sample PDFs in `./documents/`
- [ ] Convert ETL notebook to local Python script (remove Google Colab dependencies)
- [ ] Create `.env` file with credentials
- [ ] Update `ALLOWED_TABLES` and `TABLE_NAME` in app.py
- [ ] Create test query script for local development
- [ ] Test full pipeline: ETL → Snowflake → app.py → query
