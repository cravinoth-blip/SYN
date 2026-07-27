# PFIZER ANTIINF Render API

This FastAPI service is permanently restricted to:

`COMMUNICATIONS__EU__DER__DEV.PFIZER_ANTIINF.KNOWLEDGE_SEARCH`

Its isolated source table is:

`COMMUNICATIONS__EU__DER__DEV.PFIZER_ANTIINF.KNOWLEDGE_CHUNKS`

The service never reads from `KNOWLEDGE_HUB`. Cortex Search manages embeddings
with `snowflake-arctic-embed-m-v1.5`; no OpenAI embeddings are created.

## Render deployment

Create the service from `pfizer-antiinf-render-api/render.yaml`, then configure:

- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER`
- `SNOWFLAKE_ROLE` when required
- `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` when the PEM is encrypted
- Secret file `private_key.pem`, mounted at `/etc/secrets/private_key.pem`
- `PFIZER_ANTIINF_API_KEY`

Send `PFIZER_ANTIINF_API_KEY` as the `X-API-Key` request header.

Required grants for the service role:

```sql
GRANT USAGE ON DATABASE COMMUNICATIONS__EU__DER__DEV TO ROLE <ROLE>;
GRANT USAGE ON SCHEMA COMMUNICATIONS__EU__DER__DEV.PFIZER_ANTIINF TO ROLE <ROLE>;
GRANT USAGE ON WAREHOUSE WH_COMMUNICATIONS__EU__DER TO ROLE <ROLE>;
GRANT USAGE ON CORTEX SEARCH SERVICE
  COMMUNICATIONS__EU__DER__DEV.PFIZER_ANTIINF.KNOWLEDGE_SEARCH TO ROLE <ROLE>;
```

## API

- `GET /health`
- `GET /metadata` with `X-API-Key`
- `POST /search` with `query` and `limit`
- `POST /query/` with `query_text` and `top_k`
- `GET /docs`

The Custom GPT artifacts are `custom-gpt-action.json` and
`custom-gpt-instructions.txt`.
