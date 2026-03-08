# RAG Pipeline - Project Information

## What Is This Project?

A **Retrieval-Augmented Generation (RAG)** framework from Syneos Health's EU Innovation team. It enables building Custom GPTs that answer questions grounded in proprietary documents (scientific papers, clinical reports, competitor materials, etc.) with accurate citations - rather than relying on ChatGPT's general training data.

Originally designed for health communications teams to query large document collections via a ChatGPT Custom GPT interface.

---

## Original Architecture (Cloud-Based)

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ 1. ETL PIPELINE  │     │ 2. VECTOR STORE  │     │ 3. MIDDLEWARE    │
│ (Google Colab)   │────>│ (Snowflake)      │<────│ (FastAPI/Render) │
│                  │     │                  │     │                  │
│ - Extract text   │     │ - Stores chunks  │     │ - Embeds query   │
│   from docs      │     │   + embeddings   │     │   via OpenAI     │
│ - Chunk text     │     │   + metadata     │     │ - Cosine search  │
│ - Enrich metadata│     │   as VECTOR type │     │   on Snowflake   │
│ - Generate       │     │                  │     │ - Returns top-k  │
│   embeddings     │     │                  │     │   results        │
│ - Upload to SF   │     │                  │     │                  │
└──────────────────┘     └──────────────────┘     └────────▲─────────┘
                                                           │
                                                           │ API call
                         ┌──────────────────┐     ┌────────┴─────────┐
                         │ 5. RESPONSE      │     │ 4. CUSTOM GPT    │
                         │                  │<────│ (ChatGPT UI)     │
                         │ Grounded answer  │     │                  │
                         │ with citations   │     │ - Action schema  │
                         │ from your docs   │     │   calls /query   │
                         └──────────────────┘     │ - System prompt  │
                                                  └──────────────────┘
```

### Data Flow

1. Source documents (PDF, DOCX, Excel, JSON, TXT) sit in a folder
2. ETL pipeline extracts text, chunks it (1000-1500 chars), enriches metadata (DOI, Crossref, AI-generated titles/summaries), generates embeddings via OpenAI `text-embedding-3-small`
3. Chunks + embeddings + metadata uploaded to a Snowflake table as `VECTOR(FLOAT, 1536)`
4. User asks a question in Custom GPT
5. Custom GPT calls the FastAPI middleware via Action schema
6. Middleware embeds the query, runs cosine similarity search on Snowflake, returns top-k chunks
7. Custom GPT generates a grounded, cited answer from the retrieved context

---

## Files In This Project

| File | Purpose |
|------|---------|
| `ETL_Code_Dec.ipynb` | ETL pipeline notebook. Extracts text from docs, chunks, generates embeddings, uploads to Snowflake. Originally runs on Google Colab. |
| `app.py` | FastAPI middleware. Accepts queries, generates embeddings, searches Snowflake via cosine similarity, returns context. |
| `requirements.txt` | Python dependencies for the FastAPI middleware (deployed on Render in original setup). |
| `Example_Render.env` | Template for environment variables (Snowflake creds, OpenAI key, etc.). |
| `Action Schema.rtf` | OpenAPI schema for Custom GPT configuration (tells GPT how to call the middleware API). |
| `AI_Training_RAG_Dec.pdf` | Full training slides - RAG concepts, architecture, evaluation results. |
| `ETL_Pipeline_Training_snowflake.pdf` | Step-by-step ETL pipeline walkthrough with code screenshots. |

---

## ETL Pipeline Detail

### Extract
- **File extraction**: PDF (PyMuPDF with table detection), DOCX (paragraphs + tables), Excel (normalized merged cells), JSON, TXT
- **DOI extraction**: Regex on first page of PDFs
- **Crossref metadata**: Uses DOI to fetch title, authors, publication date, citation count, journal

### Transform
- **AI title extraction**: First ~4000 chars sent to `gpt-4o-mini` for title extraction
- **AI summary generation**: Document text sent to `gpt-4o-mini` for concise summary
- **Chunking**: LangChain `RecursiveCharacterTextSplitter`, 1000-1500 char chunks with overlap, page tracking
- **Embedding**: Each chunk sent to OpenAI `text-embedding-3-small` (1536-dimensional vectors)

### Load
- **CSV generation**: Each chunk = one row with columns: ID, SOURCE_FILE, CHUNK_INDEX, CHUNK_PREVIEW, TEXT, PAGES, CITATION_COUNT, DOI, TITLE, AUTHORS, PUBLISHED, CITATION, PAGE_REFERENCE, EMBEDDING, SAS_URL, IS_TABLE, FILE_TYPE, SUMMARY
- **Snowflake upload**: Creates table if needed, supports append/replace/upsert modes, converts embedding to `VECTOR(FLOAT, 1536)`
- **Pinecone upload** (optional): Same vectors + metadata to Pinecone index

### Snowflake Table Schema
```sql
CREATE TABLE IF NOT EXISTS <TABLE_NAME> (
    ID VARCHAR(16777216),
    SOURCE_FILE VARCHAR(16777216),
    CHUNK_INDEX INTEGER,
    CHUNK_PREVIEW VARCHAR(16777216),
    TEXT VARCHAR(16777216),
    PAGES VARCHAR(16777216),
    CITATION_COUNT INTEGER,
    DOI VARCHAR(16777216),
    TITLE VARCHAR(16777216),
    AUTHORS VARCHAR(16777216),
    PUBLISHED DATE,
    CITATION VARCHAR(16777216),
    PAGE_REFERENCE VARCHAR(16777216),
    SAS_URL VARCHAR(16777216),
    IS_TABLE BOOLEAN,
    SUMMARY VARCHAR(16777216),
    EMBEDDING_VECTOR VECTOR(FLOAT, 1536)
);
```

### Middleware (app.py)
- FastAPI with `POST /query/` endpoint
- Accepts: `query_text`, `table_name`, `top_k` (default 15, max 30)
- Generates embedding via OpenAI `text-embedding-3-small`
- Snowflake SQL using `VECTOR_COSINE_SIMILARITY()` for top-k matching
- Returns context as JSON (text + all metadata)
- Authenticates to Snowflake via private key

---

## Our Intention: Local Development Setup

### Goal
Run the entire RAG pipeline locally for development and testing, without Render or Custom GPT.

### Local Architecture (Simplified)

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ ETL SCRIPT       │     │ SNOWFLAKE        │     │ FastAPI LOCAL    │
│ (local Python)   │────>│ (cloud DB)       │<────│ (uvicorn)        │
│                  │     │                  │     │                  │
│ Reads PDFs from  │     │ Stores vectors   │     │ localhost:8000   │
│ local folder     │     │                  │     │                  │
└──────────────────┘     └──────────────────┘     └────────▲─────────┘
                                                           │
                                                  ┌────────┴─────────┐
                                                  │ TEST SCRIPT      │
                                                  │ (curl / Python)  │
                                                  │                  │
                                                  │ Replaces Custom  │
                                                  │ GPT for dev      │
                                                  └──────────────────┘
```

### What Changes From Original
| Component | Original | Local |
|-----------|----------|-------|
| ETL runtime | Google Colab | Local Python/Jupyter |
| Document source | Google Drive | Local folder (`./documents/`) |
| Middleware hosting | Render (cloud) | `uvicorn` on localhost:8000 |
| UI / query interface | Custom GPT (ChatGPT) | curl / test script |
| Vector DB | Snowflake (cloud) | Snowflake (still cloud - required for vector search) |
| Azure SAS URLs | Enabled | Disabled (not needed for dev) |
| Pinecone | Optional | Disabled |

### Prerequisites
1. **Snowflake account** - with credentials (account, user, warehouse, database, schema, private key)
2. **OpenAI API key** - for embeddings (`text-embedding-3-small`) and metadata generation (`gpt-4o-mini`)
3. **Sample documents** - 10-20 PDFs in a local `./documents/` folder
4. **Python 3.x** with required packages

### Snowflake Cannot Be Replaced Locally
Snowflake is the only cloud dependency that remains. It provides:
- `VECTOR(FLOAT, 1536)` native vector type
- `VECTOR_COSINE_SIMILARITY()` built-in function for similarity search
- Enterprise-grade storage and query performance

A local alternative would require replacing it with a different vector DB (e.g., ChromaDB, FAISS), which would mean rewriting both the ETL load step and the app.py query logic.

---

## Evaluation Results (from Syneos testing)

| Strategy | F1 | GPT Score | Cosine |
|----------|-----|-----------|--------|
| Standard (1000-1500 chars) | 0.84 | 0.87 | 0.95 |
| Query Expansion (best) | 0.90 | 0.86 | 0.95 |
| Split 128 (too small) | 0.04 | 0.25 | 0.85 |
| Split 256 | 0.15 | 0.46 | 0.90 |

Key takeaway: Chunk size of 1000-1500 characters with Query Expansion yields best results.

---

## Key Contacts (Syneos EU Innovation Team)
- Ayesha Hussain
- Duncan Arbour
- Lucy Ferguson
