# Knowledge Hub Render API

This FastAPI service exposes the existing Snowflake Cortex Search service:

`COMMUNICATIONS__EU__DER__DEV.KNOWLEDGE_HUB.KNOWLEDGE_SEARCH`

Its source content is stored in:

`COMMUNICATIONS__EU__DER__DEV.KNOWLEDGE_HUB.KNOWLEDGE_CHUNKS`

The vectors are managed internally by Cortex Search with
`snowflake-arctic-embed-m-v1.5`; this API does not create a second set of
OpenAI embeddings.

## Render deployment

1. Push this directory and `render.yaml` to the connected Git repository.
2. In Render, create a Blueprint using `knowledge-hub-render-api/render.yaml`.
3. Add the following secret environment values:
   - `SNOWFLAKE_ACCOUNT`
   - `SNOWFLAKE_USER`
   - `SNOWFLAKE_ROLE`
   - `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` when the PEM is encrypted
4. In the Render service, add the PEM as a secret file named
   `private_key.pem`. Render exposes it as `/etc/secrets/private_key.pem`.
5. Keep the generated `KNOWLEDGE_HUB_API_KEY` private. Send it to the API as
   the `X-API-Key` header.

The Snowflake role needs usage on the database, schema, and warehouse, plus
usage on the Cortex Search service:

```sql
GRANT USAGE ON DATABASE COMMUNICATIONS__EU__DER__DEV TO ROLE <ROLE>;
GRANT USAGE ON SCHEMA COMMUNICATIONS__EU__DER__DEV.KNOWLEDGE_HUB TO ROLE <ROLE>;
GRANT USAGE ON WAREHOUSE WH_COMMUNICATIONS__EU__DER TO ROLE <ROLE>;
GRANT USAGE ON CORTEX SEARCH SERVICE
  COMMUNICATIONS__EU__DER__DEV.KNOWLEDGE_HUB.KNOWLEDGE_SEARCH TO ROLE <ROLE>;
```

## API

Health check:

```text
GET /health
```

Search:

```http
POST /search
X-API-Key: <KNOWLEDGE_HUB_API_KEY>
Content-Type: application/json

{
  "query": "What evidence is available for this topic?",
  "limit": 12,
  "collection_id": "optional collection ID",
  "language": "optional language",
  "document_type": "optional document type",
  "evidence_type": "optional evidence type"
}
```

The compatibility endpoint for the previous GPT Action contract is:

```http
POST /query/
X-API-Key: <KNOWLEDGE_HUB_API_KEY>
Content-Type: application/json

{
  "query_text": "What evidence is available for this topic?",
  "top_k": 12
}
```

Dynamic public research:

```http
POST /research/query/
X-API-Key: <KNOWLEDGE_HUB_API_KEY>
Content-Type: application/json

{
  "source": "pubmed",
  "query_text": "a topic defined by the user",
  "top_k": 5
}
```

`source` can be `pubmed` or `clinical_trials`. The official discovery API
finds relevant identifiers, which are then hydrated from
`COMPILE_ADD_ON.PUBMED_DETAILS.PUBLICATIONS` or
`COMPILE_ADD_ON.CLINICAL_TRIAL_DETAILS`. This avoids scanning or copying the
full 184-million-row publications table.

Interactive OpenAPI documentation is available at `/docs`.

## Local validation

Copy `.env.example` values into your shell and point
`SNOWFLAKE_PRIVATE_KEY_PATH` to a local PEM. Then run:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
uvicorn main:app --reload --port 8000
```
