# PFIZER ANTIINF Render API

This existing Render service is permanently restricted to the tables, views,
and Cortex Search service inside:

`COMMUNICATIONS__EU__DER__DEV.PFIZER_ANTIINF`

Its semantic search service is:

`COMMUNICATIONS__EU__DER__DEV.PFIZER_ANTIINF.KNOWLEDGE_SEARCH`

Its isolated source table is:

`COMMUNICATIONS__EU__DER__DEV.PFIZER_ANTIINF.KNOWLEDGE_CHUNKS`

The service never reads from `KNOWLEDGE_HUB`. Cortex Search manages embeddings
with `snowflake-arctic-embed-m-v1.5`; no OpenAI embeddings are created.

The schema browser discovers the live `INFORMATION_SCHEMA` inventory and allows
read-only retrieval from every table/view in that inventory. It validates every
object name against that allowlist and never accepts SQL.

## Render deployment

Create the service from `pfizer-antiinf-render-api/render.yaml`, then configure:

- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER`
- `SNOWFLAKE_ROLE=RL_COMMUNICATIONS_EU_DER`
- `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` when the PEM is encrypted
- Secret file `private_key.pem`, mounted at `/etc/secrets/private_key.pem`
- `PFIZER_ANTIINF_API_KEY`

Send `PFIZER_ANTIINF_API_KEY` as the `X-API-Key` request header.

The API uses the existing `RL_COMMUNICATIONS_EU_DER` role for every Snowflake
connection. This project does not create or assign Snowflake roles.

## API

- `GET /health`
- `GET /metadata` with `X-API-Key`
- `POST /search` with `query` and `limit`
- `POST /query/` with `query_text` and `top_k`
- `GET /schema/objects` for the live table/view and column inventory
- `POST /schema/search` to search all or selected tables/views
- `GET /schema/tables/{table_name}/rows` to browse/search one table/view
- `GET /products/` with optional `therapeutic_set`
- `GET /products/{product_key}/trials`
- `GET /products/{product_key}/publications`
- `GET /trials/{nct_id}`
- `GET /publications/{pubmed_id}`
- `GET /docs`

There is no cross-database research route and no arbitrary SQL endpoint.
Every Snowflake connection disables secondary roles and fixes the database and
schema to `COMMUNICATIONS__EU__DER__DEV.PFIZER_ANTIINF`.

## Custom GPT table connector

1. Redeploy the existing Render service and confirm its `/health` endpoint returns
   `{"status":"ok"}`.
2. In the GPT editor, open **Configure > Actions**.
3. Import or paste `custom-gpt-tables-action.json`. It already uses the existing
   `https://pfizer-antiinf-search-api.onrender.com` hostname.
4. Set Authentication to **API Key**, Auth Type **Custom**, header name
   `X-API-Key`, and use the same value as Render's
   `PFIZER_ANTIINF_API_KEY` secret.
5. Paste `custom-gpt-tables-instructions.txt` into the GPT instructions.
6. Test the schema inventory, schema search, table rows, semantic search, and
   relevant product operations before publishing.

Use `custom-gpt-tables-action.json` and `custom-gpt-tables-instructions.txt` for
the schema-only Custom GPT connection.
